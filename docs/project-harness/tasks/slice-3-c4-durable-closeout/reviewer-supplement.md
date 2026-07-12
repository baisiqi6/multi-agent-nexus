# S3-C4 Plan Reviewer Supplement

This supplement is authoritative when `reviewer-bootstrap.md` disagrees with it.
The generated bootstrap's `openspec/changes/...` path is a known generic-bootstrap
error. The canonical plan is:

`docs/project-harness/tasks/slice-3-c4-durable-closeout/plan.md`

Review is strictly read-only. Do not edit files, branches, worktrees, Git state,
checklist/event/state files, Coordinate DB state, services, sidecar data, or runtime.

## Bound revision

- Plan-ready event: `cb163ad0-9a34-4353-a585-dd954c325b0a`
- Full plan SHA-256:
  `6190b93f1ce28ed31d891019d758fddb01d1c7e01dda01b39fa2fb9b38cbe32b`
- MultiNexus plan commit: `eee2b70`

Before reviewing, independently recompute the plan SHA-256 and stop with `blocked` if
it differs.

## Required evidence

Read the canonical S3-C4 plan plus:

- `docs/project-harness/roadmap.md`
- `docs/project-harness/tasks/slice-3-completion-closeout/plan.md`
- `docs/project-harness/tasks/slice-3-completion-closeout/integration-decision.md`
- `docs/project-harness/tasks/slice-3-completion-closeout/local-code-review.md`
- `docs/project-harness/tasks/slice-3-c3-deployment-smoke/plan.md`
- `docs/project-harness/tasks/slice-3-c3-deployment-smoke/execution-report.md`
- `docs/project-harness/tasks/slice-3-c3-deployment-smoke/execution-report-attempt-2.md`
- `docs/project-harness/tasks/slice-3-c3-deployment-smoke/result-review-round-1.md`
- `docs/project-harness/tasks/slice-3-c3-deployment-smoke/result-review-round-2.md`
- `docs/project-harness/source-of-truth-audit.md`
- `docs/project-harness/dogfood-feedback.md`
- `docs/project-harness/mvp-checklist.json`

Read-only Git and text-search commands are allowed. Do not rely on chat summaries.

## Required review questions

1. Does the plan preserve separate code-review, integration, deployment,
   control-plane, worker-execution, dogfood, and durable-closeout verdicts?
2. Is the six-file worker scope sufficient to create durable evidence without
   rewriting historical S3-C1/S3-C2/S3-C3 artifacts or mutating lifecycle state?
3. Are retained sidecar data, stale interrupted-recovery projection, consumed failed
   drift fixtures, deploy non-atomicity, CLI ergonomics, and missing full-dogfood host
   profile kept visible and correctly routed?
4. Does the Operator-only closeout order prevent a documentation worker from approving
   itself, directly editing checklist/DB state, hiding a lifecycle rejection, or
   prematurely starting Slice 4/Phase 9 implementation?
5. Are failure/recovery and acceptance matrices strong enough for an already executed
   split-host operation, especially runtime identity drift, canonical drift, receipt
   interruption, and public lifecycle rejection?
6. Are validation requirements proportionate for a documentation-only worker while
   still requiring Codex to refresh live runtime and receipt evidence independently?
7. Does any step silently authorize sidecar cleanup, deploy/restart, DB repair, push,
   direct JSON/SQLite mutation, or historical evidence rewriting?
8. Identify any P0/P1 must-fix issue that would allow false Slice 3 closure or lose
   source-of-truth provenance. Separate optional improvements from must-fix findings.

## Verdict format

Return `approve`, `changes_requested`, or `blocked`, with:

- reviewed plan-ready event and full SHA-256;
- answers to all eight questions;
- must-fix findings by priority;
- optional findings separately; and
- exactly one final machine-readable block:

```text
[agent-report]
decision=approve|reject|blocked
workspace_id=discord-nexus
task_id=slice-3-c4-durable-closeout
summary="<bounded verdict>"
```

Use `decision=reject` for `changes_requested` because the agent-report protocol has no
separate `changes_requested` enum. The prose verdict remains authoritative.
