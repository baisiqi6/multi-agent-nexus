# P9-3C0 Package 2 — Inert Deployment and Dogfood

Execution date: 2026-07-15 Asia/Shanghai

## Exact revisions

- Reviewed candidate:
  `efc75c9610c95b933bed45312bb33c446cd33051`.
- MultiNexus integrated, pushed, and deployed revision:
  `619aa0ec1c0d3a77d1ef0fe7ea03fd8332f8f93d`.
- Coordinate production dependency:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.
- Local `main`, `origin/main`, and `/opt/multinexus/VERSION_DEPLOYED` all identify
  `619aa0e`.

The integration commit contains the candidate's exact eleven fixture-package files.
Merged-main verification passed focused `72 passed, 26 subtests passed`, full
`735 passed, 2 skipped, 81 subtests passed`, `bash -n`, `compileall`, and
`git diff --check`.

## Production pre-deploy gate

- DB integrity/schema/FK: `ok` / `13` / `0`.
- pending/running jobs: `0`.
- active leases: `0`.
- fixture agents/jobs/leases/definitions/bindings/profiles/registry entries: all `0`.
- fixture executor/capacity sources: `0/0`.
- canonical config contains no `p9-3c-fixture-*` identity.
- fixture systemd units and unit files: none.
- `coordinate.service` and `multinexus-discord-bridge.service`: `active/running`, both
  with `NRestarts=0`.
- bounded pre-deploy server smoke: pass.

## Bounded inert deployment

The operator ran:

```bash
scripts/deploy-server.sh multinexus --host kook-hermes-admin
```

The clean-main deployment completed without `--allow-dirty`, fault injection,
fixture catalog sync, fixture unit start, fixture request submission, production
restore, or job/lease creation.

All ordinary production synchronization surfaces were exact retries:

- roster: no added, removed, or updated identities;
- executor catalog: `changed=false`, with no added/removed/updated definitions or
  bindings;
- capacity catalog: `changed=false`, with no added/removed/updated policies and all
  eight canonical policies unchanged.

The server smoke passed after restart. Production
`/opt/multinexus/VERSION_DEPLOYED` records commit `619aa0e` and deployment timestamp
`2026-07-15T07:42:54Z`.

## Deployed file proof

All eleven local and production SHA-256 values matched. Modes were `0755` for the two
bin files and `0644` for every config, runbook, and test file.

| Asset | SHA-256 |
| --- | --- |
| `p9-3c0-fixture.py` | `31a4647ac716e90ecd29cb4e77cec51007d5fb590dd4ab571e41c46dac073015` |
| `p9-3c0-unit.sh` | `13ae9b2f28b47ba87836c24ae70bc24087d5b763d82fedea9f19bc40e8289c91` |
| `agents.fixture.toml` | `ea467f0fa31e379f4bb273bc84b4410b6552c4e0cf77ceb6d0375a8f20ccec0a` |
| `capacity.fixture.v1.toml` | `b3de918630fc7f0cc0126b0f638c8733c2587190d2a0946adb68ffb15bb10a40` |
| `capacity.fixture.v2-empty.toml` | `f33065c74eb4a0d825dde345f04e0b207658b209b002db05764613ef47f20155` |
| `executor.fixture.v1-disabled.toml` | `9560942a1e8dbd921135fb7c8ae3697c408c718e0b3bcd9fca234976e4f9c960` |
| `executor.fixture.v2-enabled.toml` | `32f1d04aaafc90e21443d36ad7ae43782f47fc282d4e21dc0778f45f495d006c` |
| `executor.fixture.v3-disabled.toml` | `220cf01eedbf753c98c51cf3451a3991340126d2dfe67929fbb6cd8319113105` |
| `executor.fixture.v4-empty.toml` | `7dc13eb10aa0673c90af0d7140b01d89d4703fc7f6ed90af7da775fd1979d3eb` |
| `runbook.md` | `599d88b69d47237f4c5405aac1325e0cffe932059ae34795e27c57c1fb3578ea` |
| `test_p9_3c0_fixture_assets.py` | `34c9ab40d3eef99e91cc9a8060a87ee553f51a81675294d9f06b72b10d3fe7a6` |

## Post-deploy zero-activation gate

- server smoke: pass;
- DB integrity/schema/FK: `ok` / `13` / `0`;
- executor/capacity sources and capacity policies: `1/1/8`, unchanged canonical
  ownership;
- pending/running jobs and active leases: `0/0`;
- fixture agents/jobs/leases/definitions/bindings/profiles/registry entries: all `0`;
- fixture executor/capacity sources: `0/0`;
- canonical config fixture identities: none;
- fixture unit files, loaded units, and processes: none;
- both services: `active/running`, `NRestarts=0`;
- deployment staging, snapshot, and authority-backup residue in `/tmp`: none;
- bounded post-deploy warning/error journal scan: empty.

This proves that Package 2 was deployed as inert source assets only. It does not prove
or authorize Package 3 execution or P9-3C1 production activation.

## Dogfood findings

1. Provider-native JSONL was necessary to distinguish outer Claude Sonnet from Kimi
   and to supervise long worker reasoning, but Git objects and exact tests remained the
   result truth. One worker round initially amended without staging; independent Git
   checks caught the false clean-commit claim before review.
2. Read-only reviewer policy must specify the exact existing interpreter. A reviewer
   that improvised a temporary venv was terminated and discarded even though it had
   not changed tracked or production state; the fresh constrained reviewer completed
   successfully.
3. Tests can prove helper fail-closed semantics locally, while live 75-second renewal,
   systemd/cgroup, and isolated Coordinate transitions correctly remain separate
   Package 3 evidence. Inert deployment did not silently widen authorization.

## Closeout boundary

P9-3C0 Package 2 is reviewed, integrated, pushed, deployed, and accepted as inert
fixture assets. Package 3 isolated sidecar execution requires a fresh detailed plan,
independent plan review, worker/operator bootstrap review, and exact cleanup gates.
Production fixture activation remains blocked until P9-3C1.

`P9_3C0_FIXTURE_PACKAGE2_INERT_DEPLOYED_ACCEPTED`
