"""Runtime tests for DiscordClient._try_coordinator_handoff.

Tests the full handoff auto-accept flow: accept failure (blocker report),
accept success (with/without bootstrap), and adapter invocation.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from discord_nexus.adapters.base import AdapterResult
from discord_nexus.models import AgentConfig, KnownAgentMention


def _make_config(**overrides):
    defaults = dict(
        id="mac-claude",
        token="fake-token",
        adapter="claude",
        display_name="Claude",
        known_agents=[
            KnownAgentMention(
                id="mac-claude", primary_name="Claude",
                kind="managed", discord_user_id=111,
            ),
        ],
        work_dir="/tmp/test",
        coordinator_bot_id=999,
        coordinator_cli_path="/fake/mac.sh",
        coordinator_db_path="/fake/db.sqlite3",
        coordinator_workspace_path="/fake/workspace",
    )
    defaults.update(overrides)
    return AgentConfig(**defaults)


def _make_handoff_message(content=None, author_id=999, channel_id=500):
    """Build a mock Discord message that looks like a coordinator handoff."""
    if content is None:
        content = (
            "[handoff] <@111> workspace_id=discord-nexus "
            "task_id=phase-5.1 action=assignment.accept "
            "bootstrap=docs/project-harness/tasks/phase-5.1/worker-bootstrap.md"
        )
    msg = MagicMock(spec=discord.Message)
    msg.content = content
    msg.author.id = author_id
    msg.author.bot = True
    msg.channel = MagicMock(spec=discord.TextChannel)
    msg.channel.id = channel_id
    msg.channel.send = AsyncMock()
    placeholder = MagicMock()
    placeholder.edit = AsyncMock()
    msg.channel.send.return_value = placeholder
    return msg


def _make_runtime_client(config=None):
    """Create a DiscordClient-like object with all handoff dependencies mocked."""
    from discord_nexus.client import DiscordClient

    config = config or _make_config()

    with patch.object(DiscordClient, "__init__", lambda self, *a, **kw: None):
        instance = DiscordClient.__new__(DiscordClient)

    instance.agent_config = config
    instance.adapter = MagicMock()
    instance.adapter.call = AsyncMock(
        return_value=AdapterResult(text="ok", session_id=None)
    )
    # discord.Client.user reads from _connection.user
    mock_user = MagicMock()
    mock_user.id = 111
    instance._connection = MagicMock()
    instance._connection.user = mock_user
    instance._bot_user_id_map = {}
    instance.mention_router = MagicMock()
    instance.mention_router.resolve_handoff_mentions = lambda t: t
    instance.context_store = MagicMock()
    instance.session_store = MagicMock()

    return instance


class TestCoordinatorHandoffAcceptFailure(unittest.TestCase):
    """When assignment accept fails, a blocker report is sent and adapter is NOT called."""

    def test_sends_blocker_report_on_accept_failure(self):
        config = _make_config()
        msg = _make_handoff_message()
        instance = _make_runtime_client(config)

        with (
            patch(
                "discord_nexus.client.execute_assignment_accept",
                return_value=(False, "lease conflict"),
            ),
            patch("discord_nexus.client.read_bootstrap", return_value=None),
        ):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    instance._try_coordinator_handoff(msg)
                )
            finally:
                loop.close()

        self.assertTrue(result, "Should return True (handled)")

        sends = msg.channel.send.call_args_list
        self.assertTrue(len(sends) >= 1, "Should have sent at least one message")
        first_send = sends[0]
        sent_text = first_send[0][0]
        self.assertIn("[agent-report]", sent_text)
        self.assertIn("action=blocker", sent_text)
        self.assertIn("workspace_id=discord-nexus", sent_text)
        self.assertIn("task_id=phase-5.1", sent_text)
        self.assertIn("lease conflict", sent_text)

        # Adapter must NOT have been called
        instance.adapter.call.assert_not_called()

    def test_blocker_report_uses_allowed_mentions_none(self):
        config = _make_config()
        msg = _make_handoff_message()
        instance = _make_runtime_client(config)

        with (
            patch(
                "discord_nexus.client.execute_assignment_accept",
                return_value=(False, "error"),
            ),
            patch("discord_nexus.client.read_bootstrap", return_value=None),
        ):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    instance._try_coordinator_handoff(msg)
                )
            finally:
                loop.close()

        sends = msg.channel.send.call_args_list
        self.assertTrue(len(sends) >= 1)
        first_send = sends[0]
        allowed = first_send[1].get("allowed_mentions")
        self.assertIsNotNone(allowed, "allowed_mentions must be set")
        self.assertIsInstance(allowed, discord.AllowedMentions)
        self.assertFalse(allowed.everyone)
        self.assertFalse(allowed.users)
        self.assertFalse(allowed.roles)


class TestCoordinatorHandoffAcceptSuccess(unittest.TestCase):
    """When accept succeeds, accept report is sent and adapter is called with bootstrap prompt."""

    def test_sends_accept_report_and_calls_adapter(self):
        config = _make_config()
        msg = _make_handoff_message()
        instance = _make_runtime_client(config)
        bootstrap_content = "# Worker Bootstrap\nStep 1: Read the plan."

        with (
            patch(
                "discord_nexus.client.execute_assignment_accept",
                return_value=(True, "accepted"),
            ),
            patch(
                "discord_nexus.client.read_bootstrap",
                return_value=bootstrap_content,
            ),
        ):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    instance._try_coordinator_handoff(msg)
                )
            finally:
                loop.close()

        self.assertTrue(result)

        # Verify adapter was called
        instance.adapter.call.assert_called_once()
        prompt = instance.adapter.call.call_args[0][0]

        # Prompt must contain bootstrap content
        self.assertIn("Worker Bootstrap", prompt)
        self.assertIn("Step 1: Read the plan.", prompt)
        # Prompt must contain handoff context
        self.assertIn("phase-5.1", prompt)
        self.assertIn("discord-nexus", prompt)

        # Verify accept report was sent
        sends = msg.channel.send.call_args_list
        accept_send = None
        for s in sends:
            text = s[0][0]
            if "[agent-report]" in text and "action=accept" in text:
                accept_send = s
                break
        self.assertIsNotNone(accept_send, "Should have sent an accept report")
        accept_text = accept_send[0][0]
        self.assertIn("workspace_id=discord-nexus", accept_text)
        self.assertIn("task_id=phase-5.1", accept_text)

    def test_accept_report_uses_allowed_mentions_none(self):
        config = _make_config()
        msg = _make_handoff_message()
        instance = _make_runtime_client(config)

        with (
            patch(
                "discord_nexus.client.execute_assignment_accept",
                return_value=(True, "accepted"),
            ),
            patch("discord_nexus.client.read_bootstrap", return_value="bootstrap"),
        ):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    instance._try_coordinator_handoff(msg)
                )
            finally:
                loop.close()

        sends = msg.channel.send.call_args_list
        for s in sends:
            text = s[0][0]
            if "[agent-report]" in text and "action=accept" in text:
                allowed = s[1].get("allowed_mentions")
                self.assertIsNotNone(allowed, "allowed_mentions must be set")
                self.assertIsInstance(allowed, discord.AllowedMentions)
                self.assertFalse(allowed.everyone)
                self.assertFalse(allowed.users)
                self.assertFalse(allowed.roles)
                return
        self.fail("No accept report found")


class TestCoordinatorHandoffBootstrapMissing(unittest.TestCase):
    """When bootstrap is missing, adapter is still called with a prompt noting bootstrap is missing."""

    def test_calls_adapter_with_bootstrap_missing_message(self):
        config = _make_config()
        msg = _make_handoff_message()
        instance = _make_runtime_client(config)

        with (
            patch(
                "discord_nexus.client.execute_assignment_accept",
                return_value=(True, "accepted"),
            ),
            patch(
                "discord_nexus.client.read_bootstrap",
                return_value=None,
            ),
        ):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    instance._try_coordinator_handoff(msg)
                )
            finally:
                loop.close()

        self.assertTrue(result)
        # Adapter must still be called
        instance.adapter.call.assert_called_once()
        prompt = instance.adapter.call.call_args[0][0]
        # Prompt must indicate bootstrap is missing
        self.assertIn("未找到 bootstrap", prompt)


class TestCoordinatorHandoffNotCoordinatorMessage(unittest.TestCase):
    """Non-coordinator messages are not handled."""

    def test_returns_false_for_non_matching_content(self):
        config = _make_config()
        # Content without proper handoff format
        msg = _make_handoff_message(content="<@111> hello there")
        instance = _make_runtime_client(config)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                instance._try_coordinator_handoff(msg)
            )
        finally:
            loop.close()

        self.assertFalse(result)
        instance.adapter.call.assert_not_called()


class TestActionScopeConstraint(unittest.TestCase):
    """Only assignment.accept is auto-executed. Other actions must be rejected."""

    def test_rejects_mark_done_action(self):
        handoff_msg = (
            "[handoff] <@111> workspace_id=discord-nexus "
            "task_id=phase-5.1 action=assignment.mark-done"
        )
        from discord_nexus.handoff_handler import parse_coordinator_handoff
        result = parse_coordinator_handoff(
            handoff_msg, my_discord_user_id=111
        )
        self.assertIsNone(result)

    def test_rejects_closeout_action(self):
        handoff_msg = (
            "[handoff] <@111> workspace_id=discord-nexus "
            "task_id=phase-5.1 action=assignment.closeout"
        )
        from discord_nexus.handoff_handler import parse_coordinator_handoff
        result = parse_coordinator_handoff(
            handoff_msg, my_discord_user_id=111
        )
        self.assertIsNone(result)

    def test_rejects_merge_action(self):
        handoff_msg = (
            "[handoff] <@111> workspace_id=discord-nexus "
            "task_id=phase-5.1 action=merge"
        )
        from discord_nexus.handoff_handler import parse_coordinator_handoff
        result = parse_coordinator_handoff(
            handoff_msg, my_discord_user_id=111
        )
        self.assertIsNone(result)

    def test_rejects_deploy_action(self):
        handoff_msg = (
            "[handoff] <@111> workspace_id=discord-nexus "
            "task_id=phase-5.1 action=deploy"
        )
        from discord_nexus.handoff_handler import parse_coordinator_handoff
        result = parse_coordinator_handoff(
            handoff_msg, my_discord_user_id=111
        )
        self.assertIsNone(result)

    def test_rejects_pr_action(self):
        handoff_msg = (
            "[handoff] <@111> workspace_id=discord-nexus "
            "task_id=phase-5.1 action=pr.create"
        )
        from discord_nexus.handoff_handler import parse_coordinator_handoff
        result = parse_coordinator_handoff(
            handoff_msg, my_discord_user_id=111
        )
        self.assertIsNone(result)

    def test_accepts_only_assignment_accept(self):
        handoff_msg = (
            "[handoff] <@111> workspace_id=discord-nexus "
            "task_id=phase-5.1 action=assignment.accept"
        )
        from discord_nexus.handoff_handler import parse_coordinator_handoff
        result = parse_coordinator_handoff(
            handoff_msg, my_discord_user_id=111
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "assignment.accept")


if __name__ == "__main__":
    unittest.main()
