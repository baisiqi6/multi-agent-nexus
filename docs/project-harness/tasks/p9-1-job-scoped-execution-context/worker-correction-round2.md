# P9-1 worker correction bootstrap — Round 2

继续使用现有两个隔离 worktree：

- Coordinate: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-1-kimi`
- MultiNexus: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-1-kimi`

先完整阅读：

1. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/plan.md`
2. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/result-review-round2.md`

只修复 R2-1 至 R2-5。不要重写已通过的整体设计，不要启动并行 coding
subagents，不要修改 plan/review/bootstrap 文件。

硬约束：

- 不得 commit、push、merge、deploy、重启、访问生产 DB 或执行 lifecycle/receipt。
- 不得更新历史 CLI/AST baseline fixture。
- 删除非计划的 Coordinate `tests/__init__.py`；不得用新增 package marker 掩盖
  本机环境问题。
- Coordinate 权威测试命令使用：
  `PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest ...`
  且 workdir 必须是 Coordinate worktree。
- MultiNexus 测试 workdir 必须是 MultiNexus worktree。
- foreign host 路径只做 lexical validation；禁止对 foreign root 做本机 resolve。
- 保持 schema v11 与 P9-1 边界。

完成后返回 R2-1 至 R2-5 映射、精确 dirty paths、两仓 full/targeted/static/
fixture/diff/compile 输出、正确的本次 JSONL session id，并停在 Codex Round 3。
