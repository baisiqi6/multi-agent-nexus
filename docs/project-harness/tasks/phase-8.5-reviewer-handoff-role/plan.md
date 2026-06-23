# Phase 8.5 Reviewer Handoff Role

## Ownership and branches

- Operator / reviewer: `opencode`（plan + code review，已验证组合）
- Worker: `omp`
- Task id: `phase-8.5-reviewer-handoff-role`
- multinexus branch: `agents/mac-omp/phase-8.5-reviewer-handoff-role`，from `agents/mac-claude/phase-8.4.2-contracts-function-decomposition`（含 phase-8.4.4）
- coordinate branch: 同名，omp 实现 coordinate 侧时创建
- Human gates: merge, deploy, force-push, branch protection, real GitHub PR write

## Goal

让 reviewer 走 handoff（`[handoff]` 协议、`role=reviewer`），不再用 `runtime request submit` 绕 Discord。review 交互走 Discord（可见），**reviewer bot 自己发评审意见**（身份明确），coordinate 不再代发 reviewer 的 lifecycle。

## Current pressure（基于勘察）

- **coordinate `handoff.py:118 _build_handoff_text(role, ...)` 已有 `role` 参数**，但 `task handoff` CLI 只暴露 `--role {worker}`（`handoff.py:89` 注释 "worker handoff"、`_require_latest_gate_approved` 强制 plan gate）。reviewer role 没接进 CLI/delivery。
- **multinexus `handoff_handler.py:40 _HANDOFF_PREFIX_RE = r"\[handoff\]\s*<@!?(\d+)>"`** 只解析 `[handoff] @user`，无 role 概念；`cogs/agents.py:57 _HANDOFF_RE`、`handoff.py:6 _FORMAL_HANDOFF_RE` 同理。reviewer 收不到 `[handoff]`。
- **bootstrap**：`bootstrap_text_from_accept_output`（handoff_handler.py:199）从 `assignment accept` 输出提取 bootstrap；coordinate 侧 `_build_handoff_text(role,...)` 按 role 生成，但只 worker role 有实现。
- **后果（phase-8.4.4 暴露）**：reviewer 走 `runtime request submit`（operator-direct origin）→ review 落 job result（DB），**Discord 不可见**；coordinate daemon 代发 `plan.approved`/`review.completed`（coordinate bot 发，不是 reviewer bot）；reviewer bot 全程没被触发、没发任何东西。

## Workstream A — coordinate：handoff role=reviewer

- `task handoff` CLI 加 `--role {worker,reviewer}`（default `worker`，向后兼容）。
- `_build_handoff_text(role="reviewer", ...)`：生成 **reviewer bootstrap（review context）**——含 source plan / diff path、acceptance criteria、review focus、output format（`[agent-report] decision=approve|reject` + reasoning）、human gate 约束（no merge/deploy）。
- `prepare_handoff` / `handoff_task`：`role=reviewer` 时 gate 放宽——**reviewer 不要求 `plan.approved` 前置**（reviewer 就是来 review plan 的，`_require_latest_gate_approved` 对 reviewer 跳过或改 scope）。
- `worker.handoff.prepared` event payload 加 `role` 字段；policy 按 role 渲染 delivery（reviewer delivery 投递 Discord，reviewer bot 收）。

## Workstream B — multinexus：[handoff] role=reviewer 解析 + reviewer 处理

- `handoff_handler.py` / `cogs/agents.py`：从 delivery payload 读 `role`（见 open question），`role=reviewer` 时走 reviewer 分支（不触发 worker auto-accept 实现，而是 review）。
- reviewer bot（mac-opencode 等）收到 `role=reviewer` handoff → 用 reviewer bootstrap → 做 review（读 plan/diff + 评审）→ 回 `[agent-report] decision=approve|reject + summary`。
- bridge 解析 reviewer 的 `[agent-report] decision` → approve 转 `review.completed`；reject 反馈给 operator（re-handoff worker 修）。

## Workstream C — dogfood 验证（code review 用新链路）

phase-8.5 实现后，它的 **code review** 用刚实现的 reviewer handoff 走（operator `task handoff --role reviewer --target-agent mac-opencode` → Discord 可见 → opencode bot 收 → review → `[agent-report] decision=approve`），验证链路 + 可见 + reviewer bot 自己发。phase-8.5 自己的 **plan review** 仍用 `runtime request submit`（reviewer handoff 此时未实现，chicken-egg）——这本身印证了本 task 的必要性。

## Non-goals

- **不做 handoff 全 role 化**（operator/observer 等）——只加 reviewer，等更多 role 出现再抽通用框架（避免 C1 教训：两个真实案例再抽象）。
- 不改 worker handoff 既有语义（`--role worker` default 行为完全不变）。
- 不改 `runtime request submit`（保留 operator 应急/诊断路径，常态走 handoff）。
- 不改 SQLite schema、event 类型（`worker.handoff.prepared` 复用，payload 加 `role` 字段）。

## Validation

- coordinate 全量测试 + `role=reviewer` handoff 新测试（gate 放宽、bootstrap 内容、delivery role 字段）。
- multinexus 全量测试 + `[handoff] role=reviewer` 解析 + reviewer `[agent-report] decision` 处理测试。
- e2e：operator `task handoff --role reviewer --target-agent mac-opencode` → Discord 可见 → opencode bot 收 → review → `[agent-report] approve` → bridge 转 `review.completed`。

## Done criteria

- reviewer 走 handoff（Discord 可见、reviewer bot 自己发评审），不再走 `runtime request submit`。
- phase-8.5 的 code review 用 reviewer handoff 走（reviewer bot 自己发、Discord 可见），不再 `runtime request submit`。
- coordinate / multinexus 测试通过。

## Open design question（plan review 时定）

`[handoff]` 的 role 编码方式：
- **(a) delivery payload**：`[handoff] @user` 文本协议不变（向后兼容），bridge 从 `worker.handoff.prepared` 的 delivery payload 读 `role` 路由 bootstrap——**倾向这个**（文本协议不变、worker 零改动）。
- (b) 文本标记：`[handoff] role=reviewer @user`——更显式但要改正则 + worker 兼容。

plan review 时确认（payload vs 文本）。
