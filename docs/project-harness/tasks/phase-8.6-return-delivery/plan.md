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

## Open design questions（plan review 定）

1. runtime job terminal 触发 `agent.reported` 的层：`report_job_result`（agentd 层）写入 vs daemon 监听 job terminal？
2. pending 存哪：task phase=`awaiting_operator` vs 新 `pending_operator_actions` 表？
3. `operator pending` 是新 CLI 还是 `state --pending` 扩展？
4. pending 的"待办动作"怎么推断（从 task 当前 phase + 最新 event 推该 operator 做什么）？
