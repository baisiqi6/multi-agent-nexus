# P9-2B worker correction bootstrap — Round 1

你是 P9-2B 的 coding correction worker，不是 architect、plan reviewer 或最终
result reviewer。使用普通版 `Kimi for Coding`：`kimi-code/kimi-for-coding`；禁止
切换到任何带 `highspeed` 标识的模型。

## 必须先验证的 authority

- Approved plan:
  `docs/project-harness/tasks/p9-2b-deterministic-executor-routing/plan.md`
- Plan SHA-256:
  `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Independent plan verdict:
  `docs/project-harness/tasks/p9-2b-deterministic-executor-routing/plan-review-round1.md`
- Codex result review:
  `docs/project-harness/tasks/p9-2b-deterministic-executor-routing/result-review-round1.md`
- Coordinate worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-2b-kimi`
- Coordinate branch:
  `agents/mac-omp/p9-2b-deterministic-executor-routing-coordinate`
- Coordinate baseline HEAD:
  `eec9b233f6c797c73aec9d535fa723e037a0af65`
- MultiNexus worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-2b-kimi`
- MultiNexus branch:
  `agents/mac-omp/p9-2b-deterministic-executor-routing`
- MultiNexus baseline HEAD:
  `b9416d9df81afb81051bfa19627bbe45d66852f0`

先读取两个仓库各自的 `CLAUDE.md`、approved plan、plan review、Round 1 result
review，并确认两个 HEAD 与上述 baseline 相同。当前未提交实现属于上一位 ordinary
Kimi worker；保留并修正它，不要 reset、checkout 或覆盖用户/其他 agent 的改动。

## 任务

逐项修复 `result-review-round1.md` 的 R1-1 至 R1-6。重点：

1. 区分 caller normalization 与 strict stored parsing；API/CLI 输入可乱序/重复，
   stored envelope 必须 exact canonical 且拒绝 bool-as-int。
2. 完整验证 decision/candidate exact shape、types、ordering、request/override link、
   selected candidate link；无 preferred host 时 host rank 必须为零。
3. claim CAS 前把 route decision 与 P9-2A binding、P9-1 context、job/event identity
   全部交叉绑定；任何 forged link 都必须 zero mutation。
4. explicit idempotency key 在 exact/routed 两方向都不得跨 mode；replay 验证全部
   immutable links；并发 loser 必须读取 stored decision 而不是 current routing state。
5. exact mode 必须拒绝所有 route-only CLI flags，并补齐 parser/handler tests。
6. 补齐 atomic rollback、malformed-state、recovery、retry-before-write、exact
   compatibility tests。

不得降低断言、删除历史 gate、把 malformed data 当成 normalized input、引入 schema
v13、把 routing policy 放入 MultiNexus、使用 `agents.current_load`、发明 heartbeat
freshness、capacity/lease/fairness/reroute，或扩大到 P9-3/P9-4。

## 验证与提交

- 先运行 focused tests，失败时修实现而不是弱化规范。
- 再运行未通过 `tail/head` 截断的 Coordinate full baseline、MultiNexus focused/full、
  `compileall`、`git diff --check` 和 plan 要求的 static gates。
- 在 MultiNexus task 目录创建 `implementation-report.md`，记录 exact model、plan SHA、
  commits、commands/counts、历史失败对比、cross-repo contract 与 residual risks。
- 完成后在 Coordinate worktree 创建一个原子 implementation commit；在 MultiNexus
  worktree 创建一个只含 report/review/bootstrap 文档的原子 commit。
- 不要 push、cherry-pick、deploy、restart、修改 production DB、写 lifecycle event，
  也不要修改两个 `main` checkout。
- 最终输出 exact commit SHAs、测试结果、worktree status 和已知风险，等待 Codex
  Round 2 result review。
