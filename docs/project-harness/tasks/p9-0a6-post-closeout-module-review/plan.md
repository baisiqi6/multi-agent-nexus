# Detailed Execution Plan: P9-0A6 Post-Closeout Module Review

> This is a documentation-only measurement and architecture-decision package. It does
> not authorize Coordinate production-code movement. If independent review or worker
> evidence demonstrates that one extraction is required now, this plan must be revised,
> re-reviewed, and re-approved before any code edit.

## Package identity and baseline

- Package: `p9-0a6-post-closeout-module-review`.
- Parent: P9-0A Coordinate internal boundary hardening.
- Required Coordinate baseline:
  `15020c2204e8e05c6304f6ed83a5fed83ad12eae` on `main == origin/main`.
- Required MultiNexus baseline: the commit that registers this exact plan and task;
  before plan creation, `main == origin/main == 2ba677011aa11babeaf8f34afeff973b9aeda0d6`.
- Existing Coordinate worktree exception: untracked `.qoder/` is user-owned and must
  remain untouched.
- Production identity at planning time:
  - Coordinate deployed/installed `15020c2`;
  - schema code/DB `11/11`, integrity `ok`;
  - MultiNexus deployed `2ba6770`;
  - managed services active and server smoke OK;
  - full production doctor after Slice 4 stage closeout: `rc=0`, projection errors `0`.
- Architect/operator/result reviewer: Codex.
- Independent plan reviewer and documentation worker: separate non-Codex sessions.
  Default provider/model is `kimi-code/kimi-for-coding-highspeed`; GLM is fallback only
  after a documented Kimi quota/auth/provider failure.

## Goal

Remeasure the post-P9-0A1–A5 and post-Slice-4 boundaries of `completion.py`, `db.py`,
and `transitions.py`, then make a durable, evidence-backed decision about whether one
stable transaction/repository/mutation seam should be extracted before Phase 9
runtime-isolation work.

The planned decision is **no production-code extraction in P9-0A6** unless the
independent review rejects this conclusion. P9-0A6 records the measurement and routes
specific candidates into Phase 9 package planning instead of moving code only to
reduce line counts.

## Current measured facts

At Coordinate `15020c2`:

| Module | Lines | Top-level functions | Classes | Slice-4 churn from `084419c` |
|---|---:|---:|---:|---:|
| `completion.py` | 1,038 | 26 | 8 | 0 commits, `+0/-0` |
| `db.py` | 1,798 | 54 | 6 | 4 commits, `+703/-75` |
| `transitions.py` | 1,391 | 28 | 9 | 0 commits, `+0/-0` |

Context only, not P9-0A6 extraction targets:

- `split_operations.py`: 3,013 lines, 12 Slice-4 commits, `+3013/-0`;
- `projection_doctor.py`: 2,112 lines, 7 Slice-4 commits, `+2112/-0`;
- `onboarding.py`: 1,061 lines.

Static dependency direction is acyclic at the measured boundary:

```text
db -> schema
completion -> db + harness
transitions -> completion + db + harness + reconcile
CLI/daemon -> transitions/completion
```

Observed cohesion:

- `completion.py` is one receipt state machine: gate/fingerprint plus
  authorized -> claimed -> applied -> task.done/consumed. The terminal consume path is
  intentionally atomic and shares evidence types with earlier states.
- `transitions.py` contains six similarly shaped harness mutations plus legacy and
  host-aware mark-done adapters. Repetition is real, but payloads, event types,
  idempotency keys, actor defaults, and failure evidence differ per operation.
- `db.py` is a broad repository facade. Agent-registry and split-operation work caused
  its recent Slice-4 churn; jobs/deliveries/events/task mirrors are future Phase 9
  isolation inputs.

## Why the planned decision is no-change

### Completion

Splitting the receipt state machine now would scatter one authority boundary and make
atomic-consume review harder. Line count alone is not evidence of separable ownership.
`completion_cli.py` already provides the presentation/transport seam.

### Transitions

Extracting a generic harness-mutation template would hide the operation-specific
payload and idempotency differences that current tests make explicit. Moving only the
mark-done adapters into another module would be a compatibility-facade exercise without
changing authority or Phase 9 isolation readiness.

Slice 4 closeout also proved that the current `review.phase` non-idempotency lives in
the external MultiNexus harness transition projection. Moving Coordinate wrapper code
would not fix that semantic defect and P9-0A forbids lifecycle behavior changes.

### DB

`db.py` has credible repository candidates, but it is the only target with heavy
Slice-4 churn. Extracting a repository before P9-1 defines job-scoped context and
transaction ownership risks choosing the wrong aggregate boundary and retaining a
large re-export facade. P9-0A6 should identify exact candidates and consumers for the
next plans, not pre-commit to a repository layout.

## Required worker measurement

The documentation worker must independently reproduce and record:

1. exact SHAs, dirty-state boundaries, deployment identities, schema/integrity, and
   final Slice 4 doctor evidence;
2. physical lines, top-level AST function/class counts, section/function ranges, and
   Slice-4 churn for the three target modules;
3. direct import directions, public import/re-export call sites, and existing test
   ownership;
4. transaction commits/rollbacks and authority boundaries, especially receipt consume,
   event append, task mirror, delivery, registry sync, and split-operation ledger;
5. concrete extraction candidates with estimated moved lines, caller count, cycle risk,
   compatibility-facade cost, semantic-test ownership, and Phase 9 consumer;
6. the repeated dogfood evidence for source harness, deployed harness, and control DB
   as distinct projections, including non-idempotent `review.phase` replay;
7. a scored decision for each target: extract now, defer to named Phase 9 package, or
   retain cohesive module.

The worker must stop and report rather than edit Coordinate code if its evidence
contradicts the planned no-change decision.

## Deliverables

Allowed worker-owned paths:

- `docs/project-harness/tasks/p9-0a6-post-closeout-module-review/measurement.md`;
- `docs/project-harness/tasks/phase-9-execution-isolation/plan.md` only to record the
  accepted P9-0A6 decision and route named follow-up boundaries;
- `docs/project-harness/roadmap.md` and `docs/project-harness/progress.md` only for the
  accepted status/next gate;
- `docs/project-harness/dogfood-feedback.md` only for a concise cross-reference to the
  already observed authority/projection findings.

The worker must not edit:

- any Coordinate production code or tests;
- any MultiNexus runtime code, tests, scripts, config, checklist, event ledger, current
  packet, or deployment marker;
- DB schema/data, production, services, Discord/KOOK delivery state, or receipts.

Lifecycle files and deployment are Operator-owned after Codex result review.

## Decision rubric

An extraction may be recommended for a revised plan only if all are true:

1. one owner/authority and one dependency direction are explicit;
2. transaction boundaries do not cross the proposed seam, or the seam owns the whole
   transaction;
3. public identity/call-site compatibility can be preserved without circular imports;
4. permanent tests can prove movement-only behavior and cold import orders;
5. the change directly enables a named P9-1+ isolation package;
6. the benefit is more than reducing file length or duplication;
7. the target is stable enough that current Slice-4 churn will not immediately reopen
   the boundary.

If no candidate satisfies all seven, the accepted deliverable is a documented no-change
decision plus exact routing to Phase 9 plans.

## Validation

- Re-run every measurement command from a clean shell and include command/output
  summaries in `measurement.md`.
- `git diff --check`.
- `bash scripts/harness/harnessctl validate` with only the four known historical
  warnings.
- `bash scripts/harness/harnessctl doctor` with only known missing optional/current
  artifacts.
- Confirm `git diff --name-only` contains only approved documentation paths.
- Confirm Coordinate `git status --short` still contains only user-owned `.qoder/` and
  `HEAD == origin/main == 15020c2`.
- No full code suite is required because the worker is forbidden to change code; cite
  the accepted S4-D baseline `1864 passed, 449 subtests passed, 9 historical failures`.

## Review and stop gates

The plan reviewer must reject if:

- the no-change decision is asserted from line count alone;
- transaction/public-identity/import-cycle/test evidence is missing;
- a dynamic “worker may extract if useful” permission remains;
- the package hides the recent `db.py` churn or the larger new Slice-4 modules;
- authority-projection dogfood is confused with a code-movement defect;
- production/runtime mutation is permitted.

After plan approval, a fresh documentation-worker bootstrap is required. Codex then
reviews the measurement and decision. Only a separately revised/re-reviewed package
may edit Coordinate code.
