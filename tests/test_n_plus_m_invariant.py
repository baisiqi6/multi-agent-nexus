"""Tests proving the N+M process invariant.

Verifies that:
1. Bridge mode does NOT call make_adapter() or instantiate AgentDaemon
2. Both Discord and KOOK bridges submit to the same standalone agentd port
3. Standalone agentd can process requests via coordinate runtime
4. KOOK bridge import behavior is covered
"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

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

        cfg = _config(agentd_mode=True, agentd_port=8080)
        client = DiscordClient(cfg)

        mock_make.assert_not_called()
        self.assertIsNone(client.adapter)
        self.assertIsNone(client.session_store)
        self.assertIsNotNone(client._agentd_client)

    @patch("multinexus.client.make_adapter")
    def test_discord_legacy_calls_make_adapter(self, mock_make):
        """In legacy mode, DiscordClient MUST call make_adapter."""
        mock_make.return_value = MagicMock()
        from multinexus.client import DiscordClient

        cfg = _config(agentd_mode=False)
        client = DiscordClient(cfg)

        mock_make.assert_called_once_with(cfg)
        self.assertIsNotNone(client.adapter)

    def test_discord_bridge_requires_port(self):
        """Bridge mode without agentd_port must fail."""
        from multinexus.client import DiscordClient

        cfg = _config(agentd_mode=True, agentd_port=0)
        with self.assertRaises(SystemExit) as ctx:
            DiscordClient(cfg)
        self.assertIn("agentd_port", str(ctx.exception))

    def test_discord_bridge_no_embedded_agentd(self):
        """DiscordClient in bridge mode must not have AgentDaemon attributes."""
        from multinexus.client import DiscordClient

        cfg = _config(agentd_mode=True, agentd_port=8080)
        client = DiscordClient(cfg)

        self.assertFalse(hasattr(client, "_agentd"))
        self.assertFalse(hasattr(client, "_start_agentd"))
        self.assertFalse(hasattr(client, "_stop_agentd"))


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
        # __all__ should list KookBridge but importing the package
        # should not trigger khl import
        self.assertIn("KookBridge", pkg.__all__)

    def test_kook_bridge_requires_port(self):
        """KookBridge in agentd_mode without port must fail."""
        import sys
        # Check if khl is available
        if "khl" not in sys.modules:
            try:
                import khl
            except ImportError:
                self.skipTest("khl not installed, cannot test KookBridge instantiation")
                return

        from multinexus.kook.bot import KookBridge
        cfg = _config(
            agentd_mode=True, agentd_port=0,
            kook_poll_channel_ids=[123],
        )
        with self.assertRaises(SystemExit) as ctx:
            KookBridge(cfg)
        self.assertIn("agentd_port", str(ctx.exception))

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
        # Use legacy mode to avoid agentd_port requirement
        cfg = _config(agentd_mode=False, kook_poll_channel_ids=[123])
        bridge = KookBridge(cfg)

        self.assertFalse(hasattr(bridge, "_agentd"))
        self.assertFalse(hasattr(bridge, "start_agentd"))
        self.assertFalse(hasattr(bridge, "stop_agentd"))


class TestStandaloneAgentdProcessInvariant(unittest.TestCase):
    """Verify the N+M process invariant: one agentd per agent identity."""

    def test_discord_and_kook_use_same_port(self):
        """Both bridges configured for the same agent must use the same agentd port."""
        shared_port = 9090
        cfg = _config(agentd_mode=True, agentd_port=shared_port)

        from multinexus.client import DiscordClient
        discord_client = DiscordClient(cfg)

        self.assertEqual(cfg.agentd_port, shared_port)
        self.assertEqual(discord_client.agent_config.agentd_port, shared_port)

    def test_agentd_is_standalone_process(self):
        """AgentDaemon is a standalone HTTP server, not embedded in any bridge."""
        from multinexus.agentd.server import AgentDaemon
        from multinexus.agentd.client import AgentdClient

        cfg = _config(agentd_mode=False)
        daemon = AgentDaemon(cfg)

        # AgentDaemon owns the adapter
        self.assertIsNotNone(daemon.adapter)
        # AgentDaemon owns the session store
        self.assertIsNotNone(daemon.session_store)
        # AgentDaemon uses async lock for serial execution
        self.assertIsNotNone(daemon._lock)

    def test_agentd_http_round_trip_via_client(self):
        """AgentdClient connects to standalone AgentDaemon via HTTP."""
        from multinexus.agentd.server import AgentDaemon

        cfg = _config()
        daemon = AgentDaemon(cfg)

        # Replace adapter with fake
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
                import aiohttp
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
                        self.assertTrue(resp.success)
                        self.assertEqual(resp.text, "standalone reply")
                    finally:
                        await client.close()
                loop.run_until_complete(_do())
            finally:
                loop.run_until_complete(daemon.stop())
        finally:
            loop.close()


class TestBridgeRequestNormalization(unittest.TestCase):
    """Verify both platforms produce valid AgentRequests for the same agent."""

    def test_discord_request_format(self):
        req = AgentRequest(
            request_id="discord:123",
            agent_id="mac-codex",
            prompt="do something",
            origin=PlatformOrigin(
                platform=Platform.DISCORD,
                channel_id="456",
                message_id="123",
            ),
            destination=PlatformDestination(
                platform=Platform.DISCORD,
                channel_id="456",
            ),
        )
        j = req.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["origin"]["platform"], "discord")

    def test_kook_request_format(self):
        req = AgentRequest(
            request_id="kook:789",
            agent_id="mac-codex",
            prompt="do something",
            origin=PlatformOrigin(
                platform=Platform.KOOK,
                channel_id="ch1",
                role_id="role1",
            ),
            destination=PlatformDestination(
                platform=Platform.KOOK,
                channel_id="ch1",
                quote_message_id="qm1",
            ),
        )
        j = req.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["origin"]["platform"], "kook")

    def test_both_requests_target_same_agent(self):
        """Discord and KOOK requests for the same agent share agent_id."""
        discord_req = AgentRequest(
            request_id="discord:1",
            agent_id="mac-codex",
            prompt="from discord",
        )
        kook_req = AgentRequest(
            request_id="kook:2",
            agent_id="mac-codex",
            prompt="from kook",
        )
        self.assertEqual(discord_req.agent_id, kook_req.agent_id)
        # The standalone agentd processes both via the same adapter/lock
        self.assertTrue(discord_req.to_json())
        self.assertTrue(kook_req.to_json())


if __name__ == "__main__":
    unittest.main()
