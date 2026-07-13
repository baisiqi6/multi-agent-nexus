# P9-1 worker correction bootstrap — Round 3

继续使用现有两个隔离 worktree：

- Coordinate: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-1-kimi`
- MultiNexus: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-1-kimi`

先完整阅读：

1. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/plan.md`
2. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/result-review-round3.md`

只修复 R3-1 至 R3-3。这是 handoff authority/compatibility 的窄修正，不要重写
P9-1 其他已通过部分，不要启动并行 coding subagents，不要修改 plan/review/bootstrap
文件。

实现约束：

- Coordinate 的 durable `payload.execution_profile` 必须保持既有完整 profile 与
  untargeted `null` 语义；machine/human handoff 渲染可以使用单独的 canonical
  two-field context。
- MultiNexus v1 handoff 必须同时有 host-absolute `workspace_path` 与
  `harness_root`。
- `agentd_mode` 必须在 `assignment accept`、bootstrap read、SQLite fallback、agentd
  submit/provider invoke 之前检查完整 v1 authority 并 fail closed；legacy
  non-agentd 行为不变。
- 不得 commit、push、merge、deploy、重启、访问生产 DB、执行 lifecycle/receipt。
- 不得更新历史 CLI/AST baseline fixture，不得修改 schema v11。
- Coordinate 权威测试命令使用：
  `PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest ...`
  且 workdir 必须是 Coordinate worktree。
- foreign host 路径只做 lexical validation；禁止对 foreign root 做本机 resolve。

完成后返回 R3-1 至 R3-3 映射、精确 dirty paths、两仓 targeted/full/static/
fixture/diff/compile 输出、正确 JSONL session id，并停在 Codex Round 4。
