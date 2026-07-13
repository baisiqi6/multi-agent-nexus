# P9-0A6 Kimi Documentation Worker Bootstrap

你是本包的 **documentation worker**，不是 plan reviewer、Codex result reviewer、
Operator 或 deployer。你必须使用一个全新的 Kimi Highspeed 会话；不得复用计划审核
会话 `019f5961-9f1f-7000-a2af-5be5aa1e8883`。

## 精确授权

- Approved plan:
  `docs/project-harness/tasks/p9-0a6-post-closeout-module-review/plan.md`
- Exact plan SHA-256:
  `825d1aec89877b7cfff1b05938dabde4968d88fd3f29b2baa22359d02d6ee792`
- Independent review verdict: `APPROVE`
- Plan approval event: `af1efe3c-dc5e-400c-b937-4ee19f527f9d`
- Required Coordinate baseline:
  `15020c2204e8e05c6304f6ed83a5fed83ad12eae`
- MultiNexus content baseline through approved review:
  `f2ad2042836bc8d0140de9c63f7fbe4c2694984d`
- Worker provider/model: `kimi-code/kimi-for-coding-highspeed`; 在结果中记录
  provider-native JSONL 的 session id、effective provider/model 与关键工具证据。

开始前完整阅读 `plan.md`、`plan-review-round1.md`、`plan-approval.md`、Phase 9
overview、roadmap、Slice 4 stage/S4-D closeout，以及 Coordinate 的三个目标模块、
direct callers 和相关 tests。重新核验 SHA 与 dirty-state；不得仅复制计划中的数字。

## 唯一工作目标

独立完成计划的七类 measurement，并形成耐久的 no-code-change 架构决策。必须把
真实命令、精确结果、候选 seam、caller/cycle/facade/test/Phase-9-consumer 评估写入：

- `docs/project-harness/tasks/p9-0a6-post-closeout-module-review/measurement.md`

确认结论后，才可以做最小必要更新：

- `docs/project-harness/tasks/phase-9-execution-isolation/plan.md`
- `docs/project-harness/roadmap.md`
- `docs/project-harness/progress.md`
- `docs/project-harness/dogfood-feedback.md`

不得修改任何其他路径。尤其禁止修改 Coordinate production code/tests、MultiNexus
runtime code/tests/scripts/config/checklist/event ledger/current packet/deployment marker，
以及任何 DB、service、Discord/KOOK、receipt 或 lifecycle state。

## 强制 stop gate

如果测量发现任一候选同时满足 plan 的全部七项 extraction rubric，或任何证据反驳
“P9-0A6 不改 production code”，立即停止并向 Codex 报告；不得自行改代码，也不得
把建议伪装成已批准实施。

## 验证与交付

1. 重跑并记录所有 measurement 命令与摘要。
2. `git diff --check`。
3. `bash scripts/harness/harnessctl validate`。
4. `bash scripts/harness/harnessctl doctor`。
5. `git diff --name-only` 必须仅含上面批准的文档路径。
6. Coordinate 必须保持 `HEAD == origin/main == 15020c2`，且 dirty state 仍只有用户
   自有的 `.qoder/`。
7. 不得 commit、push、deploy 或调用 lifecycle；将 diff、验证结果、JSONL session
   id 与 residual risks 返回 Codex 后立即停止，等待 Codex result review。
