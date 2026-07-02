# Architecture

## Entry Point

`multinexus.py --config agents.toml --agent <id>` — one process per managed agent.

## Module Map

```
multinexus.py                          CLI entry point
multinexus/
  client.py                       DiscordClient facade (Gateway + mention + context)
  coordinator_handoff.py          coordinator handoff/lifecycle orchestration mixin
  message_chunks.py               shared Discord-sized response chunking
  config.py                       TOML config loading, [defaults] + [[agents]] merge
  models.py                       AgentConfig, KnownAgentMention dataclasses
  protocol.py                     AgentRequest/AgentResponse envelope (cross-platform)
  commands.py                     Operator text command handler
  embeds.py                       Discord Embed builders for slash commands
  handoff.py                      Handoff line splitting and parsing
  adapters/
    base.py                       AgentAdapter ABC (call, resume, health_check)
    factory.py                    make_adapter(name) -> adapter instance
    claude.py                     Claude Code CLI wrapper (stream-json, --resume)
    codex.py                      Codex CLI wrapper (exec --json, exec resume)
    opencode.py                   OpenCode CLI wrapper (--format json, --session)
    hermes.py                     Hermes CLI wrapper (one-shot, no session)
    utils.py                      filtered_env() strips tokens from subprocess env
  agentd/
    server.py                     AgentDaemon — local HTTP server, one per agent identity
    client.py                     AgentdClient — HTTP client for bridges
  kook/
    bot.py                        KookBridge — WebSocket + HTTP polling bridge
    mentions.py                   KookMentionRouter — KMarkdown mention routing
  context/
    store.py                      ChatContextStore (SQLite WAL, TTL-based cleanup)
    prompt.py                     build_agent_prompt() — history + current message
  sessions/
    store.py                      SessionStore (scope_id + agent_id PK, turn tracking)
  routing/
    mentions.py                   MentionRouter — @name -> <@UID>, [handoff] detection
  security/
    allowlist.py                  Operator access control by user ID
cogs/
  agents.py                       dispatch, handoff extraction, webhook facade
  agent_request.py                core agent call/tag/fallback request workflow mixin
```

## N+M Runtime Architecture

In N+M mode (`agentd_mode=true`), each IM platform runs as a bridge that
submits requests to a local agentd daemon. One agentd per agent identity
ensures a single adapter session regardless of which platform triggers it.

```
Discord bridge ──┐
                 ├──> agentd (mac-codex)  ──> Codex adapter
KOOK bridge ─────┘──> agentd (mac-claude) ──> Claude adapter
```

- **Bridges** handle platform-specific: Gateway, polling, mention parsing, message sending
- **Agentd** handles: adapter call/resume, session management, timeout, health
- Communication: HTTP on localhost (bridge → agentd)
- Legacy mode (`agentd_mode=false`): bridges call adapters directly

## Message Flow

### Bridge Mode (agentd_mode=true)

```
Discord/KOOK message → Bridge
  → platform filter → mention resolution
  → build prompt with context history
  → AgentRequest → HTTP POST to agentd
  → AgentResponse → resolve handoff mentions
  → chunked reply + separate handoff messages
  → record to context store
```

### Legacy Mode (agentd_mode=false)

```
Discord message → DiscordClient.on_message()
  → channel filter → bot/human filter → mention resolution
  → operator command intercept
  → build_agent_prompt() with context history
  → adapter.call() or adapter.resume()
  → handoff mention resolution in response
  → chunked reply + separate handoff messages
  → record own response to context store
```

## Two-Layer Message Filter

1. **Bot messages**: require `respond_to_bots=true` + addressed (mention/!bang) + `[handoff]` prefix
2. **Human messages**: must be addressed, checked against `allowed_user_ids`

## Config Structure

`agents.toml`:
- `[defaults]` — shared timeouts, context params, security settings, agentd settings
- `[[agents]]` — managed agents (id, adapter, token_env, system_prompt, channels, discord_user_id)
- `[[external_agents]]` — external agents (id, display_name, aliases, discord_user_id)

## Key References

- Master plan: `docs/discord-multibot-plan/multi-bot-refactor-plan.md`
- Coordinator integration design: same file, "与 coordinate 的集成" section
- Platform setup: `docs/platform-setup.md`
- Phase 7 N+M plan: `docs/project-harness/tasks/phase-7-n-plus-m-runtime/plan.md`
