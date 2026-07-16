# P9-3C1 P3 Retry Incident Package IR-A — Replacement Correction Round 2 Result Review

状态：`APPROVED_EXACT_CHERRYPICK_PUSH_ALLOWED_DEPLOY_RECOVER_RESUME_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Exact candidate authority

- Candidate：`9550fbb288e7e07f5d8e0335b8594a0a1c7e56bd`。
- Exact parent：`f76e4b51eda38f658237590e412a425e29c7b8d0`。
- Exact subject：`fix(p9-3c1): harden incident recover input`。
- Exact changed paths：
  - `scripts/production-mutation-lock.py`；
  - `tests/test_production_mutation_lock.py`。
- Diffstat：`1819 insertions(+), 34 deletions(-)`；candidate worktree tracked clean。
- Native worker provider/model：`kat-coder/kat-coder-pro-v2.5`。
- Native worker JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-correction-r2-worker-kat-coder-pro-v2.5/2026-07-16T18-09-56-038Z_019f6c1e-f546-7000-b1ae-ad9008251585.jsonl`。
- Worker JSONL SHA-256：`bc9f98105596867c46beba5f3b87bceb09c978f5a0bb4945f925bc63d129ff55`。

## 2. Test-first evidence boundary

The valid rejected-runtime failures are exactly：

- `2147483648` accepted instead of bounded enumerator rejection；
- kill `OverflowError` escaped；
- kill `ValueError` escaped。

The first draft also failed while trying to create a filesystem path containing NUL with
`Path.write_bytes()`。That was a test-construction failure，not runtime negative evidence，and is not counted。
The final embedded-NUL test creates a normal file under a valid parent and passes an actual NUL only in the final
component string to `_read_token_file()`，where real `os.open` is reached exactly once。

## 3. Codex result review

Codex confirmed：

- `_MAX_PID_VALUE = 2147483647` blocks before append and preserves strict decimal、`1 MiB` output、`131072`
  count and duplicate contracts；
- exact confirmed-exit sole pass remains `/proc ENOENT|ESRCH` plus `kill OSError(ESRCH)`；kill success、`EPERM`、
  other `OSError`、`OverflowError` and `ValueError` all return bounded `ok=False` with no exception text；
- the nine Round 2 tests directly reach enumerator、kill、real embedded-NUL open、no-LF/LF
  `_read_token_file -> recover`、one-line audit/redaction and module-level `os.read` short/growth seams；
- six misleading methods from rejected `97fbec23` were deleted exactly，while wrong-owner、non-regular、
  embedded-NUL-parent and other base authority tests remain；
- runtime changes relative to `97fbec23` are limited to the PID constant、range check and kill exception
  normalization。Release、systemd、cmdline、token-file validation and recover audit-before-release ordering are unchanged。

Independent Codex gates：

- `py_compile`：PASS；
- Round 2 focused：`9 passed`；
- helper：`163 passed`；
- deploy contract：`39 passed`；
- full suite：`1139 passed, 2 skipped, 81 subtests passed`；
- `git diff --check`：PASS。

## 4. Independent result review

- Provider/model：`xfyun/xopglm52`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-correction-r2-result-review-glm52/2026-07-16T18-30-38-013Z_019f6c31-e8bd-7000-a422-8f4772107bdb.jsonl`。
- JSONL SHA-256：`b83ac3a16b4c3f077363f5902562de6d97b57685000c3cb83ecfe7f851b52947`。
- Exact verdict：`VERDICT: APPROVE / P0_P1: NONE`。
- Independent gates：helper `163 passed`、deploy contract `39 passed`、full suite
  `1139 passed, 2 skipped, 81 subtests passed`、py_compile/diff-check PASS。

The reviewer found no P0/P1/P2 and explicitly preserved the three-failure test-first evidence boundary。

## 5. Acceptance boundary

Dual approval authorizes only exact cherry-pick of `9550fbb2` onto current main and push，followed by combined
main gates。It does not authorize deploy、P0 recover/release、cleanup、resume、service or DB mutation。

IR-A alone is not production-deployable。IR-B controller incident recovery remains a separately planned、reviewed
and implemented package before any combined production decision。

P9_3C1_P3_RETRY_INCIDENT_IR_A_CORRECTION_ROUND2_RESULT_APPROVED_EXACT_CHERRYPICK_PUSH_ALLOWED_DEPLOY_RECOVER_RESUME_BLOCKED
