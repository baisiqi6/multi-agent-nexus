# P9-3C1 P3 Retry Incident IR-B — KAT-Coder-Pro V2.5 T2-B Tests Worker Bootstrap

状态：`DRAFT_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_T2B_WORK_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Role and checkpoint boundary

You are the non-Codex T2-B tests-only worker，invoked through OMP exact model
`kat-coder/kat-coder-pro-v2.5` with `--thinking high`。Codex remains architect/operator/result reviewer。

This bootstrap opens only the strict catalog snapshot/classifier checkpoint defined by the approved IR-B plan
§7 and §12.2、the approved T2 decomposition and the accepted T2-A review。T2-C、T2-D and runtime implementation
remain blocked。

Read only these repository authorities before editing：

1. `p9-3c1-p3-retry-incident-ir-b-controller-recovery-plan.md`，especially §7 and §12.2；
2. `p9-3c1-p3-retry-incident-ir-b-controller-recovery-plan-review.md`；
3. `p9-3c1-p3-retry-incident-ir-b-t2-tests-decomposition-addendum.md` and its review；
4. `p9-3c1-p3-retry-incident-ir-b-glm52-t2a-tests-review.md`；
5. the current `tests/test_p9_3c1_production_controller.py` and
   `scripts/p9_3c1_controller.py`；
6. the six sealed executor/capacity TOMLs under
   `multinexus/fixture/config/p9-3c1/`。

Do not read any prior KAT、Claude、DeepSeek or GLM worktree/session/JSONL。The operator applies the exact accepted
T2-A recovery patch before launch；the worker reads only the resulting repository file。

## 2. Fresh base and accepted-prefix authority

After this bootstrap and its independent review are committed/pushed，the operator supplies exact
`WORKER_BASE` and creates：

- worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p3-retry-incident-ir-b-kat25-t2b-r1`；
- branch：`agents/kat25/p9-3c1-p3-retry-incident-ir-b-t2b-r1`；
- parent：exact `WORKER_BASE`。

The operator，not the worker，applies accepted patch SHA-256
`8bb438b53603f22d0569012bea322d059210e195cb0ab0b654ecf85a6f6668d7`。Before worker launch：

```text
git diff --numstat == 2584 0 tests/test_p9_3c1_production_controller.py
sha256(tests/test_p9_3c1_production_controller.py) ==
1364d7710a22fd570eb871e09c902b9cd63ccb23d1dfa45f3469151999fa8914
accepted file bytes == 175494
git diff --name-only == tests/test_p9_3c1_production_controller.py
runtime/deploy-contract diff == empty
```

The worker verifies these values before editing。T2-B is append-only：append the new T2-B section after the
existing EOF，without modifying any of the accepted first `175494` bytes。At completion，hash the first
`175494` bytes and require the same accepted SHA-256 above。Imports needed only by T2-B may be placed at the
start of the appended section。

Any prefix mismatch is `T2B_BLOCKED`。

## 3. Fixed future test-facing contracts

Tests and later implementation share exactly：

```python
_read_strict_catalog_snapshot() -> dict[str, list[dict[str, Any]]]
_classify_catalog(run_id) -> str
```

Add one future seam key `catalog_snapshot`。Its production default is `_read_strict_catalog_snapshot`；tests may
replace only this seam to inject impossible duplicate/malformed rows。`_classify_catalog(run_id)` obtains the
snapshot through that seam and returns exactly `LOWER_MONOTONIC` or `TERMINAL_SKIP`，or raises bounded
`ControllerError`。

The snapshot top-level exact keys and row keys are：

```text
executor_sources:
  source_id, source_version, catalog_hash, source_path
executor_definitions:
  id, source_id, provider, adapter, capabilities_json, metadata_json
executor_bindings:
  agent_id, source_id, executor_definition_id, runner_profile_id, enabled
capacity_sources:
  source_id, source_version, catalog_hash, source_path
capacity_policies:
  agent_id, source_id, source_version, catalog_hash, capacity_policy_id,
  max_concurrent_jobs
```

Every top-level value is a list；every row is an exact-key object；ordering is deterministic。Set the bounded
contract to at most `64` rows across the five lists。`bool` is rejected anywhere an integer is required。

## 4. Real read-only SQLite snapshot

Build one T2-B-specific temp SQLite fixture on the existing temp `production_db` seam；do not alter the shared
`controller_seams` prefix。Create only the five real schema-13 tables required by the snapshot and seed exact
rows。Reader tests call `_read_strict_catalog_snapshot()`，not a test-owned implementation。

The production reader must use `_open_evidence_db()` and explicit-column ordered SQL。It reads：

- the exact executor source id `p9-3c1-fixture-executors`；
- definitions whose `source_id` is the target **or** whose `id` is
  `p9-3c1-local-fixture`；
- bindings whose `source_id` is the target，whose `agent_id` is E1/E2，or whose
  `executor_definition_id` is `p9-3c1-local-fixture`；
- the exact capacity source id `p9-3c1-fixture-capacity`；
- capacity policies whose `source_id` is the target or whose `agent_id` is E1/E2。

Those predicates expose foreign rows claiming target definition/agent authority。Completely unrelated rows are
not returned or mutated。The helper opens read-only、performs no PRAGMA/schema/data write and closes on success
or error。Tests compare exact rows and prove DB content remains unchanged。

## 5. Independent sealed semantic oracle

The test fixture derives expected catalogs independently from the six actual TOMLs using stdlib `tomllib` and
`_ctrl.canonical_json` only。Do not import Coordinate modules or use CLI `list` output。Before parsing each file，
assert its real byte SHA equals the run manifest `config_hashes[filename]`。Source paths are dynamic exact
`os.path.realpath(_ctrl._config_asset(filename))` values，never hard-coded worktree paths。

Executor semantic catalog hash is SHA-256 over canonical UTF-8 JSON：

```json
{"contract_version":1,"executor_definitions":[...],"executor_instance_bindings":[...],"source_id":"p9-3c1-fixture-executors","source_version":N}
```

Definitions sort by `id` and contain exactly `id/provider/adapter/capabilities`；bindings sort by `agent_id` and
contain exactly `agent_id/executor_definition_id/runner_profile_id/enabled`。DB definition JSON is exact canonical
`capabilities_json` and exact `metadata_json == "{}"`；DB `enabled` is exact integer `0` or `1`。

Capacity semantic catalog hash is SHA-256 over canonical UTF-8 JSON：

```json
{"contract_version":1,"policies":[...],"source_id":"p9-3c1-fixture-capacity","source_version":N}
```

Policies sort by `agent_id` and contain exactly `agent_id/max_concurrent_jobs`。Each `capacity_policy_id` is
`sha256:` plus the SHA-256 of canonical UTF-8 JSON containing exactly
`agent_id/catalog_hash/contract_version/max_concurrent_jobs/source_id/source_version`。

Known semantic anchors from the reviewed immutable TOMLs are：

| file | semantic catalog hash |
|---|---|
| `executor.v1-disabled.toml` | `c8709b5f2f758687338884b9bc5332f36af19b1932a75648a3cb44a257790137` |
| `executor.v2-enabled.toml` | `014e8e9bd8d7adefaca005b3a5db3d3451334e166899cb79a08f5678262ef023` |
| `executor.v3-disabled.toml` | `23040a4afe1b2680cc388cec855d626346278e9581502813e14843a082134a63` |
| `executor.v4-empty.toml` | `1c39b5468c921275745f37bee8b22cc99e2333eabc38e4f70e1217f0733637b1` |
| `capacity.v1.toml` | `d5ded9c09f67095bb076ba9a8c94a44022a73c04d52e012a2e90a80b6df7dd04` |
| `capacity.v2-empty.toml` | `b2e66579b4451758194ae68105e950e587aee00ddf1d5a3f6aaadf8e03e26fd7` |

Capacity v1 exact policy ids are：

- E1：`sha256:374434c52449a9a89b108a3a5c24ae8ce7414b674da42ce394bbafc14e4cb4f0`；
- E2：`sha256:9919568fc32c8adc8627d8ba44943843b1248e9e811579733a6aae35c4140598`。

Semantic hashes must never be replaced with raw TOML file SHA or placeholder digits。

## 6. Mandatory T2-B dynamic matrix

All negative tests use `with pytest.raises(_ctrl.ControllerError, match=<boundary>)` so a correct implementation
passes while current missing helpers or wrong integration behavior remain visible。Parameterization is encouraged；
representative sampling is forbidden。

### B1. Snapshot reader and envelope

Prove one exact positive SQLite read，deterministic ordering，exact column stripping and unchanged DB rows。Prove
foreign rows claiming target ids/agents are returned。Inject/query failure and require bounded non-disclosing
`ControllerError` plus close/read-only behavior。

Through the `catalog_snapshot` seam，reject independently：

- top-level non-object、each missing top-level key and one extra key；
- each of the five top-level values as non-list；
- a non-object row in each list；
- every missing authoritative row key across all five row shapes and one extra key per row shape；
- duplicate target source、definition、binding and policy rows；
- more than `64` total rows。

### B2. Accepted decisions

Generate all eight lower Cartesian states from the sealed semantic oracle：

```text
executor absent/v1/v2/v3 × capacity absent/v1
```

Each returns exact `LOWER_MONOTONIC`。Exact empty executor v4 plus exact empty capacity v2 returns exact
`TERMINAL_SKIP`。Add unrelated non-target DB rows and prove the target decision and unrelated rows remain
unchanged。

### B3. Type、version and semantic drift

Reject independently：

- wrong type for every authoritative string field in each row shape；
- `bool` and non-integer for executor/capacity source versions、binding `enabled`、policy `source_version` and
  `max_concurrent_jobs`；
- version `< 0`、executor `0` or `> 4`、capacity `0` or `> 2`；
- source id/path/catalog-hash drift；
- definition id/source/provider/adapter/capabilities/metadata drift，including malformed、noncanonical or
  wrong-decoded JSON；
- binding agent/source/definition/profile/enabled drift；
- capacity source id/path/hash drift；
- policy agent/source/version/hash/policy-id/max drift；
- source missing while its target rows remain；missing or extra definition/binding/policy rows；partial row sets；
- a foreign source claiming the target definition id、target binding agent/definition or target capacity agent；
- executor v4 with any definition/binding and capacity v2 with any policy；
- executor v4 paired with capacity absent/v1，and capacity v2 paired with executor absent/v1/v2/v3。

Shape-valid but semantically wrong hashes/policy ids must be recomputed-invalid，not merely malformed strings。

### B4. Cleanup integration before mutation

Using existing live fakes and exact call tracing，prove：

1. an invalid classifier result at `agents-online+` blocks before a new ledger append、helper call、Coordinate
   call or agent deactivation and retains the owned lock；
2. exact `TERMINAL_SKIP` performs zero v3/v2/v4 sync calls but completes agents-offline、canonical/DB evidence、
   `done` phase and exact release；
3. every exact lower state retains the three ordered sync calls
   `executor.v3-disabled.toml -> capacity.v2-empty.toml -> executor.v4-empty.toml`；
4. cleanup from `workspace-ready` or earlier preserves the current no-catalog behavior and does not call the
   classifier。

Do not open incident resume、pre-acquire、token swap or guard-callback tests；those belong to T2-C/D。

## 7. Checkpoint verification and stop token

Before reporting：

- accepted first `175494` bytes still hash to
  `1364d7710a22fd570eb871e09c902b9cd63ccb23d1dfa45f3469151999fa8914`；
- T1 remains the same four expected runtime-negative failures；
- T2-A remains `204` helper-missing failures plus one safety meta pass；
- every T2-B positive/negative reaches its intended future helper or current integration boundary；
- the pre-existing `47` controller tests still pass；
- only `tests/test_p9_3c1_production_controller.py` changed；
- runtime and deploy-contract remain byte-identical；
- `py_compile` and `git diff --check` pass；
- no commit。

Report exact B1-B4 collected counts and a table of every parameter id/rejection boundary。If complete，output exact
`T2B_READY_FOR_CODEX_REVIEW`。Otherwise output `T2B_BLOCKED` with exact missing cases。

No T2-B output authorizes T2-C、T2-D、runtime implementation、commit、network/SSH/production access、P0
recover/release、cleanup/resume invocation、push/merge or deploy。

P9_3C1_P3_RETRY_INCIDENT_IR_B_KAT25_T2B_BOOTSTRAP_AWAITING_INDEPENDENT_REVIEW_ALL_WORK_BLOCKED
