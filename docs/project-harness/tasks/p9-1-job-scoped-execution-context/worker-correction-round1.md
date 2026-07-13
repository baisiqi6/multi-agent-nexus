# P9-1 worker correction bootstrap — Round 1

你是 P9-1 的 correction coding worker。使用当前两个隔离 worktree，不要新建分支：

- Coordinate: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-1-kimi`
- MultiNexus: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-1-kimi`

先完整阅读：

1. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/plan.md`
2. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-1-job-scoped-execution-context/result-review-round1.md`

目标：逐项修复 Round 1 的 R1-1 至 R1-7，不得跳过、弱化或用文档解释代替代码与测试。

硬约束：

- 只修改 approved plan 与 Round 1 correction 所需路径；如果必须新增生产路径，先停止并报告。
- 不得 commit、push、merge、deploy、重启服务、访问或修改生产 DB、执行 lifecycle/receipt 操作。
- 不得修改 plan、plan review、plan approval 或本 correction bootstrap。
- 不得为了绿测更新历史 CLI/AST baseline fixture。
- foreign host 路径只能做 lexical validation/join；不得对 foreign root 调用本机 `Path.resolve()`。
- handoff 路径只是 bootstrap metadata；provider cwd/session authority 只能来自已验证 claim context。
- 真实 Discord webhook machine message 必须追加 v1 字段；只改 human handoff text 不算完成。
- managed mode 缺少有效 v1 handoff/bootstrap authority 时必须 fail closed；不得回退到 configured workspace path 或 Coordinate SQLite。
- 保留 schema v11；不增加 migration、服务、ORM、DI/plugin 框架，也不扩展到 P9-2 及以后范围。

执行顺序：

1. 先为每个 finding 添加会失败的精确测试/对抗性矩阵。
2. 修正 Coordinate pre-write validation、task identity、transaction/idempotent replay。
3. 修正两仓 exact schema、path/scope/log_handle/digest validation 与 job-envelope binding，并保持 fixture byte-identical。
4. 修正真实 policy renderer、managed handoff fail-closed、Coordinate CLI error normalization/backoff。
5. 修正 progress 文档中的所有 overclaim。
6. 运行 plan 要求的 targeted/full/static/fixture/compile/diff gates。

最终只返回：

- R1-1 至 R1-7 的逐项修复映射；
- 两仓精确 dirty paths 与 diff stat；
- 所有验证命令和原始摘要，包括 Coordinate 九个历史失败的精确 accounting；
- fixture SHA；
- effective provider/model 与 provider-native JSONL session id；
- 剩余风险。

完成后停在 Codex Round 2 result review，禁止提交或部署。
