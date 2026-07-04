import asyncio
import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from multinexus.adapters.base import AdapterResult
from multinexus.adapters.jarvis import JarvisAdapter
from multinexus.models import AgentConfig


class FakeProcess:
    def __init__(
        self,
        stdout: bytes = b"jarvis response\n",
        stderr: bytes = b"",
        returncode: int = 0,
    ):
        self.stdout_data = stdout
        self.stderr_data = stderr
        self.returncode = returncode
        self.killed = False
        # communicate may receive stdin input; ignore it
        self.communicate = AsyncMock(return_value=(self.stdout_data, self.stderr_data))

    def kill(self) -> None:
        self.killed = True


def _make_config(**overrides) -> AgentConfig:
    values = {
        "id": "pad-jarvis",
        "token": "fake-token",
        "adapter": "jarvis",
        "timeout": 30,
        "jarvis_ssh_host": "vivoPad6p-ubuntu",
    }
    values.update(overrides)
    return AgentConfig(**values)


class TestJarvisCallSuccess(unittest.IsolatedAsyncioTestCase):
    async def test_basic_response(self):
        adapter = JarvisAdapter(_make_config())
        proc = FakeProcess(stdout=b"Hello from Jarvis\n")
        with patch("multinexus.adapters.jarvis.asyncio.create_subprocess_exec", return_value=proc):
            result = await adapter.call("hi")
        self.assertEqual(result.text, "Hello from Jarvis")
        self.assertEqual(result.metadata["engine"], "jarvis")

    async def test_empty_response(self):
        adapter = JarvisAdapter(_make_config())
        proc = FakeProcess(stdout=b"   \n")
        with patch("multinexus.adapters.jarvis.asyncio.create_subprocess_exec", return_value=proc):
            result = await adapter.call("hi")
        self.assertEqual(result.text, "")


class TestJarvisCallFailure(unittest.IsolatedAsyncioTestCase):
    async def test_nonzero_exit_returns_stderr(self):
        adapter = JarvisAdapter(_make_config())
        proc = FakeProcess(stdout=b"", stderr=b"brain module not found\n", returncode=1)
        with patch("multinexus.adapters.jarvis.asyncio.create_subprocess_exec", return_value=proc):
            result = await adapter.call("hi")
        self.assertIn("brain module not found", result.text)
        self.assertEqual(result.metadata["error"], "ssh_fail")

    async def test_timeout(self):
        adapter = JarvisAdapter(_make_config(timeout=1))
        proc = FakeProcess()
        # Make communicate hang
        async def _hang(_input=None):
            await asyncio.sleep(100)
            return b"", b""
        proc.communicate = _hang
        with patch("multinexus.adapters.jarvis.asyncio.create_subprocess_exec", return_value=proc):
            result = await adapter.call("hi")
        self.assertIn("超时", result.text)
        self.assertEqual(result.metadata["error"], "timeout")
        self.assertTrue(proc.killed)

    async def test_ssh_missing(self):
        adapter = JarvisAdapter(_make_config())
        with patch("multinexus.adapters.jarvis.asyncio.create_subprocess_exec", side_effect=FileNotFoundError("ssh")):
            result = await adapter.call("hi")
        self.assertIn("SSH 不可用", result.text)
        self.assertEqual(result.metadata["error"], "no_ssh")


class TestJarvisHealthCheck(unittest.IsolatedAsyncioTestCase):
    async def test_online(self):
        adapter = JarvisAdapter(_make_config())
        proc = FakeProcess(stdout=b"2\n")
        with patch("multinexus.adapters.jarvis.asyncio.create_subprocess_exec", return_value=proc):
            result = await adapter.health_check()
        self.assertEqual(result["adapter"], "jarvis")
        self.assertTrue(result["available"])
        self.assertEqual(result["path"], "vivoPad6p-ubuntu")
        self.assertEqual(result["wake_processes"], 2)

    async def test_offline_no_processes(self):
        adapter = JarvisAdapter(_make_config())
        proc = FakeProcess(stdout=b"0\n")
        with patch("multinexus.adapters.jarvis.asyncio.create_subprocess_exec", return_value=proc):
            result = await adapter.health_check()
        self.assertFalse(result["available"])
        self.assertEqual(result["wake_processes"], 0)

    async def test_ssh_error(self):
        adapter = JarvisAdapter(_make_config())
        with patch("multinexus.adapters.jarvis.asyncio.create_subprocess_exec", side_effect=OSError("connection refused")):
            result = await adapter.health_check()
        self.assertFalse(result["available"])
        self.assertIn("connection refused", result["error"])


class TestJarvisSshHostConfig(unittest.IsolatedAsyncioTestCase):
    def test_custom_ssh_host(self):
        adapter = JarvisAdapter(_make_config(jarvis_ssh_host="custom-host"))
        self.assertEqual(adapter.ssh_host, "custom-host")

    def test_ssh_cmd_construction(self):
        adapter = JarvisAdapter(_make_config())
        cmd = adapter._ssh_cmd("echo hello")
        self.assertIn("ssh", cmd)
        self.assertIn("vivoPad6p-ubuntu", cmd)
        self.assertIn("echo hello", cmd)


if __name__ == "__main__":
    unittest.main()
