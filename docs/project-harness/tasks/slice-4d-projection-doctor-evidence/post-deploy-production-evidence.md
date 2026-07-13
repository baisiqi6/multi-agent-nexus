# Slice 4D Post-Deploy Production Evidence

## Deployment identity

- Coordinate source/main/origin/deployed:
  `15020c2204e8e05c6304f6ed83a5fed83ad12eae`.
- MultiNexus source/main/origin/deployed at the doctor gate:
  `edde9df2a1396fb5795f7b3b2fa64d1e71a8bcb3`.
- Coordinate runtime import:
  `/opt/coordinate/.venv/lib/python3.12/site-packages/coordinate/__init__.py`.
- Runtime package version: `0.1.0`.
- Code schema version: `11`.
- Production `PRAGMA user_version`: `11`.
- Production `PRAGMA integrity_check`: `ok`.
- Authoritative deployment status path: both managed units active; server smoke OK.
  The active units are `coordinate.service` and
  `multinexus-discord-bridge.service` (plus active `kook-nexus-hermes.service`).

## Backup

- Pre-deploy backup:
  `/var/backups/coordinate/coord-20260713T020019Z.sqlite3`.
- Source DB integrity: `ok`.
- Backup DB integrity: `ok`.

## Production doctor

Command:

```bash
sudo /usr/local/bin/coord-local workspace doctor discord-nexus
```

Raw server artifact:
`/tmp/s4d-production-doctor-after-15020c2.json`.

Result:

```text
doctor_rc=0
projection_ok=true
checklist_valid=true
harnessctl_doctor_ok=true
warnings=[]
errors=0
warnings=2
infos=12
findings=14
```

The two warnings are legitimate expired unused
`receipt_authorization_unused` findings. The twelve infos are eleven terminal receipt
chains plus the expected approved plan-revision proof:

```text
kind=operation_plan_superseded
task_id=slice-4d-projection-doctor-evidence
operation_id=7b393f8a-7d27-4a4e-8a68-44cd5a8923fd
```

The original S4-C2 lifecycle false positive is absent. No whitelist, direct checklist
edit, production DB edit, repair mode, or `--no-projections` bypass was used.

## Dogfood lifecycle observation

Immediately after the production gate, the canonical and deployed
`mvp-checklist.json` files were byte-identical at SHA-256
`9a7d0610f21a053b16e14fce330ef8f03cdad8222473dd88adbb5b7a6cb109c6`.
They still contained the earlier `changes_requested` review projection because remote
Coordinate review mutations are later overwritten by a source deployment unless the
same lifecycle transition is replayed into the canonical source harness first.

Closeout must therefore replay the approved result through source `harnessctl`, commit
and deploy that canonical projection, then use the host-aware receipt protocol. It
must not patch JSON or the control-plane DB directly.
