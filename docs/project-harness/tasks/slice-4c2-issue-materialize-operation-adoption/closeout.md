# Slice 4C2 Durable Closeout

Slice 4C2 is implemented, adversarially reviewed, integrated, deployed, dogfooded,
and closed through a consumed completion receipt. The host-aware
`issue materialize-files` / `issue materialize-record` pair now uses the neutral C1
v1 ledger/envelope contract without a schema migration.

## Reviewed implementation

- Approved plan SHA-256:
  `7ed001a5f200109016d79298a5cd5dc86fe995d2964559808e6178db01be7dda`.
- Kimi worker session: `019f582d-a5e4-7000-8a07-16f24cebb8eb`.
- Initial implementation: `484779827cb60c5110a90ad2153a7d1a6aa6040d`.
- Corrections after three Codex request-changes rounds:
  `372b21ba4e05f2e7895e383d5b417fae2341d718`,
  `3507cc424669966064a4b1dac70a35a8a4490469`, and
  `db08180be806bf0a04ca8b8eaf43e217944d36df`.
- Final reviewed/integrated Coordinate head:
  `a21d946e4d6be78f3f481d38eb2571229a4d3a9f`.
- Result review: `result-review-round1.md`, `result-review-round2.md`,
  `result-review-round3.md`, and `result-review.md`.
- Provider stayed `kimi-code/kimi-for-coding-highspeed`; GLM fallback was not used.

The review closed topology-dependent baseline proof, missing reason propagation,
discarded ledger output, incomplete replay evidence, combined-command drift,
runtime-guard classification, mirror/ledger/event/delivery drift coverage, and a real
no-ledger delivery-collision defect. A fresh record transaction now refuses every
existing event or delivery idempotency key and rolls back all new effects.

## Verification

- Worker and Codex full suites: `1733 passed, 435 subtests passed`; the same nine
  pre-existing Python 3.12 argparse/AST historical failures remained un-rebaselined.
- Codex clean focused gate: `417 passed, 1 deselected, 49 subtests passed`.
- C2 class: `53 passed, 28 subtests passed`.
- Touched-path `ruff`, `compileall`, and `git diff --check`: pass.
- Fixed C2 node witnesses independently match the post-C1 `1cbb547` fixture.

## Production deploy

- Predeploy DB backup:
  `/var/lib/coordinate/coord.sqlite3.before-s4c2-20260712T221137Z.bak`.
- Backup SHA-256:
  `c0fae9de5c950b9eb8e6b5135344521fda756b6bbc6e901823a656b8a00304d0`.
- Backup schema/integrity: v11 / `ok`.
- Deployed Coordinate: `a21d946e4d6be78f3f481d38eb2571229a4d3a9f`, installed into
  `/opt/coordinate/.venv`; runtime import resolves from `site-packages`.
- Deployed completion projection: MultiNexus
  `6d913b64a410c7bc3950aff575a7904586e84135`.
- Production schema/integrity: v11 / `ok`; production has zero
  `issue.materialize` ledger rows because all dogfood used isolated DBs.
- Stable services: Coordinate PID `653825`, bridge PID `341847`, both
  `NRestarts=0`; repeated `server smoke OK`.

## Isolated dogfood

The same temporary script ran against the local source and the deployed server wheel.
Both runs proved:

1. files half writes the source projection only;
2. record before simulated deploy returns `files_not_deployed`;
3. deploying the plan/checklist enables one atomic record and delivery;
4. delivery advances to `sent`, exact retry returns `event_created=false` and keeps
   the progressed row;
5. an injected failure after `issue.materialized` restores the accepted mirror and
   leaves no ledger row for the interrupted operation;
6. deployed source drift returns `operation_conflict`;
7. isolated schema is v11, integrity is `ok`, and temporary roots are removed.

## Lifecycle evidence

- Closeout request: `40f8b699-af18-4e06-aa7e-e58f9291e1ec`.
- Result approval: `82fe76a4-30f2-4053-9515-a6e16f763294`.
- First receipt `924714d9-4153-452b-891b-d40a144a963c` failed closed before claim
  because local/deployed lifecycle projections had different fingerprints.
- Terminal receipt: `06a7fa5c-b6de-487a-9c93-36f85660beca`.
- Authorized: `c70b82e7-dcba-410d-a7e0-f6fd1c9f8c1b`.
- Claimed: `2c49df35-1471-45d4-ad93-0e8f25c27ebf`.
- Applied: `311e152d-6af5-494a-a230-95a9e35851da`.
- Fingerprint:
  `6b25c0b31f32a7dfb2c51497bc467d2e00cb718eb921f67b75d1023cbb20ebd1`
  -> `05d51ed894b51bb7ec7a7d181a8869b3c523610c65156c7d00f597f91d58efdf`.
- Terminal `task.done`: `050f8c0c-b156-4193-8e61-bbcdd23fedf5`.
- `completion.consumed`: `680e3ec4-f44b-4251-a4a4-c4ad4b3b87c8`.

The failed first receipt was resolved only by replaying the same closeout/review
transitions in canonical Git source, committing/deploying that projection, and issuing
a new receipt. No direct JSON/DB repair or force path was used.
