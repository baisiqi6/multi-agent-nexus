# P9-3A Independent Plan Reviewer Supplement — Round 2

本文件覆盖 `plan-reviewer-bootstrap.md` 中旧的 plan SHA。继续遵守其只读、无实现、
无子 agent、无状态变更和有界 verdict 规则。

Round 2 唯一审核对象是当前 `plan.md`，期望完整 SHA-256：

`10b9238e821a514745f20105f844887f760bf492d5a921206789493ce4a78d1c`

Round 1 的 `8b4789...` approval 已因文本修订失效。重点确认以下修订是否真正闭合：

1. `ccb2b6a...` 被明确标注为 implementation-code baseline，后续纯计划提交不应被
   当作代码 drift；
2. current capacity policy 不再 SQL FK 到 replace-style
   `executor_instance_bindings`，但 sync transaction 的 complete coverage validation、
   source FK 与 deploy/doctor parity 是否足以 fail closed，是否产生无法接受的悬空窗口；
3. lease 对 `jobs/agents/runner_profiles` 使用 `ON DELETE RESTRICT` 是否符合历史证据与
   当前实体生命周期；不 FK 到 current capacity policy 是否正确保留 snapshot 历史；
4. reserve 只 expire `target agent OR target resource` 的到期 active lease，是否完整覆盖
   本次 capacity count 和 partial unique resource index 的所有影响行；
5. 修订是否仍严格停留在 P9-3A，没有泄漏 claim/heartbeat/recovery。

输出仍必须严格使用 bootstrap 中的 `VERDICT / PLAN_SHA256 / MUST_FIX /
SHOULD_FIX / EVIDENCE / RATIONALE` 格式。只有完整新 SHA 且无 must-fix 才能 approved。
