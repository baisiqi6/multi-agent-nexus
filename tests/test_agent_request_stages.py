"""Tests for the AgentRequestMixin three-stage decomposition."""
from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

from cogs.agent_request import (
    AgentRequestMixin,
    LOCAL_AGENT_NAME,
    _AgentInvocationResult,
    _AgentRequestSetup,
    _AgentResponseResult,
)


class _DummyPlaceholder:
    def __init__(self):
        self.edits: list[str] = []

    async def edit(self, content: str) -> None:
        self.edits.append(content)


class _DummyChannel:
    def __init__(self, channel_id: int = 1):
        self.id = channel_id
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)

    def typing(self):
        class _Ctx:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        return _Ctx()


class _DummyBot:
    def __init__(self):
        self.allowlist = SimpleNamespace(is_allowed=lambda _uid: True)
        self.agents = {}
        self.agent_configs = {}
        self.conv_config = {}
        self._agent_status = {LOCAL_AGENT_NAME: True}
        self.agent_channels = {}
        self._locks = {}
        self._discovery_calls: list[tuple[str, str]] = []
        self._alerts: list[str] = []
        self.handoffs_channel_id = None
        self.alert_mention = None
        self.wiki_enabled = False

    def _get_lock(self, key: str):
        import asyncio
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def _get_channel_mission(self, channel_id: str, agent_name: str) -> str:
        return ""

    async def _post_discovery(self, finding: str, agent_name: str) -> None:
        self._discovery_calls.append((finding, agent_name))

    async def _post_to_alerts(self, text: str) -> None:
        self._alerts.append(text)


class _TestableAgentRequestMixin(AgentRequestMixin):
    MAX_HANDOFF_DEPTH = 4

    def __init__(self):
        self.bot = _DummyBot()
        self._active_agents: dict[str, object] = {}
        self._sent_as_agent: list[str] = []
        self._started_placeholders: list[tuple] = []
        self._finished_placeholders: list[tuple] = []

    def _agent_label(self, agent_name: str) -> str:
        return agent_name.capitalize()

    async def _send_as_agent(self, channel, agent_name: str, text: str):
        self._sent_as_agent.append((agent_name, text))

    async def _start_placeholder(self, channel, agent_name: str):
        self._started_placeholders.append((channel.id, agent_name))
        return _DummyPlaceholder()

    async def _process_scratch(self, thread_id: str, agent_name: str, scratch_raw: str):
        pass

    async def _handle_research(self, channel, query: str, requesting_agent: str):
        pass

    def _extract_handoffs(self, response: str, source_agent: str):
        return [], response

    def _parse_workspace(self, workspace: str, agent_name: str):
        return None, None

    def _workspace_without_session(self, workspace: str, agent_name: str):
        return workspace

    async def _finish_with_placeholder(self, channel, agent_name, placeholder, text):
        self._finished_placeholders.append((channel.id, agent_name, text))

    async def _get_managed_history(self, thread_id, budget):
        return [{"role": "user", "content": "hi"}]


class TestStageSetupAgentRequest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mixin = _TestableAgentRequestMixin()
        self.channel = _DummyChannel(channel_id=123)
        self.mixin.bot.agents["researcher"] = object()

    async def test_rejects_depth_limit(self):
        result = await self.mixin._stage_setup_agent_request(
            agent_name="researcher",
            prompt="hello",
            thread_id="t",
            channel=self.channel,
            user_id=1,
            depth=4,
            source_agent=None,
            work_dir=None,
            message_id=None,
            origin_already_persisted=False,
            attachments=None,
        )
        self.assertIsNone(result)
        self.assertEqual(
            self.mixin._sent_as_agent,
            [("researcher", "Handoff chain limit (4) reached. Stopping.")],
        )

    async def test_rejects_unauthorized_user(self):
        self.mixin.bot.allowlist = SimpleNamespace(is_allowed=lambda _uid: False)
        result = await self.mixin._stage_setup_agent_request(
            agent_name="researcher",
            prompt="hello",
            thread_id="t",
            channel=self.channel,
            user_id=1,
            depth=0,
            source_agent=None,
            work_dir=None,
            message_id=None,
            origin_already_persisted=False,
            attachments=None,
        )
        self.assertIsNone(result)
        self.assertTrue(any("not authorized" in s for s in self.channel.sent))

    async def test_returns_setup_for_valid_researcher(self):
        result = await self.mixin._stage_setup_agent_request(
            agent_name="researcher",
            prompt="hello",
            thread_id="t",
            channel=self.channel,
            user_id=1,
            depth=0,
            source_agent=None,
            work_dir=None,
            message_id=None,
            origin_already_persisted=False,
            attachments=None,
        )
        self.assertIsInstance(result, _AgentRequestSetup)
        self.assertEqual(result.agent_name, "researcher")
        self.assertEqual(result.prompt, "hello")

    async def test_resolves_work_dir_and_flags(self):
        self.mixin._resolve_work_dir = lambda prompt, channel: (
            prompt.replace(" --project foo", ""),
            "/foo",
        )
        self.mixin.bot.agents["claude"] = object()
        self.mixin.bot.agent_configs["claude"] = {}
        result = await self.mixin._stage_setup_agent_request(
            agent_name="claude",
            prompt="hello --project foo --long",
            thread_id="t",
            channel=self.channel,
            user_id=1,
            depth=0,
            source_agent=None,
            work_dir=None,
            message_id=None,
            origin_already_persisted=False,
            attachments=None,
        )
        self.assertEqual(result.work_dir, "/foo")
        self.assertEqual(result.prompt, "hello")
        self.assertTrue(result.use_extended_timeout)


class TestStageInvokeAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mixin = _TestableAgentRequestMixin()
        self.channel = _DummyChannel(channel_id=1)
        self.agent = SimpleNamespace(
            call=mock.AsyncMock(return_value=("response text", {"tokens_output": 42}))
        )
        self.mixin.bot.agents["researcher"] = self.agent
        self.setup = _AgentRequestSetup(
            agent_name="researcher",
            prompt="hello",
            thread_id="t",
            channel=self.channel,
            user_id=1,
            depth=0,
            source_agent=None,
            work_dir=None,
            use_extended_timeout=False,
            activity_timeout_override=None,
            agent=self.agent,
            agent_config={},
            is_local=False,
            message_id=None,
            origin_already_persisted=False,
            attachments=None,
        )
        self.mixin.bot.db = mock.AsyncMock()
        self.mixin.bot.db.create_job.return_value = 7

    async def test_success_invocation_returns_result(self):
        from cogs import agents as agents_facade

        result = await self.mixin._stage_invoke_agent(
            self.setup, ephemeral_context="", agents_facade=agents_facade
        )
        self.assertIsInstance(result, _AgentInvocationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.job_id, 7)
        self.assertEqual(result.response_text, "response text")
        self.assertEqual(result.metadata, {"tokens_output": 42})
        self.agent.call.assert_awaited_once()

    async def test_rate_limit_returns_fallback(self):
        from agents.base import AgentRateLimitError
        from cogs import agents as agents_facade

        self.setup.agent_name = "claude"
        self.setup.agent_config = {}
        self.agent.call = mock.AsyncMock(side_effect=AgentRateLimitError("limit"))
        self.mixin.bot._agent_status = {"codex": True, LOCAL_AGENT_NAME: True}
        result = await self.mixin._stage_invoke_agent(
            self.setup, ephemeral_context="", agents_facade=agents_facade
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "rate_limit")
        self.assertEqual(result.rate_limit_fallback, "codex")
        self.assertFalse(result.terminal)

    async def test_offline_is_terminal(self):
        from agents.base import AgentOfflineError
        from cogs import agents as agents_facade

        self.agent.call = mock.AsyncMock(side_effect=AgentOfflineError("offline"))
        result = await self.mixin._stage_invoke_agent(
            self.setup, ephemeral_context="", agents_facade=agents_facade
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "offline")
        self.assertTrue(result.terminal)

    async def test_timeout_is_terminal(self):
        from agents.base import AgentTimeoutError
        from cogs import agents as agents_facade

        self.agent.call = mock.AsyncMock(side_effect=AgentTimeoutError("timeout"))
        result = await self.mixin._stage_invoke_agent(
            self.setup, ephemeral_context="", agents_facade=agents_facade
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "timeout")
        self.assertTrue(result.terminal)


class TestStageProcessResponseTags(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mixin = _TestableAgentRequestMixin()
        self.channel = _DummyChannel(channel_id=1)
        self.setup = _AgentRequestSetup(
            agent_name="researcher",
            prompt="hello",
            thread_id="t",
            channel=self.channel,
            user_id=1,
            depth=0,
            source_agent=None,
            work_dir=None,
            use_extended_timeout=False,
            activity_timeout_override=None,
            agent=object(),
            agent_config={},
            is_local=False,
            message_id=None,
            origin_already_persisted=False,
            attachments=None,
        )
        self.mixin.bot.db = mock.AsyncMock()
        self.placeholder = _DummyPlaceholder()

    async def test_failed_invocation_is_forwarded(self):
        from cogs import agents as agents_facade

        invoke = _AgentInvocationResult(
            success=False,
            job_id=7,
            placeholder_msg=None,
            error="offline",
            terminal=True,
        )
        result = await self.mixin._stage_process_response_tags(
            self.setup, invoke, agents_facade=agents_facade
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "offline")
        self.assertTrue(result.terminal)

    async def test_processes_scratch_and_discovery(self):
        from cogs import agents as agents_facade

        self.mixin._process_scratch = mock.AsyncMock()
        invoke = _AgentInvocationResult(
            success=True,
            job_id=7,
            placeholder_msg=self.placeholder,
            response_text=(
                "<!-- SCRATCH -->{\"next_step\": \"x\"}<!-- /SCRATCH -->\n"
                "<!-- DISCOVERY: found it -->\n"
                "clean text"
            ),
            metadata={},
        )
        result = await self.mixin._stage_process_response_tags(
            self.setup, invoke, agents_facade=agents_facade
        )
        self.assertTrue(result.success)
        self.assertEqual(result.clean_response, "clean text")
        self.mixin._process_scratch.assert_awaited_once()
        self.assertEqual(
            self.mixin.bot._discovery_calls, [("found it", "researcher")]
        )

    async def test_extracts_handoffs_and_research(self):
        from cogs import agents as agents_facade

        self.setup.agent_name = "claude"
        invoke = _AgentInvocationResult(
            success=True,
            job_id=7,
            placeholder_msg=self.placeholder,
            response_text=(
                "<!-- RESEARCH: look this up -->\n"
                "@codex do more"
            ),
            metadata={},
        )

        self.mixin._extract_handoffs = lambda text, source: (
            [("codex", "do more")],
            text.replace("@codex do more", "").strip(),
        )
        result = await self.mixin._stage_process_response_tags(
            self.setup, invoke, agents_facade=agents_facade
        )
        self.assertTrue(result.success)
        self.assertEqual(result.handoff_agents, [("codex", "do more")])
        self.assertEqual(result.research_queries, ["look this up"])


class TestStageFollowUp(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mixin = _TestableAgentRequestMixin()
        self.channel = _DummyChannel(channel_id=1)
        self.setup = _AgentRequestSetup(
            agent_name="claude",
            prompt="hello",
            thread_id="t",
            channel=self.channel,
            user_id=1,
            depth=0,
            source_agent=None,
            work_dir=None,
            use_extended_timeout=False,
            activity_timeout_override=None,
            agent=object(),
            agent_config={},
            is_local=False,
            message_id=None,
            origin_already_persisted=False,
            attachments=None,
        )
        self.mixin.bot.db = mock.AsyncMock()

    async def test_rate_limit_fallback_retries(self):
        from cogs import agents as agents_facade

        self.mixin.handle_agent_request = mock.AsyncMock()
        response = _AgentResponseResult(
            success=False,
            job_id=7,
            prompt="hello",
            work_dir=None,
            rate_limit_fallback="codex",
            terminal=False,
        )
        await self.mixin._stage_follow_up(
            self.setup, response, agents_facade=agents_facade
        )
        self.mixin.handle_agent_request.assert_awaited_once()
        call_kwargs = self.mixin.handle_agent_request.await_args.kwargs
        self.assertEqual(call_kwargs["agent_name"], "codex")
        self.assertEqual(call_kwargs["depth"], 0)

    async def test_terminal_failure_does_not_retry(self):
        from cogs import agents as agents_facade

        self.mixin.handle_agent_request = mock.AsyncMock()
        response = _AgentResponseResult(
            success=False,
            job_id=7,
            prompt="hello",
            work_dir=None,
            error="offline",
            terminal=True,
        )
        await self.mixin._stage_follow_up(
            self.setup, response, agents_facade=agents_facade
        )
        self.mixin.handle_agent_request.assert_not_awaited()

    async def test_handoffs_and_research_triggered(self):
        from cogs import agents as agents_facade

        self.mixin.handle_agent_request = mock.AsyncMock()
        self.mixin._handle_research = mock.AsyncMock()
        self.mixin.bot.agent_channels = {"codex": {1}}
        response = _AgentResponseResult(
            success=True,
            job_id=7,
            prompt="hello",
            work_dir=None,
            clean_response="ok",
            handoff_agents=[("codex", "do more")],
            research_queries=["q"],
        )
        await self.mixin._stage_follow_up(
            self.setup, response, agents_facade=agents_facade
        )
        self.mixin.handle_agent_request.assert_awaited_once()
        self.mixin._handle_research.assert_awaited_once_with(
            self.channel, "q", "claude"
        )


if __name__ == "__main__":
    unittest.main()
