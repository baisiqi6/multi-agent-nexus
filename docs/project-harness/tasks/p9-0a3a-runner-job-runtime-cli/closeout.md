# P9-0A3a Durable Closeout

## Status

P9-0A3a is durably **done/closed**. Runner, job, and runtime CLI ownership now lives
in `coordinate.execution_cli`; the root remains a static compatibility facade and
composition root. P9-0A3b delivery/policy/worker extraction is next and remains
unauthorized until its own detailed plan and independent review are complete.

## Approved identities

- Plan SHA-256:
  `66784772f8b356018bdb1674b56c00bf602bb76ce226c8acb0b789e52cf49b9b`.
- Plan commit: `d5b9783995496c70e07a3db319610f88c8e21210`.
- Plan reviewer: `kimi-code/kimi-for-coding-highspeed`.
- Plan-review / worker-review continuity session:
  `019f56b7-90f5-7000-b2a1-d6963f7fd98c` for plan review.
- Coordinate start: `10135bc3a49365a6c79d2088f4e3ff4b8015f27a`.
- Worker implementation: `d9faf1a6b4554d6c890bafe0d34d20767bd99aaa`.
- Review corrections: `3980fcf2128aa5cdab7a8e71ee0b99bdfc17dc0a` and
  `533ffcb1be17c6a26e8d5acf31e9c3c05da1ef63`.
- Integrated/pushed Coordinate `main` / `origin/main`:
  `533ffcb1be17c6a26e8d5acf31e9c3c05da1ef63`.
- Worker OMP session: `019f56c5-b9bf-7000-8d0e-8a2876dbe6ff`.
- Provider transition: none; Kimi remained available and GLM fallback was not used.

## Result

Exactly five approved Coordinate paths changed:

- `src/coordinate/cli.py`;
- `src/coordinate/execution_cli.py` (new);
- `tests/fixtures/cli_contract.json`;
- `tests/test_cli_contract.py`;
- `tests/test_execution_cli.py` (new).

The new module owns 16 leaves and 159 original handler lines: runner 33, job 56,
runtime 70. Root aliases remain object-identical, parser positions stay runner between
planning/reconcile, job between issue/delivery, and runtime between worker/assignment,
and root retains the `JobError` dispatch catch. No P9-0A3b, Slice 4, schema, service,
runtime, deployment, or live-job behavior was added.

Contract counts remain 21/75/99. Fixture SHA is
`fbdb5064f1d4870e5ee3ae68628c7cd8be618c37d085530f03336899a82e949c`.
Layered rewinds reproduce P9-0A2c `dde4c0d7...`, P9-0A2b `adddac8...`, P9-0A2a
`652a77d5...`, and P9-0A1 `83c4c181...`. Canonical validation passed 58 structural,
243 focused, four rewind, and 1,467 full tests. The execution proof also passed 31/31
on both Python 3.12.13 and 3.14.

## Gate and lifecycle evidence

- corrected `plan.ready`: `9d26272f-cd96-4153-8a33-0de294160f91`;
- corrected `plan.review_requested`: `15ee17d1-a47f-439f-bed1-9ff4d1f2fb67`;
- corrected reviewer handoff: `99a36275-083a-424e-942a-13f1141e3a0a`;
- `plan.approved`: `2680cf63-1947-4945-964b-c5f352ca0181`;
- assignment requested: `fd312228-7e29-4d76-93a6-c3dda8cdeb04`;
- assignment accepted: `fd2377e6-1eec-4bf1-b0cc-b1dd5d4b552c`;
- worker handoff: `b1930c57-1439-4203-aa55-1c7fca12ca1f`;
- closeout requested: `41497f4f-7aa3-42f5-8dd9-cbb9d84210f6`;
- review approved: `b33a66a3-6627-449a-b912-687d5fdae6cc`.

Receipt `19d917fb-fb66-49f8-91ad-92d95b8cc93f` produced exactly one terminal chain:

- authorized: `9b67a9a0-b359-4bca-a1bb-f6a40c2d9453`;
- claimed: `e21c5e3c-3c48-4f2b-a4e8-0cc26ffe1032`;
- applied: `2c133bdf-6e25-48d2-b8ee-0a49456546fc`;
- `task.done`: `5196eb5a-0b2b-468e-beb3-37c987c260e7`;
- consumed: `6c246dd3-f80c-4c3a-b980-038a0fc29864`.

Fingerprint moved from
`25f959d8ad47298cb851d7704871f5a08ba6a2855e7d4532d7ae8d9474acc827`
to `49c70c6d841b08d9f1545ab41975f0663d518a1eb1670887d09d411a8f9d0adc`.
Canonical closeout commit `247357d25e1c9eec1c11a1b63bebfb011c5f6037` was pushed and deployed before
`task.done`; remote verification observed the same after fingerprint with
`status=done` and `workflow.status=closed`.

## Review and dogfood notes

Codex rejected two successive proof designs despite green tests. Whole-`FunctionDef`
`ast.dump` hashes were Python-minor-sensitive; the first correction used
`ast.unparse`, whose pretty-printer has no cross-minor stability guarantee. The accepted
second correction uses a canonical AST projection that drops only `None`/empty
container fields and preserves node type, non-empty fields, scalar values, contexts,
and list order. The artifact is `result-review.md`.

The generic generated bootstrap again pointed at MultiNexus and `feature/multi-bot`
rather than the isolated Coordinate worktree. The source-controlled bootstrap
superseded it with exact repo, branch, commit, plan hash, paths, tests, and permissions.

The first `review-result` used the invalid value `approve`; Coordinate failed closed in
event `ca4c1928-a9f7-4384-8144-b0fd296be32e`. The retry used the required `approved`
enum and became the authoritative review event above.

Receipt claim initially failed closed because canonical source still recorded `todo`
while deployed harness recorded `review_approved`. Operator synchronized the exact
remote task lifecycle projection in commit `e0c70d839b16c486ea4aff83abdceb1480a2e9b0`;
the projected source fingerprint then matched the authorized fingerprint. No repair
path, legacy mark-done, direct DB edit, or unverified receipt claim was used.

Global reconcile remains independently blocked by the historical Phase 8.7 branch
conflict. This does not weaken the canonical done/closed item or terminal receipt chain,
but it remains evidence that reconcile needs per-item conflict isolation in Slice 4 or
a bounded repair package.
