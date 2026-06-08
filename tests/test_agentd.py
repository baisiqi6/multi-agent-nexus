"""Tests for the agentd HTTP server and client."""

import asyncio
import unittest

from multinexus.models import AgentConfig
from multinexus.protocol import (
    AgentRequest,
    AgentResponse,
    Platform,
    PlatformDestination,
    PlatformOrigin,
)


class FakeAdapter:
    """Fake adapter for testing agentd without real CLI tools."""

    def __init__(self, config):
        self.name = config.adapter
        self.timeout = config.timeout
        self._responses = {}
        self._call_count = 0

    def set_response(self, prompt_substring, text, session_id="sess1"):
        self._responses[prompt_substring] = (text, session_id)

    async def call(self, prompt, *, timeout=None, work_dir=None, on_progress=None):
        self._call_count += 1
        for key, (text, sid) in self._responses.items():
            if key in prompt:
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text=text, session_id=sid)
        from multinexus.adapters.base import AdapterResult
        return AdapterResult(text="default response", session_id="sess-default")

    async def resume(self, session_id, prompt, *, timeout=None, work_dir=None, on_progress=None):
        self._call_count += 1
        for key, (text, sid) in self._responses.items():
            if key in prompt:
                from multinexus.adapters.base import AdapterResult
                return AdapterResult(text=text, session_id=sid, resumed=True)
        from multinexus.adapters.base import AdapterResult
        return AdapterResult(text="default resumed", session_id=session_id, resumed=True)

    async def health_check(self):
        return {"adapter": self.name, "available": True}


def _make_config(**overrides):
    defaults = {
        "id": "test-agent",
        "token": "fake-token",
        "adapter": "claude",
        "context_db_path": ":memory:",
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)


class TestAgentDaemonServer(unittest.TestCase):
    """Test agentd HTTP server with fake adapter."""

    def setUp(self):
        self.config = _make_config()
        # Import here to avoid circular import issues
        from multinexus.agentd.server import AgentDaemon
        self.daemon = AgentDaemon(self.config, host="127.0.0.1", port=0)
        # Replace adapter with fake
        self.fake = FakeAdapter(self.config)
        self.daemon.adapter = self.fake

    def test_process_request_basic(self):
        """Test basic request processing without HTTP."""
        self.fake.set_response("hello", "Hello world!", session_id="s1")

        req = AgentRequest(
            request_id="r1",
            agent_id="test-agent",
            prompt="hello",
        )

        loop = asyncio.new_event_loop()
        try:
            resp = loop.run_until_complete(self.daemon._process_request(req))
        finally:
            loop.close()

        self.assertEqual(resp.request_id, "r1")
        self.assertEqual(resp.agent_id, "test-agent")
        self.assertEqual(resp.text, "Hello world!")
        self.assertTrue(resp.success)
        self.assertEqual(resp.session_id, "s1")

    def test_process_request_agent_id_mismatch(self):
        """Requests with wrong agent_id should fail."""
        req = AgentRequest(
            request_id="r2",
            agent_id="wrong-agent",
            prompt="test",
        )

        loop = asyncio.new_event_loop()
        try:
            resp = loop.run_until_complete(self.daemon._process_request(req))
        finally:
            loop.close()

        # Should still return a response (daemon processes what it gets)
        # But HTTP handler would reject with 403 before reaching _process_request
        self.assertIsNotNone(resp)

    def test_process_request_with_handoff_lines(self):
        """Response with handoff lines should be split."""
        self.fake.set_response(
            "task",
            "Done!\n[handoff] <@!123456> review this",
        )

        req = AgentRequest(
            request_id="r3",
            agent_id="test-agent",
            prompt="task",
        )

        loop = asyncio.new_event_loop()
        try:
            resp = loop.run_until_complete(self.daemon._process_request(req))
        finally:
            loop.close()

        self.assertIn("Done!", resp.text)
        self.assertEqual(len(resp.handoff_lines), 1)
        self.assertIn("[handoff]", resp.handoff_lines[0])

    def test_process_request_with_report_lines(self):
        """Response with agent-report lines should be split."""
        self.fake.set_response(
            "report",
            "Working...\n[agent-report] action=progress summary=50%",
        )

        req = AgentRequest(
            request_id="r4",
            agent_id="test-agent",
            prompt="report",
        )

        loop = asyncio.new_event_loop()
        try:
            resp = loop.run_until_complete(self.daemon._process_request(req))
        finally:
            loop.close()

        self.assertIn("Working...", resp.text)
        self.assertEqual(len(resp.report_lines), 1)
        self.assertIn("[agent-report]", resp.report_lines[0])

    def test_process_request_error_response(self):
        """Adapter errors should be reflected in response."""
        self.fake.set_response("fail", "Agent error: timeout")

        req = AgentRequest(
            request_id="r5",
            agent_id="test-agent",
            prompt="fail",
        )

        loop = asyncio.new_event_loop()
        try:
            resp = loop.run_until_complete(self.daemon._process_request(req))
        finally:
            loop.close()

        self.assertFalse(resp.success)
        self.assertIn("timeout", resp.error)

    def test_process_request_with_platform_origin(self):
        """Request with KOOK origin should work."""
        self.fake.set_response("kook", "KOOK reply")

        req = AgentRequest(
            request_id="r6",
            agent_id="test-agent",
            prompt="kook",
            origin=PlatformOrigin(
                platform=Platform.KOOK,
                channel_id="kch1",
                role_id="role1",
            ),
            destination=PlatformDestination(
                platform=Platform.KOOK,
                channel_id="kch1",
                quote_message_id="qm1",
            ),
        )

        loop = asyncio.new_event_loop()
        try:
            resp = loop.run_until_complete(self.daemon._process_request(req))
        finally:
            loop.close()

        self.assertTrue(resp.success)
        self.assertEqual(resp.text, "KOOK reply")
        self.assertEqual(resp.destination.platform, Platform.KOOK)


class TestAgentDaemonHTTPEndToEnd(unittest.TestCase):
    """Test full HTTP round-trip with fake adapter."""

    def setUp(self):
        self.config = _make_config()
        from multinexus.agentd.server import AgentDaemon
        self.daemon = AgentDaemon(self.config, host="127.0.0.1", port=0)
        self.fake = FakeAdapter(self.config)
        self.daemon.adapter = self.fake

    def test_http_round_trip(self):
        """Full HTTP request/response cycle."""
        self.fake.set_response("http test", "HTTP response")

        loop = asyncio.new_event_loop()
        try:
            port = loop.run_until_complete(self.daemon.start())
            try:
                import aiohttp
                async def _do():
                    async with aiohttp.ClientSession() as session:
                        req = AgentRequest(
                            request_id="http1",
                            agent_id="test-agent",
                            prompt="http test",
                        )
                        async with session.post(
                            f"http://127.0.0.1:{port}/request",
                            data=req.to_json(),
                        ) as resp:
                            self.assertEqual(resp.status, 200)
                            body = await resp.text()
                            agent_resp = AgentResponse.from_json(body)
                            self.assertEqual(agent_resp.request_id, "http1")
                            self.assertEqual(agent_resp.text, "HTTP response")
                            self.assertTrue(agent_resp.success)

                loop.run_until_complete(_do())
            finally:
                loop.run_until_complete(self.daemon.stop())
        finally:
            loop.close()

    def test_http_health(self):
        """Health check endpoint."""
        loop = asyncio.new_event_loop()
        try:
            port = loop.run_until_complete(self.daemon.start())
            try:
                import aiohttp
                async def _do():
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"http://127.0.0.1:{port}/health",
                        ) as resp:
                            self.assertEqual(resp.status, 200)
                            data = await resp.json()
                            self.assertEqual(data["agent_id"], "test-agent")
                            self.assertTrue(data["available"])

                loop.run_until_complete(_do())
            finally:
                loop.run_until_complete(self.daemon.stop())
        finally:
            loop.close()

    def test_http_agent_id_mismatch(self):
        """Wrong agent_id should return 403."""
        loop = asyncio.new_event_loop()
        try:
            port = loop.run_until_complete(self.daemon.start())
            try:
                import aiohttp
                async def _do():
                    async with aiohttp.ClientSession() as session:
                        req = AgentRequest(
                            request_id="bad1",
                            agent_id="wrong-agent",
                            prompt="test",
                        )
                        async with session.post(
                            f"http://127.0.0.1:{port}/request",
                            data=req.to_json(),
                        ) as resp:
                            self.assertEqual(resp.status, 403)

                loop.run_until_complete(_do())
            finally:
                loop.run_until_complete(self.daemon.stop())
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()
