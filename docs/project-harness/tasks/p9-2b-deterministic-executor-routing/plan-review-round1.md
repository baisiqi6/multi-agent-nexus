# P9-2B Plan Review — Round 1

**Verdict:** `APPROVED`

**Reviewed plan SHA-256:**
`328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`

## Blocking findings

None.

## Non-blocking observations

### O1 — `routing_load` 的 `recoverable` 字段依赖未显式验证

`routing_load` 计算引用 `timed_out and recoverable == 1`。实现阶段应在 candidate
query 构建前确认当前 schema v12 中该列存在；若事实不符，必须先修订并重审计划，
不能静默改变 load 定义。

严重度：低。当前 Coordinate schema/code 审计已经显示 `jobs.recoverable` 存在，
因此这是实现阶段的确认项而非阻塞项。

### O2 — claim 证据中添加 route ids 的边界条件

计划给 routed claim 增加 `routing_request_id`、`routing_decision_id` 和
`selection_kind`，同时要求 exact jobs byte-compatible。实现必须验证 additive JSON
字段的完整兼容边界，尤其是 MultiNexus consumer 对 absent legacy fields 与 malformed
present fields 的不同处理。

严重度：低。计划测试矩阵已覆盖该要求。

### O3 — hard filter 中 “binding snapshot resolves successfully” 的精确定义

实现应使用 P9-2A 的现有 binding authority 派生并验证当前完整 snapshot，而不是只做
结构检查或自行复制验证逻辑。

严重度：低。可由 P9-2A contract 与既有 resolver 直接确定。

### O4 — generic `job retry` 的统一拒绝语义

对 routed runtime job 使用统一
`routed_runtime_retry_requires_explicit_resubmission` 即可；无需按 terminal subtype
发明多套错误。

严重度：低。

### O5 — candidate cap 256

上限来源没有展开说明，但它是明确的资源边界，且超限行为是 fail closed，不构成
计划缺陷。

严重度：信息性。

## Approval conditions

无阻塞项。计划可进入 `worker-bootstrap.md` 生成与 coding worker 分配。

批准依据：

1. Coordinate 保持唯一控制面，MultiNexus 不做 candidate policy 或读取 DB。
2. `current_load` 与 `last_seen_at` 没有被错误提升为 load/liveness authority。
3. 七项 hard filter 完整，override 只能在 eligible set 内选择。
4. replay 明确在读取当前 candidate/load 前查回原 decision。
5. event/job/binding/context 先验证、后原子创建，失败不留下部分写入。
6. tuple、evidence、digest、cap、Unicode reason 与机器错误均有精确定义。
7. P9-3/P9-4 责任被明确排除，P9-2B 的真实路由行为仍完整。
8. exact typed/legacy、same-job recovery、generic retry、claim、consumer 与 rollback
   形成闭环。
9. 新 `executor_routing.py` 的 ownership 与测试矩阵足以约束 coding worker。
10. 生产 dogfood 必须无 `--target-agent` 且通过 non-Codex executor。

## Reviewer evidence

- Reviewer model: `deepseek/deepseek-v4-pro`.
- Reviewer session: `019f5afa-48dc-7000-a64c-77fccfffd6a0`.
- GLM 5.2 and ordinary `Kimi for Coding` were attempted first but produced no bounded
  review output in their observation windows; neither highspeed Kimi nor Codex worker
  was used.

## 声明

Reviewer 没有修改任何文件、计划、测试、harness 状态、Git 状态或生产环境；审核严格
只读。
