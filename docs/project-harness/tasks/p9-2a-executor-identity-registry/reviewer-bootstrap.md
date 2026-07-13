# P9-2A Independent Plan Reviewer Bootstrap

你是独立 plan reviewer，不是 coding worker。只读审核，不修改文件，不 commit、push、
deploy、访问生产 DB、执行 lifecycle/receipt，也不要启动 subagents。

必须完整阅读：

1. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-2a-executor-identity-registry/plan.md`
2. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/phase-9-execution-isolation/plan.md`
3. `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-2a-executor-identity-registry/plan-review-round1.md`
4. 当前 Coordinate/MultiNexus 相关 schema、runtime、registry authority、deploy 与
   P9-1 binding/context 代码。

审核重点：

- 把 P9-2 拆成 identity P9-2A 与 routing P9-2B 是否合理、边界是否闭合；
- schema v12 三表是否是最小且足够的 authority model；
- “一个 source file、roster/catalog 两个 canonical projection/hash”是否会产生
  source-of-truth 冲突；
- typed binding snapshot、replay、claim-current-binding mismatch 语义是否安全；
- legacy untyped exact-target 兼容窗口是否过宽或不清晰；
- registry deploy parity、schema-bearing rollout、rollback 与 dogfood 是否足以阻止
  source/installed/DB/catalog 漂移；
- 是否意外混入 P9-2B routing、P9-3 leases/capacity 或 P9-4 heartbeat/JSONL 范围；
- 测试矩阵是否覆盖 zero-mutation、strict schema、cross-repo contract 与真实部署。
- Round 1 的两个 must-fix 是否被完整解决：agentd 的本地 runner/adapter/provider
  authority，以及同一 TOML 的 Coordinate-side canonical sync；并检查新增的
  canonical hash、多 source ownership、in-flight drain 规则是否自洽。

返回格式：

```text
verdict=approve|changes_requested|blocked
must_fix=<none or numbered findings>
recommended=<non-blocking notes>
open_questions=<questions that require architect decision>
reasoning=<evidence-backed review>
```

只有 plan 在范围、authority、兼容、迁移、测试、deploy/dogfood/rollback 上都足以直接
生成 worker bootstrap 时才能 approve。
