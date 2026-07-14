# P9-3A Production Deployment and Sidecar Dogfood

Date: 2026-07-14  
Status: complete; deployed, reviewer-approved, and terminal receipt consumed

## Accepted revisions

- Approved plan SHA-256:
  `d75486b42e8d3315bda488db1129e02c03c0a2c152c04a60cccce917a385d99e`.
- Coordinate `main`:
  `af8461efdf6beb7c47560fe3d17b30f2ac6696ba`.
- MultiNexus `main`:
  `9b1972704713b084867cdb77a6a8b9ff127bc0ac`.
- Final local result review: `result-review-round4.md`, verdict
  `approved_for_integration`.

Both canonical heads equal their upstream heads. Coordinate retains one unrelated
untracked `.qoder/` directory; it is explicitly excluded from deployment artifacts and
was not removed or modified.

## Independent local verification

```text
Coordinate focused: 226 passed, 5 subtests passed
Coordinate full: 9 historical failures, 2314 passed, 493 subtests passed
MultiNexus focused: 38 passed
MultiNexus full: 530 passed, 2 skipped, 1 warning, 36 subtests passed
bash -n, py_compile, and git diff --check: passed
```

The nine Coordinate failures are the unchanged historical eight CLI rewind/hash
contract failures plus one issue-handler AST-body failure.

## Backup and preflight

- Both `coordinate.service` and `multinexus-discord-bridge.service` were active.
- All production jobs were terminal; the pre-v13 DB had no lease table, so active lease
  count was zero by schema boundary.
- Online SQLite backup:
  `/var/lib/coordinate/backups/coord.sqlite3.p9-3a.20260714T024320Z`.
- Backup mode/owner/size: `600 coord:coord 4284416`.
- Backup integrity/schema: `ok` / 12.
- Backup SHA-256:
  `30a5f29befbe5af74fcf86388689ca45b8348720523ff38cf67d5b5ffd79ee99`.

## Producer-before-consumer deployment

Coordinate was deployed first with a full install and service restart.

- `PRAGMA user_version=13`; `PRAGMA integrity_check=ok`.
- Active and total execution leases: zero.
- Deployed and installed `coordinate.executor_capacity` SHA-256 both equal source:
  `23d0aee2e54c0167c0920b30d6e71cf53adcfc012e9053b8f4c443b86892f6cf`.

MultiNexus was then deployed through the guarded authority/snapshot path.

- Capacity source: `multinexus.discord.capacity`, version 1.
- Catalog hash:
  `3c5b31d17424f3dc12b56d5e0d545f5a46b7d212193465d79c874cb82a9a918d`.
- Eight policies exactly cover the eight enabled typed executor bindings; every policy
  has `max_concurrent_jobs=1`.
- Production DB integrity `ok`; schema 13; foreign-key violations 0; active/total leases
  0/0.
- No `/tmp/deploy-multinexus-*`, `/tmp/capacity-snapshot-*`, or
  `/tmp/agent-registry.toml.capacity-backup-*` residue remained.
- Deployed critical file SHA-256 values match local source:
  - `scripts/deploy-server.sh`: `d0b665b6...eb789d0`
  - `tests/test_deploy_contract.py`: `71aa73b6...b9e9b`
  - `multinexus/executor_capacity_authority.py`: `ef0b5d6a...7858a`

Both services were active/running with `NRestarts=0`, the committed registry verifier
passed, Discord proxy reachability passed, and bounded server smoke from the deployment
boundary returned `server smoke OK`.

## Disposable lease dogfood

No production execution lease was created. A consistent online copy of the production
DB was placed at a mode-600 `/tmp` sidecar and the installed Coordinate package executed:

1. reserve one lease for historical P9-2B job
   `request:a7438a23-6346-4952-b46a-406e717ad2c0`;
2. exact replay returned the same lease with `replayed=true`;
3. renewal advanced expiry;
4. release stored terminal reason `p9-3a-sidecar-proof`;
5. sidecar integrity remained `ok`, active lease count returned to zero, and the sidecar
   file was deleted.

Resource key:
`sha256:c922196171417c839b85dcefa78401e03037e0fc822a0502abb57776505670a4`.

The production DB was re-opened read-only after deletion: integrity `ok`, active leases
0, total leases 0.

## Durable review lifecycle

- `assignment.requested`: `c5e13747-2cb7-49c9-9d02-4e82c2139112`.
- `assignment.accepted`: `3fd313e4-4698-4458-8209-e7ab34e0c1c9`.
- `closeout.requested`: `f8746e14-f560-4130-aca3-a8a7b3b73ef1`.
- `review.completed` approved: `945fa31a-5cf0-4c05-af68-3350a080a371`.

The same semantic transitions were replayed through canonical `harnessctl`. No direct
JSON or SQLite edit, repair path, force transition, or legacy mark-done was used.

## Terminal receipt

- Canonical/deployed checklist SHA before receipt:
  `f068f63206c2ba83e56ec1e9504d13bed2ec2819b0778b5a3397f0795b1731b5`.
- Canonical/deployed P9-3A item SHA before receipt:
  `66bb2405f7e05cdf93a799205bfb388b97ae643b8003f301fd4d8d8ce8a5cc1c`.
- Receipt: `da0349ec-6832-4c73-b67e-2a97e477fc46`.
- `completion.authorized`: `02d1ede8-d7ea-48c5-8b96-d319b24f168b`.
- `completion.claimed`: `dc75bf08-3970-479a-becc-63842e16413c`.
- `completion.applied`: `33c677f5-e2eb-47e1-b30f-024dfad2b123`.
- `task.done`: `b6725326-9ebf-4d70-bc96-a03606b5f260`.
- `completion.consumed`: `63648442-fa49-4452-b39e-1ee15207280a`.
- Before/after fingerprint:
  `ffeb5078ca6f0caafc20dd464a6b53a70e79e9b3f8214e15cb31f21091e1d93a`
  -> `f5a4f7851072856dc8b04a0eb629f4b7209554f48355ffec8eed02389a893ef4`.

The first files invocation used a relative harness root and failed before claim with
`harness_fingerprint_unavailable`; no mutation occurred. The retry used the canonical
absolute path, then completed the normal receipt flow. No repair/force/legacy path or
direct JSON/SQLite edit was used.

## Next gate

P9-3B is the next detailed-plan gate. P9-3A intentionally leaves runtime claim,
heartbeat, recovery, and provider observation behavior unchanged.
