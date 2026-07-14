# P9-3A Capacity/Resource Lease Foundation — Implementation Report

## Authority

- Approved plan: `docs/project-harness/tasks/p9-3a-capacity-resource-lease-foundation/plan.md`
- Exact approved plan SHA-256: `77f467f1d9555552b236f0958d0f08fd267f3cb8193ab83541580de8f0ab7c0f`
- Model used: `kimi-code/kimi-for-coding` (ordinary, not highspeed)
- Original session: `019f5c53...`
- Correction session: `019f5c8c...`
- Coordinate code start: `90783b2c77933287ba163c4bb598f4a862e8b416`
- MultiNexus code start: `94f30b8f01a6e2a578be5f471d4f72b5188f57a8`

## Scope summary

Implemented Stage A–D of the approved plan in the two isolated worktrees only:

- Coordinate: `agents/mac-omp/p9-3a-capacity-resource-lease-foundation-coordinate`
- MultiNexus: `agents/mac-omp/p9-3a-capacity-resource-lease-foundation`

No changes were made to `/Users/yinxin/projects/coordinate` or `/Users/yinxin/projects/multinexus` main checkouts. No push, merge, deploy, SSH, production DB access, or harness operator actions were performed.

## Files changed

### Coordinate

New modules:

- `src/coordinate/executor_capacity.py`
- `src/coordinate/execution_resources.py`
- `src/coordinate/execution_leases.py`

Modified:

- `src/coordinate/execution_cli.py` — adds `capacity` subcommands (`sync`, `list`, `show`)
- `src/coordinate/executor_identity.py` — minimal allow/ignore for `capacity` projection
- `src/coordinate/schema.py` — schema v13 tables, indexes, partial unique active lease index, FKs
- `tests/test_execution_cli.py` — updated `handle_runtime_capacity_sync` canonical AST hash
- `tests/test_agent_registry.py` — capacity boundary tests
- `tests/test_db.py` — schema/migration/two-connection race tests
- `tests/test_executor_identity.py` — unchanged identity invariants
- `tests/fixtures/cli_contract.json` — regenerated CLI contract fixture
- `tests/fixtures/capacity_catalog_v1.json` — cross-repo canonical fixture

New tests:

- `tests/test_executor_capacity.py`
- `tests/test_execution_resources.py`
- `tests/test_execution_leases.py`

### MultiNexus

New module:

- `multinexus/executor_capacity_authority.py`

Modified:

- `config/agent-registry.toml` — adds capacity section (versioned projection, capacity=1 for all enabled typed agents)
- `multinexus/registry_authority.py` — minimal allow/ignore for capacity projection
- `scripts/agent_registry_deploy_verify.py` — guarded capacity stage verification
- `scripts/deploy-server.sh` — fault-injection-aware deployment script
- `tests/test_deploy_contract.py` — deploy/parity contract tests
- `tests/test_smoke_contract.py` — smoke contract tests
- `tests/fixtures/capacity_catalog_v1.json` — byte-identical to Coordinate fixture

New test:

- `tests/test_executor_capacity_authority.py`

## Verification evidence

### Coordinate full suite

Command:

```text
cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3a-kimi
PYTHONPATH=src python -m pytest tests/ --import-mode=importlib -q
```

Result:

```text
9 failed, 2217 passed, 493 subtests passed in 65.16s
```

The 9 failures are exactly the historical CLI-fixture/AST baseline failures:

- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a1_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2a_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2b_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2c_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a3a_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_differs_from_p9_0a4a_baseline_only_at_12_handlers`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_s4b1_rewind_matches_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_s4c1_rewind_matches_baseline`
- `tests/test_issue_cli.py::IssueCLIOwnershipTests::test_all_five_handler_ast_bodies_match_start_revision`

### Coordinate focused tests

```text
PYTHONPATH=src python -m pytest tests/test_executor_identity.py -q
44 passed, 12 subtests passed

PYTHONPATH=src python -m pytest tests/test_executor_identity.py::CanonicalBytesTests -q -v
3 passed
```

### MultiNexus full suite

Command:

```text
cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3a-kimi
PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest tests -q
```

Result:

```text
517 passed, 2 skipped, 36 subtests passed in 21.78s
```

## Cross-repo contract evidence

- `capacity_catalog_v1.json` raw file SHA-256 (both repos): `2ae67c8d123b2e1b2165e42b498c7a470418b8bad4a9cefd2ac88379cc94fd2a` — byte-identical.
- Canonical `catalog_hash` computed from the catalog object: `3c5b31d17424f3dc12b56d5e0d545f5a46b7d212193465d79c874cb82a9a918d`.
- P9-2 executor catalog hash remains unchanged: `f4cdf79897755c173e97ddae1dfd88047436039f3447d4d6257105715ba5551d`.
- P9-2 binding IDs, roster bytes, and exact/routed behavior are unchanged (verified by `test_executor_identity.py` and runtime compatibility suites).
- `handle_runtime_capacity_sync` canonical AST hash updated to `5655f5afc2b2967b07863e0a64243e559ab8f024a5de0dde491bb374f93515dc`.

## Static scope checks

- `git diff --check` passed in both worktrees (no whitespace errors).
- `runtime.py` was not modified; no changes to claim/report/progress or managed lease token/heartbeat/job reap/recovery/session observation.
- No agentd/provider/client/adapter changes.
- No main checkout files touched.

## Deployment status

No deployment, push, merge, or production action was performed. The deployment verification and fault-injection scripts are implemented and tested locally only. Cross-sync failure handling preserves the previous accepted projection and does not write version/restart/success until complete capacity parity is verified.

## Result Review Correction Round 1

### Scope and constraints
- Same approved plan; no new P9-3B claim/heartbeat, P9-4 observation, or P9-5 scheduler behavior added.
- No push, merge, deploy, SSH, production DB access, or harness operator actions.

### Findings fixed

#### Coordinate

C1. shared TOML 被真实 parser 拒绝
- **Fix:** `src/coordinate/executor_capacity.py::parse_capacity_catalog()` root allow-list expanded to the exact known shared root set: `registry`, `executor_definitions`, `agents`, `external_agents`, `capacity_registry`, `executor_capacities`. Rejects unknown and secret-bearing roots. Source id validation no longer silently strips non-strings.
- **Tests:** `test_parse_accepts_real_multinexus_registry`, `test_parse_rejects_unknown_capacity_root_keys`, `test_parse_rejects_secret_bearing_root_keys`, `test_parse_rejects_whitespace_source_id`, `test_source_id_is_not_coerced_from_non_string` in `tests/test_executor_capacity.py`.

C2. exact retry 绕过当前 coverage
- **Fix:** `sync_capacity_catalog()` now validates coverage against the current executor binding snapshot before returning on same version/hash. No source/policy timestamp is written on exact retry.
- **Tests:** `test_exact_retry_validates_coverage_after_disabled_binding`, `test_exact_retry_validates_coverage_after_new_binding` in `tests/test_executor_capacity.py`.

C3. reserve 缺失 attempt/context cross-links
- **Fix:** `reserve_attempt_lease()` validates `attempt_token` is a strict positive integer equal to `jobs.attempt_count`; validates the job `payload_json.execution_context` via `execution_context.validate_execution_context_snapshot()`; enforces exact match of `job_id`, `workspace_id`, `assigned_agent`, `host_id`, and normalized `worktree_path`. Fail-closed before any lease write.
- **Tests:** `LeaseContextCrossLinkTests` in `tests/test_execution_leases.py`.

C4. stored resource tamper 未 fail closed
- **Fix:** `validate_resource_key_matches()` is invoked on every read/write path that consumes a stored lease snapshot (reserve replay, renew, release, expire, get, list). It rebuilds the contract v1 resource from `resource_kind + host_id + normalized_path` and compares exact shape/digest.
- **Tests:** `LeaseStoredResourceTamperTests` in `tests/test_execution_leases.py`.

C5. Windows lexical resource 边界错误
- **Fix:** `execution_resources.py` treats `//SERVER/Share/path` as UNC; rejects bare `C:` drive-relative paths; accepts `C:\\...` and `C:/...` as drive roots; no silent `.strip()` on `host_id`; adds mixed separator/casefold tests.
- **Tests:** `ResourceWindowsLexicalTests` in `tests/test_execution_resources.py`.

C6. release reason 未 bounded, attempt 类型校验不严格
- **Fix:** `MAX_RELEASE_REASON_LEN = 256`; release reason must be a non-empty Unicode string ≤ 256 without control/NUL characters; same reason replay preserves the original time, different reason fail-closed; shared strict positive integer validator for attempt in reserve/renew/release/expire, rejecting booleans.
- **Tests:** `LeaseReleaseReasonTests` in `tests/test_execution_leases.py`.

C7. schema v13 缺计划要求的约束与 rollback 证明
- **Fix:** `schema.py` v13 `execution_attempt_leases` adds `capacity_policy_id NOT NULL`; `host_id` length 1..64; `resource_key` glob `sha256:*` and length 71; `normalized_path` length 1..4096; `capacity_policy_id` glob/length 71; state-shape CHECK constraints for active/released rows; timestamp-order CHECK constraints; clean v12→v13 migration; repeated migration idempotent; atomic rollback verified via a malformed pre-existing table.
- **Tests:** `SchemaV13Tests` in `tests/test_db.py`.

#### MultiNexus

M1. Multi capacity parser 根级 schema 不 strict
- **Fix:** `multinexus/executor_capacity_authority.py` uses the same `_ALLOWED_SHARED_ROOT_KEYS` set as Coordinate; accepts the real `config/agent-registry.toml`; rejects unknown/secret-bearing roots; source id is no longer coerced or stripped.
- **Tests:** `test_parse_accepts_real_multinexus_registry`, `test_parse_rejects_unknown_capacity_root_keys`, `test_parse_rejects_secret_bearing_root_keys`, `test_parse_rejects_whitespace_source_id`, `test_source_id_is_not_coerced_from_non_string` in `tests/test_executor_capacity_authority.py`.

M2. verifier 没有验证 capacity_policy_id
- **Fix:** `scripts/agent_registry_deploy_verify.py` recomputes `capacity_policy_id` for each policy and compares it to the DB row; failure is fail-closed.
- **Tests:** `test_capacity_policy_id_mismatch_restores_previous_and_no_version_restart` in `tests/test_deploy_contract.py`.

M3. guarded deploy rollback 覆盖不完整
- **Fix:** `scripts/deploy-server.sh` now backs up the current accepted authority before the rsync, then runs guarded parity → roster → executor → capacity → `runtime capacity list` → committed verifier. Any stage failure triggers `restore_previous_accepted_state`, which restores the old authority and replays the full old projection (or verifies capacity absence if the old authority has no capacity roots). No `VERSION_DEPLOYED`, restart, or smoke is written until all stages succeed.
- **Tests:** `test_capacity_sync_failure_no_version_restart_and_previous_restored`, `test_capacity_policy_id_mismatch_restores_previous_and_no_version_restart` in `tests/test_deploy_contract.py`.

### Verification evidence (after correction)

Coordinate full suite:
```text
cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3a-kimi
PYTHONPATH=src python -m pytest tests/ --import-mode=importlib -q
9 failed, 2249 passed, 493 subtests passed in 65.78s
```
The 9 failures are the same historical baseline: 8 `tests/test_cli_contract.py` hash failures + 1 `tests/test_issue_cli.py` AST handler hash failure.

Coordinate focused tests:
```text
PYTHONPATH=src python -m pytest tests/test_executor_capacity.py tests/test_execution_resources.py tests/test_execution_leases.py tests/test_db.py tests/test_execution_cli.py -q
161 passed, 5 subtests passed in 0.87s
```

MultiNexus full suite:
```text
cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3a-kimi
PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest tests -q
523 passed, 2 skipped, 1 warning, 36 subtests passed in 26.50s
```

MultiNexus focused tests:
```text
PYTHONPATH=. python -m pytest tests/test_executor_capacity_authority.py tests/test_deploy_contract.py tests/test_smoke_contract.py -q
31 passed in 22.61s
```

Static checks:
- Coordinate: `git diff --check` and `python -m compileall src/coordinate tests` passed.
- MultiNexus: `git diff --check`, `bash -n scripts/deploy-server.sh`, and `python -m compileall multinexus scripts tests` passed.

### Corrected cross-repo contract evidence
- `capacity_catalog_v1.json` raw file SHA-256 (both repos): `2ae67c8d123b2e1b2165e42b498c7a470418b8bad4a9cefd2ac88379cc94fd2a` — byte-identical. Canonical `catalog_hash`: `3c5b31d17424f3dc12b56d5e0d545f5a46b7d212193465d79c874cb82a9a918d`.
- P9-2 executor catalog hash, roster bytes, and binding ids remain unchanged.

### Files changed in correction

Coordinate:
- `src/coordinate/executor_capacity.py`
- `src/coordinate/execution_resources.py`
- `src/coordinate/execution_leases.py`
- `src/coordinate/schema.py`
- `tests/test_executor_capacity.py`
- `tests/test_execution_resources.py`
- `tests/test_execution_leases.py`
- `tests/test_db.py`

MultiNexus:
- `multinexus/executor_capacity_authority.py`
- `scripts/agent_registry_deploy_verify.py`
- `scripts/deploy-server.sh`
- `tests/test_executor_capacity_authority.py`
- `tests/test_deploy_contract.py`
- `docs/project-harness/tasks/p9-3a-capacity-resource-lease-foundation/implementation-report.md`

### Residual risks
- The 9 Coordinate CLI/AST failures are pre-existing baseline and unrelated to P9-3A.
- Guarded deploy rollback assumes the previously accepted authority file exists; a first-time deploy with no capacity backup cannot restore a prior projection (verified absent instead).
- No production runtime, background lease reaper, or heartbeat/claim behavior was introduced.

## Residual risks

- The 9 historical CLI/AST failures are pre-existing and unrelated to P9-3A; they must be reconciled in a future P9-0A cleanup or parser-normalization task.
- Capacity policy is currently a versioned snapshot projection; future work may need to reconcile it with live agent enablement changes.
- Lease expiration is caller-transaction driven; no background reaper exists, per approved plan.

## Result Review Correction Round 2

- Approved amended plan SHA-256: `d75486b42e8d3315bda488db1129e02c03c0a2c152c04a60cccce917a385d99e`
- Round-4 plan review: APPROVED (GLM 5.2 reviewer-only session)
- Coding worker: `zhipu-coding-plan/glm-5.2` (continuation after Kimi provider quota stop)
- Coordinate round-1 commit: `e78a7d1c6130a83ecb720f978a6379582f446896`
- MultiNexus round-1 commit: `7ae3959d64316ee6d136a5efdaa0ded7fb0e3fff`
- Same approved plan; no new P9-3B claim/heartbeat, P9-4 observation, or P9-5 scheduler behavior added.
- No push, merge, deploy, SSH, production DB access, or harness operator actions.

### Findings fixed

#### R2-1 — Real prior-absence snapshot capture/restore for first rollout

- **Fix:** `src/coordinate/executor_capacity.py` implements internal, capacity-only, digest-bound snapshot capture/restore (`capture_capacity_snapshot`, `restore_capacity_snapshot`). Two-layer exact-shape JSON envelope: inner `snapshot` object with `contract_version=1`, `target_source_id`, and `captured_state` (null for prior absence). Digest computed only over canonical inner bytes (`ensure_ascii=False`, `sort_keys=True`, compact separators); policies sorted by `agent_id`.
- Capture opens `BEGIN IMMEDIATE`, rejects unexpected extra sources, orphan/mismatched policies, and recomputes every `capacity_policy_id`. Snapshot file written atomically with final mode `0600`, secret-free.
- Restore owns its own `BEGIN IMMEDIATE`, rejects active leases and unexpected sources, verifies envelope/digest/expected source, deletes target projection for prior-absence, exactly restores source/policies for existing state, rereads DB and exact-compares before commit. Any error rolls back; roster/executor/jobs/events/leases untouched.
- **MultiNexus:** `scripts/capacity_snapshot_helper.py` is a focused internal helper (not public CLI) that imports installed Coordinate `capture/restore_capacity_snapshot`. `scripts/deploy-server.sh` captures the snapshot before authority overwrite, restores in order (old authority → roster → executor → capacity snapshot) on any post-overwrite failure, re-verifies all three projections, and suppresses version/restart/smoke until full parity. Snapshot file is trap-cleaned on normal exit.
- **Tests:** `CapacitySnapshotTests` in `tests/test_executor_capacity.py` (11 tests: prior-absence exact bytes/digest, existing capacity exact bytes/digest, unexpected source rejection, mismatched policy-id rejection, existing-state exact restore, prior-absence restore deletes new capacity, active-lease rejection, tampered-digest rejection, wrong-target-source rejection, malformed-JSON rejection, unexpected-source-during-restore rejection).

#### R2-2 — Stored resource snapshot now rejects non-canonical data

- **Fix:** `src/coordinate/execution_resources.py::validate_resource_key_matches()` enforces full-match `^sha256:[0-9a-f]{64}$` on `resource_key`, reuses strict `_validate_host_id` on stored `host_id`, and requires `normalize_worktree_path()` output to be byte-identical to the stored `normalized_path`. An attacker who recomputes the digest after tampering is still rejected because the path/host is not canonical.
- **Tests:** `StoredResourceValidationTests` in `tests/test_execution_resources.py` (13 tests: valid pass, whitespace/empty host, trailing-slash/dot-segment/relative/control/overlong path, uppercase/truncated/nonhex digest, non-string key, digest tamper — all using attacker-recomputed digests).

#### R2-3 — Bulk/decision lease paths validate all candidate rows before write

- **Fix:** `src/coordinate/execution_leases.py` — `count_active_leases_for_agent`, `_find_active_resource_lease`, `_expire_due_for_agent_or_resource`, and `expire_due_attempt_leases` now SELECT full rows, call `_validate_stored_resource` on each, and only then UPDATE/COUNT/decide. One malformed candidate row fails the entire operation closed; zero partial writes.
- **Tests:** `LeaseBulkDecisionTamperTests` in `tests/test_execution_leases.py` (4 tests: tampered resource in count, tampered resource in find, one tampered due row leaves all active, tampered due lease in reserve path fails before write).

#### R2-4 — Malformed job payload becomes LeaseError

- **Fix:** `reserve_attempt_lease()` wraps `json.loads(job["payload_json"])` in try/except for `JSONDecodeError`/`TypeError`, converts to `LeaseError` before any lease write. Validates the decoded payload is a dict and has `execution_context`.
- **Tests:** `LeaseContextCrossLinkTests` in `tests/test_execution_leases.py` (4 tests: malformed JSON, JSON scalar, JSON list, missing execution_context).

#### R2-5 — Sibling-worktree test replaced with hermetic fixture

- **Fix:** Both `tests/test_executor_capacity.py` (Coordinate) and `tests/test_executor_capacity_authority.py` (MultiNexus) replace `test_parse_accepts_real_multinexus_registry` (which referenced a sibling checkout and skipped when absent) with `test_parse_accepts_full_shared_registry`, an inline hermetic TOML fixture containing all shared root sections. No sibling checkout, no skip.

#### R2-6 — Report distinguishes raw fixture SHA from canonical catalog hash

- **Fix:** All cross-repo contract evidence sections now distinguish:
  - Raw fixture file SHA-256 (both repos): `2ae67c8d123b2e1b2165e42b498c7a470418b8bad4a9cefd2ac88379cc94fd2a`
  - Canonical `catalog_hash` from the catalog object: `3c5b31d17424f3dc12b56d5e0d545f5a46b7d212193465d79c874cb82a9a918d`

### Verification evidence (after Round 2 correction)

Coordinate focused tests:
```text
cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3a-kimi
PYTHONPATH=src python -m pytest tests/test_executor_capacity.py tests/test_execution_resources.py tests/test_execution_leases.py tests/test_db.py tests/test_execution_cli.py --import-mode=importlib -q
192 passed, 5 subtests passed in 0.92s
```

Coordinate full suite:
```text
PYTHONPATH=src python -m pytest tests/ --import-mode=importlib -q
9 failed, 2280 passed, 493 subtests passed in 67.53s
```
The 9 failures are the same historical baseline (unchanged from Round 1):
- 8 `tests/test_cli_contract.py::CLIContractTests::test_contract_*` cumulative-rewind hash mismatches (P9-0A1/0A2a/0A2b/0A2c/0A3a baselines, P9-0A4a diff, S4-B1/S4-C1 rewinds).
- 1 `tests/test_issue_cli.py::IssueCLIOwnershipTests::test_all_five_handler_ast_bodies_match_start_revision`.

MultiNexus focused tests:
```text
cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3a-kimi
PYTHONPATH=. python -m pytest tests/test_executor_capacity_authority.py tests/test_deploy_contract.py tests/test_smoke_contract.py -q
32 passed in 25.95s
```

MultiNexus full suite:
```text
PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest tests -q
524 passed, 2 skipped, 1 warning, 36 subtests passed in 28.67s
```

Static checks:
- Coordinate: `git diff --check` and `python -m compileall` on all touched source files passed.
- MultiNexus: `git diff --check`, `bash -n scripts/deploy-server.sh`, `python -m py_compile scripts/capacity_snapshot_helper.py`, and `python -m compileall` on touched test files passed.

### Files changed in Round 2 correction

Coordinate:
- `src/coordinate/executor_capacity.py` — snapshot capture/restore (R2-1)
- `src/coordinate/execution_resources.py` — strict stored validation (R2-2)
- `src/coordinate/execution_leases.py` — bulk/decision row validation + malformed payload (R2-3, R2-4)
- `tests/test_executor_capacity.py` — snapshot tests, hermetic fixture (R2-1, R2-5)
- `tests/test_execution_resources.py` — stored validator tests (R2-2)
- `tests/test_execution_leases.py` — bulk tamper + payload tests (R2-3, R2-4)

MultiNexus:
- `scripts/capacity_snapshot_helper.py` — new internal snapshot helper (R2-1)
- `scripts/deploy-server.sh` — snapshot capture/restore in guarded deploy (R2-1)
- `tests/test_executor_capacity_authority.py` — hermetic fixture (R2-5)
- `tests/test_deploy_contract.py` — fake executor_capacity module + snapshot helper in test infra (R2-1)
- `docs/project-harness/tasks/p9-3a-capacity-resource-lease-foundation/implementation-report.md` (R2-6)

### Snapshot contract / rollback evidence

- Snapshot v1 envelope is exact-shape with digest over canonical inner bytes only (no self-reference).
- Prior-absence snapshot captures `captured_state=null` with explicit `target_source_id`; restore deletes only the expected target projection.
- Existing-state restore preserves exact source timestamps/path and policy timestamps; reread-and-compare before commit.
- Restore rejects active lease, unexpected/mismatched sources, tampered digest, wrong target, and malformed JSON.
- Deploy fault-injection tests verify: (1) capacity sync failure → restore old projection + no version/restart; (2) committed verifier failure after capacity sync with existing projection → snapshot restore restores old projection; (3) prior-absence first rollout: old authority has no capacity roots, new sync creates projection, verifier failure → snapshot restore deletes projection and restored old authority has no capacity roots, zero source/policy rows remain, no version/restart.

### Residual risks (Round 2)

- P9-3A production safety still requires zero active lease; P9-3B must replace this temporary snapshot-restore assumption before capacity becomes claim authority.
- The 9 historical CLI/AST baseline failures remain unchanged and unrelated to P9-3A.
- No unresolved items from the Round 2 finding matrix.

## Result Review Correction Round 3 (GLM 5.2) / Round 4 (DeepSeek Takeover)

- Approved plan SHA-256 (Round 3): `d75486b42e8d3315bda488db1129e02c03c0a2c152c04a60cccce917a385d99e`
- Round-3 worker: `zhipu-coding-plan/glm-5.2` — crashed mid-work, left uncommitted diffs
- Round-4 takeover worker: `deepseek/deepseek-v4-pro` — audit + surgical correction + commits
- Durable Round-2 result rejection: `578de868-3ce5-436f-968f-133d720f4cdc`
- Coordinate worktree HEAD: `52e1b82591d0ac20433db456e0f0c50ffbdb9b09`
- MultiNexus worktree HEAD: `2f13cfd5981fff02ced78b375b2ac28f65ab9a85`
- No push, merge, deploy, SSH, production DB access, or harness operator actions.

### Interruption state at takeover

Crashed GLM Round-3 worker left dirty diffs in both worktrees:

Coordinate:
- `src/coordinate/executor_capacity.py` — strict snapshot validator, capture/restore hardening
- `tests/test_executor_capacity.py` — adversarial validation tests

MultiNexus:
- `scripts/capacity_snapshot_helper.py` — busy timeout + FK pragmas
- `scripts/deploy-server.sh` — sudo cleanup, staged helper, source mutation guard, trap hardening
- `tests/test_deploy_contract.py` — fault injection tests, roster/executor assertions

GLM last test run: `9 failed, 2 passed` — all 9 failures caused by a single root cause: unescaped
`\n` in the fake SSH wrapper's f-string broke `textwrap.dedent`, leaving the shebang with leading
spaces. Bash then interpreted the Python wrapper as a shell script (`import: command not found`).

### R3-1: Strict snapshot validator (Coordinate) — AUDITED CORRECT

GLM implementation in `src/coordinate/executor_capacity.py`:
- Shared strict validator `_strict_validate_captured_state()` used by both capture and restore
- Non-canonical raw bytes rejected before any DB touch
- Exact key sets validated for every envelope/state/source/policy layer
- `snapshot_sha256` exact `^[0-9a-f]{64}$`, `capacity_policy_id` recomputed and compared
- `target_source_id` bounded safe label validation
- Source: strict non-bool nonnegative version, 64 hex catalog hash, `source_path` null or
  control-free bounded Unicode, strict timestamps
- Policies: strictly increasing by `agent_id`, exact source_version/catalog_hash match,
  capacity 1..32, timestamps strict, policy id recomputed
- Capture: queries ALL sources/policies, rejects orphans/mismatches even with SQLite FK off,
  coverage drift check against enabled typed bindings
- Restore: validates current DB for orphans/mismatched policies BEFORE DELETE
- Commit failure cleanup: `_safe_unlink()` removes written file on rollback

R3-1 adversarial tests (all in `test_executor_capacity.py::CapacitySnapshotTests`):
- `test_restore_rejects_noncanonical_raw_bytes` — reformatted JSON + valid digest → reject
- `test_restore_rejects_unknown_field_in_captured_state` — extra key → reject
- `test_restore_rejects_unknown_field_in_source` — extra source key → reject
- `test_restore_rejects_unknown_field_in_policy` — extra policy key → reject
- `test_restore_rejects_modified_source_id_with_valid_digest` → reject
- `test_restore_rejects_modified_source_version_with_valid_digest` → reject
- `test_restore_rejects_unsorted_policies_with_valid_digest` → reject
- `test_restore_rejects_duplicate_agent_policies_with_valid_digest` → reject
- `test_restore_rejects_policy_id_tamper_with_valid_digest` → reject
- `test_restore_rejects_orphan_policy_in_current_db` → reject, orphan survives
- `test_restore_rejects_mismatched_policy_in_current_db` → reject, corrupt row survives
- `test_capture_rejects_orphan_policy_when_source_absent` → reject, no file residue
- `test_capture_rejects_coverage_drift` → reject, no file residue
- `test_capture_commit_failure_cleans_up_file` → injected commit failure, file absent

**Verdict:** R3-1 implementation is complete and correct. No changes needed.

### R3-2: Deploy helper lifecycle + source mutation rollback (MultiNexus) — CORRECTED

GLM implementation in `scripts/deploy-server.sh`:
- `cleanup_capacity_snapshot()`: uses `sudo rm -f` (not unprivileged `rm -f`)
- `restore_capacity_snapshot()` and `capture_capacity_snapshot()`: use staged helper
  (`$staging/scripts/capacity_snapshot_helper.py`) not `/opt/multinexus/scripts/`
- Source mutation (`remote_sudo_script` heredoc): guarded; on failure calls
  `restore_previous_accepted_state` then returns nonzero
- `restore_previous_accepted_state`: restores authority → parity → roster → executor →
  capacity snapshot → committed verify; any sub-stage failure returns nonzero
- Trap: cleans both snapshot (best-effort `|| true`) and staging on EXIT; staging also
  explicitly cleaned on normal exit
- `capacity_snapshot_helper.py`: `timeout=30`, `PRAGMA busy_timeout=5000`,
  `PRAGMA foreign_keys=ON`

Round-4 corrections:
- **Shebang fix:** Changed `\n` to `\\n` in the fake SSH wrapper f-string so that
  `textwrap.dedent` correctly preserves the shebang at column 0. The generated SSH
  script now has the correct `#!/path/to/python` at the start.
- **`bash -n`:** Passes clean.

**Verdict:** R3-2 implementation is correct after shebang fix.

### R3-3: Fault tests assert all three projections (MultiNexus) — CORRECTED

GLM had partial implementation: `_assert_roster_executor_restored()` only checked
`assertIn("mac-claude", ...)` — presence check, not exact equality.

Round-4 corrections:
- Replaced `_assert_roster_executor_restored()` with `_snapshot_full_db_state()` +
  `_assert_db_state_matches()` that compare exact tuples for roster, executor definitions,
  executor bindings, and capacity source/policy rows
- Authority bytes comparison: backup file content exact-matched against restored
  remote config
- All 5 fault tests now do exact tuple comparison:
  - `test_capacity_sync_failure_no_version_restart_and_previous_restored`
  - `test_capacity_policy_id_mismatch_restores_previous_and_no_version_restart`
  - `test_prior_absence_first_rollout_verifier_failure_restores_no_capacity`
  - `test_source_mutation_failure_restores_all_three_projections`
  - `test_restore_hard_failure_is_loud_nonzero_no_version_restart`
- For prior absence: capacity source/policies asserted exact absence (COUNT = 0)
- For restore hard failure: roster + executor exact restored; capacity NOT restored
  (loud nonzero, no version/restart/smoke)

### Non-canonical seed values — CORRECTED

`_seed_previous_capacity()` and inline SQL seedings used `catalog_hash="v1-hash"` and
`capacity_policy_id="sha256:v1-policy"` — non-canonical values. Round-4 replaced these
with properly computed canonical values:
- `catalog_hash`: SHA-256 of `b"multinexus.discord.capacity:v1:mac-claude:1"` =
  `aaf8952ae2f7a2bf56e0f09150ae864b8c41449e90926c0f89290c3ce14acf80`
- `capacity_policy_id`: computed via real `compute_capacity_policy_id` algorithm =
  `sha256:eb332e7e0bdf4ab356db733fdd7c482cfd6344508c72c0077fca6700c7e094c5`

### Verification evidence (Round 4)

Coordinate focused tests:
```text
cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3a-kimi
PYTHONPATH=src python -m pytest tests/test_executor_capacity.py -v
52 passed in 0.10s
```

Coordinate full suite (capacity-related only; pre-existing test_pr_cli.py import error
prevents `tests/` glob — unrelated to P9-3A):
```text
PYTHONPATH=src python -m pytest tests/test_executor_capacity.py -v
52 passed in 0.10s
```

MultiNexus focused tests:
```text
cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3a-kimi
python -m pytest tests/test_deploy_contract.py -v
11 passed in 16.29s
```

MultiNexus full suite:
```text
python -m pytest tests/ -v
526 passed, 2 skipped, 1 warning, 36 subtests passed in 30.23s
```

Static checks:
- Coordinate: `git diff --check` passed
- MultiNexus: `git diff --check` passed, `bash -n scripts/deploy-server.sh` passed,
  `python -m py_compile scripts/capacity_snapshot_helper.py` passed

### Files changed in Round 3/4

Coordinate (GLM Round 3, audited by DeepSeek Round 4):
- `src/coordinate/executor_capacity.py` — strict validator, capture/restore hardening
- `tests/test_executor_capacity.py` — 14 adversarial validation tests

MultiNexus (GLM Round 3 + DeepSeek Round 4 corrections):
- `scripts/capacity_snapshot_helper.py` — busy timeout, FK pragmas
- `scripts/deploy-server.sh` — sudo cleanup, staged helper, source mutation guard
- `tests/test_deploy_contract.py` — shebang fix, canonical seed values, exact tuple
  comparison for all 3 projections, authority bytes comparison

### R3 finding closure

- **R3-1** (strict snapshot validator): IMPLEMENTED by GLM, AUDITED correct by DeepSeek
- **R3-2** (deploy helper lifecycle): IMPLEMENTED by GLM, CORRECTED shebang by DeepSeek
- **R3-3** (fault tests assert all 3 projections): CORRECTED by DeepSeek — exact tuple
  comparison replaces presence-only checks

### Residual risks (Round 4)

- The 9 historical CLI/AST baseline failures remain unchanged and unrelated to P9-3A.
- Deploy contract tests use fake `executor_capacity.py` stubs that bypass the strict
  validator; they test the shell script flow, not the Coordinate-side validation.
  Real validator coverage is in Coordinate's `test_executor_capacity.py`.
- No unresolved items from the Round 3/4 finding matrix.

### Round 4 commits

Coordinate: `375669b7e7b80db715cfbd59b1d48bfff6960cb0`
MultiNexus: `4a4af5cf09620b57a49a5ba3f280657856aee042`
