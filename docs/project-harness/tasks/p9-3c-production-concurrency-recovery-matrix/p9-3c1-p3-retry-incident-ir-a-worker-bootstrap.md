# P9-3C1 P3 Retry Incident Package IR-A — Worker Bootstrap

状态：`READY_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Role and exact base

You are the non-Codex Coding worker for replacement Package IR-A。Work only in the assigned isolated local
worktree。No SSH/network、production files/DB/tokens/auth、deploy、recover/release、service/cleanup/run、sessions
read、subagent/task or other repository。

- Repository：MultiNexus。
- Exact base/parent：`f76e4b51eda38f658237590e412a425e29c7b8d0`。
- Planned branch：`agents/kat/p9-3c1-p3-retry-incident-ir-a`。
- Start gate：HEAD equals exact base；tracked clean；do not fetch/pull/rebase/cherry-pick rejected
  `344ca2c6`。

Read completely before editing：

- `p9-3c1-p3-retry-incident-ir-result-review.md`；
- `p9-3c1-p3-retry-incident-ir-replacement-plan.md`；
- `p9-3c1-p3-retry-incident-ir-replacement-plan-review.md`；
- original incident correction plan/review；
- original IR bootstrap/review；
- existing helper and complete helper test module。

## 2. Exact allowlist

Runtime：

- `scripts/production-mutation-lock.py`。

Tests：

- `tests/test_production_mutation_lock.py`。

No controller、shell、deploy、config、Coordinate、docs or other test change。Do not copy the rejected candidate
implementation；use it only as negative evidence through the result review。

## 3. Test-first requirement

Add failing tests for every new contract **before** completing runtime implementation。The final diff must
contain direct new regression tests，not only passing old suites。No skip/xfail、test deletion、timeout hiding or
mock that bypasses the actual parser/probe/file validator。

## 4. Correct systemd probe

Keep the existing bounded direct `systemctl list-units` call and fail-closed errors。Reject every returned unit
whose first column fully matches the real production family：

```text
p9-3c-fixture-e1-p9-3c1-prod-YYYYMMDDtHHMMSSz-hex8.service
p9-3c-fixture-e2-p9-3c1-prod-YYYYMMDDtHHMMSSz-hex8.service
```

This covers active、activating、reloading and deactivating states already requested by the command。Do not
match unrelated prefixes/suffixes or the obsolete `p9-3c1-` unit prefix。Missing/error/oversized output blocks。

Use this anchored regex exactly；prefix/suffix-only matching is prohibited：

```text
^p9-3c-fixture-e[12]-p9-3c1-prod-[0-9]{8}t[0-9]{6}z-[a-f0-9]{8}\.service$
```

## 5. Exact Linux process probe

Do not use `pgrep -f` or free-text `ps ... args` substring classification。

### 5.1 Bounded enumeration

Use one direct `subprocess.run(["ps", "-e", "-o", "pid="], shell=False, timeout=10, capture_output=True,
text=True)` seam。Require exit `0`、empty stderr or explicitly tolerated platform header behavior、stdout no
larger than `1 MiB`、at most `131072` unique positive decimal PIDs。The PID-count cap is deliberately derived
from the same bounded-output budget and fails closed on a host outside this reviewed operational envelope；do
not read or trust a mutable host `pid_max` as authorization。Malformed/duplicate/oversized authority blocks。

### 5.2 Exact NUL argv authority

For each PID except `os.getpid()`，read at most `64 KiB + 1` from exact `/proc/<pid>/cmdline` and parse
NUL-delimited bytes with no empty interior argv。Provide narrow injectable seams for PID enumeration and argv
read so macOS tests use synthetic authorities rather than local `/proc`。

Treat a disappearing PID as exited only when the `/proc` read returns `ENOENT/ESRCH` and a second
`os.kill(pid, 0)` existence probe also returns `ESRCH`。This sends no signal and has no mutation effect；success、
`EPERM` or any other error means the PID is present/uncertain and blocks。Empty cmdline for a kernel thread may
be ignored。Permission、I/O、size、decode or inconsistent PID authority blocks。

Block only these exact argv identities：

1. controller：`argv[0] == "/usr/bin/python3.12"` and
   `argv[1] == "/opt/multinexus/scripts/p9_3c1_controller.py"`；
2. fixture：`argv[0] == "/usr/bin/python3.12"`、`argv[1:3] == ["-m", "multinexus.agentd"]` and exactly one
   adjacent `--agent`, `p9-3c-fixture-e1` or `p9-3c-fixture-e2` pair。

Duplicate/missing `--agent` is not accepted as a valid fixture identity but malformed candidate authority
containing the exact module plus either fixture id must fail closed rather than be treated unrelated。

Required negative rows：the recovery helper argv、token-file path、`ssh`/`bash -c` string containing the
controller command、probe itself、`grep`/editor opening the controller filename、unrelated python/module/agent。
Required positive rows：exact controller and each exact fixture。One real match reports only PID(s)，never full
argv or token-bearing strings。

## 6. Recover-only token file

`recover` must require exactly one of `--token` and `--token-file`，while existing direct-token behavior remains
unchanged。

For `--token-file`：

- require non-blank absolute path；
- immediate parent `lstat` exact non-symlink root:root directory mode `0700`；
- open final component once with `O_RDONLY|O_NOFOLLOW`；
- `fstat` exact regular root:root `0600` nlink `1`；
- initial size exactly `64` or `65` bytes；read exactly that size plus a one-byte growth probe；second `fstat`
  must prove the same inode/device/size/owner/mode/nlink/mtime_ns/ctime_ns；
- accept ASCII lowercase 64 hex with either no newline or one final LF；reject CRLF、spaces、multiple newline、
  invalid UTF-8/non-ASCII、short/growing/truncated content；
- convert all path/stat/open/read/decode errors into bounded redacted structured `LockError` before recovery；
- raw token never enters argv/stdout/stderr/error detail/audit when token-file is selected。

After validation，call the existing `recover(token=...)` exactly once。Do not change its token comparison →
corrected probes → durable audit → exact release ordering；do not add `allow_already_free` or fallback。

## 7. Mandatory tests

At minimum：

1. exact E1/E2 unit family blocks；unrelated/obsolete names do not；systemctl missing/nonzero/malformed/oversize
   blocks；
2. exact controller and both fixture argv block；helper/token/SSH/bash/grep/editor/unrelated rows do not；
   malformed candidate、enumeration error/duplicate/oversize、argv read permission/I/O/oversize blocks；confirmed
   exited PID and kernel thread behavior exact；
3. parser rejects both token flags and neither before mutation；existing direct-token tests unchanged；
4. relative/blank、parent symlink/type/owner/mode、file symlink/type/owner/mode/hardlink、64/65 size race/short/
   growth、bad ASCII/shape/newline failures all cause zero recover/audit/release；
5. valid no-newline and one-LF token files each reach one successful recovery with the existing redacted
   `receipt_digest` durable audit authority；
6. valid token-file plus real unit/process block retains lock/audit state；audit/fsync/release failure ordering remains
   unchanged and raw token is absent from captured subprocess argv、stdout/stderr/error/audit。

## 8. Gates and commit

Canonical Python：`/Users/yinxin/projects/multinexus/.venv/bin/python`。

Run：

```bash
/Users/yinxin/projects/multinexus/.venv/bin/python -m py_compile scripts/production-mutation-lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_production_mutation_lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_deploy_contract.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q
git diff --check
```

Full suite timeout must be at least `20m`；a timeout is not a pass。Fix only failures caused by this allowlist。

Create exactly one commit with subject：

```text
fix(p9-3c1): harden incident recover input
```

Parent must be exact base，changed paths exactly the two-file allowlist。After commit do not amend。Final report
must include exact commit/parent、diffstat/paths、new test names/counts、focused/deploy/full outputs and precise
fail-closed semantics。If blocked，do not expand scope or touch production；report the blocker。

P9_3C1_P3_RETRY_INCIDENT_IR_A_BOOTSTRAP_READY_FOR_INDEPENDENT_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED
