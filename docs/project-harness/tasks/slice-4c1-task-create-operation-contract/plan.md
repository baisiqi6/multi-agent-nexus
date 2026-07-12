# Slice 4C1 Task-Create Split Operation Contract

> Detailed implementation plan. Implementation remains unauthorized until an
> independent non-Codex reviewer approves this exact revision, Coordinate records the
> approval, and a fresh worker bootstrap binds the approved SHA.

## Identity

- Package: `slice-4c1-task-create-operation-contract`.
- Stage: Slice 4C, first of two packages.
- Required Coordinate start:
  `ff6b8bf585e4d1e71827e2150ef33c05a82cac1f`.
- Required MultiNexus start:
  `8c914c7e2deadf331d442ddb999aaaf136003c97`.
- Plan reviewer and coding worker: Kimi Code Highspeed through Oh-My-Pi; GLM is fallback
  only after documented Kimi quota/auth/provider failure.
- Operator and result reviewer: Codex.

## Goal

Turn `task create-files` plus `task create-record` from two merely retryable commands
into one diagnosable cross-host operation:

1. one operator-supplied stable operation UUID binds both halves;
2. canonical input, before-item and after-item SHA-256 fingerprints bind intent and
   exact file projection;
3. the file half writes one self-describing operation envelope atomically into the
   canonical checklist item;
4. the record half refuses to run until the deployed item proves the exact file half;
5. all record-side task/event/ledger writes commit or roll back together; and
6. retries distinguish not applied, files applied only, record applied, and conflicting
   drift without inventing repair state.

C1 establishes the shared contract and applies it only to task creation. C2 must reuse
the same contract for issue materialization; C1 must not special-case the schema so
that C2 needs a second ledger or fingerprint format.

## Reviewed current state

At Coordinate `ff6b8bf`:

- `task create-files` accepts only paths/task/plan/title/phase/priority, mutates
  `mvp-checklist.json`, returns `workspace_id=local`, and records no operation identity
  or fingerprints;
- `task create-record` can run before the coding-host change is committed/deployed and
  cannot prove which file half it corresponds to;
- a retry after a file-side crash is indistinguishable from a new request;
- `create_plan_task_record` calls task upsert, `plan.ready`, and final mirror upsert with
  independent commits even though `upsert_task_mirror` and `append_event` already expose
  `commit=False` seams;
- `sync_to_checklist` writes directly to the target path and has no operation envelope;
- the CLI fixture SHA-256 is
  `0c54732cfd0d7c013ebd0bd9b235d002159e1eac45dd7d6d13f81344ec105d18`;
- Coordinate has the unrelated untracked `.qoder/`, which must never be touched.

`assignment mark-done-files/record` is already protected by one-time receipts,
server-side preflight/claim/apply, lifecycle fingerprints and atomic consume. It is not
an unbound S4-C target.

## Canonical contract

### 1. Operation identity and CLI

`task create-files` adds required:

- `--workspace-id` — the real control-plane workspace, never the literal `local`;
- `--operation-id` — canonical lowercase RFC 4122 UUID text.

`task create-record` adds required:

- `--operation-id`;
- `--input-fingerprint`;
- `--before-fingerprint`;
- `--after-fingerprint`;
- `--priority`, default `p1`, so both halves hash the same common request.

Both commands validate UUID and lowercase 64-character SHA-256 values before mutation.
The files result returns operation id/kind/contract version and all three fingerprints;
the operator passes those exact values to record after commit/push/deploy. Neither half
silently generates an operation id: an implicit new UUID makes a retry unsafe.

Legacy combined `task create` is unchanged. Existing split invocations without the new
required arguments fail at argparse before mutation with migration guidance.

### 2. Canonical input fingerprint

Create one pure helper module `split_operations.py`. Contract version 1 input is exactly
the UTF-8 SHA-256 of compact, key-sorted, `ensure_ascii=False` JSON:

```json
{
  "contract_version": 1,
  "operation_kind": "task.create",
  "workspace_id": "...",
  "task_id": "...",
  "plan_doc": "workspace/relative/normalized/path",
  "plan_sha256": "full lowercase file SHA-256",
  "title": "resolved title",
  "phase": "ready",
  "priority": "p1"
}
```

Resolve title exactly as the files half does (`title or task_id`). Require `plan_doc` to
be workspace-relative, normalized POSIX text with no `..`, no empty segment and no
absolute path; both halves hash the deployed/source-controlled plan bytes independently.
This deliberately removes host-specific absolute paths from identity.

Record-only fields (`owner`, `branch`, `actor`, `target`, extra payload) remain normal DB
intent and are stored in the task/event payload, but are not falsely claimed to have
been proven by the file half. Exact-operation replay still compares their persisted DB
projection and rejects a conflicting retry.

### 3. Before/after checklist fingerprints

Define a separate task-item projection, not the coarse completion lifecycle fingerprint.

- before absent: canonical object
  `{"state":"absent","task_id":"..."}`;
- present item: recursively canonicalize the full task item while excluding only
  `updated_at`, `workflow.updated_at`, `split_operation`, `completion_receipt`, and
  descriptive `verification`;
- after: the same projection after applying the deterministic checklist defaults.

Hash compact key-sorted UTF-8 JSON. Do not reuse `compute_item_fingerprint`, whose
status/workflow-only projection is intentionally correct for completion receipts but too
weak for task creation.

For C1 `task.create`, the target task must be absent unless the exact same operation
envelope is already present. A pre-existing unbound task or a different operation id is
a conflict, not an update/repair. Legacy repair behavior remains available through the
combined command or an explicitly reviewed future repair path.

### 4. File-half envelope and atomic write

The created checklist item carries:

```json
"split_operation": {
  "contract_version": 1,
  "operation_id": "uuid",
  "operation_kind": "task.create",
  "workspace_id": "discord-nexus",
  "task_id": "...",
  "input_fingerprint": "...",
  "before_fingerprint": "...",
  "after_fingerprint": "...",
  "files_applied_at": "UTC whole-second Z"
}
```

The envelope is excluded from the item fingerprint to avoid self-reference. The file
half must construct the final item and envelope in memory, write a same-directory temp
file, flush + `fsync`, preserve the target mode, and `os.replace` it once. On failure
before replace, canonical bytes remain unchanged and the temp file is cleaned.

Retry rules under a per-checklist process lock:

- absent item: apply once;
- exact envelope + recomputed after fingerprint: idempotent success, no timestamp/file
  rewrite, returning the original fingerprints;
- exact operation id but different envelope/current projection: conflict;
- existing item without this operation or with another operation: conflict.

Use a cross-platform lock implementation already supported by the project runtime, or a
small lock-file protocol with exclusive creation, bounded timeout and explicit stale
owner evidence. Never delete an unexpired lock owned by another live process. Tests use
injected time/PID probes; no sleeps. If a safe cross-platform lock cannot be achieved in
scope, the worker must stop for plan revision rather than ship an unlocked read/replace.

### 5. Versioned operation ledger

Advance Coordinate schema to v11 with table `split_operations`:

- `operation_id` primary key;
- `contract_version` integer, initially 1;
- `operation_kind` (`task.create` now; schema permits reviewed `issue.materialize` for
  C2 without a migration);
- `workspace_id`, `task_id` and optional `source_event_id`;
- input/before/after fingerprints;
- `status`, currently only `record_applied`;
- `record_event_id` and timestamps.

Add workspace/task/status indexes and foreign keys where existing deletion semantics are
clear. Migration is additive and does not fabricate rows for legacy split operations.
S4-D must later ignore pre-v11 history rather than diagnose every legacy task as orphaned.

The table is the record-side ledger; files-only partial state remains visible through the
deployed checklist envelope with no matching row. That asymmetry is intentional and is
the input to S4-D.

### 6. Record-half verification and transaction

Before any DB write, `create-record`:

1. validates the supplied contract fields;
2. resolves the registered deployed workspace/harness root read-only;
3. loads the deployed checklist item and requires the exact operation envelope;
4. recomputes deployed plan/input/after fingerprints and matches all supplied/envelope
   values;
5. classifies missing item/envelope as `files_not_deployed`, different operation as
   `operation_conflict`, and projection/hash mismatch as `fingerprint_drift`.

Then use one savepoint/transaction for:

- inserting the split-operation ledger row;
- initial task mirror upsert;
- `plan.ready` append with operation metadata;
- final task mirror update with `last_event_id`;
- ledger status/event linkage.

Pass `commit=False` to existing DB helpers; commit once after release. Any injected
failure rolls back all five effects. Do not weaken helper defaults for other callers.

Retry classification:

- no file envelope: not started/not deployed, no DB mutation;
- exact file envelope and no ledger: files applied only; apply record transaction;
- exact ledger plus exact deployed envelope and exact persisted task/event intent:
  idempotent already-applied result, no new event/revision/timestamp;
- same operation id with any changed field, missing promised DB artifact or deployed
  drift: conflict, no repair;
- different operation for the same C1 task: conflict.

The `plan.ready` idempotency key is operation-bound. Its payload and task mirror include
contract version, operation id/kind and all fingerprints so audit does not depend only
on the ledger table.

## Compatibility and failure matrix

| Failure point | Canonical file | DB ledger/task/event | Safe retry |
|---|---|---|---|
| validation/lock before temp write | unchanged | none | same operation |
| temp write/fsync failure | unchanged | none | same operation |
| after atomic replace, before CLI output | exact envelope | none | files returns idempotent |
| before deploy | source has envelope; deployed lacks it | none | deploy, then record |
| record verification failure | deployed unchanged | none | correct drift/input |
| injected DB step failure | deployed exact envelope | fully rolled back | same record call |
| DB commit, before CLI output | deployed exact envelope | record_applied | record returns idempotent |
| later deployed/source drift | changed | existing ledger retained | conflict; S4-D reports |

Different workspace/task operations use independent IDs and task-scoped fingerprints;
unrelated checklist-item changes do not cause false conflict. Concurrent operations on
the same checklist serialize at the file lock and same-task conflicts fail closed.

## Allowed paths

Coordinate production:

- `src/coordinate/schema.py`;
- new `src/coordinate/split_operations.py`;
- `src/coordinate/db.py` only for focused ledger helpers/transaction seams;
- `src/coordinate/onboarding.py`;
- `src/coordinate/planning_cli.py`;
- minimal compatibility exports/import registration if required.

Coordinate tests:

- new focused split-operation tests;
- planning/onboarding, DB/schema, CLI and CLI-contract tests/fixture;
- failure-injection and cross-platform lock tests.

MultiNexus:

- this package's review/result/closeout artifacts;
- Slice 4 overview, progress, dogfood feedback and runbook examples;
- normal generated checklist/current artifacts.

No issue-materialize production changes are allowed in C1. C2 may add a failing
contract fixture proving the shared module is reusable, but must not implement the
second consumer before its own plan approval.

## Tests and acceptance

1. pure contract tests lock canonical input/absent/present/after hashes, excluded fields,
   UUID/SHA/path validation and Coordinate-v11 portable fixtures;
2. file-half tests cover happy path, exact retry with byte-identical file, pre-existing
   task conflict, same-id drift, different-id conflict, temp/fsync/replace failures,
   lock contention/stale rules, mode preservation and no temp leak;
3. record-half tests cover not-deployed, exact apply, already-applied retry, wrong
   operation, every fingerprint drift, plan-byte drift and missing promised DB artifact;
4. injected failure after every DB step leaves no ledger, new event or partial task
   projection; success creates all effects in one commit;
5. two different tasks can complete independently; same-task concurrent operations
   cannot overwrite each other;
6. CLI help/JSON/exit codes expose required fields, and a fixture delta/rewind proof
   shows that removing only approved C1 arguments restores CLI fixture SHA
   `0c54732c...105d18`;
7. legacy combined `task create`, issue commands and mark-done receipt suites remain
   unchanged and passing;
8. full Coordinate tests, focused MultiNexus harness validation, `git diff --check`,
   schema reopen/idempotency and v10-to-v11 migration pass;
9. Codex result review accepts the worker commit before integration/deploy;
10. isolated local and server-side dogfood proves files-only detection, deploy then
    record, record retry, conflict drift and complete cleanup without creating a real
    production task. Real production schema deployment includes a predeploy backup and
    service smoke.

## Explicit non-goals

- No `issue materialize-*` implementation; that is C2.
- No rewrite or weakening of completion receipts/mark-done.
- No S4-D doctor/repair command or automatic partial-operation recovery.
- No generic distributed transaction, queue, scheduler, worktree lease or Phase 9
  execution-isolation work.
- No Git transport/deploy orchestration inside Coordinate.
- No direct editing of private config, tokens, production checklist or unrelated
  `.qoder/`.

## Review stop conditions

The independent reviewer must request changes if C1 allows record-before-deploy,
generates a fresh operation id on retry, fingerprints host-absolute paths, reuses the
coarse completion fingerprint, writes file and envelope separately, ships without a
safe file lock, commits any record-side effect independently, treats conflict as
idempotency, fabricates legacy ledger rows, weakens mark-done receipts, or makes C2 need
a competing operation schema/format.
