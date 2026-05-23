import argparse
import os
import shutil
import tomllib
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .models import (
    AgentConfig,
    CODEX_CMD,
    DEFAULT_HERMES_BIN,
    DEFAULT_OPENCLAW_BIN,
    KnownAgentMention,
)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _as_int_list(value: Any) -> list[int]:
    return [int(v) for v in _as_list(value)]


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _first_existing_command(*candidates: str | None) -> str:
    for candidate in candidates:
        if not candidate:
            continue
        found = shutil.which(candidate)
        if found:
            return found
        if Path(candidate).exists():
            return candidate
    return candidates[-1] or ""


def _build_known_agent(agent_id: str, values: dict[str, Any]) -> KnownAgentMention:
    aliases = _as_list(values.get("aliases"))
    names = set(aliases)
    display_name = str(values.get("display_name", "")).strip()
    if display_name:
        names.add(display_name)
    names.add(agent_id)
    primary_name = display_name or (aliases[0] if aliases else agent_id)
    discord_user_id = values.get("discord_user_id")
    if discord_user_id is not None:
        discord_user_id = int(discord_user_id)
    return KnownAgentMention(
        id=agent_id,
        primary_name=primary_name,
        names=names,
        role_ids=set(_as_list(values.get("role_ids"))),
        discord_user_id=discord_user_id,
    )


def _build_toml_roster(
    defaults: dict[str, Any], agents: list[dict[str, Any]]
) -> list[KnownAgentMention]:
    roster: list[KnownAgentMention] = []
    for agent in agents:
        agent_id = str(agent.get("id", "")).strip()
        if not agent_id:
            continue
        merged = {**defaults, **agent}
        roster.append(_build_known_agent(agent_id, merged))
    return roster


def _build_external_agents(
    externals: list[dict[str, Any]],
) -> list[KnownAgentMention]:
    roster: list[KnownAgentMention] = []
    for ext in externals:
        agent_id = str(ext.get("id", "")).strip()
        if not agent_id:
            continue
        roster.append(_build_known_agent(agent_id, ext))
    return roster


def _load_toml_agent(config_path: Path, agent_id: str) -> AgentConfig:
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    defaults = data.get("defaults", {})
    agents = data.get("agents", [])
    externals = data.get("external_agents", [])
    known_agents = _build_toml_roster(defaults, agents) + _build_external_agents(externals)

    selected = None
    for agent in agents:
        if str(agent.get("id", "")) == agent_id:
            selected = agent
            break
    if selected is None:
        available = ", ".join(str(a.get("id")) for a in agents)
        raise SystemExit(
            f"Agent {agent_id!r} not found in {config_path}. Available: {available}"
        )

    merged = {**defaults, **selected}

    token = merged.get("token")
    token_env = merged.get("token_env")
    if not token and token_env:
        token = os.getenv(str(token_env))
    if not token:
        raise SystemExit(
            f"Discord token missing for agent {agent_id!r}. Set {token_env} or token."
        )

    return AgentConfig(
        id=str(merged.get("id") or agent_id),
        token=str(token),
        adapter=str(merged.get("adapter", "openclaw")),
        display_name=str(merged.get("display_name", "")),
        aliases=set(_as_list(merged.get("aliases"))),
        role_ids=set(_as_list(merged.get("role_ids"))),
        channels=_as_int_list(merged.get("channels")),
        respond_to_bots=_as_bool(merged.get("respond_to_bots"), True),
        context_db_path=str(
            merged.get("context_db_path", "data/discord_context.sqlite3")
        ),
        context_recent_messages=int(merged.get("context_recent_messages", 40)),
        context_budget_chars=int(merged.get("context_budget_chars", 12000)),
        context_max_message_chars=int(merged.get("context_max_message_chars", 500)),
        context_ttl_seconds=int(merged.get("context_ttl_seconds", 86400)),
        handoff_dedupe_seconds=int(merged.get("handoff_dedupe_seconds", 600)),
        timeout=int(merged.get("timeout", 360)),
        first_byte_timeout=int(merged.get("first_byte_timeout", 120)),
        activity_timeout=int(merged.get("activity_timeout", 120)),
        system_prompt=str(merged.get("system_prompt", "")),
        known_agents=known_agents,
        work_dir=str(Path(str(merged["work_dir"])).expanduser()) if merged.get("work_dir") else None,
        model=str(merged["model"]) if merged.get("model") else None,
        openclaw_agent_id=str(merged.get("openclaw_agent_id", "main")),
        openclaw_bin=_first_existing_command(
            os.getenv("OPENCLAW_BIN"),
            str(merged.get("openclaw_bin", "")),
            shutil.which("openclaw"),
            DEFAULT_OPENCLAW_BIN,
        ),
        hermes_bin=_first_existing_command(
            os.getenv("HERMES_BIN"),
            str(merged.get("hermes_bin", "")),
            shutil.which("hermes"),
            DEFAULT_HERMES_BIN,
        ),
        hermes_provider=(
            str(merged["hermes_provider"]) if merged.get("hermes_provider") else None
        ),
        hermes_toolsets=(
            str(merged["hermes_toolsets"]) if merged.get("hermes_toolsets") else None
        ),
        hermes_accept_hooks=_as_bool(merged.get("hermes_accept_hooks"), False),
        claude_bin=_first_existing_command(
            str(merged.get("claude_bin", "claude")), "claude"
        ),
        claude_dangerously_skip_permissions=_as_bool(
            merged.get("claude_dangerously_skip_permissions"), False
        ),
        codex_bin=_first_existing_command(
            str(merged.get("codex_bin", CODEX_CMD)), CODEX_CMD
        ),
        codex_sandbox=str(merged.get("codex_sandbox", "danger-full-access")),
        codex_fallback_model=(
            str(merged["codex_fallback_model"])
            if merged.get("codex_fallback_model")
            else None
        ),
        opencode_bin=_first_existing_command(
            os.getenv("OPENCODE_BIN"),
            str(merged.get("opencode_bin", "")),
            shutil.which("opencode"),
            "opencode",
        ),
        opencode_dangerously_skip_permissions=_as_bool(
            merged.get("opencode_dangerously_skip_permissions"), False
        ),
        wiki_enabled=_as_bool(merged.get("wiki_enabled"), False),
        wiki_path=str(merged.get("wiki_path", "wiki")),
        discoveries_channel_id=(
            int(merged["discoveries_channel_id"])
            if merged.get("discoveries_channel_id")
            else None
        ),
        allowed_user_ids=_as_int_list(merged.get("allowed_user_ids")),
    )


def load_config(argv: list[str] | None = None) -> AgentConfig:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Discord Nexus single-agent bot runner"
    )
    parser.add_argument(
        "--config",
        default=os.getenv("DISCORD_AGENTS_CONFIG", "agents.toml"),
    )
    parser.add_argument("--agent", default=os.getenv("DISCORD_AGENT_ID"))
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")

    if not args.agent:
        raise SystemExit("--agent or DISCORD_AGENT_ID is required")

    return _load_toml_agent(config_path, args.agent)
