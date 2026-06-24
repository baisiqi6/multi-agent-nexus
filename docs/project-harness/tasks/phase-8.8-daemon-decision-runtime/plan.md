# Phase 8.8 Daemon decision= Runtime Path（可见性核心）

## Ownership and branches

- Operator: 我（Claude Code）
- Reviewer: `opencode` / `mac-claude`
- Worker: `omp` / `mac-opencode`
- Task id: `phase-8.8-daemon-decision-runtime`
- branch: `agents/mac-omp/phase-8.8-daemon-decision-runtime`，from `agents/mac-claude/phase-8.4.2-contracts-function-decomposition`（含 phase-8.4.4/8.5/8.6/8.7）
- Human gates: merge, deploy, force-push, branch protection, real GitHub PR write

## Goal

runtime job 的 `[agent-report] decision=/action=` 自动解析 → `review.completed`/`closeout.requested` + 投递 Discord 可见 + operator 收到。**解决"review 在 Discord 看不到 + operator 手动挖 job list"**——这是用户最初诉求的最终一块。

## Current pressure（基于 phase-8.6 report_job_result runtime.py:376）

- `report_job_result` 创建 `agent.reported`(source=runtime)，但：
  - `action` 只基于 job status（done/blocker），**没解析 `result.response_text` 里的 `[agent-report] decision=approve/reject`**
  - `agent.reported` payload 没 `decision` 字段
  - 没触发 `review.completed`/`review.rejected`（只 `agent.reported` event）
- daemon `_parse_agent_report`（phase-8.5 must-fix-5）解析 **Discord 消息**的 `[agent-report] decision=`，但 runtime 路径（`report_job_result`）没接同一解析。
- 后果（phase-8.5/8.6/8.7 实测）：opencode/mac-claude 的 review 意见（response_text 含 `[agent-report] decision=approve`）埋在 job result，`agent.reported` 没 decision，`review.completed` 不自动（fallback `progress.reported`），**Discord 看不到 review 意见，operator 手动 `job list` 挖**。

## Workstream A — report_job_result 解析 [agent-report] decision=

- `report_job_result` 解析 `result.response_text` 的 `[agent-report]` 块——复用 daemon `_parse_agent_report` 的解析逻辑（提取为共享 helper，避免重复），取 `decision=approve/reject` + `action=done/blocker/progress` + `summary`。
- `agent.reported` payload 加 `decision` 字段（+ 保留 raw `action`）。
- 若 response_text 无 `[agent-report]` 块（如 "(no response)"），保持 phase-8.6 现状（action 按 job status）。

## Workstream B — decision= → review.completed / closeout

- `report_job_result`（或 daemon pump runtime `agent.reported`）：
  - `decision=approve` → `review.completed`（reviewer approve 自动落 lifecycle）
  - `decision=reject` → `review.rejected`（反馈 operator/worker 修）
  - 无 decision + `action=done`（worker 实现完成，非 review）→ phase-8.6 `awaiting_operator`（半自动，operator 推进 closeout）
- 与 phase-8.6 `awaiting_operator` 协调：review decision 不进 awaiting，直接 review.completed/rejected；worker done 仍 awaiting_operator。

## Workstream C — agent.reported delivery 投递 Discord（可见）

- `agent.reported`(source=runtime) 含 decision/review 意见 → policy 渲染 delivery 投递 Discord（**review 意见可见**，不只 `[agent-report]` 卡片）+ operator 收到。
- 解决 review 意见 Discord 看不到——agent 的 review 内容（summary + decision）自动到 Discord + operator。

## dogfood

本 task plan/code review 走 reviewer handoff，验证：
- `review.completed` **自动**（不再 fallback progress.reported）
- Discord **可见** review 意见（opencode review 内容到频道）
- operator **收到**（不挖 job list；`operator pending` 或 delivery 看到）

## Non-goals

- 不改 Discord 路径 `agent.reported`（已工作）。
- 不改 reviewer handoff（phase-8.5）。
- 不改 phase-8.6 `awaiting_operator`（半自动；review decision 走 review.completed，worker done 走 awaiting_operator）。
- 不做 worker self-test 硬 gate（#7 结论指向的，另立 task）。

## Reviewer round-1 notes（opencode via reviewer handoff，Approve + 6 must-fix，closeout 前落实）

- **must-fix-1 self_test_evidence**：closeout 前必须 deploy SHA + raw e2e 输出，e2e 覆盖 `decision=approve` **和** `decision=reject` 两条 runtime 路径。引用 phase-8.7 硬 gate 结论（软提醒不够）。
- **must-fix-2 idempotency key**：runtime `agent.reported` 带 source-specific key（`runtime:job:{job_id}:agent-reported:{decision}`），防与 Discord 路径重复触发。
- **must-fix-3 测试清单**：parse helper 单测 + lifecycle transition（approve/reject/done）+ delivery 渲染 + 无 `[agent-report]` fallback 测试。
- **must-fix-4 malformed decision**：malformed/unknown `decision=` fail loud（不静默 fallback）。
- **must-fix-5 open q 落定**：解析 helper 抽到**共享 module**（daemon + runtime 复用，避免重复）；触发点放在 `report_job_result`（边界简单）；review 意见 delivery 复用 `review.completed` renderer。
- **must-fix-6 循环保护**：runtime 触发的 `review.completed` 绝不再触发 reviewer handoff（reviewer decision 只推进 lifecycle 给 operator，不回 reviewer）。
