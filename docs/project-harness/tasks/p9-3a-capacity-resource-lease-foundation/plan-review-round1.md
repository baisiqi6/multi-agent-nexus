# P9-3A Independent Plan Review — Round 1

- Initial preferred reviewer: GLM 5.2 via Oh-My-Pi
- GLM model: `zhipu-coding-plan/glm-5.2`
- GLM session: `019f5c39-c4f0-7000-a0c8-222a0bc61142`
- GLM JSONL:
  `/Users/yinxin/.omp/agent/sessions/-projects-multinexus/2026-07-13T16-05-17-680Z_019f5c39-c4f0-7000-a0c8-222a0bc61142.jsonl`
- GLM outcome: stopped after multiple bounded observation intervals without a verdict;
  no provider error and no file mutation were observed.
- Completed fallback reviewer: fresh ordinary Kimi session via Oh-My-Pi
- Kimi model: `kimi-code/kimi-for-coding` (not highspeed)
- Kimi session: `019f5c40-e16a-7000-a80a-97e3a1ef8d7d`
- Kimi JSONL:
  `/Users/yinxin/.omp/agent/sessions/-projects-multinexus/2026-07-13T16-13-03-722Z_019f5c40-e16a-7000-a80a-97e3a1ef8d7d.jsonl`
- Reviewed plan SHA-256:
  `8b478937275fb6c85209a959aff19eeee615de15d4627bee1cf273dbdb5c33d0`
- Verdict: `approved`

## Reviewer report

```text
VERDICT: approved
PLAN_SHA256: 8b478937275fb6c85209a959aff19eeee615de15d4627bee1cf273dbdb5c33d0
MUST_FIX:
- none
SHOULD_FIX:
- plan.md 中 MultiNexus baseline 行应更新：当前 main HEAD 为 171ccf06361d316e3d159fdc65b7babc5c003f1a，ccb2b6aee4c66903ebabae2451c657cf815c36ab 是其父提交（即 plan doc 本身），并非当前 main。
- 建议在 execution_attempt_leases 的 schema 描述中显式声明 FK 约束（至少到 jobs.id 与 agents.id/runner_profiles.id），当前计划只写明了 capacity policy 的 FK，容易在实现中遗漏。
- 建议将 reserve 前的 "mark every due active lease as expired" 限定范围（例如同一 agent 或同一资源），避免全局扫描造成不必要的跨 agent 锁竞争。
EVIDENCE:
- plan.md 实际 SHA-256 = 8b478937...5c33d0，与计划声明一致。
- Coordinate main 为 90783b2c...，与计划一致。
- MultiNexus 当前 main 为 171ccf0...；ccb2b6a... 是计划包提交的父提交。
- Coordinate schema 当前为 v12，executor identity 与 MultiNexus registry parser 的
  strict-root/canonical-hash 边界与计划描述相符。
- measurement.md 已复现同一 mac-omp/同一 worktree 可同时 claim 两次的缺口。
RATIONALE:
计划把 capacity 表达为独立版本化投影并保持 P9-2A identity bytes 不变；schema、
transaction、partial unique index、caller-owned transaction 及 P9-3A 非目标足以安全派发。
```

## Codex disposition

Round 1 没有 must-fix，但 Codex 吸收了三条 should-fix 的实质部分，并进一步发现：
若 capacity policy 直接外键到 current executor binding，现有 executor catalog sync 的
replace transaction 会被跨投影 FK 耦合阻断。计划因此改为 source FK + transaction/parity
coverage validation，并显式定义 lease 稳定实体 FK、历史 capacity snapshot 边界和 scoped
expiry。任何文本变更都会产生新 SHA，因此 Round 1 approval 不授权 worker；修订版必须产生
fresh `plan.ready` 并独立重审。
