# Architecture

> **⚠️ Legacy architecture document** — this describes the removed single-bot
> (`bot.py` + `cogs/`) topology. The production entry is now `multinexus.py
> --platform discord` → `multinexus/client.py` (`DiscordBridge` /
> `DiscordClient`). See `README.md` "Architecture" section for the current
> topology. This file is retained for historical reference.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Discord Server                           │
│                                                                 │
│  #general     #agent-chat     #discoveries     #wiki-feed       │
└────────┬──────────────┬──────────────────────────────────────── ┘
         │              │
         │  Message / Slash Command
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       bot.py — NexusBot                         │
│                                                                 │
│  on_message ──► routing/dispatcher.py                           │
│                   should_respond()   → bool                     │
│                   parse_commands()   → list[AgentCommand]       │
│                   resolve_channel_id() → str                    │
│                                                                 │
│  handle_agent_request(agent, prompt, thread_id, channel, user)  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    cogs/agents.py — AgentsCog                   │
│                                                                 │
│  dispatch_agents()                                              │
│    │  build_discord_context()  → inject history, wiki, mission  │
│    │  agent.call()             → raw response string            │
│    │  security/filter.py       → scan_output()                  │
│    │  parse agent tags         → SCRATCH, DISCOVERY, WIKI, etc. │
│    │  post via webhook         → distinct identity per agent    │
│    │  chunk_message()          → split >1900 char responses     │
│    └  parse_handoff()          → route to next agent if needed  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
     agents/cli.py    agents/local_llm.py  agents/openclaw_relay.py
     ┌──────────┐     ┌──────────────────┐  ┌─────────────────────┐
     │ClaudeAgent│    │  LocalLLMAgent   │  │ OpenClawRelayAgent  │
     │CodexAgent │    │  (HTTP/OpenAI)   │  │   (optional)        │
     │(subprocess│    │  LM Studio       │  │                     │
     │  via CLI) │    │  Ollama / vLLM   │  │ agents/researcher.py│
     └──────────┘     └──────────────────┘  │  ResearcherAgent    │
                                             │  (optional)         │
                                             └─────────────────────┘
```

---

## Data Flow

### Inbound message

1. Discord delivers message to `on_message` in `bot.py`
2. `dispatcher.should_respond()` checks if bot should handle it (mention, role, channel whitelist)
3. `dispatcher.parse_commands()` extracts which agents to invoke and with what prompt
4. `bot.handle_agent_request()` is called for each agent

### Agent invocation

1. `cogs/agents.dispatch_agents()` is the core orchestration loop
2. Per-thread history is loaded from SQLite (`persistence/db.py`)
3. `build_discord_context()` constructs the full prompt:
   - Channel mission (from `config.yaml channel_missions`)
   - Agent workspace / scratch state (from prior turns)
   - Relevant wiki pages (from `services/wiki.WikiStore.get_relevant_context()`)
   - Recent conversation history
4. `agent.call(prompt, system_prompt, thread_id)` is called
5. Output is passed through `security/filter.scan_output()` — secrets redacted
6. Agent tags are parsed and dispatched (see Tag Processing below)
7. The cleaned response is chunked and posted via Discord webhook

### Handoffs

If the agent response ends with `@AgentName <task>` or `!bang <task>`, the cog:
1. Parses the handoff target and task
2. Calls `dispatch_agents()` recursively for the target agent
3. Maximum handoff depth is enforced to prevent infinite loops (default: 3)

---

## Component Map

### bot.py

- `NexusBot(commands.Bot)` — main bot class
- Loads agents from config on startup
- Registers cogs: `agents`, `utility`, `wiki`
- Exposes `handle_agent_request()` as the central entry point
- Manages `_agent_status` dict for health tracking
- Handles private DB hardening on first run (Windows: icacls)

### routing/dispatcher.py

- `should_respond(message, config)` — determines if a message warrants a response
- `parse_commands(message, config)` → list of `(agent_name, prompt)` pairs
- `resolve_channel_id(channel)` → consistent string thread ID
- `BANG_ALIASES` — `!bang` shorthand mappings

### agents/

| Module | Class | Backend |
|---|---|---|
| `cli.py` | `ClaudeAgent` | `claude` CLI subprocess |
| `cli.py` | `CodexAgent` | `codex` CLI subprocess |
| `local_llm.py` | `LocalLLMAgent` | OpenAI-compatible HTTP |
| `openclaw_relay.py` | `OpenClawRelayAgent` | OpenClaw gateway HTTP |
| `researcher.py` | `ResearcherAgent` | OpenClaw researcher workspace |
| `base.py` | `BaseAgent` (ABC) | — |

### cogs/

| Module | Class | Responsibilities |
|---|---|---|
| `agents.py` | `AgentsCog` | dispatch, tag processing, handoffs, webhooks |
| `utility.py` | `Utility` | /help, /monitor, /dashboard, /discover, /restart, agent slash cmds |
| `wiki.py` | `WikiCog` | /wiki, /wiki-private, ingest loop, curation loop |

### persistence/db.py

SQLite via aiosqlite. Tables:

| Table | Purpose |
|---|---|
| `conversation_history` | Per-agent per-thread message log |
| `jobs` | Async job tracking (status, result) |
| `workspaces` | Per-agent per-thread scratch state |
| `sessions` | Session metadata |
| `plans` | Agent plans (optional) |
| `token_usage` | Per-agent token + cost tracking |
| `discoveries` | Discovery log |

A separate private DB (path from `PRIVATE_DB_PATH` env var) can hold sensitive tables.

### services/wiki.py

- `WikiStore` manages flat-file Markdown pages
- Public pages: `wiki/pages/*.md`
- Draft pages: `wiki/drafts/*.md`
- Private pages: stored in private DB directory (`wiki/private/`)
- Index: `wiki/index.json`
- `get_relevant_context(query)` — returns top-N wiki pages by keyword relevance

### security/

- `filter.py` — `scan_output(text)` redacts secrets matching known env var names and patterns
- `allowlist.py` — `Allowlist` class controls privileged command access

---

## Tag Processing

The bot scans every agent response for these HTML-comment tags:

| Tag | Action |
|---|---|
| `<!-- SCRATCH -->…<!-- /SCRATCH -->` | Stripped before posting |
| `<!-- DISCOVERY: text -->` | Posted to #discoveries, logged to DB |
| `<!-- WIKI: name\ncontent -->` | Written to `wiki/pages/name.md` |
| `<!-- WIKI-PRIVATE: name\ncontent -->` | Written to private wiki tier |
| `<!-- RESEARCH: query -->` | Triggers researcher agent (if configured) |

---

## Rate-Limit Fallback Chain

If `claude` returns an `AgentRateLimitError`, the bot falls back:

```
claude → codex → local-agent (local LLM)
```

Each step is attempted in order. If all agents are unavailable, an error is posted to the channel.

---

## Configuration Flow

```
config.yaml
  └── bot.py reads on startup
        ├── agent configs → instantiate agent objects
        ├── channel_missions → injected into agent prompts per channel
        ├── agent_channels → which channels each agent listens to
        ├── agent_roles → Discord role IDs that trigger each agent
        └── wiki config → WikiStore paths and settings
```

Environment variables (`.env`) override sensitive values:
- `DISCORD_TOKEN`
- `LMSTUDIO_API_KEY` (optional)
- `OPENCLAW_GATEWAY_TOKEN` (optional)
- `PRIVATE_DB_PATH` (optional)
