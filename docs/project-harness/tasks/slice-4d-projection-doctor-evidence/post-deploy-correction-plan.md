# Slice 4D Post-Deploy Correction Plan

## Status and trigger

- Parent package: `slice-4d-projection-doctor-evidence`.
- Approved/deployed Coordinate commit: `0563cc01f9b12d5c196f59aaece8d81d1d5e5bc5`.
- Production dogfood command: `coordinate workspace doctor discord-nexus` without
  `--no-projections`.
- Production result: exit 1 with two `operation_envelope_drift` errors.
- This is a post-deploy correctness correction. It does not reopen the already closed
  receipt, immutability, or AST-rewind findings.
- Coordinate worker start commit is exactly
  `0563cc01f9b12d5c196f59aaece8d81d1d5e5bc5`. Round 5 is evidence for the
  already-integrated S4-D baseline only; it is not approval of this post-deploy fix.

## Exact production evidence

### Normal lifecycle evolution is misclassified

Task `slice-4c2-issue-materialize-operation-adoption`, operation
`66616b54-2502-4981-922f-8d18e86e70c5`, reports:

```text
deployed after fingerprint does not match recomputed after fingerprint
```

The task was legitimately accepted, reviewed, completed, and closed after its
`task.create` operation. Those harness mutations changed current checklist fields such
as `status`, `owner`, `workflow`, `review`, `lease`, `verification`, artifacts, and
completion receipt. The operation's `after_fingerprint` describes the creation-time
projection; it is not a fingerprint of all future lifecycle state.

### Reviewed plan revision is misclassified

Task `slice-4d-projection-doctor-evidence`, operation
`7b393f8a-7d27-4a4e-8a68-44cd5a8923fd`, reports:

```text
deployed input fingerprint does not match recomputed input fingerprint
```

The create operation recorded initial `plan.ready`
`5849b456-4211-434e-97bc-044623bbef0a` at SHA
`dbe4d029b5bb0272a0002a494fb24b9bb8dcf7e31247841c7059bfb9087f8a1a`.
Plan review rejected that revision, then `plan.ready`
`ef80e0a4-63c5-46c1-b3d4-393949a4048f` explicitly superseded it at SHA
`4a16f55005567a6640b98130ec9cf83391224b8e5f25622bf17cac0b0c6d4c64`.
`plan.approved` `b5176124-d930-4617-bb74-6e784006ec52` explicitly references the
new ready event. The deployed plan bytes still equal that approved SHA.

## Required semantics

### 1. Creation-time operation proof

For a `task.create` split operation, the doctor must use the ledger row's
`record_event_id` and its immutable `plan.ready` payload as the creation-time
authority. It must validate:

- record event exists and is the expected event type/workspace/task;
- payload operation metadata exactly matches ledger/envelope identity and three stored
  fingerprints;
- payload carries canonical `plan_doc`, `plan_sha256`, title, phase, and priority;
- recomputing the create input fingerprint from that historical payload equals the
  stored input fingerprint;
- reconstructing the creation-time checklist projection from historical payload,
  envelope, and `files_applied_at` equals the stored after fingerprint;
- the before fingerprint remains the absent-task projection.

Do not validate the historical after fingerprint by hashing the current lifecycle
item. Reuse or expose neutral pure helpers from `split_operations.py`; do not duplicate
private contract logic in the doctor.

The reconstruction helper belongs in `split_operations.py`. It must reuse the same
canonical input builder and checklist-item constructor/projection used by the write
path. It returns a typed/read-only verification result; it does not write or repair.

### 2. Current immutable task projection

Compare current checklist state to the creation record only for immutable creation
identity:

- task id;
- title;
- phase;
- priority;
- canonical plan document path in the item/artifacts;
- split-operation envelope identity.

Lifecycle-owned fields may evolve without invalidating the historical operation:
`status`, `owner`, `workflow`, `review`, `lease`, `handoff`, `selected_in_session`,
`updated_at`, `verification`, branch/closeout artifacts, `completion_receipt`, and other
fields demonstrably written by supported lifecycle transitions. The implementation
must not silently ignore unknown top-level fields: use an explicit allowlist or a
creation-projection helper and add a failure test for immutable-field tampering.

### 3. Approved plan supersession

If current plan bytes differ from the create operation's historical plan SHA, accept
the revision only when the event chain proves all of the following:

1. a later `plan.ready` exists for the same workspace/task and same canonical
   `plan_doc`;
2. its `plan_sha256` exactly equals the current file SHA;
3. it explicitly supersedes the earlier ready event, directly or through a valid
   acyclic supersession chain;
4. a later `plan.approved` for the same task explicitly references that exact ready
   event through `plan_ready_event_id`;
5. no later `plan.rejected` invalidates that same ready revision.

When all conditions hold, emit a deterministic non-error finding such as
`operation_plan_superseded` with old/new SHA and ready/approval event ids. If any
condition is absent, malformed, cross-task, cyclic, rejected, or SHA-mismatched, retain
an error finding. Do not mutate the old envelope, ledger, events, checklist, or plan.

### 3A. Standard plan-ready provenance contract

Current production proves that callers can already attach `plan_sha256` and
`supersedes_plan_ready_event_id`, but the default Coordinate paths do not guarantee
them. This correction must standardize the event vocabulary without a schema change:

- every newly emitted `plan.ready` payload includes canonical full `plan_sha256`;
- a later revision includes `supersedes_plan_ready_event_id` pointing to the latest
  prior same-workspace/same-task `plan.ready` event;
- an initial ready event omits or nulls the supersedes field;
- event idempotency remains content-derived and exact retry remains idempotent;
- cross-task/workspace supersedes targets are rejected;
- the write path never rewrites historical events.

Apply this to both split `task.create` record events and the non-split
`create_plan_task_record`/task-create compatibility path. Keep `plan_content_hash` for
backward-compatible presentation/idempotency, but full SHA is the verification
authority.

Legacy rule: a ready event missing full `plan_sha256`, or a later ready event missing
an explicit supersedes link, is insufficient for exact supersession proof and remains
an error. Do not accept a 16-character prefix as exact evidence. Existing production
S4-C2 and S4-D operation record events include full SHA, and the reviewed S4-D revision
includes both full SHA and explicit supersedes link; acceptance must verify those facts
from live data, not hard-code them. Other legacy tasks may remain explicitly
unverifiable until a separately reviewed repair/migration exists.

`plan.rejected` currently has no `plan_ready_event_id`. Therefore the fail-closed rule
is rowid-based: any rejection after a candidate ready event invalidates it unless a
strictly later ready revision is itself exactly approved. This is intentional.

### 4. Read-only and deterministic boundary

- No DB writes, file writes, subprocess, shell-out, network, repair execution, or
  lifecycle mutation from the doctor.
- Preserve deterministic finding ids/order and immutable report structures.
- Production and acceptance commands must not use `--no-projections`.
- Do not whitelist task ids, operation ids, event ids, plan paths, or current SHAs.

## Allowed Coordinate paths

- `src/coordinate/projection_doctor.py`.
- `src/coordinate/split_operations.py` for neutral pure reconstruction/verification
  helpers and for adding full plan SHA/supersedes metadata to split record events.
- `src/coordinate/onboarding.py` for the same metadata on the non-split compatibility
  plan-ready path.
- `src/coordinate/planning_cli.py` only if argument/payload plumbing is required; do
  not add a new command.
- `src/coordinate/plan_gate.py` only for a neutral read helper if exact approval
  linkage cannot be implemented in `projection_doctor.py` without duplication.
- `tests/test_projection_doctor.py`.
- focused split-operation/onboarding/plan-gate tests required by the provenance
  payload extension.

Do not change CLI routing, receipt code, DB schema/migrations, lifecycle mutation
semantics, `src/coordinate/cli.py`, or MultiNexus runtime code. The only authorized
event-write-path change is adding the two provenance fields to future `plan.ready`
payloads; no existing event, ledger row, checklist item, or plan may be rewritten.

## Required tests

1. A real checklist item is created, then mutated through representative supported
   lifecycle shapes to accepted/reviewed/closed/completed; no operation drift error.
2. Title, phase, priority, plan path, or split-operation identity tampering remains an
   error.
3. Historical creation record/envelope/ledger fingerprint tampering remains an error.
4. Plan bytes changed with a valid later ready + exact approval reference produces
   `operation_plan_superseded` info and no error.
5. Changed plan with no approval remains an error.
6. Rejected latest revision remains an error.
7. Approval referencing a missing, cross-task, wrong-SHA, or older ready event remains
   an error.
8. Supersession cycles remain an error.
9. S4-C2 and S4-D production-shape fixtures reproduce the observed cases without
   hard-coded identities.
10. No-write tests cover SQLite `total_changes`, plan/checklist bytes, and no subprocess.
11. Existing receipt, registry, mirror, C1/C2, immutable-report, and AST-delta tests
    remain green.
12. Both split and non-split future `plan.ready` paths store full `plan_sha256`; a
    revision links the exact prior ready event; retries do not create duplicates.
13. Legacy missing-full-SHA or missing-supersedes events do not receive false approval.

The existing `test_production_like_c1_and_later_task_done_is_clean` must be replaced or
augmented so it actually mutates checklist lifecycle-owned fields. The existing
`test_deployed_s4d_task_with_plan_bytes_changed_after_record_reports_drift` must be
split into approved-supersession info and unapproved/rejected error cases.

## Acceptance and deployment gates

- Focused tests pass.
- Full suite introduces no failure beyond the same historical nine hash failures.
- `ruff check`, `compileall`, and `git diff --check` pass for changed paths.
- `src/coordinate/cli.py` remains byte-identical to worker start `0563cc0` (which is
  already byte-identical to `a21d946`).
- Independent Codex result review approves the exact worker commit.
- Coordinate main fast-forwards, pushes, backs up the production DB, deploys, restarts,
  and passes server smoke.
- Isolated server fixtures pass.
- Production `workspace doctor discord-nexus` without `--no-projections` returns exit 0,
  zero error findings, explicit plan-supersession info for the reviewed S4-D revision,
  and only legitimate warning/info findings.
- Only after those gates may S4-D mark-done/closeout proceed.

## Provider and role policy

- Codex: architect/operator/result reviewer.
- Plan reviewer and coding worker: `kimi-for-coding-highspeed` through OMP.
- GLM may replace Kimi only after an explicit Kimi quota/auth/provider failure is
  captured. Ordinary plan/code/test failures do not trigger a provider switch.
- Provider-native JSONL remains the primary live-activity evidence.
