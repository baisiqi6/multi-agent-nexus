# P9-3C1 P3 Retry Incident Package IR-A — Result Review

状态：`REQUEST_CHANGES_ALL_MERGE_DEPLOY_RECOVER_RESUME_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Exact candidate authority

- Worker base/parent：`f76e4b51eda38f658237590e412a425e29c7b8d0`。
- Rejected worker commit：`3f337eb243dfa229ac3d25c5b08636ad0de1b9d9`。
- Exact subject：`fix(p9-3c1): harden incident recover input`。
- Changed paths only：
  - `scripts/production-mutation-lock.py`；
  - `tests/test_production_mutation_lock.py`。
- Diffstat：`1040 insertions(+), 31 deletions(-)`；candidate worktree tracked clean。
- The candidate remains immutable rejection evidence and is not merged or deployed。

## 2. Worker evidence

- Native provider/model：`deepseek/deepseek-v4-pro`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-worker-deepseek-v4-pro-retry/2026-07-16T16-14-26-807Z_019f6bb5-39f7-7000-be65-4b8bdf22e7fa.jsonl`。
- JSONL SHA：`c230129e1e2d0b6ae7659464d0ae8b2e92ca18ab38163f3f52043b0076f1ee02`。
- Test-first evidence exists：new tests failed before runtime implementation；the worker then produced one exact
  commit with the reviewed parent/subject/allowlist。
- Worker gates：helper `117 passed`；deploy contract `39 passed`；full suite
  `1093 passed, 2 skipped, 81 subtests passed`；`py_compile` and diff check clean。

These green suites do not override the uncovered successful-release regression or the reviewed fail-closed
authority gaps below。

## 3. Codex blocking findings

### P0 — successful `release` mutates state but reports failure

`scripts/production-mutation-lock.py:1310-1314` calls `lock.release(...)` but no longer emits
`_json_out(result)` or returns `0`。An isolated CLI reproduction acquired a real synthetic lock and then
released it with the valid token：

```json
{"acquire_rc":0,"lock_exists_after":false,"release_rc":1,"release_stderr":"","release_stdout":""}
```

The lock is removed，but the caller receives failure and no canonical JSON。This breaks the existing release
CLI contract and can cause retry/state divergence。The old suite has only release-failure CLI coverage，so all
reported suites remain green。

Required correction：restore `_json_out(result); return 0` in the successful release branch and add a direct
acquire → successful CLI release regression asserting `rc == 0`、canonical JSON、empty stderr and no raw token。

### P1 — PID enumeration accepts non-empty stderr

`_default_enumerate_pids()` requires `returncode == 0` but ignores `result.stderr`。The reviewed contract
requires empty stderr or one explicitly enumerated compatible header。A direct mocked reproduction with
`returncode=0`、stdout `123` and stderr `unexpected authority warning` returns `[123]` and authorizes the
enumeration。

Required correction：reject non-empty stderr before parsing，bound error reporting，and directly test the
default `subprocess.run` path rather than only injecting an already-parsed PID list。

### P1 — the `64 KiB + 1` cmdline sentinel is authorized

`_default_read_cmdline()` reads exactly `_MAX_CMDLINE_READ == 64 KiB + 1`。The later guard checks
`len(raw) > _MAX_CMDLINE_READ`，which is unreachable。A direct reproduction passing exactly `65537` unrelated
bytes returns `ok=True`。The extra byte is the oversize sentinel and must block；silently classifying its
truncated prefix is not a bounded authority proof。

Required correction：treat `len(raw) == 64 KiB + 1` as oversized/fail-closed；add exact `65536` and `65537`
boundary tests through the real parser seam。

### P1 — mandatory test matrix is materially incomplete

The worker final report says PID stderr/oversize/duplicate/count/malformed paths are covered，but
`ProcessProbeDefaultTests` injects a pre-parsed PID list and has no direct tests for
`_default_enumerate_pids()`。It also defines but never exercises the probe-self argv，and has no editor row。
Token-file tests do not directly exercise parent/file wrong-owner or non-regular-file boundaries because the
shared fixture rewrites every temp path to root:root。Systemd tests treat internal blank output as ignorable
although the reviewed bootstrap requires malformed output to block。

Required correction：add direct regression rows for every listed boundary without weakening production code
or using mocks that bypass the parser/validator under test。

### P1 — some token-file path errors escape structured `LockError`

`_read_token_file()` catches only `OSError` around `lstat/open/fstat/read`。Path/open failures such as an
embedded-NUL `ValueError` escape the bounded structured error contract and can print a traceback instead of a
redacted `LockError` response。Required correction：normalize every supported path/stat/open/read failure to a
bounded static reason and add a zero-mutation CLI test。

## 4. Accepted implementation portions

- exact anchored E1/E2 systemd family regex；
- direct `ps -e -o pid=` architecture and exact `/proc/<pid>/cmdline` classification approach；
- controller identity and fixture module plus exactly one adjacent `--agent <fixture-id>` pair；
- confirmed-exit `ENOENT/ESRCH` plus `kill(pid, 0) == ESRCH` rule；
- token-file immediate-parent/final-component ownership、mode、nlink、size、content and second-fstat model；
- raw token redaction and existing recover ordering；
- exact parent/subject/allowlist and test-first workflow。

The fixture identity deliberately permits other real fixture arguments while requiring exactly one valid
adjacent agent pair。The independent reviewer suggestion to require `len(argv) == 5` is not adopted because it
would reject the actual production fixture command shape。

## 5. Independent result review

- Reviewer provider/model：`minimax-code-cn/MiniMax-M3`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-result-review-minimax-m3/2026-07-16T16-37-50-945Z_019f6bca-a6e1-7000-a602-b6f2efa6069d.jsonl`。
- JSONL SHA：`ab7a748c089953c66de0755c9ec6d575636f4c3be894ea3ed506e4b263710a96`。
- Exact verdict：`REQUEST_CHANGES`。
- Reviewer independently reproduced the successful-release P0 and reran helper/deploy suites
  (`117 / 39 passed`)。

The reviewer classified the cmdline sentinel and missing default-enumerator tests as P2。Codex does not adopt
that severity：both belong to the explicit reviewed fail-closed authorization envelope，and the `65537` direct
reproduction is an actual false authorization。This difference does not affect the shared rejection verdict。

## 6. Replacement boundary

The rejected commit must not be amended、merged or deployed。A replacement candidate starts from exact
`f76e4b51...` and may mechanically apply the rejected two-file diff only as an uncommitted starting point，then
must correct every finding and produce a new single commit with the exact subject。It must not change controller、
shell、deploy、Coordinate or docs files。

No P0 recover、release、cleanup、resume、deploy、service or DB mutation is authorized。Production remains
frozen on the previously recorded incident authority。

P9_3C1_P3_RETRY_INCIDENT_IR_A_RESULT_REQUEST_CHANGES_ALL_MERGE_DEPLOY_RECOVER_RESUME_BLOCKED
