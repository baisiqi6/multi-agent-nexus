"""Agent commands — !bang dispatch, @role routing, webhook identity, handoffs.

This cog handles all agent interactions:
  - !claude / !c  → Claude Code CLI
  - !codex / !g   → Codex CLI
  - !mac-openclaw / !local-agent / !m  → Local LLM via OpenClaw or LocalLLMAgent
  - !all / !a     → Broadcasts to all agents
  - @AgentRole    → Discord role mention routing

Processed tags (stripped before Discord output):
  <!-- SCRATCH -->...</>        — agent working memory (per-thread)
  <!-- DISCOVERY: ... -->       — posts to #discoveries channel
  <!-- WIKI: name -->...</>     — writes to shared wiki
  <!-- WIKI-PRIVATE: name -->...</> — writes to private wiki tier (local agent only)
  <!-- RESEARCH: query -->      — triggers researcher agent follow-up
  @AgentName ...               — handoff to another agent
"""

import asyncio
import json
import logging
import re
import time

import discord
from discord.ext import commands

from agents.base import AgentOfflineError, AgentRateLimitError, AgentTimeoutError
from routing.dispatcher import (
    ALL_AGENTS, parse_commands, parse_sectioned_commands, split_stages,
    resolve_channel_id, should_respond, expand_list_reference,
)
from security.filter import scan_output
from utils.attachments import ProcessedAttachments, process_attachments
from utils.chunker import chunk_message
from utils.confirm import PrivateWikiPromoteView
from utils.log import clear_correlation, set_correlation
from .agent_request import (
    AgentRequestMixin,
    LEGACY_LOCAL_AGENT_NAME,
    LOCAL_AGENT_NAME,
    LOCAL_AGENT_NAMES,
    _format_memory_block,
    _is_local_agent_name,
    build_discord_context,
)

log = logging.getLogger("multinexus")


class Agents(AgentRequestMixin, commands.Cog):
    """Agent interaction: direct chat, handoffs, webhook identity."""

    MAX_HANDOFF_DEPTH = 4

    # Matches both legacy !bang and new @Agent handoff lines in agent responses
    _HANDOFF_RE = re.compile(
        r"^(?:!(?:mac-openclaw|local-agent|m|小龙虾|openclaw|龙虾|claude|c|codex|g)|@\S+)\s*(.*)",
        re.IGNORECASE | re.MULTILINE,
    )

    # Maps @AgentName text to internal agent name
    _MENTION_AGENT_MAP = {
        "mac-openclaw": LOCAL_AGENT_NAME,
        "local-agent": LOCAL_AGENT_NAME,
        "小龙虾": LOCAL_AGENT_NAME,
        "openclaw": LOCAL_AGENT_NAME,
        "龙虾": LOCAL_AGENT_NAME,
        "claude": "claude",
        "codex": "codex",
    }

    def _strip_history_timestamps(self, rows: list[dict]) -> list[dict]:
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def _history_chars(self, rows: list[dict]) -> int:
        return sum(len(row.get("content", "")) for row in rows)

    def _trim_history_to_budget(self, rows: list[dict], budget_chars: int) -> list[dict]:
        trimmed = []
        total = 0
        for row in reversed(rows):
            content = row.get("content", "")
            msg_chars = len(content)
            if trimmed and total + msg_chars > budget_chars:
                break
            trimmed.append(row)
            total += msg_chars
        trimmed.reverse()
        return self._strip_history_timestamps(trimmed)

    def _format_history_block(self, history: list[dict]) -> str:
        parts = ["[Discord Conversation Context]"]
        for msg in history:
            parts.append(f"{msg['role'].upper()}: {msg['content']}")
        return "\n".join(parts)

    async def _compact_history(
        self,
        thread_id: str,
        existing_summary: str,
        old_rows: list[dict],
        summary_budget_chars: int,
    ) -> str | None:
        """Use the local OpenClaw agent to compact older Discord history."""
        summary_agent = self.bot.agents.get(LOCAL_AGENT_NAME)
        if summary_agent is None:
            return None

        old_text = self._format_history_block(self._strip_history_timestamps(old_rows))
        prompt = (
            "Summarize this Discord multi-agent conversation context for future "
            "Claude, Codex, and local agents.\n\n"
            "Keep durable facts, decisions, open tasks, user preferences, names, IDs, "
            "important constraints, and unresolved questions. Drop greetings, filler, "
            "duplicate logs, and step-by-step tool chatter. Do not answer the user. "
            f"Return a compact summary under {summary_budget_chars} characters.\n\n"
        )
        if existing_summary:
            prompt += f"Existing summary to update:\n{existing_summary}\n\n"
        prompt += f"Messages to compact:\n{old_text}"

        try:
            try:
                result = await summary_agent.call(
                    [{"role": "user", "content": prompt}],
                    "You are a precise conversation context compactor.",
                    session_id=f"multinexus-context:{thread_id}",
                )
            except TypeError:
                result = await summary_agent.call(
                    [{"role": "user", "content": prompt}],
                    "You are a precise conversation context compactor.",
                )
        except Exception:
            log.warning("context: compaction failed for thread=%s", thread_id, exc_info=True)
            return None

        summary_text = result[0] if isinstance(result, tuple) else result
        summary_text = (summary_text or "").strip()
        if not summary_text:
            return None
        if len(summary_text) > summary_budget_chars:
            summary_text = summary_text[:summary_budget_chars].rstrip()
        return summary_text

    async def _get_managed_history(self, thread_id: str, budget_chars: int) -> list[dict]:
        conv_cfg = self.bot.conv_config or {}
        if not conv_cfg.get("managed_context_enabled", False):
            return await self.bot.db.get_history(thread_id, budget_chars)

        ttl_hours = float(conv_cfg.get("context_ttl_hours", 24))
        ttl_seconds = max(ttl_hours, 0.1) * 3600
        summary_budget_chars = int(conv_cfg.get("summary_budget_chars", 4000))
        recent_budget_chars = int(conv_cfg.get("recent_budget_chars", budget_chars))
        compact_threshold_chars = int(conv_cfg.get("compact_threshold_chars", budget_chars))

        since_ts = time.time() - ttl_seconds
        rows = await self.bot.db.get_history_since(thread_id, since_ts)
        stored_summary = await self.bot.db.get_conversation_summary(thread_id)
        summary_text = (stored_summary or {}).get("content", "") or ""
        covered_until = float((stored_summary or {}).get("covered_until", 0) or 0)

        uncompacted_rows = [row for row in rows if row["timestamp"] > covered_until]
        summary_row = (
            {
                "role": "assistant",
                "content": "[Compacted Discord conversation summary]\n" + summary_text,
                "timestamp": covered_until,
            }
            if summary_text
            else None
        )
        candidate_rows = ([summary_row] if summary_row else []) + uncompacted_rows

        if self._history_chars(candidate_rows) <= min(budget_chars, compact_threshold_chars):
            return self._trim_history_to_budget(candidate_rows, budget_chars)

        recent_rows = []
        recent_chars = 0
        for row in reversed(uncompacted_rows):
            msg_chars = len(row.get("content", ""))
            if recent_rows and recent_chars + msg_chars > recent_budget_chars:
                break
            recent_rows.append(row)
            recent_chars += msg_chars
        recent_rows.reverse()

        old_count = max(len(uncompacted_rows) - len(recent_rows), 0)
        old_rows = uncompacted_rows[:old_count]
        if old_rows:
            new_summary = await self._compact_history(
                thread_id, summary_text, old_rows, summary_budget_chars
            )
            if new_summary:
                summary_text = new_summary
                covered_until = old_rows[-1]["timestamp"]
                await self.bot.db.upsert_conversation_summary(
                    thread_id, summary_text, covered_until
                )
                summary_row = {
                    "role": "assistant",
                    "content": "[Compacted Discord conversation summary]\n" + summary_text,
                    "timestamp": covered_until,
                }
            else:
                return await self.bot.db.get_history(thread_id, budget_chars)

        final_rows = ([summary_row] if summary_row else []) + recent_rows
        return self._trim_history_to_budget(final_rows, budget_chars)

    def __init__(self, bot):
        self.bot = bot
        # channel_id (str) → agent currently running in that channel
        self._active_agents: dict[str, object] = {}

    def _agent_label(self, agent_name: str) -> str:
        return self.bot.agent_configs.get(agent_name, {}).get(
            "display_name", agent_name.capitalize()
        )

    # --- list-reference expansion ---

    async def _expand_list_refs(
        self,
        stages: list[list[tuple[str, str]]],
        thread_id: str,
        channel,
    ) -> list[list[tuple[str, str]]] | None:
        """Expand shorthand list references (e.g. 'do (1)') in all stages.

        Returns expanded stages, or None if any reference can't be resolved
        (in which case an error has already been sent to the channel).
        """
        prior_msg = await self.bot.db.get_last_assistant_message(thread_id)
        expanded: list[list[tuple[str, str]]] = []
        for stage in stages:
            expanded_stage: list[tuple[str, str]] = []
            for agent_name, prompt in stage:
                new_prompt, error = expand_list_reference(prompt, prior_msg)
                if error:
                    await channel.send(f"⚠️ {error}")
                    return None
                expanded_stage.append((agent_name, new_prompt))
            expanded.append(expanded_stage)
        return expanded

    # --- workspace / session helpers ---

    # Keys used to store CLI session IDs in workspace JSON, keyed by agent name.
    _SESSION_KEY = {
        "codex": "codex_session_id",
        "claude": "session_id",
    }

    def _parse_workspace(self, workspace: str, agent_name: str) -> tuple[str | None, dict | None]:
        """Return stored session id plus parsed workspace dict when possible."""
        if not workspace:
            return None, None
        try:
            data = json.loads(workspace)
        except (TypeError, json.JSONDecodeError):
            return None, None
        if not isinstance(data, dict):
            return None, None
        key = self._SESSION_KEY.get(agent_name)
        session_id = data.get(key) if key else None
        if not isinstance(session_id, str) or not session_id.strip():
            session_id = None
        return session_id, data

    def _workspace_without_session(self, workspace: str, agent_name: str) -> str:
        """Strip internal session state before injecting workspace into prompts."""
        _, data = self._parse_workspace(workspace, agent_name)
        if data is None:
            return workspace
        key = self._SESSION_KEY.get(agent_name)
        prompt_data = {k: v for k, v in data.items() if k != key}
        return json.dumps(prompt_data) if prompt_data else ""

    def _workspace_with_session(self, workspace: str, agent_name: str, session_id: str) -> str:
        """Merge a session id into the workspace JSON object."""
        _, data = self._parse_workspace(workspace, agent_name)
        merged = dict(data) if data is not None else {}
        key = self._SESSION_KEY.get(agent_name)
        if key:
            merged[key] = session_id
        return json.dumps(merged)

    # Legacy aliases — scratch processing still calls these for Codex
    def _parse_codex_workspace(self, workspace: str) -> tuple[str | None, dict | None]:
        return self._parse_workspace(workspace, "codex")

    def _workspace_without_codex_session(self, workspace: str) -> str:
        return self._workspace_without_session(workspace, "codex")

    def _workspace_with_codex_session(self, workspace: str, session_id: str) -> str:
        return self._workspace_with_session(workspace, "codex", session_id)

    async def dispatch_agents(self, message: discord.Message) -> bool:
        """Handle agent @role mentions and !bang prefix dispatch.

        Returns True if any agent was dispatched (consumed the message).
        """
        # Process attachments once — shared across all routing paths below.
        _attachments: ProcessedAttachments | None = None
        if message.attachments:
            _attachments = await process_attachments(
                message, self.bot.attachments_temp_dir
            )

        # --- @team → all agents in parallel ---
        team_role_id = getattr(self.bot, "_team_role_id", None)
        if team_role_id and message.role_mentions:
            if any(r.id == team_role_id for r in message.role_mentions):
                content = message.content
                for role in message.role_mentions:
                    content = content.replace(role.mention, "")
                prompt = content.strip()
                if _attachments and _attachments.text_block:
                    prompt = (prompt + "\n\n" + _attachments.text_block).strip()
                if not prompt:
                    await message.channel.send("用法：@team <你的问题>")
                    return True
                channel_id = resolve_channel_id(message.channel)
                active_agents = [
                    a for a in ALL_AGENTS
                    if should_respond(channel_id, self.bot.agent_channels.get(a, set()))
                ]
                if active_agents:
                    thread_id = str(message.channel.id)
                    await asyncio.gather(*[
                        self.handle_agent_request(
                            agent_name=agent_name,
                            prompt=prompt,
                            thread_id=thread_id,
                            channel=message.channel,
                            user_id=message.author.id,
                            attachments=_attachments,
                        )
                        for agent_name in active_agents
                    ])
                return True

        # --- @role mention routing ---
        agent_role_ids = getattr(self.bot, "_agent_role_ids", {})
        if agent_role_ids and message.role_mentions:
            # Build mention_string -> agent_name map for matched roles
            mention_to_agent: dict[str, str] = {}
            for agent_name, role_id in agent_role_ids.items():
                for role_mention in message.role_mentions:
                    if role_mention.id == role_id:
                        mention_to_agent[role_mention.mention] = agent_name
                        break
            if mention_to_agent:
                content = message.content

                def _parse_role_chunk(chunk: str) -> list[tuple[str, str]]:
                    """Parse a single chunk for role-mention sections."""
                    hits: list[tuple[int, int, str]] = []
                    for mention_str, agent_name in mention_to_agent.items():
                        idx = chunk.find(mention_str)
                        if idx >= 0:
                            hits.append((idx, idx + len(mention_str), agent_name))
                    if not hits:
                        return []
                    hits.sort(key=lambda h: h[0])
                    sections: list[tuple[str, str]] = []
                    for i, (start, end, agent_name) in enumerate(hits):
                        text_end = hits[i + 1][0] if i + 1 < len(hits) else len(chunk)
                        section_text = chunk[end:text_end].strip()
                        if section_text:
                            sections.append((agent_name, section_text))
                    return sections

                # Split on barrier keywords (THEN, AFTER, etc.), then parse each chunk.
                raw_stages = split_stages(content)
                role_stages: list[list[tuple[str, str]]] = []
                for chunk in raw_stages:
                    sections = _parse_role_chunk(chunk)
                    if sections:
                        role_stages.append(sections)

                if not role_stages:
                    names = " / ".join(
                        f"@{self._agent_label(a)}" for a in mention_to_agent.values()
                    )
                    await message.channel.send(f"用法：{names} <你的问题>")
                    return True

                channel_id = resolve_channel_id(message.channel)
                thread_id = str(message.channel.id)

                # Expand shorthand list references before dispatch.
                role_stages = await self._expand_list_refs(role_stages, thread_id, message.channel)
                if role_stages is None:
                    return True

                # Save full user message once.
                all_prompts = [p for stage in role_stages for _, p in stage]
                await self.bot.db.save_message(
                    thread_id, "user", "\n\n".join(all_prompts),
                    author_id=str(message.author.id),
                    message_id=str(message.id),
                )

                # Run stages sequentially; agents within a stage in parallel.
                for stage in role_stages:
                    if _attachments and _attachments.text_block:
                        stage = [
                            (a, (p + "\n\n" + _attachments.text_block).strip())
                            for a, p in stage
                        ]
                    dispatch_list: list[tuple[str, str]] = []
                    inactive: list[str] = []
                    for agent_name, prompt in stage:
                        if should_respond(channel_id, self.bot.agent_channels.get(agent_name, set())):
                            dispatch_list.append((agent_name, prompt))
                        else:
                            inactive.append(agent_name)
                    if inactive:
                        names = ", ".join(self._agent_label(a) for a in inactive)
                        await message.channel.send(f"{names} 在当前频道未激活。")
                    if dispatch_list:
                        await asyncio.gather(*[
                            self.handle_agent_request(
                                agent_name=agent_name,
                                prompt=agent_prompt,
                                thread_id=thread_id,
                                channel=message.channel,
                                user_id=message.author.id,
                                origin_already_persisted=True,
                                attachments=_attachments,
                            )
                            for agent_name, agent_prompt in dispatch_list
                        ])
                return True

        # --- bang command routing ---
        stages = parse_sectioned_commands(message.content)
        if not stages:
            return False

        channel_id = resolve_channel_id(message.channel)
        thread_id = str(message.channel.id)

        # Expand shorthand list references (e.g. "do (1)") before dispatch.
        stages = await self._expand_list_refs(stages, thread_id, message.channel)
        if stages is None:
            return True  # error already sent

        # Save the full user message once before any dispatch.
        all_prompts = [p for stage in stages for _, p in stage]
        await self.bot.db.save_message(
            thread_id, "user", "\n\n".join(all_prompts),
            author_id=str(message.author.id),
            message_id=str(message.id),
        )

        # Run stages sequentially; agents within a stage run in parallel.
        for stage in stages:
            # Expand __all__ into broadcast list
            if stage[0][0] == "__all__":
                broadcast_prompt = stage[0][1]
                if _attachments and _attachments.text_block:
                    broadcast_prompt = (broadcast_prompt + "\n\n" + _attachments.text_block).strip()
                stage = [(a, broadcast_prompt) for a in ALL_AGENTS]

            # Append attachment text to each section's prompt
            if _attachments and _attachments.text_block:
                stage = [
                    (a, (p + "\n\n" + _attachments.text_block).strip())
                    for a, p in stage
                ]

            dispatch_list: list[tuple[str, str]] = []
            inactive_agents = []
            for agent_name, prompt in stage:
                agent_chs = self.bot.agent_channels.get(agent_name, set())
                if should_respond(channel_id, agent_chs):
                    dispatch_list.append((agent_name, prompt))
                else:
                    inactive_agents.append(agent_name)

            if inactive_agents:
                names = ", ".join(self._agent_label(a) for a in inactive_agents)
                await message.channel.send(f"{names} 在当前频道未激活。")

            if not dispatch_list:
                continue

            await asyncio.gather(*[
                self.handle_agent_request(
                    agent_name=agent_name,
                    prompt=agent_prompt,
                    thread_id=thread_id,
                    channel=message.channel,
                    user_id=message.author.id,
                    origin_already_persisted=True,
                    attachments=_attachments,
                )
                for agent_name, agent_prompt in dispatch_list
            ])
        return True

    def _resolve_work_dir(self, prompt: str, channel) -> tuple[str, str | None]:
        """Strip --project flag from prompt and return (cleaned_prompt, work_dir).

        Resolution order:
          1. --project <name> flag in prompt (stripped before forwarding to agent)
          2. channel_projects config mapping for the current channel
          3. None (agent uses no CWD override)

        Hook point: customize project resolution logic here if needed.
        """
        projects = getattr(self.bot, "_projects", {})
        channel_projects = getattr(self.bot, "_channel_projects", {})

        proj_match = re.search(r"--project\s+(\S+)", prompt)
        if proj_match:
            project_name = proj_match.group(1)
            prompt = re.sub(r"\s*--project\s+\S+", "", prompt).strip()
        else:
            channel_id_str = str(resolve_channel_id(channel))
            project_name = channel_projects.get(channel_id_str)

        work_dir = projects.get(project_name, {}).get("path") if project_name else None
        return prompt, work_dir

    def _extract_handoffs(
        self,
        response: str,
        source_agent: str,
    ) -> tuple[list[tuple[str, str]], str]:
        """Extract handoff commands from an agent's response.

        Supports two formats:
          @Claude <prompt>   — @mention format (preferred, per system prompt)
          !c <prompt>        — legacy !bang format
        """
        handoffs = []
        lines = response.split("\n")
        clean_lines = []

        _at_mention_re = re.compile(r"^@([^\s]+)\s*(.*)")

        for line in lines:
            stripped = line.strip()
            match = self._HANDOFF_RE.match(stripped)
            if match:
                at_match = _at_mention_re.match(stripped)
                if at_match:
                    mention_name = at_match.group(1).lower()
                    agent_name = self._MENTION_AGENT_MAP.get(mention_name)
                    prompt = at_match.group(2).strip()
                    if agent_name and agent_name != source_agent and prompt:
                        handoffs.append((agent_name, prompt))
                        continue
                    clean_lines.append(line)
                    continue
                # Legacy !bang format
                agents, prompt = parse_commands(stripped)
                agents = [agent for agent in agents if agent != source_agent]
                if agents and prompt:
                    for agent in agents:
                        handoffs.append((agent, prompt))
                    continue
            clean_lines.append(line)

        cleaned = "\n".join(clean_lines).strip()
        return handoffs, cleaned

    async def _handle_research(
        self, channel, query: str, requesting_agent: str
    ) -> None:
        """Call the researcher agent for a RESEARCH tag query and post the result."""
        researcher = self.bot.agents.get("researcher")
        if not researcher:
            log.warning(
                "RESEARCH tag from %s but no researcher agent configured", requesting_agent
            )
            return
        log.info("Researcher query from %s: %r", requesting_agent, query[:100])
        placeholder = await self._start_placeholder(channel, "researcher")
        try:
            raw_result, _ = await researcher.call(
                [{"role": "user", "content": query}], ""
            )
            response = f"**Research:** {scan_output(query)}\n\n{raw_result}"
        except Exception as e:
            log.warning("Researcher call failed for query %r: %s", query, e)
            response = f"*Research failed for '{query[:100]}': {e}*"
        await self._finish_with_placeholder(channel, "researcher", placeholder, response)

    async def _process_scratch(
        self, thread_id: str, agent_name: str, scratch_raw: str
    ):
        """Validate and store agent scratch zone content.

        Scratch is a small JSON object agents use for working memory across turns.
        It is validated strictly: only allowed keys, no instruction-like phrases,
        max 800 chars.
        """
        allowed_keys = {"files_touched", "decisions", "next_step"}
        instruction_phrases = ("always", "never", "from now on")

        try:
            scratch_data = json.loads(scratch_raw)
        except json.JSONDecodeError:
            log.warning(
                "Scratch zone invalid JSON — discarding (thread=%s, agent=%s)",
                thread_id, agent_name,
            )
            return

        if not isinstance(scratch_data, dict):
            log.warning("Scratch zone not a JSON object — discarding")
            return

        extra_keys = set(scratch_data.keys()) - allowed_keys
        if extra_keys:
            log.warning("Scratch zone has disallowed keys %s — discarding", extra_keys)
            return

        scratch_str = json.dumps(scratch_data)
        if any(phrase in scratch_str.lower() for phrase in instruction_phrases):
            log.warning(
                "Scratch zone contains instruction-like content — discarding "
                "(thread=%s, agent=%s)", thread_id, agent_name,
            )
            return

        if len(scratch_str) > 800:
            log.warning(
                "Scratch zone exceeds 800 chars (%d) — discarding", len(scratch_str)
            )
            return

        await self.bot.db.upsert_workspace(thread_id, agent_name, scratch_str)
        log.info(
            "Scratch stored (thread=%s, agent=%s, chars=%d)",
            thread_id, agent_name, len(scratch_str),
        )

    async def _start_placeholder(
        self, channel, agent_name: str
    ) -> "discord.WebhookMessage | None":
        """Send a 'thinking...' placeholder via webhook. Returns the message for later editing."""
        try:
            webhook = await self._get_webhook(channel, agent_name)
            display_name = self.bot.agent_configs.get(agent_name, {}).get(
                "display_name", agent_name.capitalize()
            )
            avatar_url = self.bot.agent_configs.get(agent_name, {}).get("avatar_url") or None
            return await webhook.send(
                content="🔄 thinking...",
                username=display_name,
                avatar_url=avatar_url,
                wait=True,
                **self._thread_kwargs(channel),
            )
        except Exception:
            log.debug(
                "Could not send placeholder for %s — will send response normally", agent_name
            )
            return None

    async def _finish_with_placeholder(
        self,
        channel,
        agent_name: str,
        placeholder_msg: "discord.WebhookMessage | None",
        text: str,
    ):
        """Send final response, editing the placeholder if available."""
        chunks = list(chunk_message(text))
        if not chunks:
            return

        webhook = await self._get_webhook(channel, agent_name)
        display_name = self.bot.agent_configs.get(agent_name, {}).get(
            "display_name", agent_name.capitalize()
        )
        avatar_url = self.bot.agent_configs.get(agent_name, {}).get("avatar_url") or None
        thread_kw = self._thread_kwargs(channel)

        first_chunk, *rest_chunks = chunks

        if placeholder_msg is not None:
            try:
                await placeholder_msg.edit(content=first_chunk)
            except discord.HTTPException:
                await webhook.send(
                    content=first_chunk, username=display_name, avatar_url=avatar_url, **thread_kw
                )
        else:
            await webhook.send(
                content=first_chunk, username=display_name, avatar_url=avatar_url, **thread_kw
            )

        for chunk in rest_chunks:
            await webhook.send(content=chunk, username=display_name, avatar_url=avatar_url, **thread_kw)

    @staticmethod
    def _thread_kwargs(channel) -> dict:
        """Return {'thread': channel} for Discord threads; {} for regular channels.

        Webhook posts to a thread require this kwarg — without it the message
        goes to the parent channel instead of the thread.
        """
        return {"thread": channel} if isinstance(channel, discord.Thread) else {}

    async def _get_webhook(self, channel, agent_name: str) -> discord.Webhook:
        """Get or create a webhook for an agent in a channel.

        Threads don't own webhooks — the webhook lives on the parent channel
        and messages are routed into the thread via the 'thread' kwarg on send().
        """
        webhook_channel = channel.parent if isinstance(channel, discord.Thread) else channel
        key = (webhook_channel.id, agent_name)
        if key in self.bot._webhooks:
            return self.bot._webhooks[key]

        display_name = self.bot.agent_configs.get(agent_name, {}).get(
            "display_name", agent_name.capitalize()
        )
        webhooks = await webhook_channel.webhooks()
        for webhook in webhooks:
            if webhook.name == display_name:
                self.bot._webhooks[key] = webhook
                return webhook

        webhook = await webhook_channel.create_webhook(name=display_name)
        self.bot._webhooks[key] = webhook
        log.info("Created %s webhook in #%s", display_name, webhook_channel.name)
        return webhook

    async def _send_as_agent(self, channel, agent_name: str, text: str):
        """Send a message as an agent via webhook."""
        webhook = await self._get_webhook(channel, agent_name)
        display_name = self.bot.agent_configs.get(agent_name, {}).get(
            "display_name", agent_name.capitalize()
        )
        avatar_url = self.bot.agent_configs.get(agent_name, {}).get("avatar_url") or None
        thread_kw = self._thread_kwargs(channel)

        for chunk in chunk_message(text):
            await webhook.send(
                content=chunk,
                username=display_name,
                avatar_url=avatar_url,
                **thread_kw,
            )


async def setup(bot):
    cog = Agents(bot)
    await bot.add_cog(cog)
    # Expose handle_agent_request on the bot for use by other cogs and slash commands
    bot.handle_agent_request = cog.handle_agent_request
    bot._send_as_agent = cog._send_as_agent
