# Detailed Execution Plan: Slice 4C2 Issue Materialize Operation Adoption

> This plan is an execution gate, not worker authorization. Implementation starts only
> after an independent non-Codex reviewer approves this exact revision, Coordinate
> records the approval, and Codex generates a fresh worker bootstrap.

## Package identity and reviewed baseline

- Package: `slice-4c2-issue-materialize-operation-adoption`.
- Parent: `slice-4-projection-hardening`, S4-C bound split operations.
- Required Coordinate start: `1cbb547d7966c83c198125370f46bddc2d8640c9`.
- Required MultiNexus start: `720c2641a4b6622932a479a9db112e1a2ea7366c`.
- Production baseline: Coordinate schema v11; `split_operations` exists; C1 receipt
  `c968e093-c5b0-4773-800c-0f17b1abd2dd` consumed.
- Architect/operator/result reviewer: Codex.
- Plan reviewer and coding worker must be non-Codex agents. Default provider is
  `kimi-code/kimi-for-coding-highspeed`; GLM is fallback only after a documented
  Kimi quota/auth/provider failure.

## Goal

Adopt the reviewed C1 split-operation contract for
`issue materialize-files/materialize-record` so one accepted `issue.triaged` event is
bound to one checklist task projection and one all-or-nothing record transaction.

The completed flow must prove:

1. the operator, not either half, owns one stable operation UUID;
2. the coding-host file half binds the accepted triage event as the operation source;
3. the record half refuses before the exact file envelope is deployed;
4. the record half verifies the accepted triage event, deployed plan/item/envelope and
   all supplied fingerprints before writes;
5. ledger, task mirror, `plan.ready`, `issue.materialized`, final mirror linkage and
   optional delivery intent commit or roll back together;
6. exact replay distinguishes safe already-applied state from every persisted-intent,
   event, delivery, target and source conflict; and
7. C1 `task.create`, combined legacy materialize, mark-done receipts, event rendering
   and the delivery pump remain compatible.

## Current facts and defect statement

At the reviewed start:

- `materialize_issue_files` delegates to legacy `sync_to_checklist`, has no workspace
  authority, operation id, source id or envelope, and repairs existing checklist items;
- `materialize_issue_record` can run before deploy because it reads only DB state;
- retry identity is inferred by scanning `issue.materialized` payloads for triage/task/
  plan equality rather than a ledger row and deployed fingerprint;
- task upsert, `plan.ready`, `issue.materialized` and delivery each commit separately;
- `create_delivery` / `create_delivery_for_event` have no transaction seam;
- a failure after any earlier step leaves durable partial state;
- the accepted triage step intentionally creates a DB task mirror before file
  materialization, while the checklist target is still absent. C2 must preserve that
  valid asymmetry rather than require the DB mirror to be absent.

The combined `issue materialize` command remains a legacy single-host compatibility
path. C2 hardens only the explicit host-aware files/record pair.

## Approved contract extension

### 1. Reuse one ledger and one checklist projection

Do not add a schema migration or C2-only table. Use v11 `split_operations` with:

- `contract_version=1`;
- `operation_kind=issue.materialize`;
- `workspace_id=<registered workspace>`;
- `target_kind=checklist_task`, `target_id=<resolved task id>`;
- `source_kind=issue_triaged_event`, `source_id=<accepted triage event UUID>`;
- the same input/before/after fingerprints and `record_applied` status;
- `record_event_id=<issue.materialized event id>`.

The source binding is mandatory. A different triage event may not materialize through
the same operation or silently target an already bound checklist task.

### 2. CLI contract

`issue materialize-files` adds required:

- `--workspace-id`;
- `--operation-id`;
- `--event-id` (the accepted `issue.triaged` source UUID).

It keeps required local `--workspace-path`, `--harness-root`, `--task-id`,
`--plan-doc`, and file-authored title/phase/priority intent.

`issue materialize-record` adds required:

- `--operation-id`;
- `--input-fingerprint`;
- `--before-fingerprint`;
- `--after-fingerprint`.

Its existing required `workspace_id`, `--event-id`, `--plan-doc` and optional task/
title/phase/owner/branch/actor/platform/destination remain. It has no `--priority`;
priority is derived from the deployed checklist item. Neither half generates an
operation id.

CLI JSON returns operation kind/id, contract version, source/target binding, all three
fingerprints and file timestamp or ledger/event/delivery state as appropriate. Stable
error output must preserve the C1 classifications:

- `files_not_deployed`;
- `operation_conflict`;
- `fingerprint_drift`;
- `lock_timeout`;
- `validation_error`.

### 3. Canonical input and item fingerprints

Extend the shared canonical input builder rather than fork a second format. For C2 the
compact key-sorted UTF-8 JSON contains exactly:

```json
{
  "contract_version": 1,
  "operation_kind": "issue.materialize",
  "workspace_id": "discord-nexus",
  "target": {"kind": "checklist_task", "id": "task-id"},
  "source": {"kind": "issue_triaged_event", "id": "triage-event-uuid"},
  "plan_doc": "docs/project-harness/tasks/.../plan.md",
  "plan_sha256": "full-lowercase-sha256",
  "title": "resolved title",
  "phase": "ready",
  "priority": "p1"
}
```

The path is workspace-relative and POSIX. Host-absolute paths, issue title/body/repo
metadata, delivery destination, owner, branch, actor and timestamps are not file-proven
input. The full plan bytes are hashed. Reuse the C1 full item projection and exclusion
set unchanged.

The shared module may introduce neutral internal builders/helpers, but public C1
wrappers and their exact hashes/tests must remain stable.

### 4. File-half rules

Use the existing C1 checklist lock and atomic write implementation. The C2 file half:

1. validates canonical UUID/SHA/path/source fields;
2. requires the target checklist item to be absent unless the exact same C2 operation
   envelope is already present;
3. builds the deterministic item in memory with C2 source binding;
4. writes one same-directory temp file, flushes/fsyncs, preserves mode and replaces
   once under the per-checklist exclusive lock;
5. returns exact retry without timestamp or byte rewrite; and
6. rejects an unbound task, a C1 envelope, another C2 operation, source change or item
   drift as conflict.

The file host cannot prove that the source event is accepted in the server DB. It proves
only the caller-supplied source UUID binding. The record half is the authority that
loads and validates the actual `issue.triaged` event.

### 5. Record preflight

Before any DB write, the record half must:

1. load the registered workspace and accepted `issue.triaged` row;
2. require same workspace, `decision=accept`, and resolve the same task id as the
   deployed envelope target;
3. require the triage accept task mirror to exist, but not treat its pre-materialize
   payload as already-applied materialization;
4. load the deployed checklist item and require the exact C2 envelope shape, operation,
   source and target;
5. resolve deployed plan bytes read-only and recompute input/before/after fingerprints;
6. derive title/phase/priority from the item and reject record CLI disagreement;
7. reject another ledger for the same checklist target or same triage source; and
8. classify no envelope as `files_not_deployed`, changed operation/source/target as
   `operation_conflict`, and plan/item/hash drift as `fingerprint_drift`.

All checks happen before the savepoint.

## One record transaction

After preflight, use one savepoint/transaction for exactly:

1. insert the neutral split-operation ledger row;
2. upsert the accepted task mirror to the materialized projection with untrusted GitHub
   traceability and operation metadata;
3. append operation-bound `plan.ready`;
4. append operation-bound `issue.materialized`, whose payload binds the plan-ready id,
   triage/spotted ids, task/plan and operation metadata;
5. update the final task mirror with `last_event_id=<issue.materialized id>`;
6. link ledger `record_event_id` to `issue.materialized`; and
7. if effective platform/destination exists, create the rendered delivery intent for
   `issue.materialized` inside the same transaction.

Add `commit: bool = True` seams to the minimum existing delivery helpers required for
this path. Preserve defaults for every existing caller. Do not inline a second delivery
renderer or bypass policy.

If `plan.ready`, `issue.materialized` or delivery returns an existing idempotency key
while no exact ledger exists, fail closed and roll back; do not repair partial state.
Delivery absence is valid only when no effective platform/destination is configured or
the renderer explicitly reports unsupported.

## Exact replay and evolving delivery status

An exact ledger retry performs no writes and returns the persisted result only after
verifying:

- exact ledger operation/source/target/fingerprints/status/event link;
- exact deployed envelope and current item projection;
- triage event still accepted with the same resolved task/source metadata;
- exact task mirror columns, final `last_event_id`, immutable payload and operation
  metadata;
- exact `plan.ready` and `issue.materialized` immutable row metadata, idempotency keys
  and payloads; and
- delivery immutable intent: event id, platform, destination, message key and rendered
  payload.

Delivery operational fields (`status`, `attempt_count`, `platform_message_id`,
`last_error`, `updated_at`) may legitimately advance after commit and are not reset or
treated as drift. An exact retry after delivery becomes `sent` must succeed and report
the current delivery row. A changed platform/destination or missing promised delivery
is conflict. A retry may not create a delivery that was absent from the original record
intent merely because new CLI delivery arguments appear later.

## Compatibility and failure matrix

| Failure point | Checklist | Ledger/task/events/delivery | Safe retry |
|---|---|---|---|
| file validation/lock/temp/fsync | unchanged | unchanged | same operation |
| after replace, before output | exact C2 envelope | unchanged | files idempotent |
| record before deploy | source envelope only | unchanged | deploy, then record |
| triage/source/plan/item drift | unchanged | unchanged | correct intent/drift |
| after any injected DB step | exact envelope | all new effects rolled back | same record call |
| pre-existing bound event/delivery key without ledger | exact envelope | pre-existing row retained; no repair | resolve conflict |
| DB commit before output | exact envelope | full record_applied transaction | record idempotent |
| delivery progresses pending -> sent | exact envelope | immutable intent same | record idempotent; preserve sent |
| later deployed/source drift | changed | ledger retained | conflict; S4-D reports |

The legacy combined `issue materialize` behavior and its tests remain unchanged. C2
does not retrofit historical materializations or fabricate ledger rows.

## Allowed paths

Coordinate production:

- `src/coordinate/split_operations.py` for neutral extension/C2 wrappers;
- `src/coordinate/issues.py` for C2 adoption and exact materialize replay;
- `src/coordinate/issue_cli.py` for approved CLI fields;
- `src/coordinate/db.py` and `src/coordinate/policy.py` only for focused transaction
  seams with unchanged defaults;
- minimal result dataclass/import changes required by those paths.

Coordinate tests:

- focused C2 split-operation/issue tests;
- delivery transaction and immutable-intent tests;
- CLI/issue boundary and CLI fixture/rewind tests;
- existing C1, combined materialize, handoff, policy, completion and full suites.

MultiNexus:

- this task package, Slice 4 overview, progress, dogfood feedback and runbook examples;
- normal generated checklist/current artifacts.

No schema migration, issue scan/triage redesign, renderer redesign, delivery pump lease,
S4-D doctor/repair, Phase 9 isolation or mark-done change is allowed.

## Tests and acceptance

1. shared contract tests lock unchanged C1 hashes and new C2 source-bound canonical
   hashes/envelope fixtures;
2. C2 file tests cover happy path, cross-second exact retry, unbound/C1/other-source
   conflicts, current-item drift, atomic failure and lock behavior through the shared
   implementation;
3. record preflight tests cover missing deploy, wrong workspace/type/decision/source/
   target/operation, every fingerprint, plan bytes, title/phase and missing triage task;
4. failure injection after ledger, task, plan-ready, materialized, final mirror,
   ledger-link and delivery leaves no new partial effect and preserves the original
   accepted task mirror;
5. exact retry tests cover changed owner/branch/actor/platform/destination, triage
   payload drift, missing/wrong events, mirror linkage, ledger drift and pre-existing
   idempotency collisions;
6. delivery tests prove no-delivery intent, optional delivery in the same transaction,
   pending -> sent replay without reset, immutable delivery drift conflict and missing
   promised delivery conflict;
7. two different accepted issues materialize independently; same source or target with
   another operation fails closed;
8. CLI help/JSON/exit codes expose the new fields; a C2-only fixture rewind restores the
   exact post-C1 fixture bytes without changing any P9/S4-B/C1 historical SHA;
9. C1 focused tests, combined materialize tests, mark-done receipts, event presentation,
   policy/delivery, handoff and full Coordinate tests pass apart from explicitly
   documented pre-existing Python-version baselines;
10. Codex result review accepts the worker commits before integration/deploy;
11. predeploy backup, runtime package import/schema verification and server smoke pass;
12. isolated local/server interruption dogfood proves files-only, before-deploy refusal,
   transactional record, exact retry after delivery progression, injected rollback,
   source/target drift refusal and cleanup without a real production issue/task.

## Execution order and gates

1. Commit this detailed plan and compute its exact SHA-256.
2. Create the C2 task through the deployed C1 `task create-files/create-record` flow;
   commit/deploy between halves and retain operation/fingerprint evidence.
3. Request independent Kimi plan review. Every P0/P1 must be resolved in the plan and
   the revised SHA reviewed again.
4. Record Coordinate plan approval only for the exact approved SHA.
5. Generate and commit a fresh Kimi worker bootstrap from the approved plan.
6. Worker implements in a dedicated Coordinate worktree from the required start and
   commits without deploy or lifecycle closeout.
7. Codex performs adversarial result review and requests corrections until no P0/P1
   remains.
8. Fast-forward/push Coordinate only after result approval.
9. Back up production DB, deploy runtime package, verify import path/schema/integrity,
   run local/server isolated dogfood and stable-window smoke.
10. Complete normal closeout/review/receipt lifecycle and durable docs.

## Review stop conditions

The independent reviewer must request changes if C2 can record before deploy, trusts
file-host acceptance claims instead of the DB triage row, forks the C1 fingerprint or
ledger format, allows one source/target to bind multiple operations, commits delivery
outside the record transaction, treats a pre-existing event/delivery as repairable,
resets a progressed delivery on retry, fails to preserve the accepted task mirror on
rollback, weakens combined materialize/mark-done/C1 behavior, or makes S4-D infer
canonical state instead of diagnosing recorded evidence.

