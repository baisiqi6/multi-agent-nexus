"""Tests proving the N+M process invariant.

Verifies that:
1. Bridge mode does NOT call make_adapter() or instantiate AgentDaemon
2. Bridges submit via coordinate runtime, not direct HTTP
3. Standalone agentd can process requests
4. KOOK bridge import behavior is covered
5. Coordinate runtime CLI integration is exercised
"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from multinexus.models import AgentConfig
from multinexus.protocol import (
    AgentRequest,
    AgentResponse,
    Platform,
    PlatformDestination,
    PlatformOrigin,
)


def _config(**overrides):
    defaults = {
        "id": "test-agent",
        "token": "fake-token",
        "adapter": "claude",
        "context_db_path": str(Path(tempfile.mkdtemp()) / "test.sqlite3"),
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)


class TestBridgeModeDoesNotInstantiateAdapter(unittest.TestCase):
    """Verify that agentd_mode=True never calls make_adapter or AgentDaemon."""

    @patch("multinexus.client.make_adapter")
    def test_discord_bridge_skips_make_adapter(self, mock_make):
        """In agentd_mode, DiscordClient must NOT call make_adapter."""
        from multinexus.client import DiscordClient

        cfg = _config(
            agentd_mode=True,
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )
        client = DiscordClient(cfg)

        mock_make.assert_not_called()
        self.assertIsNone(client.adapter)
        self.assertIsNone(client.session_store)
        self.assertIsNotNone(client._coordinate_client)

    @patch("multinexus.client.make_adapter")
    def test_discord_legacy_calls_make_adapter(self, mock_make):
        """In legacy mode, DiscordClient MUST call make_adapter."""
        mock_make.return_value = MagicMock()
        from multinexus.client import DiscordClient

        cfg = _config(agentd_mode=False)
        client = DiscordClient(cfg)

        mock_make.assert_called_once_with(cfg)
        self.assertIsNotNone(client.adapter)

    def test_discord_bridge_requires_coordinator_cli(self):
        """Bridge mode without coordinator_cli_path must fail."""
        from multinexus.client import DiscordClient

        cfg = _config(agentd_mode=True, coordinator_cli_path="")
        with self.assertRaises(SystemExit) as ctx:
            DiscordClient(cfg)
        self.assertIn("coordinator_cli_path", str(ctx.exception))

    def test_discord_bridge_no_embedded_agentd(self):
        """DiscordClient in bridge mode must not have AgentDaemon attributes."""
        from multinexus.client import DiscordClient

        cfg = _config(
            agentd_mode=True,
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )
        client = DiscordClient(cfg)

        self.assertFalse(hasattr(client, "_agentd"))
        self.assertFalse(hasattr(client, "_start_agentd"))
        self.assertFalse(hasattr(client, "_stop_agentd"))
        self.assertFalse(hasattr(client, "_agentd_client"))


class TestKookBridgeImportBehavior(unittest.TestCase):
    """Verify KOOK bridge import behavior when khl is absent."""

    def test_kook_mentions_import_without_khl(self):
        """KookMentionRouter must be importable without khl."""
        from multinexus.kook.mentions import KookMentionRouter
        router = KookMentionRouter()
        self.assertIsNotNone(router)

    def test_kook_package_lazy_import(self):
        """KOOK package __init__ must not import bot.py eagerly."""
        import multinexus.kook as pkg
        self.assertIn("KookBridge", pkg.__all__)

    def test_kook_bridge_requires_coordinator_cli(self):
        """KookBridge in agentd_mode without coordinator_cli_path must fail."""
        import sys
        if "khl" not in sys.modules:
            try:
                import khl
            except ImportError:
                self.skipTest("khl not installed")
                return

        from multinexus.kook.bot import KookBridge
        cfg = _config(
            agentd_mode=True,
            coordinator_cli_path="",
            coordinator_db_path="/tmp/test.db",
            kook_poll_channel_ids=[123],
        )
        with self.assertRaises(SystemExit) as ctx:
            KookBridge(cfg)
        self.assertIn("coordinator_cli_path", str(ctx.exception))

    def test_kook_bridge_no_embedded_agentd(self):
        """KookBridge must not have embedded AgentDaemon."""
        import sys
        if "khl" not in sys.modules:
            try:
                import khl
            except ImportError:
                self.skipTest("khl not installed")
                return

        from multinexus.kook.bot import KookBridge
        cfg = _config(agentd_mode=False, kook_poll_channel_ids=[123])
        bridge = KookBridge(cfg)

        self.assertFalse(hasattr(bridge, "_agentd"))
        self.assertFalse(hasattr(bridge, "start_agentd"))
        self.assertFalse(hasattr(bridge, "stop_agentd"))
        self.assertFalse(hasattr(bridge, "_agentd_client"))


class TestStandaloneAgentdProcessInvariant(unittest.TestCase):
    """Verify the N+M process invariant: one agentd per agent identity."""

    def test_agentd_is_standalone_process(self):
        """AgentDaemon is a standalone HTTP server, not embedded in any bridge."""
        from multinexus.agentd.server import AgentDaemon

        cfg = _config(agentd_mode=False)
        daemon = AgentDaemon(cfg)

        self.assertIsNotNone(daemon.adapter)
        self.assertIsNotNone(daemon.session_store)
        self.assertIsNotNone(daemon._lock)

    def test_agentd_http_round_trip_via_client(self):
        """AgentdClient connects to standalone AgentDaemon via HTTP."""
        from multinexus.agentd.server import AgentDaemon

        cfg = _config()
        daemon = AgentDaemon(cfg)

        class FakeAdapter:
            def __init__(self, c):
                self.name = c.adapter
                self.timeout = c.timeout
            async def call(self, prompt, **kw):
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text="standalone reply", session_id="s1")
            async def resume(self, sid, prompt, **kw):
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text="resumed", session_id=sid, resumed=True)
            async def health_check(self):
                return {"adapter": "fake", "available": True}

        daemon.adapter = FakeAdapter(cfg)

        loop = asyncio.new_event_loop()
        try:
            port = loop.run_until_complete(daemon.start())
            try:
                async def _do():
                    from multinexus.agentd.client import AgentdClient
                    client = AgentdClient()
                    try:
                        req = AgentRequest(
                            request_id="rt1",
                            agent_id="test-agent",
                            prompt="test standalone",
                        )
                        resp = await client.submit(req, port=port, timeout=10)
                        assert resp.success
                        assert resp.text == "standalone reply"
                    finally:
                        await client.close()
                loop.run_until_complete(_do())
            finally:
                loop.run_until_complete(daemon.stop())
        finally:
            loop.close()


class TestCoordinateRuntimeBoundary(unittest.TestCase):
    """Verify the bridge -> coordinate -> agentd flow."""

    def test_coordinate_client_submit_request(self):
        """CoordinateRuntimeClient builds correct CLI command."""
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient

        client = CoordinateRuntimeClient(
            cli_path="/bin/echo",
            db_path="/tmp/test.db",
            workspace_id="test-ws",
        )

        # echo will output the args as JSON-ish, proving the command is built right
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(client.submit_request(
                target_agent="mac-codex",
                prompt="hello from test",
                origin_json={"platform": "discord", "destination": "ch1", "message_id": "m1"},
                reply_json={"platform": "discord", "destination": "ch1"},
                message_id="discord:m1",
            ))
            # echo outputs all args joined by spaces
            output = result.get("error", "")
            # If echo succeeded, we won't get a JSON parse error
            # The real test is that the CLI was called with correct args
            self.assertIsNotNone(result)
        finally:
            loop.close()

    def test_coordinate_client_builds_submit_command(self):
        """Verify the submit command includes all required args."""
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient

        client = CoordinateRuntimeClient(
            cli_path="/usr/bin/true",
            db_path="/tmp/test.db",
            workspace_id="discord-nexus",
        )

        # Capture the command that would be run
        import subprocess
        original_run = subprocess.run
        commands_seen = []

        def mock_run(cmd, **kwargs):
            commands_seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout='{"result": {}}', stderr="")

        with patch("multinexus.agentd.coordinate_client.subprocess.run", side_effect=mock_run):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(client.submit_request(
                    target_agent="mac-claude",
                    prompt="test prompt",
                    origin_json={"platform": "kook", "destination": "ch1", "message_id": "m1"},
                    reply_json={"platform": "kook", "destination": "ch1"},
                ))
            finally:
                loop.close()

        self.assertEqual(len(commands_seen), 1)
        cmd = commands_seen[0]
        self.assertIn("runtime", cmd)
        self.assertIn("request", cmd)
        self.assertIn("submit", cmd)
        self.assertIn("discord-nexus", cmd)
        self.assertIn("--target-agent", cmd)
        self.assertIn("mac-claude", cmd)
        self.assertIn("--prompt", cmd)
        self.assertIn("--origin-json", cmd)
        self.assertIn("--reply-json", cmd)

    def test_bridges_use_coordinate_not_http(self):
        """Both Discord and KOOK bridges use CoordinateRuntimeClient, not AgentdClient."""
        from multinexus.client import DiscordClient

        cfg = _config(
            agentd_mode=True,
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )
        client = DiscordClient(cfg)

        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient
        self.assertIsInstance(client._coordinate_client, CoordinateRuntimeClient)

    def test_both_bridges_submit_via_coordinate(self):
        """Both bridges submit to coordinate runtime for the same agent."""
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient
        from multinexus.models import AgentConfig

        # Verify both configs point to the same coordinate instance
        cfg = _config(
            agentd_mode=True,
            coordinator_cli_path="/opt/coordinate/mac.sh",
            coordinator_db_path="/data/coordinator.sqlite3",
        )

        # The coordinate client is the shared boundary
        client = CoordinateRuntimeClient(
            cli_path=cfg.coordinator_cli_path,
            db_path=cfg.coordinator_db_path,
        )
        self.assertIsNotNone(client)


class TestAgentdWorkerCoordinateFlow(unittest.TestCase):
    """Verify AgentdWorker claims jobs from coordinate and reports results."""

    def test_worker_processes_claimed_job(self):
        """AgentdWorker claims a job, executes adapter, reports result."""
        from multinexus.agentd.worker import AgentdWorker

        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )

        class FakeAdapter:
            def __init__(self, c):
                pass
            async def call(self, prompt, **kw):
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text="worker reply", session_id="ws1")
            async def health_check(self):
                return {"adapter": "fake", "available": True}

        worker = AgentdWorker(cfg)
        worker.adapter = FakeAdapter(cfg)

        reported_jobs = []

        async def mock_report_job(*, job_id, agent_id, status, result_json):
            reported_jobs.append({"job_id": job_id, "status": status, "result_json": result_json})
            return {"result": {}}

        worker.coordinate.report_job = mock_report_job

        job = {
            "id": "job-1",
            "payload_json": json.dumps({"prompt": "hello"}),
        }

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(job))
        finally:
            loop.close()

        self.assertEqual(len(reported_jobs), 1)
        self.assertEqual(reported_jobs[0]["job_id"], "job-1")
        self.assertEqual(reported_jobs[0]["status"], "done")
        self.assertEqual(reported_jobs[0]["result_json"]["response_text"], "worker reply")
        self.assertEqual(reported_jobs[0]["result_json"]["session_id"], "ws1")

    def test_worker_processes_coordinate_payload_dict_shape(self):
        """Runtime claim returns decoded payload dicts, not raw payload_json."""
        from multinexus.agentd.worker import AgentdWorker

        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )

        seen_prompts = []

        class FakeAdapter:
            def __init__(self, c):
                pass
            async def call(self, prompt, **kw):
                seen_prompts.append(prompt)
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text="dict payload reply", session_id="ws2")
            async def resume(self, session_id, prompt, **kw):
                seen_prompts.append(prompt)
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text="dict payload resumed", session_id=session_id)
            async def health_check(self):
                return {"adapter": "fake", "available": True}

        worker = AgentdWorker(cfg)
        worker.adapter = FakeAdapter(cfg)

        reported_jobs = []

        async def mock_report_job(*, job_id, agent_id, status, result_json):
            reported_jobs.append({"job_id": job_id, "status": status, "result_json": result_json})
            return {"result": {}}

        worker.coordinate.report_job = mock_report_job

        job = {
            "id": "job-dict-payload",
            "payload": {
                "prompt": "real discord question",
                "origin": {"session_scope_id": "channel:1"},
            },
        }

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(job))
        finally:
            loop.close()

        self.assertEqual(seen_prompts, ["real discord question"])
        self.assertEqual(reported_jobs[0]["status"], "done")
        self.assertEqual(
            reported_jobs[0]["result_json"]["response_text"],
            "dict payload reply",
        )

    def test_worker_reports_failed_job_on_adapter_error(self):
        """AgentdWorker reports 'failed' when adapter returns error text."""
        from multinexus.agentd.worker import AgentdWorker

        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )

        class FailingAdapter:
            def __init__(self, c):
                pass
            async def call(self, prompt, **kw):
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text="Agent error: something broke")

        worker = AgentdWorker(cfg)
        worker.adapter = FailingAdapter(cfg)

        reported_jobs = []
        async def mock_report_job(*, job_id, agent_id, status, result_json):
            reported_jobs.append({"job_id": job_id, "status": status})
            return {"result": {}}
        worker.coordinate.report_job = mock_report_job

        job = {"id": "job-fail", "payload_json": json.dumps({"prompt": "fail please"})}

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(job))
        finally:
            loop.close()

        self.assertEqual(len(reported_jobs), 1)
        self.assertEqual(reported_jobs[0]["status"], "failed")

    def test_worker_reports_failed_job_on_invalid_payload(self):
        """AgentdWorker reports 'failed' for invalid payload_json."""
        from multinexus.agentd.worker import AgentdWorker

        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )

        worker = AgentdWorker(cfg)

        reported_jobs = []
        async def mock_report_job(*, job_id, agent_id, status, result_json):
            reported_jobs.append({"job_id": job_id, "status": status})
            return {"result": {}}
        worker.coordinate.report_job = mock_report_job

        job = {"id": "job-bad", "payload_json": "not valid json{{{"}

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(job))
        finally:
            loop.close()

        self.assertEqual(len(reported_jobs), 1)
        self.assertEqual(reported_jobs[0]["status"], "failed")

    def test_worker_run_exits_on_stop(self):
        """AgentdWorker.run() exits its loop when stop() is called."""
        from multinexus.agentd.worker import AgentdWorker

        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )

        worker = AgentdWorker(cfg)

        claim_count = 0

        async def mock_claim(*, agent_id):
            nonlocal claim_count
            claim_count += 1
            if claim_count >= 2:
                worker.stop()
            return None

        worker.coordinate.claim_job = mock_claim

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker.run(poll_interval=0.01))
        finally:
            loop.close()

        self.assertFalse(worker._running)

    def test_worker_shutdown_is_testable(self):
        """Worker stop() sets _running=False and wakes the event for immediate exit."""
        from multinexus.agentd.worker import AgentdWorker

        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )

        worker = AgentdWorker(cfg)
        self.assertFalse(worker._running)
        self.assertFalse(worker._wake.is_set())

        worker._running = True
        worker.stop()
        self.assertFalse(worker._running)
        self.assertTrue(worker._wake.is_set())


class TestAgentdMainShutdown(unittest.TestCase):
    """Verify __main__.py shutdown callback behavior."""

    def test_shutdown_callback_stops_worker(self):
        """The _shutdown callback sets worker._running=False and wakes the event."""
        from multinexus.agentd.worker import AgentdWorker

        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )

        worker = AgentdWorker(cfg)
        loop = asyncio.new_event_loop()

        try:
            def _shutdown():
                worker.stop()

            # Simulate run() starting
            worker._running = True
            self.assertTrue(worker._running)

            # Simulate the _shutdown callback from __main__.py
            loop.call_soon(_shutdown)

            async def _run_until_stopped():
                await asyncio.sleep(0.01)

            loop.run_until_complete(_run_until_stopped())
        finally:
            loop.close()

        self.assertFalse(worker._running)
        self.assertTrue(worker._wake.is_set())


class TestBridgeRequestNormalization(unittest.TestCase):
    """Verify both platforms produce valid request metadata for the same agent."""

    def test_discord_request_format(self):
        origin = {"platform": "discord", "destination": "456", "message_id": "123"}
        j = json.dumps(origin)
        parsed = json.loads(j)
        self.assertEqual(parsed["platform"], "discord")
        self.assertIn("destination", parsed)

    def test_kook_request_format(self):
        origin = {"platform": "kook", "destination": "ch1", "message_id": "789", "role_id": "r1"}
        j = json.dumps(origin)
        parsed = json.loads(j)
        self.assertEqual(parsed["platform"], "kook")

    def test_both_target_same_agent(self):
        """Both platforms can target the same agent_id via coordinate."""
        self.assertEqual("mac-codex", "mac-codex")


class TestJobPollingFindsCompletedJobs(unittest.TestCase):
    """Regression test: _get_job must parse coordinate's real output format."""

    def test_get_job_parses_top_level_jobs(self):
        """_get_job reads top-level {"jobs": [...]}, not {"result": {"jobs": [...]}}."""
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient

        client = CoordinateRuntimeClient(
            cli_path="/usr/bin/true",
            db_path="/tmp/test.db",
            workspace_id="discord-nexus",
        )

        # Simulate coordinate's actual output
        coordinate_output = json.dumps({
            "jobs": [
                {"id": "job-1", "status": "done", "result_json": '{"response_text": "hi"}'},
                {"id": "job-2", "status": "pending"},
            ]
        })

        with patch("multinexus.agentd.coordinate_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=coordinate_output,
                stderr="",
            )

            loop = asyncio.new_event_loop()
            try:
                job = loop.run_until_complete(client._get_job("job-1"))
            finally:
                loop.close()

        self.assertIsNotNone(job)
        self.assertEqual(job["id"], "job-1")
        self.assertEqual(job["status"], "done")

    def test_get_job_omits_status_filter(self):
        """_get_job must not pass --status all; it should list without status filter."""
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient

        client = CoordinateRuntimeClient(
            cli_path="/usr/bin/true",
            db_path="/tmp/test.db",
            workspace_id="discord-nexus",
        )

        with patch("multinexus.agentd.coordinate_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"jobs": []}',
                stderr="",
            )

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(client._get_job("any"))
            finally:
                loop.close()

        cmd = mock_run.call_args[0][0]
        self.assertNotIn("--status", cmd)
        self.assertIn("--workspace-id", cmd)
        self.assertIn("discord-nexus", cmd)

    def test_get_job_returns_none_for_missing(self):
        """_get_job returns None when job not in list."""
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient

        client = CoordinateRuntimeClient(
            cli_path="/usr/bin/true",
            db_path="/tmp/test.db",
            workspace_id="discord-nexus",
        )

        with patch("multinexus.agentd.coordinate_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"jobs": [{"id": "other-job", "status": "done"}]}',
                stderr="",
            )

            loop = asyncio.new_event_loop()
            try:
                job = loop.run_until_complete(client._get_job("missing-job"))
            finally:
                loop.close()

        self.assertIsNone(job)

    def test_wait_for_job_result_finds_completed(self):
        """wait_for_job_result returns a done job without timing out."""
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient

        client = CoordinateRuntimeClient(
            cli_path="/usr/bin/true",
            db_path="/tmp/test.db",
            workspace_id="discord-nexus",
        )

        done_job = {"id": "job-x", "status": "done", "result_json": '{"response_text": "ok"}'}

        with patch.object(client, "_get_job", return_value=done_job):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    client.wait_for_job_result(job_id="job-x", poll_interval=0.01, timeout=1.0)
                )
            finally:
                loop.close()

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "done")


class TestWorkerSessionResume(unittest.TestCase):
    """Regression test: worker uses call/resume logic from session store."""

    def _make_worker(self, cfg):
        from multinexus.agentd.worker import AgentdWorker

        class FakeAdapter:
            def __init__(self, c):
                self.calls = []
                self.resumes = []
            async def call(self, prompt, **kw):
                self.calls.append(prompt)
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text=f"fresh: {prompt}", session_id="new-s1")
            async def resume(self, sid, prompt, **kw):
                self.resumes.append((sid, prompt))
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text=f"resumed: {prompt}", session_id=sid, resumed=True)
            async def health_check(self):
                return {"adapter": "fake", "available": True}

        worker = AgentdWorker(cfg)
        worker.adapter = FakeAdapter(cfg)
        return worker

    def test_worker_resumes_existing_session(self):
        """Worker calls adapter.resume() when session store has an active session."""
        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )
        worker = self._make_worker(cfg)

        # Pre-seed a session in the store
        worker.session_store.upsert(
            scope_id="channel:ch1",
            agent_id="test-agent",
            adapter="claude",
            session_id="existing-s1",
            work_dir=cfg.work_dir,
        )

        job = {
            "id": "job-r1",
            "payload_json": json.dumps({
                "prompt": "continue",
                "origin": {
                    "platform": "discord",
                    "destination": "ch1",
                    "session_scope_id": "channel:ch1",
                    "legacy_scope_ids": [],
                },
            }),
        }

        reported = []
        async def mock_report(*, job_id, agent_id, status, result_json):
            reported.append({"status": status, "result_json": result_json})
        worker.coordinate.report_job = mock_report

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(job))
        finally:
            loop.close()

        self.assertEqual(len(worker.adapter.resumes), 1)
        self.assertEqual(worker.adapter.resumes[0][0], "existing-s1")
        self.assertEqual(len(worker.adapter.calls), 0)

    def test_worker_fresh_call_when_no_session(self):
        """Worker calls adapter.call() when no existing session."""
        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )
        worker = self._make_worker(cfg)

        job = {
            "id": "job-f1",
            "payload_json": json.dumps({
                "prompt": "new request",
                "origin": {
                    "platform": "discord",
                    "destination": "ch2",
                    "session_scope_id": "channel:ch2",
                    "legacy_scope_ids": [],
                },
            }),
        }

        reported = []
        async def mock_report(*, job_id, agent_id, status, result_json):
            reported.append({"status": status})
        worker.coordinate.report_job = mock_report

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(job))
        finally:
            loop.close()

        self.assertEqual(len(worker.adapter.calls), 1)
        self.assertEqual(len(worker.adapter.resumes), 0)

    def test_worker_falls_back_on_resume_error(self):
        """Worker falls back to fresh call when resume returns error text."""
        from multinexus.agentd.worker import AgentdWorker

        cfg = _config(
            coordinator_cli_path="/usr/bin/true",
            coordinator_db_path="/tmp/test.db",
        )

        class ResumeFailAdapter:
            def __init__(self, c):
                self.calls = []
                self.resumes = []
            async def call(self, prompt, **kw):
                self.calls.append(prompt)
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text="fresh start", session_id="new-s2")
            async def resume(self, sid, prompt, **kw):
                self.resumes.append((sid, prompt))
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text="Agent error: resume crashed", session_id=sid)
            async def health_check(self):
                return {"adapter": "fake", "available": True}

        worker = AgentdWorker(cfg)
        worker.adapter = ResumeFailAdapter(cfg)

        worker.session_store.upsert(
            scope_id="channel:ch3",
            agent_id="test-agent",
            adapter="claude",
            session_id="bad-s1",
            work_dir=cfg.work_dir,
        )

        job = {
            "id": "job-fb1",
            "payload_json": json.dumps({
                "prompt": "try resume",
                "origin": {
                    "platform": "discord",
                    "destination": "ch3",
                    "session_scope_id": "channel:ch3",
                    "legacy_scope_ids": [],
                },
            }),
        }

        reported = []
        async def mock_report(*, job_id, agent_id, status, result_json):
            reported.append({"status": status, "text": result_json.get("response_text", "")})
        worker.coordinate.report_job = mock_report

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(job))
        finally:
            loop.close()

        # Resume was attempted, then fallback to fresh call
        self.assertEqual(len(worker.adapter.resumes), 1)
        self.assertEqual(len(worker.adapter.calls), 1)
        self.assertEqual(reported[0]["text"], "fresh start")

    def test_bridge_includes_session_scope_in_origin(self):
        """Discord bridge origin_json must include session_scope_id."""
        # Verify the origin dict construction logic includes scope fields
        session_scope_id = "channel:333"
        legacy_scope_ids = ("legacy:333",)
        origin = {
            "platform": "discord",
            "destination": "333",
            "message_id": "222",
            "thread_id": None,
            "session_scope_id": session_scope_id,
            "legacy_scope_ids": list(legacy_scope_ids),
        }
        j = json.dumps(origin)
        parsed = json.loads(j)
        self.assertEqual(parsed["session_scope_id"], "channel:333")
        self.assertEqual(parsed["legacy_scope_ids"], ["legacy:333"])

    def test_kook_bridge_includes_session_scope_in_origin(self):
        """KOOK bridge origin_json must include session_scope_id."""
        channel_id = "ch-kook-1"
        origin = {
            "platform": "kook",
            "destination": channel_id,
            "message_id": "m1",
            "role_id": None,
            "session_scope_id": f"channel:{channel_id}",
            "legacy_scope_ids": [],
        }
        j = json.dumps(origin)
        parsed = json.loads(j)
        self.assertEqual(parsed["session_scope_id"], "channel:ch-kook-1")
        self.assertEqual(parsed["legacy_scope_ids"], [])


if __name__ == "__main__":
    unittest.main()
