# P9-0A4a Durable Closeout

## Status

P9-0A4a is durably **done/closed**. Receipt-aware completion CLI ownership now lives
in `coordinate.completion_cli`; root still owns the assignment parser and supplies its
subparser to the completion registrar. P9-0A4b workflow/assignment extraction is next
and remains unauthorized until its own detailed plan and independent review complete.

## Approved identities

- Plan SHA-256:
  `3f060777f40210a23ff6781c4937eccff32e060b8abf34c226436fc6e1556b28`.
- Plan commit: `bc434a3839f441334d8d0e89ca1fc27b209c74e7`.
- Plan reviewer: `kimi-code/kimi-for-coding-highspeed`.
- Plan-review OMP session: `019f570d-62de-7000-9131-666e8054f23f`.
- Coordinate start: `cfcb56f6605b381d54d6a9ca335b602c41e6e8ab`.
- Worker implementation: `41b6a9c0b8e85d86119267b9d779e2d81ea7be40`.
- Review correction: `4526d098ba4edcdcf669c41b6b6d827373088e5a`.
- Integrated/pushed Coordinate `main` / `origin/main`:
  `4526d098ba4edcdcf669c41b6b6d827373088e5a`.
- Worker OMP session: `019f5714-06fb-7000-b60c-744542c54755`.
- Provider transition: none; Kimi remained available and GLM fallback was not used.

## Result

Exactly five approved Coordinate paths changed:

- `src/coordinate/cli.py`;
- `src/coordinate/completion_cli.py` (new);
- `tests/fixtures/cli_contract.json`;
- `tests/test_cli_contract.py`;
- `tests/test_completion_cli.py` (new).

The new module owns six receipt-aware leaves and 14 measured functions. Root retains
legacy mark-done, assignment/workflow ownership, the global dispatch exception tuple,
and direct compatibility aliases. Receipt order remains preflight -> claim -> local
write -> apply; record consumes only a valid applied receipt. The moved function ASTs
are identical to reviewed start `cfcb56f`, and no root/workflow/delivery/execution
backedge was added.

Contract counts remain 21/75/99. Fixture SHA moved from
`0bb76d483de6fcc122e82e5f242d34d326abc57e02b4647478320555dc5bc0bb`
to `a7c6e955062078bd67795f45dcdc27d82d076b31084e38ed1e459b8d4f758aca`.
Six layered rewinds reproduce all accepted P9-0A3b through P9-0A1 fixtures. Codex
independently passed 59 boundary/contract, 342 existing focused, 401 total focused,
and 1,523 full tests.

## Gate and lifecycle evidence

- `plan.ready`: `427423c9-ee19-401b-8654-d0e1c78e0541`;
- `plan.review_requested`: `064e0692-d8bd-4855-832d-b415ff87e5bb`;
- reviewer handoff: `8b4ebb54-f2bd-4380-9581-8145fddb63c0`;
- `plan.approved`: `52b73c62-2fc5-451f-9138-ede593cbcf1c`;
- successful assignment requested: `8a32f909-2b6b-421d-9f05-6c75ec687875`;
- assignment accepted: `9af1b838-e8a6-4d8f-9fa7-0491565c20b5`;
- worker handoff: `ff79ef1d-9086-40b6-9cfe-ab55a9a6e3ab`;
- closeout requested: `f420bb68-82a6-4f3c-96f2-3781fcc049b2`;
- review approved: `2f5c1426-037f-4724-8e0d-6246ea0ad0be`.

Receipt `23b7563a-89c7-4642-992f-5d50ebdefca0` produced exactly one terminal chain:

- authorized: `383e2166-f52c-4a0b-a087-ccfebcdae8c0`;
- claimed: `56f1b754-e2ac-446e-a3a8-2b1b99b13a54`;
- applied: `a4749437-92f9-4967-9bf4-e0af46fa2b97`;
- `task.done`: `05ce756a-13c2-4b46-902c-bb0b107ac498`;
- consumed: `4d7e114f-d525-4270-896e-8f18ffb39c38`.

Fingerprint moved from
`341aebe44e84c9439d25524ed0ac6830628739e0196321991ace44a5f80b6148`
to `123063c7b06c8c833ba50f42760b87f0da2f9165db5a486991d3c78a1c4ef231`.
Canonical checklist commit `92afd51ab9725bd2a3c6218b4f41860c630b330b` was pushed and
deployed before `task.done`; remote verification observed the same after fingerprint
with `status=done` and `workflow.status=closed`.

## Review and dogfood notes

Codex rejected the first security-order test because it recorded only preflight, claim,
and apply; the local write mock was absent from the shared call sequence. Correction
`4526d09` adds `write` and locks the exact order
`[preflight, claim, write, apply]`. The implementation bodies themselves were already
AST-identical and were not changed by the correction.

The first task materialization used legacy server-side `task create`. A later deploy
correctly replaced the `/opt` checklist with canonical source, so assignment failed
closed in event `d732d7e5-941d-49a3-87fa-5c57700df220` with `Checklist item not found`.
Operator recovered through the intended host-aware flow: local `task create-files`,
commit/deploy `11d4271`, and idempotent `task create-record` using the original
`plan.ready` key. The successful assignment used a new idempotency key. No direct JSON
or DB repair was used.

The shared Coordinate checkout independently acquired a different set of uncommitted
P9-0A4a-looking edits. Operator preserved them in named stash
`safety: preserve concurrent canonical P9-0A4a edits before reviewed integration` and
left unrelated `.qoder/` untouched. The earlier P9-0A3b safety stash also remains.

Deploy breaker scans observed the known concurrent-pump `sending` race on deliveries
`fc7b140e-4287-40c7-96ce-26273853e7c2` and
`c39a0bcc-139c-45d4-a8d8-ece666234562`. Both authoritatively became `sent` with no
last error; the latter has a platform message id. This repeated evidence remains owned
by Slice 4 / Phase 9 runtime hardening and was not mixed into the static extraction.
