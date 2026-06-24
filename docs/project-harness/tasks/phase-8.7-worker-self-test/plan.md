# Phase 8.7 Worker Self-Test Before Closeout（根因）

## Ownership and branches

- Operator: 我（Claude Code）
- Reviewer: `opencode` / `mac-claude`
- Worker: `omp`
- Task id: `phase-8.7-worker-self-test`
- branch: `agents/mac-omp/phase-8.7-worker-self-test`，from `agents/mac-claude/phase-8.4.2-contracts-function-decomposition`（含 phase-8.4.4/8.5/8.6）
- Human gates: merge, deploy, force-push, branch protection, real GitHub PR write

## Goal

worker closeout 前必须 **deploy + 自举验证（跑通新链路）+ 附自举证据**。解决 phase-8.5（3 KeyError + idempotency + bootstrap 只 plan）+ phase-8.6（dedup/action==done）反复"没自举就 closeout 藏 bug"——operator 实测才发现。

## Current pressure（根因）

- phase-8.5 omp 写完 reviewer handoff **没 deploy+自举就 closeout** → 藏 3 KeyError + idempotency key bug + bootstrap 只 plan。全部 operator deploy 后实测才发现。
- phase-8.6 同样藏 2 code review bug（policy dedup + operator action==done，都是 opencode round-2 notes 提过没落实）。
- 根因：**无机制强制 worker 自举**。worker 倾向"代码 + 单测通过就 closeout"，不 deploy + 跑通真实链路。单测不能覆盖 daemon/bridge 长进程代码的集成 bug（phase-8.5 的 KeyError 都是 prepare_handoff 真实调用才暴露）。

## Design decision（半自动 + 证据，不硬 gate）

- worker bootstrap 加**自举 checklist**（deploy 步骤 + e2e smoke 命令 + 证据要求）。
- closeout packet schema 加 `self_test_evidence`（worker 填：deploy SHA + e2e 结果 + 发现的 bug）。
- reviewer 检查 `self_test_evidence` 真实性（review 时验证 worker 真自举）。
- **不硬 gate**（不自动阻断 closeout）——靠 worker bootstrap 提醒 + reviewer 把关。硬 gate（closeout 自动跑 e2e）留后续，先靠协议 + reviewer。

## Workstream A — worker bootstrap 加自举 checklist

- `_build_worker_bootstrap`（handoff.py）加 "Self-Test Before Closeout" 段：deploy 命令（`scripts/deploy-server.sh`）+ e2e smoke（跑通本 task 的新链路，如 reviewer handoff / operator pending）+ "closeout 前必填 self_test_evidence"。
- 让 worker 从 handoff 起就知道 closeout 前要 deploy + 自举。

## Workstream B — closeout packet schema 加 self_test_evidence

- closeout packet（`docs/.../current/closeout-packet.md`）加 `self_test_evidence` 字段：deploy SHA + e2e smoke 结果 + 发现的 bug（如有，写怎么修的）。
- `assignment closeout` 可选 `--self-test-evidence <text>`（写 payload）。
- 空 `self_test_evidence` → closeout 输出 warning（不阻断，但 reviewer 会看到）。

## Workstream C — reviewer 检查 self_test_evidence

- reviewer bootstrap 加"验证 worker self_test_evidence"：reviewer 检查 worker 真自举（evidence 非空 + 真实：deploy SHA 对应实际 deploy + e2e 结果合理）。
- reviewer reject 无/假 `self_test_evidence` 的 closeout（回到 worker 补自举）。

## Non-goals

- **不自动化自举**（不自动跑 e2e gate；worker 手动 deploy + e2e + 填证据）。
- 不改 closeout 硬 gate（reviewer 软检查；硬 gate 留后续）。
- 不改 worker 代码生成（只 bootstrap 协议 + packet schema + reviewer 检查）。

## dogfood

#7 自己走完整 lifecycle 验证：worker omp 实现 #7 → deploy + 自举（**worker bootstrap 自举 checklist 生效**）→ closeout 附 `self_test_evidence` → reviewer 检查 evidence 真实 → approve。如果 #7 有效，omp 这次该 deploy+自举后才 closeout（不再藏 bug）。

## Validation

- coordinate 全量测试 + worker bootstrap 含自举 checklist 测试 + closeout self_test_evidence 字段测试 + reviewer bootstrap 检查测试。
- e2e：omp 实现 #7 + deploy + 自举 + closeout 附 evidence + reviewer 验证 evidence + approve。

## Done criteria

- worker bootstrap 有自举 checklist；closeout packet 有 self_test_evidence；reviewer bootstrap 检查 evidence。
- #7 dogfood：omp 实现 + **deploy+自举后才 closeout**（附 evidence），reviewer 验证通过。
- 自举 checklist 对后续 worker（phase-8.5/8.6 那种藏 bug）有约束力（至少 worker 知道要自举 + reviewer 把关）。
