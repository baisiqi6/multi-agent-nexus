# P9-2A production-copy rehearsal result review

Date: 2026-07-13  
Implementation commit: `aaed0de5e5f5b03458ad004f80a9fc22c342de1d`  
Reviewed script SHA-256: `75423566ddb612bef91a355d8e5b7233ae1d99b61d856441b9798ff6eaa307e1`  
Codex reviewer verdict: **APPROVE FOR PRODUCTION EXECUTION**  
`codex-operator` verdict: **AUTHORIZED FOR ONE PRODUCTION RUN AND EXACT RETRY**

## Static and test evidence

- focused standalone tests: 11 passed;
- full MultiNexus pytest: 503 passed, 2 skipped, 36 subtests passed;
- `compileall`: passed;
- `git diff --check`: passed;
- source commit pushed with `HEAD == origin/main`.

Reviewer verified that the script:

- starts `BEGIN IMMEDIATE` and rolls back all exceptions;
- validates the unique ledger row and exact six-key immutable record metadata;
- requires immutable record-event phase to be a non-empty string and exactly equal
  to `tasks.phase` before any write;
- fails closed on null, malformed, or conflicting payload phase/metadata;
- merges only missing validated fields;
- updates only `tasks.payload_json`;
- inserts the deterministic `projection.repaired` event and mirror update in one
  transaction;
- validates exact retry identity, fingerprints, hashes, phase, and allowed sorted
  repaired fields, then performs zero writes;
- emits no plan contents or secrets in the audit payload.

## Fresh production-copy rehearsal

Source backup:
`/var/backups/coordinate/coord.sqlite3.p9-2a-mirror-fix.20260713T093705Z`

Backup SHA-256:
`5807973f138b37c3ec7dd674d2310ccf50fa7727eaf35ca35b743f2718482580`

The earlier mutated disposable copy was discarded. A new copy was created from the
verified backup and exercised with the exact reviewed script:

- pre-doctor: `projection_ok=false`, errors 1,
  `operation_task_mirror_metadata_drift`;
- first run: `status=repaired`, repair event
  `594892d1-1783-546d-b842-652990545826`;
- before payload SHA-256:
  `ff1858641fff5e19026a501adaae901187bfa3e12fd2fcf73d9d6f55e9ab661e`;
- after payload SHA-256:
  `1827e922f4cc7ebed52618b5eb7e542ce82e27ae4f88f9d8b5532d331890ec0e`;
- exact retry: `status=already_repaired`, same event id and original before hash;
- post-doctor: `projection_ok=true`, errors 0, warnings 2, both
  `receipt_authorization_unused`;
- SQLite integrity: `ok`;
- matching repair-event count: 1;
- audit repaired fields: `["phase", "split_operation"]`;
- task columns `phase`, `owner`, `branch`, `pr`, `last_event_id`, and `updated_at`
  were identical before and after.

## Authorized production command boundary

Only `codex-operator` may execute script SHA-256 `75423566...07e1` against
`/var/lib/coordinate/coord.sqlite3`, once followed by one exact retry. Any hash
mismatch, validation error, different repair event id/hash, doctor error, integrity
failure, or unexpected warning aborts closeout and triggers rollback assessment.
