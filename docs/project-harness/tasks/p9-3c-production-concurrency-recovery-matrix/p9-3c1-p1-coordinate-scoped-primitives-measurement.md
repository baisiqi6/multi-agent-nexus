# P9-3C1 P1 Coordinate Scoped Primitives — Fresh Measurement

状态：`MEASURED_PLAN_REQUIRED_NO_IMPLEMENTATION`

日期：2026-07-16 Asia/Shanghai

本文件是只读 source/test/runtime measurement。它不授权 coding、worktree、worker、commit、
push、deploy、SSH mutation、production DB mutation、lease reap、agent deactivate、service
restart、fixture activation 或 P9-3C1 live matrix。

## 1. Exact revisions and production boundary

- Coordinate source/origin/deployed：
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- MultiNexus source/origin/deployed documentation projection：
  `1b1d1fd1c5c160e3ede16ee2f07fb2989990e3c2`。
- P0 implementation：
  `ec748dc040b9ebf8f456c6bc0ab6db28e0dd26c6`；installed helper SHA-256
  `7dd71c31595c7135a8a75ef3d8e459788682f6a30272ea5bdeb66bb7c2a2ebd4`。
- P0 production lock status：`state=free, phase=free`；canonical services active，
  PID/NRestarts `836234/0` 与 `1276892/0`。
- Production DB：integrity/schema/FK `ok/13/0`，pending/running jobs `0`，active leases
  `0`，P9-3C1 agents/runners/jobs/executor sources/capacity sources/units/processes全为 `0`。

P1 只实现并 inert-deploy Coordinate primitives；不得在 production 调用新 mutation CLI。部署
后只允许 `--help`、version、integrity、hash、lock/status 和 residue readback。

## 2. Exact reap gap

Current `src/coordinate/runtime_lease.py`：

- `reap_due_leases()` 先调用 `_find_due_active_leases(conn, now, batch_size)` 做 global scan；
- 每个 candidate 再 `BEGIN IMMEDIATE`、调用 `_reap_one_lease()`、commit/rollback；
- `_reap_one_lease()` 已具备 stored resource snapshot、exact job/attempt/agent、running job、CAS、
  idempotent `execution_lease.expired`/`job.timed_out` event 和 transaction rollback correctness；
- `_require_active_lease_for_reap()` 会在 write lock 内重新验证 active/due，避免 stale due
  snapshot 与 concurrent renew race。

Current CLI 只有：

```text
coordinate runtime job lease reap --actor ... --batch-size 100
```

`execution_cli.py` parser 把 `--batch-size` default 固定为 `100`，handler 永远调用 global
`reap_due_leases()`。不存在 `--lease-id/--job-id` exact selector。即使 core 的单 lease
transaction安全，P9-3C1 也不能用 global selector，因为 unrelated due production lease 可能在
同一时刻出现。

## 3. Claim-time implicit global reap gap

Typed claim flow：

```text
runtime.claim_job()
-> BEGIN IMMEDIATE
-> runtime_lease.claim_leased_job()
-> _reap_due_leases_in_transaction()
-> select_claim_candidate()
-> CAS job + reserve lease + job.claimed event
```

`claim_leased_job()` 每次 typed claim 都无条件做 bounded global due scan。新增 exact reap CLI
仍不能阻止 normal/recovery fixture claim 改写 unrelated due lease。Current API/CLI 没有
`reap_mode` 或 audited skip reason；`job.claimed` payload 也不记录 claim 的 reap policy。

Compatibility requirement：所有 existing caller 默认行为必须保持 `global`。只有 future P2
P9-3C1 agentd normal/recovery paths 才会显式传 `none + sealed reason`；P1 不修改 MultiNexus
client/agentd。

## 4. Deactivate gap and a newly measured race

Current runtime agent CLI 只有 `register` 和 `heartbeat`。`heartbeat_agent()` 会验证 exact host，
将 existing agent 设为 online 并 append `agent.heartbeat`。没有 audited offline/deactivate
primitive；直接 SQL 修改不允许，删除 agent/runner/history 也不符合 final residue contract。

P1 deactivate 必须在 single `BEGIN IMMEDIATE` transaction 内验证：

- exact agent/host/client type；
- zero active lease；
- zero assigned `pending`、`running`、`timed_out AND recoverable=1` job；
- 然后只更新 exact agent `online_state=offline` 并 append one idempotent
  `agent.deactivated` event。

Fresh red-team finding：`runtime.claim_job()` 当前在 `BEGIN IMMEDIATE` **之前**调用
`_require_online_agent()`；`claim_leased_job()` 在 transaction 内不重新验证 agent online/host。
因此 claim 可能先读到 online、等待 deactivate commit、随后仍 claim 并创建 active lease。P1
不能只新增 deactivate query；必须在 typed claim transaction 内重新验证 agent online + exact
host。若 claim 先赢，deactivate 会看到 active lease/running job并 blocked；若 deactivate 先赢，
claim transaction 内 recheck 必须 fail closed。

Exact request creation目前只要求 agent exists，不要求 online。P9-3C1 controller 必须在 P3
cleanup 前 freeze intake；offline agent 即使出现 pending audit residue也不能 claim。P1 不扩大为
submit-routing redesign，但 tests 必须证明 offline typed claim不能执行。

## 5. Current test and CLI contract surfaces

Likely implementation files：

- `src/coordinate/runtime_lease.py`；
- `src/coordinate/runtime.py`；
- `src/coordinate/execution_cli.py`。

Focused tests：

- `tests/test_runtime_lease.py`；
- `tests/test_runtime.py`；
- `tests/test_execution_cli.py`；
- `tests/test_cli_contract.py`；
- `tests/fixtures/cli_contract.json`。

Fresh base command：

```bash
.venv/bin/python -m pytest -q \
  tests/test_runtime_lease.py tests/test_runtime.py \
  tests/test_execution_cli.py tests/test_cli_contract.py
```

Result：`214 passed, 37 subtests passed, 8 failed in 4.40s`。Eight failures are exact
pre-existing CLI historical-rewind SHA tests；P1 must not add a failure or silently rewrite historical
baseline hashes。它应新增 P1 delta proof：从 candidate contract 删除 only P1 parser/handler
surface 后 exact match base `tests/fixtures/cli_contract.json` bytes/hash。Base fixture SHA-256 is
`13cb4f3b748fdf7dc1d91dfbb27d9a214d23dfff1112d253d0e01aa0c701ad3d`。

Fresh full base：

```text
2461 passed, 517 subtests passed, 9 failed in 65.41s
```

Ninth failure is existing
`tests/test_issue_cli.py::IssueCLIOwnershipTests::test_all_five_handler_ast_bodies_match_start_revision`。
Candidate full gate必须保持 exact nine-test failure set，无新增失败；P1-specific delta tests必须 PASS。

## 6. Planning conclusion

P1 should be one Coordinate-only reviewed package because exact reap、claim reap policy、transactional
online recheck 和 deactivate共享同一 SQLite/CLI/golden authority boundary。MultiNexus propagation
belongs to P2 to avoid half-deployed caller changes。Before implementation, write a detailed P1 plan,
obtain fresh independent exact-plan review, then generate and independently review a worker bootstrap。

P9_3C1_P1_MEASUREMENT_COMPLETE_IMPLEMENTATION_BLOCKED
