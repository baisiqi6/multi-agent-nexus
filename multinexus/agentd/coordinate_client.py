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

log = logging.getLogger(__name__)


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
        message_id: str = "",
        idempotency_key: str = "",
    ) -> dict:
        """Submit a bridge request to coordinate. Returns the coordinate response dict."""
        cmd = [
            self.cli_path,
            "runtime", "request", "submit",
            self.workspace_id,
            "--target-agent", target_agent,
            "--prompt", prompt,
            "--origin-json", json.dumps(origin_json, ensure_ascii=False),
            "--reply-json", json.dumps(reply_json, ensure_ascii=False),
        ]
        if message_id:
            cmd.extend(["--idempotency-key", message_id])

        log.info("coordinate submit: agent=%s msg=%s", target_agent, message_id)

        result = await asyncio.to_thread(self._run_cli, cmd)
        return result

    async def claim_job(self, *, agent_id: str) -> dict | None:
        """Claim the next pending job for this agent. Returns job dict or None."""
        cmd = [
            self.cli_path,
            "runtime", "job", "claim",
            "--agent-id", agent_id,
        ]
        result = await asyncio.to_thread(self._run_cli, cmd)
        if result.get("result", {}).get("claimed"):
            return result["result"]["job"]
        return None

    async def report_job(
        self,
        *,
        job_id: str,
        agent_id: str,
        status: str,
        result_json: dict,
    ) -> dict:
        """Report job result back to coordinate."""
        cmd = [
            self.cli_path,
            "runtime", "job", "report",
            job_id,
            "--agent-id", agent_id,
            "--status", status,
            "--result-json", json.dumps(result_json, ensure_ascii=False),
        ]
        return await asyncio.to_thread(self._run_cli, cmd)

    async def wait_for_job_result(
        self,
        *,
        job_id: str,
        poll_interval: float = 2.0,
        timeout: float = 1800.0,
    ) -> dict | None:
        """Poll coordinate until a job reaches a terminal state, then return the result.

        Returns the job dict with result_json populated, or None on timeout.
        """
        import time as _time
        start = _time.monotonic()
        while _time.monotonic() - start < timeout:
            job = await self._get_job(job_id)
            if job is None:
                await asyncio.sleep(poll_interval)
                continue
            status = job.get("status", "")
            if status in ("done", "failed"):
                return job
            await asyncio.sleep(poll_interval)
        return None

    async def _get_job(self, job_id: str) -> dict | None:
        """Fetch a single job's current state from coordinate."""
        cmd = [
            self.cli_path,
            "job", "list",
            "--status", "all",
        ]
        result = await asyncio.to_thread(self._run_cli, cmd)
        jobs = result.get("result", {}).get("jobs", [])
        for job in jobs:
            if job.get("id") == job_id:
                return job
        return None

    def _run_cli(self, cmd: list[str]) -> dict:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=self._base_env(),
            )
            if proc.returncode != 0:
                log.error("coordinate CLI failed: %s stderr=%s", cmd, proc.stderr[:500])
                return {"error": f"CLI exit {proc.returncode}: {proc.stderr[:300]}"}
            return json.loads(proc.stdout)
        except subprocess.TimeoutExpired:
            return {"error": "coordinate CLI timed out"}
        except json.JSONDecodeError as exc:
            return {"error": f"coordinate CLI non-JSON: {exc}"}
        except Exception as exc:
            return {"error": str(exc)}
