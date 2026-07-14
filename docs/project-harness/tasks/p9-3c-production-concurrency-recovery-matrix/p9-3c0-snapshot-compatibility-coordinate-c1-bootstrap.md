# P9-3C0 Snapshot/Restore Multi-Source Compatibility — Coordinate C1 Bootstrap

> **Implementation bootstrap only.** Before an independent reviewer approves this document at an exact revision, it authorizes **no** code changes, deploy, service restart, DB mutation, fixture activation, schema/migration/CLI/doc/config changes, or push/merge. After independent approval, it authorizes changes **only** to the two allowlisted files inside an isolated Coordinate worktree, producing **one local commit**. Push, merge, deploy, SSH, production DB mutation, fixture activation, service restart, schema/migration/CLI/doc/config changes, and any modification outside the allowlist remain unauthorized.

## 1. Worker identity and authorization

- **Role**: P9-3C0 snapshot/restore compatibility Coordinate C1 implementation worker.
- **Scope**: Implement v2 per-source snapshot envelope with `preserved_state` witness in Coordinate, and the matching unit tests, in a dedicated Coordinate worktree.
- **Authorization chain**:
  - Measurement: `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-snapshot-compatibility-measurement.md`
  - Approved plan: `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-snapshot-compatibility-plan.md`
  - Independent plan review: `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-snapshot-compatibility-plan-review.md`
  - This bootstrap: `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-snapshot-compatibility-coordinate-c1-bootstrap.md`
- **Exact base revisions**:
  - MultiNexus (planning repo): `061746b3d6c7e232ee4afe936136b3d2a9a4460d`
  - Coordinate (implementation repo): `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`
- **Mandatory gate**: This bootstrap **must be independently reviewed at exact revision** before the coding worker begins. The reviewer must confirm every section below is internally consistent and matches the approved plan/review. Approval only authorizes the two allowlisted files in the isolated Coordinate worktree; nothing else.

## 2. Coding branch and worktree

- **Coordinate worker branch**: `agents/mac-claude/p9-3c0-snapshot-compatibility-coordinate-c1`
- **Coordinate worktree**: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3c0-snapshot-compatibility-c1`
- **Main checkout preconditions** (the operator must satisfy these before creating the branch/worktree; the coding worker does not create them):
  - The Coordinate main checkout HEAD must be exactly `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`.
  - There must be no tracked-file modifications, staged changes, or merge/rebase conflicts.
  - The user-owned `.qoder/` directory may remain untracked; it must **not** be read, copied, deleted, staged, or touched.
- **Creation steps** (performed by the operator, not by the coding worker):
  1. In the Coordinate repository at `/Users/yinxin/projects/coordinate`, verify HEAD is `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5` and there are no tracked modifications or conflicts.
  2. `git branch agents/mac-claude/p9-3c0-snapshot-compatibility-coordinate-c1 a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`
  3. `git worktree add /Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3c0-snapshot-compatibility-c1 agents/mac-claude/p9-3c0-snapshot-compatibility-coordinate-c1`
- **Forbidden workspace**: The main Coordinate checkout's user-owned `.qoder/` directory, and any file under it, is **strictly off limits** for read, copy, delete, stage, or touch. The worker must never operate inside or reference `.qoder/`.

## 3. Allowed files

- `src/coordinate/executor_capacity.py` — implementation.
- `tests/test_executor_capacity.py` — tests.

Any change outside these two files **must stop the worker immediately** and return to Codex for bootstrap re-review. Specifically forbidden without explicit re-authorization:
- schema or migration files;
- CLI (`execution_cli.py`) or helper scripts;
- `deploy-server.sh`, `capacity_snapshot_helper.py`, or `agent_registry_deploy_verify.py`;
- any `agents.toml`, config, doc, runbook, or MultiNexus planning file;
- any file in the main Coordinate checkout `.qoder/` directory.

## 4. v2 capture contract — precise implementation semantics

`SNAPSHOT_CONTRACT_VERSION` becomes `2`.

The v2 envelope is:

```json
{
  "snapshot": {
    "contract_version": 2,
    "target_source_id": "<target-source-id>",
    "captured_state": null | { "source": {...}, "policies": [...] },
    "preserved_state": { "sources": [...], "policies": [...] }
  },
  "snapshot_sha256": "<hex-digest-of-snapshot-object>"
}
```

Capture steps, in order:

1. Validate `target_source_id` with the existing bounded-label validator.
2. Begin `BEGIN IMMEDIATE`.
3. Read **all** capacity source rows and **all** capacity policy rows.
4. Strictly validate the complete current projection (see section 7).
5. Separate rows:
   - target source and its policies (`source_id == target_source_id`);
   - preserved sources and policies (every other `source_id`).
6. Build `captured_state` from the target set exactly as v1 did (or `null` if target source absent and target policies empty). The structure must remain `{source, policies}` when non-null.
7. Build `preserved_state` by canonicalizing non-target sources/policies into deterministic sorted arrays:
   - `sources` sorted by `source_id` in **strictly increasing** order, no duplicates;
   - `policies` sorted by `agent_id` in **strictly increasing** order, no duplicates;
   - each source object contains exactly `source_id`, `source_version`, `catalog_hash`, `source_path`, `updated_at`;
   - each policy object contains exactly `agent_id`, `source_id`, `source_version`, `catalog_hash`, `capacity_policy_id`, `max_concurrent_jobs`, `created_at`, `updated_at`.
8. Write the v2 envelope atomically with mode `0600` using the existing `_atomic_write_snapshot` pattern.
9. Commit the read-only transaction.
10. On any exception, rollback and unlink the output file if already written.

`preserved_state` is a **witness only**. It is **never** restored or written back to the DB. It proves non-target rows did not drift between capture and restore.

## 5. v1/v2 restore parser — precise implementation semantics

Restore begins by reading canonical raw bytes and validating them before any DB mutation. Reuse existing helpers; do not reinvent encoding logic.

Top-level envelope requirements:
- Raw bytes must equal `_snapshot_canonical_bytes(envelope)`.
- Exact top-level keys: `{"snapshot", "snapshot_sha256"}`.
- `snapshot_sha256` must be accepted by `_validate_snapshot_hash(envelope["snapshot_sha256"], "snapshot_sha256")` and must equal `sha256(_snapshot_canonical_bytes(snapshot)).hexdigest()`.

Inner `snapshot` requirements by version:
- `contract_version` must be `1` or `2`.
- `target_source_id` must equal the caller-provided target.
- For `contract_version == 1`, exact inner keys: `{"contract_version", "target_source_id", "captured_state"}`. Presence of `preserved_state` is a key-shape mismatch.
- For `contract_version == 2`, exact inner keys: `{"contract_version", "target_source_id", "captured_state", "preserved_state"}`. Absence of `preserved_state` is a key-shape mismatch.
- Reject any unknown version or any unknown/missing key **before** any DB mutation.

Normalize `witness_state`:
- For v1, set `witness_state = {"sources": [], "policies": []}`.
- For v2, `witness_state` is the validated `preserved_state` object (must contain exact keys `sources` and `policies`, both lists).

Then continue with the unified restore algorithm below.

## 6. Restore flow and ordering

1. Read file → canonical raw bytes check → top-level key/digest validation.
2. Version-specific inner key validation → normalize `witness_state`.
3. `_strict_validate_captured_state(captured_state, target_source_id)`.
4. Begin `BEGIN IMMEDIATE`.
5. Read all current capacity source/policy rows and run the same full-projection strict validation used at capture (section 7).
6. Reject any active lease on **any** source (`execution_attempt_leases.status = 'active'`).
7. v1 gate: if `contract_version == 1` and current DB contains any capacity source or policy other than `target_source_id`, reject with a clear contract/multi-source error.
8. Separate current rows into target set and non-target set.
9. Witness equality: compare current non-target set field-for-field with `witness_state`. Any add/remove/update must fail closed with zero mutation. Comparison must use a sorted canonical row projection, not raw SQLite bytes.
10. Validate `captured_state` semantics against current target set:
    - Non-null: target source row and policies must be structurally replaceable (target may differ from snapshot — that is the rollback scenario).
    - Null: target source and target policies may currently exist; restore will delete them. Only validate internal consistency of the current target projection.
11. Construct proposed post-restore union:
    - target policies from `captured_state` (or empty if null);
    - non-target policies from `witness_state` (which equals current non-target rows).
12. Validate Package 1 global invariants on the proposed union:
    - every policy `agent_id` belongs to a typed binding (`_all_typed_agent_ids`), enabled or disabled;
    - every enabled typed binding (`_enabled_typed_agent_ids`) is covered by the union;
    - no target captured policy claims an `agent_id` owned by a preserved source.
13. Delete `executor_capacity_policies WHERE source_id = target_source_id`.
14. Delete `executor_capacity_sources WHERE source_id = target_source_id`.
15. If `captured_state` is non-null, reinsert target source row and policies exactly as captured.
16. Verify:
    - target source/policies match `captured_state` exactly (or target absent when null);
    - non-target source/policies still match `witness_state` exactly;
    - no active lease appeared during the transaction (re-check explicitly before commit).
17. Commit.
18. On any exception, rollback.

All validation of current projection, active leases, witness mismatch, version/key shape, and proposed-union invariants must occur **before** any `DELETE`.

## 7. Full projection strict validation

Extend the existing C5-3 strict current validation to the full multi-source projection. Do not present it as a new recovery rule.

For every source row:
- exact fields `{source_id, source_version, catalog_hash, source_path, updated_at}`;
- bounded label for `source_id`;
- non-negative integer `source_version`;
- 64 lowercase hex `catalog_hash`;
- `source_path` is `None` or a string with no Unicode Cc controls and length ≤ 4096;
- canonical UTC Z timestamp for `updated_at`.

For every policy row:
- exact fields `{agent_id, source_id, source_version, catalog_hash, capacity_policy_id, max_concurrent_jobs, created_at, updated_at}`;
- bounded labels for `agent_id` and `source_id`;
- `source_version` equals its source's `source_version`;
- `catalog_hash` equals its source's `catalog_hash`;
- `capacity_policy_id` equals `compute_capacity_policy_id(...)` recomputed from its fields;
- `max_concurrent_jobs` in `1..32`;
- canonical UTC Z timestamps for `created_at` and `updated_at`.

Because `executor_capacity_policies.agent_id` is a global primary key, a single agent cannot be owned by two sources. Full-projection validation must be fail-closed on ownership conflicts: if two policies share the same `agent_id` with different `source_id` values, or if a policy's `source_id` does not match any existing source row, reject before any mutation.

Global projection checks:
- every policy `agent_id` exists in `_all_typed_agent_ids`;
- every enabled typed binding (`_enabled_typed_agent_ids`) is covered by the union of all policies;
- no orphan policies (policy exists whose `source_id` has no matching source row).

## 8. `preserved_state` witness rule

`preserved_state` is **only a witness**. It must never be inserted, updated, or deleted in the DB. Any drift in non-target rows between capture and restore must produce a **loud fail with zero write**. The restore must leave every non-target source and policy untouched.

## 9. Required test matrix

Add a new `CapacitySnapshotMultiSourceTests` class in `tests/test_executor_capacity.py`. The existing `CapacitySnapshotTests` must remain as regression golden tests, with their capture golden expectations updated to v2 (see section 10).

| Test | Expected result |
|---|---|
| `test_v2_capture_single_source_exact_bytes_digest_and_empty_witness` | v2 envelope with empty `preserved_state`; digest verifies via `_snapshot_canonical_bytes`/`_validate_snapshot_hash`; mode `0600`; DB unchanged. |
| `test_v2_capture_two_sources_exact_bytes_digest_and_witness` | Target `captured_state` + non-target `preserved_state`; digest verifies; mode `0600`. |
| `test_v2_capture_target_absence_with_other_source_zero_policies` | `captured_state=null`; `preserved_state` contains a source with zero policies; mode `0600`. |
| `test_v2_capture_target_absence_with_other_source_nonzero_policies` | `captured_state=null`; `preserved_state` contains source + policies; mode `0600`. |
| `test_v2_capture_rejects_unknown_binding_in_target` | Target policy for untyped agent fails before write; snapshot file absent. |
| `test_v2_capture_rejects_unknown_binding_in_any_source` | Non-target policy for untyped agent fails before write; snapshot file absent. |
| `test_v2_capture_rejects_orphan_policy_without_source` | Any source absent but policies exist fails before write. |
| `test_v2_capture_rejects_union_coverage_miss` | Enabled typed binding uncovered by any source fails before write. |
| `test_v2_capture_rejects_corrupt_non_target_policy_id` | Bad `capacity_policy_id` in non-target row fails before write. |
| `test_v2_restore_two_sources_preserves_witness` | Restore target to a different state; non-target rows exact/value-identical before/after; target exact match. |
| `test_v2_restore_prior_absence_deletes_target_only` | Prior-absence restore: current target source/policies exist, restore deletes target only; non-target rows survive and remain exact/value-identical. |
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
| `test_v1_restore_succeeds_on_single_source_db` | A handcrafted v1 single-source snapshot restores correctly on a single-source DB. |
| `test_v2_deterministic_bytes_order_and_digest` | Two captures of identical multi-source state produce identical bytes and digest. |
| `test_v2_atomic_write_failure_cleans_output` | Post-write chmod/commit failure removes final output; DB unchanged. |
| `test_v2_zero_mutation_before_delete_on_every_validation_failure` | Parametric or explicit tests proving that each pre-delete validation class leaves target and non-target rows untouched. |
| `test_v2_post_write_target_verification_failure_rolls_back` | After DELETE/INSERT, a target-state verification failure triggers rollback; both target and non-target rows remain as before restore. |
| `test_v2_post_write_witness_verification_failure_rolls_back` | After DELETE/INSERT, a witness-state verification failure triggers rollback; both target and non-target rows remain as before restore. |
| `test_v2_malformed_preserved_state_rejected` | Parametric or grouped tests covering: exact key mismatch; `sources` or `policies` not lists; `sources` not strictly increasing by `source_id` or contains duplicates; `policies` not strictly increasing by `agent_id` or contains duplicates; tampered `preserved_state` structure or values that cause digest mismatch. All reject before DB mutation. |

## 10. Resolution of approved plan literal ambiguity — v1 golden bytes

The existing tests `test_capture_prior_absence_exact_bytes_and_digest` and `test_capture_existing_capacity_exact_bytes_and_digest` currently assert v1 envelope bytes as golden. The new writer will output v2 envelopes.

Bootstrap directive:
- **Keep the test scenarios and regression intent.** Do not delete them.
- **Update their golden expectations to v2**, where `preserved_state` is present and empty for single-source DBs (`{"sources": [], "policies": []}`).
- Add separate **handcrafted v1 fixture tests** that prove old v1 snapshots still parse and restore correctly on single-source DBs, and reject multi-source DBs.
- Do **not** require v1 capture bytes to be unchanged under the v2 writer. Do **not** delete the prior-absence or existing-capacity exact-bytes regression scenarios. Handcrafted v1 fixtures are the sole proof of backward restore compatibility.

## 11. Worker verification

Before declaring completion, the worker must run, in the isolated Coordinate worktree, using the Coordinate repository's existing interpreter:

```bash
PYTHON=/Users/yinxin/projects/coordinate/.venv/bin/python
```

1. Focused capacity suite:
   ```bash
   PYTHONPATH=src $PYTHON -m pytest tests/test_executor_capacity.py -v
   ```
   Expected focused baseline: **91 passed**.

2. Coordinate full suite:
   ```bash
   PYTHONPATH=src $PYTHON -m pytest
   ```
   Expected full baseline from Package 1 review: **2415 passed, 493 subtests passed, 9 historical failures**. The worker must first reproduce the exact base `a7397b9` result, then report the worker HEAD result. It must report the exact failure list at both revisions and confirm no new failures and no historical failure suppressed; baseline differences caused by counting or timing drift are not failures.

3. Compile check:
   ```bash
   PYTHONPATH=src $PYTHON -m compileall src/coordinate tests
   ```

4. Whitespace check:
   ```bash
   git diff --check
   ```

5. Changed-file allowlist verification — only `src/coordinate/executor_capacity.py` and `tests/test_executor_capacity.py` may differ from base.

6. Base-vs-worker failure comparison — capture the full suite failure list at base `a7397b9` and at worker HEAD; report any new failure or any missing historical failure.

Do **not** install or upgrade dependencies during verification.

## 12. Worker completion contract

On completion, the worker must:

- Produce exactly **one local commit** in the isolated Coordinate worktree.
- **Not** push, merge, deploy, SSH, modify DB, activate fixtures, or run production services.
- Report:
  - exact commit SHA;
  - changed files with line counts;
  - focused suite result (count + duration);
  - full suite result (count + duration + failure list);
  - base-vs-worker failure comparison;
  - brief architecture summary;
  - residual risks;
  - provider-native JSONL log path, if any.

After worker self-verification, the implementation and result must be reviewed by Codex, and then by an independent exact-revision result reviewer. Both reviews must pass before C1 is considered closed, merged, deployed, or used to unblock C2 / fixture activation / P9-3C1.

## 13. Fail-closed stop conditions and production prohibitions

Stop and escalate immediately if any of the following occur:
- Any validation failure results in observable DB mutation.
- `preserved_state` is accidentally written back to the DB.
- v1 snapshot is accepted on a multi-source DB.
- A file outside `src/coordinate/executor_capacity.py` or `tests/test_executor_capacity.py` is modified.
- The full suite shows a new failure or a historical failure is silently suppressed.
- Any change to schema, CLI, deploy scripts, config, docs, or MultiNexus planning files is requested.

Production prohibitions remain in force:
- Do not activate a second capacity source.
- Do not create fixture runtime agents, executor sources, capacity sources, units, or jobs.
- Do not run production deploys, service restarts, or fixture units.
- Do not perform real v2 restore round-trips against the live production DB; production verification is read-only capture/readback only.
- C2 (MultiNexus deploy contract tests), fixture activation, and P9-3C1 remain blocked until C1 closes with Codex review and independent exact-revision result review.

## 14. Bootstrap review sentinel

`P9_3C0_SNAPSHOT_COMPATIBILITY_C1_BOOTSTRAP_CORRECTED_FOR_INDEPENDENT_REVIEW`
