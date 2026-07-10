# MultiNexus Domain Model

> **Status: current MultiNexus-owned runtime entities.** Product-level Operator,
> Coordinate, Harness, and Executor definitions live in [product-definition.md](product-definition.md).

## Runtime entities

### AgentConfig

Configuration for one managed agent identity and adapter. It includes runtime identity,
adapter type, work directory, timeout, platform identity, known peers, session behavior,
and agentd settings. Configuration does not grant project-level Operator authority.

### KnownAgentMention

Platform routing identity for a managed or external peer. Aliases and platform IDs allow
handoffs to resolve to native mentions. This is routing metadata, not an agent registry
for durable project ownership.

### AgentRequest

Platform-neutral invocation envelope. It carries a request ID, target agent, prompt,
origin/destination metadata, author, session scope, and optional managed-handoff context.

### AgentResponse

Platform-neutral result envelope. It carries request/agent identity, output text,
session ID, success classification, handoff/report lines, timing, and structured runtime
metadata. It is execution evidence, not automatic acceptance or completion.

### AdapterResult

Executor-specific call/resume result normalized by an adapter. Current common fields
include text, session ID, resumed status, and metadata. Adapters may preserve richer
vendor capabilities in metadata rather than flattening every executor to prompt/text.

### AgentdWorker

Long-running worker for one managed agent identity. It registers with Coordinate,
claims eligible jobs, invokes the adapter, reports liveness/progress, and returns a
structured terminal result. Coordinate remains authoritative for the managed job.

### Bridge

Platform-specific ingress and egress runtime. A bridge handles Gateway or polling,
identity, allowlists, mention resolution, message formatting, and visible delivery.
It does not own project workflow state.

### Session

Mapping from `(scope_id, agent_id)` to an executor-native session identifier and runtime
metadata. It supports resume across visible turns but remains replaceable scratch state;
the project must still be recoverable without it.

### ContextMessage

Visible conversation record stored for prompt construction with TTL and budget limits.
It may improve continuity but is not a source of truth for project completion.

## Agent kinds

| Kind | Invocation ownership | Session handling | Examples |
|---|---|---|---|
| Managed | MultiNexus adapter/agentd | MultiNexus plus executor-native session | Claude Code, Codex, OpenCode, OMP |
| External gateway | External runtime | External runtime | OpenClaw, Hermes gateway |
| Compound executor | Parent managed/external runtime | Executor-defined internally | Agent team, subagent graph, native workflow |

## Relationships

```text
AgentConfig
  ├── selects Adapter
  ├── identifies AgentdWorker
  ├── owns scoped Sessions
  └── references KnownAgentMention peers

Bridge
  ├── creates AgentRequest
  ├── may submit a managed job through Coordinate
  └── renders AgentResponse to a platform

AgentdWorker
  ├── claims Coordinate Job
  ├── invokes Adapter
  └── reports progress and AgentResponse
```

## Ownership summary

| Fact | Authority |
|---|---|
| Adapter invocation, resume, native session, local runtime health | MultiNexus/runtime |
| Managed job and attempt lifecycle | Coordinate DB |
| Platform identity and routing configuration | MultiNexus configuration |
| Project plan, acceptance, task completion | Harness plus required evidence |
| Internal compound-agent graph | Owning Executor unless promoted to managed delegation |
