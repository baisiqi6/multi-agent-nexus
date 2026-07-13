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

- `capacity_catalog_v1.json` SHA-256 (both repos): `2ae67c8d123b2e1b2165e42b498c7a470418b8bad4a9cefd2ac88379cc94fd2a` — byte-identical.
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

## Residual risks

- The 9 historical CLI/AST failures are pre-existing and unrelated to P9-3A; they must be reconciled in a future P9-0A cleanup or parser-normalization task.
- Capacity policy is currently a versioned snapshot projection; future work may need to reconcile it with live agent enablement changes.
- Lease expiration is caller-transaction driven; no background reaper exists, per approved plan.
