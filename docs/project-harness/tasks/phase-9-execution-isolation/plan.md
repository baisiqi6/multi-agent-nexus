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

### P9-0A — Coordinate internal boundary hardening

Reduce change concentration before Phase 9 adds execution identity, context, routing,
and lease commands. This is a behavior-preserving modularization stage, not a package,
service, schema, or framework rewrite.

P9-0A runs after durable Slice 3 closeout and before Slice 4 so Slice 4 command and
projection work lands in extracted domain modules. Phase 9 runtime isolation (`P9-1+`)
remains blocked until Slice 4 is accepted. Every structural package still requires a
fresh drift check, detailed plan, independent review, worker bootstrap, and Codex result
review.

Status on 2026-07-12: P9-0A1 and all P9-0A2a/b/c packages are durably `done/closed`; exact evidence is
indexed in `../p9-0a1-cli-boundary-extraction/closeout.md` and
`../p9-0a2a-workspace-state-reconcile-cli/closeout.md` plus
`../p9-0a2b-event-task-plan-operator-cli/closeout.md` plus
`../p9-0a2c-issue-cli/closeout.md`. Measured post-closeout scope
split the former combined P9-0A2 into P9-0A2a/b/c. P9-0A3 is the next executable
package; prior approvals/bootstrap do not authorize it or its siblings.

Bounded packages:

1. `p9-0a1-cli-boundary-extraction` — **done/closed**: captured the exact CLI contract
   and extracted the tiny shared `cli_support` seam. No domain handler moved.
2. `p9-0a2a-workspace-state-reconcile-cli` — **done/closed**: moved workspace/state/
   reconcile registration and 11 handlers behind `workspace_cli`; preserved exact
   command ordering and all non-handler contract bytes.
3. `p9-0a2b-event-task-plan-operator-cli` — **done/closed**: separately moved
   event/task/plan/operator registration and handlers behind `planning_cli`.
4. `p9-0a2c-issue-cli` — **done/closed**: separately moved issue registration and
   handlers behind `issue_cli`.
5. `p9-0a3-execution-delivery-cli` — move runner/job/runtime and
   delivery/policy/worker families behind static registrars.
6. `p9-0a4-workflow-completion-cli` — move branch/CI/review/merge and assignment;
   `workflow_cli` owns the assignment parser while `completion_cli` registers the
   receipt-aware mark-done leaf commands into its supplied subparser.
7. `p9-0a5-event-presentation-registry` — keep `policy.py` as the orchestration facade;
   extract only the pure event text/base-payload renderer registry and lock supported,
   rendered, and explicitly unstyled event-key relationships.
8. `p9-0a6-post-closeout-module-review` — after P9-0A CLI/presentation extraction and
   Slice 4, remeasure `completion.py`, `db.py`, and `transitions.py`. Extract only a
   proven stable transaction/repository/mutation seam; a documented no-change decision
   is acceptable.

P9-0A must not alter lifecycle authority, completion receipt semantics, DB schema,
delivery defaults, runtime behavior, or public CLI contracts. Keep one Python package
and an explicit static composition root; do not introduce plugin discovery or a DI
framework. Each package requires its own detailed plan and independent review.

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
