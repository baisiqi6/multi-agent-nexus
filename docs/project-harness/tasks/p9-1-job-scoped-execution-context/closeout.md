# P9-1 Durable Closeout

## Accepted implementation

P9-1 is durably closed as the first Phase 9 runtime-isolation package.

- Coordinate owns and persists immutable `ExecutionContext` v1 snapshots per managed
  job, validates replay/backfill/claim identity, and preserves public import and
  handoff-profile compatibility.
- MultiNexus consumes the full claim envelope, validates the context before provider
  invocation, and uses its worktree/session authority for every managed adapter and
  session-store operation.
- Managed worker/reviewer handoffs use versioned host paths and do not read Coordinate
  SQLite. Missing or malformed authority fails closed with one visible blocker.
- Schema remains v11. P9-2 owns rerouting/scheduling; P9-4 owns richer provider JSONL
  liveness semantics.

## Review and integration

- Approved plan SHA-256:
  `c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e`.
- Plan reviewer session: `019f598b-6caf-7000-9bf3-c412a01f6405`.
- Final correction worker session:
  `019f59ed-25fe-7000-9b99-7ec15882c76c`.
- Codex result review: Rounds 1–4 `changes_requested`; Round 5 `APPROVE`.
- Result-review approval event: `223d2f55-ffec-477a-a7ab-b0e294bc0949`.
- Integrated code commits:
  - Coordinate `b732159c4a1bbced39dc6ab9cde8841e7959a8cb`;
  - MultiNexus `066ca74980132ce7d98a9cd315bfeab56574c526`.
- Verification:
  - Coordinate focused: `525 passed, 88 subtests passed`;
  - Coordinate full baseline: `1944 passed, 449 subtests passed` plus exactly nine
    historical CLI/AST failures;
  - MultiNexus full: `461 passed, 2 skipped, 26 subtests passed`;
  - both compile/diff gates clean and cross-repository fixture SHA
    `975be64ca2cba84530cf969038cce4c5fb74df0b5f33aed86df9352ec9d12786`.

## Production evidence

- Coordinate DB backup:
  `/var/lib/coordinate/backups/coord.sqlite3.p9-1.20260713T053258Z`.
- Producer-before-consumer deployment installed both runtime packages and restarted
  Coordinate, MultiNexus, and all four local managed agentd services.
- Server smoke passed against both actual deployment restart boundaries.
- Real managed job:
  `request:ced328ec-4a97-4052-817e-bb4ab5adb4fc`.
- Immutable context id:
  `sha256:bf7f6096230afa8f524c8e9ed4e44666dd8b8b9ca2076002247d443a10575bb9`.
- `job.claimed` event: `c9a7f35c-9917-4c15-85f4-e6472566da33`.
- `job.completed` event: `3c91efd3-1356-4475-8713-a28c73b12112`.
- Exact provider result: `P9-1_EXECUTION_CONTEXT_OK`.
- Sent reply delivery: `5f0bae5f-0d67-48f2-9f2a-5b8b40c86671`.
- Detailed evidence: `deployment-dogfood.md`.

## Closeout and terminal receipt

- Closeout requested: `8b1f410c-8ff1-4d47-8861-16877018e4ae`.
- Final closeout approval: `c0d82102-66a3-441d-8c2e-f5a3e8516734`.
- Lifecycle projection commit: `b3a3fd50837e7e46ddc36f10a1812db3882fcdb5`.
- Receipt-files commit: `7031377eed4ad1edd3987d62cacbc9df816f8dc5`.
- Receipt: `e7feda4e-e0d7-4115-9cd0-fe713f87b5d8`.
- Authorized: `91a60cde-1bcd-42ac-b361-a59280d14243`.
- Claimed: `4336f717-1e02-4b90-b721-769d507806f3`.
- Applied: `616a1dc9-f6aa-4815-9388-077f6cea5f7d`.
- `task.done`: `bb16f54e-4d83-4ee5-97a7-ac46a9106d7f`.
- Consumed: `9b92d3e1-2a43-4bfa-9dbe-42ad671bce6f`.
- Receipt fingerprint:
  `24e80c08c8507a0bd4d5caa95e73a35b95ba5875f9621d9d35aef69f00df3c5e`
  -> `00a3188880a1266a2450e11aba4143c060605689bc3856c409357a83eb4f39f3`.
- Deployed verification: task `done`, workflow `closed`, fingerprint exact.

## Next gate

P9-2 is now the next Phase 9 detailed-plan package. It must receive a fresh detailed
plan, independent GLM/Kimi plan review, separate Kimi coding worker, Codex result
review, ordered deployment, managed-runtime dogfood, and terminal receipt.
