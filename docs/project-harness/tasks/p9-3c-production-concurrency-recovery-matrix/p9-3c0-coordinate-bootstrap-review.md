# P9-3C0 Coordinate Capacity-Source Decoupling — Implementation Bootstrap Review

Reviewer: Claude independent exact-revision bootstrap reviewer (sonnet)  
Verdict: **APPROVED_FOR_P9_3C0_COORDINATE_WORKER_LAUNCH**

Reviewed bootstrap SHA-256:  
`3c6cbfeb6d96bbba8b4a6fbe87eab1d8b99bcbeb6e49750e63df69582c7cbdbb`

## Scope

仅读取以下五个文件：

- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-coordinate-implementation-bootstrap.md`
- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-plan.md`
- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-plan-review-round3.md`
- `/Users/yinxin/projects/coordinate/src/coordinate/executor_capacity.py`
- `/Users/yinxin/projects/coordinate/src/coordinate/schema.py`

仅创建本 review 文件。未执行 Bash/ls/rg、subagent、TaskCreate、测试、provider、git、deploy、SSH、DB、service、job 或 lease 操作。

## Findings

- P0：无。
- P1：无。
- P2（worker / Codex verification items）：
  - 当前 `sync_capacity_catalog` 的 active-lease guard（`executor_capacity.py:349-355`）仅检查被移除的 `agent_id`，未检查因 `source_version` / `catalog_hash` / `max_concurrent_jobs` 变化导致 `capacity_policy_id` 替换的旧 policy id。worker 必须按 bootstrap #5 实现“旧 policy id 集合 vs 新 policy id 集合”的完整比较，并在 Required tests #8 中覆盖。
  - `capture_capacity_snapshot` / `restore_capacity_snapshot` 当前拒绝任何非目标 source 的 policy。multi-source 实现后，若 fixture capacity source 已存在，canonical source 的 snapshot 行为会变化；worker 完成 `sync_capacity_catalog` 后应确认是否需要在本文件内兼容或文档化该限制。
  - 确保每个 zero-mutation 测试在调用前后 snapshot `executor_capacity_sources` 与 `executor_capacity_policies` 的相关行，并做逐字段比较，而非仅断言异常文本。
  - 确保 `sync_capacity_catalog` 在 same-version/same-hash 路径上仍按 bootstrap 要求重新验证 global ownership / known-binding / union invariants。
  - 确保 `added_policy_ids` / `updated_policy_ids` / `removed_policy_ids` / `unchanged_policy_ids` 返回结果保持确定性排序与现有字段名不变。

## Bootstrap vs current code consistency

- **Exact repo / branch / worktree 边界**：bootstrap 限定在单一 Coordinate repo（`/Users/yinxin/projects/coordinate`），分支 `agents/mac-claude/p9-3c0-capacity-source-decoupling-coordinate`，孤立 worktree `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3c0-capacity-source-decoupling`；不与 MultiNexus / Package 2/3 混用。符合单 repo 边界。
- **Schema 边界**：`schema.py` 中 `executor_capacity_policies` 已存在 `source_id TEXT NOT NULL`，且 `agent_id` 为 PRIMARY KEY；无需新增列或迁移。ownership 由现有 `source_id` 表达，符合 bootstrap “Do not add a column or schema migration”。
- **Union coverage**：bootstrap 的 post-sync union = 其他 source 的现有 policy agents ∪ 本 source 的 proposed agents；要求覆盖所有 `enabled=1` typed executor bindings；允许 disabled typed bindings 的 policy；拒绝 unknown / untyped ids。当前代码为 single-source complete coverage，worker 按 bootstrap 扩展即可。
- **Cross-source takeover**：由 ownership guard 在写入前拒绝，结合 `agent_id` PRIMARY KEY 的 DB 级唯一约束作为 fail-safe，实现零写入。
- **Active lease guard**：bootstrap 明确要求比较旧 source 的 policy id 集合与新 source 的 policy id 集合，覆盖 removal 与 version / hash / capacity 导致的 replacement；当前代码尚未满足，但实现路径清晰，对应 Required tests #7/#8。
- **Same-version / same-hash**：bootstrap 要求 exact retry 仍重验 global invariants；当前代码在 exact retry 前已重验 missing / extra，worker 需将其扩展为 union / ownership / known-binding 重验。
- **Empty source cleanup / deterministic result / zero-mutation tests**：bootstrap 定义充分；worker 按 #6 与 Required tests #9–#11 实现即可。
- **Worker 动作限制**：bootstrap 明确限制为本地 commit，禁止 push / merge / deploy / service 重启 / Package 2 / 生产 DB 或 job/lease 操作。

## Authorization boundary

本 verdict 仅批准 **Package 1 Coordinate capacity-source decoupling worker 开始编码**。

不授权：

- merge、push、deploy、service 重启；
- 修改 schema、migration、executor identity / routing / runtime、doctor / projection、docs、packaging、deploy scripts；
- Package 2 / Package 3 启动或并行修改；
- 生产 DB 操作、生产 fixture activation、job / lease 创建；
- 除本地 commit 外的任何 git 写操作。

worker 完成后须通过独立的 exact-revision review，方可进入下一步。
