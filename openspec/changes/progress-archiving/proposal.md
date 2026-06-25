## Why

`docs/project-harness/` 是项目 source-of-truth：harness state、checklist、当前 blocker/closeout packet 都集中在这里，用于协调多 agent 与 operator 的工作状态。经过 Phase 8 密集迭代（8.3.1–8.8），活跃目录积累了大量已完成 phase 的中间产物（plan.md、worker-bootstrap.md、test 片段、runtime 产物引用）。这些文件已不再影响当前工作，却仍出现在 `current/`、`tasks/` 的根路径，导致：

- operator 打开目录时难以快速定位**当前活跃任务**；
- worker/reviewer handoff 的 bootstrap 容易引用到已完成任务的旧 plan 或旧测试基线；
- 归档历史缺少统一规则，drift 和重复搬运风险随 phase 数量线性增长。

本变更建立一套轻量、可自动化的 progress 归档机制：phase closeout 后把相关产物移入 `docs/project-harness/archive/<phase-id>/`，同时在活跃目录保留一个稳定的 `index.md` 指针。这样 active workspace 保持最小，历史仍可追溯。

## What Changes

- 在 `docs/project-harness/` 下新增 `archive/` 目录结构约定。
- 定义归档触发条件：task 进入 `closed`/`done` 状态且 `closeout` packet 已记录。
- 新增 CLI 子命令 `coordinate task archive <workspace-id> --task-id <phase-id>`：
  - 把 `tasks/<phase-id>/` 下所有文件复制到 `archive/<phase-id>/`；
  - 在 `archive/<phase-id>/` 生成 `INDEX.md`，记录原始路径、closeout event id、closed_at、相关 commit SHA；
  - 将 `tasks/<phase-id>/` 替换为一个 stub `README.md`，指向 `archive/<phase-id>/`；
  - 更新 `docs/project-harness/current/` 中仍指向旧路径的 packet（若存在）。
- 修改 `harnessctl`（bash ~line 269）+ `build_harness_state.py` + `workflow_transition.py`：识别 `tasks/<id>/README.md` archive stub，从 `archive/<id>/plan.md` 解析 plan（详见 tasks 4.1）。
- `assignment mark-done --archive` 自动归档**不在本次变更**（Phase 2 后续，见 design Migration Plan）；本次只做显式 `coordinate task archive` 命令。
- **BREAKING**：外部脚本若直接硬编码读取 `tasks/<phase-id>/plan.md`，需要改为解析 stub README 中的 archive 指针，或直接读 `archive/<phase-id>/plan.md`。

## Capabilities

### New Capabilities

- `task-archive`: 安全迁移已完成 phase 的产物到 archive，并生成索引指针。
- `archive-index`: 在活跃目录保留轻量 stub，指向归档副本，保证旧链接不 404。

### Modified Capabilities

- `harness-validation`: 校验规则需把 archive stub 视为合法路径；若 task 状态为 closed 但 archive 索引缺失，可降级为 warning（保留兼容）。

*(task-mark-done `--archive` 自动归档是 Phase 2，不在本次 scope，见 design Migration Plan)*

## Impact

- `coordinate` CLI 增加 `task archive` 命令与测试。
- `scripts/harness/harnessctl validate` 需识别 archive stub。
- `docs/project-harness/` 目录结构多一层 `archive/`，不影响现有未关闭 task。
- 生产部署脚本（`deploy-server.sh`）无需改动，archive 是普通文本文件。
