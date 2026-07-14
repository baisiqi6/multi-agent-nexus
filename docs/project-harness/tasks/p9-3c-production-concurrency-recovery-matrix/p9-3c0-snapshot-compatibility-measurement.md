# P9-3C0 Snapshot/Restore Multi-Source Compatibility Measurement

> **Read-only audit.** This document records exact code paths, facts, inferences, and the gap introduced by Package 1. It does not authorize implementation, deploy, service restart, DB mutation, or fixture activation.

## Audit targets

| Repository | Path | Exact SHA |
|------------|------|-----------|
| Coordinate source | `/Users/yinxin/projects/coordinate` | `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5` |
| MultiNexus planning worktree | `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c0-snapshot-compatibility-plan` | `aec171f22180cc8b7405762ff79cf93c155cc243` |
| Accepted Package 1 result review | `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-coordinate-package1-result-review.md` | present in base `aec171f`; evidence records initial reviewed revision `777412603053d30480663d120a010b7eaaef4e8f` |
| Accepted Package 1 deployment dogfood | `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-coordinate-package1-deployment-dogfood.md` | present in base `aec171f`; evidence records initial deployed review-document revision `777412603053d30480663d120a010b7eaaef4e8f` |
| Canonical plan | `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-plan.md` | `aec171f` worktree version |

## Coordinate capacity projection state (Package 1 baseline)

### Files audited

- `src/coordinate/executor_capacity.py`
- `src/coordinate/execution_cli.py`
- `src/coordinate/schema.py`
- `src/coordinate/execution_leases.py` (referenced for lease semantics, not fully re-read)
- `tests/test_executor_capacity.py`

### Verified facts

1. **Multi-source sync is allowed.** `sync_capacity_catalog` in `executor_capacity.py:273` accepts a source that owns a partial policy set. Post-sync union coverage is checked at `executor_capacity.py:354-360`.
2. **Ownership is expressed by `source_id`.** `executor_capacity_policies.source_id` is the owner column. Cross-source takeover is rejected at `executor_capacity.py:339-351`.
3. **Active-lease guard is per policy id.** Removing or replacing a policy id referenced by an `active` lease is rejected at `executor_capacity.py:384-408`.
4. **Schema v13 capacity tables.** `schema.py:458-478` creates `executor_capacity_sources` and `executor_capacity_policies`. `executor_capacity_policies.agent_id` is `PRIMARY KEY`; a single agent can only be owned by one source globally.
5. **CLI handlers expose multi-source list.** `handle_runtime_capacity_list` (`execution_cli.py:71`) returns every source and policy.
6. **Snapshot contract version is 1.** `executor_capacity.py:29` defines `SNAPSHOT_CONTRACT_VERSION = 1`.

### Snapshot/restore fail-closed facts

- `capture_capacity_snapshot` (`executor_capacity.py:839`) queries **all** capacity sources at line 855 and rejects any source other than `target_source_id` at line 856-860.
- It also queries **all** policies at line 863 and rejects any policy whose `source_id != target_source_id` at line 864-868.
- It then checks that the captured target policy set exactly equals `_enabled_typed_agent_ids(conn)` at line 949-955.
- `restore_capacity_snapshot` (`executor_capacity.py:968`) rejects any active lease at line 1033-1039, rejects any unexpected capacity source at line 1041-1046, rejects other-source policies at line 1054-1061, validates every field of the current target source and its policies before any `DELETE` (lines 1070-1139), and checks that the snapshot policy set equals current enabled typed bindings at line 1145-1158.

### Inference from those facts

- **Production currently single-source:** Dogfood evidence confirms exactly one capacity source (`multinexus.discord.capacity`) and eight policies. Today, capture/restore works as designed.
- **After Package 2/3 activate a second source:** Any `scripts/deploy-server.sh multinexus` invocation will call `capture_capacity_snapshot` with `--target-source-id multinexus.discord.capacity`. Because a second source (e.g. `p9-3c0-fixture-capacity`) exists, `capture_capacity_snapshot` will raise `CapacityError("unexpected capacity sources in DB: ...")` at line 856-860. The deploy will halt at the snapshot-capture stage.
- **Capture failure does not enter the restore rollback path.** In `deploy-server.sh:487-494`, `capture_capacity_snapshot` failure calls `cleanup_deploy_artifacts` and returns nonzero. `restore_previous_accepted_state` is only invoked when capture succeeds and a later stage (source mutation, parity, roster/executor/capacity sync, committed verifier, or cleanup) fails.
- **If a later stage fails after capture succeeded:** `restore_capacity_snapshot` will then reject the same unexpected source at line 1041-1046. The deploy will fall through to `recovery-failure` / `recovery-cleanup-failure`, leaving staging/backup/snapshot residue and requiring operator intervention.
- **Therefore a second capacity source must not be activated until this compatibility package closes.** This is consistent with the Package 1 review’s stated residual condition, but the present audit pins the exact lines and call chain.

## MultiNexus deploy flow audited

### Files audited

- `scripts/deploy-server.sh`
- `scripts/capacity_snapshot_helper.py`
- `scripts/agent_registry_deploy_verify.py`
- `tests/test_deploy_contract.py`

### Verified facts

1. `deploy-server.sh` calls `capture_capacity_snapshot` at line 271-278 and `restore_capacity_snapshot` at line 332-341.
2. Both calls hard-code `--target-source-id multinexus.discord.capacity` at lines 274 and 337.
3. The helper (`capacity_snapshot_helper.py`) passes the target through to Coordinate functions unchanged.
4. The deploy script backs up `/opt/multinexus/config/agent-registry.toml` (line 478), not the capacity projection DB tables. Capacity recovery relies entirely on the snapshot.
5. Rollback sequence (`restore_previous_accepted_state`, line 344-375) is: restore authority file → remote parity → roster sync → executor sync → restore capacity snapshot → committed verifier.
6. The committed verifier (`agent_registry_deploy_verify.py`) only checks the single canonical capacity source identified by the authority file. It does not inspect other capacity sources or policies.
7. The deploy contract test (`tests/test_deploy_contract.py`) uses a fake `executor_capacity.py` that captures/restores a single target source and ignores other sources. It does not reproduce the Coordinate multi-source rejection.

### Inference

- Because the deploy script only backs up the authority file, the snapshot is the only recovery artifact for capacity tables. If the snapshot rejects multi-source DBs, the deploy cannot survive rollback either.
- The hard-coded target source id means the deploy is only concerned with preserving the canonical source. Any other source must survive the deploy untouched; the snapshot must not restore it, and rollback must not destroy it.

## Canonical registry deploy scope

A normal MultiNexus registry deploy:

- Overwrites `/opt/multinexus/config/agent-registry.toml`.
- Runs `coord-local workspace agent sync` (roster).
- Runs `coord-local runtime executor sync`.
- Runs `coord-local runtime capacity sync` for the canonical source `multinexus.discord.capacity`.
- Does **not** touch fixture executor definitions, fixture bindings, fixture capacity sources, fixture runtime agents, or fixture units unless the authority file is changed to include them (which P9-3C0 forbids).

Therefore the snapshot/restore compatibility package must guarantee:

- Capture: validate the complete current capacity projection, bind a `preserved_state` witness of all non-target sources/policies, and snapshot the target source plus that witness.
- Restore: validate the complete current projection and the witness, reject any drift in non-target rows, restore only the canonical target source, and leave every other capacity source and policy untouched.
- Fail-closed: reject on orphan, unknown, ownership conflict, active lease on any source, current-DB drift, or witness mismatch, with zero mutation.

## Gap summary

| Capability needed | Current Coordinate `a7397b9` | Current MultiNexus `aec171f` |
|---|---|---|
| Multiple capacity sources coexist | Yes (`sync_capacity_catalog`) | Not activated |
| Capture target source while validating full projection and binding a non-target witness | **No** — rejects any other source (`capture_capacity_snapshot` line 856-860) | Calls capture with hard-coded canonical id |
| Restore target source while preserving and witnessing other sources | **No** — rejects any other source (`restore_capacity_snapshot` line 1041-1061) | Calls restore with hard-coded canonical id |
| Rollback preserves other sources | **No** — restore would reject and fail | Rollback path relies on restore |
| Snapshot envelope knows it is multi-source-safe | **No** — contract version 1 has no such marker | N/A |
| Old v1 snapshot recognized and handled | N/A — only v1 exists | N/A |

## Boundaries to preserve

1. **Active lease guard:** Any restore must reject active leases on **any** capacity source, not just the target source, because leases reference `capacity_policy_id` rows that could belong to any source.
2. **Ownership / primary key invariant:** `executor_capacity_policies.agent_id` is globally unique. The snapshot must not create or remove policies for agents owned by other sources.
3. **Executor binding coverage invariant:** After restore, the union of all capacity policies must still cover all enabled typed executor bindings. The snapshot’s captured target policies may legitimately not cover all enabled bindings if other sources cover the rest.
4. **Witness invariant:** Non-target source/policy persistent fields must be exact/value-identical before and after restore (compared via a sorted canonical row projection, not raw SQLite bytes). Any add/remove/update in non-target rows between capture and restore is a concurrent drift and must fail closed.
5. **Atomicity:** Snapshot file write must remain atomic with mode `0600`; restore must remain a single SQLite transaction.
6. **Determinism:** Canonical JSON, sorted keys, sorted policies/sources, and stable timestamps must remain byte-deterministic.
7. **Backward compatibility:** Single-source deployments must see zero behavior change.

## Forbidden actions

- Do not activate a second capacity source before this compatibility package is implemented, reviewed, and deployed.
- Do not edit `executor_capacity.py`, `capacity_snapshot_helper.py`, or `deploy-server.sh` in this planning phase.
- Do not run production deploys, service restarts, or fixture units as part of this task.

## Next step

See `p9-3c0-snapshot-compatibility-plan.md` for the recommended contract, implementation package, test matrix, and deployment/rollback gates.
