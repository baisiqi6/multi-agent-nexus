# P9-3C0 Snapshot/Restore Multi-Source Compatibility Plan

> **Planning document only.** This plan does not authorize code changes, deploy, service restart, DB mutation, or fixture activation. Implementation requires an independent worker branch, exact-revision review, and inert deploy gate.

## Base revisions

- Coordinate: `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`
- MultiNexus: `aec171f22180cc8b7405762ff79cf93c155cc243`

## Background

Package 1 decoupled capacity sources so that a fixture source can own a partial policy set and union coverage can be satisfied across sources. However, `capture_capacity_snapshot` and `restore_capacity_snapshot` in `src/coordinate/executor_capacity.py` still reject any capacity source or policy outside the single target source. `scripts/deploy-server.sh` calls the snapshot helper with the canonical `multinexus.discord.capacity` target before every registry deploy. Once a second capacity source exists, deploy capture will fail closed; if capture succeeds and a later stage fails, the subsequent rollback restore will also fail closed, leaving deploy artifacts in `/tmp`.

This package makes snapshot/restore multi-source-aware while keeping single-source behavior identical.

## Recommended design

### Contract choice: per-source envelope with `preserved_state` witness, versioned, fail-closed

We compared three candidate contracts.

#### Candidate A: snapshot all capacity sources and policies in one envelope

- Capture every source row and every policy row.
- Restore atomically replaces the entire capacity projection.
- **Rejected.** A canonical MultiNexus registry deploy only mutates `multinexus.discord.capacity`; it must not back up and restore fixture sources that it does not own. Restoring all sources would require the deploy script to know every fixture source id, would couple fixture lifecycle to registry deploys, and would silently revert operator-managed fixture state during a rollback. It also expands the blast radius if a restore is triggered.

#### Candidate B: snapshot target source + bind a read-only `preserved_state` witness of all non-target sources/policies

- Capture only `multinexus.discord.capacity` source/policies, but strictly validate the full current projection and include a deterministic witness of every non-target source and policy in the envelope.
- Restore deletes and reinserts only the target source rows, then verifies non-target rows are all persisted fields exact/value-identical via sorted canonical row projection.
- Other sources are neither backed up nor restored; they simply survive, and any drift from the witness is a concurrency failure.
- **Accepted as the minimal safe contract.** It preserves the existing deploy scope (canonical source only), requires no fixture metadata in the deploy script, keeps rollback from touching other sources, and remains fail-closed against concurrent drift.

#### Candidate C: one independent envelope per capacity source, captured/restored separately

- Each source has its own snapshot file and helper invocation.
- **Rejected for the canonical deploy path.** It would require the deploy script to enumerate sources, which violates the principle that a canonical registry deploy only touches the canonical source. It is useful as a future operator tool for fixture-specific backup, but not as the deploy-managed artifact.

### Envelope contract version

- Introduce `SNAPSHOT_CONTRACT_VERSION = 2`.
- v2 envelope top-level schema remains:
  - `snapshot`: object
  - `snapshot_sha256`: hex digest
- Inner snapshot fields:
  - `contract_version`: `2`
  - `target_source_id`: the source being captured/restored
  - `captured_state`: `null` (prior absence) or object with `source` and `policies` for the target source only
  - `preserved_state`: object with sorted `sources` and `policies` arrays containing every non-target capacity source and policy, in canonical form, included in the digest
- Deterministic JSON encoding, sorted keys, sorted arrays, exact timestamps, and `sha256` digest semantics are unchanged.
- `preserved_state` is a **concurrency/ownership witness** only. It is never written back to the DB. Restore uses it to prove non-target rows did not drift between capture and restore.

### Old v1 snapshot handling

| Scenario | Rule |
|---|---|
| v1 snapshot on a single-source DB | Accept and restore exactly as today. |
| v1 snapshot on a multi-source DB | Reject with a clear error: v1 contract predates multi-source awareness and cannot prove it will not silently drop or ignore other sources. |
| v2 snapshot on a single-source DB | Accept and restore; `preserved_state` is empty, so behavior is identical to v1. |
| v2 snapshot on a multi-source DB | Accept capture and restore; restore preserves non-target rows and rejects witness drift. |

Rationale: v1 restore deletes `WHERE source_id = target` and reinserts target rows. In practice that preserves other rows, but the v1 envelope does not declare multi-source safety, does not contain a witness, and v1 capture rejected multi-source DBs. Treating v1 as single-source-only prevents an operator from mistaking an old backup for a multi-source rollback artifact.

### Capture behavior (v2)

1. Validate `target_source_id`.
2. Begin `BEGIN IMMEDIATE`.
3. Read **all** capacity source rows and **all** capacity policy rows.
4. Strictly validate the complete current projection:
   - every source row field shape (`source_id`, `source_version`, `catalog_hash`, `source_path`, `updated_at`);
   - every policy row field shape, source/version/hash alignment, `capacity_policy_id` recompute match, known typed binding (`agent_id` exists in `executor_instance_bindings`), no duplicate `agent_id`, and no orphan policy without a matching source;
   - global union coverage: every enabled typed executor binding is covered by the union of all policies (Package 1 semantics).
5. Separate rows into target set (source id == `target_source_id`) and preserved set (all other sources/policies).
6. Build `captured_state` from the target set exactly as v1 did (or `null` if target source is absent and target policies are empty).
7. Build `preserved_state` by canonicalizing the non-target sources/policies into deterministic sorted arrays (source order by `source_id`; policy order by `agent_id`).
8. Write the v2 envelope atomically with mode `0600`.
9. Commit the read-only transaction.
10. On any exception, rollback and unlink the output file if already written.

### Restore behavior (v1 and v2)

1. Read and validate the envelope file: canonical raw bytes, exact top-level keys, digest, inner `snapshot` object keys.
2. Validate inner `snapshot` fields by contract version:
   - `contract_version` must be `1` or `2`;
   - `target_source_id` must match the caller-provided target;
   - for `contract_version == 1`, exact inner keys must be `{contract_version, target_source_id, captured_state}` (no `preserved_state`);
   - for `contract_version == 2`, exact inner keys must be `{contract_version, target_source_id, captured_state, preserved_state}`;
   - reject unknown versions and any unknown or missing keys.
3. Parse the envelope into an in-memory restore request:
   - `contract_version`, `target_source_id`, `captured_state` as declared;
   - `witness_state`: for v2, the validated `preserved_state` object (`sources` and `policies` arrays); for v1, normalize to `{"sources": [], "policies": []}` so the remainder of the algorithm is identical.
4. Begin `BEGIN IMMEDIATE`.
5. Read **all** current capacity source/policy rows and strictly validate the complete current projection (same checks as capture step 4).
6. Reject any active lease on **any** source (`execution_attempt_leases.status = 'active'`). A lease references a policy id that could belong to any source.
7. If `contract_version == 1` and the current DB contains any capacity source or policy other than the target source, reject.
8. Separate current rows into target set (source id == `target_source_id`) and non-target set.
9. Compare current non-target set field-for-field with `witness_state`. Any add/remove/update must fail closed with zero mutation.
10. Validate `captured_state` semantics against the current target set:
    - if `captured_state` is non-null, the target source row and target policies must be structurally replaceable (the target may differ from the snapshot — that is the rollback scenario);
    - if `captured_state` is null, the target source and target policies may currently exist (because a deploy created them); restore will delete them. Only validate that the current target projection is internally consistent.
11. Construct proposed post-restore union:
    - target policies from `captured_state` (or empty if null);
    - non-target policies from `witness_state` (which equals current non-target rows).
12. Validate Package 1 global invariants on the proposed union:
    - every policy agent belongs to an existing typed binding (enabled or disabled);
    - every enabled typed binding is covered by the union;
    - no target captured policy claims an agent owned by a preserved source.
13. Delete `executor_capacity_policies WHERE source_id = target_source_id`.
14. Delete `executor_capacity_sources WHERE source_id = target_source_id`.
15. If `captured_state` is non-null, reinsert the target source row and policies exactly as captured.
16. Verify:
    - target source/policies match `captured_state` exactly;
    - non-target source/policies still match `witness_state` exactly;
    - no active lease appeared during the transaction (re-check explicitly before commit).
17. Commit.
18. On any exception, rollback.

### Zero-mutation failure proof

- All validation of current projection, active leases, witness mismatch, and proposed-union invariants must occur before any `DELETE`.
- The new v2 code must add tests proving that when any validation fails, target and non-target rows are untouched.
- The new v2 code must add tests proving that when restore succeeds, non-target rows are exact/value-identical before and after (sorted canonical row projection, not raw SQLite bytes).

## Files to modify

### Package C1 — Coordinate implementation and tests

- `src/coordinate/executor_capacity.py`
  - Bump `SNAPSHOT_CONTRACT_VERSION` to `2`.
  - Add `preserved_state` construction and validation helpers.
  - Modify `capture_capacity_snapshot` to validate full projection, build `preserved_state`, and write v2 envelope.
  - Modify `restore_capacity_snapshot` to validate full projection, reject witness drift, restore only target source, and verify post-restore invariants.
  - Keep all existing strict validation, atomic write, mode `0600`, and cleanup behavior.
- `tests/test_executor_capacity.py`
  - Add `CapacitySnapshotMultiSourceTests` covering the matrix below.
  - Keep all existing single-source tests as regression golden tests.

### Package C2 — MultiNexus deploy contract coverage

- `scripts/capacity_snapshot_helper.py`
  - No interface change. The existing `--target-source-id` default is still correct. Only update if Coordinate function signatures change (they do not).
- `scripts/deploy-server.sh`
  - No interface change. Existing calls already pass the canonical target source id.
  - Confirm the capture-failure path is cleanup-only and does not invoke restore (it already is).
- `tests/test_deploy_contract.py`
  - Update the fake `executor_capacity.py` to produce/consume v2 envelopes with `preserved_state` and to validate full projection.
  - Add tests for capture failure (cleanup only), successful deploy with second source, rollback preserving second source, and v1 snapshot fail-closed on multi-source DB.

## Test matrix

### Coordinate unit tests (`CapacitySnapshotMultiSourceTests`)

| Test | Expected result |
|---|---|
| `test_v2_capture_two_sources_exact_bytes_digest_and_witness` | Capture target source succeeds; envelope contains target `captured_state` and non-target `preserved_state`; digest verifies; file mode `0600`. |
| `test_v2_capture_target_absence_with_other_source` | Prior-absence `captured_state=null`; `preserved_state` contains the other source; file mode `0600`. |
| `test_v2_capture_rejects_unknown_binding_in_any_source` | Non-target policy for untyped agent fails before write; snapshot file absent. |
| `test_v2_capture_rejects_orphan_policy_without_source` | Any source absent but policies exist fails before write. |
| `test_v2_capture_rejects_union_coverage_miss` | Enabled typed binding uncovered by any source fails before write. |
| `test_v2_capture_rejects_corrupt_non_target_policy_id` | Bad `capacity_policy_id` in non-target row fails before write. |
| `test_v2_restore_two_sources_preserves_witness` | Restore target to a different state; non-target rows exact/value-identical before/after (sorted canonical row projection); target exact match. |
| `test_v2_restore_prior_absence_deletes_target_only` | Prior-absence restore: current target source/policies exist (deploy created them), restore deletes target only; non-target rows survive and remain exact/value-identical. |
| `test_v2_restore_rejects_active_lease_on_other_source` | Restore fails with zero mutation; all rows unchanged. |
| `test_v2_restore_rejects_active_lease_on_target_source` | Restore fails with zero mutation; all rows unchanged. |
| `test_v2_restore_rejects_witness_source_added` | New non-target source appeared since capture; zero mutation. |
| `test_v2_restore_rejects_witness_source_removed` | Non-target source disappeared since capture; zero mutation. |
| `test_v2_restore_rejects_witness_source_version_changed` | Non-target source version changed; zero mutation. |
| `test_v2_restore_rejects_witness_source_hash_changed` | Non-target source hash changed; zero mutation. |
| `test_v2_restore_rejects_witness_policy_added` | New non-target policy appeared; zero mutation. |
| `test_v2_restore_rejects_witness_policy_removed` | Non-target policy disappeared; zero mutation. |
| `test_v2_restore_rejects_witness_policy_capacity_changed` | Non-target policy `max_concurrent_jobs` changed; zero mutation. |
| `test_v2_restore_rejects_witness_policy_hash_changed` | Non-target policy `catalog_hash` changed; zero mutation. |
| `test_v2_restore_rejects_witness_policy_version_changed` | Non-target policy `source_version` changed; zero mutation. |
| `test_v2_restore_rejects_witness_policy_timestamp_changed` | Non-target policy `created_at`/`updated_at` changed; zero mutation. |
| `test_v2_restore_rejects_target_ownership_takeover_by_preserved` | Snapshot target wants an agent owned by a preserved source; zero mutation. |
| `test_v2_restore_rejects_post_restore_union_coverage_miss` | Restored target + preserved non-target would leave an enabled binding uncovered; zero mutation. |
| `test_v2_restore_rejects_unknown_agent_in_target_snapshot` | Target captured policy targets an untyped binding; zero mutation. |
| `test_v2_restore_rejects_v1_snapshot_on_multi_source_db` | v1 envelope restore fails with contract/multi-source error; zero mutation. |
| `test_v1_restore_rejects_unknown_version` | Envelope with `contract_version = 0` or `3` fails before touching DB. |
| `test_v1_restore_rejects_v2_key_shape` | v1 envelope containing `preserved_state` fails key-shape validation. |
| `test_v2_restore_rejects_v1_key_shape` | v2 envelope missing `preserved_state` fails key-shape validation. |
| `test_v1_restore_still_works_on_single_source_db` | Existing single-source tests continue to pass unchanged. |
| `test_v2_deterministic_bytes_order_and_digest` | Two captures of identical multi-source state produce identical bytes and digest. |
| `test_v2_atomic_write_failure_cleans_output` | Post-write chmod/commit failure removes final output; DB unchanged. |

### MultiNexus deploy contract tests

| Test | Expected result |
|---|---|
| `test_capture_failure_cleanup_only_no_restore` | Inject capture failure; deploy exits at `snapshot-capture`; no `restore-capacity-snapshot` in log; no residue. |
| `test_deploy_with_second_capacity_source_succeeds` | Fake DB has fixture capacity source; deploy succeeds; canonical source synced; fixture source preserved in witness; no residue. |
| `test_deploy_rollback_with_second_capacity_source_preserves_witness` | Inject capacity sync failure after capture; rollback restores canonical source; fixture source exact/value-identical before/after. |
| `test_rollback_with_witness_drift_is_loud_recovery_failure` | Alter non-target row between capture and restore; restore rejects witness drift; deploy enters `recovery-failure`; residue semantics documented. |
| `test_v1_snapshot_downgrade_fails_on_multi_source_db` | Deploy uses old v1-format snapshot artifact with fixture source present; restore rejects and deploy fails closed. |

## Deployment and rollback gates

### Coordinate deployment (Package C1)

1. Merge Package 1 (already done).
2. Implement Package C1 in a Coordinate worker branch.
3. Run Coordinate full test suite plus the new `CapacitySnapshotMultiSourceTests`.
4. Independent exact-revision review.
5. Deploy Coordinate with `scripts/deploy-server.sh coordinate`.
6. Verify production still has exactly one capacity source and that an inert capture succeeds (mode `0600`, digest verifies, DB unchanged). Do **not** run restore against the live production DB.

### MultiNexus deployment (Package C2)

1. Implement Package C2 in a MultiNexus worker branch.
2. Merge MultiNexus changes.
3. Deploy MultiNexus with `scripts/deploy-server.sh multinexus`.
4. Verify capture runs without residue and that the canonical source exact-retry returns `changed=false`.

### Two-source proof (isolated environment)

- Before any production fixture activation, run an isolated two-source proof on a local temp DB or a replicated sidecar DB:
  - seed canonical + fixture sources covering disjoint enabled bindings;
  - capture v2 snapshot;
  - mutate target only;
  - restore;
  - assert exact global state match.
- This proof must close before P9-3C1 activation.

### Inert deploy gate (production still single-source)

- No fixture capacity source, fixture executor source, fixture runtime agent, fixture unit, or fixture job may exist.
- `runtime capacity list` must show exactly one source.
- Production validation is read-only: capture + digest/mode/contents check, exact retry `changed=false`, DB unchanged readback.
- Real v2 restore round-trip is performed only on isolated/local DBs.
- `git diff --check` and deploy contract tests must pass.

## Package dependencies

| Package | What it can do after this package | What remains blocked |
|---|---|---|
| Package 1 (merged) | Multi-source sync logic is live but second source activation remains blocked. | Activating a second capacity source. |
| **Package C1 (Coordinate)** | Safe capture/restore of canonical source while other sources may exist. | Does not itself create or enable fixture sources. |
| **Package C2 (MultiNexus contract tests)** | Deploy contract covers multi-source witness preservation and rollback. | Does not change runtime interface. |
| Package 2 inert assets | Technically can be developed/inert-deployed in parallel, but this route closes the compatibility gate first. | Must not register fixture runtime agents or sync fixture executor/capacity sources until P9-3C1. |
| Package 3 local verification | Can run local/isolated verification using a local DB after C1+C2 close. | Must not activate production fixture sources until P9-3C1. |
| P9-3C1 | Authorized production fixture source activation after isolated two-source proof. | Requires independent operator runbook, exclusive lock, global quiescence, and exact-revision gate. |

## Acceptance criteria

- [ ] Coordinate `executor_capacity.py` supports v2 per-source envelope with `preserved_state` witness.
- [ ] Capture validates the complete current capacity projection and binds a deterministic non-target witness.
- [ ] Restore validates full projection, rejects active leases on any source, rejects witness drift, restores only target source, and verifies post-restore invariants.
- [ ] v1 snapshots still restore on single-source DBs and fail closed on multi-source DBs.
- [ ] All new multi-source unit tests pass.
- [ ] All existing single-source snapshot tests pass unchanged.
- [ ] MultiNexus `deploy-server.sh` and `capacity_snapshot_helper.py` require no breaking interface change.
- [ ] MultiNexus deploy contract tests cover capture-failure cleanup-only, multi-source preservation, witness-drift rollback failure, and v1 fail-closed downgrade.
- [ ] Production inert deploy succeeds with exactly one capacity source and read-only verification only.
- [ ] No production fixture source/agent/unit/job is created by this package.
- [ ] `git diff --check` passes.

## Unresolved risks

1. **Foreign-key ordering during restore.** `executor_capacity_policies` has a foreign key to `executor_capacity_sources(source_id) ON DELETE CASCADE`. In v2 restore we still delete target policies before target source, which is safe. Non-target rows are never deleted.
2. **Active lease on another source blocks canonical rollback.** If a fixture job is running with an active lease on a fixture policy, a canonical MultiNexus registry deploy rollback would fail. This is correct fail-closed behavior, but operators must understand that fixture activation widens the conditions under which deploys/rollbacks can be blocked.
3. **Stale v1 snapshot artifacts.** If an operator keeps an old v1 snapshot and later activates a second source, using that snapshot will fail. Documentation and runbook must require fresh v2 snapshots before any fixture activation.
4. **Witness drift during rollback.** A non-target source changing between capture and restore turns a routine rollback into a loud recovery failure. This is by design, but incident response must know to inspect residue and perform manual reconciliation.
5. **Coordination with Package 2/3.** This package does not create fixture sources. If Package 2 accidentally adds fixture source sync to a deploy path before this package is merged, deploys will break. The bootstrap order must remain: C1 → C2 → Package 2 inert artifacts → Package 3 isolated verification → P9-3C1 activation.

## Prohibited actions

- Do not activate a second capacity source before this package is reviewed, merged, and deployed.
- Do not modify `agents.toml`, canonical executor bindings, canonical capacity policies, or production services as part of this package.
- Do not run fixture jobs, leases, or transient units in production before P9-3C1 authorization.
- Do not perform real v2 restore round-trips against the live production DB; use isolated sidecar DBs.
- Do not bypass `--allow-dirty` deploy checks except for an emergency hotfix with independent approval.

P9_3C0_SNAPSHOT_COMPATIBILITY_PLAN_CORRECTED_FOR_REVIEW
