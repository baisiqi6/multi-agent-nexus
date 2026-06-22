import unittest

from cogs.agent_request import AgentRequestMixin
from cogs.agents import Agents
from multinexus.client import DiscordClient
from multinexus.coordinator_handoff import CoordinatorHandoffMixin
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
        self.assertEqual(chunk_message("   "), [])
        chunks = chunk_message("x" * 1901)
        self.assertEqual("".join(chunks), "x" * 1901)
        self.assertTrue(all(len(chunk) <= 1900 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
