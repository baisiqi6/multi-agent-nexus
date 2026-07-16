# P9-3C1 P3 Retry Incident Package IR-A — Replacement Correction Result Review

状态：`REQUEST_CHANGES_ALL_MERGE_DEPLOY_RECOVER_RESUME_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Exact candidate authority

- Candidate：`97fbec23f915b887ba549091377e196c6ed2f72b`。
- Exact parent：`f76e4b51eda38f658237590e412a425e29c7b8d0`。
- Exact subject：`fix(p9-3c1): harden incident recover input`。
- Changed paths only：
  - `scripts/production-mutation-lock.py`；
  - `tests/test_production_mutation_lock.py`。
- Diffstat：`1649 insertions(+), 34 deletions(-)`；candidate worktree tracked clean。
- Native worker provider/model：`kat-coder/kat-coder-pro-v2.5`。
- Native worker JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-correction-worker-kat-coder-pro-v2.5/2026-07-16T17-10-15-160Z_019f6be8-5178-7000-9c2a-5b2223203400.jsonl`。
- Worker JSONL SHA-256：`339bfd166c178dc43c12555b415b56d41744470150a438c89283263bd7bed1e1`。

The candidate is immutable rejection evidence。Do not amend、merge、deploy or use it for P0 recovery。

## 2. Green gates do not establish acceptance

Worker and independent Codex reruns agree on：

- `py_compile`：PASS；
- helper suite：`160 passed`；
- deploy contract：`39 passed`；
- full suite：`1136 passed, 2 skipped, 81 subtests passed`；
- `git diff --check`：PASS。

These green gates coexist with a directly reproduced fail-closed runtime escape and mandatory tests that do not
reach the authority seams named by their test names。

## 3. Codex blocking findings

### P1 — out-of-range positive PID escapes through `os.kill(pid, 0)`

`_default_enumerate_pids()` accepts every positive decimal integer with no reviewed Linux PID upper bound。
When `/proc/<pid>/cmdline` returns `ENOENT/ESRCH`，`_probe_processes_default()` invokes `kill_0(pid, 0)` but
catches only `OSError`。Python raises `OverflowError` before the syscall for values outside the C integer range，
so the exception escapes instead of producing bounded `ok=False` authority。

Independent isolated reproductions：

```text
2147483648 ESCAPED OverflowError signed integer is greater than maximum
1000000000000000000000000000000 ESCAPED OverflowError Python int too large to convert to C long
```

The reviewed confirmed-exit contract allows only `/proc ENOENT|ESRCH` plus `kill(pid, 0) == ESRCH` to pass；
success、`EPERM` **or any other error** must block。Required correction：apply a fixed reviewed Linux PID value
bound during enumeration and independently normalize `OverflowError`/`ValueError` from the existence probe to a
static blocked result。Add direct boundary and exception regressions。

### P1 — the mandatory embedded-NUL test-first row never existed

The correction bootstrap required the rejected runtime failure run to demonstrate that an embedded-NUL
token-file path escaped structured `LockError`。The preserved failure run contains only six failures：release、
systemd blank/stderr、PID stderr and cmdline `65537`/missing-NUL；there is no embedded-NUL failure。

The final `test_embedded_nul_final_component_produces_structured_lockerror` does not repair the evidence gap：
it calls `_read_token_file("/tmp/token")` while `/tmp` is mode `1777`，so validation blocks at the parent-mode
check before the mocked `_open(ValueError)` seam is called。It also acquires no synthetic lock and asserts no
audit/release state，despite the zero-mutation requirement。

Required correction：use a test-owned `0700` parent with rewritten root:root authority and an actual NUL in the
final component；prove the open seam is reached，the result is `LockError(state="blocked", exit_code=4)`，the
lock remains held and no audit exists。

### P1 — several mandatory token-file tests are name-only coverage

- `test_token_file_no_newline_reaches_recover` creates two token files but never calls `_read_token_file()`；it
  passes the direct acquire token straight to `recover()`。
- `test_growth_probe_detected_blocks` opens the file `O_RDONLY` and then calls `os.write()` inside the `_open`
  shim；the write fails and is normalized as `token-file open failed` before the growth probe。
- `test_truncated_on_read_blocks` similarly calls `os.ftruncate()` on the `O_RDONLY` descriptor and exits through
  the open-error branch before the short-read check。

These are explicit bootstrap authorities，not optional cosmetic tests。Required correction：make no-LF and LF
token files each pass through `_read_token_file()` into exactly one successful recover；inject read results at the
`os.read` seam so short/growth rows reach `len(raw) != size` without mutating an `O_RDONLY` descriptor；assert
bounded error、retained lock and absent audit。

## 4. Independent result review

- Provider/model：`minimax-code-cn/MiniMax-M3`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-correction-result-review-minimax-m3/2026-07-16T17-37-05-707Z_019f6c00-e4ab-7000-b856-83038ee934b6.jsonl`。
- JSONL SHA-256：`ac97067116d11ae38114fbe5b6a967cbf3090d3c30d034d5f71e7b253341b915`。
- Verdict：`APPROVE / P0_P1: NONE`。

The reviewer independently noted the no-LF、growth and truncated tests do not reach their named seams，but
classified them P2。It did not test out-of-range PID authority or the embedded-NUL final-component call path。
Codex therefore does not adopt the approval。The dual-approval gate is not satisfied。

## 5. Replacement boundary

A fresh replacement candidate must start from exact `f76e4b51...`，may apply the exact two-file
`f76e4b51..97fbec23` diff only as an uncommitted starting tree，and must create a new single commit after the next
reviewed correction bootstrap。The rejected commit remains immutable。

Production remains frozen。No cherry-pick、merge、push of candidate code、deploy、P0 recover/release、cleanup、
resume、service or DB mutation is authorized。

P9_3C1_P3_RETRY_INCIDENT_IR_A_CORRECTION_RESULT_REQUEST_CHANGES_ALL_MERGE_DEPLOY_RECOVER_RESUME_BLOCKED
