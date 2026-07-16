# P9-3C1 P3 Retry Incident Package IR-A — Replacement Correction Round 2 Plan

状态：`READY_FOR_INDEPENDENT_PLAN_REVIEW_IMPLEMENTATION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Objective and immutable evidence

Replace rejected candidate `97fbec23f915b887ba549091377e196c6ed2f72b` with one clean candidate whose
parent is exact `f76e4b51eda38f658237590e412a425e29c7b8d0`。Preserve the accepted helper architecture and all prior
fixes while closing the out-of-range PID exception escape and replacing name-only token-file tests with direct
authority coverage。

Rejected candidates `3f337eb2` and `97fbec23` plus their native JSONL remain immutable evidence；do not amend、
merge or deploy either candidate。

## 2. Scope and construction

Exact allowlist remains：

- `scripts/production-mutation-lock.py`；
- `tests/test_production_mutation_lock.py`。

Create a fresh clean worktree/branch at exact base。The worker may use：

```bash
git diff f76e4b51eda38f658237590e412a425e29c7b8d0..97fbec23f915b887ba549091377e196c6ed2f72b \
  -- scripts/production-mutation-lock.py tests/test_production_mutation_lock.py | git apply
```

only to construct an uncommitted starting tree。No cherry-pick、amend、rebase、other path、SSH/network、sessions
read or production action。

## 3. Runtime correction

### 3.1 Bounded Linux PID value

Introduce one fixed reviewed Linux PID upper bound of `2147483647`。`_default_enumerate_pids()` must reject
zero、negative and values greater than that bound with bounded static `OSError`。Do not read mutable host
`pid_max` as recovery authority。

### 3.2 Existence-probe exception normalization

Keep the confirmed-exit rule exact：only cmdline `ENOENT|ESRCH` followed by `kill(pid, 0)` raising
`OSError(errno.ESRCH)` may pass。`kill` success、`EPERM`、all other `OSError`、`OverflowError` and `ValueError`
must return `ok=False` with a bounded static reason containing at most the validated PID number。No exception text
may enter reason/detail。

No other runtime semantics change。In particular preserve release rc/JSON、systemd exact regex/parser、cmdline
`65536/65537` boundary、fixture extra-argument behavior、token-file validation/order/redaction and direct-token
compatibility。

## 4. Mandatory direct tests

### 4.1 Test-first runtime failure

Before changing runtime beyond the mechanically applied `97fbec23` tree，add and run direct regressions showing
at least：

- enumerator rejects `2147483648`；
- process probe normalizes injected `OverflowError` from `kill_0` to `ok=False` rather than raising；
- `2147483647` remains the accepted numeric boundary；
- `kill_0` success、`EPERM`、other `OSError` and `ValueError` all block，while exact `ESRCH` passes。

Preserve the exact failing output before runtime correction。

### 4.2 Replace bypassed token-file rows

- Actual final-component embedded NUL under a test-owned `0700` root:root-authorized parent must reach the open
  seam and produce structured `LockError(state="blocked", exit_code=4)`；assert the open seam was invoked、the
  synthetic lock remains and audit is absent。
- Valid no-LF and one-LF files must each call `_read_token_file()` and then exactly one successful `recover()`；
  assert lock release、durable audit receipt and raw-token redaction。
- Short read and one-byte growth must be injected at `production_mutation_lock.os.read` (or an equivalently direct
  read seam) after a valid first `fstat`，not by writing/truncating an `O_RDONLY` descriptor；prove the intended
  size-change branch was reached with bounded error、retained lock and absent audit。
- Keep direct wrong uid/gid、non-regular、symlink、hardlink、mode、content、race、audit/fsync/release-order tests
  green。No skip/xfail、test deletion、blanket root:root bypass or misleading test names。

## 5. Worker and reviewer routing

First Coding worker：OMP `kat-coder/kat-coder-pro-v2.5`。Native JSONL must prove provider/model and preserve
test-first failures。If unavailable or capped，use the already approved fallback order without mixing worktrees。

After worker completion：Codex performs exact diff/reproductions；a different non-KAT non-Codex result reviewer
must review the exact commit。Worker self-report and green suites do not authorize acceptance。

## 6. Gates and commit boundary

Canonical Python：`/Users/yinxin/projects/multinexus/.venv/bin/python`。

```bash
/Users/yinxin/projects/multinexus/.venv/bin/python -m py_compile scripts/production-mutation-lock.py tests/test_production_mutation_lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_production_mutation_lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_deploy_contract.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q
git diff --check
```

Full-suite timeout at least `20m`；timeout is not PASS。Create exactly one new commit with exact parent、two-path
allowlist and subject：

```text
fix(p9-3c1): harden incident recover input
```

Only exact Codex plus independent result-review approval authorizes cherry-pick onto current main。IR-A merge
still does not authorize deploy or P0 recovery；IR-B remains a later reviewed package。

P9_3C1_P3_RETRY_INCIDENT_IR_A_CORRECTION_ROUND2_PLAN_READY_FOR_INDEPENDENT_REVIEW_IMPLEMENTATION_BLOCKED
