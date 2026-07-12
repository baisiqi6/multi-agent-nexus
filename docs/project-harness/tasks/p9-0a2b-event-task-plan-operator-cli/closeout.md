# P9-0A2b Durable Closeout

## Status

P9-0A2b is durably **done/closed**. It extracted event/task/plan/operator CLI
ownership without changing the public parser contract beyond the approved ten handler
identities. P9-0A2c issue CLI extraction is next and remains unauthorized until its
own detailed plan and independent review are complete.

## Approved identities

- Plan SHA-256:
  `b17714dc5d06a38363dfabdc1f66d4d684d312410f3ce11a1b054202830249d5`
- Plan-introducing MultiNexus commit: `30c9ef75070cc751a52576221fdb904ee8df1286`
- Plan reviewer: `kimi-code/kimi-for-coding-highspeed`
- Accepted plan-review session: `019f55e4-ee41-7000-8a14-368e4db6abd0`
- Coordinate start: `10862d97d02d6e20b191005f02a732c6fa44ad59`
- Worker implementation: `320b501`
- Reviewer correction: `d250e47`
- Integrated/pushed Coordinate `main` / `origin/main`:
  `38da30f8bb508638e0cc30c301968153a420bdb7`
- Worker OMP session: `019f55ea-75fa-7000-949c-7d4216f9c4bc`
- Result verdict: `result-review-round-1.md` approved after the test-isolation
  correction.

## Result

Exactly five approved Coordinate paths changed:

- `src/coordinate/cli.py`
- `src/coordinate/planning_cli.py` (new)
- `tests/test_cli_contract.py`
- `tests/test_planning_cli.py` (new)
- `tests/fixtures/cli_contract.json`

The root remains a static composition facade. Event/task/plan registration remains
before runner; operator remains after assignment. Ten root aliases are object-identical
to the new module's handlers, the new module has no root backedge, and all ten handler
AST bodies match the start revision. `latest_prepared_handoff_bootstrap` remains in the
root for the unmoved assignment handler, and task-handoff repository-root resolution is
unchanged.

The normalized contract remains 21 top-level commands / 75 leaves / 99 nodes. Fixture
SHA is `adddac8bd623b20a1f8b0f931e0ae83a45148315652c220d6f70c276f0f7cc74`.
Rewinding P9-0A2b reproduces P9-0A2a SHA `652a77d5...`; rewinding P9-0A2b and
P9-0A2a reproduces P9-0A1 SHA `83c4c181...`. Canonical validation passed 48 focused
and 1,411 full tests.

## Gate and lifecycle evidence

- `plan.ready`: `c7b0d0e2-cad8-4767-b95a-a8ef3a6984f3`
- `plan.review_requested`: `1cb205ff-9614-4232-97ec-7df5a8400d36`
- reviewer handoff: `363eefd2-0afc-495c-a1db-f3d655c871df`
- `plan.approved`: `7ae48999-645f-4d29-a181-3b22cdf9630a`
- assignment requested: `6834a2e8-02e5-422e-8bd7-1a80dead20de`
- assignment accepted: `00fc3284-38fd-4998-abc3-aac79e55f99b`
- worker handoff: `9b08faee-a759-4571-a0ac-0d4f4534631d`
- closeout requested: `a5d3f663-9c98-40af-82ed-05ac65707576`
- review approved: `529e342e-50c1-40f6-b9fd-2ea8d5a6e841`

Receipt `4c85dd46-97b7-415f-85a1-450107e30112` produced exactly one terminal chain:

- authorized: `9ebc372b-c8aa-4c49-aae6-9a8b0e2cae76`
- claimed: `d74f0d39-7acf-4ab1-b1d6-cb3a2aa738ac`
- applied: `bcc92be9-99b4-4763-b482-7f32caa9f696`
- `task.done`: `032f991e-84f7-4355-b937-ab0454fa8544`
- consumed: `5311fca4-e6cd-4592-9180-193674880d97`

Fingerprint moved from
`4fffae00e7c80f396798be4e5b97700aacf1929fbba31db19c8a77940281a671`
to `52198c058cecb2c49df6fb0acfd9880ddad822839344b5da9beefac60a24089c`.
No legacy mark-done, repair path, or direct checklist/SQLite edit was used.

## Dogfood boundary and residual

This package is semi-dogfood: Coordinate carried the plan, assignment, lifecycle and
receipt gates, while the reviewer and worker ran as supervised local OMP sessions.
Kimi remained available, so the authorized GLM fallback was not used.

The first remote closeout/review attempt failed closed because deployed MultiNexus
did not yet contain the newly committed checklist item (`harness.mutation_failed`
events `d12f0a77...` and `df624ee3...`). After deploying canonical MultiNexus, retry
succeeded. The first receipt file attempt then failed before claim because local source
was still `running` while the deployed projection was `review_approved`; replaying the
same approved harnessctl transitions locally aligned fingerprints and allowed the
terminal chain. This exposes a repeated source/deploy projection UX gap.

Final global reconcile is not claimed: it fails closed on an unrelated pre-existing
`phase-8.7-worker-self-test` branch conflict (`agents/mac-opencode/...` in harness vs
`agents/mac-omp/...` in the task mirror). P9-0A2b canonical checklist and receipt/event
chain are terminal, but its task-mirror creation is deferred behind that independently
routed reconcile conflict.

Assignment request also created pending delivery
`02c5fe8d-5b04-4292-936f-7c1f5ca5db3a`; it remains unpumped.
