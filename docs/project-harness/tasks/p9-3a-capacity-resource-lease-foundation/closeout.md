# P9-3A Durable Closeout

Date: 2026-07-14  
Status: complete; production deployment accepted and terminal receipt consumed

## Accepted implementation

P9-3A adds a separately versioned capacity authority, deterministic worktree resource
identity, and transaction-owned attempt lease primitives without changing runtime claim
behavior. Snapshot capture/restore and guarded deployment fail closed on malformed or
corrupt state and preserve the pre-deploy authority/projection on recoverable failures.

- Coordinate: `af8461efdf6beb7c47560fe3d17b30f2ac6696ba`.
- Final MultiNexus lifecycle head before this closeout document:
  `47e1aa5b6a13077e0528c845f1c99f69553237f8`.
- Approved plan SHA-256:
  `d75486b42e8d3315bda488db1129e02c03c0a2c152c04a60cccce917a385d99e`.
- Final local reviewer verdict: `approved_for_integration` in
  `result-review-round4.md`.

## Verification and production

- Coordinate focused 226 passed; full 2314 passed plus the exact nine historical
  failures; 493 subtests passed.
- MultiNexus focused 38 passed; full 530 passed, 2 skipped, 36 subtests passed.
- Backup:
  `/var/lib/coordinate/backups/coord.sqlite3.p9-3a.20260714T024320Z`, mode 600,
  integrity `ok`, schema 12, SHA-256 `30a5f29b...79ee99`.
- Production schema 13, integrity `ok`, foreign-key violations 0.
- Capacity source v1 covers eight enabled typed bindings; all policies have max 1.
- Production active/total execution leases remained 0/0.
- Disposable sidecar reserve/exact-replay/renew/release passed and sidecar was deleted.
- Both services active/running, `NRestarts=0`; bounded server smoke passed.
- No per-run staging, capacity snapshot, or authority backup residue remained.

Detailed evidence is in `deployment-dogfood.md` and the appended Round-5/6 section of
`implementation-report.md`.

## Durable lifecycle

- `assignment.requested`: `c5e13747-2cb7-49c9-9d02-4e82c2139112`.
- `assignment.accepted`: `3fd313e4-4698-4458-8209-e7ab34e0c1c9`.
- `closeout.requested`: `f8746e14-f560-4130-aca3-a8a7b3b73ef1`.
- `review.completed`: `945fa31a-5cf0-4c05-af68-3350a080a371`.
- Receipt: `da0349ec-6832-4c73-b67e-2a97e477fc46`.
- `completion.authorized`: `02d1ede8-d7ea-48c5-8b96-d319b24f168b`.
- `completion.claimed`: `dc75bf08-3970-479a-becc-63842e16413c`.
- `completion.applied`: `33c677f5-e2eb-47e1-b30f-024dfad2b123`.
- `task.done`: `b6725326-9ebf-4d70-bc96-a03606b5f260`.
- `completion.consumed`: `63648442-fa49-4452-b39e-1ee15207280a`.
- Fingerprint:
  `ffeb5078ca6f0caafc20dd464a6b53a70e79e9b3f8214e15cb31f21091e1d93a`
  -> `f5a4f7851072856dc8b04a0eb629f4b7209554f48355ffec8eed02389a893ef4`.

Canonical and deployed task projections were verified equal before authorization and
again before record. The lifecycle used only `harnessctl` and Coordinate host-aware
receipt commands; no direct file/DB edit, repair, force, or legacy mark-done path.

## Next gate

P9-3B claim/reserve/renew/release runtime wiring is next. It requires its own detailed
plan, independent plan review, exact plan approval, and fresh worker bootstrap before
implementation.
