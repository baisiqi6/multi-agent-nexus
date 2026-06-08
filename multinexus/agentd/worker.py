"""Standalone agentd worker: claims jobs from coordinate, executes adapter, reports.

This is the `agentd` side of the N+M runtime boundary:
```text
bridge -> coordinate runtime request submit -> coordinate job
agentd worker -> coordinate runtime job claim -> execute adapter -> report
```

Run as: ``python -m multinexus.agentd --config agents.toml --agent <id>``
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from ..adapters.base import AdapterResult
from ..adapters.factory import make_adapter
from ..config import load_config
from ..models import AgentConfig
from ..sessions.store import SessionStore
from .coordinate_client import CoordinateRuntimeClient

log = logging.getLogger(__name__)


class AgentdWorker:
    """Standalone agentd that claims jobs from coordinate and processes them."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.adapter = make_adapter(config)
        self.session_store = SessionStore(config.context_db_path)
        self.coordinate = CoordinateRuntimeClient(
            cli_path=config.coordinator_cli_path,
            db_path=config.coordinator_db_path,
        )
        self._running = False
        self._wake = asyncio.Event()

    async def run(self, *, poll_interval: float = 2.0) -> None:
        """Main worker loop: claim jobs, execute, report."""
        self._running = True
        log.info("Agentd worker started: agent=%s", self.config.id)
        while self._running:
            job = await self.coordinate.claim_job(agent_id=self.config.id)
            if job is None:
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=poll_interval)
                except asyncio.TimeoutError:
                    pass
                self._wake.clear()
                continue
            await self._process_job(job)
        log.info("Agentd worker stopped: agent=%s", self.config.id)

    async def _process_job(self, job: dict) -> None:
        job_id = job.get("id", "?")
        payload_str = job.get("payload_json", "{}")
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            log.error("Invalid payload for job %s", job_id)
            await self.coordinate.report_job(
                job_id=job_id,
                agent_id=self.config.id,
                status="failed",
                result_json={"error": "invalid payload_json"},
            )
            return

        prompt = payload.get("prompt", "")
        origin = payload.get("origin", {})
        log.info("Processing job %s: agent=%s prompt_len=%d", job_id, self.config.id, len(prompt))

        # Extract session scope from bridge payload
        session_scope_id = origin.get("session_scope_id", "")
        legacy_scope_ids = tuple(origin.get("legacy_scope_ids", []))
        work_dir = self.config.work_dir

        start = time.time()
        try:
            result = await asyncio.wait_for(
                self._call_or_resume(prompt, session_scope_id, legacy_scope_ids, work_dir),
                timeout=self.config.timeout,
            )
        except asyncio.TimeoutError:
            result = AdapterResult(text=f"Agent error: timed out after {self.config.timeout}s")
        except Exception as exc:
            result = AdapterResult(text=f"Agent error: {exc}")

        duration_ms = int((time.time() - start) * 1000)

        if result.session_id and session_scope_id:
            self.session_store.upsert(
                scope_id=session_scope_id,
                agent_id=self.config.id,
                adapter=self.config.adapter,
                session_id=result.session_id,
                work_dir=work_dir,
            )

        status = "done" if not self._is_error(result.text) else "failed"
        result_json = {
            "response_text": result.text,
            "session_id": result.session_id or "",
            "duration_ms": duration_ms,
        }

        await self.coordinate.report_job(
            job_id=job_id,
            agent_id=self.config.id,
            status=status,
            result_json=result_json,
        )
        log.info("Job %s complete: status=%s duration=%dms", job_id, status, duration_ms)

    async def _call_or_resume(
        self,
        prompt: str,
        session_scope_id: str,
        legacy_scope_ids: tuple[str, ...],
        work_dir: str | None,
    ) -> AdapterResult:
        """Check session store for existing session; resume if found, else fresh call."""
        if not session_scope_id:
            return await self.adapter.call(prompt, work_dir=work_dir)

        existing = self.session_store.get_first_active(
            scope_ids=(session_scope_id, *legacy_scope_ids),
            agent_id=self.config.id,
        )

        if existing:
            current_work_dir = work_dir
            if (
                current_work_dir
                and existing.get("work_dir")
                and current_work_dir != existing["work_dir"]
            ):
                log.info(
                    "Session work_dir mismatch (had=%s now=%s), marking stale",
                    existing["work_dir"], current_work_dir,
                )
                self.session_store.mark_stale(
                    scope_id=existing["scope_id"],
                    agent_id=self.config.id,
                )
                existing = None

        if existing:
            log.info(
                "Resuming session %s for scope=%s",
                existing["session_id"], existing["scope_id"],
            )
            result: AdapterResult = await self.adapter.resume(
                existing["session_id"],
                prompt,
                work_dir=work_dir,
            )
            if self._is_error(result.text):
                log.warning("Resume failed for %s, falling back to fresh call", existing["session_id"])
                self.session_store.mark_stale(
                    scope_id=existing["scope_id"],
                    agent_id=self.config.id,
                )
                result = await self.adapter.call(prompt, work_dir=work_dir)
            return result

        return await self.adapter.call(prompt, work_dir=work_dir)

    def stop(self) -> None:
        self._running = False
        self._wake.set()

    _ERROR_PREFIXES = (
        "Agent error:",
        "OpenCode CLI failed", "OpenCode timed out",
        "Codex CLI failed", "Codex timed out", "Codex stopped responding",
        "Hermes CLI failed", "Hermes timed out",
        "Claude CLI failed", "Claude error:", "Claude timeout",
    )

    @classmethod
    def _is_error(cls, text: str) -> bool:
        return any(text.startswith(p) for p in cls._ERROR_PREFIXES)
