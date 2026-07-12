# Slice 4B2 Closeout

## Outcome

Slice 4B2 is implemented, reviewed, integrated and deployed. MultiNexus now owns one
tracked secret-free authority, private runtime configs are parity-gated consumers, and
normal deployment performs Coordinate v10 authoritative replace-sync plus independent
read-only committed-state verification before writing the version marker or restarting
the bridge.

## Plan and worker chain

- Approved plan SHA-256:
  `b9cd5c80b8d84c3e011863a7f2b526ab72c2ec083d664c46b76ad00345299811`.
- Plan approval event: `7485d430-0c7b-43da-9fd1-ba69655627f7`.
- Worker handoff event: `482bcc1d-aca7-477d-8f2b-2431381a8297`.
- Worker/provider: Kimi Code Highspeed through Oh-My-Pi; GLM fallback was not used.
- Worker JSONL/session:
  `019f57cd-6a0d-7000-9c74-05083544ceec` at
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-multinexus-s4b2-kimi/2026-07-12T19-28-27-661Z_019f57cd-6a0d-7000-9c74-05083544ceec.jsonl`.
- Worker commit: `1441ad90b21984574414c7f3f1c49a502167bc09`.
- Codex correction/integration commit:
  `ac123966c2c3b39ce9f245789212c1d4111c4948`.

Codex initially requested changes because the verifier could migrate the observed DB,
the deploy committed-state check was not strict about active overrides, and surrounding
whitespace was accepted in Discord IDs. The accepted correction opens SQLite with
`mode=ro` plus `query_only`, passes `--strict-effective`, rejects whitespace and
requires a positive committed registry revision.

## Local verification

- authority/deploy/smoke focused: 39 passing;
- full MultiNexus: 391 passing, 2 skipped;
- focused Coordinate B1 registry/daemon: 83 passing;
- canonical local private-runtime parity: 10 identities;
- authority source/hash: `multinexus.discord` v1 /
  `95bdad3b3d1f0526873e4acd8156ba296d6aa153fb11d5c9e6ddc4482212213b`;
- shell syntax, Python compile and `git diff --check`: pass;
- harness validation: pass with four historical warnings; doctor has only existing
  optional/current misses and the historical `round-2-hardening` plan miss.

## Production rollout

Predeploy:

- schema v10;
- nine `legacy` entries, no authoritative source row;
- Coordinate PID `4009950`, active since `Mon 2026-07-13 03:07:51 CST`;
- production backup:
  `/var/lib/coordinate/coord.sqlite3.before-s4b2-20260712T194617Z.bak`;
- backup SHA-256:
  `bc02f5507ceb46b241bd4a9df2f6d73ab1d8b5cd51b6b2a860253013b9904b09`;
- backup `PRAGMA integrity_check`: `ok`.

Deployed MultiNexus `ac123966c2c3b39ce9f245789212c1d4111c4948` with the
reviewed deployment script. Sync result:

- source `multinexus.discord` v1 and canonical hash above;
- revision `1`;
- added `pad-jarvis`;
- updated the nine migrated identities;
- removed/skipped/shadowed: none.

Postdeploy committed state:

- 10 authoritative, 0 legacy, 0 active override;
- compatibility projection count 10;
- strict registry verifier passes;
- `/opt/multinexus/VERSION_DEPLOYED` records `ac12396`;
- Coordinate PID/start time remained exactly `4009950` / `03:07:51 CST`;
- bridge restarted as PID `4186459` and all configured managed identities, including
  `pad-jarvis`, reached ready state.

The deploy command's first default ten-minute smoke returned non-zero because its log
window included a recovered predeploy Discord TLS reset and a transient startup reset.
Registry/source/PID gates had already passed. A stable-window rerun from
`2026-07-13 03:46:35` passed `server smoke OK`; no rollback was needed. This is retained
as dogfood evidence rather than misreported as a registry failure.

## Isolated same-process removal proof

On the server, deployed Coordinate code created a new empty isolated v10 DB and a
single non-networked `CoordinatorDaemon` object in PID `3446`:

- v1 source `s4b2.sidecar` authorized synthetic `alpha` and `beta`;
- v2 removed `beta`; the same daemon object immediately resolved only `alpha`;
- same-version/different-hash was rejected with rc=1;
- rollback to v1 was rejected with rc=1;
- state remained unchanged after both rejected attempts;
- final source version/revision were 2/2 with one authoritative row;
- `PRAGMA integrity_check` was `ok`;
- `/var/lib/coordinate/s4b2-sidecar/registry-uxlo2gvy` was deleted and cleanup was
  independently verified.

The sidecar never connected to Discord, read a token, touched the production DB or left
a production workspace/source row.

## Residual boundary

S4-B is closed. S4-D will later diagnose stale projections and partial repair evidence;
this package deliberately adds no automatic source takeover, rollback or repair. The
next Slice 4 package is S4-C bound split operations.
