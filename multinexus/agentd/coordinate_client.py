"""Client for submitting bridge requests via coordinate runtime.

Uses the coordinate CLI to submit requests, which creates pending jobs
that standalone agentd processes can claim. This is the bridge -> coordinate
part of the N+M runtime boundary.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Any

log = logging.getLogger(__name__)


class CoordinateRuntimeError(RuntimeError):
    """Raised when the Coordinate CLI returns a non-zero exit or non-JSON output."""


class CoordinateRuntimeClient:
    """Submit bridge requests to coordinate runtime.

    Wraps the coordinate CLI:
      runtime request submit <workspace> --target-agent <id> --prompt <text>
        --origin-json <json> --reply-json <json>
    """

    def __init__(
        self,
        *,
        cli_path: str,
        db_path: str,
        workspace_id: str = "discord-nexus",
    ):
        self.cli_path = cli_path
        self.db_path = db_path
        self.workspace_id = workspace_id

        if sys.platform == "win32" and cli_path.endswith(".py"):
            self._base_cmd = [sys.executable, cli_path]
        else:
            self._base_cmd = [cli_path]

    def _base_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["MAC_DB"] = self.db_path
        return env

    async def submit_request(
        self,
        *,
        target_agent: str,
        prompt: str,
        origin_json: dict,
        reply_json: dict,
        workspace_id: str = "",
        task_id: str = "",
        message_id: str = "",
        idempotency_key: str = "",
    ) -> dict:
        """Submit a bridge request to coordinate. Returns the coordinate response dict."""
        workspace = workspace_id or self.workspace_id
        cmd = [
            *self._base_cmd,
            "runtime", "request", "submit",
            workspace,
            "--target-agent", target_agent,
            "--prompt", prompt,
            "--origin-json", json.dumps(origin_json, ensure_ascii=False),
            "--reply-json", json.dumps(reply_json, ensure_ascii=False),
        ]
        if task_id:
            cmd.extend(["--task-id", task_id])
        idempotency = idempotency_key or message_id
        if idempotency:
            cmd.extend(["--idempotency-key", idempotency])

        log.info("coordinate submit: agent=%s msg=%s", target_agent, message_id)

        return await asyncio.to_thread(self._run_cli, cmd)

    async def claim_job(
        self, *, agent_id: str, recoverable: bool = False
    ) -> dict[str, Any] | None:
        """Claim the next pending job for this agent. Returns the full result envelope or None.

        recoverable=True (operator recovery mode only) also claims timed_out+
        recoverable jobs (appends --recoverable). Default False = only pending,
        so normal launchd agentd never auto-reclaims a stuck timed_out job (8.4.3 P1 #1).

        The caller must validate ``result["execution_context"]`` before invoking
        an adapter; this client preserves the raw Coordinate response.
        """
        cmd = [
            *self._base_cmd,
            "runtime", "job", "claim",
            "--agent-id", agent_id,
        ]
        if recoverable:
            cmd.append("--recoverable")
        result = await asyncio.to_thread(self._run_cli, cmd)
        if not isinstance(result, dict):
            raise CoordinateRuntimeError(
                f"coordinate claim for {agent_id} returned non-dict result"
            )
        inner = result.get("result")
        if not isinstance(inner, dict):
            raise CoordinateRuntimeError(
                f"coordinate claim for {agent_id} returned missing/invalid result envelope"
            )
        if inner.get("claimed"):
            return inner
        return None

    async def report_job(
        self,
        *,
        job_id: str,
        agent_id: str,
        status: str,
        result_json: dict,
        attempt_token: int | None = None,
    ) -> dict:
        """Report job result back to coordinate."""
        cmd = [
            *self._base_cmd,
            "runtime", "job", "report",
            job_id,
            "--agent-id", agent_id,
            "--status", status,
            "--result-json", json.dumps(result_json, ensure_ascii=False),
        ]
        if attempt_token is not None:
            cmd.extend(["--attempt-token", str(attempt_token)])
        return await asyncio.to_thread(self._run_cli, cmd)

    async def record_progress(
        self,
        *,
        job_id: str,
        agent_id: str,
        stage: str = "",
        summary: str = "",
        session_id: str = "",
        attempt_token: int | None = None,
    ) -> dict:
        """Record a bounded progress checkpoint for a running job."""
        cmd = [
            *self._base_cmd,
            "runtime", "job", "progress",
            job_id,
            "--agent-id", agent_id,
        ]
        if stage:
            cmd.extend(["--stage", stage])
        if summary:
            cmd.extend(["--summary", summary])
        if session_id:
            cmd.extend(["--session-id", session_id])
        if attempt_token is not None:
            cmd.extend(["--attempt-token", str(attempt_token)])
        return await asyncio.to_thread(self._run_cli, cmd)

    async def wait_for_job_result(
        self,
        *,
        job_id: str,
        workspace_id: str = "",
        poll_interval: float = 2.0,
        timeout: float = 1800.0,
    ) -> dict | None:
        """Poll coordinate until a job reaches a terminal state, then return the result.

        Returns the job dict with result_json populated, or None on timeout.
        """
        import time as _time
        start = _time.monotonic()
        workspace = workspace_id or self.workspace_id
        while _time.monotonic() - start < timeout:
            job = await self._get_job(job_id, workspace_id=workspace)
            if job is None:
                await asyncio.sleep(poll_interval)
                continue
            status = job.get("status", "")
            if status in ("done", "failed", "timed_out"):
                return job
            await asyncio.sleep(poll_interval)
        return None

    async def _get_job(self, job_id: str, *, workspace_id: str = "") -> dict | None:
        """Fetch a single job's current state from coordinate."""
        cmd = [
            *self._base_cmd,
            "job", "list",
            "--workspace-id", workspace_id or self.workspace_id,
        ]
        result = await asyncio.to_thread(self._run_cli, cmd)
        if not isinstance(result, dict):
            raise CoordinateRuntimeError(
                f"coordinate job list for {job_id} returned non-dict result"
            )
        jobs = result.get("jobs", [])
        if not isinstance(jobs, list):
            raise CoordinateRuntimeError(
                f"coordinate job list for {job_id} returned non-list jobs"
            )
        for job in jobs:
            if job.get("id") == job_id:
                return job
        return None

    def _run_cli(self, cmd: list[str]) -> dict:
        """Run the Coordinate CLI and return its JSON output as a dict.

        All failure modes (non-zero exit, timeout, non-JSON output, OS errors,
        and malformed envelopes) are normalized into a bounded
        CoordinateRuntimeError so the agentd loop can back off instead of
        spinning or crashing.
        """
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                env=self._base_env(),
            )
        except subprocess.TimeoutExpired:
            raise CoordinateRuntimeError("coordinate CLI timed out")
        except OSError as exc:
            raise CoordinateRuntimeError(f"coordinate CLI execution failed: {exc}")
        except Exception as exc:
            raise CoordinateRuntimeError(f"coordinate CLI unexpected error: {exc}")

        if proc.returncode != 0:
            stderr = proc.stderr[:300] if proc.stderr else ""
            raise CoordinateRuntimeError(
                f"coordinate CLI exit {proc.returncode}: {stderr}"
            )

        stdout = proc.stdout.strip()
        if not stdout:
            raise CoordinateRuntimeError("coordinate CLI returned empty stdout")

        try:
            result = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise CoordinateRuntimeError(f"coordinate CLI non-JSON: {exc}")

        if not isinstance(result, dict):
            raise CoordinateRuntimeError("coordinate CLI returned non-object JSON")

        # If Coordinate itself reported a runtime error, surface it as a bounded
        # exception rather than making every caller inspect an error dict.
        if result.get("error"):
            raise CoordinateRuntimeError(
                f"coordinate runtime error: {result['error']}"
            )

        return result
