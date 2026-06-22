"""Core agent request orchestration used by the Discord Agents cog."""
from __future__ import annotations

import logging
import re
import time

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

        This is the central dispatch point. It:
          1. Resolves the work directory (--project flag or channel mapping)
          2. Loads conversation history from DB
          3. Fetches wiki context
          4. Calls the agent backend
          5. Processes special tags (SCRATCH, DISCOVERY, WIKI, WIKI-PRIVATE, RESEARCH)
          6. Handles handoffs to other agents
          7. Triggers researcher follow-ups
        """
        from cogs import agents as agents_facade

        agents_facade.set_correlation(agent=agent_name, channel=str(channel.id))

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
            return

        if not self.bot.allowlist.is_allowed(user_id):
            await channel.send(
                f"You're not authorized to use {self._agent_label(agent_name)}."
            )
            return

        agent = self.bot.agents.get(agent_name)
        if not agent:
            await channel.send(f"Unknown agent: {agent_name}")
            return

        agent_config = self.bot.agent_configs.get(agent_name, {})
        handoff_agents = []
        rate_limit_fallback: str | None = None
        placeholder_msg: discord.WebhookMessage | None = None
        last_chunk_edit: float = 0.0
        last_streamed_text: str = ""  # last text seen by on_chunk — fallback save on interruption
        research_queries: list[str] = []
        private_wiki_pages: list[str] = []  # pages written as drafts — get promote buttons

        lock = self.bot._get_lock(f"{thread_id}:{agent_name}")
        async with lock:
            if depth == 0 and not origin_already_persisted:
                await self.bot.db.save_message(
                    thread_id, "user", prompt,
                    author_id=str(user_id),
                    message_id=message_id,
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
            _is_local = agents_facade._is_local_agent_name(agent_name) or (
                agent_config.get("inference_backend") in {"local", "openclaw"}
            )
            memory_block = ""
            if agent_name != "researcher":
                shared_memories = await self.bot.db.get_memories(limit=10)
                if shared_memories:
                    memory_block = agents_facade._format_memory_block(shared_memories)
                if _is_local and getattr(self.bot, "private_db", None) is not None:
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
                preview = text[:1990] + "\u2026" if len(text) > 1990 else text
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
                                include_private=_is_local,
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
                        if agent_name == "codex" and activity_timeout_override:
                            call_kwargs["activity_timeout"] = activity_timeout_override
                        call_timeout = agent_config.get("timeout_extended") if use_extended_timeout else None

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
                                resume_kwargs = {"work_dir": work_dir, "timeout": call_timeout, "on_chunk": _on_chunk}
                                if agent_name == "codex" and activity_timeout_override:
                                    resume_kwargs["activity_timeout"] = activity_timeout_override
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
                                    mission=mission, workspace=workspace_for_prompt, work_dir=work_dir,
                                    timeout=call_timeout,
                                    **call_kwargs,
                                )
                        else:
                            result = await agent.call(
                                history, system_prompt,
                                mission=mission, workspace=workspace_for_prompt, work_dir=work_dir,
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
                        page_name=pw_page, wiki=wiki, author_id=user_id
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
                    job_id,
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
                return

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
                return

        # Rate-limit fallback: retry with the fallback agent
        if rate_limit_fallback:
            await self.handle_agent_request(
                agent_name=rate_limit_fallback,
                prompt=prompt,
                thread_id=thread_id,
                channel=channel,
                user_id=user_id,
                depth=depth,
                source_agent=agent_name,
                work_dir=work_dir,
            )
            return

        # Process handoffs
        for target_agent, handoff_prompt in handoff_agents:
            channel_id = resolve_channel_id(channel)
            target_chs = self.bot.agent_channels.get(target_agent, set())
            if should_respond(channel_id, target_chs):
                log.info(
                    "Handoff: %s → %s (depth %d)", agent_name, target_agent, depth + 1
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
                            f" (depth {depth + 1})\n> {preview}"
                        )
                await self.handle_agent_request(
                    agent_name=target_agent,
                    prompt=handoff_prompt,
                    thread_id=thread_id,
                    channel=channel,
                    user_id=user_id,
                    depth=depth + 1,
                    source_agent=agent_name,
                )

        # Trigger researcher agent for any RESEARCH tags
        for query in research_queries:
            await self._handle_research(channel, query, agent_name)
