# Architecture

## Entry Point

`multinexus.py --config agents.toml --agent <id>` — one process per managed agent.

## Module Map

```
multinexus.py                          CLI entry point
multinexus/
  client.py                       DiscordClient (discord.Client + CommandTree)
  config.py                       TOML config loading, [defaults] + [[agents]] merge
  models.py                       AgentConfig, KnownAgentMention dataclasses
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
  context/
    store.py                      ChatContextStore (SQLite WAL, TTL-based cleanup)
    prompt.py                     build_agent_prompt() — history + current message
  sessions/
    store.py                      SessionStore (scope_id + agent_id PK, turn tracking)
  routing/
    mentions.py                   MentionRouter — @name -> <@UID>, [handoff] detection
  security/
    allowlist.py                  Operator access control by user ID
```

## Message Flow

```
Discord message → DiscordClient.on_message()
  → channel filter → bot/human filter → mention resolution
  → operator command intercept (session status, agents, health)
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
- `[defaults]` — shared timeouts, context params, security settings
- `[[agents]]` — managed agents (id, adapter, token_env, system_prompt, channels, discord_user_id)
- `[[external_agents]]` — external agents (id, display_name, aliases, discord_user_id)

## Key References

- Master plan: `docs/discord-multibot-plan/multi-bot-refactor-plan.md`
- Coordinator integration design: same file, "与 multi-agent-coordinator 的集成" section
- Platform setup: `docs/platform-setup.md`
