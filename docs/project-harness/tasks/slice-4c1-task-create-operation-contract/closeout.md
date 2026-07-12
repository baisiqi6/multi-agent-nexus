# Slice 4C1 Durable Closeout

Slice 4C1 is implemented, adversarially reviewed, integrated and deployed. Coordinate
now has one reusable v1 split-operation contract and schema v11 ledger for the
`task create-files` / `task create-record` pair. C2 can adopt the same neutral
target/source model without a second schema.

## Reviewed implementation

- Approved plan SHA-256:
  `e83024a5a125994bd5eee0c9de332d19d939cbf485da3e877c26aa5ba3e8b765`.
- Kimi worker session: `019f5800-43f6-7000-a437-59b6aaf8d701`.
- Initial implementation: `f0fff49`.
- Corrections after three Codex request-changes rounds:
  `52a29f4`, `8c733ae`, `ddec76c`.
- Final reviewed Coordinate head: `1cbb547d7966c83c198125370f46bddc2d8640c9`.
- Result-review evidence: `result-review-round1.md`, `result-review-round2.md`,
  `result-review-round3.md`, and `result-review.md`.
- Provider stayed `kimi-code/kimi-for-coding-highspeed`; GLM fallback was not used.

The review found and closed cross-second retry, incomplete envelope binding,
same-target multi-ledger, persisted-intent, final mirror linkage, timestamp validation,
and pre-existing event collision defects. The final no-ledger path treats any existing
operation-bound event as conflict and rolls back ledger/task state.

## Verification

- Worker full suite: `1662 passed, 407 subtests passed`; nine known Python 3.12
  argparse/AST historical baseline failures remained un-rebaselined.
- Codex final focused set: `124 passed, 15 subtests passed`.
- New-module/focused-test `ruff check`, `compileall`, and `git diff --check`: pass.
- C1 fixture delta differs from pre-C1 only at `task create-files` and
  `task create-record`; rewinding those leaves restores `0c54732c...105d18`.

## Production deploy

- Predeploy DB backup:
  `/var/lib/coordinate/coord.sqlite3.before-s4c1-20260712T205625Z.bak`.
- Backup SHA-256:
  `b031c2fcbfad0cbe488a98d13fe3db249b0417cd328ce878b801bd96ae43b0cb`.
- Backup/source integrity: `ok`; predeploy schema: v10.
- Deployed Coordinate: `1cbb547d7966c83c198125370f46bddc2d8640c9`.
- Deployed MultiNexus done projection: `963b0e95e6a99ecd8ea03e807199aa60f4f4d4fb`.
- Production schema: v11, `split_operations` present with zero production rows,
  integrity `ok`.
- Coordinate PID after final package install/migration: `318285`; both Coordinate and
  `multinexus-discord-bridge` active; `server smoke OK`.

The first code-sync deploy used `--skip-install`. Because Coordinate uses a `src/`
package layout, systemd continued importing the old v10 wheel from `site-packages`, and
the DB correctly remained v10. Codex stopped the service, installed the local deployed
package with `pip --no-deps`, explicitly migrated the backed-up DB with
`PYTHONPATH=/opt/coordinate/src`, and restarted. Deploy/version evidence alone is
therefore not sufficient for schema-bearing Coordinate changes.

## Isolated dogfood

Both local and deployed-server isolated runs proved the full partial-state sequence
without creating a production task:

1. file half wrote an isolated source envelope;
2. record before deploy returned `files_not_deployed` with no DB write;
3. copying the plan/checklist simulated deploy;
4. record created one `record_applied` ledger/event/task transaction;
5. exact retry returned `event_created=false`;
6. deployed item drift returned `fingerprint_drift`;
7. isolated DB integrity was `ok`, schema v11 on server, and temp roots were removed.

## Lifecycle evidence

- Initial pre-checklist-deploy closeout failed closed:
  `d472f173-95b3-4f3f-b646-2148a7c3b002`.
- Successful closeout request: `0d011b93-354f-49d4-8add-145e67c1f46c`.
- Result approval: `16890825-a7f6-4a15-94cc-56268c949fd6`.
- Completion receipt: `c968e093-c5b0-4773-800c-0f17b1abd2dd`.
- Authorized event: `a725ad8e-80a3-41e2-abf9-f14edfc92ad8`.
- Claimed event: `37d7da39-5b9c-4e29-8568-e7b9237c5bf8`.
- Applied event: `e68a827e-6e00-4d5e-8d2e-72e94cf0673d`.
- Fingerprint: `5204d330...a5a5c1` -> `cfd6fc9e...ea90f`.
- Terminal `task.done`: `948ff132-f9a8-40b9-af21-b643619d2fd8`.
- `completion.consumed`: `61ec9d97-3d69-49c1-8fc4-9d4d90480b76`.

`mark-done-record` independently read the deployed done/closed projection and matched
`cfd6fc9e...ea90f` before emitting the terminal pair. The default post-doc-deploy smoke
returned non-zero because its ten-minute log window included already recovered Discord
TLS/proxy tracebacks from before the new bridge PID. Re-running from the new process
start (`2026-07-13 05:03:08 CST`) returned `server smoke OK`.
