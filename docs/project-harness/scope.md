# Scope

## Project

multinexus: multi-agent Discord bot framework connecting AI coding agents (Claude Code, Codex, OpenCode, Hermes) as distinct Discord bot users.

## In Scope

- **Managed coding agents**: mac-claude, mac-codex, mac-opencode — launched by `multinexus.py --agent <id>`, wrapped in adapter subprocess
- **External gateway agents**: 小龙虾 (OpenClaw), Hermes — own Discord Gateway; multinexus does handoff routing only
- **Handoff protocol**: `[handoff] @AgentName task` parsed and resolved to Discord `<@USER_ID>` mentions
- **Per-agent session persistence**: scope_id + agent_id composite key, SQLite-backed, supports resume
- **Context management**: recent channel history injected into agent prompts, configurable TTL/budget/limit
- **Adapter layer**: claude, codex, opencode, hermes — CLI subprocess wrappers with streaming JSON output
- **Slash commands**: /agents, /health, /session status, /session reset
- **launchd lifecycle**: macOS user-level LaunchAgents with auto-restart
- **Coordinator handoff intake**: managed agents can auto-accept structured `[handoff]` messages from the configured coordinator bot, then read the generated bootstrap before invoking the adapter

## Out of Scope

- **multi-agent-coordinator**: separate project (`~/projects/multi-agent-coordinator`), owns task assignment, event pipeline, Discord delivery daemon, targeted agent handoff generation, CI/review/merge gate state
- **Harness protocol files**: schema and lifecycle owned by coordinator + harnessctl mutation service, not hand-edited
- **Legacy single-bot architecture** (`bot.py`, `cogs/`, `agents/`): being replaced by `multinexus.py`, retained for reference only
- **washer.py** (memory extraction pipeline): runs independently
- **Platform deployment** (systemd, Windows): Phase 5

## Boundaries

- multinexus is the **agent runtime layer** — it starts agents, routes messages, manages sessions
- coordinator is the **control plane** — it tracks tasks, events, deliveries, assignment leases, branch/PR/CI/review state, and generates visible handoffs
- harness is the **protocol layer** — file-backed state between the two
- ordinary task lifecycle mutations must go through coordinator CLI; harnessctl is for coordinator internals and explicit operator repair
