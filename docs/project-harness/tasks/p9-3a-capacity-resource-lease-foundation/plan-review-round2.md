# P9-3A Independent Plan Review — Round 2

- Reviewer: fresh ordinary Kimi session through Oh-My-Pi
- Model: `kimi-code/kimi-for-coding` (not highspeed)
- Session: `019f5c48-3930-7000-9f4b-dfd51277046b`
- JSONL:
  `/Users/yinxin/.omp/agent/sessions/-projects-multinexus/2026-07-13T16-21-04-944Z_019f5c48-3930-7000-9f4b-dfd51277046b.jsonl`
- Reviewed plan SHA-256:
  `10b9238e821a514745f20105f844887f760bf492d5a921206789493ce4a78d1c`
- `plan.ready`: `5f9dd7da-a7af-450f-b802-776736cf6cfe`
- `plan.review_requested`: `80a4ef98-7d6a-4d53-a5e5-b193f0229988`
- Verdict: `approved`

## Reviewer report

```text
VERDICT: approved
PLAN_SHA256: 10b9238e821a514745f20105f844887f760bf492d5a921206789493ce4a78d1c
MUST_FIX:
- none
SHOULD_FIX:
- 显式说明 executor sync 与 capacity sync 独立事务之间的一致性窗口、检测命令、
  doctor 失败语义和回滚路径。
- 明确 reserve 初始 TTL 边界；当前 renewal 已写 30..600 秒。
- 展开 capacity_policy_id 的 exact canonical digest object，保证跨仓 fixture 一致。
EVIDENCE:
- plan.md 字节级 SHA-256 与 Round 2 supplement 一致。
- Coordinate baseline、MultiNexus implementation-code baseline、schema v12、executor
  catalog hash 与只读验证一致。
- capacity 独立投影、无 binding FK、lease stable-entity FK、scoped expiry 和 P9-3A
  非目标均闭合 Round 2 重点问题。
RATIONALE:
修订后的 authority、schema、transaction、path normalization、deploy parity 与 scope
足以安全派发；三条建议用于减少 worker 对细节的猜测，不构成 must-fix。
```

## Codex disposition

Codex 接受三条精度建议：计划进一步写明 canonical policy-id bytes、reserve 初始 TTL，
以及独立 sync 的 guarded transitional window、失败阶段、恢复与 P9-3B 重新收紧责任。
因此 Round 2 approval 不授权修订后的 plan，需 fresh SHA 与窄范围 Round 3 re-review。
