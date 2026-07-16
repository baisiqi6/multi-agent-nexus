# P9-3C1 P3 Retry Incident Package IR-A — Replacement Correction Plan

状态：`READY_FOR_INDEPENDENT_PLAN_REVIEW_IMPLEMENTATION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Objective and immutable evidence

Replace rejected candidate `3f337eb243dfa229ac3d25c5b08636ad0de1b9d9` with one clean candidate whose
parent is exact `f76e4b51eda38f658237590e412a425e29c7b8d0`。Preserve the accepted IR-A design while fixing the
result-review P0/P1 findings。The rejected commit and its native JSONL remain immutable evidence；do not amend
or merge it。

## 2. Scope and construction

Exact allowlist remains：

- `scripts/production-mutation-lock.py`；
- `tests/test_production_mutation_lock.py`。

The replacement worker may use `git diff f76e4b51..3f337eb2 -- <allowlist> | git apply` only to create an
uncommitted starting tree in a new clean worktree at exact base。It must then implement the corrections below，
run test-first regression rows，and create exactly one new commit。No cherry-pick commit、amend、rebase、other
path、SSH/network or sessions read。No P0 recover、release、cleanup、resume、deploy、service、DB or other
production mutation。

## 3. Required runtime corrections

1. Restore successful `release` CLI `_json_out(result)` and `return 0` without changing failure semantics。
2. Default PID enumeration：require `returncode == 0` and empty stderr；bound stdout to `1 MiB` before parse；
   accept at most `131072` unique positive decimal PIDs；all other authority blocks with bounded static detail。
3. Cmdline read：read at most `64 KiB + 1` and treat exactly `64 KiB + 1` as oversized。Only at most `64 KiB`
   proceeds to NUL parsing。Keep confirmed-exit and exact identity semantics unchanged。
4. Systemd output：keep the exact reviewed regex and direct command；nonzero/missing/oversized blocks。Reject
   non-empty rows whose first column cannot be parsed as a systemd unit name；internal blank or whitespace-only
   rows block。Well-formed unrelated/obsolete unit names continue to pass；prefix/suffix-only matches do not
   block。
5. Token-file：convert `OSError` and path-shape `ValueError` from path/stat/open/read authorities into bounded
   redacted `LockError` before recover。Do not include exception text that can echo untrusted path/token data。
   Preserve one open、two fstats、size/content rules and existing recover ordering。
6. Do not require fixture argv length exactly five。The authority remains exact Python/module prefix plus exactly
   one adjacent `--agent` pair for E1/E2；other real fixture arguments are permitted。Malformed duplicate/missing
   fixture authority blocks。

## 4. Mandatory direct tests

Add tests that fail on the rejected candidate before runtime correction，including：

- successful CLI acquire → release：mutation succeeds，`rc=0`，canonical released JSON，empty stderr，no token；
- `_default_enumerate_pids()` direct mocked subprocess rows：non-empty stderr、nonzero、oversized stdout、
  malformed/non-positive/duplicate PID、count cap，plus one valid row；verify exact argv and `shell=False`；
- cmdline sizes `65536` and `65537`，non-UTF8、empty interior argv、probe-self and editor negative rows；
- malformed systemd non-empty and internal blank rows block；exact E1/E2 block；unrelated/obsolete/prefix/suffix
  rows pass；
- parent wrong uid/gid、file wrong uid/gid、non-regular final component and embedded-NUL/path-shape errors
  produce structured blocked errors with zero recover/audit/release；
- all original direct-token、audit/fsync/release-order and valid token-file cases remain green。

Tests must exercise the parser/validator under review。A pre-parsed injected list does not count as coverage of
`_default_enumerate_pids()`；blanket root:root rewriting does not count as wrong-owner coverage。No skip/xfail、
test deletion、timeout hiding or production command execution。

## 5. Worker routing and evidence

First worker candidate：OMP `kat-coder/kat-coder-pro-v2.5`，per operator preference。If it produces no tracked
progress after a bounded observation window or is unavailable，preserve its JSONL and route to approved fallback
without mixing edits。Kimi/Claude remains unavailable in the current route；DeepSeek or MiniMax may be fallback。

Native JSONL must identify actual provider/model。Final report must include test-first failing output、exact
commit/parent/subject/paths/diffstat and every gate output。The worker may not self-approve。

## 6. Gates and merge boundary

Canonical Python：`/Users/yinxin/projects/multinexus/.venv/bin/python`。

```bash
/Users/yinxin/projects/multinexus/.venv/bin/python -m py_compile scripts/production-mutation-lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_production_mutation_lock.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_deploy_contract.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q
git diff --check
```

Full-suite timeout at least `20m`；timeout is not PASS。Exact subject remains：

```text
fix(p9-3c1): harden incident recover input
```

After worker completion，Codex performs independent reproductions and line review，then a different non-Codex
result reviewer issues `APPROVE` or `REQUEST_CHANGES`。Only exact dual approval authorizes cherry-pick of the
single replacement commit onto current main。IR-A merge does not authorize deploy or P0 recovery；IR-B planning
and review remain separate gates。

P9_3C1_P3_RETRY_INCIDENT_IR_A_CORRECTION_PLAN_READY_FOR_INDEPENDENT_REVIEW_IMPLEMENTATION_BLOCKED
