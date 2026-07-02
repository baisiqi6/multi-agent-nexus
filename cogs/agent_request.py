"""Core agent request orchestration used by the Discord Agents cog."""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field

import discord

from agents.base import AgentOfflineError, AgentRateLimitError, AgentTimeoutError
from routing.dispatcher import resolve_channel_id, should_respond
from security.filter import scan_output
from utils.attachments import ProcessedAttachments
from utils.confirm import PrivateWikiPromoteView
from utils.log import set_correlation

log = logging.getLogger("multinexus")

LOCAL_AGENT_NAME = "mac-openclaw"
LEGACY_LOCAL_AGENT_NAME = "local-agent"
LOCAL_AGENT_NAMES = {LOCAL_AGENT_NAME, LEGACY_LOCAL_AGENT_NAME}


def build_discord_context(alert_mention: str | None, mission: str, wiki_context: str) -> str:
    """Build the [Discord Context] block appended to relay messages for local agents."""
    parts = ["[Discord Context]"]
    if alert_mention:
        parts.append(f"alert_mention: {alert_mention}")
    if mission:
        parts.append(f"mission: {mission}")
    if wiki_context:
        parts.append(f"wiki_context:\n{wiki_context}")
    return "\n".join(parts)


def _format_memory_block(memories: list[dict]) -> str:
    """Format a list of memory dicts into a plain-text block for prompt injection."""
    lines = []
    for m in memories:
        lines.append(f"- [{m['type']}] {m['content']}")
    return "\n".join(lines)


def _is_local_agent_name(agent_name: str) -> bool:
    return agent_name in LOCAL_AGENT_NAMES


@dataclass
class _AgentRequestSetup:
    """Inputs validated before any irreversible agent call is made."""

    agent_name: str
    prompt: str
    thread_id: str
    channel: object
    user_id: int
    depth: int
    source_agent: str | None
    work_dir: str | None
    use_extended_timeout: bool
    activity_timeout_override: int | None
    agent: object
    agent_config: dict
    is_local: bool
    message_id: str | None
    origin_already_persisted: bool
    attachments: ProcessedAttachments | None


@dataclass
class _AgentInvocationResult:
    """Result of the agent call stage, including success and failure paths."""

    success: bool
    job_id: int
    placeholder_msg: discord.WebhookMessage | None
    response_text: str = ""
    metadata: dict = field(default_factory=dict)
    last_streamed_text: str = ""
    private_wiki_pages: list[str] = field(default_factory=list)
    error: str | None = None
    exception: Exception | None = None
    rate_limit_fallback: str | None = None
    terminal: bool = False


@dataclass
class _AgentResponseResult:
    """Result of response-tag processing, consumed by follow-up stage."""

    success: bool
    job_id: int
    prompt: str
    work_dir: str | None
    clean_response: str = ""
    handoff_agents: list[tuple[str, str]] = field(default_factory=list)
    research_queries: list[str] = field(default_factory=list)
    error: str | None = None
    exception: Exception | None = None
    rate_limit_fallback: str | None = None
    terminal: bool = False


class AgentRequestMixin:
    async def handle_agent_request(
        self,
        agent_name: str,
        prompt: str,
        thread_id: str,
        channel,
        user_id: int,
        depth: int = 0,
        source_agent: str | None = None,
        *,
        ephemeral_context: str = "",
        work_dir: str | None = None,
        message_id: str | None = None,
        origin_already_persisted: bool = False,
        attachments: ProcessedAttachments | None = None,
    ):
        """Handle a request for any agent.

        This is the central dispatch point. It delegates to three stages:
          1. _stage_setup_agent_request — validate and prepare inputs.
          2. _stage_invoke_agent — run the agent call under the per-thread lock.
          3. _stage_process_response_tags — process SCRATCH/DISCOVERY/WIKI/etc.
          4. _stage_follow_up — rate-limit fallback, handoffs, researcher follow-ups.
        """
        from cogs import agents as agents_facade

        agents_facade.set_correlation(agent=agent_name, channel=str(channel.id))

        setup = await self._stage_setup_agent_request(
            agent_name,
            prompt,
            thread_id,
            channel,
            user_id,
            depth,
            source_agent,
            work_dir=work_dir,
            message_id=message_id,
            origin_already_persisted=origin_already_persisted,
            attachments=attachments,
        )
        if setup is None:
            return

        lock = self.bot._get_lock(f"{thread_id}:{agent_name}")
        async with lock:
            invoke = await self._stage_invoke_agent(
                setup, ephemeral_context=ephemeral_context, agents_facade=agents_facade
            )
            response = await self._stage_process_response_tags(
                setup, invoke, agents_facade=agents_facade
            )

        await self._stage_follow_up(setup, response, agents_facade=agents_facade)

    async def _stage_setup_agent_request(
        self,
        agent_name: str,
        prompt: str,
        thread_id: str,
        channel,
        user_id: int,
        depth: int,
        source_agent: str | None,
        *,
        work_dir: str | None,
        message_id: str | None,
        origin_already_persisted: bool,
        attachments: ProcessedAttachments | None,
    ) -> _AgentRequestSetup | None:
        """Resolve work directory, parse flags, enforce limits, and look up agent.

        Returns None when the request is rejected before any irreversible work.
        """
        # Resolve project work directory for CLI agents
        if agent_name in ("claude", "codex") and work_dir is None:
            prompt, work_dir = self._resolve_work_dir(prompt, channel)

        # --long flag: use extended timeout (Claude/Codex)
        use_extended_timeout = False
        if agent_name in ("claude", "codex") and re.search(r"--long\b", prompt):
            prompt = re.sub(r"\s*--long\b", "", prompt).strip()
            use_extended_timeout = True

        # Detect and strip -t <seconds> flag for per-command activity timeout (Codex only).
        activity_timeout_override: int | None = None
        if agent_name == "codex":
            t_match = re.search(r"-t\s+(\d+)", prompt)
            if t_match:
                activity_timeout_override = int(t_match.group(1))
                prompt = re.sub(r"\s*-t\s+\d+", "", prompt).strip()

        # Enforce handoff depth limit
        if depth > 0 and depth >= self.MAX_HANDOFF_DEPTH:
            await self._send_as_agent(
                channel,
                source_agent or agent_name,
                f"Handoff chain limit ({self.MAX_HANDOFF_DEPTH}) reached. Stopping.",
            )
            return None

        if not self.bot.allowlist.is_allowed(user_id):
            await channel.send(
                f"You're not authorized to use {self._agent_label(agent_name)}."
            )
            return None

        agent = self.bot.agents.get(agent_name)
        if not agent:
            await channel.send(f"Unknown agent: {agent_name}")
            return None

        agent_config = self.bot.agent_configs.get(agent_name, {})
        is_local = _is_local_agent_name(agent_name) or (
            agent_config.get("inference_backend") in {"local", "openclaw"}
        )

        return _AgentRequestSetup(
            agent_name=agent_name,
            prompt=prompt,
            thread_id=thread_id,
            channel=channel,
            user_id=user_id,
            depth=depth,
            source_agent=source_agent,
            work_dir=work_dir,
            use_extended_timeout=use_extended_timeout,
            activity_timeout_override=activity_timeout_override,
            agent=agent,
            agent_config=agent_config,
            is_local=is_local,
            message_id=message_id,
            origin_already_persisted=origin_already_persisted,
            attachments=attachments,
        )

    async def _stage_invoke_agent(
        self,
        setup: _AgentRequestSetup,
        *,
        ephemeral_context: str,
        agents_facade,
    ) -> _AgentInvocationResult:
        """Load context, call the agent backend, and return a success/failure result.

        This stage runs inside the per-thread lock and performs the irreversible
        external agent call. Response-tag processing is intentionally left to the
        next stage so it can be tested independently.
        """
        channel = setup.channel
        agent_name = setup.agent_name
        prompt = setup.prompt
        thread_id = setup.thread_id
        user_id = setup.user_id
        depth = setup.depth
        agent = setup.agent
        agent_config = setup.agent_config
        is_local = setup.is_local
        attachments = setup.attachments

        rate_limit_fallback: str | None = None
        placeholder_msg: discord.WebhookMessage | None = None
        last_chunk_edit: float = 0.0
        last_streamed_text: str = ""

        if depth == 0 and not setup.origin_already_persisted:
            await self.bot.db.save_message(
                thread_id, "user", prompt,
                author_id=str(user_id),
                message_id=setup.message_id,
            )

        budget = self.bot.conv_config.get("history_budget_chars", 12000)
        history = await self._get_managed_history(thread_id, budget)
        if ephemeral_context:
            if not history or history[-1]["role"] != "user":
                raise RuntimeError(
                    "Expected last history entry to be user message"
                )
            history[-1]["content"] = ephemeral_context + "\n\n" + history[-1]["content"]

        # Memory injection — shared always; private only for local-inference agents
        memory_block = ""
        if agent_name != "researcher":
            shared_memories = await self.bot.db.get_memories(limit=10)
            if shared_memories:
                memory_block = agents_facade._format_memory_block(shared_memories)
            if is_local and getattr(self.bot, "private_db", None) is not None:
                private_memories = await self.bot.private_db.get_memories_for_injection(limit=10)
                if private_memories:
                    private_block = (
                        "[Private Memory]\n"
                        + agents_facade._format_memory_block(private_memories)
                    )
                    memory_block = (
                        (memory_block + "\n\n" + private_block)
                        if memory_block
                        else private_block
                    )

        placeholder_msg = await self._start_placeholder(channel, agent_name)

        async def _on_chunk(text: str) -> None:
            """Update the placeholder message with streaming progress (throttled to 1Hz)."""
            nonlocal last_chunk_edit, last_streamed_text
            last_streamed_text = text  # always capture, used as fallback on interruption
            if placeholder_msg is None:
                return
            now = time.monotonic()
            if now - last_chunk_edit < 1.0:
                return
            last_chunk_edit = now
            preview = text[:1990] + "…" if len(text) > 1990 else text
            try:
                await placeholder_msg.edit(content=preview)
            except discord.HTTPException:
                pass

        job_id = await self.bot.db.create_job(thread_id, agent_name, prompt)
        agents_facade.set_correlation(job_id=str(job_id), session_id=thread_id)
        await self.bot.db.update_job(job_id, "running")

        try:
            workspace = await self.bot.db.get_workspace(thread_id, agent_name)
            cli_session_id = None
            workspace_for_prompt = workspace
            if agent_name in ("codex", "claude"):
                cli_session_id, _ = self._parse_workspace(workspace, agent_name)
                workspace_for_prompt = self._workspace_without_session(workspace, agent_name)
            channel_id_str = str(resolve_channel_id(channel))
            mission = self.bot._get_channel_mission(channel_id_str, agent_name)

            self._active_agents[str(channel.id)] = agent
            async with channel.typing():
                # Wiki context — injected for conversational agents (not researcher)
                wiki_context = ""
                if (
                    agent_name != "researcher"
                    and getattr(self.bot, "wiki_enabled", False)
                    and getattr(self.bot, "wiki", None) is not None
                ):
                    try:
                        wiki_context = await self.bot.wiki.get_relevant_context(
                            query=prompt,
                            budget_chars=4000,
                            channel_id=channel_id_str,
                            include_private=is_local,
                            agent_name=agent_name,
                        ) or ""
                    except Exception:
                        log.warning(
                            "wiki: context lookup failed for agent=%s", agent_name,
                            exc_info=True,
                        )

                # --- Agent call ---

                if agent_name == LOCAL_AGENT_NAME:
                    # Local agent relay path — system prompt is owned by the backend.
                    # Discord context (mission, wiki, memory) is appended to the last user message.
                    relay_messages = [dict(m) for m in history]
                    ctx_block = agents_facade.build_discord_context(
                        self.bot.alert_mention, mission, wiki_context
                    )
                    if memory_block:
                        ctx_block += f"\n\nmemory:\n{memory_block}"
                    if relay_messages and relay_messages[-1]["role"] == "user":
                        last_text = relay_messages[-1]["content"] + "\n\n" + ctx_block
                        vision_blocks = (attachments.vision_blocks if attachments else [])
                        if vision_blocks:
                            # OpenAI multimodal format: content is a list of blocks.
                            relay_messages[-1]["content"] = [
                                {"type": "text", "text": last_text},
                                *vision_blocks,
                            ]
                        else:
                            relay_messages[-1]["content"] = last_text
                    if hasattr(agent, "call_streaming"):
                        result = await agent.call_streaming(
                            relay_messages, "", on_chunk=_on_chunk,
                            mission=mission, workspace=workspace,
                        )
                    else:
                        result = await agent.call(
                            relay_messages, "", mission=mission, workspace=workspace
                        )

                elif agent_name == "researcher":
                    # One-shot query — pass only the current prompt, not history
                    result = await agent.call([{"role": "user", "content": prompt}], "")

                else:
                    # Cloud agents (Claude, Codex) — system prompt injected here
                    system_prompt = agent_config.get(
                        "system_prompt", f"You are {agent_name.capitalize()}."
                    )
                    if self.bot.alert_mention:
                        system_prompt += (
                            f"\n\nUSER MENTION: To notify the user directly, "
                            f"use {self.bot.alert_mention} in your response."
                        )
                    if wiki_context:
                        system_prompt += f"\n\n## [Wiki Context]\n{wiki_context}"
                    if memory_block:
                        system_prompt += f"\n\n## [Remembered Facts]\n{memory_block}"
                    # on_chunk streams partial text to the placeholder as agent generates.
                    call_kwargs = {}
                    if agent_name in ("claude", "codex"):
                        call_kwargs["on_chunk"] = _on_chunk
                    if agent_name == "codex" and setup.activity_timeout_override:
                        call_kwargs["activity_timeout"] = setup.activity_timeout_override
                    call_timeout = agent_config.get("timeout_extended") if setup.use_extended_timeout else None

                    # Resume existing session if available, otherwise fresh call.
                    if cli_session_id and agent_name in ("codex", "claude"):
                        try:
                            # Prepend wiki context to resumed prompt — resume()
                            # doesn't take a system_prompt param.
                            resume_prompt = self._format_history_block(history)
                            if wiki_context:
                                resume_prompt = (
                                    f"[Wiki Context]\n{wiki_context}\n\n---\n\n{resume_prompt}"
                                )
                            resume_kwargs = {"work_dir": setup.work_dir, "timeout": call_timeout, "on_chunk": _on_chunk}
                            if agent_name == "codex" and setup.activity_timeout_override:
                                resume_kwargs["activity_timeout"] = setup.activity_timeout_override
                            result = await agent.resume(
                                cli_session_id,
                                resume_prompt,
                                **resume_kwargs,
                            )
                        except agents_facade.AgentOfflineError:
                            log.warning(
                                "%s resume failed (thread=%s, session=%s); falling back to fresh call",
                                agent_name,
                                thread_id,
                                cli_session_id,
                                exc_info=True,
                            )
                            result = await agent.call(
                                history, system_prompt,
                                mission=mission, workspace=workspace_for_prompt, work_dir=setup.work_dir,
                                timeout=call_timeout,
                                **call_kwargs,
                            )
                    else:
                        result = await agent.call(
                            history, system_prompt,
                            mission=mission, workspace=workspace_for_prompt, work_dir=setup.work_dir,
                            timeout=call_timeout,
                            **call_kwargs,
                        )

            if isinstance(result, tuple):
                response_text, metadata = result
                if isinstance(metadata, int):
                    metadata = {"tokens_output": metadata or None}
                elif metadata is None:
                    metadata = {}
            else:
                response_text = result
                metadata = {}
            # Persist CLI session ID for resumable agents
            if agent_name in ("codex", "claude"):
                _sid_key = "codex_session_id" if agent_name == "codex" else "session_id"
                returned_session_id = metadata.get(_sid_key)
                if isinstance(returned_session_id, str) and returned_session_id:
                    workspace = self._workspace_with_session(workspace, agent_name, returned_session_id)
                    await self.bot.db.upsert_workspace(thread_id, agent_name, workspace)
            self._active_agents.pop(str(channel.id), None)

            return _AgentInvocationResult(
                success=True,
                job_id=job_id,
                placeholder_msg=placeholder_msg,
                response_text=response_text,
                metadata=metadata,
                last_streamed_text=last_streamed_text,
            )

        except agents_facade.AgentRateLimitError as e:
            await self.bot.db.update_job(job_id, "failed")
            log.warning("%s rate/usage limit hit: %s", agent_name, e)
            # Fallback chain: claude → codex → mac-openclaw; codex → mac-openclaw
            fallback_chain = {
                "claude": ["codex", LOCAL_AGENT_NAME],
                "codex": [LOCAL_AGENT_NAME],
            }
            for fallback in fallback_chain.get(agent_name, []):
                if self.bot._agent_status.get(fallback, True):
                    rate_limit_fallback = fallback
                    break
            if rate_limit_fallback:
                await self.bot._post_to_alerts(
                    f"{self._agent_label(agent_name)} usage/rate limit hit — "
                    f"falling back to {self._agent_label(rate_limit_fallback)}."
                )
                switch_msg = (
                    f"*{self._agent_label(agent_name)} limit reached — "
                    f"switching to {self._agent_label(rate_limit_fallback)}...*"
                )
                if placeholder_msg:
                    try:
                        await placeholder_msg.edit(content=switch_msg)
                        placeholder_msg = None
                    except discord.HTTPException:
                        await channel.send(switch_msg)
                else:
                    await channel.send(switch_msg)
            else:
                err_msg = (
                    f"{self._agent_label(agent_name)} hit its usage limit "
                    "and no fallback is available."
                )
                if placeholder_msg:
                    try:
                        await placeholder_msg.edit(content=err_msg)
                        placeholder_msg = None
                    except discord.HTTPException:
                        await channel.send(err_msg)
                else:
                    await channel.send(err_msg)

            return _AgentInvocationResult(
                success=False,
                job_id=job_id,
                placeholder_msg=placeholder_msg,
                last_streamed_text=last_streamed_text,
                error="rate_limit",
                exception=e,
                rate_limit_fallback=rate_limit_fallback,
                terminal=False,
            )

        except agents_facade.AgentOfflineError as e:
            await self.bot.db.update_job(job_id, "failed")
            msg = f"{self._agent_label(agent_name)} is offline: {e}"
            log.error(msg)
            if placeholder_msg:
                try:
                    await placeholder_msg.edit(content=msg)
                except discord.HTTPException:
                    await channel.send(msg)
            else:
                await channel.send(msg)
            return _AgentInvocationResult(
                success=False,
                job_id=job_id,
                placeholder_msg=placeholder_msg,
                error="offline",
                exception=e,
                terminal=True,
            )

        except agents_facade.AgentTimeoutError as e:
            await self.bot.db.update_job(job_id, "failed")
            msg = f"{self._agent_label(agent_name)} timed out: {e}"
            log.error(msg)
            # Save partial streamed response so it appears in future history.
            if last_streamed_text:
                partial = agents_facade.scan_output(last_streamed_text)
                if partial:
                    await self.bot.db.save_message(
                        thread_id, "assistant",
                        f"[partial — timed out]\n{partial}",
                    )
            if placeholder_msg:
                try:
                    await placeholder_msg.edit(content=msg)
                except discord.HTTPException:
                    await channel.send(msg)
            else:
                await channel.send(msg)
            return _AgentInvocationResult(
                success=False,
                job_id=job_id,
                placeholder_msg=placeholder_msg,
                last_streamed_text=last_streamed_text,
                error="timeout",
                exception=e,
                terminal=True,
            )

    async def _stage_process_response_tags(
        self,
        setup: _AgentRequestSetup,
        invoke: _AgentInvocationResult,
        *,
        agents_facade,
    ) -> _AgentResponseResult:
        """Process special tags, persist the response, and prepare follow-ups.

        Runs inside the same lock as the agent call. For failure invocations this
        stage is a no-op that simply forwards the failure context.
        """
        if not invoke.success:
            return _AgentResponseResult(
                success=False,
                job_id=invoke.job_id,
                prompt=setup.prompt,
                work_dir=setup.work_dir,
                error=invoke.error,
                exception=invoke.exception,
                rate_limit_fallback=invoke.rate_limit_fallback,
                terminal=invoke.terminal,
            )

        agent_name = setup.agent_name
        channel = setup.channel
        thread_id = setup.thread_id
        prompt = setup.prompt
        response_text = invoke.response_text
        metadata = invoke.metadata
        placeholder_msg = invoke.placeholder_msg
        private_wiki_pages: list[str] = []
        handoff_agents: list[tuple[str, str]] = []
        research_queries: list[str] = []

        # --- Process special tags ---

        # SCRATCH — agent working memory, stored per-thread per-agent
        scratch_match = re.search(
            r"<!--\s*SCRATCH\s*-->(.*?)<!--\s*/SCRATCH\s*-->",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if scratch_match:
            _scratch_raw = scratch_match.group(1).strip()
            response_text = re.sub(
                r"\s*<!--\s*SCRATCH\s*-->.*?<!--\s*/SCRATCH\s*-->\s*",
                "",
                response_text,
                flags=re.DOTALL | re.IGNORECASE,
            ).strip()
            await self._process_scratch(thread_id, agent_name, _scratch_raw)

        # DISCOVERY — posts to #discoveries channel
        discovery_match = re.search(
            r"<!--\s*DISCOVERY:\s*(.*?)\s*-->",
            response_text,
            re.IGNORECASE,
        )
        if discovery_match:
            finding = discovery_match.group(1).strip()
            response_text = re.sub(
                r"\s*<!--\s*DISCOVERY:.*?-->\s*",
                "",
                response_text,
                flags=re.IGNORECASE,
            ).strip()
            await self.bot._post_discovery(finding, agent_name)

        # WIKI — writes to shared wiki
        wiki_blocks = list(re.finditer(
            r"<!--\s*WIKI:\s*(\S+)\s*-->(.*?)<!--\s*/WIKI\s*-->",
            response_text,
            re.DOTALL | re.IGNORECASE,
        ))
        if wiki_blocks:
            response_text = re.sub(
                r"\s*<!--\s*WIKI:\s*\S+\s*-->.*?<!--\s*/WIKI\s*-->\s*",
                "",
                response_text,
                flags=re.DOTALL | re.IGNORECASE,
            ).strip()
            for wiki_match in wiki_blocks:
                raw_page_name = wiki_match.group(1).strip()
                wiki_page_name = raw_page_name.lower()
                # Validate page name: lowercase alphanumeric + hyphens
                if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*[a-z0-9]", wiki_page_name):
                    log.warning(
                        "wiki: rejected invalid page name from agent: %r", raw_page_name
                    )
                    response_text += (
                        f"\n*[Wiki: rejected invalid page name `{raw_page_name[:40]}`]*"
                    )
                    continue
                wiki_page_content = wiki_match.group(2).strip()
                wiki_aliases = []
                alias_line = re.match(
                    r"^ALIASES:\s*(.+)$", wiki_page_content, re.MULTILINE
                )
                if alias_line:
                    wiki_aliases = [a.strip() for a in alias_line.group(1).split(",")]
                    wiki_page_content = wiki_page_content[alias_line.end():].lstrip("\n")
                try:
                    if (
                        getattr(self.bot, "wiki_enabled", False)
                        and getattr(self.bot, "wiki", None) is not None
                    ):
                        await self.bot.wiki.write_page(
                            wiki_page_name,
                            wiki_page_content,
                            author=agent_name,
                            source_message_id=None,
                            source="inline",
                            aliases=wiki_aliases,
                        )
                        response_text += f"\n*[Wiki: updated `{wiki_page_name}`]*"
                    else:
                        response_text += "\n*[Wiki: write skipped — wiki not configured]*"
                except Exception as exc:
                    log.error(
                        "Wiki inline write failed for page %s: %s", wiki_page_name, exc
                    )
                    response_text += (
                        f"\n*[Wiki: write failed for `{wiki_page_name}` — {exc}]*"
                    )

        # WIKI-PRIVATE — writes to private wiki tier (local agent only)
        if agent_name == LOCAL_AGENT_NAME:
            private_wiki_blocks = list(re.finditer(
                r"<!--\s*WIKI-PRIVATE:\s*(\S+)\s*-->(.*?)<!--\s*/WIKI-PRIVATE\s*-->",
                response_text,
                re.DOTALL | re.IGNORECASE,
            ))
            if private_wiki_blocks:
                response_text = re.sub(
                    r"\s*<!--\s*WIKI-PRIVATE:\s*\S+\s*-->.*?<!--\s*/WIKI-PRIVATE\s*-->\s*",
                    "",
                    response_text,
                    flags=re.DOTALL | re.IGNORECASE,
                ).strip()
                for pw_match in private_wiki_blocks:
                    raw_page_name = pw_match.group(1).strip()
                    pw_page_name = raw_page_name.lower()
                    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*[a-z0-9]", pw_page_name):
                        log.warning(
                            "wiki-private: rejected invalid page name: %r", raw_page_name
                        )
                        response_text += (
                            f"\n*[Private wiki: rejected invalid page name "
                            f"`{raw_page_name[:40]}`]*"
                        )
                        continue
                    pw_content = pw_match.group(2).strip()
                    pw_aliases: list[str] = []
                    alias_line = re.match(
                        r"^ALIASES:\s*(.+)$", pw_content, re.MULTILINE
                    )
                    if alias_line:
                        pw_aliases = [a.strip() for a in alias_line.group(1).split(",")]
                        pw_content = pw_content[alias_line.end():].lstrip("\n")
                    try:
                        if (
                            getattr(self.bot, "wiki_enabled", False)
                            and getattr(self.bot, "wiki", None) is not None
                        ):
                            await self.bot.wiki.write_private_draft(
                                pw_page_name,
                                pw_content,
                                author=LOCAL_AGENT_NAME,
                                aliases=pw_aliases,
                            )
                            private_wiki_pages.append(pw_page_name)
                            response_text += (
                                f"\n*[Private wiki: `{pw_page_name}` saved as draft]*"
                            )
                        else:
                            response_text += (
                                "\n*[Private wiki: write skipped — wiki not configured]*"
                            )
                    except Exception as exc:
                        log.error(
                            "Wiki-private draft write failed for page %s: %s",
                            pw_page_name, exc,
                        )
                        response_text += (
                            f"\n*[Private wiki: write failed for `{pw_page_name}` — {exc}]*"
                        )

        # RESEARCH — triggers researcher agent follow-up
        if agent_name != "researcher":
            research_blocks = list(re.finditer(
                r"<!--\s*RESEARCH:\s*(.*?)\s*-->",
                response_text,
                re.IGNORECASE,
            ))
            if research_blocks:
                response_text = re.sub(
                    r"\s*<!--\s*RESEARCH:\s*.*?-->\s*",
                    "",
                    response_text,
                    flags=re.IGNORECASE,
                ).strip()
                research_queries = [
                    m.group(1).strip() for m in research_blocks
                    if m.group(1).strip()
                ]

        # Scan for leaked secrets before posting
        response_text = agents_facade.scan_output(response_text)

        # Extract handoff commands from the response
        handoff_agents, clean_response = self._extract_handoffs(response_text, agent_name)

        await self.bot.db.save_message(thread_id, "assistant", f"[{agent_name}]: {clean_response}")
        await self._finish_with_placeholder(
            channel, agent_name, placeholder_msg, clean_response
        )
        placeholder_msg = None

        # Send Promote / Reject buttons for each private wiki draft written this turn.
        wiki = getattr(self.bot, "wiki", None)
        for pw_page in private_wiki_pages:
            view = agents_facade.PrivateWikiPromoteView(
                page_name=pw_page, wiki=wiki, author_id=setup.user_id
            )
            await channel.send(
                f"*Promote private draft `{pw_page}` to published?*", view=view
            )

        if handoff_agents:
            targets = ", ".join(self._agent_label(t) for t, _ in handoff_agents)
            await channel.send(
                f"*{self._agent_label(agent_name)} → {targets}*"
            )

        await self.bot.db.update_job(
            invoke.job_id,
            "completed",
            tokens_input=metadata.get("tokens_input"),
            tokens_output=metadata.get("tokens_output"),
            tokens_cache_read=metadata.get("tokens_cache_read"),
            cost_usd=metadata.get("cost_usd"),
        )

        # Context window warning for local agents
        if agent_name == LOCAL_AGENT_NAME:
            ctx_window = self.bot.agent_configs.get(
                LOCAL_AGENT_NAME, {}
            ).get("context_window", 32768)
            prompt_tokens = metadata.get("tokens_input") or 0
            if prompt_tokens and (prompt_tokens / ctx_window) > 0.85:
                await self.bot._post_to_alerts(
                    f"Local agent context at {prompt_tokens / ctx_window:.1%} "
                    f"({prompt_tokens:,}/{ctx_window:,} tokens) — approaching limit"
                )

        await self.bot.db.audit(
            f"{agent_name}_response",
            f"thread={thread_id} chars={len(clean_response)}",
        )

        return _AgentResponseResult(
            success=True,
            job_id=invoke.job_id,
            prompt=prompt,
            work_dir=setup.work_dir,
            clean_response=clean_response,
            handoff_agents=handoff_agents,
            research_queries=research_queries,
        )

    async def _stage_follow_up(
        self,
        setup: _AgentRequestSetup,
        response: _AgentResponseResult,
        *,
        agents_facade,
    ) -> None:
        """Execute failure fallbacks and success follow-ups outside the agent lock."""
        # Rate-limit fallback: retry with the fallback agent
        if response.rate_limit_fallback:
            await self.handle_agent_request(
                agent_name=response.rate_limit_fallback,
                prompt=response.prompt,
                thread_id=setup.thread_id,
                channel=setup.channel,
                user_id=setup.user_id,
                depth=setup.depth,
                source_agent=setup.agent_name,
                work_dir=response.work_dir,
            )
            return

        if not response.success:
            return

        channel = setup.channel
        agent_name = setup.agent_name

        # Process handoffs
        for target_agent, handoff_prompt in response.handoff_agents:
            channel_id = resolve_channel_id(channel)
            target_chs = self.bot.agent_channels.get(target_agent, set())
            if should_respond(channel_id, target_chs):
                log.info(
                    "Handoff: %s → %s (depth %d)", agent_name, target_agent, setup.depth + 1
                )
                if self.bot.handoffs_channel_id:
                    handoffs_channel = self.bot.get_channel(self.bot.handoffs_channel_id)
                    if handoffs_channel:
                        preview = (
                            handoff_prompt[:200] + "..."
                            if len(handoff_prompt) > 200
                            else handoff_prompt
                        )
                        await handoffs_channel.send(
                            f"**{self._agent_label(agent_name)} → {self._agent_label(target_agent)}**"
                            f" (depth {setup.depth + 1})\n> {preview}"
                        )
                await self.handle_agent_request(
                    agent_name=target_agent,
                    prompt=handoff_prompt,
                    thread_id=setup.thread_id,
                    channel=channel,
                    user_id=setup.user_id,
                    depth=setup.depth + 1,
                    source_agent=agent_name,
                )

        # Trigger researcher agent for any RESEARCH tags
        for query in response.research_queries:
            await self._handle_research(channel, query, agent_name)
