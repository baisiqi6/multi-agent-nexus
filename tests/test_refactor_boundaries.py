import asyncio
from types import SimpleNamespace
import unittest
from unittest import mock

from cogs import agents as agents_facade
from cogs.agent_request import AgentRequestMixin
from cogs.agents import Agents
from multinexus import client as client_facade
from multinexus.client import DiscordClient
from multinexus.coordinator_handoff import (
    CoordinatorHandoffMixin,
    _chunk_handoff_message,
)
from multinexus.message_chunks import chunk_message


class RefactorBoundaryTests(unittest.TestCase):
    def test_discord_client_keeps_coordinator_handoff_api(self):
        self.assertTrue(issubclass(DiscordClient, CoordinatorHandoffMixin))
        self.assertIs(
            DiscordClient._try_coordinator_handoff,
            CoordinatorHandoffMixin._try_coordinator_handoff,
        )

    def test_agents_cog_keeps_request_api(self):
        self.assertTrue(issubclass(Agents, AgentRequestMixin))
        self.assertIs(Agents.handle_agent_request, AgentRequestMixin.handle_agent_request)

    def test_message_chunk_boundary_preserves_empty_and_size_behavior(self):
        self.assertEqual(client_facade._MAX_DISCORD_MSG_LEN, 1900)
        self.assertEqual(chunk_message("   "), [])
        chunks = chunk_message("x" * 1901)
        self.assertEqual("".join(chunks), "x" * 1901)
        self.assertTrue(all(len(chunk) <= 1900 for chunk in chunks))
        with mock.patch.object(
            client_facade, "_chunk_message", return_value=["patched"]
        ) as patched:
            self.assertEqual(_chunk_handoff_message("payload"), ["patched"])
        patched.assert_called_once_with("payload")

    def test_client_keeps_handoff_import_surface_and_patch_hook(self):
        for name in (
            "CoordinatorHandoff",
            "build_agent_report",
            "build_handoff_prompt",
            "parse_coordinator_handoff",
            "parse_coordinator_lifecycle",
            "split_agent_report_lines",
        ):
            with self.subTest(name=name):
                self.assertTrue(hasattr(client_facade, name))

        dummy = SimpleNamespace(
            user=SimpleNamespace(id=123),
            agent_config=SimpleNamespace(id="agent"),
        )
        message = SimpleNamespace(content="ignored")
        with mock.patch.object(
            client_facade, "parse_coordinator_lifecycle", return_value=None
        ) as patched:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            handled = loop.run_until_complete(
                CoordinatorHandoffMixin._try_coordinator_lifecycle(dummy, message)
            )
            loop.close()
            asyncio.set_event_loop(None)
        self.assertFalse(handled)
        patched.assert_called_once_with("ignored", my_discord_user_id=123)

    def test_agents_keeps_request_import_surface_and_patch_hook(self):
        for name in (
            "AgentOfflineError",
            "AgentRateLimitError",
            "AgentTimeoutError",
            "PrivateWikiPromoteView",
            "set_correlation",
            "clear_correlation",
        ):
            with self.subTest(name=name):
                self.assertTrue(hasattr(agents_facade, name))

        class Dummy:
            MAX_HANDOFF_DEPTH = 1

            async def _send_as_agent(self, *_args, **_kwargs):
                return None

        channel = SimpleNamespace(id=456)
        with mock.patch.object(agents_facade, "set_correlation") as patched:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                AgentRequestMixin.handle_agent_request(
                    Dummy(), "researcher", "prompt", "thread", channel, 1, depth=1
                )
            )
            loop.close()
            asyncio.set_event_loop(None)
        patched.assert_called_once_with(agent="researcher", channel="456")


if __name__ == "__main__":
    unittest.main()
