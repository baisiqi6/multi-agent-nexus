# P9-3C1 P3 Retry Incident IR-B — DeepSeek Fallback Bootstrap Review

状态：`APPROVED_FOR_BOUNDED_LOCAL_T1_TESTS_ONLY`

日期：2026-07-17 Asia/Shanghai

## Reviewed candidate

- candidate commit：`f6fd13c`；
- bootstrap：
  `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c1-p3-retry-incident-ir-b-deepseek-fallback-worker-bootstrap.md`；
- bootstrap SHA-256：`baa62927d1fcd350f48b700535e0ec4a2bf2625ca8bd038366e7bf33422f3157`。

## Independent review evidence

- reviewer：`minimax-code-cn/MiniMax-M3`；
- native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-b-deepseek-fallback-bootstrap-review-minimax-m3-r2/2026-07-16T19-41-27-887Z_019f6c72-c1cf-7000-a7c0-e3522a9a8f58.jsonl`；
- JSONL SHA-256：`70eef81415b9b6aee444bbb1b554cf163a1f7b2770e32eb0901b3a46a6264951`；
- verdict：`APPROVE`；
- severity：`P0: 0 P1: 0 P2: 0`。

The reviewer confirmed that the fallback changes only the worker model/transport and fresh worktree coordinates，
while preserving without weakening：

- exact base and KAT/Claude isolation；
- the four real T1 behavior failures and `T1_READY_FOR_CODEX_REVIEW` stop；
- the exact T1-to-T2 and T2-to-I authorization tokens；
- the complete T2 matrix and runtime authority rules；
- the three-path allowlist，single commit，native JSONL and all final gates；
- the complete network/production/deploy/push/merge/subagent prohibition。

An earlier selector-only attempt resolved the ambiguous name `MiniMax-M3` to an unconfigured provider and exited
before any model call。It produced no verdict and grants no authority。The accepted review used the exact configured selector
shown above。

## Authorization boundary

This approval authorizes only commit/push of this review，then one fresh OMP
`deepseek/deepseek-v4-pro` T1 tests-only turn and Codex review of that uncommitted checkpoint。

It does not authorize T2 without exact `T1_APPROVED_CONTINUE_TESTS_ONLY`，does not authorize runtime
implementation without exact `T2_APPROVED_IMPLEMENT`，and never authorizes production access/mutation，P0
recover/release，cleanup/resume execution，push/merge or deploy。

P9_3C1_P3_RETRY_INCIDENT_IR_B_DEEPSEEK_FALLBACK_BOOTSTRAP_APPROVED_FOR_FRESH_LOCAL_T1_TESTS_ONLY
