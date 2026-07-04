# multinexus

> 本仓库基于 [baisiqi6/discord-nexus](https://github.com/baisiqi6/discord-nexus) 继续维护，原项目 README 标注为 MIT License。本分支保留原始 Git 历史，并在此基础上加入 OpenClaw CLI、managed context、KOOK 接入规划和多主机 agent routing 等定制能力。来源与维护说明见 [docs/provenance.md](docs/provenance.md)。

A modular Discord bot framework for connecting AI agents — Claude Code CLI, Codex CLI, and local LLMs (LM Studio, Ollama, vLLM) — to Discord as a collaborative multi-agent system.

---

## What It Is

multinexus lets you run multiple AI agents in a Discord server where they can:

- Respond to messages via role mention (`@Claude`, `@Local Agent`, `@Codex`) or slash command
- Respond to `@team <prompt>` to call all agents simultaneously
- Hand off tasks to each other with a simple `@AgentName <task>` protocol
- Maintain per-thread conversation history and agent workspaces
- Write to a shared wiki (public and private tiers)
- Post discoveries to a shared channel
- Trigger web research tasks
- Extract and inject persistent memories from conversation history (via `washer.py`)

Each agent posts as a distinct Discord user via webhook, with its own name and avatar.

---

## Architecture

Production runs as one `DiscordBridge` process hosting N `DiscordClient`
instances (one per agent identity). Entry point is `multinexus.py`:

```
multinexus.py --platform discord --config agents.toml
      │
      └── multinexus/client.py  DiscordBridge → [DiscordClient per agent]
            │   each agent is its own Discord identity with its own slash
            │   commands (/health, /agents, /session status, /session reset)
            │
            ├── multinexus/adapters/        Claude / Codex / OpenCode / OMP / OpenClaw gateway
            ├── multinexus/agentd/          local agentd job protocol (coordinate runtime)
            ├── multinexus/sessions/        per-scope session persistence
            ├── multinexus/commands.py      operator command handlers (text + slash)
            ├── multinexus/embeds.py        embed builders for /health /agents /session status
            ├── multinexus/handoff.py       coordinator handoff message parsing
            ├── persistence/db.py           SQLite (aiosqlite) — history, jobs, memory, workspaces
            └── multinexus/wiki/            flat-file wiki with public + private tiers

washer.py (scheduled independently, nightly memory extraction)
      │
      ├── Reads conversations + conversations_archive (watermark-based)
      ├── Calls local LLM (LM Studio) for memory extraction
      ├── memory/content_validator.py  — filters secrets + validates types
      └── Routes to:
            ├── persistence/db.py → memories          (fact)
            ├── persistence/db.py → memory_promotions (preference/context)
            └── private DB        → review_queue      (is_private=true)
```

> The legacy single-bot entry (`bot.py` + `cogs/`) has been removed. The
> per-agent compatibility mode `multinexus.py --agent <id>` is retained.

Agent output is scanned for structured tags (`<!-- DISCOVERY: -->`, `<!-- WIKI: -->`, etc.)
before being chunked and posted to Discord.

---

## Quickstart

### 1. Prerequisites

- Python 3.11+
- A Discord application and bot token ([discord.com/developers](https://discord.com/developers))
- At least one of:
  - [Claude Code CLI](https://docs.anthropic.com/claude-code) (`npm install -g @anthropic-ai/claude-code`)
  - [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`)
  - A local LLM server (LM Studio, Ollama, vLLM) running on `http://localhost:1234`

### 2. Clone and install

```bash
git clone https://github.com/your-org/multinexus.git
cd multinexus
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
cp config.yaml.example config.yaml
```

Edit `.env` — fill in your Discord bot token.
Edit `config.yaml` — set your server ID, channel IDs, agent roles, and which agents to enable.

See [`docs/platform-setup.md`](docs/platform-setup.md) for a full walkthrough.

### 4. Run

```bash
python multinexus.py --platform discord --config agents.toml
```

For production deployment (systemd on Linux, launchd on Mac), see
[`docs/platform-setup.md`](docs/platform-setup.md) and the deploy scripts in
`scripts/`.

### 5. Invite the bot

In the Discord Developer Portal, enable the **Message Content Intent** and generate an invite URL with:
- `bot` scope
- `applications.commands` scope
- Permissions: Send Messages, Manage Webhooks, Read Message History, Embed Links, Add Reactions

---

## Features

| Feature | Description |
|---|---|
| Multi-agent routing | Each agent is its own Discord identity; messages route to the configured agent |
| `[handoff]` protocol | Agents hand tasks to each other via `[handoff] <@agent>` lines in responses |
| **Session persistence** | Per-scope Claude/Codex sessions resume on subsequent messages |
| Per-thread history | Conversation history stored per thread/channel in SQLite |
| Chunked output | Responses are split into Discord-sized chunks before posting |
| Operator commands | Text commands: `agents` (list), `health` (check), `session status`, `session reset` |
| Public wiki | Shared Markdown wiki, written by agents or users |
| Private wiki | Separate tier for sensitive content, stored outside the repo |
| Persistent memory | `washer.py` extracts facts/preferences/context from history via local LLM |
| Private review queue | Sensitive extractions held for manual approval before injection |
| Secret redaction | Output is scanned for secrets before posting |
| Cross-platform | Windows and Mac/Linux supported |

---

## Memory Washing Machine

`washer.py` is an optional nightly pipeline that harvests durable memories from your conversation history using a local LLM (LM Studio / Ollama).

It reads from `conversations` and `conversations_archive`, calls the local model for extraction, and routes results to three tiers:

- **Shared memories** (`fact` type) — injected into all agent prompts
- **Shared promotions** (`preference` / `context`) — queued for review before injection
- **Private review queue** — `is_private` items go here; reviewed and approved via CLI

**Setup:**
```
# .env
TARGET_USER_ID=your_discord_user_id
USER_DISPLAY_NAME=YourName
E4B_BASE_URL=http://localhost:1234/v1
E4B_MODEL=gemma-3-4b-it

# Schedule (Windows)
python scripts/setup-scheduler.ps1

# Schedule (Linux/macOS — add to crontab)
# 0 2 * * * cd /path/to/multinexus && python washer.py
```

The memory washing machine concept is from **Mark Kashef** — ["I Tried OpenClaw and Hermes. I Kept Claude Code."](https://youtu.be/rVzGu5OYYS0) (timestamp 10:57).

---

## Agents

| Agent | Type | Required |
|---|---|---|
| `claude` | Claude Code CLI subprocess | Optional |
| `codex` | Codex CLI subprocess | Optional |
| `local-agent` | Local LLM (OpenAI-compatible HTTP) | Optional |
| `openclaw` | OpenClaw gateway relay | Optional |
| `researcher` | Web research via OpenClaw | Optional |

At least one agent must be configured and online. See [`docs/agents.md`](docs/agents.md).

---

## Documentation

- [Architecture](docs/architecture.md) — system diagram, data flow, component overview
- [Multi-Agent Collaboration](docs/multi-agent-collaboration.md) — Discord/KOOK as visible message bus, harness-backed workflow, coordinator design
- [Agents](docs/agents.md) — configuring each agent type, adding custom agents
- [Wiki System](docs/wiki-system.md) — wiki structure, tags, private tier, curation
- [Platform Setup](docs/platform-setup.md) — Windows and Mac/Linux install guides, systemd/launchd persistence

---

## Data & Privacy

| Agent | Where inference runs | Data leaves your machine? |
|---|---|---|
| `claude` | Anthropic API (cloud) | Yes — prompts sent to Anthropic |
| `codex` | OpenAI API (cloud) | Yes — prompts sent to OpenAI |
| `local-agent` | Your machine (LM Studio, Ollama, etc.) | No |
| `openclaw` / `researcher` | Your machine (via OpenClaw/Dream Server) | No |

**What stays local regardless of which agents you use:**
- Conversation history (SQLite database on your machine)
- The wiki (`wiki/pages/`, `wiki/private/`)
- All config, secrets, and bot state

For a fully private setup with no cloud inference, use only the `local-agent` with a self-hosted model. [Dream Server](https://github.com/Light-Heart-Labs/DreamServer) is a good companion for this.

---

## Security Notes

- Bot token and API keys are read from `.env` — never commit this file
- Private wiki pages live in `wiki/private/` (gitignored — never committed); `PRIVATE_DB_PATH` controls where the private SQLite DB is stored
- On Windows, the private DB directory is hardened with `icacls` on first run
- All agent output is scanned for secrets before posting to Discord
- The allowlist controls who can use `/restart` and other privileged commands

---

## Support

If you find this useful, donations are appreciated:

- **BTC:** `bc1qyqx8eqlzpjvp3nnmgpfltq5p5vj43z5tqt553y`
- **SOL:** `FxM3HmqJFNErRr3MFiPbAL9ojpuActaQ1h6TfH9fUPs2`
- **ETH:** `0x55BF0d4a4185F6905268E503f4E64ecc5fB8538f`

---

- The allowlist controls who can use `session reset` and other privileged operator commands

The optional `OpenClawRelayAgent` is designed to work with [Dream Server](https://github.com/Light-Heart-Labs/DreamServer) by Light Heart Labs — a fully local AI stack (LLM inference, agents, voice, workflows, RAG) deployable on your own hardware with a single command. It's a natural companion to multinexus if you want a complete self-hosted setup.

---

## License

MIT
