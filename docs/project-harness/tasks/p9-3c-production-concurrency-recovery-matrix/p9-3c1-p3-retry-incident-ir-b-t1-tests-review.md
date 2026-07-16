# P9-3C1 P3 Retry Incident IR-B — T1 Tests-only Review

状态：`T1_APPROVED_CONTINUE_TESTS_ONLY`

日期：2026-07-17 Asia/Shanghai

## Candidate and evidence

- worker base：`03bd6c719a4b496178c35beed68668c10f5a3c2e`；
- worker model：`deepseek/deepseek-v4-pro`；
- branch：`agents/deepseek/p9-3c1-p3-retry-incident-ir-b-r1`；
- changed path：`tests/test_p9_3c1_production_controller.py` only；
- native JSONL T1 snapshot：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-b-worker-deepseek-v4-pro-t1/t1-approved-snapshot.jsonl`；
- snapshot lines：`200`；
- snapshot SHA-256：`1fd17fb6519719a4689340a8fb05fab3367801d1ad49ad33fed04a8558c45fbb`。

## Review rounds

The initial checkpoint and R2 were rejected because they omitted exact CLI arguments/dispatch，used incomplete or
invented lock seams，and replaced the transaction under test with a test-owned implementation。R3 fixed the
runtime-facing contracts；R4 added explicit eight-record tail and pre-transaction absence assertions。

Accepted T1 now proves：

1. exact `resume-cleanup --run-id --authorization-file --authorization-sha256` parser and dispatch contract；
2. a valid exact eight-record incident chain ending `machine.failure` then `cleanup.initiated`；
3. old runtime reaches all three sync calls while an injected future classifier returns `TERMINAL_SKIP`；
4. `_acquire_global_lock(run_id)` must use existing stateful `lock_status`/`lock_acquire` seams，transition
   free-to-held，and preserve stale standard bytes；
5. `_execute_token_swap_transaction(run_id, new_token, *, after_install)` must create the fixed temp，perform both
   renames，then preserve archive/new-standard/exact held lock/zero release on injected post-install failure。

## Independent gate evidence

- `py_compile`：PASS；
- T1 focused selection：expected `4 failed`，with exact runtime-missing/wrong reasons and no fixture/path/owner/
  lock/ledger/catalog/SQL failure；
- pre-existing controller tests：`47 passed, 4 deselected`；
- `git diff --check`：PASS；
- runtime and deploy-contract tests versus base：byte-identical；
- no commit。

## Authorization boundary

Codex authorizes exact token `T1_APPROVED_CONTINUE_TESTS_ONLY`。The same worker session may add the complete T2
dynamic test matrix，still without editing runtime or creating a commit。It must stop at
`T2_READY_FOR_CODEX_REVIEW`。

This does not authorize runtime implementation，which remains blocked until exact `T2_APPROVED_IMPLEMENT`。It
never authorizes network/SSH/production access，P0 recover/release，cleanup/resume invocation，push/merge or
deploy。

P9_3C1_P3_RETRY_INCIDENT_IR_B_T1_APPROVED_CONTINUE_TESTS_ONLY_RUNTIME_AND_PRODUCTION_BLOCKED
