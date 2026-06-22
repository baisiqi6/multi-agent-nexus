# Phase 8.4.4 Host-Aware Mark-Done (Reconcile Drift)

## Ownership and branches

- Operator / reviewer: `opencode` 或 `omp`（codex 已限额，接力当 reviewer）
- Coding agent (worker): `omp`（首次以 worker 身份干实活，dogfood 压力测试）
- Task id: `phase-8.4.4-host-aware-mark-done`
- coordinate branch: `agents/<owner>/phase-8.4.4-host-aware-mark-done`，from 当前活跃分支
- Human gates: merge, deployment, deletion, force-push, branch protection, 任何真实 GitHub PR write。

## Goal

照 `materialize` 的 host-aware 拆分模式，给 `assignment mark-done` 补上本地/云端分离：

- `mark-done-files`：在 coding host 本地写 `mvp-checklist.json`（标 done），**不碰云端 DB**。
- `mark-done-record`：经 `coord-ssh` 幂等写云端 DB 的 `task.done` event，**不碰本地 checklist 文件**。

目标是让 operator 能 reconcile 当前 checklist drift：对那些云端 DB 已 done、本地 checklist 仍 `todo` 的历史 task，走一次受控的 host-aware lifecycle，让本地 git source 对齐生产状态，而不必破例直接改 JSON 或裸调 harnessctl。

## Current pressure

- `assignment mark-done` 是单命令，远端 workspace `discord-nexus` 的 `harness_root=/opt/multinexus/...`，`HarnessAdapter` 调远端 harnessctl 改 `/opt` 副本，本地 git checklist 不被更新（drift 根因，见 `operator-needs-backlog.md` 2026-06-22 A1 条）。
- 对已 done 的 task 重跑 `coord-ssh assignment mark-done` 是 no-op（`mark_done_task` 的 idempotency_key 命中 `task.done`），连 `/opt` 副本都不改。
- `materialize` 的 `materialize-files` / `materialize-record` 已验证 host-aware 拆分可行，可直接参照其边界与 `/opt` guard。

## Workstream A — `mark-done-files`（本地侧）

参照 `materialize_issue_files` 的边界：

- 入参：`assignment mark-done-files <workspace_id> --task-id <id> [--actor <actor>] [--verification <text>]`。
- 行为：读本地 workspace `harness_root` 指向的 `mvp-checklist.json`，把对应 item 标 `done` + workflow `closed` + verification 字段；**不写云端 DB、不发 event**。
- 失败闭合：task 不在 checklist、或 workspace 路径在 `/opt/` 下（部署副本）时拒绝，错误信息指向 host-aware 流程（参照 materialize-files 的 `/opt` guard）。
- 验收：本地 checklist item 标 done；无 DB event 写入；`/opt` 路径 fail-closed；幂等（已 done 的 item 再跑 no-op）。

## Workstream B — `mark-done-record`（云端侧）

参照 `materialize_issue_record` 的边界：

- 入参：`assignment mark-done-record <workspace_id> --task-id <id> --actor <actor> [--idempotency-hint <hint>]`。
- 行为：经现有 `mark_done_task` 在云端 DB 幂等写 `task.done` event（复用 idempotency_key + gate）；**不碰任何本地 harness 文件**。
- 对已 done 的 task 幂等返回 `event_created=false`，不报错。
- 验收：已 done task 幂等 no-op；新 task 写 `task.done`；本地 checklist 文件零变更；gate fail 时 exit 1。

## Workstream C — reconcile 操作手册

- 在 `docs/runbook.md` 写明 reconcile drift 的标准流程：`mark-done-files`（coding host）→ commit/push → `deploy-server.sh` → `mark-done-record`（coord-ssh）→ `coord-ssh state` / `event list` 验证。
- 不改 `assignment mark-done` 既有语义（保留为兼容入口）。

## Non-goals（重要——C1 勿忘，但本 task 不做）

- **不做 C1**：不抽象通用 "host-aware mutation" 框架。本 task 只给 mark-done 再做一次手工拆分（参照 materialize）。C1 作为独立后续 task，在第二个真实案例（materialize + mark-done）都落地后再抽通用机制——两个案例比一个更能暴露正确抽象边界。见 `operator-needs-backlog.md` 2026-06-22 C1 条。
- 不改 SQLite schema、event 类型、payload 字段、idempotency key、既有 CLI 参数/退出码/JSON、Discord 文案、harness lifecycle 语义。
- 不改 `_check_mark_done_gate` 的 status-based 设计为 event-based（C2，另立）。
- 不安装新依赖，不引入 DI 框架。

## Validation

- coordinate 全量测试通过（当前基线 1087）+ 新增 `mark-done-files`/`mark-done-record` 覆盖。
- multinexus 全量测试通过（当前基线 319）。
- `harnessctl validate` / `doctor` 通过；`git diff --check` 干净。
- 真实 reconcile dogfood：选一个云端已 done、本地 todo 的 drift task，走 host-aware 流程，验证本地 checklist 标 done 且云端 DB 无重复 event。

## Done criteria

- `mark-done-files` + `mark-done-record` 实现并有测试覆盖。
- operator 能用它 reconcile 至少一个真实 drift task，本地 git checklist 对齐云端 DB，全程不直接改 JSON、不裸调 harnessctl。
- 文档（runbook）写明流程。
