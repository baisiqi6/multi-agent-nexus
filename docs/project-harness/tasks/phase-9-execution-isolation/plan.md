# Phase 9 Multi-Project Execution Isolation

> **Plan level: roadmap overview.** This phase must be implemented through bounded
> work packages with reviewed detailed plans, not as one broad architecture rewrite.

## Goal

Safely run multiple projects, task lines, providers, and executor instances without
session, workspace, worktree, queue, log, authority, or result contamination while
preserving vendor-native compound-agent capabilities.

## Dependency

Architecture contract work may start during Slice 4. Runtime implementation requires
accepted Slice 4 authority/registry/partial-operation foundations.

## Work packages

### P9-0 — Execution identity and contract

Define and review the minimum domain separation:

- `ExecutorDefinition`: logical capability/provider.
- `ExecutorInstance`: concrete process/host identity.
- `RunnerProfile`: invocation/transport mechanics.
- `Job`: managed execution record.
- `Attempt`: one claim/retry generation.
- `ExecutionContext`: job-scoped project/worktree/harness/log context.
- `ResourceLease`: bounded occupancy of an executor instance or worktree.

Do not add schema or abstractions until the contract identifies current concrete
callers, compatibility mappings, and migration order.

### P9-1 — Job-scoped execution context

Coordinate claim/handoff returns authoritative host-resolved workspace, worktree,
branch, harness, session-scope, and log handles. MultiNexus agentd uses the job context
instead of a fixed agent `work_dir`. Remove MultiNexus direct reads of Coordinate
SQLite tables from the managed execution path.

### P9-2 — Executor routing and instance identity

Separate logical target capability, eligible executor instances, runner profile, and
concrete assignment. First version uses explicit deterministic routing based on
capability, workspace authorization, host, health, load, and Operator override; it is
not a speculative autonomous scheduler.

### P9-3 — Capacity and resource leases

Add executor capacity, attempt lease, normalized worktree mutual exclusion, stale
lease recovery, and a documented queue-order/fairness rule. Different worktrees may
run concurrently; the same worktree is exclusive by default.

### P9-4 — Provider-neutral observation contract

Expose bounded `provider_session_id`, JSONL/native log handle, progress stage,
heartbeat, last-activity time, process/session exit evidence, and provider failure
classification. Observation proves activity/liveness, not correctness or completion.

### P9-5 — Multi-line dogfood matrix

Validate at least:

- project A with Claude and project B with OhMyPi concurrently;
- two projects using the same provider through different instances;
- one project with distinct worktrees concurrently;
- same-worktree conflict rejection or waiting;
- crash/retry without stale-attempt overwrite;
- provider overload isolated to the affected job;
- Operator/session replacement without loss of durable state;
- reviewer execution through a third agent without mutation of worker evidence.

## Architectural constraints

- Coordinate remains the deterministic control plane; MultiNexus remains the
  execution fabric.
- No third project-level control plane or duplicate lifecycle authority.
- Internal vendor subagents remain opaque unless promoted to managed jobs.
- Prefer composition and explicit contracts over inheritance or provider-specific
  branches in the core.
- CLI/subprocess may remain a transport adapter initially; direct cross-repository DB
  reads may not remain the managed contract.
- Every new projection declares its authority and rebuild/reconcile path.

## Non-goals

- Reimplementing Claude/Codex/Hermes/OpenClaw workflow engines.
- Flattening every provider to a lowest-common-denominator feature set.
- Building a general distributed scheduler before explicit routing and leases are
  proven insufficient.
- Automatic merge/deploy/closeout judgment.

## Stage acceptance

- The dogfood matrix passes with durable, independently reviewed evidence.
- Job execution directory and session/log scope are job-specific and workspace-safe.
- Executor/provider identity is not conflated with one runner or one project path.
- Same-resource conflicts fail closed; retry and recovery preserve attempt authority.
- Cross-repository contracts are versioned and compatibility-tested.
- No project line can advance another project's lifecycle or reuse its private session.
