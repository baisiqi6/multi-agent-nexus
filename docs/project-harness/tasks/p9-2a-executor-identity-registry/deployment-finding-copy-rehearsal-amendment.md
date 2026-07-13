# P9-2A production-copy rehearsal amendment: restore immutable payload phase

Date: 2026-07-13  
Status: proposed must-fix amendment; production remains untouched  
Owner: Codex operator/reviewer  
Plan reviewer: GLM 5.2 through OpenCode; Codex retains result-review authority

## Trigger and exact evidence

The reviewed repair script SHA-256
`bec25815fb60db174ad609da18ac1da895fd369ff359fdf04ca700708805eb47`
was executed against a disposable copy of the fresh production backup, never
against the production database.

Before repair, `workspace doctor discord-nexus` reported the expected error:

- kind: `operation_task_mirror_metadata_drift`;
- operation: `62175918-ce07-4da5-8bf4-03b9784fb64e`;
- reason: `mirror_payload_has_no_split_operation_metadata`.

The script restored the exact six-key `split_operation` object and its exact
retry was idempotent, but post-repair doctor still returned one error. Its
evidence changed to:

```text
record_mismatches = ["phase: mirror=None deployed='ready'"]
```

Inspection of that disposable copy established:

- immutable record event `a73556cf-5960-4542-b1c8-73bc771ed109` has payload
  `phase = "ready"`;
- the current task row column has `phase = "ready"`;
- the task payload has no `phase` key;
- current Coordinate commit `eec9b233f6c797c73aec9d535fa723e037a0af65`
  already writes payload `phase` when a compatibility plan revision carries a
  stored split operation, preventing recurrence.

Therefore the old compatibility revision erased two immutable payload members,
not only the originally visible six-key metadata. The exact-copy rehearsal gate
correctly prevented production mutation.

## Required outcome

Repair the one production task mirror from existing durable authorities so that:

1. payload `split_operation` is the exact validated six-key ledger/event object;
2. payload `phase` is the exact immutable record-event phase, independently
   corroborated by the existing task row phase column;
3. all other payload keys and every task table column remain unchanged;
4. one deterministic `projection.repaired` audit event records hashes, ids,
   fingerprints, repaired field names, and the restored phase, but no plan
   contents or secrets;
5. exact retry performs zero writes and returns the same repair event id and the
   original before-payload hash;
6. post-repair doctor reports `projection_ok=true`, zero errors, with only the two
   known `receipt_authorization_unused` warnings allowed.

## Revised validation and repair contract

The one-shot script must retain all controls in the approved base addendum and add
the following controls before any write:

1. Decode the immutable record event payload as a JSON object.
2. Continue to require its `split_operation` object to have exactly the approved
   six keys and to match the ledger exactly.
3. Require record-event `phase` to be a non-empty string.
4. Require `tasks.phase` to be the same string as record-event `phase`; a null or
   mismatch fails closed. This gives two independent durable values without
   trusting the damaged task payload.
5. Treat payload phase states explicitly:
   - missing: eligible for repair;
   - exactly equal to the validated phase: already correct;
   - null, wrong type, or different value: fail closed.
6. A repair is needed when either eligible field is missing. Merge only the
   missing validated field or fields into a copy of the current payload.
7. Update only `tasks.payload_json`; do not update `phase`, `owner`, `branch`, `pr`,
   `last_event_id`, `updated_at`, or any other column.
8. Audit payload must include `repaired_fields`, a sorted list whose only allowed
   members are `phase` and `split_operation`, plus `restored_phase`. Exact retry
   validates these values along with the existing deterministic event identity.
9. If mirror metadata is missing while the deterministic repair event already
   exists, continue to fail closed. Do not use an audit event to complete a
   partially applied repair.

The production database currently has neither repair field in its payload and has
no `projection.repaired` event for this task. The already-mutated disposable copy
is evidence only and will be discarded. Rehearsal must restart from a new copy of
the immutable backup.

## Focused regression coverage

Extend the standalone tests to prove:

1. first run restores both missing fields and preserves every other task column;
2. exact retry is zero-write and returns the original before hash;
3. preexisting exact fields with no repair event are zero-write success;
4. preexisting exact phase plus missing split metadata repairs only split metadata;
5. preexisting exact split metadata plus missing phase repairs only phase;
6. record-event phase/task-column mismatch fails before mutation;
7. payload phase null, wrong type, or conflicting value fails closed;
8. audit `repaired_fields` and `restored_phase` are exact and contain no plan data;
9. record-event extra split-operation keys and orphaned/conflicting repair events
   continue to fail closed.

## Gates and production sequence

1. GLM 5.2 independently reviews this exact amendment; all must-fix findings are
   resolved before implementation.
2. Codex updates and adversarially reviews the one-shot script and tests.
3. Full MultiNexus tests, `compileall`, and `git diff --check` pass.
4. The updated script is committed, pushed, and its SHA-256 recorded.
5. Create a new disposable copy from backup
   `/var/backups/coordinate/coord.sqlite3.p9-2a-mirror-fix.20260713T093705Z`
   (SHA-256
   `5807973f138b37c3ec7dd674d2310ccf50fa7727eaf35ca35b743f2718482580`).
6. On the fresh copy, capture pre-doctor, run the exact script once, run exact
   retry, run post-doctor, verify SQLite integrity and one audit event.
7. Codex and `codex-operator` record approval of the exact script SHA-256.
8. Only then execute once and retry against `/var/lib/coordinate/coord.sqlite3`.
9. Run production doctor, service/sentinel/catalog/binding checks, and document
   closeout and rollback evidence.

## Rollback

The base rollback remains unchanged. Production has not yet been mutated. If the
future atomic production repair or post-repair doctor fails, stop relevant writers,
assess intervening events, and restore the fresh pre-repair backup only when safe.
