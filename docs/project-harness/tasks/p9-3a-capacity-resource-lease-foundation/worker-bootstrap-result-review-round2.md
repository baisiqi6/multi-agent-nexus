# P9-3A Codex Result Review Correction — Round 2

你是 P9-3A 的 coding correction worker。必须使用普通版
`kimi-code/kimi-for-coding`，不是 highspeed。你不是计划审核者或最终 reviewer；不得启动
subagent，不得调用 `task` tool/Codex，不得 push、merge、deploy、SSH、重启服务、写生产 DB、
修改 Coordinate harness 状态或执行 lifecycle closeout。

## 工作区、基线与已审核 gate

- Coordinate worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3a-kimi`
- MultiNexus worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3a-kimi`
- Coordinate correction-round-1 commit:
  `e78a7d1c6130a83ecb720f978a6379582f446896`
- MultiNexus correction-round-1 commit:
  `7ae3959d64316ee6d136a5efdaa0ded7fb0e3fff`
- Approved amended plan SHA-256:
  `d75486b42e8d3315bda488db1129e02c03c0a2c152c04a60cccce917a385d99e`
- Canonical `plan.ready`:
  `9a63f3ee-9135-4e12-8157-851a7fd99f4f`
- Canonical `plan.approved`:
  `246da1d6-473a-4093-86f1-f468a5d6d160`
- Independent amendment review: `zhipu-coding-plan/glm-5.2`, session
  `019f5cc0-83ff-7000-9d97-1a76b7f0e509`, verdict `APPROVED`.
- Plan:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3a-kimi/docs/project-harness/tasks/p9-3a-capacity-resource-lease-foundation/plan.md`
- Round-4 review:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3a-kimi/docs/project-harness/tasks/p9-3a-capacity-resource-lease-foundation/plan-review-round4.md`

先验证两个 worktree branch、HEAD 与 `git status --short`。MultiNexus 中上述 plan/review/
approval/bootstrap 文档应已由 operator 单独提交；不得改写 `plan.md`、plan review 或 approval
记录。只修复下列已确认 finding，不提前实现 P9-3B claim/heartbeat/reaper、P9-4 observation
或 P9-5 scheduler。

## R2-1 MUST_FIX — 真正恢复 first-rollout prior absence

当前 `scripts/deploy-server.sh` 在旧 accepted TOML 没有 capacity roots 时，只能验证旧
capacity 不存在；新 capacity sync 已成功而 committed verifier 随后失败时，它无法删除刚创建
的 projection。这不是 rollback。

按 amended plan 在 Coordinate `executor_capacity.py` 中实现内部、capacity-only、
digest-bound snapshot capture/restore；不得新增 public `runtime capacity restore` CLI，不得恢复
整库，也不得直接修改 roster/executor/jobs/events/leases。

### Snapshot v1 exact canonical contract

采用两层 exact-shape JSON envelope：

```json
{
  "snapshot": {
    "contract_version": 1,
    "target_source_id": "multinexus.discord.capacity",
    "captured_state": null
  },
  "snapshot_sha256": "<64 lowercase hex over canonical UTF-8 JSON bytes of snapshot>"
}
```

`captured_state` 非空时 exact shape 为：

```json
{
  "source": {
    "source_id": "...",
    "source_version": 1,
    "catalog_hash": "<64 lowercase hex>",
    "source_path": "... or null",
    "updated_at": "..."
  },
  "policies": [
    {
      "agent_id": "...",
      "source_id": "...",
      "source_version": 1,
      "catalog_hash": "<64 lowercase hex>",
      "capacity_policy_id": "sha256:<64 lowercase hex>",
      "max_concurrent_jobs": 1,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

- canonical bytes：UTF-8、`ensure_ascii=False`、`sort_keys=True`、compact separators；policies
  按 `agent_id` 排序；digest 只计算内层 `snapshot`，避免 self-reference；outer/inner/state/
  source/policy 均拒绝 unknown/missing fields。
- `target_source_id` 即使 prior absence 也必须显式保存；capture/restore 只允许 expected target。
- capture 必须拒绝数据库中 unexpected extra capacity source、orphan/mismatched policy、invalid
  source/policy id/hash/version/bounds/timestamp shape；非空 state 必须重算每个 policy id。
- snapshot 文件 secret-free，原子写入且最终 mode `0600`；fixed fixture 测试必须断言 exact bytes
  和 digest。不要假设动态 timestamp 的每次 capture bytes 相同。
- restore 自己拥有一个 `BEGIN IMMEDIATE`；先严格验证 envelope/digest/expected source；拒绝任何
  active lease；拒绝 current DB 中 unexpected/mismatched extra source。
- prior absence restore 只删除 expected target 的 policies/source；existing-state restore 精确恢复
  source 与 policies（含 captured timestamps/path），commit 前重新读取并与 snapshot exact compare。
- restore 失败必须 rollback 整个 transaction；roster/executor/jobs/events/leases byte/logical state
  不变。不得隐藏 commit，也不得返回“恢复成功”但留下 mismatch。

MultiNexus deploy 可以增加一个 focused internal operational helper 来 import 已安装 Coordinate
snapshot functions；它不属于 public runtime CLI。`deploy-server.sh` 必须：

1. 在 authority overwrite 前 capture previous capacity projection snapshot 到 mode-0600 temp file；
2. 保存并恢复 old authority；
3. 任一 post-overwrite parity、roster sync、executor sync、capacity sync/list、committed verifier
   失败时，按顺序恢复 old authority、old roster、old executor、capacity snapshot；
4. 对三套 projection 重新 verifier；restore 或 verifier 任一失败都 loud/nonzero；
5. 全部 accepted 前绝不写 version、restart、smoke；临时 snapshot 必须 trap-cleanup。

Fault-injection tests 至少覆盖：existing capacity restore、prior absence first rollout 在 capacity
sync 成功后 verifier 失败、sync 原子失败、snapshot tamper/wrong source/malformed、active lease、
restore 自身失败；断言 roster + executor + capacity 三者恢复且无 version/restart/smoke。
P9-3A production safety 仍要求 zero active lease；在 implementation report 明确 P9-3B 在 capacity
成为 claim authority 前必须替换这一临时前提。

## R2-2 MUST_FIX — stored resource snapshot 仍接受非 canonical 数据

`execution_resources.validate_resource_key_matches()` 当前只检查 object shape/version/kind 后按原值
算 digest，仍会接受 `host_id=" host "`、relative path 或非 canonical path，只要 attacker 同步
重算 key。

- full-match `resource_key`：`^sha256:[0-9a-f]{64}$`；
- stored `host_id` 复用 strict `_validate_host_id`；
- stored `normalized_path` 复用 `normalize_worktree_path()`，并要求 normalizer 输出与 stored bytes
  exact 相同；不得 silent strip、realpath、filesystem probe；
- 拒绝 non-string、relative、control/NUL、overbound、non-canonical UNC/drive/POSIX、uppercase/
  truncated/nonhex digest；
- 添加 direct validator 与 lease read-path tamper tests，证明 zero write。

## R2-3 MUST_FIX — bulk/decision lease 路径绕过 stored validation

以下路径必须在同一个 caller-owned transaction 内先读取将要消费/计数/更新的完整 lease rows，
逐行调用统一 stored snapshot validator，再做任何 decision 或 write：

- `_expire_due_for_agent_or_resource`
- `expire_due_attempt_leases`
- `count_active_leases_for_agent`
- `_find_active_resource_lease`

不得通过 `COUNT(*)` 或 partial SELECT 绕开 malformed row。一个 candidate 损坏时整个 operation
fail closed，任何 lease 不得部分 expire。补测试：malformed due row 与 valid due row 同时存在时，
bulk expire 零写；capacity count 与 resource collision 也拒绝 tamper。

## R2-4 MUST_FIX — malformed job payload 必须成为 LeaseError

`reserve_attempt_lease()` 的 `json.loads(job["payload_json"])` 必须捕获 JSON decode、bytes/type
错误并转换成稳定的 `LeaseError`（保留原因链即可），在任何 lease write 前失败。覆盖 malformed
JSON、JSON scalar/list、missing execution_context。

## R2-5 MUST_FIX — 删除 sibling-worktree 假测试

`test_parse_accepts_real_multinexus_registry` 依赖
`REPO_ROOT.parent / "multinexus-p9-3a-kimi"` 并在缺失时 skip，不可移植。

- 用 committed hermetic full-shared-TOML fixture 或测试内完整 fixture 证明已知共享根可解析；
- 不能引用 sibling checkout，不能 skip；
- cross-repo 真实 `config/agent-registry.toml` parity 作为 operator integration command/report evidence，
  不伪装成仓库单测。

## R2-6 MUST_FIX — 报告区分 raw fixture SHA 与 canonical catalog hash

两个仓库 `tests/fixtures/capacity_catalog_v1.json` 的 raw file SHA-256 是：
`2ae67c8d123b2e1b2165e42b498c7a470418b8bad4a9cefd2ac88379cc94fd2a`。

由 canonical catalog object 计算的 `catalog_hash` 是：
`3c5b31d17424f3dc12b56d5e0d545f5a46b7d212193465d79c874cb82a9a918d`。

修正 `implementation-report.md`，不得再把后者称为 fixture file SHA。报告追加 Round 2
finding -> fix -> tests、snapshot contract/rollback evidence、exact test commands/counts、known baseline
和 residual risk。不要改动 raw fixture bytes，除非能证明 plan 必需且两仓同步。

## 实施与验证

1. 先补 focused failing tests，再做 surgical implementation；避免大重构。
2. Coordinate focused 至少运行：
   `tests/test_executor_capacity.py tests/test_execution_resources.py tests/test_execution_leases.py tests/test_db.py tests/test_execution_cli.py`。
3. Coordinate full：
   `PYTHONPATH=src python -m pytest tests/ --import-mode=importlib -q`。
   当前历史 baseline 仅允许 8 个 CLI contract hash + 1 个 issue AST；如果本轮合法 module surface
   变化使 AST fixture 必须更新，须精确解释，不得笼统归为 baseline。
4. Multi focused 至少运行：
   `tests/test_executor_capacity_authority.py tests/test_deploy_contract.py tests/test_smoke_contract.py`。
5. Multi full：
   `PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest tests -q`。
6. 运行两仓 `git diff --check`、Python `compileall`，以及 deploy/helper `bash -n`（如适用）。
7. 两仓分别新建 Round-2 correction commit，不 amend 旧 commit，不包含 operator 的 plan/review/
   approval/bootstrap commit，不 push/deploy。
8. 最终报告：两个新 commit SHA、逐项 finding closure、测试 exact command/count、known baseline、
   modified files，以及任何真实 unresolved item。不得声称生产验证；最终 acceptance 由 Codex 完成。

如果实现需要改变 `plan.md`、新增 public restore CLI、恢复整个 DB、提前实现 P9-3B/P9-4/P9-5，
立即停止并报告 blocker，不自行扩 scope。
