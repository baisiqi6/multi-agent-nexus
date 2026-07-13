# P9-1 Independent Plan Reviewer Bootstrap

你是独立 **plan reviewer**，不是 architect、coding worker、result reviewer 或
Operator。只做对抗性计划审核，不实现、不重构、不提交、不 push、不部署、不操作
lifecycle/production DB/service/message。

## 精确审核对象

- Plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/plan.md`
- Exact SHA-256:
  `c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e`
- Plan-ready event: `9e70e470-da68-4264-a066-36e63dfe1667`
- Plan-review-requested event: `5845d3fd-2574-4904-8cc5-314a84227930`
- Split operation: `7aa8b1f2-d5c7-4c6a-b12e-4ae9bd2fbf89`
- Coordinate implementation start:
  `15020c2204e8e05c6304f6ed83a5fed83ad12eae`
- MultiNexus implementation start:
  `0d7c716b7dc3620767069e61c3ad168ca78b78dd`
- Plan registration commits after the implementation start are Operator-owned docs/
  checklist only and are not worker code baselines.
- Reviewer provider/model: fresh reviewer-only Kimi Highspeed session. Record exact
  effective provider/model and JSONL session id. This session may not be reused by the
  later coding worker.

## 必读与复核

1. exact plan、Phase 9 overview、P9-0A6 measurement/closeout、roadmap/dogfood；
2. Coordinate current `runtime.py`, `db.py`, job region, host profiles, handoff,
   policy rendering, CLI handlers and relevant tests；
3. MultiNexus current agentd worker/client, coordinator handoff, handoff parser,
   session store, adapters, bridge callers and tests；
4. 两仓库真实 HEAD/origin/dirty state、production deployed identities、schema、当前
   test baselines；
5. 用 read-only commands 重现关键 caller/import/transaction/direct-SQL/work_dir facts。

## 对抗性问题

- P9-1 是否应该保持一个 cross-repo contract package，还是必须拆成独立 reviewed
  Coordinate/MultiNexus 子包才有可审核性与安全 rollout？
- context 在 submit、first claim、recovery 之间的 snapshot/immutability/backfill
  规则是否无矛盾？idempotent replay 是否可能产生 request event without job？
- task scope、non-task scope 与 legacy scope 的 authority/bounds 是否完整；能否跨项目
  复用 private session？
- host profile/path mapping 对 POSIX/Windows/relative/space/backslash 是否真实可实现，
  是否误用本机 `pathlib.resolve()`？
- `worktree_path = workspace_path` fallback 是否诚实且足够 fail-closed；branch mismatch
  与 worktree provisioning 非目标是否清楚？
- context digest 是否绑定正确字段；nullable log path 是否诚实，是否偷跑 P9-4？
- job repository extraction 能否在保留 `coordinate.db` symbol identity 下真正无 cycle，
  narrow SQL 是否复制 authority/validation？
- missing profile/context、old pending job、host change、CLI failure 是否会 poison queue、
  silent poll、hot spin、daemon death或 provider invocation？
- MultiNexus 的 managed path 是否真的完全不再直接读 Coordinate SQLite；reviewer
  handoff 与 worker handoff 是否都覆盖？
- handoff machine message 增加 host-native paths 是否需要 sender/auth/path validation，
  是否扩大 spoof/path traversal surface？
- rolling deployment/rollback rules、fixture compatibility、old/new pairing 是否足够？
- tests 是否能证明 adapter zero-call、session/cwd separation、CAS、cold imports、
  cross-repo bytes 和 legacy compatibility？
- sidecar dogfood 是否使用真实 installed binaries/contracts而不污染 production authority？
- plan 是否越界到 P9-2 routing、P9-3 leases、P9-4 observation 或 P9-5 matrix？
- worker path scope 是否 deterministic；是否存在“顺手改”或 worker deploy/lifecycle 权限？

## Verdict artifact

只允许创建：

`/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/plan-review-round1.md`

使用单一 verdict：`APPROVE`、`APPROVE_WITH_NON_BLOCKING_NOTES` 或 `REJECT`。

每个 must-fix 必须包含 severity、plan section、当前代码/事实证据、后果和具体修改
要求。若批准，明确写出 exact SHA
`c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e`
可作为 implementation gate。不得修改其他文件；完成 artifact 后立即停止。
