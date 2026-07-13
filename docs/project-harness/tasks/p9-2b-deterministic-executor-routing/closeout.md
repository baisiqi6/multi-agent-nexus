# P9-2B Durable Closeout

Date: 2026-07-13  
Status: complete; production routed dogfood accepted and terminal receipt consumed

## Accepted implementation

P9-2B adds deterministic executor routing above the P9-2A identity catalog:

- routed requests require one or more bounded capabilities and are mutually exclusive
  with the legacy exact `--target-agent` path;
- candidate filtering uses the typed executor binding, workspace/host authority,
  registered online state, runner profile, optional definition/host preferences, and
  current Coordinate job load;
- the selected request and decision are canonical, bounded, hash-identified, stored on
  the request event and job, and replayed unchanged through claim/completion events;
- Operator override is explicit and reason-bound; the first production dogfood did not
  use it;
- exact-target behavior and the P9-1 execution-context contract remain compatible.

P9-3 capacity/resource leases and P9-4 provider-neutral observation remain separate
packages. P9-2B is not a general autonomous scheduler.

## Review and integration

- Approved plan SHA-256:
  `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`.
- Ordinary Kimi worker model: `kimi-code/kimi-for-coding` (no `highspeed`).
- Worker session: `019f5c0d-9fb9-7000-a7fe-926c6ab190cc`.
- Worker JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-p9-2b-kimi/2026-07-13T15-17-04-569Z_019f5c0d-9fb9-7000-a7fe-926c6ab190cc.jsonl`.
- Final isolated Coordinate worker head: `41b2769f159a5717bb0cb081a791ac515e339e14`.
- Final isolated MultiNexus review head: `16fdc919817148e22387850564ff0201c131e5bf`.
- Integrated Coordinate `main`: `90783b2c77933287ba163c4bb598f4a862e8b416`.
- Integrated MultiNexus implementation/review head: `6f52630bec15895c2f25ded3d09219adf8be400d`.
- Codex result verdict: approved after six rounds; final evidence is
  `result-review-round6.md`.

## Verification

- Coordinate focused routing/identity/context suites: `189 passed`.
- Coordinate full suite: `2156 passed` plus exactly the same nine historical
  CLI-fixture/AST failures; no new failure was accepted or rebaselined.
- MultiNexus full suite: `503 passed, 2 skipped`.
- `compileall`, `git diff --check`, direct overlong stored-request/candidate rejection
  probes, and immutable replay/cross-link probes passed.

## Production deployment

- Fresh DB backup:
  `/var/backups/coordinate/coord.sqlite3.p9-2b.20260713T153948Z`.
- Backup SHA-256:
  `d26ff95722ad4f88048aa459c591f8c7d9feff3410bb5e989d9eca32e029b407`.
- Backup mode/owner/size: `600 root:root 4136960`; backup/source integrity `ok`;
  schema v12.
- Deployed Coordinate: `90783b2c77933287ba163c4bb598f4a862e8b416`.
- Source, deployed source, and installed module hashes matched for
  `executor_routing.py` (`ffcb6b93...01bba`) and `runtime.py`
  (`081506f3...6d247`).
- Final lifecycle projection deploy: MultiNexus
  `8c34b8c94186bb17b4e2a6554f161d3ce24259ac`.
- Executor catalog source `multinexus.discord`, version 2, catalog hash
  `f4cdf79897755c173e97ddae1dfd88047436039f3447d4d6257105715ba5551d`.
- Final Coordinate PID `1228243`; bridge PID `1272667`; both active/running with
  `NRestarts=0`.
- Production doctor: `projection_ok=true`, errors 0, only the two pre-existing
  superseded unused-receipt warnings. Bounded server smoke passed.

The first Coordinate deploy command returned non-zero only because its default
ten-minute breaker scan included a pre-deploy Discord gateway 503 that had already
resumed. A window beginning at the deployment boundary passed; the same bounded smoke
passed again after the terminal projection deploy.

## Real routed dogfood

The request intentionally omitted `--target-agent` and used
`--route-capability coding --route-definition omp-code` with no Operator override.

- Request event/job:
  `a7438a23-6346-4952-b46a-406e717ad2c0` /
  `request:a7438a23-6346-4952-b46a-406e717ad2c0`.
- Routing request id:
  `sha256:ec19e363e7fe7b0789137e85f91f63aee1016afd7739ce69648f43b07da342a2`.
- Routing decision id:
  `sha256:ed98af88f77164f0be2e743abcf9c3baeb103bce5c064040611aed29432f80cb`.
- Automatically selected instance/profile/definition:
  `mac-omp` / `mac-omp` / `omp-code`.
- Binding id:
  `sha256:04122c692364a1be05de9016004d599b5486dcf1cd7680b387135df37dd15e27`.
- Execution context id:
  `sha256:4fbb26367892f3245b641ae628a846bf883685568cf3f96221904704eb2c8cc1`.
- `job.claimed`: `19406529-5cf9-4ab6-bef1-5ea1b67aaa1d`.
- `job.completed`: `b1ff268f-009a-47b8-bf97-f8b7350653dc` in 4,985 ms.
- Exact result: `P9-2B_ROUTED_SENTINEL_20260713T154315Z`.
- Sent Discord delivery: `a3681e4f-1955-40d8-b281-c949c2371c9d`, platform message
  `discord_bot:1526252822071345192`.

The live agentd log, Coordinate job, event ledger, and sent delivery agree. This very
short OMP invocation returned an empty provider `session_id` and created no new
provider-native JSONL file. The absence is recorded as an observation-contract gap,
not interpreted as worker inactivity; P9-4 owns bounded provider session/log handles.

## Closeout and terminal receipt

- Closeout requested: `c38f7218-9f06-4460-aeef-ef9396203197`.
- Review approved: `b774741b-30cf-45b6-993e-c053c6270223`.
- Receipt: `a2a23a06-f551-404b-b917-9e29278c2809`.
- `completion.authorized`: `d7ed55c2-4bc0-4547-8a58-d3d77eacf65d`.
- `completion.claimed`: `d3221906-6445-4dde-9072-7ae5485c780d`.
- `completion.applied`: `43740292-cb5a-4007-8ab8-98b68a67bc0c`.
- `task.done`: `b608cb3f-5411-41ca-b401-db50afc5cb7e`.
- `completion.consumed`: `e4cac329-8304-4bb1-b211-8571d802121b`.
- Canonical/deployed fingerprint:
  `24304486e30b49ac358c8ca1c6a51a597abcfe5b8281d5a84f6479162903a61d`
  ->
  `e27e49442b330f1e22a8f1fe2ae8ece6153396be61a1b1f88d95174d71fceab8`.

Lifecycle projection was replayed only through `harnessctl`/Coordinate commands.
Source and deployed task items were byte-identical before receipt issuance. No legacy
mark-done, repair path, direct JSON edit, direct SQLite edit, or Operator override was
used.

## Next gate

P9-3 capacity and resource leases is next. It requires refreshed measurement, a new
detailed plan, independent non-Codex plan review, recorded approval of the exact plan
revision, and only then a new worker bootstrap. Ordinary `Kimi for Coding` remains the
preferred coding worker; GLM 5.2 is preferred for plan review when responsive.
