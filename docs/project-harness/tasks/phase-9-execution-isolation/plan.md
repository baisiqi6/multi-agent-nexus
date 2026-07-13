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

Status on 2026-07-13: P9-0A1, all P9-0A2a/b/c packages, both P9-0A3a/b, and
both P9-0A4a/b are durably `done/closed`; exact evidence is
indexed in `../p9-0a1-cli-boundary-extraction/closeout.md` and
`../p9-0a2a-workspace-state-reconcile-cli/closeout.md` plus
`../p9-0a2b-event-task-plan-operator-cli/closeout.md` plus
`../p9-0a2c-issue-cli/closeout.md` plus
`../p9-0a3a-runner-job-runtime-cli/closeout.md` plus
`../p9-0a3b-delivery-policy-worker-cli/closeout.md` plus
`../p9-0a4a-receipt-completion-cli/closeout.md` plus
`../p9-0a4b-workflow-assignment-cli/closeout.md` plus
`../p9-0a5-event-presentation-registry/closeout.md`. Measured post-closeout scope
split the former combined P9-0A2 into P9-0A2a/b/c. Fresh measurement similarly splits
the former combined P9-0A3 into P9-0A3a/b and the former P9-0A4 into P9-0A4a/b.
P9-0A1 through P9-0A5 are now durably closed. Slice 4 is the next executable stage;
its historical overview is not worker authorization until refreshed detailed planning,
independent review, Coordinate approval, and a fresh bootstrap complete.

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
5. `p9-0a3a-runner-job-runtime-cli` — **done/closed**: moved runner/job/runtime
   registration and 16 handlers behind `execution_cli` with three static registrar
   call sites.
6. `p9-0a3b-delivery-policy-worker-cli` — **done/closed**: separately moved the
   contiguous delivery/policy/worker registration and 10 handlers behind `delivery_cli`.
7. `p9-0a4a-receipt-completion-cli` — **done/closed**: moved the six receipt-aware
   assignment leaves and their 14 orchestration/helper functions behind
   `completion_cli`; root still owns the assignment parser and supplies its subparser
   to the registrar.
8. `p9-0a4b-workflow-assignment-cli` — **done/closed**: moved branch/CI/review/merge and assignment;
   `workflow_cli` owns the assignment parser and invokes the already extracted
   `completion_cli` registrar with its supplied subparser.
9. `p9-0a5-event-presentation-registry` — **done/closed**: `event_presentation.py`
   owns the 44 pure text/base-payload functions and 34-key renderer registry; `policy`
   remains the facade and the 34 supported = 34 rendered = 31 styled + exact 3
   explicitly unstyled relationship is executable evidence.
10. `p9-0a6-post-closeout-module-review` — **done/closed**: measured
    `completion.py`, `db.py`, and `transitions.py` after Slice 4 closeout and
    accepted **no production-code extraction**. Exact evidence is in
    `../p9-0a6-post-closeout-module-review/closeout.md`. The accepted decision
    routes repository seams into later Phase 9 packages instead of moving code only
    to reduce line counts. Terminal receipt:
    `15e7d03f-43af-42ab-92cb-dfc5fc06c00b`:
    - job repository candidates -> P9-1 job-scoped execution context;
    - delivery/event repository candidates -> P9-1 context first, then P9-4 observation contract if needed;
    - agent registry repository candidates -> P9-2 executor routing and instance identity;
    - split-operation ledger candidates -> remain a Slice-4 primitive, revisit only when P9-1 context stabilizes;
    - `completion.py` receipt state machine and `transitions.py` harness mutations -> retain as cohesive authority modules; no further P9-0A extraction.

P9-0A must not alter lifecycle authority, completion receipt semantics, DB schema,
delivery defaults, runtime behavior, or public CLI contracts. Keep one Python package
and an explicit static composition root; do not introduce plugin discovery or a DI
framework. Each package requires its own detailed plan and independent review.

### P9-1 — Job-scoped execution context

Coordinate claim/handoff returns authoritative host-resolved workspace, worktree,
branch, harness, session-scope, and log handles. MultiNexus agentd uses the job context
instead of a fixed agent `work_dir`. Remove MultiNexus direct reads of Coordinate
SQLite tables from the managed execution path.

Status (2026-07-13): deployed and durably closed. See
`tasks/p9-1-job-scoped-execution-context/deployment-dogfood.md`.

### P9-2 — Executor routing and instance identity

Separate logical target capability, eligible executor instances, runner profile, and
concrete assignment. First version uses explicit deterministic routing based on
capability, workspace authorization, host, health, load, and Operator override; it is
not a speculative autonomous scheduler.

Status (2026-07-13): P9-2A identity catalog and P9-2B deterministic routing are
deployed and durably closed. See
`tasks/p9-2a-executor-identity-registry/closeout.md` and
`tasks/p9-2b-deterministic-executor-routing/closeout.md`.

### P9-3 — Capacity and resource leases

Add executor capacity, attempt lease, normalized worktree mutual exclusion, stale
lease recovery, and a documented queue-order/fairness rule. Different worktrees may
run concurrently; the same worktree is exclusive by default.

Status: next detailed-plan gate. No implementation is authorized until refreshed
measurement, independent plan review, and exact-revision approval complete.

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
