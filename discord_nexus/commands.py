"""Operator commands: session status/reset, agents listing, health check."""

import time

OPERATOR_COMMANDS = {"session status", "session reset", "agents", "health"}


def parse_operator_command(text: str) -> str | None:
    cleaned = text.strip().lower()
    for cmd in OPERATOR_COMMANDS:
        if cleaned == cmd:
            return cmd
    return None


def is_dangerous_command(cmd: str) -> bool:
    return cmd == "session reset"


async def handle_operator_command(cmd: str, client, message) -> str:
    if cmd == "session status":
        return _cmd_session_status(client, message)
    if cmd == "session reset":
        return _cmd_session_reset(client, message)
    if cmd == "agents":
        return _cmd_agents(client)
    if cmd == "health":
        return await _cmd_health(client)
    return "Unknown command."


def _cmd_session_status(client, message) -> str:
    scope_id = str(message.channel.id)
    agent_id = client.agent_config.id
    current = client.session_store.get(scope_id=scope_id, agent_id=agent_id)
    all_sessions = client.session_store.list_by_agent(agent_id=agent_id)

    lines = [f"**Session Status** — {agent_id}\n"]
    if current:
        sid = current["session_id"]
        lines.append(f"**Current scope** (channel {scope_id}):")
        lines.append(f"  session_id: `{sid[:16]}...`" if len(sid) > 16 else f"  session_id: `{sid}`")
        lines.append(f"  adapter: {current['adapter']}")
        lines.append(f"  work_dir: {current['work_dir'] or '(none)'}")
        lines.append(f"  status: {current['status']}")
        lines.append(f"  turns: {current['turn_count']}")
        lines.append(f"  updated: {_fmt_time(current['updated_at'])}")
    else:
        lines.append(f"No active session in this scope (channel {scope_id}).")

    lines.append(f"\nActive sessions: {len(all_sessions)} total")
    return "\n".join(lines)


def _cmd_session_reset(client, message) -> str:
    scope_id = str(message.channel.id)
    agent_id = client.agent_config.id
    current = client.session_store.get(scope_id=scope_id, agent_id=agent_id)
    if not current:
        return f"No active session in this scope (channel {scope_id})."

    client.session_store.mark_stale(scope_id=scope_id, agent_id=agent_id)
    return (
        f"**Session reset** — {agent_id}\n\n"
        f"Marked session in scope {scope_id} as stale.\n"
        f"Next call will start fresh."
    )


def _cmd_agents(client) -> str:
    known = client.agent_config.known_agents
    managed = [a for a in known if a.kind == "managed"]
    external = [a for a in known if a.kind == "external"]

    lines = ["**Known Agents**\n"]
    if managed:
        lines.append("**Managed:**")
        for a in managed:
            mention = f"<@{a.discord_user_id}>" if a.discord_user_id else "(no Discord ID)"
            lines.append(f"  {a.id} ({a.primary_name}) — {mention}")
    if external:
        lines.append("\n**External:**")
        for a in external:
            mention = f"<@{a.discord_user_id}>" if a.discord_user_id else "(no Discord ID)"
            lines.append(f"  {a.id} ({a.primary_name}) — {mention}")
    return "\n".join(lines)


async def _cmd_health(client) -> str:
    health = await client.adapter.health_check()
    cfg = client.agent_config
    available = health.get("available", False)
    status = "yes" if available else "no"
    path = health.get("path") or health.get("bin", "?")
    lines = [
        f"**Health Check** — {cfg.id}\n",
        f"adapter: {health.get('adapter', '?')}",
        f"bin: {health.get('bin', '?')}",
        f"available: {status} (`{path}`)",
        f"work_dir: {cfg.work_dir or '(none)'}",
        f"model: {cfg.model or '(default)'}",
        f"timeout: {cfg.timeout}s",
    ]
    return "\n".join(lines)


def _fmt_time(ts: float) -> str:
    if not ts:
        return "(unknown)"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
