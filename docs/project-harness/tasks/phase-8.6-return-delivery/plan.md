# Phase 8.6 Return Delivery (agent done → pending operator action)

## Ownership and branches

- Operator: 我（Claude Code）
- Plan / code reviewer: `opencode` / `mac-claude`
- Worker: `omp`
- Task id: `phase-8.6-return-delivery`
- branch: `agents/mac-omp/phase-8.6-return-delivery`，from `agents/mac-claude/phase-8.4.2-contracts-function-decomposition`（含 phase-8.4.4）
- Human gates: merge, deploy, force-push, branch protection, real GitHub PR write

## Goal

agent（reviewer/worker）完成 → 创建 `agent.reported` event + 记 **pending operator action** → operator 会话查 pending 推进（**不手动轮询 job list**）。半自动：agent done 不立即推进，等 operator（保留人判断 review/deploy 等关键点）。

## Design decision（用户定）：半自动 pending operator action

- agent done → `agent.reported` event + pending operator action（task 进入 `awaiting_operator`）
- operator 一条命令查所有 pending → 推进（approve/reject/advance）
- 不自动 handoff（operator 人判断推进）
- 对比全自动 operator loop：保留人判断，避免 review/deploy 自动化的风险

## Current pressure（基于勘察）

- `agent.reported` event 已在 `SUPPORTED_EVENT_TYPES`（policy.py:13），daemon 解析 `[agent-report]`（Discord 路径）创建 event（daemon.py:240）+ delivery。
- **但 runtime request 路径的 job done 不创建 `agent.reported`**——`report_job_result` 只更新 job row，job result 落 DB，不产 event、不 delivery。两路径不统一，runtime 路径"哑"。
- 后果（phase-8.4.4/8.5 实证）：omp job done 后 operator 必须手动 `job list` 轮询才发现；agent 完成 45min 没 closeout/通知 operator。
- 无 pending operator action 概念——operator 查"待推进"要拼 event + task 状态，没一等命令。

## Workstream A — 统一 runtime 路径 → agent.reported

- runtime request job terminal（done/failed）→ 创建 `agent.reported` event（payload: job_id, task_id, agent, status, result_summary）。
- 触发层：`report_job_result`（agentd 报告时）写入，或 daemon 监听 job terminal（plan review 定）。
- 与 Discord 路径统一（都产 `agent.reported`），policy 渲染 delivery（可见）。

## Workstream B — pending operator action

- `agent.reported`（action=done / job terminal）→ task 进入 `awaiting_operator`（或新 `pending_operator_actions` 表，plan review 定）。
- operator CLI：`coordinate operator pending <workspace>`（或 `state --pending`）列所有待推进 task + 待办动作（approve plan / review code / advance / mark-done）。
- operator 推进：复用现有 `plan approve` / `assignment review-result` / `task handoff` / `mark-done`（不新造推进命令，pending 只是指引"该 operator 做什么"）。

## Workstream C — dogfood

- phase-8.6 自己的 omp job done → `agent.reported` → pending → operator（我）查 pending 推进（验证不手动 `job list` 轮询）。
- phase-8.5 的 omp job done（已完成但没 closeout）也该被 pending 捕获——回填验证。

## Non-goals

- **不做全自动 operator loop**（保留人判断；routine 自推 + 关键点人判 的混合模式留后续 task）。
- 不自动 handoff/advance（operator 推进）。
- 不改 Discord 路径既有 `agent.reported` 解析（只让 runtime 路径接入）。
- 不改 SQLite schema 破坏性（pending 用 task phase 或新表，plan review 定）。

## Validation

- coordinate 全量测试 + 新测试：runtime job terminal → `agent.reported` event；`agent.reported` → pending；`operator pending` 命令。
- multinexus：agentd report_job_result 触发（如选 agentd 层）。
- e2e：omp job done → `agent.reported` → pending → `operator pending` 列出 → operator 推进（不手动 job list）。

## Done criteria

- runtime job done 产生 `agent.reported` event（两路径统一），不再"哑"。
- operator 用一条命令查 pending 推进，不手动 `job list` 轮询。
- phase-8.6 / phase-8.5 的 omp job done 都被 pending 捕获。

## Round-1 review decisions（opencode round-1 APPROVE，open questions 已定）

- **(a) 触发层 = `report_job_result`（agentd 层）**。daemon 不监听 job terminal（加 listener 复杂）；`report_job_result` 已有 agent_id/task_id/workspace_id/result summary，在那里 emit `agent.reported` 最小幂等。
- **(b) pending 存储 = `task.phase = awaiting_operator`**。不新建表；phase 已和 harness state reconcile，是"task 在什么状态"的自然位置。加进 onboarding/schema 允许的 phase。
- **(c) 新 CLI `coordinate operator pending <workspace>`**。不扩展 `state --pending`（state 读 harness JSON，pending 是 coordinator 派生概念）；新 `operator` 子command 职责分离、易扩展。
- **(d) 推断 = 规则（phase + latest event）**。例：`planned + plan.review_requested → approve/reject plan`；`implementing + agent.reported done → review code/closeout`；`ready + no owner → handoff`；`awaiting_operator + agent.reported → advance/mark-done`。
- **recommended edit-1**：runtime `agent.reported` payload 显式含 `source="runtime"`、`job_id`、`agent_id`、`status`、`result_summary`（policy 据 source 区分 runtime vs Discord）。
- **recommended edit-2**：runtime 路径**不** auto `mark_done_task`（只设 `awaiting_operator`，operator 决定）；与 Discord 路径 `action=done → mark_done_task` 区分，符合半自动设计。
- **recommended edit-3**：reconciliation 清 stale `awaiting_operator`（harness status=done/closed 时清）。
- **double agent.reported 风险**：runtime 设 `source="runtime"` + source-specific idempotency key（`runtime:job:{id}:agent-reported:{status}` vs `discord-agent-report:{msg_id}`）。

## Review history

- round-1 (opencode, job 49458e65, via runtime request — 注：该用 reviewer handoff，round-2 改用): APPROVE + 4 open question 答案（a-d）+ 3 recommended edits（source=runtime payload / 不 auto mark_done / reconcile 清 stale）+ double-agent.reported 风险（source 区分 + idempotency）。已融入 Round-1 decisions。
