# P9-0A2c Durable Closeout

## Status

P9-0A2c is durably **done/closed**. It extracted issue CLI ownership without changing
the public parser contract beyond the approved five handler identities. P9-0A3
execution/delivery CLI extraction is next and remains unauthorized until its own
measured detailed plan and independent review are complete.

## Approved identities

- Plan SHA-256:
  `d5ff4620afc7799bcc050c960bd1491f82a136ec829431f92d04e021bb88d444`
- Plan-introducing MultiNexus commit: `3fef5b17a32865f25a6a411ded1f8b52d02d91ef`
- Plan reviewer: `kimi-code/kimi-for-coding-highspeed`
- Plan-review session: `019f5601-9a0a-7000-b739-15812644bbb4`
- Coordinate start: `38da30f8bb508638e0cc30c301968153a420bdb7`
- Worker implementation: `3ae4f9f8d9de381210dab2d4d2a4cc5414bc831d`
- Reviewer correction: `d978d755752e117b8f1d05e0d9bd41dec8cac13c`
- Integrated/pushed Coordinate `main` / `origin/main`:
  `10135bc3a49365a6c79d2088f4e3ff4b8015f27a`
- Worker OMP session: `019f5606-3bc7-7000-9bee-ebe1c0edfe31`
- Result verdict: `result-review-round-1.md` approved after correction.

## Result

Exactly five approved Coordinate paths changed:

- `src/coordinate/cli.py`
- `src/coordinate/issue_cli.py` (new)
- `tests/test_cli_contract.py`
- `tests/test_issue_cli.py` (new)
- `tests/fixtures/cli_contract.json`

`issues.py` is unchanged. The root remains a static facade and calls the issue registrar
after merge and before job. Five public root handler aliases are object-identical to the
new owner, no moved root `FunctionDef` remains, and the new module has no root backedge.
The event-CLI scan path still bypasses local DB opening; combined/files-only/record-only
materialization responsibilities remain unchanged.

Contract counts remain 21/75/99. Fixture SHA is
`dde4c0d7d8ac2b732be8cd3d2f915c880019c93ca993783c7a8cd0a1bd104c5f`.
Layered rewinds reproduce P9-0A2b `adddac8...`, P9-0A2a `652a77d5...`, and P9-0A1
`83c4c181...`. Canonical validation passed 46 boundary/contract tests, 242 related
focused tests, and 1,434 full tests.

## Gate and lifecycle evidence

- `plan.ready`: `fd9d578a-80ad-4443-aca9-abac13fb62a9`
- `plan.review_requested`: `016d9fcb-4de0-4951-93c2-3560e70ad70a`
- reviewer handoff: `d061a181-0a1d-4997-97d3-1356c1a2263d`
- `plan.approved`: `50d40775-d0f0-459a-89f9-e530197be0f9`
- assignment requested: `50cefcbb-12aa-4296-a9e2-dcb9674e7385`
- assignment accepted: `4e2bcd6e-69a2-422c-b47d-d702fa590a0a`
- worker handoff: `ac2bbd23-094b-40b0-b049-b69c6ad640e9`
- closeout requested: `d932abc2-15b8-4359-8ccd-1a5faa22ffe4`
- review approved: `fcaed612-4e83-45a6-8b2e-cba231ea34eb`

Receipt `2ce2cedc-33ca-4f4f-b66f-c9d6034c262a` produced exactly one terminal chain:

- authorized: `dbf33365-7edd-4c8e-81f4-fed7b4452aee`
- claimed: `2268d538-8c42-4905-b4d5-bab94fbf4c2f`
- applied: `dcb77527-a279-4845-a230-428d225cf363`
- `task.done`: `9a10544d-b887-4c43-a116-553634656941`
- consumed: `061c5eb8-1b58-4085-9367-3910787a2b4f`

Fingerprint moved from
`81f817dc7b9a7161c71cc1caad94cdbac0ba9f8486aa40dd4e87a694d888012b`
to `47e967559414b386e6c1402242bceb0a0b51a24a45375341f0a9a4a6cde45016`.
No legacy mark-done, repair path, or direct JSON/SQLite edit was used.

## Review and dogfood notes

Codex caught two weak permanent tests despite 1,433 green tests: a `git show` dependency
that would fail in shallow/source-archive environments, and a test claiming root
definition absence while checking only alias metadata. Kimi resumed the same JSONL,
replaced the former with stable per-handler AST body hashes and added a real root AST
definition check. Full count became 1,434.

The reviewer initially ran a full suite from the MultiNexus cwd, detected the wrong
modules in JSONL, discarded that run, and reran the accepted 1,411-test baseline from
Coordinate. Kimi quota remained available; GLM fallback was not used.

The generic reviewer and worker bootstraps again pointed at nonexistent OpenSpec or
`/opt/multinexus`/`feature/multi-bot` implementation paths and required exact
supplements. Assignment created pending delivery
`0c0cde61-afd5-4f72-a129-5533549a9bb1`; it remains unpumped.

Operator proactively replayed assignment/accept/closeout/review through local
`harnessctl` before receipt claim, so local source and deployed projections shared the
same before fingerprint; unlike P9-0A2b, no fingerprint mismatch retry occurred.

Global reconcile remains blocked by the independently routed historical Phase 8.7
branch conflict. The P9-0A2c canonical checklist and receipt/event chain are terminal,
but its control-plane task mirror remains stale at `ready` until reconcile gains
per-item conflict isolation or that old conflict is resolved.
