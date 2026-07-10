# MultiNexus Scope

> **Status: current MultiNexus repository boundary.** The shared product position is
> defined in [product-definition.md](product-definition.md).

## Project

MultiNexus is an agent execution fabric. It connects replaceable managed and external
agent runtimes to Operator- or Coordinate-initiated work while preserving each
executor's native subagents, teams, skills, plugins, and workflows.

Discord and KOOK are current visible adapters. They are not the product boundary and
are not durable project-state authorities.

## In scope

- Managed agent adapters for Claude Code, Codex, OpenCode, Hermes, OMP, and compatible runtimes.
- External gateway agent registration and platform mention routing.
- Platform-neutral `AgentRequest`, `AgentResponse`, and adapter result envelopes.
- Agent invocation, resume, timeout, health, progress, and structured result return.
- Per-agent session persistence and scoped conversation context.
- N+M runtime topology: platform bridges share one agentd per managed agent identity.
- Discord and KOOK bridge behavior, filtering, identity mapping, commands, and delivery.
- Intake of Coordinate-managed handoffs and jobs.
- Internal handoff parsing for conversational collaboration.
- Host-specific runtime configuration and lifecycle scripts.

## Out of scope

- Product-level planning, acceptance, review judgment, or permanent Operator behavior.
- Coordinate-owned events, jobs, deliveries, runtime claims, task mirrors, and forge gates.
- Defining or directly editing the reusable harness protocol.
- Reimplementing the internal workflow graph of a compound executor.
- Owning Git commits, PRs, CI results, review decisions, or project completion.
- Requiring every internal subagent action to become a top-level managed job.
- Treating platform transcripts or agent session memory as project truth.

## Boundaries

- MultiNexus owns agent-runtime invocation and agent-local session state.
- Coordinate owns managed runtime job records and durable cross-runtime execution events.
- The current human or agent Operator chooses what work to delegate and how to evaluate it.
- The harness owns accepted project intent, plan, acceptance criteria, and coarse workflow.
- Internal delegation remains the parent Executor's responsibility unless it needs an independent lifecycle.
- Managed delegation is registered with Coordinate and may be executed through MultiNexus agentd.
- `docs/project-harness/` is the active harness for this managed integration project.
- External/upstream code repositories use a sidecar `harness_root`; deploy copies such as `/opt/multinexus` are not development sources of truth.
