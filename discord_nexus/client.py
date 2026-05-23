"""DiscordClient: one discord.Client per agent, with two-layer message filtering."""

import asyncio
import collections.abc
import logging
import time

import discord

from .adapters.base import AdapterResult
from .adapters.factory import make_adapter
from .config import load_config
from .context.prompt import build_agent_prompt
from .context.store import ChatContextStore
from .models import AgentConfig
from .routing.mentions import MentionRouter
from .sessions.store import SessionStore

log = logging.getLogger(__name__)

_MAX_DISCORD_MSG_LEN = 1900


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
            await self._handle_request(message)
            return

        # Layer 3: human message — must be addressed to me
        if self.agent_config.allowed_user_ids and message.author.id not in self.agent_config.allowed_user_ids:
            return
        if self._is_addressed_to_me(message):
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
        if isinstance(message.channel, discord.Thread):
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

    def _make_progress_callback(self, progress_state: dict) -> collections.abc.Callable:
        """Create an on_progress callback that writes partial output to a shared dict."""
        def _on_progress(partial_text: str):
            progress_state["partial"] = partial_text

        return _on_progress

    async def _handle_request(self, message: discord.Message):
        """Process an addressed message: call adapter, send response."""
        channel = message.channel
        scope_id = str(self._resolve_channel_id(message))

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
            channel_id=scope_id,
            message_id=str(message.id),
            current_text=prompt_text,
        )

        # 3. Check for existing session and call adapter
        progress_state: dict = {"partial": ""}
        progress_cb = self._make_progress_callback(progress_state)
        existing = self.session_store.get(scope_id=scope_id, agent_id=self.agent_config.id)

        try:
            if existing:
                log.info(
                    "Resuming session %s for agent=%s scope=%s",
                    existing["session_id"], self.agent_config.id, scope_id,
                )
                result: AdapterResult = await self._run_with_heartbeat(
                    placeholder,
                    self.adapter.resume(
                        existing["session_id"], prompt,
                        work_dir=self.agent_config.work_dir, on_progress=progress_cb,
                    ),
                    progress_state=progress_state,
                )
                # If resume produced an error, fallback to fresh call
                if self._is_error_response(result.text):
                    log.warning(
                        "Resume failed for session %s, falling back to fresh call",
                        existing["session_id"],
                    )
                    self.session_store.mark_stale(scope_id=scope_id, agent_id=self.agent_config.id)
                    progress_state["partial"] = ""
                    result = await self._run_with_heartbeat(
                        placeholder,
                        self.adapter.call(
                            prompt,
                            work_dir=self.agent_config.work_dir, on_progress=progress_cb,
                        ),
                        progress_state=progress_state,
                    )
            else:
                result = await self._run_with_heartbeat(
                    placeholder,
                    self.adapter.call(
                        prompt,
                        work_dir=self.agent_config.work_dir, on_progress=progress_cb,
                    ),
                    progress_state=progress_state,
                )
        except Exception as exc:
            log.exception("Adapter call failed for agent %s", self.agent_config.id)
            result = AdapterResult(text=f"Agent error: {exc}")

        response_text = result.text

        # 4. Save session ID if we got one
        if result.session_id:
            self.session_store.upsert(
                scope_id=scope_id,
                agent_id=self.agent_config.id,
                adapter=self.agent_config.adapter,
                session_id=result.session_id,
                work_dir=self.agent_config.work_dir,
            )

        # 5. Resolve handoff mentions in response
        response_text = self.mention_router.resolve_handoff_mentions(response_text)

        # 6. Send response
        chunks = _chunk_message(response_text)
        if not chunks:
            if placeholder:
                try:
                    await placeholder.edit(content="(no response)")
                except discord.HTTPException:
                    pass
            return

        # Edit placeholder with first chunk
        if placeholder:
            try:
                await placeholder.edit(content=chunks[0])
            except discord.HTTPException:
                await channel.send(chunks[0])
        else:
            await channel.send(chunks[0])

        # Send remaining chunks
        for chunk in chunks[1:]:
            try:
                await channel.send(chunk)
            except discord.HTTPException:
                break

        # 7. Record our response to context (skip adapter errors)
        if not self._is_error_response(result.text):
            self.context_store.record_message(
                message_id=f"response:{int(time.time() * 1000)}:{self.agent_config.id}",
                channel_id=scope_id,
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
        "Codex CLI failed", "Codex timed out", "Codex stopped responding",
        "Hermes CLI failed", "Hermes timed out",
        "Claude CLI failed", "Claude error:", "Claude timeout",
    )

    @classmethod
    def _is_error_response(cls, text: str) -> bool:
        return any(text.startswith(p) for p in cls._ERROR_PREFIXES)
