# P9-1 worker correction bootstrap — Round 4

继续使用现有两个隔离 worktree；本轮只需要修改 MultiNexus：

- Coordinate: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-1-kimi`
- MultiNexus: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-1-kimi`

先完整阅读：

1. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/plan.md`
2. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/result-review-round4.md`

只修复 R4-1，不要改动 P9-1 其他已通过部分，不要启动 parallel coding
subagents，不要修改 plan/review/bootstrap 文件。

硬约束：

- `parse_coordinator_handoff()` 默认仍须 strict；直接解析 partial/relative/
  unsupported v1 必须返回 `None`。
- managed runtime 可以使用安全的 diagnostic/candidate 模式识别候选 handoff，
  但 malformed context 绝不能成为 authority；必须由现有 authority gate 发一条
  blocker 后停止。
- worker 与 reviewer 的 malformed v1 集成测试都要证明：handled=true、恰好一个
  blocker，且 assignment accept、bootstrap read、SQLite fallback、agentd submit、
  provider invocation 全部未调用。
- legacy non-agentd 行为不变；schema v11、fixture 与历史 baseline 不变。
- 不得 commit、push、merge、deploy、重启、访问生产 DB、执行 lifecycle/receipt。

完成后返回 R4-1 映射、精确 dirty paths、focused/full/static/fixture 输出以及本轮
实际 JSONL session id，并停在 Codex Round 5。
