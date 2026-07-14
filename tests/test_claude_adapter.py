import asyncio
import json
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
    def __init__(self, events=None, *, hang=False, returncode=0):
        lines = [(json.dumps(event) + "\n").encode("utf-8") for event in (events or [])]
        self.stdin = _FakeStdin()
        self.stdout = _FakeStream(lines, hang=hang)
        self.stderr = _FakeStream([])
        self.returncode = None
        self._final_returncode = returncode
        self.killed = False

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
