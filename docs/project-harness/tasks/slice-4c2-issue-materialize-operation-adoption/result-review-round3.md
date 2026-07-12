# Result Review Round 3 — Changes Requested

- Reviewer: Codex
- Coordinate review head: `3507cc424669966064a4b1dac70a35a8a4490469`
- Decision: `changes_requested`

## Closed from Round 2

- Legacy combined error shape was restored.
- The host-aware runtime-copy guard is `validation_error` without changing combined.
- Exact-replay state/event/delivery probes and real reason-boundary tests were added.
- Touched paths passed `ruff`.

## Remaining findings

1. On a fresh no-ledger transaction, a supported delivery result with
   `created=false` and an existing row was accepted. The approved contract requires
   any pre-existing delivery idempotency key without an exact ledger to fail closed
   and roll back all new record effects.
2. The `plan.ready` metadata table test restored each subtest from the already
   tampered row, so later fields were not independently proven.
3. Progress documentation contained amend-before SHAs and inaccurate patch/evidence
   text.

The result remained blocked from integration and deploy.
