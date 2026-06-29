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
from typing import Any

from ..adapters.base import AdapterResult
from ..adapters.factory import make_adapter
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
        attempt_token = job.get("attempt_count")  # 8.4.3 P1 #2: CAS token from claim
        try:
            payload = self._extract_payload(job)
        except ValueError as exc:
            log.error("Invalid payload for job %s", job_id)
            await self.coordinate.report_job(
                job_id=job_id,
                agent_id=self.config.id,
                status="failed",
                result_json={"error": str(exc)},
                attempt_token=attempt_token,
            )
            return

        prompt = payload.get("prompt", "")
        origin = payload.get("origin", {})
        log.info("Processing job %s: agent=%s prompt_len=%d", job_id, self.config.id, len(prompt))

        # Extract session scope from bridge payload
        session_scope_id = origin.get("session_scope_id", "")
        legacy_scope_ids = tuple(origin.get("legacy_scope_ids", []))
        work_dir = self.config.work_dir
        recovery_session_id = self._recovery_session_id(job)
        progress_callback, progress_tasks, progress_state = self._make_coordinate_progress_callback(
            job_id=job_id,
            session_scope_id=session_scope_id,
            attempt_token=attempt_token,
        )

        start = time.time()
        try:
            result = await self._call_or_resume(
                prompt,
                session_scope_id,
                legacy_scope_ids,
                work_dir,
                on_progress=progress_callback,
                recovery_session_id=recovery_session_id,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            result = AdapterResult(text=f"Agent error: {exc}")

        if progress_tasks:
            await asyncio.gather(*progress_tasks, return_exceptions=True)

        duration_ms = int((time.time() - start) * 1000)

        if result.session_id and session_scope_id:
            self.session_store.upsert(
                scope_id=session_scope_id,
                agent_id=self.config.id,
                adapter=self.config.adapter,
                session_id=result.session_id,
                work_dir=work_dir,
            )

        status = self._status_for_result(result)
        result_json = {
            "response_text": result.text,
            "session_id": result.session_id or "",
            "duration_ms": duration_ms,
        }
        if progress_state:
            result_json["progress"] = dict(progress_state)
        if "timeout" in result.metadata:
            result_json["timeout"] = {
                **result.metadata["timeout"],
                "progress": dict(progress_state),
            }

        await self.coordinate.report_job(
            job_id=job_id,
            agent_id=self.config.id,
            status=status,
            result_json=result_json,
            attempt_token=attempt_token,
        )
        log.info("Job %s complete: status=%s duration=%dms", job_id, status, duration_ms)

    def _make_coordinate_progress_callback(
        self,
        *,
        job_id: str,
        session_scope_id: str,
        attempt_token: int | None = None,
    ):
        tasks: list[asyncio.Task] = []
        state: dict[str, str] = {}
        sent: dict[str, float | str] = {"at": 0.0, "session_id": ""}

        def _record(update: str | dict[str, Any]) -> None:
            progress = self._normalize_progress(update)
            if not progress:
                return
            state.update({k: v for k, v in progress.items() if v})
            session_id = progress.get("session_id", "")
            if session_id and session_scope_id:
                self.session_store.upsert(
                    scope_id=session_scope_id,
                    agent_id=self.config.id,
                    adapter=self.config.adapter,
                    session_id=session_id,
                    work_dir=self.config.work_dir,
                )
            now = time.monotonic()
            should_send = bool(session_id and session_id != sent.get("session_id"))
            should_send = should_send or (now - float(sent.get("at", 0.0)) >= 10.0)
            if not should_send:
                return
            sent["at"] = now
            if session_id:
                sent["session_id"] = session_id
            tasks.append(
                asyncio.create_task(
                    self.coordinate.record_progress(
                        job_id=job_id,
                        agent_id=self.config.id,
                        stage=progress.get("stage", ""),
                        summary=progress.get("summary", ""),
                        session_id=session_id,
                        attempt_token=attempt_token,
                    )
                )
            )

        return _record, tasks, state

    @staticmethod
    def _normalize_progress(update: str | dict[str, Any]) -> dict[str, str]:
        if isinstance(update, dict):
            progress: dict[str, str] = {}
            for key in ("stage", "summary", "session_id"):
                value = update.get(key)
                if isinstance(value, str) and value.strip():
                    limit = 200 if key == "session_id" else 1000
                    progress[key] = value.strip()[:limit]
            return progress
        if isinstance(update, str) and update.strip():
            return {"summary": update.strip()[:1000]}
        return {}

    @staticmethod
    def _recovery_session_id(job: dict) -> str:
        for candidate in (
            job.get("terminal_session_id"),
            (job.get("progress") or {}).get("session_id") if isinstance(job.get("progress"), dict) else "",
            ((job.get("result") or {}).get("timeout") or {}).get("session_id")
            if isinstance(job.get("result"), dict) and isinstance((job.get("result") or {}).get("timeout"), dict)
            else "",
            (job.get("result") or {}).get("session_id") if isinstance(job.get("result"), dict) else "",
        ):
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    @staticmethod
    def _extract_payload(job: dict) -> dict:
        """Accept both current coordinate CLI payload shape and legacy raw JSON."""
        payload = job.get("payload")
        if isinstance(payload, dict):
            return payload
        if payload is not None:
            raise ValueError("payload must be an object")

        payload_json = job.get("payload_json")
        if payload_json in (None, ""):
            return {}
        if isinstance(payload_json, dict):
            return payload_json
        if not isinstance(payload_json, str):
            raise ValueError("payload_json must be a JSON string")
        try:
            decoded = json.loads(payload_json)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid payload_json") from exc
        if not isinstance(decoded, dict):
            raise ValueError("payload_json must decode to an object")
        return decoded

    async def _call_or_resume(
        self,
        prompt: str,
        session_scope_id: str,
        legacy_scope_ids: tuple[str, ...],
        work_dir: str | None,
        *,
        on_progress=None,
        recovery_session_id: str = "",
    ) -> AdapterResult:
        """Check session store for existing session; resume if found, else fresh call."""
        if not session_scope_id:
            if recovery_session_id:
                return await self._resume_recoverable_session(
                    recovery_session_id,
                    prompt,
                    work_dir=work_dir,
                    on_progress=on_progress,
                )
            return await self.adapter.call(
                prompt,
                timeout=self.config.timeout,
                work_dir=work_dir,
                on_progress=on_progress,
            )

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

        # 8.4.3 P1 #3: recovery_session_id present ⇒ always fail-closed recoverable
        # resume, EVEN IF an existing session is also present. The legacy existing-
        # session resume below falls back to a fresh duplicate on error, which must
        # never happen for a recoverable job (invariant 4: no fresh duplicate).
        if recovery_session_id:
            return await self._resume_recoverable_session(
                recovery_session_id,
                prompt,
                work_dir=work_dir,
                on_progress=on_progress,
            )

        if existing:
            log.info(
                "Resuming session %s for scope=%s",
                existing["session_id"], existing["scope_id"],
            )
            result: AdapterResult = await self.adapter.resume(
                existing["session_id"],
                prompt,
                timeout=self.config.timeout,
                work_dir=work_dir,
                on_progress=on_progress,
            )
            if self._is_error(result.text):
                log.warning("Resume failed for %s, falling back to fresh call", existing["session_id"])
                self.session_store.mark_stale(
                    scope_id=existing["scope_id"],
                    agent_id=self.config.id,
                )
                result = await self.adapter.call(
                    prompt,
                    timeout=self.config.timeout,
                    work_dir=work_dir,
                    on_progress=on_progress,
                )
            return result

        return await self.adapter.call(
            prompt,
            timeout=self.config.timeout,
            work_dir=work_dir,
            on_progress=on_progress,
        )

    async def _resume_recoverable_session(
        self,
        session_id: str,
        prompt: str,
        *,
        work_dir: str | None,
        on_progress=None,
    ) -> AdapterResult:
        log.info("Resuming recoverable session %s", session_id)
        result: AdapterResult = await self.adapter.resume(
            session_id,
            prompt,
            timeout=self.config.timeout,
            work_dir=work_dir,
            on_progress=on_progress,
        )
        if self._is_error(result.text):
            return AdapterResult(
                text=(
                    "Agent error: recoverable session resume failed; "
                    "not starting duplicate fresh execution"
                ),
                session_id=session_id,
                resumed=True,
            )
        return result

    def stop(self) -> None:
        self._running = False
        self._wake.set()

    _ERROR_PREFIXES = (
        "Agent error:",
        "OpenCode CLI failed", "OpenCode timed out", "OpenCode returned no text",
        "Codex CLI failed", "Codex timed out", "Codex stopped responding",
        "Hermes CLI failed", "Hermes timed out",
        "Claude CLI failed", "Claude error:", "Claude timeout",
    )

    @classmethod
    def _is_error(cls, text: str) -> bool:
        return any(text.startswith(p) for p in cls._ERROR_PREFIXES)

    @classmethod
    def _status_for_result(cls, result: AdapterResult) -> str:
        if result.metadata.get("timeout"):
            return "timed_out"
        if result.text.startswith("Claude timeout:"):
            return "timed_out"
        return "done" if not cls._is_error(result.text) else "failed"
