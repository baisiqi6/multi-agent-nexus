import asyncio
import json
import logging
import unittest
from unittest.mock import patch

from multinexus.adapters.claude import ClaudeAdapter
from multinexus.models import AgentConfig


class _FakeStream:
    def __init__(self, lines=None, *, hang=False):
        self._lines = list(lines or [])
        self._hang = hang

    async def readline(self):
        if self._lines:
            return self._lines.pop(0)
        if self._hang:
            await asyncio.Event().wait()
        return b""

    async def read(self):
        return b""


class _FakeStdin:
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data

    async def drain(self):
        return None

    def close(self):
        return None


class _FakeProcess:
    _next_pid = 1000

    def __init__(self, events=None, *, hang=False, returncode=0):
        lines = [(json.dumps(event) + "\n").encode("utf-8") for event in (events or [])]
        self.stdin = _FakeStdin()
        self.stdout = _FakeStream(lines, hang=hang)
        self.stderr = _FakeStream([])
        self.returncode = None
        self._final_returncode = returncode
        self.killed = False
        self.pid = _FakeProcess._next_pid
        _FakeProcess._next_pid += 1

    async def wait(self):
        self.returncode = self._final_returncode
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


def _config(**overrides):
    values = {
        "id": "mac-claude",
        "token": "",
        "adapter": "claude",
        "claude_bin": "claude",
        "work_dir": ".",
        "timeout": 30,
        "first_byte_timeout": 5,
        "activity_timeout": 5,
    }
    values.update(overrides)
    return AgentConfig(**values)


class ClaudeAdapterProgressTests(unittest.IsolatedAsyncioTestCase):
    async def test_emits_session_and_safe_progress(self):
        events = [
            {"type": "system", "subtype": "init", "session_id": "sess-1"},
            {"type": "assistant", "content": [{"type": "text", "text": "edited file"}]},
            {"type": "result", "result": "done"},
        ]
        proc = _FakeProcess(events)
        progress = []
        spawn_kwargs = {}

        async def fake_exec(*args, **kwargs):
            spawn_kwargs.update(kwargs)
            return proc

        adapter = ClaudeAdapter(_config())
        with (
            patch("multinexus.adapters.claude.asyncio.create_subprocess_exec", new=fake_exec),
            patch(
                "multinexus.adapters.claude.async_subprocess_kwargs",
                return_value={"start_new_session": True},
            ),
        ):
            result = await adapter.call("do work", on_progress=progress.append)

        self.assertEqual(result.text, "done")
        self.assertEqual(result.session_id, "sess-1")
        self.assertIs(spawn_kwargs["start_new_session"], True)
        self.assertIn(
            {"stage": "session", "summary": "Claude session initialized", "session_id": "sess-1"},
            progress,
        )
        self.assertIn(
            {"stage": "stream", "summary": "edited file", "session_id": "sess-1"},
            progress,
        )


class ClaudeAdapterBoundaryLogTests(unittest.IsolatedAsyncioTestCase):
    async def test_boundary_log_uses_frozen_clock_and_matches_timer_anchor(self):
        events = [
            {"type": "system", "subtype": "init", "session_id": "sess-boundary"},
            {"type": "result", "result": "done"},
        ]
        proc = _FakeProcess(events)
        frozen_ns = 1_700_000_000_000_000_000

        async def fake_exec(*args, **kwargs):
            return proc

        class FrozenLoop:
            def time(self):
                return frozen_ns / 1_000_000_000

        adapter = ClaudeAdapter(_config())
        with (
            patch("multinexus.adapters.claude.asyncio.create_subprocess_exec", new=fake_exec),
            patch("multinexus.adapters.claude.async_subprocess_kwargs", return_value={}),
            patch("multinexus.adapters.claude.asyncio.get_event_loop", return_value=FrozenLoop()),
        ):
            with self.assertLogs("multinexus.adapters.claude", level="DEBUG") as cm:
                result = await adapter.call("do work")

        self.assertEqual(result.text, "done")
        boundary_records = [
            r for r in cm.records if "claude_child_boundary" in r.getMessage()
        ]
        self.assertEqual(len(boundary_records), 1)
        message = boundary_records[0].getMessage()
        self.assertIn(f"monotonic_ns={frozen_ns}", message)
        self.assertIn(f"pid={proc.pid}", message)
        self.assertIn("claude_child_boundary", message)

    async def test_boundary_log_precedes_stdin_write(self):
        events = [{"type": "result", "result": "ok"}]
        proc = _FakeProcess(events)
        log_before_write = []
        boundary_seen = {"value": False}

        class BoundaryHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records = []

            def emit(self, record):
                self.records.append(record)
                if "claude_child_boundary" in record.getMessage():
                    boundary_seen["value"] = True

        original_write = proc.stdin.write

        def capture_write(data):
            log_before_write.append(boundary_seen["value"])
            return original_write(data)

        proc.stdin.write = capture_write

        async def fake_exec(*args, **kwargs):
            return proc

        adapter = ClaudeAdapter(_config())
        logger = logging.getLogger("multinexus.adapters.claude")
        handler = BoundaryHandler()
        prior_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            with (
                patch("multinexus.adapters.claude.asyncio.create_subprocess_exec", new=fake_exec),
                patch("multinexus.adapters.claude.async_subprocess_kwargs", return_value={}),
            ):
                await adapter.call("x")
        finally:
            logger.removeHandler(handler)
            logger.setLevel(prior_level)

        write_happened = proc.stdin.data.find(b"x") >= 0
        self.assertTrue(write_happened)
        boundary_index = next(
            i for i, r in enumerate(handler.records) if "claude_child_boundary" in r.getMessage()
        )
        # There are no records before the boundary that contain the prompt bytes.
        for r in handler.records[:boundary_index]:
            self.assertNotIn("x", r.getMessage())
        # The boundary log emitted before the synchronous write to stdin.
        self.assertEqual(log_before_write, [True])

    async def test_boundary_log_does_not_call_on_progress(self):
        events = [{"type": "result", "result": "ok"}]
        proc = _FakeProcess(events)
        progress = []

        async def fake_exec(*args, **kwargs):
            return proc

        adapter = ClaudeAdapter(_config())
        with (
            patch("multinexus.adapters.claude.asyncio.create_subprocess_exec", new=fake_exec),
            patch("multinexus.adapters.claude.async_subprocess_kwargs", return_value={}),
        ):
            with self.assertLogs("multinexus.adapters.claude", level="DEBUG") as cm:
                await adapter.call("x", on_progress=progress.append)

        self.assertEqual(progress, [])
        boundary_message = next(
            r.getMessage() for r in cm.records if "claude_child_boundary" in r.getMessage()
        )
        self.assertNotIn("progress", boundary_message.lower())

    async def test_boundary_log_contains_no_prompt_or_environment(self):
        events = [{"type": "result", "result": "ok"}]
        proc = _FakeProcess(events)

        async def fake_exec(*args, **kwargs):
            return proc

        adapter = ClaudeAdapter(_config())
        with (
            patch("multinexus.adapters.claude.asyncio.create_subprocess_exec", new=fake_exec),
            patch("multinexus.adapters.claude.async_subprocess_kwargs", return_value={}),
        ):
            with self.assertLogs("multinexus.adapters.claude", level="DEBUG") as cm:
                await adapter.call("secret prompt text")

        boundary_message = next(
            r.getMessage() for r in cm.records if "claude_child_boundary" in r.getMessage()
        )
        self.assertNotIn("secret", boundary_message)
        self.assertNotIn("PATH", boundary_message)
        self.assertNotIn("PWD", boundary_message)
        self.assertNotIn("HOME", boundary_message)


class ClaudeAdapterCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_activity_timeout_kills_process_and_preserves_session_id(self):
        proc = _FakeProcess(
            [{"type": "system", "subtype": "init", "session_id": "sess-timeout"}],
            hang=True,
        )

        async def fake_exec(*args, **kwargs):
            return proc

        cleanup_calls = []

        async def fake_cleanup(target):
            cleanup_calls.append(target)
            target.kill()
            await target.wait()

        adapter = ClaudeAdapter(_config(timeout=30, activity_timeout=0))
        with (
            patch("multinexus.adapters.claude.asyncio.create_subprocess_exec", new=fake_exec),
            patch(
                "multinexus.adapters.claude.terminate_owned_process_group",
                new=fake_cleanup,
            ),
        ):
            result = await adapter.call("hang")

        self.assertTrue(proc.killed)
        self.assertEqual(cleanup_calls, [proc])
        self.assertEqual(result.session_id, "sess-timeout")
        self.assertEqual(result.metadata["timeout"]["kind"], "activity")
        self.assertTrue(result.metadata["timeout"]["resume_allowed"])

    async def test_cancellation_kills_process(self):
        proc = _FakeProcess(hang=True)

        async def fake_exec(*args, **kwargs):
            return proc

        cleanup_calls = []

        async def fake_cleanup(target):
            cleanup_calls.append(target)
            target.kill()
            await target.wait()

        adapter = ClaudeAdapter(_config())
        with (
            patch("multinexus.adapters.claude.asyncio.create_subprocess_exec", new=fake_exec),
            patch(
                "multinexus.adapters.claude.terminate_owned_process_group",
                new=fake_cleanup,
            ),
        ):
            task = asyncio.create_task(adapter.call("hang"))
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertTrue(proc.killed)
        self.assertEqual(cleanup_calls, [proc])

    async def test_cleanup_failure_is_reported_without_retry(self):
        proc = _FakeProcess(hang=True)

        async def fake_exec(*args, **kwargs):
            return proc

        cleanup_calls = []

        async def failing_cleanup(target):
            cleanup_calls.append(target)
            raise RuntimeError("process group cleanup failed")

        adapter = ClaudeAdapter(_config(first_byte_timeout=0))
        with (
            patch("multinexus.adapters.claude.asyncio.create_subprocess_exec", new=fake_exec),
            patch(
                "multinexus.adapters.claude.terminate_owned_process_group",
                new=failing_cleanup,
            ),
        ):
            result = await adapter.call("hang")

        self.assertEqual(cleanup_calls, [proc])
        self.assertIn("process group cleanup failed", result.text)
