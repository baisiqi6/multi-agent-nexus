"""Session scope key helpers for channel, thread, and coordinator task sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import discord
except ImportError:  # pragma: no cover - exercised in minimal worker runtimes
    discord = None


@dataclass(frozen=True)
class ScopeDescription:
    scope_id: str
    kind: str
    label: str
    detail: str


def channel_scope(channel_id: int | str) -> str:
    return f"channel:{channel_id}"


def thread_scope(thread_id: int | str) -> str:
    return f"thread:{thread_id}"


def task_scope(workspace_id: str, task_id: str) -> str:
    return f"task:{workspace_id}:{task_id}"


def scope_for_channel(channel: Any) -> str:
    if is_thread_channel(channel):
        return thread_scope(channel.id)
    return channel_scope(channel.id)


def scope_for_channel_id(channel_id: int | str, *, is_thread: bool = False) -> str:
    if is_thread:
        return thread_scope(channel_id)
    return channel_scope(channel_id)


def legacy_scope_for_channel_id(channel_id: int | str) -> str:
    return str(channel_id)


def is_thread_channel(channel: Any) -> bool:
    if discord is None:
        return False
    return isinstance(channel, discord.Thread)


def describe_scope(scope_id: str) -> ScopeDescription:
    if scope_id.startswith("channel:"):
        return ScopeDescription(
            scope_id=scope_id,
            kind="channel",
            label="channel scope",
            detail=scope_id.removeprefix("channel:"),
        )
    if scope_id.startswith("thread:"):
        return ScopeDescription(
            scope_id=scope_id,
            kind="thread",
            label="thread scope",
            detail=scope_id.removeprefix("thread:"),
        )
    if scope_id.startswith("task:"):
        parts = scope_id.split(":", 2)
        detail = parts[2] if len(parts) == 3 else scope_id.removeprefix("task:")
        return ScopeDescription(
            scope_id=scope_id,
            kind="task",
            label="task scope",
            detail=detail,
        )
    return ScopeDescription(
        scope_id=scope_id,
        kind="legacy",
        label="legacy channel scope",
        detail=scope_id,
    )
