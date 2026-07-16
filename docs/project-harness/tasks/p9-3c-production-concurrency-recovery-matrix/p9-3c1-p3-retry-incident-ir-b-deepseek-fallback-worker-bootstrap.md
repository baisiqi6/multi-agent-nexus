# P9-3C1 P3 Retry Incident IR-B — DeepSeek V4 Pro Fallback Worker Bootstrap

状态：`DRAFT_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_LOCAL_WORK_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Authority and inherited protocol

You are the replacement non-Codex Coding worker，invoked with OMP model
`deepseek/deepseek-v4-pro` at `thinking=high`。Codex remains architect/operator/test-gate reviewer/result reviewer。

Read completely and obey：

1. the approved IR-B controller recovery plan and plan review；
2. the original approved IR-B worker bootstrap and bootstrap review；
3. the KAT attempt rejection；
4. the Claude-hosted Kimi correction worker bootstrap and accepted review；
5. the Claude-hosted Kimi transport-failure record。

This bootstrap changes only worker transport/model and fresh worktree coordinates。Every T1/T2/I fixture rule，
exact gate token，allowlist，test command，single-commit rule and production prohibition in the correction
bootstrap remains mandatory without weakening。

The KAT and Claude branches/worktrees/JSONL are negative evidence only。Do not read or reuse their source/test
diffs，patches，helper names or sessions。No subagents。

## 2. Exact fresh base and assignment

The operator supplies exact `WORKER_BASE` after this bootstrap and its independent review are committed and
pushed。Before any edit require：

```bash
test "$(git rev-parse HEAD)" = "$WORKER_BASE"
test "$(git rev-parse origin/main)" = "$WORKER_BASE"
test -z "$(git status --short)"
git diff --quiet 6ba82a90d3cf0390eba97c472d8eff62261a9d90.."$WORKER_BASE" -- \
  scripts multinexus tests config agents.toml
```

Fresh assignment：

- worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p3-retry-incident-ir-b-deepseek-r1`；
- branch：`agents/deepseek/p9-3c1-p3-retry-incident-ir-b-r1`；
- parent：exact launch-time `WORKER_BASE`。

Allowed paths remain only：

- `scripts/p9_3c1_controller.py`；
- `tests/test_p9_3c1_production_controller.py`；
- `tests/test_deploy_contract.py` only under the correction bootstrap's narrow condition。

## 3. Mandatory staged turns

Use one resumable native OMP session across all authorized stages and preserve its JSONL outside the worktree。

### T1 only

The first turn may edit only `tests/test_p9_3c1_production_controller.py` and may add only the four correction-
bootstrap T1 tests。Runtime and every other file remain byte-identical。Run only those four tests，fix all
fixture-first failures，then stop without commit at exact output `T1_READY_FOR_CODEX_REVIEW`。

No similar text grants continuation。Only exact operator token `T1_APPROVED_CONTINUE_TESTS_ONLY` opens T2。

### T2 only

T2 remains tests-only and must implement the complete reviewed matrix。Stop without commit at exact output
`T2_READY_FOR_CODEX_REVIEW`。No similar text grants implementation authority。Only exact operator token
`T2_APPROVED_IMPLEMENT` opens runtime implementation。

### Implementation

After the exact implementation token，implement the complete reviewed plan and correction-bootstrap runtime
requirements，run every prescribed gate and create exactly one commit with parent `WORKER_BASE` and subject：

```text
fix(p9-3c1): add reviewed incident cleanup resume
```

Do not amend、push、merge or deploy。

## 4. Hard prohibitions

No network、SSH、production/state-root/token/auth/DB/service access、P0 recover/release、cleanup/resume invocation、
deploy、push/merge、sessions read or subagents。The worker may write only its native OMP JSONL through the
operator-controlled session directory and must never open that directory。

Any ambiguity，fixture that does not reach the intended runtime behavior，unexpected path change or conflict with
the approved plan is `BLOCKED`，not permission to improvise or broaden authority。

P9_3C1_P3_RETRY_INCIDENT_IR_B_DEEPSEEK_FALLBACK_BOOTSTRAP_AWAITING_INDEPENDENT_REVIEW_ALL_LOCAL_WORK_AND_PRODUCTION_MUTATION_BLOCKED
