# MultiNexus Architecture

> **Status: current runtime architecture.** Shared product roles and authority rules are
> defined in [product-definition.md](product-definition.md).

## Position in the system

```text
Human or agent Operator
        │
        ├── direct interaction ───────────────┐
        │                                     ▼
        └── Coordinate managed job ──> MultiNexus execution fabric
                                              ├── agentd / session / context
                                              ├── Claude Code / Codex / OpenCode / OMP
                                              ├── external OpenClaw / Hermes gateways
                                              └── Discord / KOOK / future bridges
```

MultiNexus executes agent work and returns structured runtime results. It does not own
project lifecycle decisions, durable Coordinate jobs, harness acceptance, or forge truth.

## Entry points

- `python multinexus.py --config agents.toml --platform discord` — current per-platform Discord bridge hosting N configured agent identities.
- `python multinexus.py --config agents.toml --agent <id>` — compatibility mode hosting one Discord client for one agent.
- `python -m multinexus.agentd --config agents.toml --agent <id>` — one Coordinate-connected worker daemon per managed agent identity.
- KOOK uses the dedicated bridge modules and deployment scripts under `multinexus/kook/` and `scripts/`.

## Module map

```text
multinexus.py                         Discord bridge/compatibility entry point
multinexus/
  client.py                          DiscordBridge + DiscordClient
  config.py                          agents.toml loading and validation
  models.py                          agent and peer configuration
  protocol.py                        platform-neutral request/response envelopes
  coordinator_handoff.py             managed handoff intake and lifecycle glue
  commands.py / embeds.py            visible operator commands and views
  handoff.py / routing/               handoff parsing and mention resolution
  adapters/                           executor-specific call/resume/health adapters
  agentd/                             Coordinate-connected agent worker runtime
  context/                            scoped visible conversation context
  sessions/                           executor session persistence
  kook/                               KOOK bridge and mention routing
  security/                           operator allowlist and subprocess environment filtering
cogs/
  agent_request.py / agents.py        shared request workflow and compatibility facade
```

## N+M runtime

Platform bridges and agent runtimes are separated so one agent identity does not need
one process per platform.

```text
Discord bridge ──┐
                 ├──> Coordinate runtime job ──> agentd (mac-codex)  ──> Codex adapter
KOOK bridge ─────┘                         └────> agentd (mac-claude) ──> Claude adapter
```

- **Bridge:** platform Gateway/polling, identity, filtering, mention routing, rendering.
- **Coordinate:** managed job, claim, attempt, liveness, result, and delivery records.
- **Agentd:** adapter invocation, resume, timeout, progress, result reporting.
- **Adapter:** executor-specific CLI or API behavior.

The compatibility path may invoke an adapter directly from a bridge. New managed project
execution should use Coordinate plus agentd when it needs durable lifecycle and recovery.

## Execution flows

### Direct interaction

```text
platform message
  → bridge filtering and routing
  → scoped context construction
  → adapter call/resume
  → structured AdapterResult
  → response rendering and context persistence
```

This is appropriate for conversational interaction or execution whose lifecycle remains
the responsibility of the current agent session.

### Coordinate-managed execution

```text
Coordinate job
  → agentd claim with attempt token
  → adapter call/resume in configured workspace
  → heartbeat/progress
  → structured AgentResponse/report
  → Coordinate records terminal event and visible delivery
```

This is appropriate when work needs independent recovery, reassignment, cancellation,
review, permissions, or cross-host execution.

### Executor-internal delegation

An adapter may invoke a compound executor that creates its own subagents or workflow.
MultiNexus does not flatten that internal graph. The parent invocation is responsible
for returning a coherent result unless a child is explicitly promoted to a
Coordinate-managed job.

## Runtime state ownership

| State | Owner |
|---|---|
| Adapter invocation and native session id | MultiNexus / executor runtime |
| Scoped visible conversation context | MultiNexus context store |
| Managed job, attempt, liveness, and terminal event | Coordinate DB |
| Project plan, acceptance, and coarse workflow | Harness files |
| Code and forge state | Git / configured forge |
| Platform transcript | Platform, as a visible non-authoritative record |

## Key references

- Shared product definition: `docs/project-harness/product-definition.md`
- Cross-stage roadmap and plan gates: `docs/project-harness/roadmap.md`
- Repository scope: `docs/project-harness/scope.md`
- Runtime entities: `docs/project-harness/domain-model.md`
- Agent configuration: `docs/agents.md`
- Deployment: `docs/deploy-runbook.md`, `docs/platform-setup.md`
- Historical Discord refactor plan: `docs/discord-multibot-plan/multi-bot-refactor-plan.md`
