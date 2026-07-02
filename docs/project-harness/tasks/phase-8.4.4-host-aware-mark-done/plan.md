# Phase 8.4.4 Host-Aware Mark-Done (Reconcile Drift)

## Ownership and branches

- Operator / reviewer: `opencode`（codex 已限额，接力 reviewer；round-1 plan review 给出 REJECT + 4 must-fix，本版为 round-2 修订）
- Coding agent (worker): `omp`（首次以 worker 身份干实活，dogfood 压力测试）
- Task id: `phase-8.4.4-host-aware-mark-done`
- coordinate branch: `agents/<owner>/phase-8.4.4-host-aware-mark-done`，from 当前活跃分支
- Human gates: merge, deployment, deletion, force-push, branch protection, 任何真实 GitHub PR write。

## Goal

照 `materialize` 的 host-aware 拆分模式，给 `assignment mark-done` 补上本地/云端分离：

- `mark-done-files`：在 coding host 本地写 `mvp-checklist.json`（标 done），**不碰云端 DB**。
- `mark-done-record`：经 `coord-ssh` 幂等写云端 DB 的 `task.done` event，**不碰任何 harness 文件（本地或 /opt）**。

目标是让 operator 能 reconcile 当前 checklist drift：对那些云端 DB 已 done、本地 checklist 仍 `todo` 的历史 task，走一次受控的 host-aware lifecycle，让本地 git source 对齐生产状态，而不必破例直接改 JSON 或裸调 harnessctl。

## Current pressure

- `assignment mark-done` 是单命令，远端 workspace `discord-nexus` 的 `harness_root=/opt/multinexus/...`，`mark_done_task` (transitions.py:965) 调 `adapter.run_mutation("mark-done")` → harnessctl → 改 `/opt` 副本 + 写 `task.done` event，本地 git checklist 不被更新（drift 根因，见 `operator-needs-backlog.md` 2026-06-22 A1 条）。
- 对已 done 的 task 重跑 `coord-ssh assignment mark-done` 是 no-op（`mark_done_task` 的 idempotency_key 命中 `task.done`），连 `/opt` 副本都不改。
- `materialize` 的 `materialize_issue_files` (issues.py:802) / `materialize_issue_record` (issues.py:870) 已验证 host-aware 拆分可行：files 侧用 `--workspace-path`/`--harness-root`（不连 DB），record 侧 inline `conn.execute`/`append_event`（**不调 adapter.run_mutation、不碰文件**）。本 task 直接参照这两个边界。

## Workstream A — `mark-done-files`（本地侧，特权绕 gate 工具）

> **⚠️ 特权 operator 工具**：`mark-done-files` 直接把 checklist item 写成 `status=done` + `workflow.status=closed`，**绕过 `_check_mark_done_gate` 的 review 前置检查**。这与 operator 直接编辑 JSON 同级别特权，但走受控 CLI（有审计、有 `/opt` guard）。它的前提是 operator 已通过别的手段（host-aware lifecycle 的 record 侧、或该 task 已在生产 DB done）确认任务确实完成。类比 `materialize-files` 的 `/opt` guard，必须把"绕 gate"显式化，避免被误读为正常 lifecycle 语义（must-fix-4）。

参照 `materialize_issue_files` (issues.py:802) 的边界：

- **入参（must-fix-1）**：`assignment mark-done-files --workspace-path <path> --harness-root <root> --task-id <id> [--actor <actor>] [--verification <text>] [--allow-runtime-copy]`。**无 `workspace_id`、不连 DB**（与 materialize-files 一致），用显式 `--workspace-path` + `--harness-root` 定位本地 checklist。
- 行为：读 `--harness-root` 下的 `mvp-checklist.json`，把对应 item 标 `status=done` + `workflow.status=closed` + 写 `verification` 字段；**不写 DB、不发 event**。
- `/opt` guard：`--workspace-path`/`--harness-root` 落在 `/opt/` 下（部署副本）时拒绝，提示走 host-aware 流程，除非显式 `--allow-runtime-copy`（与 materialize-files 一致）。
- 失败闭合：task 不在 checklist 时报错。

### Workstream A 验收（具体测试条目）

- 写入：item 变 `status=done` + `workflow.status=closed` + `verification` 非空。
- `/opt` 路径拒绝（无 `--allow-runtime-copy`）；带 `--allow-runtime-copy` 放行。
- task 不在 checklist → 报错。
- 幂等：已 done 的 item 重跑 no-op（无重复写入）。
- DB 零写入（断言无 event 产生）。

## Workstream B — `mark-done-record`（云端侧，inline 不碰文件）

> **关键约束（must-fix-2）**：`mark-done-record` **不调用 `mark_done_task`、不调用 `adapter.run_mutation`**——因为 `mark_done_task` (transitions.py:965) 会 `adapter.run_mutation("mark-done")` → harnessctl → 写 `/opt` checklist 文件，违背"不碰任何 harness 文件"。必须像 `materialize_issue_record` (issues.py:870) 那样 **inline 操作**：直接 `conn.execute` / `append_event("task.done", ...)`，文件零触碰。

参照 `materialize_issue_record` 的边界：

- 入参：`assignment mark-done-record <workspace_id> --task-id <id> --actor <actor> [--verification <text>] [--idempotency-hint <hint>]`。
- 行为：在云端 DB inline 写 `task.done` event（`append_event`，**不调 adapter.run_mutation**）；**不碰任何 harness 文件（本地或 /opt）**。
- **幂等（宽匹配，must-fix-3）**：不只依赖精确 `idempotency_key`。先扫描该 task 的所有 prior `task.done` event（按 `workspace_id` + `task_id` 匹配，**忽略 actor**——drift task 的历史 `task.done` 可能是别的 actor 如 `omp` 写的）；若已存在任意 `task.done`，返回那条作为 no-op（`event_created=false`），不创建第二个。参照 `materialize_issue_record` 扫描 prior `issue.materialized` 的做法 (issues.py:944-981)。
- gate：可选用 `_check_mark_done_gate` 读 `/opt` checklist 出诊断信息，但**不作为硬前置**（record 侧可能 /opt checklist 还没 sync，gate 会假阴——见 C2）。gate 信息出现在输出里但不阻断 record（record 的职责是写 DB event，文件 gate 由 files 侧负责）。

### Workstream B 验收（具体测试条目）

- 新 task → 写一个 `task.done` event。
- task 已有 `task.done`（任意 actor，含 `omp`）→ `event_created=false`，返回既有 event，**无论 `--idempotency-hint` 是什么**。
- 本地 + `/opt` checklist 文件零变更（断言 `adapter.run_mutation` 没被调）。
- gate 诊断信息出现但不阻断 record（exit 0）。

## Workstream C — reconcile 操作手册 + legacy 竞态警告

- 在 `docs/runbook.md` 写明 reconcile drift 的标准流程：`mark-done-files`（coding host 写本地 checklist）→ commit/push → `deploy-server.sh multinexus`（把 checklist 同步到 /opt）→ `mark-done-record`（coord-ssh 写云端 DB）→ `coord-ssh state` / `event list` 验证。
- **⚠️ legacy 竞态警告（次要建议）**：runbook 必须警告——在 `mark-done-files` 和 `mark-done-record` 之间**不要**运行 legacy `assignment mark-done`，否则它会调 harnessctl 可能在 /opt 创建重复 `task.done` 或破坏中间状态。
- 不改 `assignment mark-done` 既有语义（保留为兼容入口）。

## Non-goals（重要——C1 勿忘，但本 task 不做）

- **不做 C1**：不抽象通用 "host-aware mutation" 框架。本 task 只给 mark-done 再做一次手工拆分（参照 materialize）。C1 作为独立后续 task，在第二个真实案例（materialize + mark-done）都落地后再抽通用机制——两个案例比一个更能暴露正确抽象边界。见 `operator-needs-backlog.md` 2026-06-22 C1 条。
- 不改 SQLite schema、event 类型、payload 字段、既有 CLI 参数/退出码/JSON、Discord 文案、harness lifecycle 语义。
- **不改 `_check_mark_done_gate` 的 status-based 设计为 event-based（C2，另立）**；本 task 的 `mark-done-record` gate 只作诊断不阻断（C2 落地后再收紧）。
- 不安装新依赖，不引入 DI 框架。

## Validation

- coordinate 全量测试通过（当前基线 1087）+ Workstream A/B 列举的具体测试条目。
- multinexus 全量测试通过（当前基线 319）。
- `harnessctl validate` / `doctor` 通过；`git diff --check` 干净。
- 真实 reconcile dogfood：选一个云端已 done、本地 todo 的 drift task，走 host-aware 流程，验证本地 checklist 标 done 且云端 DB 无重复 `task.done`。

## Done criteria

- `mark-done-files`（`--workspace-path`/`--harness-root` 签名，特权绕 gate）+ `mark-done-record`（inline、宽幂等、不碰文件）实现并有 Workstream A/B 的测试覆盖。
- operator 能用它 reconcile 至少一个真实 drift task，本地 git checklist 对齐云端 DB，全程不直接改 JSON、不裸调 harnessctl、无重复 `task.done` event。
- runbook 写明流程 + legacy 竞态警告。

## Review history

- round-1 (opencode, 2026-06-22, job request:77dfeba3): REJECT + 4 must-fix —— ① `mark-done-files` 签名要用 `--workspace-path`/`--harness-root`（无 workspace_id）；② `mark-done-record` 不能复用 `mark_done_task`（会 `adapter.run_mutation` 写 /opt 文件），要 inline `append_event`；③ 幂等要扫描 task 所有 prior `task.done`（忽略 actor），不能只精确匹配 key；④ `mark-done-files` 绕 gate 要显式标注为特权工具。次要：runbook 加 legacy 竞态警告、列举具体测试条目、说明 gate 假阴（C2）。已在本版 Workstream A/B/C 落实。
