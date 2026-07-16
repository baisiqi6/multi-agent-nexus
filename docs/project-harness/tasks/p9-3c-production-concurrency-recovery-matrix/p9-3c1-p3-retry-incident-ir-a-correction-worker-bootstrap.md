# P9-3C1 P3 Retry Incident Package IR-A — Replacement Correction Worker Bootstrap

状态：`READY_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Role and exact authority

You are the non-Codex OMP `kat-coder/kat-coder-pro-v2.5` Coding worker for the IR-A replacement correction。
Work only in the assigned isolated local worktree。No subagent/task、SSH/network、sessions read、production
files/DB/token/auth、P0 recover/release、cleanup/resume、deploy、service/run or other repository。

- Worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p3-retry-incident-ir-a-kat-r2`。
- Branch：`agents/kat/p9-3c1-p3-retry-incident-ir-a-r2`。
- Exact base/parent：`f76e4b51eda38f658237590e412a425e29c7b8d0`。
- Start gate：HEAD equals exact base；tracked clean；no existing commit；do not fetch/pull/rebase/cherry-pick。

Read completely from current main docs before editing：

- original IR-A worker bootstrap and bootstrap review；
- `p9-3c1-p3-retry-incident-ir-a-result-review.md`；
- `p9-3c1-p3-retry-incident-ir-a-correction-plan.md`；
- `p9-3c1-p3-retry-incident-ir-a-correction-plan-review.md`。

## 2. Exact allowlist and starting tree

Only：

- `scripts/production-mutation-lock.py`；
- `tests/test_production_mutation_lock.py`。

You may construct the rejected candidate as an **uncommitted** starting tree with exactly：

```bash
git diff f76e4b51eda38f658237590e412a425e29c7b8d0..3f337eb243dfa229ac3d25c5b08636ad0de1b9d9 \
  -- scripts/production-mutation-lock.py tests/test_production_mutation_lock.py | git apply
```

Verify only the two allowlisted paths are modified。Do not cherry-pick or amend rejected commit `3f337eb2`。

## 3. Correction test-first gate

Before changing runtime beyond the mechanically applied rejected diff，add correction regression tests and run
them against that rejected runtime。Preserve exact failing output。At minimum the failure run must demonstrate：

- successful CLI `release` returns wrong rc/output；
- non-empty `ps` stderr is accepted；
- exactly `65537` cmdline bytes are accepted；
- embedded-NUL token-file path escapes structured `LockError`。

The remaining mandatory coverage may be added in the same test-first block。No skip/xfail、test deletion、
timeout hiding or mock that bypasses the parser/validator being asserted。

## 4. Exact runtime corrections

### 4.1 Successful release contract

The successful `release` CLI branch must call `_json_out(result)` and return `0` immediately。Failure behavior
remains unchanged。It must not fall through into `recover` or the final `return 1`。

### 4.2 Systemd authority

Keep the direct `systemctl list-units` argv、`shell=False` behavior、10-second timeout and exact target regex：

```text
^p9-3c-fixture-e[12]-p9-3c1-prod-[0-9]{8}t[0-9]{6}z-[a-f0-9]{8}\.service$
```

Require `returncode == 0`、empty stderr and stdout no larger than `1 MiB`。Empty stdout is valid no-unit proof。
For every returned line：blank/whitespace-only line blocks；otherwise require at least four whitespace columns
(`UNIT LOAD ACTIVE SUB`) and first column ending in `.service` with no whitespace/control characters。A valid
unrelated/obsolete service row passes；only a full exact target match blocks。Missing、decode、timeout、malformed、
nonzero、stderr or oversized output blocks with bounded static reason，never raw subprocess output。

### 4.3 Default PID enumeration

Keep exactly：

```python
subprocess.run(
    ["ps", "-e", "-o", "pid="],
    shell=False,
    timeout=10,
    capture_output=True,
    text=True,
)
```

Require `returncode == 0`、empty stderr、stdout encoded size no larger than `1 MiB`。Each non-blank stripped row
must full-match `[0-9]+` and convert to a positive PID。Reject duplicates and more than `131072` unique PIDs。
Every failure is bounded/static and is returned by the process probe as `ok=False`。

### 4.4 Exact cmdline boundary and parsing

Read `/proc/<pid>/cmdline` at most `65537` bytes。Exactly `65537` bytes is the oversize sentinel and blocks；
only `<=65536` proceeds。Empty bytes or one NUL byte may represent a kernel thread and may pass。Every other
authority must end with NUL，decode as UTF-8 and contain no empty leading/interior argv。Decode、shape、read、
permission or inconsistent authority blocks。

Keep the confirmed-exit rule exact：only `/proc` `ENOENT/ESRCH` plus `os.kill(pid, 0)` `ESRCH` passes。Success、
`EPERM` or any other error blocks。Skip only `os.getpid()`。

Block controller exact prefix：

```text
/usr/bin/python3.12 /opt/multinexus/scripts/p9_3c1_controller.py
```

Block fixture exact Python/module prefix plus exactly one adjacent `--agent p9-3c-fixture-e1|e2` pair。Other
real fixture arguments remain permitted；do not require `len(argv) == 5`。Duplicate/missing agent structure with
the exact module plus fixture id is malformed and blocks。Report only PID numbers，never argv/token paths。

### 4.5 Token-file structured errors

Keep the accepted ownership/mode/nlink/size/read/second-fstat/content rules unchanged。Convert path/stat/open/
fstat/read path-shape `ValueError` and `OSError` into `LockError(state="blocked", exit_code=4)` with bounded static
reasons。Do not interpolate exception text、untrusted path or token content。Validation failure occurs before
`recover()`、audit or release。Raw token remains absent from argv/stdout/stderr/detail/audit except approved
digest/prefix fields generated by existing recovery logic。

## 5. Mandatory direct tests

### CLI/release

- acquire synthetic lock → valid CLI release：`rc == 0`，one canonical JSON object with
  `state == "released"`/`phase == "free"`，empty stderr，lock absent，raw token absent from output；
- existing release mismatch remains nonzero and redacted。

### Systemd

- exact E1/E2 block；unrelated、obsolete、partial prefix、suffix-added target pass；empty stdout passes；
- missing、nonzero、non-empty stderr、oversized、single-column、wrong non-service first column and internal blank
  row block；assert exact subprocess argv/flags。

### PID enumeration and cmdline

- direct mock of `_default_enumerate_pids()` for valid、nonzero、stderr、oversized、malformed、plus-sign、zero、
  negative、duplicate and `131073` unique PID rows；assert exact subprocess invocation；
- cmdline `65536` well-formed unrelated argv passes and `65537` blocks；missing final NUL、leading/interior empty、
  non-UTF8、EIO/EPERM block；confirmed exit/kernel/self behavior remains exact；
- exact controller/E1/E2 block；helper、token-file、SSH、bash、probe-self、grep、editor and unrelated rows pass；
  malformed fixture rows block；one match reason contains only PID(s)。

### Token file

- parent wrong uid and gid separately；file wrong uid and gid separately；non-regular final component；embedded
  NUL/path-shape open error；all produce structured blocked result and zero recover/audit/release；
- do not use blanket root:root rewriting as the wrong-owner authority；override the relevant stat seam per row；
- valid no-LF/one-LF、wrong modes、symlink、hardlink、size/content/race and audit/fsync/release ordering remain green。

## 6. Gates and commit

Canonical Python：`/Users/yinxin/projects/multinexus/.venv/bin/python`。

```bash
/Users/yinxin/projects/multinexus/.venv/bin/python -m py_compile scripts/production-mutation-lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_production_mutation_lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_deploy_contract.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q
git diff --check
```

Full suite timeout at least `20m`；timeout is not PASS。Fix only failures caused by the allowlist。

Create exactly one commit with parent exact base and subject：

```text
fix(p9-3c1): harden incident recover input
```

After commit do not amend。Final report：exact provider/model、commit/parent/subject/paths/diffstat、new tests、
test-first failures、all gate outputs and precise fail-closed semantics。Worker completion does not authorize merge
or production action。

P9_3C1_P3_RETRY_INCIDENT_IR_A_CORRECTION_BOOTSTRAP_READY_FOR_INDEPENDENT_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED
