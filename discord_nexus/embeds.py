"""Embed builders for slash command operator output."""

import time

import discord


def build_agents_embed(config) -> discord.Embed:
    embed = discord.Embed(title="Known Agents", color=discord.Color.blurple())
    managed = [a for a in config.known_agents if a.kind == "managed"]
    external = [a for a in config.known_agents if a.kind == "external"]
    if managed:
        lines = []
        for a in managed:
            ident = f"discord_id: `{a.discord_user_id}`" if a.discord_user_id else "no Discord ID"
            lines.append(f"{a.id} ({a.primary_name}) — {ident}")
        embed.add_field(name="Managed", value="\n".join(lines), inline=False)
    if external:
        lines = []
        for a in external:
            ident = f"discord_id: `{a.discord_user_id}`" if a.discord_user_id else "no Discord ID"
            lines.append(f"{a.id} ({a.primary_name}) — {ident}")
        embed.add_field(name="External", value="\n".join(lines), inline=False)
    return embed


def build_health_embed(config, health: dict) -> discord.Embed:
    available = health.get("available", False)
    if available:
        color = discord.Color.green()
    else:
        color = discord.Color.red()
    embed = discord.Embed(
        title=f"Health Check — {config.id}",
        color=color,
    )
    embed.add_field(name="adapter", value=health.get("adapter", "?"), inline=True)
    embed.add_field(name="bin", value=health.get("bin", "?"), inline=True)
    embed.add_field(name="available", value="yes" if available else "no", inline=True)
    embed.add_field(name="work_dir", value=config.work_dir or "(none)", inline=True)
    embed.add_field(name="model", value=config.model or "(default)", inline=True)
    embed.add_field(name="timeout", value=f"{config.timeout}s", inline=True)
    path = health.get("path") or health.get("bin", "?")
    embed.add_field(name="path", value=f"`{path}`", inline=False)
    if health.get("error"):
        embed.add_field(name="error", value=str(health["error"])[:1024], inline=False)
    return embed


def build_session_status_embed(client, channel_id: int) -> discord.Embed:
    scope_id = str(channel_id)
    agent_id = client.agent_config.id
    current = client.session_store.get(scope_id=scope_id, agent_id=agent_id)
    all_sessions = client.session_store.list_by_agent(agent_id=agent_id)

    if current:
        embed = discord.Embed(
            title=f"Session Status — {agent_id}",
            color=discord.Color.green(),
        )
        sid = current["session_id"]
        embed.add_field(name="scope", value=scope_id, inline=True)
        embed.add_field(
            name="session_id",
            value=f"`{sid[:16]}...`" if len(sid) > 16 else f"`{sid}`",
            inline=True,
        )
        embed.add_field(name="adapter", value=current["adapter"], inline=True)
        embed.add_field(name="work_dir", value=current["work_dir"] or "(none)", inline=True)
        embed.add_field(name="status", value=current["status"], inline=True)
        embed.add_field(name="turns", value=str(current["turn_count"]), inline=True)
        embed.add_field(
            name="updated",
            value=_fmt_time(current["updated_at"]),
            inline=False,
        )
        embed.add_field(name="active sessions", value=f"{len(all_sessions)} total", inline=False)
    else:
        embed = discord.Embed(
            title=f"Session Status — {agent_id}",
            description="No active session in this scope.",
            color=discord.Color.gold(),
        )
        embed.add_field(name="scope", value=scope_id, inline=True)
        embed.add_field(name="active sessions", value=f"{len(all_sessions)} total", inline=True)

    return embed


def _fmt_time(ts: float) -> str:
    if not ts:
        return "(unknown)"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
