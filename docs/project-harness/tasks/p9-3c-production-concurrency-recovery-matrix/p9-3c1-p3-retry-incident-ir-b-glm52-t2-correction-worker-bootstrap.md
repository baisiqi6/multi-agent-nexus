# P9-3C1 P3 Retry Incident IR-B — GLM 5.2 T2 Correction Worker Bootstrap

状态：`DRAFT_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_LOCAL_WORK_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Role and authority

You are the replacement non-Codex tests-only worker，invoked through OMP exact model `xfyun/xopglm52`。Codex
remains architect/operator/checkpoint reviewer/result reviewer。

Read the approved IR-B plan/review、correction bootstrap/reviews、T1 review、T2 decomposition addendum/review and
DeepSeek T2 attempt review。This bootstrap changes only worker model、fresh worktree and the operator-applied
accepted T1 patch。All no-network/no-production/no-runtime/no-commit boundaries remain mandatory。

KAT、Claude and DeepSeek source/test diffs、worktrees、branches and sessions are prohibited。The only reusable
worker output is the exact independently accepted T1 patch identified below，applied by the operator before
launch。The worker must not read sessions。

## 2. Fresh base and exact pre-applied T1 state

After this bootstrap and its review are committed/pushed，the operator supplies exact `WORKER_BASE` and creates：

- worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p3-retry-incident-ir-b-glm52-r1`；
- branch：`agents/glm52/p9-3c1-p3-retry-incident-ir-b-r1`；
- parent：exact `WORKER_BASE`。

The operator，not the worker，applies the accepted patch with SHA-256
`95e0b9cd4f823099bf4f8197fce27679296d1b51b3e4434e8d9ff4220c54be33`。Before worker launch the required state is：

```text
git diff --numstat == 320 0 tests/test_p9_3c1_production_controller.py
sha256(tests/test_p9_3c1_production_controller.py) ==
1723293f2c3d9bc2963340fe2af5c483b19d6fd9ef37748d90edcce8a3bdf905
git diff --name-only == tests/test_p9_3c1_production_controller.py
runtime/deploy-contract diff == empty
```

The worker verifies these values without opening the patch/session path。Any mismatch is `BLOCKED`。

## 3. T2 staged authority

The first worker turn is T2-A tests-only。Implement every item in the approved T2 decomposition addendum §3-§6，
using its exact six helper contracts and complete A1-A5 matrices。Representative sampling is not completion。

Only `tests/test_p9_3c1_production_controller.py` may change。No runtime、deploy-contract、docs or other path。
Every correct-runtime rejection must use `pytest.raises(ControllerError, match=<boundary>)` while the unchanged
runtime's missing helper `AttributeError` escapes。Positive fixtures must be capable of passing a correct
implementation。No test-owned implementation、placeholder authority、tracked TOML mutation or source-text test。

Stop without commit at exact `T2A_READY_FOR_CODEX_REVIEW` and enumerate every A1-A5 case plus exact negative
reason。Only an exact later Codex token may open T2-B，then T2-C，then T2-D。Only all four accepted checkpoints may
produce exact `T2_APPROVED_IMPLEMENT`。

## 4. Hard prohibitions

No network、SSH、production/state-root/token/auth/DB/service access、P0 recover/release、cleanup/resume invocation、
deploy、push/merge、sessions read、subagents or commit。Do not fetch/rebase main after launch。Native OMP JSONL is
written only by the operator-supplied session directory and must never be opened by the worker。

Any ambiguity、incomplete matrix or fixture that would fail a correct implementation is `T2A_BLOCKED` with exact
remaining cases，never permission to sample、improvise or edit runtime。

P9_3C1_P3_RETRY_INCIDENT_IR_B_GLM52_T2_CORRECTION_BOOTSTRAP_AWAITING_INDEPENDENT_REVIEW_ALL_LOCAL_WORK_RUNTIME_AND_PRODUCTION_BLOCKED
