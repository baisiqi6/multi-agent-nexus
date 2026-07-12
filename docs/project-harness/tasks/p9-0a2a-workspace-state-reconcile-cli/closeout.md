# P9-0A2a Durable Closeout

## Status

P9-0A2a is durably **done/closed**. It extracted workspace/state/reconcile CLI ownership
without changing the public parser contract beyond the approved 11 handler identities.
P9-0A2b is next and remains unauthorized until its own detailed plan and independent
review are complete.

## Approved identities

- Plan SHA-256:
  `24197103213a6644125f1c6a6528f5b74ce0f1ba594eefa5567e41d8ba0f3598`
- Plan-introducing MultiNexus commit:
  `f8f4922b62ee1e365fcc3cb7d2159b3784a73b90`
- Plan reviewer: `kimi-code/kimi-for-coding-highspeed`
- Accepted plan-review session: `019f55c9-38b7-7000-be88-ba0c372c3fbf`
- Coordinate start: `947368a4c278aa847b40eea20a7088c5cb28446f`
- Worker implementation: `e4c98ea44f609ee7468d283a82840b16e41a9fec`
- Review correction: `10862d97d02d6e20b191005f02a732c6fa44ad59`
- Integrated/pushed Coordinate `main` / `origin/main`:
  `10862d97d02d6e20b191005f02a732c6fa44ad59`
- Worker OMP session: `019f55ce-6283-7000-be7b-0204c5d16138`
- Result verdict: `result-review-round-2.md` approved; Round 1 P1 is closed.

## Result

Exactly five approved Coordinate paths changed:

- `src/coordinate/cli.py`
- `src/coordinate/workspace_cli.py` (new)
- `tests/test_cli_contract.py`
- `tests/test_workspace_cli.py` (new)
- `tests/fixtures/cli_contract.json`

`coordinate.cli` remains the static facade and calls two registrars at the original
positions. It directly re-exports all 11 moved handlers. `workspace_cli` owns their
registration and service imports and has no backedge to the root. AST comparison proved
all 11 handler bodies identical to the start revision.

The normalized contract remains 21 top-level commands / 75 leaves / 99 nodes. Fixture
SHA changed from `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`
to `652a77d5ee7ab2239b7e2a406560ae21ada4d93b7f7c076fa7c65d6e0aa3f048`.
Rewinding exactly the 11 approved owner strings reproduces the old fixture SHA, proving
all other normalized bytes are unchanged.

Canonical validation passed 37 contract/boundary tests and 1,384 full tests. Four
HOME/DB/COLUMNS contract-generation environments produced identical bytes. No deploy
or multi-host smoke was required because the package changes only static CLI ownership.

## Gate and lifecycle evidence

- `plan.ready`: `eb4606a1-d076-46d9-9a2b-2e9a6659b95e`
- `plan.review_requested`: `56d96194-641e-4672-bebb-d21b21598195`
- reviewer handoff: `3d1adbfe-19fe-4216-902f-d5f2055d5e79`
- `plan.approved`: `fd5d063e-7be0-444e-9f6c-4c86e345b925`
- assignment requested: `4801c793-dcb5-47c4-b806-30f879770991`
- worker handoff: `4bedc79a-7858-4ba9-ad7c-f8d28e2755cd`
- assignment accepted: `8a8ffc8f-4ff8-4ad7-828c-16aa29b4f542`
- closeout requested: `8df39305-c518-4bf5-b127-c228b54e6ec2`
- review approved: `1d960403-8546-4f35-9f19-ad622c75a18d`

Receipt `b2fedbf8-d54c-4586-b3f9-04d3b2e683b9` produced exactly one terminal chain:

- authorized: `95c15e9a-2584-423c-b5b9-8090f296f1ec`
- claimed: `5c11ff10-1b8f-449b-9c4d-4242c0131972`
- applied: `eb6112b5-acfb-4386-bbf3-5bff7c3be633`
- `task.done`: `837c7545-419e-42e8-9220-d0802c78f65a`
- consumed: `8b651614-c0af-4371-a292-be157ccc44d1`
- reconciled closed mirror: `41b56472-e7cb-491e-90e0-7ce6ce4c51cf`

Fingerprint moved from
`5d22dca14de5069c01c6d0515f89a95e51d93d4245722663c224893f6967ea78`
to `5260600d9be9673a3f8446e3bdeed7872644f4e252ce35aaf91414b0319e901c`.
No legacy mark-done, repair path, direct checklist edit, or direct SQLite edit was used.

## Dogfood boundary

This package is semi-dogfood: plan/task/assignment/review/receipt/reconcile used
Coordinate, while plan reviewer and coding worker ran as supervised local OMP sessions
because a usable targeted host execution profile is still absent. Provider JSONL was
the live activity authority. Kimi completed this package without quota failure; future
Kimi quota failures may fall back to GLM with an explicit provider transition record.

Generated reviewer/worker bootstraps again required supplements because they named a
nonexistent OpenSpec source, historical/control-workspace paths, and generic deploy/
progress instructions. Assignment request also created pending live delivery
`30aeb26b-0346-41d5-8706-40eb3e480ff2`; it remains unpumped and uncancelled. These are
retained dogfood backlog items, not reasons to reopen P9-0A2a.
