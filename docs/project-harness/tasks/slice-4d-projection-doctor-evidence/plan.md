# Detailed Execution Plan: Slice 4D Projection Doctor and Repair Evidence

> **Status:** in_review
>
> This is an execution gate, not worker authorization. Implementation starts only
> after an independent non-Codex reviewer approves this exact revision, Coordinate
> records that approval, and Codex generates a fresh worker bootstrap.

## Identity and revision

- Parent stage: `slice-4-projection-hardening`, S4-D.
- Package id: `slice-4d-projection-doctor-evidence`.
- Plan author / architect: Codex.
- Intended plan reviewer: non-Codex Kimi reviewer.
- Intended coding worker: non-Codex Kimi worker after approval.
- Intended code/result reviewer: Codex.
- Plan path:
  `docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan.md`.
- Plan revision: exact SHA-256 computed after commit.
- Supersedes: none.
- Provider route: `kimi-code/kimi-for-coding-highspeed`; GLM is fallback only after
  documented Kimi quota/auth/provider failure.

## Refreshed preflight

- Required Coordinate start:
  `a21d946e4d6be78f3f481d38eb2571229a4d3a9f` on `main`, equal to upstream.
- Required MultiNexus start:
  `347c7850aab71144d1c681789f3d0f622c678d13` on `main`, equal to upstream.
- Coordinate schema: v11; neutral `split_operations` is deployed.
- Production registry authority: `multinexus.discord` v1 / revision 1 / source hash
  `95bdad3b3d1f0526873e4acd8156ba296d6aa153fb11d5c9e6ddc4482212213b`.
- Production split ledger: one C1 `task.create` row and zero `issue.materialize` rows.
- Runtime: Coordinate `a21d946`, MultiNexus `347c785`; schema v11 / integrity `ok`;
  Coordinate PID `653825`, bridge PID `341847`, zero restarts, `server smoke OK`.
- Existing `workspace doctor` in `src/coordinate/doctor.py` diagnoses filesystem and
  harness capability but not registry/split-operation/mirror/receipt projections.
- Existing `workspace audit` in `src/coordinate/audit.py` diagnoses coarse task mirror
  status/owner/untracked drift and unresolved harness mutation failures.
- S4-B established versioned registry/source/override authority. S4-C established the
  v1 split-operation envelope/ledger and receipt completion remains a stronger,
  separate protocol.
- S4-C2 dogfood observed that `mark-done-preflight` reports the original authorized
  payload even after a terminal `completion.consumed` event; S4-D must report the
  authoritative terminal state rather than repeat a stale projection.
- Coordinate main has an unrelated untracked `.qoder/`; preserve it and never deploy it.

## Problem and evidence

The system now records enough evidence to diagnose projection drift, but no single
read-only report consumes it:

1. registry source metadata, normalized entries, effective resolver, and compatibility
   `agents_json` can disagree;
2. file-half envelopes and DB ledgers can be pending, orphaned, incompatible, or drifted;
3. task mirrors may lag operation record events or later legitimate lifecycle events;
4. completion receipts are event chains, but the current preflight lookup reads only
   `completion.authorized` and can display stale `authorized` after consumption; and
5. existing audit/doctor reports do not state the authority, exact evidence, or safe
   next action for these conditions.

A diagnostic that guesses canonical state or silently repairs rows would recreate the
multiple-source-of-truth problem Slice 4 is intended to remove.

## Goal

Add one deterministic, read-only projection diagnostic surface that consumes S4-B,
S4-C, task-mirror, and completion-receipt evidence; reports every supported finding
with authority and actionable evidence; and fixes receipt preflight to return its
authoritative derived state. No generic repair executor is introduced.

## Non-goals

- No schema migration or table/index change.
- No automatic registry sync, checklist write, mirror rewrite, ledger fabrication,
  receipt repair, event deletion, or direct JSON/SQLite mutation.
- No new generic `repair` command and no `--force` path.
- No redesign of existing S4-B registry sync, C1/C2 split operations, receipt
  claim/apply/consume, harness lifecycle, or reconciliation authority.
- No Phase 9 scheduler, executor pool, worktree lease, provider routing, or service API.
- No MultiNexus runtime/registry-authority behavior change; cross-repository changes are
  documentation and contract tests only.

## Invariants and authority boundaries

### Authorities

- Registry source identity/version/hash: `workspace_agent_registry_sources` plus the
  referenced readable authority file when available.
- Effective registry: normalized authoritative/legacy/override rows resolved by the
  existing resolver; `workspaces.agents_json` is compatibility projection only.
- Checklist task and split envelope: deployed canonical harness file.
- Split record state: v11 `split_operations` plus its bound event and task mirror.
- Task lifecycle ordering: SQLite `events.rowid`, not timestamp alone.
- Receipt state: event-chain order
  `completion.authorized -> claimed -> applied -> task.done + completion.consumed`.
- Repair authority remains the existing explicit command for that domain. Doctor may
  recommend it only when all required evidence is known.

### Read-only contract

- Diagnostic execution performs no `INSERT`, `UPDATE`, `DELETE`, harness mutation,
  registry sync, event append, delivery creation, or repair.
- Tests and dogfood prove DB `total_changes`, data version, task/checklist bytes, and
  registry source bytes are unchanged.
- Findings are deterministically ordered and use stable machine-readable kinds.
- Each finding contains: `finding_id`, `kind`, `severity`, `scope`, `workspace_id`,
  optional `task_id`/`operation_id`/`receipt_id`, `authority`, exact `evidence`,
  `repairable`, and `next_action`.
- `repairable=true` means an existing audited authority command can be emitted with
  complete inputs. Otherwise the report must say `repairable=false` and preserve
  evidence; it may not invent actor, source path, operation intent, fingerprints, or
  canonical state.

## Proposed changes

### 1. Shared projection diagnostic module

Add `src/coordinate/projection_doctor.py` with immutable report/finding types and a
single read-only collector, for example:

```python
diagnose_projections(conn, workspace_id, *, adapter=None, now=None) -> ProjectionReport
```

The collector must use existing DB/resolver/harness helpers and may add focused
read-only query helpers in `db.py`. It must not import CLI owners or mutation services.

### 2. Registry findings

Report at least:

- `registry_source_missing`: normalized authoritative rows exist without source metadata;
- `registry_source_unreadable`: a recorded source path is not readable on this host;
- `registry_source_identity_mismatch`: readable source id/version/hash differs from the
  recorded source metadata;
- `registry_projection_stale`: compatibility `agents_json` differs from the existing
  effective resolver after expired overrides are excluded;
- `registry_override_shadowed`: active override shadows an authoritative identity
  (auditable informational finding, not an error);
- `registry_expired_override_retained`: expired override remains retained for audit but
  is correctly excluded from effective authorization (informational unless projected).

Unreadable source is not proof of stale authorization. Severity and evidence must
distinguish “cannot verify here” from an actual mismatch.

### 3. Split-operation findings

For every v11 ledger row and every deployed checklist envelope, report at least:

- `operation_file_pending`: exact supported envelope exists with no ledger; safe next
  action is the original record half with the recorded operation/fingerprints;
- `operation_ledger_orphaned`: ledger target/envelope is missing;
- `operation_contract_unsupported`: unknown contract version or operation kind;
- `operation_envelope_drift`: source/target/operation/fingerprint/envelope shape or
  current item projection differs from the ledger;
- `operation_record_event_missing` / `operation_record_event_mismatch`: the bound event
  is absent or has wrong workspace/task/type/operation intent;
- `operation_status_invalid`: ledger status is outside the supported state machine;
- `operation_target_conflict`: multiple ledger rows bind one target or source contrary
  to the C1/C2 contract.

The doctor must reuse C1/C2 canonical fingerprint and envelope validators. It may expose
neutral read-only helpers from `split_operations.py`, but must not fork hashing formats
or call record/file mutation functions.

Supported operation/event mapping is explicit:

- `task.create` -> `plan.ready`;
- `issue.materialize` -> `issue.materialized`.

### 4. Task-mirror findings

Preserve existing audit semantics and add operation-aware checks:

- `operation_task_mirror_missing`;
- `operation_task_mirror_metadata_drift` for immutable operation metadata/payload;
- `operation_task_event_regression` when `last_event_id` is absent, points to another
  workspace/task, or precedes the operation record event by `rowid`.

A later legitimate same-task lifecycle event is not drift. In particular, a C1/C2 task
that later reached `task.done` may have `last_event_id` newer than the operation record
event and must remain clean.

The existing coarse `workspace audit` findings remain compatible. Shared comparison
logic should be reused rather than duplicated with conflicting kind names.

### 5. Completion-receipt findings and preflight correctness

Group receipt events by `receipt_id` and derive the authoritative state in rowid order.
Report at least:

- `receipt_chain_incomplete`: claimed without authorized, applied without claimed, or
  consumed without applied/task.done;
- `receipt_chain_conflict`: workspace/task/actor/fingerprint links disagree;
- `receipt_authorization_unused`: an authorized receipt remains unclaimed past expiry
  or is superseded by a later terminal receipt for the same task (warning);
- `receipt_terminal`: consumed chain is internally consistent (summary evidence, not an
  error).

Fix `assignment mark-done-preflight` so a consumed receipt returns `status=consumed`
and terminal event evidence rather than the original authorized payload. Precedence is
`consumed > applied > claimed > authorized`; unknown and inconsistent chains fail
closed. This lookup remains read-only and does not change claim/apply/consume behavior.

### 6. Doctor and audit integration

- Extend `DoctorReport` additively with `projection_report` and `projection_ok`.
- `workspace doctor <id>` reports projections by default after filesystem/harness
  checks. A projection `error` makes the CLI non-zero; warnings/info remain visible but
  do not fail unless an existing health gate already fails.
- Add `--no-projections` only as a compatibility/diagnostic escape hatch; default is the
  S4-D report. It may not be used by deployment smoke to hide errors.
- Add the new fields to the CLI fixture intentionally and provide a C2-to-D delta proof
  independent of Git topology.
- Extend `workspace audit` only where sharing avoids duplicate mirror findings; do not
  change its current refresh/no-refresh authority or silently repair.

### 7. Repair evidence

Every error/warning includes a safe next action:

- registry source mismatch -> explicit authoritative `workspace agent sync ... --replace`
  only when recorded source path/id/version/hash are complete;
- exact file-pending operation -> re-run the original record half using the recorded
  operation/source/target/fingerprints, but do not guess record-only owner/branch/actor/
  destination; if those are not recoverable, `repairable=false`;
- mirror drift -> existing `reconcile` only when deployed harness is readable and named
  as authority;
- orphan/conflicting ledger, unsupported contract, or broken receipt chain -> preserve
  evidence and escalate; no generated repair command.

The report records prior explicit repair-only evidence already present in events, but
S4-D does not add a second event vocabulary or execute repairs.

## Failure and recovery matrix

| Failure | Required diagnosis | Mutation | Retry |
|---|---|---|---|
| harness/source file unreadable | `*_unreadable`, not false mismatch | none | same report after access/deploy fix |
| exact file half only | `operation_file_pending` warning | none | record half remains idempotent authority |
| ledger exists, envelope missing | orphan/error with ledger evidence | none | deploy correct source or escalate |
| item/envelope fingerprint drift | drift/error with expected/actual hashes | none | correct canonical projection; rerun doctor |
| record event missing/wrong | error with ledger/event ids | none | preserve DB and escalate |
| later legitimate lifecycle event | clean monotonic mirror linkage | none | deterministic |
| expired/shadowed override | informational unless projected incorrectly | none | registry authority remains S4-B |
| receipt consumed | preflight/doctor report consumed | none | exact retry read is stable |
| broken receipt chain | fail-closed finding | none | preserve chain; no fabricated terminal event |
| doctor crashes midway | no partial DB/file state | none | safe retry |

## Acceptance matrix

| Case | Setup | Expected result |
|---|---|---|
| clean production-like | B2 registry + C1/C2 applied operations + later task.done | no error findings |
| file pending | exact C1/C2 envelope, no ledger | warning + recorded record-half inputs |
| orphan ledger | ledger, missing item/envelope | deterministic error, no repair |
| envelope drift | changed source/target/fingerprint/item | exact expected/actual evidence |
| record event drift | missing/wrong event | error, ledger retained |
| mirror progression | last_event newer same task | clean |
| mirror regression | missing/older/other-task event | error |
| registry projection stale | effective resolver != agents_json | error + authoritative sync action if complete |
| unreadable source | source path unavailable | unverifiable warning, not mismatch |
| override | active shadow + expired retained | info; projected expired override is error |
| receipt terminal | full consumed chain | consumed in doctor and preflight |
| receipt broken | partial/conflicting chain | error, no mutation |
| read-only proof | snapshot DB/file bytes before/after | exact unchanged state |
| compatibility | existing doctor/audit callers | additive JSON and documented exit behavior |

## Validation

- New focused `tests/test_projection_doctor.py` with registry, C1, C2, mirror, receipt,
  ordering, severity, deterministic-order, no-write, and serialization cases.
- Existing `tests/test_audit.py`, `tests/test_doctor.py`, workspace CLI and completion
  CLI suites.
- C1/C2 split-operation, registry, receipt, event presentation, daemon, policy, handoff,
  and full Coordinate suites.
- CLI contract fixture plus self-contained S4-D delta/rewind proof; do not rebaseline
  historical Python 3.12 failures.
- MultiNexus contract tests for runbook/deploy authority wording and harness
  validate/doctor.
- `ruff`, `compileall`, `git diff --check`.
- Local and deployed-server isolated fixtures proving all finding classes and no writes.
- Production read-only dogfood must diagnose the deployed B2 registry, existing C1
  ledger, zero C2 rows, terminal receipts (including the unused first S4-C2 receipt),
  and a later `task.done` without false errors. Preserve raw JSON evidence.

## Rollout and rollback

- No migration. Coordinate first, MultiNexus docs second.
- Result review and local integration precede deploy.
- Back up production DB despite the read-only design; deploy Coordinate with full venv
  installation, verify import path/version/schema/integrity, then run read-only doctor.
- Rollback is Coordinate code rollback only. No data rollback should be necessary; any
  observed DB/file mutation is a release blocker and triggers backup comparison.
- Stop on a production false positive that cannot be explained by recorded authority,
  any mutation, any generic repair execution, or any change to S4-B/C/receipt semantics.

## Worker boundaries

- Dedicated Coordinate worktree from exact start `a21d946`.
- Allowed production modules: new `projection_doctor.py`; focused additive changes in
  `doctor.py`, `audit.py`, `workspace_cli.py`, `completion_cli.py`, `db.py`, and neutral
  read-only helpers in `split_operations.py` only when necessary.
- Allowed tests: new/focused projection-doctor, doctor, audit, completion, workspace CLI,
  split-operation and CLI contract tests.
- MultiNexus changes during implementation are forbidden; Codex owns reviewed docs,
  deployment, dogfood, and lifecycle closeout.
- No schema, mutation service, registry sync, file/record operation, receipt transition,
  daemon loop, scheduler, provider, or Phase 9 change.
- Worker commits only to its branch. No push/merge/deploy/SSH/production DB/config/
  lifecycle action.
- JSONL/session path is mandatory evidence. Worker report must list exact changed paths,
  finding kinds, focused/full counts, historical failures, and commit SHA.

## Plan review record

- Review artifact: pending
  `docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan-review-round1.md`.
- Reviewer: pending non-Codex Kimi reviewer.
- Verdict: pending.
- Reviewed plan revision: pending exact SHA-256.
- Must-fix findings: pending.
- Resolution revision: pending.

Any material edit after approval resets this plan to `in_review`, invalidates approval
and worker bootstrap, and requires a new independent review.

## Bootstrap gate

After approval, generate `worker-bootstrap.md` in this package. It must cite the exact
approved plan SHA, review artifact, Coordinate start SHA, allowed paths, no-mutation/
no-repair boundary, validation matrix, and provider route. Before handoff, re-hash the
plan and refuse stale approval/bootstrap references.
