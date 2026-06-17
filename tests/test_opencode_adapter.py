import asyncio
import json
import unittest
from unittest.mock import patch

from multinexus.adapters.opencode import OpenCodeAdapter
from multinexus.models import AgentConfig


class _FakeStream:
    def __init__(self, lines):
        self._lines = list(lines)

    async def readline(self):
        if not self._lines:
            return b""
        return self._lines.pop(0)

    async def read(self):
        return b""


class _FakeStdin:
    def write(self, data):
        self.data = data

    async def drain(self):
        return None

    def close(self):
        return None


class _FakeProcess:
    def __init__(self, events, returncode=0):
        self.stdin = _FakeStdin()
        self.stdout = _FakeStream(
            [(json.dumps(event) + "\n").encode("utf-8") for event in events]
        )
        self.stderr = _FakeStream([])
        self.returncode = returncode
        self.killed = False

    async def wait(self):
        return self.returncode

    def kill(self):
        self.killed = True


def _config():
    return AgentConfig(
        id="win-opencode",
        token="",
        adapter="opencode",
        opencode_bin="opencode",
        work_dir=".",
        timeout=30,
        first_byte_timeout=5,
        activity_timeout=5,
    )


class OpenCodeAdapterRetryTests(unittest.TestCase):
    def test_retries_empty_success_without_tool_use(self):
        calls = []
        processes = [
            _FakeProcess([{"type": "step_start", "sessionID": "s1"}]),
            _FakeProcess(
                [
                    {"type": "step_start", "sessionID": "s2"},
                    {"type": "text", "part": {"text": "ok"}},
                ]
            ),
        ]

        async def fake_create(*args, **kwargs):
            calls.append((args, kwargs))
            return processes.pop(0)

        async def run():
            adapter = OpenCodeAdapter(_config())
            with patch("multinexus.adapters.opencode.asyncio.create_subprocess_exec", fake_create):
                return await adapter.call("reply ok")

        result = asyncio.run(run())

        self.assertEqual(result.text, "ok")
        self.assertEqual(len(calls), 2)

    def test_does_not_retry_empty_success_after_tool_use(self):
        calls = []
        processes = [
            _FakeProcess(
                [
                    {"type": "step_start", "sessionID": "s1"},
                    {"type": "tool_use", "part": {"tool": "edit"}},
                ]
            )
        ]

        async def fake_create(*args, **kwargs):
            calls.append((args, kwargs))
            return processes.pop(0)

        async def run():
            adapter = OpenCodeAdapter(_config())
            with patch("multinexus.adapters.opencode.asyncio.create_subprocess_exec", fake_create):
                return await adapter.call("reply ok")

        result = asyncio.run(run())

        self.assertEqual(result.text, "(no response)")
        self.assertEqual(len(calls), 1)
