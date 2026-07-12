# P9-0A4b Durable Closeout

## Status

P9-0A4b is durably **done/closed**. Workflow and assignment CLI ownership now lives in
`coordinate.workflow_cli`; root remains the static composition/public facade and the
six receipt leaves remain owned by `coordinate.completion_cli`. P9-0A5 event
presentation is next and remains unauthorized until its own refreshed detailed plan,
independent review, and worker bootstrap complete.

## Approved identities

- Approved plan SHA-256:
  `62a7f267d5e68a42c68cc18553866302d18490b772b3472bc1f998dd1b622f7c`.
- Revised plan commit: `ac63cdb2d1d303d34fe16dd5bbe64412d766178f`.
- Plan reviewers: Kimi Highspeed sessions
  `019f572b-5869-7000-9063-ff9af65eea79` (Round 1 reject) and
  `019f572f-d55d-7000-ab5e-42911e15177f` (Round 2 approve).
- Coordinate reviewed start: `4526d098ba4edcdcf669c41b6b6d827373088e5a`.
- Worker implementation: `009533f8cc869a4b4596b648deda625859cee1d0`.
- Codex correction / integrated and pushed Coordinate `main`:
  `882c2a1487e4102d35c3c1f5b18b4a542be2d3bc`.
- Worker provider session: `019f5735-f0ab-7000-9588-8e694e5c662a`.
- Provider transition: none; Kimi remained available and GLM fallback was not used.

## Result

Exactly six approved Coordinate paths changed. `workflow_cli.py` owns three static
registrars and the 12 measured handler bodies. Root has no moved definitions, directly
re-exports every moved name, and preserves branch -> PR -> forge -> middle registrars
-> assignment -> operator -> serve. Assignment remains eight workflow leaves followed
by six completion leaves. `completion_cli.py` and all lower services are unchanged.

Contract counts remain 21/75/99. Fixture SHA moved from `a7c6e955...` to
`43e181046d3baa174199e3c02bcbc1ab1fedf83177d5c3725516a839bbb1f9e1`.
Seven rewinds reproduce every accepted P9-0A4a through P9-0A1 fixture. All 12 moved
functions are AST-identical to start `4526d09`. Codex independently passed 91
boundary/contract, 440 existing service-focused, and 1,555 full tests.

The worker's first green result did not prove fresh import orders for the new dependency
chain. Codex correction `882c2a1` adds three isolated import permutations across
completion/workflow/root plus an AST lock for the global exception dispatch tuple. No
production body or public contract changed.

## Gate and lifecycle evidence

- corrected `plan.ready`: `5d27f131-ef1c-4db2-891b-f8b6e093ffef`;
- corrected `plan.review_requested`: `9879b121-ef64-4725-960a-d831ca47e8a6`;
- corrected reviewer handoff: `a5ed3ec9-4236-4844-b03a-0eb476442d31`;
- `plan.approved`: `0fbdae56-ea25-4ca5-9037-1f13fe6e4608`;
- assignment requested: `882886dc-3bbf-483b-a3a1-14ad0ab67684`;
- assignment accepted: `1b46579e-1d4d-4740-8616-4444ad07e053`;
- worker handoff: `7015b680-be3b-4c59-b61f-e5b82d66503a`;
- production closeout requested: `fdb90545-6066-4387-b00b-c2cf4976db08`;
- production review approved: `9deef464-c364-42bc-8839-caceb03fcbed`.

Receipt `1c9269e9-e7b5-442c-b856-d0216d62bdab` produced exactly one terminal chain:

- authorized: `8909f9d5-8b53-49c2-a5a4-785698da953d`;
- claimed: `fcb19afc-5051-4400-8bf0-89059fd0ead8`;
- applied: `47011828-2bb3-46f4-b273-6cb4867176a6`;
- `task.done`: `637521bb-afd2-4040-b287-cb02abc1d2e4`;
- consumed: `60d0469c-3d60-4434-95b5-f2b3efde506d`.

Fingerprint moved from
`dfceae7efd659784e1b470c0c2959296f423c38f6748e32da101d8d6b4df795e`
to `74282c7c9c1198adc7a8232a6a7cabf8dde6666efe314720c21d09cf49fba8ae`.
Canonical checklist commit `9ebf4421528391e68f77ebacaf5d6673d93957b7` was pushed and
deployed before `task.done`; remote record verified the same after fingerprint with
`status=done` and `workflow_status=closed`.

## Dogfood and projection evidence

The source item was initially materialized correctly through host-aware `task
create-files` plus deploy and idempotent `task create-record`. The first DB-only record
attempt also exposed a duplicate branch uniqueness failure because the historical
`feature/multi-bot` branch was reused; retrying without unrelated branch metadata
succeeded. No direct DB edit was used.

After result-review documentation was deployed, canonical source still described the
task as `todo`, so deployment correctly replaced the runtime copy and removed the
earlier running projection. Operator replayed canonical `assign`/`accept`, committed
and deployed it, then replayed closeout/review on both source and production before
claiming the receipt. This kept source and deployed fingerprints aligned without direct
JSON repair.

Host-side `mark-done-files` was invoked with control workspace `discord-nexus`, while
its result envelope reported the harness-config project id `local`. Receipt events and
terminal record correctly used `discord-nexus`, so closeout is valid, but the mixed
identity surface should be made explicit by Slice 4 rather than left to Operator
interpretation.

Concurrent-pump delivery races `b35a6365-1308-414a-b416-ea4a3d9a6cca`,
`e468a6e5-21e8-496f-ba7e-87f20986ba89`, and
`9c9f4f4d-4142-4b51-b4b6-956ec10dee41` all authoritatively ended `sent`, with platform
message ids and no last error. The repeated race remains routed to Slice 4/runtime
hardening; it was not mixed into this static extraction.

Global reconcile remains blocked by the historical Phase 8.7 branch conflict, so the
task mirror payload remains stale even though canonical files, deployed verification,
and the terminal receipt chain are authoritative.
