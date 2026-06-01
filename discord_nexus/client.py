"""DiscordClient: one discord.Client per agent, with two-layer message filtering."""

import asyncio
import collections.abc
import logging
import time

import discord
from discord import app_commands

from .adapters.base import AdapterResult
from .adapters.factory import make_adapter
from .config import load_config
from .context.prompt import build_agent_prompt
from .context.store import ChatContextStore
from .models import AgentConfig
from .routing.mentions import MentionRouter
from .sessions.store import SessionStore
from .sessions.scope import (
    is_thread_channel,
    legacy_scope_for_channel_id,
    scope_for_channel,
    task_scope,
)

log = logging.getLogger(__name__)

_MAX_DISCORD_MSG_LEN = 1900


from .commands import (
    can_run_operator_command,
    handle_operator_command,
    parse_operator_command,
)
from .embeds import build_agents_embed, build_health_embed, build_session_status_embed
from .handoff import split_handoff_lines
from .handoff_handler import (
    CoordinatorHandoff,
    build_agent_report,
    build_handoff_prompt,
    contains_agent_report,
    execute_assignment_accept,
    parse_coordinator_handoff,
    parse_coordinator_lifecycle,
    read_bootstrap,
)


def _chunk_message(text: str) -> list[str]:
    """Split text into Discord-sized chunks."""
    if len(text) <= _MAX_DISCORD_MSG_LEN:
        return [text] if text.strip() else []
    chunks = []
    while text:
        if len(text) <= _MAX_DISCORD_MSG_LEN:
            chunks.append(text)
            break
        # Try to break at a newline or space
        cut = text.rfind("\n", 0, _MAX_DISCORD_MSG_LEN)
        if cut < _MAX_DISCORD_MSG_LEN // 2:
            cut = text.rfind(" ", 0, _MAX_DISCORD_MSG_LEN)
        if cut < _MAX_DISCORD_MSG_LEN // 2:
            cut = _MAX_DISCORD_MSG_LEN
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n ")
    return chunks


class DiscordClient(discord.Client):
    """One agent = one DiscordClient instance."""

    def __init__(self, config: AgentConfig):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.agent_config = config
        self.adapter = make_adapter(config)
        self.context_store = ChatContextStore(config.context_db_path)
        self.session_store = SessionStore(config.context_db_path)
        self.mention_router = MentionRouter(config)
        self._bot_user_id_map: dict[str, int] = {}
        self.tree = app_commands.CommandTree(self)
        self._commands_synced = False

    async def setup_hook(self):
        self._register_slash_commands()

    async def on_ready(self):
        log.info(
            "DiscordClient ready: agent=%s bot=%s#%s",
            self.agent_config.id,
            self.user.name,
            self.user.discriminator,
        )
        # Register our own user ID
        self._bot_user_id_map[self.agent_config.id] = self.user.id
        self.mention_router.update_discord_user_ids(self._bot_user_id_map)

        # One-time guild-scoped slash command sync
        if not self._commands_synced:
            guild = None
            if self.agent_config.channels:
                ch = self.get_channel(self.agent_config.channels[0])
                if ch:
                    guild = ch.guild
            if not guild and self.guilds:
                guild = self.guilds[0]
            if guild:
                try:
                    self.tree.copy_global_to(guild=discord.Object(id=guild.id))
                    await self.tree.sync(guild=discord.Object(id=guild.id))
                    self._commands_synced = True
                    log.info("Synced slash commands to guild %s", guild.id)
                except Exception:
                    log.warning("Slash command sync failed", exc_info=True)

    def register_peer_bot(self, agent_id: str, user_id: int) -> None:
        """Called when another agent's bot comes online to build the mention map."""
        self._bot_user_id_map[agent_id] = user_id
        self.mention_router.update_discord_user_ids(self._bot_user_id_map)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # Only react to edits from OTHER bots that now contain a handoff to us
        if not after.author.bot:
            return
        if after.author.id == self.user.id:
            return
        channel_id = self._resolve_channel_id(after)
        if self.agent_config.channels and channel_id not in self.agent_config.channels:
            return
        if not self.agent_config.respond_to_bots:
            return
        addressed = self._is_addressed_to_me(after)
        handoff = self.mention_router.is_handoff_message(after.content)
        if not addressed or not handoff:
            return
        log.info(
            "[handoff-edit] agent=%s received edited handoff from=%s",
            self.agent_config.id, after.author,
        )
        self._record_message(after)
        await self._handle_request(after)

    async def on_message(self, message: discord.Message):
        # Layer 0: never respond to own messages
        if message.author.id == self.user.id:
            return

        # Layer 1: channel allowlist check (before any processing)
        channel_id = self._resolve_channel_id(message)
        if self.agent_config.channels and channel_id not in self.agent_config.channels:
            return

        # Layer 2: bot message filtering
        if message.author.bot:
            # respond_to_bots=false: ignore all bot messages entirely
            if not self.agent_config.respond_to_bots:
                return
            # respond_to_bots=true: only accept formal handoff to this agent
            addressed = self._is_addressed_to_me(message)
            handoff = self.mention_router.is_handoff_message(message.content)
            log.debug(
                "[handoff-check] agent=%s from=%s addressed=%s handoff=%s mentions=%s content=%.200s",
                self.agent_config.id, message.author, addressed, handoff,
                [u.id for u in message.mentions], message.content,
            )
            if not addressed:
                return
            if not handoff:
                return
            # Valid handoff: persist and handle
            self._record_message(message)

            # Coordinator handoff auto-accept
            if (
                self.agent_config.coordinator_bot_id
                and message.author.id == self.agent_config.coordinator_bot_id
            ):
                handled = await self._try_coordinator_lifecycle(message)
                if handled:
                    return
                handled = await self._try_coordinator_handoff(message)
                if handled:
                    return

            await self._handle_request(message)
            return

        # Layer 3: human message — must be addressed to me
        if self.agent_config.allowed_user_ids and message.author.id not in self.agent_config.allowed_user_ids:
            return
        if self._is_addressed_to_me(message):
            # Operator command interception
            prompt_text = self._get_prompt_text(message)
            op_cmd = parse_operator_command(prompt_text)
            if op_cmd:
                deny = can_run_operator_command(self.agent_config, message.author.id, op_cmd)
                if deny:
                    await message.channel.send(
                        deny,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                    return
                self._record_message(message)
                response = await handle_operator_command(
                    op_cmd,
                    self,
                    message.channel.id,
                    is_thread=is_thread_channel(message.channel),
                )
                chunks = _chunk_message(response)
                for chunk in chunks:
                    try:
                        await message.channel.send(
                            chunk,
                            allowed_mentions=discord.AllowedMentions.none(),
                        )
                    except discord.HTTPException:
                        break
                return
            self._record_message(message)
            await self._handle_request(message)
        else:
            # Not addressed to me — persist for context only
            self._record_message(message)

    def _is_addressed_to_me(self, message: discord.Message) -> bool:
        """Check if message @mentions this bot or uses a matching !bang command."""
        if self.user in message.mentions:
            return True
        return self.mention_router.matches_bang_command(message.content)

    @staticmethod
    def _resolve_channel_id(message: discord.Message) -> int:
        """For threads, return the parent channel ID; otherwise the channel ID."""
        if is_thread_channel(message.channel):
            return message.channel.parent_id
        return message.channel.id

    def _record_message(self, message: discord.Message) -> None:
        """Persist message to context store."""
        self.context_store.record_message(
            message_id=str(message.id),
            channel_id=str(self._resolve_channel_id(message)),
            author_id=str(message.author.id),
            author_name=message.author.display_name,
            author_is_bot=message.author.bot,
            content=message.content,
            created_at_ms=int(message.created_at.timestamp() * 1000),
            source="discord",
            ttl_seconds=self.agent_config.context_ttl_seconds,
        )

    async def _try_coordinator_handoff(self, message: discord.Message) -> bool:
        """Auto-accept a coordinator handoff. Returns True if handled."""
        cfg = self.agent_config
        handoff = parse_coordinator_handoff(
            message.content,
            my_discord_user_id=self.user.id,
        )
        if handoff is None:
            return False

        log.info("Coordinator handoff: task=%s agent=%s", handoff.task_id, cfg.id)
        context_channel_id = str(self._resolve_channel_id(message))
        session_scope_id = task_scope(handoff.workspace_id, handoff.task_id)

        # Execute assignment accept
        success, output = await asyncio.to_thread(
            execute_assignment_accept,
            cli_path=cfg.coordinator_cli_path,
            db_path=cfg.coordinator_db_path,
            workspace_id=handoff.workspace_id,
            task_id=handoff.task_id,
            agent_name=cfg.id,
        )

        if not success:
            error_msg = build_agent_report(
                "blocker",
                handoff,
                reason=f"assignment accept failed: {output[:500]}",
            )
            await message.channel.send(
                error_msg,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            log.error("Assignment accept failed: %s", output)
            return True

        # Read bootstrap
        bootstrap_content = None
        if handoff.bootstrap_path and cfg.coordinator_workspace_path:
            bootstrap_content = await asyncio.to_thread(
                read_bootstrap, cfg.coordinator_workspace_path, handoff.bootstrap_path,
            )

        # Build prompt and call adapter
        prompt = build_handoff_prompt(
            handoff,
            bootstrap_content,
            agent_name=cfg.id,
            accept_output=output,
        )

        # Confirm acceptance
        await message.channel.send(
            build_agent_report(
                "accept",
                handoff,
                summary=f"auto accepted by {cfg.id}",
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )

        # Call adapter with bootstrap prompt
        channel = message.channel

        placeholder = None
        try:
            placeholder = await channel.send("\U0001f504 working on task...")
        except discord.HTTPException:
            pass

        progress_state: dict = {"partial": ""}
        result = await self._run_adapter_for_scope(
            prompt,
            session_scope_id=session_scope_id,
            legacy_scope_ids=(),
            placeholder=placeholder,
            progress_state=progress_state,
        )

        # Send response
        response_text = self.mention_router.resolve_handoff_mentions(result.text)
        handoff_lines, display_text = split_handoff_lines(response_text)

        chunks = _chunk_message(display_text) if display_text else []
        if chunks:
            if placeholder:
                try:
                    await placeholder.edit(content=chunks[0])
                except discord.HTTPException:
                    await channel.send(chunks[0])
            else:
                await channel.send(chunks[0])
            for chunk in chunks[1:]:
                try:
                    await channel.send(chunk)
                except discord.HTTPException:
                    break
        elif placeholder:
            try:
                await placeholder.edit(content="✅ done")
            except discord.HTTPException:
                pass

        for hl in handoff_lines:
            try:
                await channel.send(hl)
            except discord.HTTPException:
                pass

        if not self._is_error_response(result.text):
            self.context_store.record_message(
                message_id=f"response:{int(time.time() * 1000)}:{cfg.id}",
                channel_id=context_channel_id,
                author_id=str(self.user.id),
                author_name=cfg.display_name or cfg.id,
                author_is_bot=True,
                content=response_text[:2000],
                created_at_ms=int(time.time() * 1000),
                source="discord",
                ttl_seconds=cfg.context_ttl_seconds,
            )

        await self._send_missing_report_fallback(
            channel,
            handoff,
            response_text=response_text,
            is_error=self._is_error_response(result.text),
        )
        return True

    async def _send_missing_report_fallback(
        self,
        channel,
        handoff: CoordinatorHandoff,
        *,
        response_text: str,
        is_error: bool,
    ) -> None:
        """Emit a structured report if the adapter forgot to include one."""
        if contains_agent_report(response_text):
            return
        if is_error:
            report = build_agent_report(
                "blocker",
                handoff,
                reason="adapter returned an error without a structured agent report",
            )
        else:
            report = build_agent_report(
                "progress",
                handoff,
                summary=(
                    "adapter completed without a structured agent-report; "
                    "operator should inspect the visible response"
                ),
            )
        try:
            await channel.send(
                report,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            log.warning("Failed to send missing agent-report fallback", exc_info=True)

    async def _try_coordinator_lifecycle(self, message: discord.Message) -> bool:
        """Archive local task-scoped sessions after coordinator closeout/done notices."""
        cfg = self.agent_config
        event = parse_coordinator_lifecycle(
            message.content,
            my_discord_user_id=self.user.id,
        )
        if event is None:
            return False

        archived = self.session_store.mark_task_archived(
            workspace_id=event.workspace_id,
            task_id=event.task_id,
            agent_id=cfg.id,
        )
        handoff = CoordinatorHandoff(
            workspace_id=event.workspace_id,
            task_id=event.task_id,
            bootstrap_path="",
            action=event.action,
        )
        await message.channel.send(
            build_agent_report(
                "progress",
                handoff,
                summary=(
                    f"archived {archived} task session(s) for {cfg.id} "
                    f"after {event.action}"
                ),
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        log.info(
            "Archived %s task session(s): task=%s agent=%s action=%s",
            archived, event.task_id, cfg.id, event.action,
        )
        return True

    def _get_prompt_text(self, message: discord.Message) -> str:
        """Extract the actual prompt text, stripping @mentions and !bang prefix."""
        content = message.content
        # Strip @mentions of this bot
        content = content.replace(f"<@{self.user.id}>", "").strip()
        content = content.replace(f"<@!{self.user.id}>", "").strip()
        # Strip !bang prefix if present
        if self.mention_router.matches_bang_command(content):
            content = self.mention_router.strip_bang_prefix(content)
        return content.strip()

    async def _run_with_heartbeat(self, placeholder: discord.Message | None, coro, progress_state: dict | None = None):
        """Run an async coroutine while updating a placeholder with elapsed time or partial output."""
        if placeholder is None:
            return await coro

        start = time.time()
        task = asyncio.create_task(coro)
        try:
            while not task.done():
                elapsed = int(time.time() - start)
                mins, secs = divmod(elapsed, 60)
                label = f"{mins}m{secs:02d}s" if mins else f"{secs}s"
                # If adapter has produced partial output, show it instead of just "thinking"
                partial = progress_state.get("partial", "") if progress_state else ""
                if partial:
                    preview = partial[:1800]
                    if len(partial) > 1800:
                        preview += "\n..."
                    content = f"\U0001f4dd ({label})\n{preview}"
                else:
                    content = f"\U0001f504 thinking... ({label})"
                try:
                    await placeholder.edit(content=content)
                except discord.HTTPException:
                    pass
                done, _ = await asyncio.wait({task}, timeout=15)
                if done:
                    break
            return task.result()
        except Exception:
            task.cancel()
            raise

    def _register_slash_commands(self):
        """Register /agents, /health, /session status, /session reset."""
        cfg = self.agent_config

        def _is_channel_allowed(interaction: discord.Interaction) -> bool:
            if not cfg.channels:
                return True
            ch = interaction.channel
            ch_id = ch.parent_id if is_thread_channel(ch) else ch.id
            return ch_id in cfg.channels

        @self.tree.command(name="agents", description="列出所有已知 agent")
        async def slash_agents(interaction: discord.Interaction):
            if not _is_channel_allowed(interaction):
                await interaction.response.send_message("此频道不可用。", ephemeral=True)
                return
            deny = can_run_operator_command(cfg, interaction.user.id, "agents")
            if deny:
                await interaction.response.send_message(deny, ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            embed = build_agents_embed(cfg)
            await interaction.followup.send(
                embed=embed, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True,
            )

        @self.tree.command(name="health", description="检查 adapter 健康状态")
        async def slash_health(interaction: discord.Interaction):
            if not _is_channel_allowed(interaction):
                await interaction.response.send_message("此频道不可用。", ephemeral=True)
                return
            deny = can_run_operator_command(cfg, interaction.user.id, "health")
            if deny:
                await interaction.response.send_message(deny, ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                health = await self.adapter.health_check()
            except Exception as exc:
                health = {
                    "adapter": cfg.adapter, "bin": "?",
                    "available": False, "error": str(exc),
                }
            embed = build_health_embed(cfg, health)
            await interaction.followup.send(
                embed=embed, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True,
            )

        session_group = app_commands.Group(name="session", description="会话管理")

        @session_group.command(name="status", description="显示会话状态")
        async def slash_session_status(interaction: discord.Interaction):
            if not _is_channel_allowed(interaction):
                await interaction.response.send_message("此频道不可用。", ephemeral=True)
                return
            deny = can_run_operator_command(cfg, interaction.user.id, "session status")
            if deny:
                await interaction.response.send_message(deny, ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            embed = build_session_status_embed(
                self,
                interaction.channel_id,
                is_thread=is_thread_channel(interaction.channel),
            )
            await interaction.followup.send(
                embed=embed, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True,
            )

        @session_group.command(name="reset", description="重置当前会话")
        async def slash_session_reset(interaction: discord.Interaction):
            if not _is_channel_allowed(interaction):
                await interaction.response.send_message("此频道不可用。", ephemeral=True)
                return
            deny = can_run_operator_command(cfg, interaction.user.id, "session reset")
            if deny:
                await interaction.response.send_message(deny, ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            response = await handle_operator_command(
                "session reset",
                self,
                interaction.channel_id,
                is_thread=is_thread_channel(interaction.channel),
            )
            await interaction.followup.send(
                response, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True,
            )

        self.tree.add_command(session_group)

    def _make_progress_callback(self, progress_state: dict) -> collections.abc.Callable:
        """Create an on_progress callback that writes partial output to a shared dict."""
        def _on_progress(partial_text: str):
            progress_state["partial"] = partial_text

        return _on_progress

    async def _run_adapter_for_scope(
        self,
        prompt: str,
        *,
        session_scope_id: str,
        legacy_scope_ids: tuple[str, ...],
        placeholder: discord.Message | None,
        progress_state: dict,
    ) -> AdapterResult:
        """Run call/resume for a canonical scope, with legacy scope fallback."""
        progress_cb = self._make_progress_callback(progress_state)
        existing = self.session_store.get_first_active(
            scope_ids=(session_scope_id, *legacy_scope_ids),
            agent_id=self.agent_config.id,
        )

        try:
            if existing:
                current_work_dir = self.agent_config.work_dir
                if (
                    current_work_dir
                    and existing.get("work_dir")
                    and current_work_dir != existing["work_dir"]
                ):
                    log.info(
                        "Session work_dir mismatch (had=%s now=%s), marking stale for agent=%s scope=%s",
                        existing["work_dir"],
                        current_work_dir,
                        self.agent_config.id,
                        existing["scope_id"],
                    )
                    self.session_store.mark_stale(
                        scope_id=existing["scope_id"],
                        agent_id=self.agent_config.id,
                    )
                    existing = None

            if existing:
                log.info(
                    "Resuming session %s for agent=%s scope=%s",
                    existing["session_id"],
                    self.agent_config.id,
                    existing["scope_id"],
                )
                result: AdapterResult = await self._run_with_heartbeat(
                    placeholder,
                    self.adapter.resume(
                        existing["session_id"],
                        prompt,
                        work_dir=self.agent_config.work_dir,
                        on_progress=progress_cb,
                    ),
                    progress_state=progress_state,
                )
                if self._is_error_response(result.text):
                    log.warning(
                        "Resume failed for session %s, falling back to fresh call",
                        existing["session_id"],
                    )
                    self.session_store.mark_stale(
                        scope_id=existing["scope_id"],
                        agent_id=self.agent_config.id,
                    )
                    existing = None
                    progress_state["partial"] = ""
                    result = await self._run_with_heartbeat(
                        placeholder,
                        self.adapter.call(
                            prompt,
                            work_dir=self.agent_config.work_dir,
                            on_progress=progress_cb,
                        ),
                        progress_state=progress_state,
                    )
            else:
                result = await self._run_with_heartbeat(
                    placeholder,
                    self.adapter.call(
                        prompt,
                        work_dir=self.agent_config.work_dir,
                        on_progress=progress_cb,
                    ),
                    progress_state=progress_state,
                )
        except Exception as exc:
            log.exception("Adapter call failed for agent %s", self.agent_config.id)
            result = AdapterResult(text=f"Agent error: {exc}")

        if result.session_id:
            self.session_store.upsert(
                scope_id=session_scope_id,
                agent_id=self.agent_config.id,
                adapter=self.agent_config.adapter,
                session_id=result.session_id,
                work_dir=self.agent_config.work_dir,
            )
            if existing and existing["scope_id"] != session_scope_id:
                self.session_store.mark_stale(
                    scope_id=existing["scope_id"],
                    agent_id=self.agent_config.id,
                )

        return result

    async def _handle_request(self, message: discord.Message):
        """Process an addressed message: call adapter, send response."""
        channel = message.channel
        # Session scope: regular messages use channel/thread scope.
        session_scope_id = scope_for_channel(channel)
        legacy_scope_ids = (legacy_scope_for_channel_id(channel.id),)
        # Context scope: always use resolved channel id (parent for threads)
        context_channel_id = str(self._resolve_channel_id(message))

        # 1. Send placeholder
        placeholder = None
        try:
            placeholder = await channel.send("\U0001f504 thinking...")
        except discord.HTTPException:
            pass

        # 2. Build prompt with context
        prompt_text = self._get_prompt_text(message)
        prompt = build_agent_prompt(
            context_store=self.context_store,
            config=self.agent_config,
            bot_id=self.user.id,
            channel_id=context_channel_id,
            message_id=str(message.id),
            current_text=prompt_text,
        )

        progress_state: dict = {"partial": ""}
        result = await self._run_adapter_for_scope(
            prompt,
            session_scope_id=session_scope_id,
            legacy_scope_ids=legacy_scope_ids,
            placeholder=placeholder,
            progress_state=progress_state,
        )

        response_text = result.text

        # 3. Resolve handoff mentions in response
        response_text = self.mention_router.resolve_handoff_mentions(response_text)

        # 4. Split handoff lines from response text
        handoff_lines, display_text = split_handoff_lines(response_text)

        # 5. Send response (edit placeholder)
        chunks = _chunk_message(display_text) if display_text else []
        if not chunks and not handoff_lines:
            if placeholder:
                try:
                    await placeholder.edit(content="(no response)")
                except discord.HTTPException:
                    pass
            return

        if chunks:
            if placeholder:
                try:
                    await placeholder.edit(content=chunks[0])
                except discord.HTTPException:
                    await channel.send(chunks[0])
            else:
                await channel.send(chunks[0])

            for chunk in chunks[1:]:
                try:
                    await channel.send(chunk)
                except discord.HTTPException:
                    break
        elif placeholder:
            try:
                await placeholder.edit(content="✅ done")
            except discord.HTTPException:
                pass

        # 8. Send each handoff as a separate new message (MESSAGE_CREATE)
        for handoff in handoff_lines:
            try:
                await channel.send(handoff)
            except discord.HTTPException:
                pass

        # 9. Record our response to context (skip adapter errors)
        if not self._is_error_response(result.text):
            self.context_store.record_message(
                message_id=f"response:{int(time.time() * 1000)}:{self.agent_config.id}",
                channel_id=context_channel_id,
                author_id=str(self.user.id),
                author_name=self.agent_config.display_name or self.agent_config.id,
                author_is_bot=True,
                content=response_text[:2000],
                created_at_ms=int(time.time() * 1000),
                source="discord",
                ttl_seconds=self.agent_config.context_ttl_seconds,
            )

    _ERROR_PREFIXES = (
        "Agent error:",
        "OpenCode CLI failed", "OpenCode timed out",
        "Codex CLI failed", "Codex timed out", "Codex stopped responding", "Codex resume failed",
        "Hermes CLI failed", "Hermes timed out",
        "Claude CLI failed", "Claude error:", "Claude timeout",
    )

    @classmethod
    def _is_error_response(cls, text: str) -> bool:
        return any(text.startswith(p) for p in cls._ERROR_PREFIXES)
