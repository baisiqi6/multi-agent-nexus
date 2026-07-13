# P9-3A Independent Plan Reviewer Supplement — Round 3

本文件覆盖所有旧 plan SHA。继续遵守 `plan-reviewer-bootstrap.md` 的只读、无实现、
无子 agent、无状态变更和有界 verdict 规则。

Round 3 只审核当前 `plan.md` 的最终精度修订，期望完整 SHA-256：

`77f467f1d9555552b236f0958d0f08fd267f3cb8193ab83541580de8f0ab7c0f`

只回答以下问题，不重新扩展整个任务：

1. `capacity_policy_id` canonical object 是否字段完整、排除非确定数据并足以跨仓复现；
2. reserve/renew 的 TTL 是否都明确为 integer 30..600 秒并在写前校验；
3. executor/capacity 独立 transaction 的 transitional mismatch 是否被限定为 P9-3A
   guarded deploy window，且 failure stage、no-version/restart/success、previous projection
   restore 与 P9-3B re-tightening 是否闭合；
4. 新增 fault-injection test 是否足以约束 worker；
5. 新文字是否引入 P9-3B runtime 行为或与原计划冲突。

输出严格使用 bootstrap 中的 `VERDICT / PLAN_SHA256 / MUST_FIX / SHOULD_FIX /
EVIDENCE / RATIONALE` 格式。只有完整新 SHA 且无 must-fix 才能 approved。
