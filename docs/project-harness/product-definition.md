# Coordinate + MultiNexus Product Definition

> **Status: canonical cross-repository product definition.**
>
> This document defines the shared product position and responsibility boundaries
> of Coordinate and MultiNexus. Repository-specific documents may add implementation
> detail, but they must not redefine these terms or duplicate this document as a
> second editable source of truth.

## Mission

Coordinate and MultiNexus form an agent-independent project execution layer.
Any authorized human or agent may temporarily act as the Operator, use the same
durable harness and execution ledger, and delegate work to replaceable compound
agents such as Claude Code, Codex, OpenCode, OpenClaw, Hermes, or OMP.

The system is successful when the Operator and executors can change without losing:

- project intent and acceptance criteria;
- current execution state and recovery information;
- responsibility for review and closeout;
- the causal and audit trail of material actions.

The durable project execution loop is the product. Cross-agent invocation by
stdin, plugin, skill, SDK, IM mention, or subprocess is only an execution primitive.

## Core invariants

1. **Operator and executors are replaceable.** No single agent session owns the project.
2. **Coordinate is not the permanent coordinator.** It records and enforces deterministic
   coordination mechanics; the current Operator makes judgments.
3. **Nested agent systems remain opaque by default.** A Claude Code agent team or a
   Codex workflow may be treated as one compound executor unless its child work needs
   an independent lifecycle.
4. **Every fact has one authority.** Copies used for display, caching, or recovery are
   projections and must be rebuildable or explicitly reconciled.
5. **Visible conversation is not durable project state.** Discord, KOOK, terminals, and
   chat transcripts are interaction surfaces, not the final authority for completion.
6. **Completion is evidence-based.** A worker response is not equivalent to accepted,
   reviewed, merged, or closed work.
7. **Vendor capabilities are composable.** Native subagents, agent teams, skills, plugins,
   and workflow engines are capabilities of an executor, not competing control planes.

## Roles and components

### Operator

The Operator is the currently authorized decision-maker. It may be a human or an
agent. The Operator reads durable state, selects the next action, delegates work,
handles escalation, and decides when the evidence is sufficient to advance a gate.

An Operator role is temporary and scoped. Changing Operator must not require moving
or reconstructing project truth from the previous agent's conversation.

### Coordinator

Coordinator is a runtime role, not a permanently assigned product component. An
Operator acts as coordinator when it decomposes, routes, reviews, or advances work.
The role may move between a human, Codex, Claude Code, or another capable agent.

Existing source identifiers that use `coordinator` are compatibility names. They do
not imply that Coordinate owns AI judgment.

### Coordinate

Coordinate is the deterministic coordination kernel and durable control-plane toolkit.
It owns mechanics such as:

- workspace, job, event, delivery, runtime claim, and runner records;
- idempotent lifecycle transitions and recovery;
- durable outbox delivery to visible surfaces;
- runner dispatch and managed handoff records;
- GitHub branch, PR, CI, review, and merge-gate evidence;
- reconciliation and drift reporting.

Coordinate may expose tools used by an Operator, but it must not silently become an
autonomous product-level decision-maker. A replaceable Operator or explicit policy
backend supplies judgment.

### MultiNexus

MultiNexus is the agent execution fabric. It connects managed and external agent
runtimes to project work through replaceable adapters and platform bridges. It owns:

- agent adapter invocation, resume, timeout, and health;
- agent-local session and conversation context;
- platform-neutral request and response envelopes;
- Discord, KOOK, and future interaction bridges;
- intake of managed handoffs and return of structured execution results.

Discord and KOOK are useful visible surfaces, not the boundary of MultiNexus or of
the overall product. A direct CLI, API, plugin, or future platform may use the same
execution fabric.

### Harness

The harness is durable project memory and the project-level protocol. It records
accepted scope, constraints, plans, acceptance criteria, human-readable progress,
and task artifacts. It must remain understandable without access to a particular
agent session.

Machine-readable harness state is a projection of canonical harness files, not an
additional hand-edited truth.

### Executor

An Executor is a replaceable agent runtime that performs delegated work. It may be a
single agent process or a compound system with its own subagents, teams, skills, and
workflow engine. Executors do not own project-level truth merely because they own
their internal execution graph.

## Delegation boundary

The system supports two delegation modes.

### Internal delegation

Internal delegation stays inside a parent Executor:

- the parent retains responsibility for the result;
- child steps do not require independent recovery or authority;
- Coordinate may record only the parent run and its final structured result;
- the Executor may freely use native subagents, agent teams, or workflows.

### Managed delegation

Delegation becomes managed when the child work needs any of the following:

- an independent lifecycle, lease, budget, or permission scope;
- execution on another host or runtime;
- externally visible side effects;
- separate review or acceptance;
- recovery after the parent session disappears;
- direct inspection, cancellation, retry, or reassignment by the Operator.

Managed delegation is registered as a child job/run through Coordinate and executed
through MultiNexus or another runner adapter. The distinction is responsibility and
lifecycle, not whether the call happens through stdin, a plugin, an SDK, or a network.

## Source-of-truth ownership

Redundancy is allowed for audit, caching, and presentation. Duplicate authority is not.

| Fact | Authority | Derived or non-authoritative views |
|---|---|---|
| Product mission, shared roles, cross-repo boundaries | This document | README summaries, prompts, diagrams |
| Project scope, constraints, plans, acceptance, coarse task workflow, assignment owner/lease | Canonical harness files | `harness-state.json`, packets, dashboards |
| Runtime jobs, claim tokens, runner attempts, liveness, deliveries, durable execution events | Coordinate database | CLI output, status pages, IM notifications |
| Code, commits, branches | Git | Coordinate references and mirrors |
| PR, CI, review, merge state | GitHub or the configured forge | Coordinate's last-known gate evidence |
| Agent invocation, session resume, runtime health, local context | MultiNexus or the owning runtime | Coordinate job summaries |
| Human-visible conversation | The platform transcript for what was said | Context summaries and memory extraction |
| Product/project completion | Harness acceptance plus required runtime and forge evidence | Worker claims, chat acknowledgements |

Rules for all projections:

1. A projection must declare its authority and refresh path.
2. Reconciliation may repair a projection or report drift; it must not silently
   overwrite the authoritative source.
3. Bidirectional free-form synchronization of the same fact is prohibited.
4. A historical document must be labeled historical and excluded from current
   navigation paths.

## Repository boundaries

### `coordinate`

The Coordinate repository owns the deterministic coordination kernel, its schemas,
services, policies, adapters, operational tooling, and implementation documentation.
It does not own MultiNexus runtime internals or the cross-repository product definition.

### `multinexus`

The MultiNexus repository owns the agent execution fabric, adapters, bridges, sessions,
runtime envelopes, deployment instructions, and its active project harness. The active
harness currently hosts this shared definition because it is the integration project's
durable planning location; that placement does not make MultiNexus the control plane.

## Non-goals

- Reimplement every vendor's internal multi-agent workflow.
- Flatten all agents to a lowest-common-denominator prompt-to-text interface.
- Require Discord or KOOK for project execution.
- Make every internal subagent visible to the top-level control plane.
- Let Coordinate, MultiNexus, or one flagship agent become the sole owner of project truth.
- Treat activity, a successful process exit, or a plausible response as completion.

## Decision test

Before adding a component, state field, document, or workflow, ask:

1. Does it improve durable responsibility, recovery, authority, evidence, or executor
   replaceability?
2. Which fact does it own, and where is that fact authoritative today?
3. Can an existing projection or adapter solve the need without creating another truth?
4. Does it preserve the ability to use a vendor's native compound-agent capabilities?

If these questions have no concrete answer, the addition should not enter the core.
