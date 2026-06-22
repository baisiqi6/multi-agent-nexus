import asyncio
import json
import contextlib

from ..models import AgentConfig
from .base import AdapterResult, AgentAdapter
from .utils import NO_WINDOW, filtered_env


def _timeout_message(kind: str, elapsed_seconds: int, total_seconds: int) -> str:
    return (
        f"Claude timeout:{kind} after {elapsed_seconds}s "
        f"(total budget {total_seconds}s). Aborted, no handoff."
    )


async def _kill_process(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        proc.kill()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        pass


def _emit_progress(on_progress, update: dict) -> None:
    if not on_progress:
        return
    on_progress(update)


def _progress_summary_from_event(event: dict) -> str:
    content = event.get("content")
    if content is None and isinstance(event.get("message"), dict):
        content = event["message"].get("content")
    if isinstance(content, str):
        return content.strip()[:1000]
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") not in {"text", "text_delta"}:
                continue
            text = item.get("text") or item.get("delta")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        return "\n".join(parts).strip()[:1000]
    return ""


class ClaudeAdapter(AgentAdapter):
    def __init__(self, config: AgentConfig):
        super().__init__(name="claude", timeout=config.timeout)
        self.config = config

    def _with_system_prompt(self, prompt: str) -> str:
        if not self.config.system_prompt.strip():
            return prompt
        return f"{self.config.system_prompt.strip()}\n\nUSER: {prompt}"

    def _build_cmd(self, *, resume_session_id: str | None = None) -> list[str]:
        cmd = [
            self.config.claude_bin,
            "-p",
            "--verbose",
            "--output-format",
            "stream-json",
            "--include-partial-messages",
        ]
        if self.config.claude_dangerously_skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        if self.config.model:
            cmd += ["--model", self.config.model]
        if resume_session_id:
            cmd += ["--resume", resume_session_id]
        return cmd

    async def call(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
        work_dir: str | None = None,
        on_progress=None,
    ) -> AdapterResult:
        return await self._run(prompt, timeout=timeout, work_dir=work_dir, on_progress=on_progress)

    async def resume(
        self,
        session_id: str,
        prompt: str,
        *,
        timeout: int | None = None,
        work_dir: str | None = None,
        on_progress=None,
    ) -> AdapterResult:
        result = await self._run(
            prompt,
            timeout=timeout,
            work_dir=work_dir,
            on_progress=on_progress,
            resume_session_id=session_id,
        )
        result.resumed = True
        return result

    async def _run(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
        work_dir: str | None = None,
        on_progress=None,
        resume_session_id: str | None = None,
    ) -> AdapterResult:
        timeout = timeout or self.config.timeout
        cmd = self._build_cmd(resume_session_id=resume_session_id)
        cwd = work_dir or self.config.work_dir

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=filtered_env(cwd=cwd),
                limit=10 * 1024 * 1024,
                **NO_WINDOW,
            )
        except FileNotFoundError:
            return AdapterResult(text=f"Claude CLI not found: {self.config.claude_bin}")

        response_text = ""
        session_id: str | None = resume_session_id
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        last_activity = loop.time()
        saw_output = False

        try:
            full_prompt = self._with_system_prompt(prompt)
            assert proc.stdin is not None
            proc.stdin.write(full_prompt.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

            while True:
                now = loop.time()
                if now >= deadline:
                    await _kill_process(proc)
                    return AdapterResult(
                        text=_timeout_message("total", timeout, timeout),
                        session_id=session_id,
                        metadata={
                            "timeout": {
                                "kind": "total",
                                "configured_budget_seconds": timeout,
                                "session_id": session_id or "",
                                "resume_allowed": bool(session_id),
                            }
                        },
                    )

                assert proc.stdout is not None
                idle_timeout = (
                    self.config.activity_timeout if saw_output else self.config.first_byte_timeout
                )
                read_timeout = min(idle_timeout, deadline - now)
                try:
                    raw = await asyncio.wait_for(proc.stdout.readline(), timeout=read_timeout)
                except asyncio.TimeoutError:
                    elapsed = loop.time() - last_activity
                    if not saw_output and elapsed >= self.config.first_byte_timeout:
                        await _kill_process(proc)
                        return AdapterResult(
                            text=_timeout_message("first_byte", self.config.first_byte_timeout, timeout),
                            session_id=session_id,
                            metadata={
                                "timeout": {
                                    "kind": "first_byte",
                                    "configured_budget_seconds": timeout,
                                    "session_id": session_id or "",
                                    "resume_allowed": bool(session_id),
                                }
                            },
                        )
                    if saw_output and elapsed >= self.config.activity_timeout:
                        await _kill_process(proc)
                        return AdapterResult(
                            text=_timeout_message("activity", self.config.activity_timeout, timeout),
                            session_id=session_id,
                            metadata={
                                "timeout": {
                                    "kind": "activity",
                                    "configured_budget_seconds": timeout,
                                    "session_id": session_id or "",
                                    "resume_allowed": bool(session_id),
                                }
                            },
                        )
                    continue
                if not raw:
                    break
                last_activity = loop.time()
                saw_output = True
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    event.get("type") == "system"
                    and event.get("subtype") == "init"
                    and event.get("session_id")
                ):
                    session_id = event["session_id"]
                    _emit_progress(
                        on_progress,
                        {
                            "stage": "session",
                            "summary": "Claude session initialized",
                            "session_id": session_id,
                        },
                    )
                summary = _progress_summary_from_event(event)
                if summary:
                    _emit_progress(
                        on_progress,
                        {"stage": "stream", "summary": summary, "session_id": session_id or ""},
                    )
                if event.get("type") == "result":
                    if event.get("subtype") == "error" or event.get("is_error"):
                        return AdapterResult(
                            text=f"Claude error: {event.get('result', '')[:500]}",
                            session_id=session_id,
                        )
                    response_text = event.get("result", "") or response_text

            await proc.wait()
            if not response_text and proc.returncode != 0:
                assert proc.stderr is not None
                stderr = (await proc.stderr.read()).decode("utf-8", errors="replace")
                return AdapterResult(
                    text=f"Claude CLI failed ({proc.returncode}): {stderr[:500]}",
                    session_id=session_id,
                )
            return AdapterResult(
                text=response_text.strip() or "(no response)",
                session_id=session_id,
            )
        except asyncio.CancelledError:
            await _kill_process(proc)
            raise
        except Exception as exc:
            await _kill_process(proc)
            return AdapterResult(text=f"Claude error: {exc}", session_id=session_id)

    async def health_check(self) -> dict:
        import shutil

        found = shutil.which(self.config.claude_bin)
        return {
            "adapter": "claude",
            "bin": self.config.claude_bin,
            "available": found is not None,
            "path": found,
        }
