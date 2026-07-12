# P9-0A3b Durable Closeout

## Status

P9-0A3b is durably **done/closed**. Delivery, policy, and worker CLI ownership now
lives in `coordinate.delivery_cli`; the root remains a static compatibility facade and
composition root. P9-0A4 workflow/completion extraction is next and remains
unauthorized until its own detailed plan and independent review are complete.

## Approved identities

- Plan SHA-256:
  `5a9438c345a67a4fb7d73ce4e7cade6f951f9b8da5bf46567b4270adaa153a2f`.
- Plan commit: `7c3137d`.
- Plan reviewer: `kimi-code/kimi-for-coding-highspeed`.
- Plan-review OMP session: `019f56ee-5849-7000-b2a1-d6963f7fd98c`.
- Coordinate start: `533ffcb1be17c6a26e8d5acf31e9c3c05da1ef63`.
- Worker implementation: `f1ccf37b565941bee9e3549306c602bd7e768e00`.
- Review correction: `cfcb56f6605b381d54d6a9ca335b602c41e6e8ab`.
- Integrated/pushed Coordinate `main` / `origin/main`:
  `cfcb56f6605b381d54d6a9ca335b602c41e6e8ab`.
- Worker OMP session: `019f56f4-79c4-7000-888a-05cc20a49cb5`.
- Provider transition: none; Kimi remained available and GLM fallback was not used.

## Result

Exactly five approved Coordinate paths changed:

- `src/coordinate/cli.py`;
- `src/coordinate/delivery_cli.py` (new);
- `tests/fixtures/cli_contract.json`;
- `tests/test_cli_contract.py`;
- `tests/test_delivery_cli.py` (new).

The new module owns ten leaves and 114 original handler lines: delivery 56, policy 44,
and worker 14. Root aliases remain object-identical, parser placement remains one
contiguous range after job and before runtime, and root retains the `BusError` and
`PolicyError` dispatch catches. No concurrent-pump race fix, Slice 4 behavior, schema,
service, daemon, harness, or deployment behavior was added.

Contract counts remain 21/75/99. Fixture SHA is
`0bb76d483de6fcc122e82e5f242d34d326abc57e02b4647478320555dc5bc0bb`.
Five layered rewinds pass, and all ten old/new canonical AST handler bodies are equal.
Canonical validation passed 53 boundary/contract, 384 focused, and 1,493 full tests.
The Python 3.12 delivery boundary also passed 24/24.

## Gate and lifecycle evidence

- `plan.ready`: `b8aec896-5336-4198-8e8d-3327319b6c3f`;
- `plan.review_requested`: `f2e0a18e-7187-41cb-beb7-91655f0cbd0e`;
- reviewer handoff: `0a0f7fdd-98f5-435c-b27c-a9c5b7bb9e80`;
- `plan.approved`: `c4d46ce9-a968-4152-b430-d66942097c57`;
- assignment requested: `a9b7843f-850c-485c-be9f-d45afbc3f3e2`;
- assignment accepted: `6caa253b-257e-43a7-ba85-737c1f8e323b`;
- worker handoff: `ab671233-1fe2-40e7-817b-6850e53124c2`;
- closeout requested: `b48cec19-20b1-4687-8243-44ee079e5a9d`;
- review approved: `0a16cd9c-22a6-4872-a186-461e6646d655`.

Receipt `63c3543b-bf56-45f2-bb40-8c2a805ed883` produced exactly one terminal chain:

- authorized: `e852b70a-787c-439e-ba9e-20b5411e7aad`;
- claimed: `87b671b3-e887-4fd5-8f5b-45b9a65b2921`;
- applied: `de7eb4c3-e757-4be6-8ea4-df731f6b0876`;
- `task.done`: `1ed663f4-be48-4caa-8d19-3c37f1ba01e4`;
- consumed: `fd651891-b7e2-4010-ae23-76f6119fb835`.

Fingerprint moved from
`955b7c5ab80a2122fda7e9d1284df7ea935ba444b2213adc4c7094064ba41e71`
to `fca58d44754071bb5300fb6ff0b3e098fee03822200c6601385f0c45d8900ab3`.
Canonical checklist commit `0eb1f06c0e02752b9fe16fe03e30d936c7595e33` was pushed and
deployed before `task.done`; remote verification observed the same after fingerprint
with `status=done` and `workflow.status=closed`. Server smoke passed.

## Review and dogfood notes

Codex rejected the worker's out-of-scope removal of the pre-existing root
`get_workspace` import. Correction `cfcb56f` restored it before integration. A named
safety stash preserves unrelated concurrent canonical edits discovered during
integration; it was neither applied nor dropped. A later unrelated dirty change to
`tests/test_delivery_cli.py` also remains untouched in the shared Coordinate checkout.

The generic generated bootstrap again described the MultiNexus checkout rather than the
isolated Coordinate worktree. The source-controlled bootstrap supplied the exact repo,
branch, commit, plan hash, allowed paths, tests, and permissions and was authoritative.

The first record-side closeout attempt used the local `mac.sh` fallback and failed
closed with `unknown_receipt`; the receipt had been issued by the production Coordinate
DB. Replaying the same idempotent operation through the required
`/Users/yinxin/.local/bin/coord-ssh` boundary succeeded. No direct DB edit, repair path,
legacy mark-done, or duplicate terminal event was used.

The previously observed delivery pump `sending` race remains excluded from this static
extraction and is retained as Slice 4 / Phase 9 evidence. Global reconcile also remains
independently blocked by the historical Phase 8.7 branch conflict; neither residual
weakens this package's terminal receipt chain.
