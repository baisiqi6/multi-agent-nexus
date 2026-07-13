# P9-3A Plan Reviewer Supplement — Round 4

你是独立计划审核者，不是 coding worker。只审核本轮 material plan amendment；不得
修改任何文件、Git 状态、harness 状态或生产环境。

## 背景

首轮实现与 Codex result review 发现：旧 accepted authority 尚无 capacity roots 时，
新的 capacity sync 一旦成功而随后的 committed verifier 失败，单靠恢复旧 TOML 无法
删除刚写入的 capacity projection。现有实现只能检测不一致后失败，不能满足计划中
“previous accepted projection restored before command exit”的承诺。

计划因此新增一个非公开、capacity-only、digest-bound snapshot capture/restore 协议。
它只修改 `executor_capacity_sources` 与 `executor_capacity_policies`，restore 必须在一个
`BEGIN IMMEDIATE` 内完成，必须拒绝 active lease，并且不得成为通用 CLI 或触碰
roster/executor/jobs/events/leases。

被审核计划 SHA-256：
`d75486b42e8d3315bda488db1129e02c03c0a2c152c04a60cccce917a385d99e`。

## 必须对抗性审核

1. 这是补足 P9-3A rollback，还是偷偷新增第二套 capacity authority？
2. prior-absence snapshot 是否能在 first rollout 的 post-sync verifier failure 后原子删除
   新 projection，而不是只检查失败或静默留下不一致状态？
3. snapshot 的 exact shape、canonical bytes、digest、source id、policy id/hash/bounds 和
   secret-free 约束是否足以 fail closed？
4. restore 是否严格拒绝 active lease、未知 source、tamper、missing snapshot 与部分恢复，
   并保证 roster/executor/jobs/events/leases 不变？
5. deploy fault injection 是否覆盖：旧 projection 已存在、旧 projection 不存在、capacity
   sync 原子失败、sync 成功后 verifier 失败、restore 自身失败；每条都无 version/restart/
   smoke 并验证三套 projection 回到 previous accepted state？
6. 是否需要 public CLI、停服务或恢复整库；若不需要，计划是否明确解释 capacity 在
   P9-3A 尚非 runtime claim authority且 production active lease 必须为零这一安全前提？
7. P9-3B 是否被明确要求在 capacity 成为 claim authority 前废止/收紧该零 lease 假设？
8. 是否仍遵守原 non-goals，不提前实现 claim/heartbeat/reaper/observation/scheduler？

## Verdict 与输出

只允许 `APPROVED` 或 `CHANGES_REQUESTED`。返回可保存为
`plan-review-round4.md` 的 Markdown，包含：

1. `# P9-3A Plan Review — Round 4`
2. `Verdict: ...`
3. `Reviewed plan SHA-256: ...`
4. Blocking findings（severity、章节、失败场景、必须修改）；
5. Non-blocking observations；
6. Approval conditions；
7. 明确声明没有修改文件或执行实现。

若 snapshot restore 仍不能真正恢复 first-rollout prior absence，必须
`CHANGES_REQUESTED`。不要输出实现代码或寒暄。
