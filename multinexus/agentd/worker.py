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
from .coordinate_client import CoordinateRuntimeClient, CoordinateRuntimeError
from .execution_context import ExecutionContextError, validate_claim_response
from .executor_binding import ExecutorBindingError, validate_executor_binding
from .execution_lease import ExecutionLeaseError, validate_execution_lease

log = logging.getLogger(__name__)


class LeaseLostError(RuntimeError):
    """Raised when the managed lease is lost or renewal fails authoritatively."""


RENEWAL_SAFETY_MARGIN_SECONDS = 5


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

    async def run(self, *, poll_interval: float = 2.0, recoverable: bool = False) -> None:
        """Main worker loop: claim jobs, execute, report.

        recoverable=True (operator recovery mode only) claims timed_out+recoverable
        jobs to resume them. Default False = normal launchd poll, only pending jobs
        (8.4.3 P1 #1: never auto-reclaim stuck timed_out jobs).
        """
        self._running = True
        if recoverable:
            log.warning("Agentd worker started in RECOVERY mode: agent=%s (will claim timed_out+recoverable jobs)", self.config.id)
        else:
            log.info("Agentd worker started: agent=%s", self.config.id)
        while self._running:
            try:
                claim_result = await self.coordinate.claim_job(
                    agent_id=self.config.id, recoverable=recoverable
                )
            except CoordinateRuntimeError as exc:
                log.error("Coordinate claim error for agent %s: %s", self.config.id, exc)
                # Bounded backoff: wait the normal poll interval before retrying.
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=poll_interval)
                except asyncio.TimeoutError:
                    pass
                self._wake.clear()
                continue

            if claim_result is None:
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=poll_interval)
                except asyncio.TimeoutError:
                    pass
                self._wake.clear()
                continue

            await self._process_job(claim_result)
        log.info("Agentd worker stopped: agent=%s", self.config.id)

    async def _process_job(self, claim_result: dict[str, Any]) -> None:
        job = claim_result.get("job") or {}
        job_id = job.get("id", "?")
        raw_attempt_token = claim_result.get("attempt_token")
        attempt_token = raw_attempt_token if isinstance(raw_attempt_token, int) else None

        # P9-3B: validate lease identity before context/binding are trusted.
        raw_lease = claim_result.get("execution_lease")
        lease_id: str | None = None
        if raw_lease is not None and isinstance(raw_lease, dict):
            try:
                lease = validate_execution_lease(
                    raw_lease,
                    expected_agent_id=self.config.id,
                    expected_job_id=job_id if job_id != "?" else None,
                    expected_attempt_token=attempt_token,
                )
                lease_id = lease.lease_id
            except ExecutionLeaseError as exc:
                log.error("Invalid execution lease for agent %s: %s", self.config.id, exc)
                # No provider invocation; report failed only if we have a usable
                # attempt token. Without one, expiry recovery will clean the job.
                if isinstance(attempt_token, int):
                    try:
                        await self.coordinate.report_job(
                            job_id=job_id,
                            agent_id=self.config.id,
                            status="failed",
                            result_json={"error": f"execution lease rejected: {exc}"},
                            attempt_token=attempt_token,
                        )
                    except CoordinateRuntimeError:
                        log.exception("Lease rejection report failed for %s", job_id)
                return

        try:
            job, ctx, attempt_token = validate_claim_response(
                {"result": claim_result},
                agent_id=self.config.id,
            )
        except ExecutionContextError as exc:
            log.error("Invalid execution context for agent %s: %s", self.config.id, exc)
            # P9-3B: if lease identity is already trusted, report failed with lease.
            if lease_id is not None and isinstance(attempt_token, int):
                try:
                    await self.coordinate.report_job(
                        job_id=job_id,
                        agent_id=self.config.id,
                        status="failed",
                        result_json={"error": f"execution context rejected: {exc}"},
                        attempt_token=attempt_token,
                        lease_id=lease_id,
                    )
                except CoordinateRuntimeError:
                    log.exception("Context rejection report failed for %s", job_id)
            elif isinstance(attempt_token, int):
                await self.coordinate.report_job(
                    job_id=job_id,
                    agent_id=self.config.id,
                    status="failed",
                    result_json={
                        "error": f"execution context rejected: {exc}",
                        "execution_context_id": "",
                    },
                    attempt_token=attempt_token,
                )
            return

        # P9-3B: re-validate lease against the now-trusted execution context.
        if raw_lease is not None and isinstance(raw_lease, dict):
            try:
                lease = validate_execution_lease(
                    raw_lease,
                    expected_agent_id=self.config.id,
                    expected_job_id=ctx.job_id,
                    expected_attempt_token=attempt_token,
                    execution_context=ctx.to_dict(),
                )
                lease_id = lease.lease_id
            except ExecutionLeaseError as exc:
                log.error("Lease cross-check failed for agent %s: %s", self.config.id, exc)
                await self.coordinate.report_job(
                    job_id=job_id,
                    agent_id=self.config.id,
                    status="failed",
                    result_json={"error": f"execution lease cross-check failed: {exc}"},
                    attempt_token=attempt_token,
                    lease_id=lease_id,
                )
                return

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
                lease_id=lease_id,
            )
            return

        binding_snapshot = payload.get("executor_binding")
        try:
            binding = validate_executor_binding(
                binding_snapshot,
                agent_id=self.config.id,
                adapter=self.config.adapter,
            )
        except ExecutorBindingError as exc:
            log.error("Executor binding mismatch for agent %s: %s", self.config.id, exc)
            await self.coordinate.report_job(
                job_id=job_id,
                agent_id=self.config.id,
                status="failed",
                result_json={"error": str(exc)},
                attempt_token=attempt_token,
                lease_id=lease_id,
            )
            return

        # P9-3B: cross-check lease against the trusted executor binding.
        if raw_lease is not None and isinstance(raw_lease, dict) and binding is not None:
            try:
                lease = validate_execution_lease(
                    raw_lease,
                    expected_agent_id=self.config.id,
                    expected_job_id=ctx.job_id,
                    expected_attempt_token=attempt_token,
                    execution_context=ctx.to_dict(),
                    executor_binding=binding_snapshot,
                )
                lease_id = lease.lease_id
            except ExecutionLeaseError as exc:
                log.error("Lease binding cross-check failed for agent %s: %s", self.config.id, exc)
                await self.coordinate.report_job(
                    job_id=job_id,
                    agent_id=self.config.id,
                    status="failed",
                    result_json={"error": f"execution lease binding cross-check failed: {exc}"},
                    attempt_token=attempt_token,
                    lease_id=lease_id,
                )
                return

        prompt = payload.get("prompt", "")
        log.info(
            "Processing job %s: agent=%s prompt_len=%d cwd=%s lease=%s",
            job_id, self.config.id, len(prompt), ctx.cwd, lease_id,
        )

        session_scope_id = ctx.session_scope_id
        legacy_scope_ids = ctx.legacy_scope_ids
        work_dir = ctx.cwd
        recovery_session_id = self._recovery_session_id(job)
        progress_callback, progress_tasks, progress_state = self._make_coordinate_progress_callback(
            job_id=job_id,
            session_scope_id=session_scope_id,
            work_dir=work_dir,
            attempt_token=attempt_token,
            lease_id=lease_id,
        )

        # P9-3B: start dedicated renewal supervisor before provider invocation.
        lease_lost = asyncio.Event()
        renewal_task: asyncio.Task | None = None
        if lease_id is not None and isinstance(attempt_token, int) and raw_lease is not None:
            renewal_task = asyncio.create_task(
                self._renewal_supervisor(
                    lease=raw_lease,
                    lease_lost=lease_lost,
                )
            )

        start = time.time()
        provider_task: asyncio.Task | None = None
        try:
            provider_task = asyncio.create_task(
                self._call_or_resume(
                    prompt,
                    session_scope_id,
                    legacy_scope_ids,
                    work_dir,
                    on_progress=progress_callback,
                    recovery_session_id=recovery_session_id,
                )
            )
            coros = [provider_task]
            if renewal_task is not None:
                coros.append(renewal_task)
            done, pending = await asyncio.wait(
                coros,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if renewal_task in done:
                # Authoritative lease loss: cancel provider and do not report normally.
                if provider_task and not provider_task.done():
                    provider_task.cancel()
                    try:
                        await provider_task
                    except asyncio.CancelledError:
                        pass
                log.error("Lease lost for job %s; provider cancelled", job_id)
                if progress_tasks:
                    await asyncio.gather(*progress_tasks, return_exceptions=True)
                return
            # Provider finished first.
            result = provider_task.result()
            if renewal_task and not renewal_task.done():
                renewal_task.cancel()
                try:
                    await renewal_task
                except asyncio.CancelledError:
                    pass
        except asyncio.CancelledError:
            if provider_task and not provider_task.done():
                provider_task.cancel()
                try:
                    await provider_task
                except asyncio.CancelledError:
                    pass
            if renewal_task and not renewal_task.done():
                renewal_task.cancel()
                try:
                    await renewal_task
                except asyncio.CancelledError:
                    pass
            raise
        except Exception as exc:
            if provider_task and not provider_task.done():
                provider_task.cancel()
                try:
                    await provider_task
                except asyncio.CancelledError:
                    pass
            if renewal_task and not renewal_task.done():
                renewal_task.cancel()
                try:
                    await renewal_task
                except asyncio.CancelledError:
                    pass
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
            "execution_context_id": ctx.context_id,
            "worktree_path": ctx.worktree_path,
            "session_scope_id": ctx.session_scope_id,
        }
        if binding is not None:
            result_json.update(binding.result_evidence())
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
            lease_id=lease_id,
        )
        log.info("Job %s complete: status=%s duration=%dms", job_id, status, duration_ms)

    async def _renewal_supervisor(
        self,
        *,
        lease: dict[str, Any],
        lease_lost: asyncio.Event,
    ) -> None:
        """Dedicated heartbeat: renew the lease before its monotonic deadline.

        Converts Coordinate's server_now + expires_at into a local monotonic
        deadline with a fixed safety margin. Ordinary renewals update the lease
        row without event spam; authoritative rejection or transport failure
        marks the lease lost and exits so the worker can cancel the provider.
        """
        from datetime import datetime, timezone

        lease_id = lease["lease_id"]
        job_id = lease["job_id"]
        attempt_token = lease["attempt_token"]
        agent_id = lease["agent_id"]
        renew_interval_seconds = lease["renew_interval_seconds"]

        def _to_monotonic_deadline(server_now: str, expires_at: str) -> float:
            server_dt = datetime.strptime(server_now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            expires_dt = datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            remaining = (expires_dt - server_dt).total_seconds()
            return time.monotonic() + remaining - RENEWAL_SAFETY_MARGIN_SECONDS

        deadline = _to_monotonic_deadline(lease["server_now"], lease["expires_at"])

        while True:
            now = time.monotonic()
            if now >= deadline:
                log.warning("Lease %s deadline reached without successful renewal", lease_id)
                lease_lost.set()
                return

            sleep_until = min(deadline, now + max(1, renew_interval_seconds))
            try:
                await asyncio.wait_for(lease_lost.wait(), timeout=sleep_until - now)
                return
            except asyncio.TimeoutError:
                pass

            try:
                response = await self.coordinate.renew_lease(
                    job_id=job_id,
                    agent_id=agent_id,
                    attempt_token=attempt_token,
                    lease_id=lease_id,
                )
            except CoordinateRuntimeError as exc:
                log.error("Lease renewal transport error for %s: %s", lease_id, exc)
                # Fail closed: treat transport failure as lease lost.
                lease_lost.set()
                return

            if not isinstance(response, dict):
                log.error("Lease renewal returned non-dict for %s", lease_id)
                lease_lost.set()
                return

            result = response.get("result")
            if not isinstance(result, dict):
                log.error("Lease renewal missing result for %s", lease_id)
                lease_lost.set()
                return

            new_expires_at = result.get("expires_at")
            new_server_now = result.get("server_now")
            if not isinstance(new_expires_at, str) or not isinstance(new_server_now, str):
                log.error("Lease renewal missing timestamps for %s", lease_id)
                lease_lost.set()
                return

            try:
                deadline = _to_monotonic_deadline(new_server_now, new_expires_at)
            except ValueError as exc:
                log.error("Lease renewal returned invalid timestamps for %s: %s", lease_id, exc)
                lease_lost.set()
                return

            log.debug("Lease %s renewed; new deadline %s", lease_id, deadline)

    def _make_coordinate_progress_callback(
        self,
        *,
        job_id: str,
        session_scope_id: str,
        work_dir: str,
        attempt_token: int | None = None,
        lease_id: str | None = None,
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
                    work_dir=work_dir,
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
                        lease_id=lease_id,
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
        "Codex resume failed",
        "Hermes CLI failed", "Hermes timed out",
        "Claude CLI failed", "Claude error:", "Claude timeout",
        "omp CLI failed", "omp timed out",
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
