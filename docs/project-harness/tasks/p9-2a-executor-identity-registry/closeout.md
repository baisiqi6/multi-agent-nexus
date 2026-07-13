# P9-2A Durable Closeout

Date: 2026-07-13  
Status: complete; production accepted and terminal receipt consumed

## Accepted implementation

P9-2A establishes durable executor identity without implementing P9-2B routing:

- the source-controlled registry remains authority for executor definitions and
  concrete instance bindings;
- Coordinate schema v12 stores versioned catalog projections and snapshots one exact
  binding into typed jobs before durable submission;
- claim and MultiNexus provider dispatch validate that immutable binding before
  status/attempt mutation or provider invocation;
- legacy exact targets retain the explicitly bounded null-binding path;
- P9-2B candidate filtering, health, leases, scheduling, and rerouting remain out of
  scope and are the next detailed-plan package.

## Integration and tests

- Coordinate implementation/reviewer commits: `2a3a819`, `4463572`, final recurrence
  fix `eec9b233f6c797c73aec9d535fa723e037a0af65`.
- MultiNexus implementation/reviewer commits: `4a38520`, `b192b27`, deployment gate
  `3939059`, repair artifact `aaed0de`, approval evidence `6e980be`.
- Coordinate full verification: 1998 passed, 461 subtests, plus the same nine
  baseline-identical historical CLI/AST failures; focused recurrence suite 250 passed,
  43 subtests.
- MultiNexus final full verification: 503 passed, 2 skipped, 36 subtests.
- `compileall` and `git diff --check` passed in both repositories.

## Deployment and real typed dogfood

- Deployed Coordinate commit: `eec9b233f6c797c73aec9d535fa723e037a0af65`.
- Source, deployed source, and installed `coordinate/onboarding.py` SHA-256:
  `8909382b7483bc85e0445efc4f223961b0ca28a05377c55709faa2a01a0e9c63`.
- Production schema: v12.
- Executor source: `multinexus.discord`, version 2, catalog hash
  `f4cdf79897755c173e97ddae1dfd88047436039f3447d4d6257105715ba5551d`.
- Real job: `request:64f42ca6-3b8b-4f78-a56c-c417c6ddeebd`, status `done`, agent/profile
  `mac-omp`.
- Binding id:
  `sha256:04122c692364a1be05de9016004d599b5486dcf1cd7680b387135df37dd15e27`.
- Execution context id:
  `sha256:0fad70b494dd51081147ffed340d5e3157d6981a5723831949d401030c86869f`.
- Exact provider result: `P9-2A_TYPED_SENTINEL_20260713T074839Z`.
- Completed event: `e6926827-384a-47f2-99f5-b1347f614b7b`.
- Sent Discord delivery: `0e792036-e220-4714-a342-4cd7f3815af8`, platform message
  `discord_bot:1526133399553577041`.

## Deployment finding and deterministic repair

The final production doctor exposed a compatibility plan revision that replaced the
task payload and erased immutable `split_operation` metadata. Coordinate `eec9b23`
now preserves the exact reserved six-key metadata and payload phase for future split-
bound revisions, while leaving ordinary legacy tasks unchanged.

The first disposable-copy rehearsal correctly found the initial repair addendum was
incomplete: after metadata restoration, doctor exposed the second erased field as
`phase: mirror=None deployed='ready'`. Production remained untouched. A separately
reviewed amendment added dual-source phase validation and a conditional two-field
repair.

- Fresh backup:
  `/var/backups/coordinate/coord.sqlite3.p9-2a-mirror-fix.20260713T093705Z`;
- backup SHA-256:
  `5807973f138b37c3ec7dd674d2310ccf50fa7727eaf35ca35b743f2718482580`;
- mode/owner/size: `600 root:root 4112384`;
- backup integrity/schema: `ok` / v12;
- exact reviewed script SHA-256:
  `75423566ddb612bef91a355d8e5b7233ae1d99b61d856441b9798ff6eaa307e1`;
- repair event: `594892d1-1783-546d-b842-652990545826`;
- payload SHA-256:
  `ff1858641fff5e19026a501adaae901187bfa3e12fd2fcf73d9d6f55e9ab661e` ->
  `1827e922f4cc7ebed52618b5eb7e542ce82e27ae4f88f9d8b5532d331890ec0e`;
- repaired fields: `phase`, `split_operation`;
- exact retry: `already_repaired`, same event id and original before hash, zero writes;
- every non-payload task column remained identical;
- production integrity: `ok`;
- production doctor: `projection_ok=true`, errors 0, only the two pre-existing
  `receipt_authorization_unused` warnings.

## Runtime stability and closeout review

- Coordinate and `multinexus-discord-bridge` stayed active with `NRestarts=0` across
  repeated observations.
- Full server smoke passed after repair, including proxy and registry authority checks.
- No new traceback, import, SQLite lock, or integrity breaker appeared in the bounded
  post-deploy logs.
- Closeout requested event: `e3c17b26-6c48-4813-92bb-f233eeb40872`.
- Final closeout approval event: `ca0bfd31-bdc5-4e80-b59d-5a91dd53fe59`.

## Terminal host-aware receipt

- Receipt: `56addb44-f72b-4e31-bdab-a230c59fe9d6`.
- `completion.authorized`: `62e571e1-3274-4097-a539-0def01d9daa4`.
- `completion.claimed`: `6b72f237-da1c-4281-9ad7-7e758007778f`.
- `completion.applied`: `e2ca772f-d69c-4577-b6ea-082896843407`.
- `task.done`: `85fa6c75-eaa3-48a8-9559-9576ff8eb13a`.
- `completion.consumed`: `2f0f6700-0523-4271-a72d-c3f89e62ce9f`.
- Source/deployed checklist fingerprint:
  `03b1823acb41015c22fed3f639774d0d735d2ebcb3d145db1d895a67f530f880` ->
  `1bf05285318a2aab26659fd0bac5587c25adc8b9b96fb28f41f78f32294d1667`.
- Deployed verification observed task `done`, workflow `closed`, and the exact applied
  fingerprint before recording `task.done`.
- The first local invocation omitted the explicit actor and failed closed before claim
  because the default `operator` did not match authorized actor `codex-operator`; the
  same receipt then completed normally with the explicit actor and no repair bypass.
- Final production doctor: `projection_ok=true`, errors 0, warnings 2 (the same
  superseded unused historical receipts), including a terminal info finding for this
  consumed receipt.

## Rollback

Code rollback redeploys Coordinate `44635726`. Data rollback uses the fresh backup
above only after stopping writers and assessing events created after the backup; the
repair itself was atomic and accepted, so no restore is currently required. The data
change adds two payload members and one audit event and requires no schema rollback.

## Next gate

P9-2B is now the next authorized planning package. It requires a fresh detailed plan
and independent plan review before worker dispatch. Coding worker preference is
ordinary `Kimi for Coding`
(`kimi-code/kimi-for-coding`, without `highspeed`); use the agreed fallback chain only
when that model is unavailable.
