# Domain Model

## Core Entities

### AgentConfig

Per-agent configuration loaded from `agents.toml`. Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier (e.g. "mac-claude") |
| `adapter` | str | "claude", "codex", "opencode", "hermes" |
| `token_env` | str | Env var name holding Discord bot token |
| `display_name` | str | Human-visible name |
| `channels` | list[int] | Discord channel IDs this agent listens in |
| `work_dir` | str | Default CWD for adapter subprocess |
| `discord_user_id` | int | Discord bot user ID for mention resolution |
| `system_prompt` | str | Injected into every adapter call |
| `timeout` | int | Total adapter timeout (default 1800s) |
| `known_agents` | list[KnownAgentMention] | Peer agents for routing |

### KnownAgentMention

A peer agent known to this agent for routing purposes.

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Agent identifier |
| `primary_name` | str | Display name |
| `names` | set[str] | All matchable names (id + aliases + display_name) |
| `discord_user_id` | int | Discord user ID |
| `kind` | str | "managed" (started by nexus) or "external" (own Gateway) |

### AdapterResult

Returned by every adapter call.

| Field | Type | Description |
|-------|------|-------------|
| `text` | str | Response text |
| `session_id` | str | CLI session ID for resume |
| `resumed` | bool | Whether this was a resumed session |
| `metadata` | dict | Extensible metadata |

## Data Stores

### Context Store (SQLite)

Table: `messages`
- PK: `message_id TEXT`
- Key cols: `channel_id`, `author_id`, `author_name`, `author_is_bot`, `content`, `created_at_ms`, `source`
- Index: `(channel_id, created_at_ms)`
- Cleanup: TTL-based on every `record_message()` call

### Session Store (SQLite)

Table: `sessions`
- PK: `(scope_id, agent_id)`
- Key cols: `adapter`, `session_id`, `work_dir`, `status`, `turn_count`, `created_at`, `updated_at`
- Upsert: increments `turn_count` on match, resets to 1 on new session

## Handoff Protocol

- Regex: `^\[handoff\]\s*(?:<@!?(\d+)>\s*(.*)|@([^\n]+))$`
- Resolution: text `@AgentName` → longest alias match → `<@discord_user_id>`
- Delivery: handoff lines sent as separate Discord messages to trigger target bot

## Agent Types

| Type | Launch | Session | Examples |
|------|--------|---------|----------|
| Managed | `nexus.py --agent <id>` | Yes (resume supported) | mac-claude, mac-codex, mac-opencode |
| External | Own process | N/A | 小龙虾 (OpenClaw), Hermes |
