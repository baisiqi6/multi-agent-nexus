import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

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
        process_kwargs = {"start_new_session": True}
        with (
            patch(
                "multinexus.adapters.jarvis.async_subprocess_kwargs",
                return_value=process_kwargs,
            ),
            patch(
                "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
                return_value=proc,
            ) as spawn,
        ):
            result = await adapter.call("hi")
        self.assertEqual(result.text, "Hello from Jarvis")
        self.assertEqual(result.metadata["engine"], "jarvis")
        self.assertEqual(spawn.call_args.kwargs["start_new_session"], True)

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
        cleanup = AsyncMock(side_effect=lambda target: target.kill())
        with (
            patch(
                "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
                return_value=proc,
            ),
            patch(
                "multinexus.adapters.jarvis.terminate_owned_process_group",
                cleanup,
            ),
        ):
            result = await adapter.call("hi")
        self.assertIn("超时", result.text)
        self.assertEqual(result.metadata["error"], "timeout")
        self.assertTrue(proc.killed)
        cleanup.assert_awaited_once_with(proc)

    async def test_cancellation(self):
        adapter = JarvisAdapter(_make_config())
        proc = FakeProcess()
        started = asyncio.Event()

        async def _hang(_input=None):
            started.set()
            await asyncio.Event().wait()

        proc.communicate = _hang
        cleanup = AsyncMock(side_effect=lambda target: target.kill())
        with (
            patch(
                "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
                return_value=proc,
            ),
            patch(
                "multinexus.adapters.jarvis.terminate_owned_process_group",
                cleanup,
            ),
        ):
            task = asyncio.create_task(adapter.call("hi"))
            await asyncio.wait_for(started.wait(), timeout=5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertTrue(proc.killed)
        cleanup.assert_awaited_once_with(proc)

    async def test_cleanup_failure_propagates_once(self):
        adapter = JarvisAdapter(_make_config(timeout=1))
        proc = FakeProcess()

        async def _hang(_input=None):
            await asyncio.sleep(100)

        proc.communicate = _hang
        cleanup = AsyncMock(side_effect=RuntimeError("cleanup failed"))
        with (
            patch(
                "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
                return_value=proc,
            ),
            patch(
                "multinexus.adapters.jarvis.terminate_owned_process_group",
                cleanup,
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
                await adapter.call("hi")

        cleanup.assert_awaited_once_with(proc)

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



class TestLocalBrainAdapter(unittest.IsolatedAsyncioTestCase):
    """Tests for LocalBrainAdapter (agentd on Pad, owned local subprocess)."""

    async def test_call_success(self):
        from multinexus.adapters.jarvis import LocalBrainAdapter

        adapter = LocalBrainAdapter(_make_config(adapter="jarvis-local"))
        proc = FakeProcess(stdout=b"Hello from local brain\n")
        process_kwargs = {"start_new_session": True}
        with (
            patch(
                "multinexus.adapters.jarvis.async_subprocess_kwargs",
                return_value=process_kwargs,
            ),
            patch(
                "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
                return_value=proc,
            ) as spawn,
        ):
            result = await adapter.call("hi")

        self.assertEqual(result.text, "Hello from local brain")
        self.assertEqual(result.metadata["engine"], "jarvis-local")
        self.assertEqual(spawn.call_args.kwargs["start_new_session"], True)
        proc.communicate.assert_awaited_once_with(b"hi")

    async def test_call_timeout(self):
        from multinexus.adapters.jarvis import LocalBrainAdapter

        adapter = LocalBrainAdapter(_make_config(adapter="jarvis-local", timeout=1))

        proc = FakeProcess()

        async def _hang(_input=None):
            await asyncio.sleep(100)

        proc.communicate = _hang
        cleanup = AsyncMock(side_effect=lambda target: target.kill())
        with (
            patch(
                "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
                return_value=proc,
            ),
            patch(
                "multinexus.adapters.jarvis.terminate_owned_process_group",
                cleanup,
            ),
        ):
            result = await adapter.call("hi")

        self.assertIn("超时", result.text)
        self.assertEqual(result.metadata["error"], "timeout")
        cleanup.assert_awaited_once_with(proc)

    async def test_call_brain_exception(self):
        from multinexus.adapters.jarvis import LocalBrainAdapter

        adapter = LocalBrainAdapter(_make_config(adapter="jarvis-local"))
        proc = FakeProcess()

        async def _boom(_input=None):
            raise RuntimeError("brain crashed")

        proc.communicate = _boom
        cleanup = AsyncMock(side_effect=lambda target: target.kill())
        with (
            patch(
                "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
                return_value=proc,
            ),
            patch(
                "multinexus.adapters.jarvis.terminate_owned_process_group",
                cleanup,
            ),
        ):
            result = await adapter.call("hi")

        self.assertIn("brain crashed", result.text)
        self.assertEqual(result.metadata["error"], "brain_fail")
        cleanup.assert_awaited_once_with(proc)

    async def test_call_cancellation_cleans_up_once(self):
        from multinexus.adapters.jarvis import LocalBrainAdapter

        adapter = LocalBrainAdapter(_make_config(adapter="jarvis-local"))
        proc = FakeProcess()
        started = asyncio.Event()

        async def _hang(_input=None):
            started.set()
            await asyncio.Event().wait()

        proc.communicate = _hang
        cleanup = AsyncMock(side_effect=lambda target: target.kill())
        with (
            patch(
                "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
                return_value=proc,
            ),
            patch(
                "multinexus.adapters.jarvis.terminate_owned_process_group",
                cleanup,
            ),
        ):
            task = asyncio.create_task(adapter.call("hi"))
            await asyncio.wait_for(started.wait(), timeout=5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        cleanup.assert_awaited_once_with(proc)

    async def test_call_cleanup_failure_propagates_once(self):
        from multinexus.adapters.jarvis import LocalBrainAdapter

        adapter = LocalBrainAdapter(_make_config(adapter="jarvis-local", timeout=1))
        proc = FakeProcess()

        async def _hang(_input=None):
            await asyncio.sleep(100)

        proc.communicate = _hang
        cleanup = AsyncMock(side_effect=RuntimeError("cleanup failed"))
        with (
            patch(
                "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
                return_value=proc,
            ),
            patch(
                "multinexus.adapters.jarvis.terminate_owned_process_group",
                cleanup,
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
                await adapter.call("hi")

        cleanup.assert_awaited_once_with(proc)

    async def test_nonzero_child_returns_brain_fail(self):
        from multinexus.adapters.jarvis import LocalBrainAdapter

        adapter = LocalBrainAdapter(_make_config(adapter="jarvis-local"))
        proc = FakeProcess(stderr=b"brain crashed\n", returncode=1)
        with patch(
            "multinexus.adapters.jarvis.asyncio.create_subprocess_exec",
            return_value=proc,
        ):
            result = await adapter.call("hi")

        self.assertIn("brain crashed", result.text)
        self.assertEqual(result.metadata["error"], "brain_fail")

    def test_build_cmd_uses_current_python_and_brain_import(self):
        import sys

        from multinexus.adapters.jarvis import LocalBrainAdapter

        adapter = LocalBrainAdapter(_make_config(adapter="jarvis-local"))
        cmd = adapter._build_cmd()
        self.assertEqual(cmd[:2], [sys.executable, "-c"])
        self.assertIn("from jarvis_pkg.brain import brain", cmd[2])

    async def test_health_check_ok(self):
        from multinexus.adapters.jarvis import LocalBrainAdapter
        adapter = LocalBrainAdapter(_make_config(adapter="jarvis-local"))
        mock_brain = MagicMock()
        adapter._brain_fn = mock_brain
        proc = FakeProcess(stdout=b"1\n")
        with patch("multinexus.adapters.jarvis.asyncio.create_subprocess_exec", return_value=proc):
            result = await adapter.health_check()
        self.assertTrue(result["available"])
        self.assertEqual(result["adapter"], "jarvis-local")
        self.assertEqual(result["bin"], "brain()")
        self.assertEqual(result["wake_processes"], 1)

    async def test_health_check_import_fail(self):
        from multinexus.adapters.jarvis import LocalBrainAdapter
        adapter = LocalBrainAdapter(_make_config(adapter="jarvis-local"))
        # Simulate import failure
        def _fail():
            raise ImportError("no jarvis_pkg")
        adapter._get_brain = _fail
        result = await adapter.health_check()
        self.assertFalse(result["available"])
        self.assertIn("import failed", result["error"])

    def test_factory_routes_jarvis_local(self):
        from multinexus.adapters.factory import make_adapter
        cfg = _make_config(adapter="jarvis-local")
        adapter = make_adapter(cfg)
        self.assertEqual(type(adapter).__name__, "LocalBrainAdapter")

if __name__ == "__main__":
    unittest.main()
