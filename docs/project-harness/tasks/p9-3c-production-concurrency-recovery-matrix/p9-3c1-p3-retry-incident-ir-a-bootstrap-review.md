# P9-3C1 P3 Retry Incident Package IR-A — Bootstrap Review

状态：`APPROVED_FOR_BOUNDED_LOCAL_KAT_IMPLEMENTATION_ONLY_ALL_PRODUCTION_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Exact reviewed authority

- Exact base：`f76e4b51eda38f658237590e412a425e29c7b8d0`。
- Bootstrap：`p9-3c1-p3-retry-incident-ir-a-worker-bootstrap.md`。
- Final replacement bootstrap SHA：`674773300dc5662c7d7abcf070d5ca88ebb0f2242f502df457eea2abe7796a81`。
- Allowed implementation paths only：
  - `scripts/production-mutation-lock.py`；
  - `tests/test_production_mutation_lock.py`。

## 2. Review rounds

Initial reviewer JSONL：

- provider/model：`deepseek/deepseek-v4-pro`；
- path：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-bootstrap-review-deepseek-v4-pro/2026-07-16T15-49-08-560Z_019f6b9e-0f50-7000-af59-2988ec5f843e.jsonl`；
- SHA：`3f5478f06363368df55b9701758b98c811c470f343fd2daf6680279ff3043e4c`。

The initial review returned `APPROVE` but also named two P1 ambiguities。Codex did not treat that as final
authorization。The bootstrap was replaced to add the exact anchored unit regex、explicit `os.kill(pid, 0)`/
`ESRCH` exit proof、EPERM fail-closed behavior、PID-cap rationale、second-fstat time metadata and exact
`receipt_digest` terminology。

Final replacement reviewer JSONL：

- provider/model：`deepseek/deepseek-v4-pro`；
- path：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-bootstrap-replacement-review-deepseek-v4-pro/2026-07-16T15-54-56-913Z_019f6ba3-6011-7000-9826-f859e98b7464.jsonl`；
- SHA：`62eaee7b304cebbe09f3be087a680b1b50be16d5052364b511ee8714ca286326`；
- exact first-line verdict：`APPROVE`；no remaining P0/P1 finding。

## 3. Approved semantics

The reviewer verified the unit regex against actual `_p9c0_unit_name()`，controller argv against the fixed
Python/controller `exec`，and fixture argv against actual `-m multinexus.agentd --agent <id>` construction。
It approved exact NUL argv identity、bounded enumeration、confirmed-exit handling、macOS seams、token-file
TOCTOU authority、zero-mutation/redaction tests、allowlist and gates。

## 4. Authorization boundary

This review authorizes one bounded local KAT worker in a new clean worktree from exact base，one exact commit
and only the two changed paths。It does not authorize merge/push of implementation、deploy、SSH/network、P0
recover/release、production token/auth access、cleanup/run、service/DB mutation or any production action。

P9_3C1_P3_RETRY_INCIDENT_IR_A_BOOTSTRAP_APPROVED_FOR_BOUNDED_LOCAL_KAT_IMPLEMENTATION_ONLY_ALL_PRODUCTION_MUTATION_BLOCKED
