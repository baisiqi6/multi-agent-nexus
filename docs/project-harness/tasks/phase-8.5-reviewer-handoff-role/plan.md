# Phase 8.5 Reviewer Handoff Role

## Ownership and branches

- Operator: 我（Claude Code）
- Plan reviewer: `opencode`（round-1 REJECT + 7 must-fix，本版 round-2）
- Code reviewer: **`mac-claude`**（非 opencode——opencode 自己实现了 reviewer handoff，review 自己有自我审查偏见，must-fix-7）
- Worker: `omp`
- Task id: `phase-8.5-reviewer-handoff-role`
- multinexus branch: `agents/mac-omp/phase-8.5-reviewer-handoff-role`，from `agents/mac-claude/phase-8.4.2-contracts-function-decomposition`（含 phase-8.4.4）
- coordinate branch: 同名，omp 实现 coordinate 侧时创建
- Human gates: merge, deploy, force-push, branch protection, real GitHub PR write

## Goal

让 reviewer 走 handoff（`[handoff]` 协议、`role=reviewer`），不再用 `runtime request submit` 绕 Discord。review 交互走 Discord（可见），**reviewer bot 自己发评审意见**（身份明确），coordinate 不再代发 reviewer 的 lifecycle。

## Design decision（round-1 open question 已定）

**role 编码用 (a) delivery payload**：`[handoff] @user` 文本协议不变（向后兼容），bridge 从 `worker.handoff.prepared` 的 delivery payload 读 `role` 路由 reviewer bootstrap。理由（opencode round-1）：`[handoff]` 是机器协议无需人读；方案 (b)（文本标记 `[handoff] role=reviewer @user`）要改 3 个正则（`_HANDOFF_PREFIX_RE`/`_HANDOFF_RE`/`_FORMAL_HANDOFF_RE`）+ 所有 worker agent 学新语法；(a) 把 role 放 envelope 旁（`target_agent`/`execution_profile`/`bootstrap_text`），worker 端零改动。

## Current pressure（基于勘察 + opencode round-1 cross-check）

- coordinate `handoff.py:143 _build_handoff_text(role,...)` 有 role 参数但**不分支**（只输出 Worker 标题）；`handoff.py:411 _require_latest_gate_approved` 无条件强制 plan gate；`handoff.py:472` payload 已带 `role`、`:497` event target=role（部分已实现）。
- coordinate `daemon.py:437 _do_handoff` 硬编码 `role="worker"`；`daemon.py:520 _parse_agent_report` 只接受 `{accept, done, blocker, progress}`，不支持 `decision=`。
- multinexus `handoff_handler.py:46 _ALLOWED_ACTIONS={assignment.accept}`、`:235 _is_allowed_bootstrap_path` 只白名单 `worker-bootstrap.md`、`:40 _HANDOFF_PREFIX_RE` 无 role。
- 后果：reviewer 走 runtime request → review 不可见、coordinate bot 代发、reviewer bot 不触发。

## Workstream A — coordinate：handoff role=reviewer

- `task handoff` CLI 加 `--role {worker,reviewer}`（default `worker`，向后兼容）。
- **must-fix-1**：新 `_build_reviewer_bootstrap` helper（`_build_handoff_text` 按 role 分支）。reviewer bootstrap = **review context**：source plan / diff path、acceptance criteria、review focus、output format（`[agent-report] decision=approve|reject` + reasoning）、human gate 约束（no merge/deploy）。
- **must-fix-2**：`daemon._do_handoff` role plumbing（`:437` 硬编码 worker → 透传 role）。
- `prepare_handoff`/`handoff_task`：`role=reviewer` 时 gate-skip——在 `_require_latest_gate_approved`（`:411`）**内部**加 `role==reviewer` 检查（不放宽整个 gate 函数，避免 scope creep）。gate-skip 安全：plan review 时 reviewer 本身就是 gate（否则自引用）；code review 时 plan 已 approved。
- `worker.handoff.prepared` payload `role` 字段（`:472` 已有）+ policy 按 role 渲染 delivery。

## Workstream B — multinexus + coordinate：role=reviewer 解析 + reviewer 处理

- bridge 从 `worker.handoff.prepared` delivery payload 读 `role`（(a) 方案，文本协议不变）→ 选 reviewer bootstrap。
- **must-fix-3**：`_is_allowed_bootstrap_path`（`handoff_handler.py:235`）白名单加 reviewer bootstrap 文件名（`reviewer-bootstrap.md`）。
- **must-fix-4**：reviewer action = **`review.begin`**（新 action，reviewer 不 `accept` task ownership，而是 begin review；`_ALLOWED_ACTIONS` `:46` 加 `review.begin`，不复用 `assignment.accept`）。
- **must-fix-5**：`decision=approve|reject` 解析在 **coordinate daemon**（`_parse_agent_report` `:520` 扩展支持 `decision=` → `review.completed`/`review.rejected`；review.completed 是 coordinate transition，daemon 解析发，不是 multinexus bridge）。
- **must-fix-6**：reviewer→reviewer 循环保护——reviewer 的 `decision=approve` 绝不触发另一次 reviewer handoff（handoff 调度加 guard，reviewer decision 只推进 lifecycle 给 operator/worker，不回 reviewer）。
- reviewer bot（mac-claude 等）收 `role=reviewer` handoff → reviewer bootstrap → review（读 plan/diff + 评审）→ `[agent-report] decision=approve|reject + summary`。

## Workstream C — dogfood 验证（code review 用新链路 + 非 opencode reviewer）

- phase-8.5 实现后，**code review 用 reviewer handoff 走**（operator `task handoff --role reviewer --target-agent mac-claude` → Discord 可见 → mac-claude bot 收 → review → `[agent-report] decision=approve`）——验证链路 + 可见 + reviewer bot 自己发。
- **must-fix-7**：code review reviewer 用 **mac-claude**（非 opencode，避免自我审查偏见）。
- phase-8.5 的 **plan review** 仍用 `runtime request submit`（reviewer handoff 此时未实现，chicken-egg）——这本身印证本 task 必要性。

## Non-goals

- **不做 handoff 全 role 化**（operator/observer 等）——只加 reviewer，等更多 role 出现再抽通用框架（避免 C1 教训）。
- 不改 worker handoff 既有语义（`--role worker` default 行为完全不变；既有 event 已带 `role="worker"`）。
- 不改 `runtime request submit`（保留 operator 应急/诊断路径）。
- 不改 `[handoff]` 文本协议（(a) 方案，role 在 payload）。
- 不改 SQLite schema、event 类型（`worker.handoff.prepared` 复用，payload `role` 已存在）。

## Validation

- coordinate 全量测试 + 新测试：`--role reviewer` CLI、`_build_reviewer_bootstrap` 内容、gate-skip（reviewer 跳过、worker 不跳）、daemon role plumbing、`_parse_agent_report` 支持 `decision=` → review.completed/rejected、reviewer→reviewer 循环 guard。
- multinexus 全量测试 + 新测试：bridge 从 payload 读 role 路由、`_is_allowed_bootstrap_path` 含 reviewer-bootstrap.md、`_ALLOWED_ACTIONS` 含 review.begin。
- e2e：operator `task handoff --role reviewer --target-agent mac-claude` → Discord 可见 → mac-claude bot 收 → review → `[agent-report] decision=approve` → daemon 解析 → `review.completed`。

## Done criteria

- reviewer 走 handoff（Discord 可见、reviewer bot 自己发评审），不再 `runtime request submit`。
- phase-8.5 code review 用 reviewer handoff（mac-claude reviewer）自举验证。
- coordinate / multinexus 测试通过。

## Review history

- round-1 (opencode, job fa41dd22): REJECT + 7 must-fix + open question→(a)。must-fix：①`_build_reviewer_bootstrap` helper（`_build_handoff_text:143` 不分支）；②`daemon._do_handoff:437` role plumbing（硬编码 worker）；③`_is_allowed_bootstrap_path:235` 白名单 + reviewer bootstrap 文件名；④reviewer action = `review.begin`（非 accept）；⑤decision 解析在 coordinate daemon（`_parse_agent_report:520` 扩展）；⑥reviewer→reviewer 循环保护；⑦code review 用 mac-claude（非 opencode，避免自我审查）。open question：(a) delivery payload。已在本版 Workstream A/B/C + Design decision 落实。
