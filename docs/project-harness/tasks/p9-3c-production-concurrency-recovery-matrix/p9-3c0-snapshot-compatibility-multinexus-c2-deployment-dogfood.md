# P9-3C0 Snapshot/Restore Compatibility — MultiNexus C2 Deployment and Dogfood

Execution date: 2026-07-15 Asia/Shanghai

## Exact revisions

- Reviewed C2 candidate: `952522dcaf4e27aa920045129e41830c42f15009`.
- MultiNexus merge/deployed revision:
  `c5cf5f27a9aafbce828e1ff028c7c7e53d186907`.
- The merge commit has reviewed candidate `952522d` as its second parent. The deployed
  `tests/test_deploy_contract.py` blob is exactly the reviewed blob
  `f6ec0922578a7fffad49343586eb824825ace08f`.
- Coordinate production dependency remains:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.

Before push, merged `main` passed focused `20 passed`, full
`663 passed, 2 skipped, 55 subtests passed`, `compileall`, and `git diff --check`.
Local `HEAD` and `origin/main` then both identified `c5cf5f2`.

## Production pre-deploy gate

- `PRAGMA integrity_check`: `ok`.
- schema: `13`.
- foreign-key violations: `0`.
- capacity sources/policies: exactly `1/8`, all eight policies owned by
  `multinexus.discord.capacity`.
- active/total leases: `0/0`.
- pending/running jobs: `0`.
- `p9-3c*` fixture agents and capacity sources: `0/0`.
- `coordinate.service` and `multinexus-discord-bridge.service`: `active/running`, both
  with `NRestarts=0`.
- deployment snapshot, staging, and authority-backup residue in `/tmp`: none.
- bounded pre-deploy server smoke: pass.

Production MultiNexus was previously at
`aec171f22180cc8b7405762ff79cf93c155cc243`.

## Bounded deployment

`scripts/deploy-server.sh multinexus --host kook-hermes-admin` deployed clean local
`main` without `--allow-dirty`, fault injection, fixture activation, or a manually
requested restore.

The guarded deployment captured and later cleaned its transient capacity snapshot.
All three synchronization surfaces were exact retries:

- roster: no added/removed/updated identities;
- executor catalog: `changed = false`, no added/removed/updated definitions or
  bindings;
- capacity catalog: `changed = false`, no added/removed/updated policies, eight
  unchanged canonical policies.

The accepted path completed normally, so the rollback/live-restore branch was not
entered. No intentional production restore was performed.

Production `/opt/multinexus/VERSION_DEPLOYED` records:

- branch: `main`;
- commit: `c5cf5f27a9aafbce828e1ff028c7c7e53d186907`;
- deployed at: `2026-07-15T03:17:45Z`.

The SHA-256 of `tests/test_deploy_contract.py` matched local and production:

`164dbe2d18ad38dd590b1ee6dff8c802b3e9d85996aa5f7423aa9095c7a0cd0d`.

## Post-deploy gate

- server smoke: pass;
- database integrity/schema/FK violations: `ok` / `13` / `0`;
- capacity sources/policies: one canonical source / eight canonical policies;
- active/total leases: `0/0`;
- pending/running jobs: `0`;
- fixture agents and capacity sources: none;
- both services: `active/running`, `NRestarts=0`;
- deployment snapshot, staging, and authority-backup residue: none;
- bounded journal scan for recovery failures and known breakers: empty.

## Dogfood findings

1. Provider-native JSONL correctly distinguished the outer Claude Sonnet harness from
   the Kimi provider and was useful for live supervision, but it did not prove that a
   worker's claimed amend existed in Git. The operator caught one false clean/amended
   report through `git status --porcelain=v2`, `git diff`, and `git show HEAD:`.
2. Exact-revision review remained sound across divergent documentation history by
   preserving the approved candidate as a merge parent and proving that the deployed
   test-file blob exactly matched the reviewed blob.
3. The production deploy exercised the ordinary v2 capture/cleanup boundary and exact
   retry without broadening authority to live restore or a second source.

## Closeout boundary

C2 deploy-contract coverage is reviewed, merged, pushed, deployed, and accepted.
Package 2 may now plan the isolated fixture assets. A second production capacity source,
fixture activation, production job/lease creation, and live-production restore remain
blocked until their later independently reviewed gates.

`P9_3C0_SNAPSHOT_COMPATIBILITY_MULTINEXUS_C2_DEPLOYED_ACCEPTED`
