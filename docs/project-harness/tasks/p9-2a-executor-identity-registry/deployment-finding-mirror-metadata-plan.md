# P9-2A deployment finding: preserve split-operation task-mirror metadata

Date: 2026-07-13  
Status: proposed deployment must-fix addendum  
Owner: Codex operator/reviewer  
Implementation worker: ordinary `Kimi for Coding` through OMP  
Plan reviewer: GLM 5.2 first, ordinary Kimi fallback

## Trigger and evidence

P9-2A code, schema, catalog deployment, typed job, Discord sentinel delivery, and
isolated tamper probes passed. The final production command
`coordinate workspace doctor discord-nexus` nevertheless reported one error:

- kind: `operation_task_mirror_metadata_drift`;
- task: `p9-2a-executor-identity-registry`;
- operation: `62175918-ce07-4da5-8bf4-03b9784fb64e`;
- reason: `mirror_payload_has_no_split_operation_metadata`.

The durable ledger row and its original `plan.ready` event
`a73556cf-5960-4542-b1c8-73bc771ed109` contain the correct v1 operation metadata.
The later revised `plan.ready` event `3dc704af-f627-4953-a5bc-5721f67ca3cf` was
created through the compatibility `task create` path and omitted that metadata.
`create_task()` in `coordinate/onboarding.py` then replaced the complete mirror
payload, so the subsequent approval preserved an already-damaged mirror.

## Required outcome

1. A compatibility `task create` plan revision must preserve an existing task
   mirror's valid `split_operation` object byte-for-byte.
2. Caller-supplied payload must not forge or replace that reserved metadata.
3. Ordinary legacy tasks with no split operation must retain current behavior.
4. The production P9-2A mirror must be repaired from its existing immutable ledger
   and record event without rewriting the ledger or historical events.
5. Production doctor must return `projection_ok=true`, zero errors, with only the
   already-known superseded-unused receipt warnings allowed.

## Scope and boundaries

Expected Coordinate implementation files:

- `src/coordinate/onboarding.py`;
- focused tests in `tests/test_onboarding.py` and/or
  `tests/test_projection_doctor.py`;
- another existing focused test file only if needed to exercise the CLI boundary.

Expected MultiNexus artifacts:

- this addendum;
- P9-2A deployment/closeout evidence after reviewer acceptance.

Do not change:

- split-operation ledger schema or fingerprints;
- `projection_doctor` severity or detection logic;
- task-create operation envelopes;
- plan approval semantics;
- P9-2A executor/catalog/binding contracts;
- P9-2B routing, leases, health, or scheduling behavior.

Do not make the doctor ignore the drift. Do not repair production before a database
backup and an independently reviewed deterministic repair procedure exist.

## Implementation design

### A. Reserve and preserve `split_operation`

In the compatibility `create_task()` path:

1. Read the existing task mirror, if any, before building the replacement payload.
2. Decode its payload and inspect `split_operation`.
3. If existing metadata is a dictionary, carry that exact dictionary into the new
   task payload after all caller payload merging, so a plan revision cannot erase it.
4. Treat caller-provided `split_operation` as reserved:
   - if no existing operation metadata exists, reject the supplied reserved key;
   - if existing metadata exists, reject a supplied value that is not exactly equal;
   - an exactly equal retry may proceed and still uses the stored value.
5. A malformed stored `split_operation` must fail closed rather than silently copy,
   delete, or normalize it.

The implementation should use a small helper with explicit error messages rather
than introducing generic payload merge machinery.

### B. Regression coverage

Add tests proving:

1. split `task.create-files` + `task.create-record`, followed by a revised legacy
   `create_task`, preserves the exact operation metadata in the task mirror;
2. the resulting projection doctor report has no
   `operation_task_mirror_metadata_drift` finding (an expected
   `operation_plan_superseded` info is acceptable after the revision is approved);
3. a conflicting caller-supplied `split_operation` is rejected with zero mirror/event
   mutation;
4. a caller cannot create forged split metadata on an unbound legacy task;
5. a normal legacy plan revision without split metadata retains current behavior;
6. plan approve/reject continues to preserve the repaired metadata.

### C. Production repair procedure

The result reviewer will prepare and inspect a one-shot repair script. It must:

1. open the production DB under `BEGIN IMMEDIATE`;
2. identify the task and the unique `split_operations` ledger row;
3. load `record_event_id` and validate that event's `split_operation` fields exactly
   match ledger contract version, operation id/kind, and all three fingerprints;
4. require the current mirror to be missing `split_operation` (not conflicting);
5. merge only that validated object into the current mirror payload, preserving
   current phase/owner/branch/pr/last-event columns and all other payload keys;
6. append one audited `projection.repaired` event that contains ids/fingerprints but
   no plan contents or secrets;
7. commit atomically and be idempotent on exact retry;
8. print before/after payload hashes and the repair event id.

This one-shot repair is operational evidence, not a new general repair API. A future
generic doctor repair command requires its own package.

## Validation and gates

Before integration:

- focused onboarding/split-operation/projection-doctor tests;
- full Coordinate suite with the existing nine baseline-identical AST/CLI failures
  distinguished from regressions;
- `compileall` and `git diff --check`;
- Codex adversarial result review.

Before production mutation:

- reviewed commit pushed and deployed with full Coordinate reinstall;
- fresh SQLite `.backup` plus SHA-256 and restricted permissions;
- dry-run repair against a copy of the production DB;
- dry-run doctor on that copy proves the target error disappears and no new finding
  appears.

Production acceptance:

- deterministic repair succeeds once and exact retry is idempotent;
- `workspace doctor discord-nexus` reports `projection_ok=true`, `errors=0`;
- deployed/source/installed Coordinate SHA and module hashes agree;
- service and MultiNexus bridge remain active;
- P9-2A typed binding/context/delivery evidence remains unchanged;
- final closeout documents the root cause, code fix, backup, repair event, doctor
  output, and rollback path.

## Rollback

- Code rollback: redeploy the previous reviewed Coordinate SHA.
- Data rollback: restore the fresh pre-repair SQLite backup only if the atomic repair
  or post-repair doctor fails; restoring also removes events written after that backup,
  so stop services and assess intervening runtime events before restoration.
- The repair adds one payload member and one audit event; no schema rollback is
  required.
