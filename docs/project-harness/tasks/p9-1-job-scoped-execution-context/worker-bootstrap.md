# P9-1 Kimi Coding Worker Bootstrap

你是 P9-1 的 **coding worker**，不是 plan reviewer、Codex result reviewer、Operator
或 deployer。使用全新 Kimi Highspeed session；不得复用 reviewer session
`019f598b-6caf-7000-9bf3-c412a01f6405`。

## 精确授权与工作树

- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/plan.md`
- Exact plan SHA-256:
  `c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e`
- Plan approval event: `1b8b0136-a0de-496c-a9da-b1bf4428aee6`
- Independent review: `plan-review-round1.md`
- Coordinate implementation baseline:
  `15020c2204e8e05c6304f6ed83a5fed83ad12eae`
- MultiNexus implementation baseline:
  `0d7c716b7dc3620767069e61c3ad168ca78b78dd`
- Coordinate worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-1-kimi`
- MultiNexus worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-1-kimi`
- Provider/model: `kimi-code/kimi-for-coding-highspeed`; 最终返回 provider-native
  JSONL session id、effective provider/model 与关键工具证据。

开始前完整阅读 plan、plan review、plan approval、P9-0A6 measurement/closeout 和两仓
当前实现。核对两个 worktree 的 branch/HEAD/dirty state。MultiNexus worktree 包含
Operator 的计划/审核/bootstrap commits；生产代码 diff 的审计基线仍是上面的
`0d7c716...`。Coordinate 仅允许保留主 checkout 的用户自有 `.qoder/`，不得触碰。

## 执行顺序

严格按 approved plan 的 Stage A → B → C → D：

1. Coordinate job repository seam 与 cold-import/public identity tests。
2. Coordinate v1 `ExecutionContext` authority、snapshot/replay/backfill/claim contract
   与 versioned handoff fields。
3. MultiNexus strict parser/client/agentd cwd+session consumption、managed handoff
   SQLite removal、bounded error/backoff。
4. 两仓 byte-identical fixture、兼容矩阵、全量 validation 与 docs/progress。

不得先在 MultiNexus 做一个 `config.work_dir` fallback 版本；managed path 从第一次
提交起就必须 fail closed。不得用第三个 shared Python package、ORM、DI/framework、
provider-specific branch 或 schema migration 简化契约。

## Reviewer notes 变成强制执行检查

1. Foreign host root/path mapping 必须纯字符串/segment + host-native separator；不得
   对 Windows/foreign root 调用本机 `Path.resolve()`。
2. `[handoff]` message 中的 workspace/harness/branch fields 只能用于定位 bootstrap
   metadata；adapter cwd、session scope、filesystem execution authority 只来自
   Coordinate `runtime job claim` 的 digest-validated context。
3. `submit_request` replay 必须比较 stored origin/scope/context 与本次输入；相同
   idempotency key 但语义不同必须 bounded error，不能静默复用。

## Stop gates

立即停止并返回 Codex，不得自行扩展，如果：

- current code/transaction/schema/host-profile facts 与 plan 不符；
- job repository 无法在保留 `coordinate.db` symbol identity 下无环提取；
- 需要新增/修改 schema 或 event/lifecycle authority；
- missing context/profile 的正确处理需要 P9-2 routing 或 P9-3 lease；
- 跨仓 fixture 无法 byte-identical；
- 需要修改 approved path 之外的 production code；
- full suite 出现非已知 baseline failure。

## 禁止操作

- 不得 commit、push、merge、deploy、SSH、restart service、访问/修改 production DB；
- 不得调用 Coordinate lifecycle、receipt、Discord/KOOK delivery；
- 不得编辑主 checkout、review artifacts、checklist/events/current packets；
- 不得直接修改 harness JSON/SQLite；
- 不得清理或覆盖任何非本任务 dirty/untracked 文件。

## 验证与返回

逐项执行 plan 的 permanent tests/validation gates。必须至少返回：

- 两仓 `git diff --check`、compileall、targeted/full test 精确结果；
- Coordinate 九个历史 failure 的 exact accounting，任何新增 failure 单列；
- MultiNexus baseline `389 passed, 2 skipped, 26 subtests passed` 的对比；
- fixture SHA/byte equality；
- static no-direct-Coordinate-SQLite / no-managed-config-work_dir gates；
- 两仓所有 modified/untracked paths；
- compatibility/rollout residual risks；
- JSONL session id 和关键 tool-call evidence。

完成实现和自测后立即停止等待 Codex result review；不要提交或部署。
