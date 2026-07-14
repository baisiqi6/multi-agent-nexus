# P9-3B Durable Closeout

Date: 2026-07-14  
Status: complete; synchronized production deployment accepted and terminal receipt consumed

## Accepted implementation

P9-3B wires the P9-3A capacity and attempt-lease authority into runtime claim,
heartbeat/renew, report/progress fencing, release/reap, worker cancellation, and
provider process-tree cleanup. It keeps provider-native execution behind MultiNexus
while Coordinate remains the deterministic lease authority.

- Coordinate main/upstream/deployed: `3eaa7bfdeb0f660da46bd7fe6003231822c9658c`.
- MultiNexus implementation: `0348c8b`.
- MultiNexus integration main deployed before closeout projection: `6bc1adfd30fc46911e320f52506b9d50f0032663`.
- Approved plan SHA-256:
  `5c04d3bd8d297da1565d67a4aa41b679559481a3bed75ede287dd941f75b1378`.
- Final result verdict: `approved for durable closeout` in `result-review.md`.

## Verification and production

- Coordinate full gate: 2396 passed and 493 subtests passed, plus the exact nine
  historical CLI/AST failures.
- MultiNexus full gate: 650 passed, 2 skipped.
- Every constructible provider adapter owns a cancellable child process group; real
  POSIX tree cleanup and Windows API contract tests passed.
- Fresh backup:
  `/var/lib/coordinate/backups/coord.sqlite3.p9-3b.20260714T184701Z`, mode 600,
  integrity `ok`, schema 13, SHA-256
  `5a6e3faae9593ad8f152d1d15034174a78280b7ee4f20ab83e5ba7c89b5ddf3b`.
- Coordinate and MultiNexus were synchronized while both services were stopped to
  avoid an incompatible producer/consumer window; both returned active/running with
  `NRestarts=0` and server smoke passed.
- Final DB integrity/FK/schema: `ok/0/13`; nonterminal jobs 0; attempt leases
  active/total `0/0`; deployment residue 0; error-priority journal empty.
- No production execution job or lease was created. The production concurrency,
  crash, reap, and recovery matrix remains P9-3C.

Detailed evidence is in `implementation-report.md`, `result-review.md`, and
`deployment-dogfood.md`.

## Durable lifecycle

Local canonical review lifecycle:

- `assignment.requested`: `8b715d40-1c93-4441-99fa-e24cb3b8dacf`.
- `assignment.accepted`: `b44d1672-3559-4e93-9350-fb1da2c7c0c3`.
- `closeout.requested`: `e500773a-842b-4905-acd1-d1d6b62038f5`.
- `review.completed`: `3e93a81f-9930-4587-8ac3-1f1b924725a8`.

Production host-aware completion:

- Receipt: `8f36d34c-0485-4cef-be54-8eaad08404e2`.
- `completion.authorized`: `bf3b551a-3b21-48c4-a68d-65133c838d8b`.
- `completion.claimed`: `dc45826a-195b-41c5-bf65-14dcfb581140`.
- `completion.applied`: `8486e57f-a87a-4f4d-9f4e-486c0606fe3a`.
- `task.done`: `de7a0b5b-d488-4800-8cc0-fc6dd4547add`.
- `completion.consumed`: `97c546a4-44ef-4ce7-bf3c-74cec2427ed0`.
- Fingerprint:
  `07bf20b961012279dbe225684ca8577e22178b7948547e6754f0c545bbdb75ee`
  -> `e407e9608d602f88716fc4da8fbbbf3adc97ad91ea74a9962877f01933beed40`.

The receipt-applied checklist was committed as `82fe511`, pushed, deployed, and
verified byte-identical before record. The normal completion used online preflight,
claim, canonical file mutation, deploy verification, record, and consumption; no
repair, force, legacy path, direct JSON edit, or SQLite mutation was used.

## Residual observations

- Production receipt review evidence is `not_applicable` because the local lifecycle
  review event is not mirrored into the production event store. Authorization still
  required the deployed canonical task projection to be `review_approved`; the exact
  local review event and summary are retained above. Event-plane mirroring remains a
  future projection/control-plane hardening topic.
- Windows process-tree behavior has contract proof but no real Windows tree smoke in
  P9-3B. This is not represented as runtime proof.
- The nine Coordinate full-suite failures and MultiNexus full-repo Ruff findings are
  historical, exact, and outside the changed scope; they were not silently rebaselined.

## Next gate

P9-3C is limited to fresh measurement, an independently reviewed detailed plan,
exact-revision approval, checklist registration, and a new bootstrap before any
disposable production concurrency/crash/recovery execution. It must prove capacity
saturation/release, worktree exclusion/concurrency, quiet renewals, crash/expiry/reap,
attempt `N+1` recovery, stale attempt `N` rejection, restart behavior, residue, and
data integrity without using real user jobs.
