# P9-3B Production Deployment and Dogfood Evidence

Date: 2026-07-14  
Status: deployed, reviewer-approved, and terminally closed

## Accepted revisions

- Coordinate main/upstream/deployed: `3eaa7bfdeb0f660da46bd7fe6003231822c9658c`.
- MultiNexus main/upstream/deployed: `6bc1adfd30fc46911e320f52506b9d50f0032663`.
- MultiNexus implementation commit: `0348c8b`.
- Result review: `result-review.md`, approved for durable closeout.

## Synchronized maintenance window

The preflight found both services active, schema 13, DB integrity `ok`, 171 terminal
jobs, no nonterminal job, and zero active/total attempt leases. Production was still
running Coordinate `af8461e` plus MultiNexus `b898605`; the latter did not contain the
P9-3B heartbeat consumer, so an ordinary producer-before-consumer rolling restart would
have created an unsafe compatibility window.

The Operator therefore:

1. stopped `multinexus-discord-bridge` and `coordinate` together;
2. verified both were inactive and rechecked zero nonterminal jobs/active leases;
3. created and verified a fresh SQLite backup;
4. deployed/installed both repositories with `--no-restart --no-smoke`;
5. verified exact source/deployed/installed hashes, DB state, and zero residue while
   both services remained stopped;
6. started both services together and ran bounded smoke plus post-start checks.

No job or execution lease was created during this deployment. The full production
concurrency/crash/recovery matrix remains P9-3C.

## Backup and rollback boundary

- Backup:
  `/var/lib/coordinate/backups/coord.sqlite3.p9-3b.20260714T184701Z`.
- Mode/owner/size: `600`, `coord:coord`, `4366336` bytes.
- SHA-256:
  `5a6e3faae9593ad8f152d1d15034174a78280b7ee4f20ab83e5ba7c89b5ddf3b`.
- Integrity/schema/active leases: `ok` / 13 / 0.

The rollback artifact remains available. No rollback was required. MultiNexus guarded
authority/capacity deployment captured and cleaned its per-run snapshot/backup/staging
artifacts; the locally accepted rollback matrix remains the executable rollback proof.
Production data was not hand-edited.

## Deployed identity and integrity

- Coordinate source and installed hashes match:
  - `runtime_lease.py`: `fcd854cf...a5dd6ed1`;
  - `lease_envelope.py`: `3c96a67c...2dd047f5`.
- MultiNexus deployed hashes match local main:
  - `agentd/worker.py`: `fe2e25c9...14d59363`;
  - `adapters/utils.py`: `804d15ba...9ab46f5`;
  - `adapters/jarvis.py`: `0b7be81b...55df3d7`.
- Final DB: integrity `ok`, schema 13, foreign-key violations 0,
  `execution_attempt_leases` active/total `0/0`, nonterminal jobs 0.
- Registry, executor catalog, and capacity policy syncs were unchanged and exact.
- `/tmp/deploy-*`, capacity snapshot, and authority backup residue count: 0.

## Service smoke

- `coordinate.service`: active/running, `NRestarts=0`.
- `multinexus-discord-bridge.service`: active/running, `NRestarts=0`.
- `scripts/server-smoke.sh`: `server smoke OK`.
- Deployed imports for strict lease envelope, claim authority, heartbeat parser, and
  process-group cleanup succeeded.
- Installed CLI surface is
  `coordinate runtime job lease renew ...`; `runtime job lease-renew` is not the
  implemented spelling.
- Error-priority journal entries in the deployment window: none.

## Dogfood findings

Two probes failed safely without mutation:

1. The first backup verifier queried the guessed table name `execution_leases`; the
   real v13 table is `execution_attempt_leases`. Backup integrity/schema checks had
   already passed, services remained stopped, and the corrected query proved active 0.
2. The first CLI surface probe used plan prose `lease-renew`; argparse rejected it
   before mutation. The deployed nested `lease renew` help surface then passed.

These failures are retained as evidence that Operator probes must derive live schema
and CLI facts rather than treating plan wording as executable syntax.

## Control-plane review lifecycle

- `assignment.requested`: `8b715d40-1c93-4441-99fa-e24cb3b8dacf`.
- `assignment.accepted`: `b44d1672-3559-4e93-9350-fb1da2c7c0c3`.
- `closeout.requested`: `e500773a-842b-4905-acd1-d1d6b62038f5`.
- `review.completed` approved: `3e93a81f-9930-4587-8ac3-1f1b924725a8`.

The commands used the canonical `discord-nexus` workspace and its registered
`harnessctl`; source checklist transitions were produced by the mutation service, not
by direct JSON editing.

## Host-aware completion receipt

- Receipt: `8f36d34c-0485-4cef-be54-8eaad08404e2`.
- `completion.authorized`: `bf3b551a-3b21-48c4-a68d-65133c838d8b`.
- `completion.claimed`: `dc45826a-195b-41c5-bf65-14dcfb581140`.
- `completion.applied`: `8486e57f-a87a-4f4d-9f4e-486c0606fe3a`.
- `task.done`: `de7a0b5b-d488-4800-8cc0-fc6dd4547add`.
- `completion.consumed`: `97c546a4-44ef-4ce7-bf3c-74cec2427ed0`.
- Fingerprint:
  `07bf20b961012279dbe225684ca8577e22178b7948547e6754f0c545bbdb75ee`
  -> `e407e9608d602f88716fc4da8fbbbf3adc97ad91ea74a9962877f01933beed40`.
- Receipt-applied checklist commit: `82fe51128ec6be87e39c1c371913dd748df47f72`.
- Canonical/deployed checklist SHA-256 before record:
  `88b9dcb948358a20e1d6e4a88022507f953ffefbe5f1fdfcba04b46b38a120d1`.

The first receipt was accidentally issued through the local `mac.sh` control plane;
the remote preflight returned `unknown_receipt` and canonical files remained unchanged.
The normal path was rerun with production `coord-ssh`, then online claim, canonical
commit/push/deploy, byte-equality verification, record, and consumption. No repair,
force, legacy completion path, direct JSON edit, or SQLite write was used.

The production receipt event reports `review_evidence.not_applicable` because the
earlier `review.completed` event lives in the local lifecycle plane rather than the
production event store. This did not bypass the gate: production authorized only after
the deployed canonical projection was `review_approved`, and the exact local review
event plus approval summary remain recorded above. Event-plane mirroring is retained as
an observation for later projection/control-plane hardening, not silently represented
as an end-to-end review event.
