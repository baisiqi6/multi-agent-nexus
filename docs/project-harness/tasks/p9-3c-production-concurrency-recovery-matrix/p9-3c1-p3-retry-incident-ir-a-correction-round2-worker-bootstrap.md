# P9-3C1 P3 Retry Incident Package IR-A — Replacement Correction Round 2 Worker Bootstrap

状态：`READY_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Role and exact authority

You are the non-Codex OMP `kat-coder/kat-coder-pro-v2.5` Coding worker。Work only in the assigned isolated
local worktree。No subagent/task、SSH/network、sessions read、production files/DB/token/auth、P0 recover/release、
cleanup/resume、deploy、service/run or other repository。

- Worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p3-retry-incident-ir-a-kat-r3`。
- Branch：`agents/kat/p9-3c1-p3-retry-incident-ir-a-r3`。
- Exact base/parent：`f76e4b51eda38f658237590e412a425e29c7b8d0`。
- Start gate：HEAD equals exact base；tracked clean；no existing commit；do not fetch/pull/rebase/cherry-pick。

Read completely from current main before editing：

- original IR-A bootstrap/review and rejected result review；
- correction plan/review/bootstrap/review and rejected correction result review；
- Round 2 plan and plan review；
- complete current helper and test module。

## 2. Exact allowlist and starting tree

Only：

- `scripts/production-mutation-lock.py`；
- `tests/test_production_mutation_lock.py`。

Construct the rejected `97fbec23` candidate only as an **uncommitted** starting tree：

```bash
git diff f76e4b51eda38f658237590e412a425e29c7b8d0..97fbec23f915b887ba549091377e196c6ed2f72b \
  -- scripts/production-mutation-lock.py tests/test_production_mutation_lock.py | git apply
```

Verify only the two allowlisted paths are modified。Do not cherry-pick、amend or commit rejected candidates。

## 3. Round 2 test-first gate

Before runtime edits beyond the mechanically applied starting tree，add direct tests and run the focused Round 2
selection against `97fbec23` runtime。Preserve exact failing output。The failure run must demonstrate at least：

- `_default_enumerate_pids()` accepts `2147483648` instead of raising bounded `OSError`；
- `_probe_processes_default()` lets injected `kill_0 OverflowError` escape；
- injected `kill_0 ValueError` also escapes。

In the same block add boundary rows for `2147483647` accepted、kill success/`EPERM`/other `OSError` blocked and
exact `ESRCH` passed。Rows already correct in the starting runtime may pass in the test-first run；do not weaken
them to manufacture failures。No skip/xfail、test deletion、timeout hiding or mock bypassing the parser/probe。

## 4. Exact runtime correction

Add a fixed constant `_MAX_PID_VALUE = 2147483647`。After strict `[0-9]+` conversion and the existing positive
check，`_default_enumerate_pids()` must reject `pid > _MAX_PID_VALUE` with bounded static `OSError` before append。
Do not inspect mutable host `pid_max`。

In the confirmed-exit branch，preserve this sole pass：cmdline read raises `OSError` with `ENOENT|ESRCH` and the
subsequent `kill_0(pid, 0)` raises `OSError(errno.ESRCH)`。Normalize `kill_0` `OverflowError` and `ValueError` to
the same bounded blocked result as other non-ESRCH errors。Kill success、`EPERM` and every other `OSError` remain
blocked。No exception text、argv or path may enter reason/detail；only the already validated PID number may be
included。

Do not change release、systemd、cmdline classifier/boundary、token-file validation rules、recover ordering、
direct-token behavior or any other runtime semantics。

## 5. Replace name-only token-file coverage

### 5.1 Embedded-NUL final component

Use a test-owned real `0700` parent whose immediate-parent `lstat` authority is rewritten root:root only for that
exact parent。Create a path whose **final component contains actual `\x00`**。Wrap the real open seam to record
invocation and allow `os.open` to raise `ValueError`；do not use `/tmp/token` or pre-raise from a mock before path
validation。Assert：open invoked once、structured `LockError(state="blocked", exit_code=4)`、bounded reason、
synthetic lock still held and audit absent。

### 5.2 Valid no-LF and one-LF recover

For each form，acquire one synthetic lock，write the exact acquired token to a valid token file，call
`_read_token_file()` and pass its result to exactly one `recover()`。Assert recovered/free state、lock absent、one
durable audit receipt and raw token absent except already approved digest/prefix fields。Remove unused token-file
variables and misleading direct-token-only tests。

### 5.3 Short and growth read

Keep a valid first `fstat` size of `64` or `65`。Patch `production_mutation_lock.os.read` directly (or introduce a
single narrow injectable read seam without expanding public API)：

- short row returns fewer than `size` bytes；
- growth row returns `size + 1` bytes。

Both must reach the `len(raw) != size` branch，raise bounded structured `LockError`，retain an acquired synthetic
lock and leave audit absent。Do not call `os.write` or `os.ftruncate` on the `O_RDONLY` token descriptor。

Keep all ownership、mode、link、content、second-fstat race、audit/fsync and release-order tests green。Wrong-owner
tests must override the exact stat seam per row，not blanket-rewrite the authority being tested。

## 6. Required gates and exact commit

Canonical Python：`/Users/yinxin/projects/multinexus/.venv/bin/python`。

```bash
/Users/yinxin/projects/multinexus/.venv/bin/python -m py_compile scripts/production-mutation-lock.py tests/test_production_mutation_lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_production_mutation_lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_deploy_contract.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q
git diff --check
```

Full-suite timeout at least `20m`；timeout is not PASS。Fix only allowlisted failures。

Create exactly one commit with parent exact base and subject：

```text
fix(p9-3c1): harden incident recover input
```

After commit do not amend。Final report must include exact provider/model、commit/parent/subject/paths/diffstat、
test-first failures、all gate outputs and precise fail-closed semantics。Do not push、merge、deploy or touch
production。Worker completion does not authorize acceptance。

P9_3C1_P3_RETRY_INCIDENT_IR_A_CORRECTION_ROUND2_BOOTSTRAP_READY_FOR_INDEPENDENT_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED
