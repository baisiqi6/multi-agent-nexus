# P9-3C0 Package 3 — Implementation Worker Bootstrap

> **Bootstrap draft only.** This document is not executable authority until a fresh
> independent reviewer approves its exact SHA-256. Even after approval it authorizes
> local implementation/tests in the specified worktree only—not merge, push, deploy,
> SSH, systemd, catalog sync, DB mutation outside test temporaries, provider use, or
> fixture execution.

## 1. Worker/runtime identity

- Worker: Claude Code outer agent fixed to `sonnet`.
- Provider-native model must be `kimi-for-coding`.
- Opus and `kimi-for-coding-highspeed` are forbidden.
- Do not invoke subagents, Agent Team, Task, Workflow, or another coding agent.
- Main Codex remains architect/reviewer/operator; the worker implements only the
  reviewed allowlist and must not self-approve.
- Provider-native JSONL is required as the activity/model evidence stream.

## 2. Exact authority

- Repository: `/Users/yinxin/projects/multinexus`.
- Implementation worktree base:
  `27b506da3368f4b7f51878c4c19e3041a4ef357d`.
- Approved detailed plan:
  `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-package3-plan.md`.
- Approved plan SHA-256:
  `358c28ec0fc06d4717d1762ffe79c5bd54b2ccb20d18dd58152f02a022e08ee5`.
- Plan approval:
  `p9-3c0-fixture-package3-plan-review-round2.md`, token
  `APPROVED_FOR_P9_3C0_FIXTURE_PACKAGE3_BOOTSTRAP_DRAFT`.
- Coordinate contract revision (read-only dependency):
  `/Users/yinxin/projects/coordinate` at
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.

Before editing, independently verify all exact revisions/SHA values and that the
implementation worktree is clean at the exact base. If any value differs, stop without
editing.

Read completely before implementation:

1. Package 3 measurement, detailed plan, Round 1 review, and Round 2 approval;
2. parent fixture plan;
3. Package 2 detailed plan, worker bootstrap, result review, deployment dogfood;
4. current fixture executable, helper, authority TOMLs, runbook, and fixture tests;
5. current `agentd/__main__.py`, `agentd/worker.py`, `agentd/coordinate_client.py`,
   `adapters/claude.py`, `adapters/utils.py`, launch/deploy surfaces, and related tests;
6. only the Coordinate source/tests directly required to preserve current CLI,
   catalog, lease/reap/recovery, report, and DB contracts.

## 3. Exact implementation allowlist

Modify/add only:

- `multinexus/fixture/bin/p9-3c0-unit.sh`;
- `multinexus/fixture/docs/runbook.md`;
- `multinexus/agentd/__main__.py`;
- `multinexus/adapters/claude.py`;
- `scripts/p9-3c0-local-verify.sh` (new, executable `100755`);
- `scripts/p9-3c0-cleanup.sh` (new, executable `100755`);
- `tests/test_p9_3c0_fixture_assets.py`;
- `tests/test_p9_3c0_package3_scripts.py` (new, `100644`);
- `tests/test_agentd_recovery_evidence.py`;
- `tests/test_claude_adapter.py`.

Existing shell helper remains `100755`; runbook/Python/tests remain `100644`. No other
path or mode may change. In particular, do not modify Coordinate, fixture executable,
authority TOML, canonical config, deploy scripts, `agentd/worker.py`, adapter utilities,
service/plist/NSSM files, harness progress/review docs, or dependency files. If another
path appears necessary, stop and report the exact reason; do not broaden scope.

Runbook edits are restricted to replacing the Package 3 unauthorized preview with the
reviewed Package 3 implementation/operator contract. Do not weaken or rewrite Package
2 inert deployment, P9-3C1, or forbidden-operation sections.

## 4. Absolute safety boundary

Implementation and tests are local/mocked only. Forbidden:

- SSH/network/web/provider calls;
- real `systemctl`, `systemd-run`, `systemd-analyze`, journal, cgroup, `/proc` process,
  production wrapper, production DB, or deployed `/opt` mutation;
- any real Coordinate workspace/agent/catalog/job/lease/report/reap mutation;
- direct SQLite writes/deletes outside test-owned temporaries;
- canonical service restart, launch agent change, deploy, commit push, merge, PR;
- `pip install`, venv creation, dependency download, fallback interpreter, or test
  duration shortcut for the fixed 75-second fixture contract;
- wildcard unit/process commands, `pkill`, `pgrep`, guessed PID, `eval`, or mutable
  authority TOML editing.

Tests must inject all operating-system/Coordinate/time/process evidence. The new
verify/cleanup scripts must do nothing when sourced by tests; real actions occur only
through explicit main/subcommands after every preflight.

## 5. Required implementation

### A. Portable unit helper and ownership authority

In `p9-3c0-unit.sh`:

1. Completely remove every `systemd-run --dry-run` path.
2. Add the reviewed `systemd-analyze verify` static definition gate and keep exact
   post-start property validation.
3. Implement systemd 255 semantic normalizers exactly as plan §4.1 specifies:
   duration microseconds, bools, octal umask, strict protection, one canonical writable
   state path, positive AF_UNIX-only allow-set, and full IPv4+IPv6 deny. Unknown or
   partial representations fail closed and stop/clean the exact unit.
4. Enforce the root-controller/non-root-unit ownership and mode matrix. Reject root or
   unknown unit identity, symlink/traversal/alias, wrong owner/group/mode, unexpected
   file, and non-private runtime parents.
5. Add wrapper manifest authority: raw/resolved under approved state prefix; fixed
   Coordinate executable/isolated DB; device/inode/size/link count/owner/group/mode/
   SHA-256; root-owned wrapper `0750`, root:unit-group manifest `0640`; controller
   recheck and wrapper self-check before every invocation. Fixed arrays only; no eval.
6. Add fail-closed recovery flag grouping:
   `--recoverable --recovery-reason ... --prior-process-stopped`, all-or-none, bounded
   normalized reason, digest-only ledger. Normal unit gets none; recovery unit gets all.
7. Fixture units launch agentd with `--log-level DEBUG`; keep the reviewed exact
   sandbox and minimal environment/credential-variable denylist.
8. Preserve exact-unit ledger cgroup authority, read-failure handling, timing cleanup,
   locks, budgets, state modes, and raw/realpath production rejections already accepted
   in Package 2.

Do not solve Package 3 by weakening an accepted Package 2 failure path.

### B. Agentd log level

In `agentd/__main__.py`:

- parse `--log-level {DEBUG,INFO,WARNING,ERROR}` before `logging.basicConfig`;
- default exactly `INFO` when omitted;
- invalid values fail via argparse before config/worker creation;
- pass no new field to `AgentdWorker.run`; recovery evidence behavior is unchanged;
- no service definition or production default changes.

Tests cover DEBUG/default/invalid and the equivalent existing launchd/systemd/NSSM
argv surfaces that omit the flag.

### C. Exact Claude first-byte boundary

In `adapters/claude.py`:

- preserve the exact `loop.time()` value used for `last_activity` immediately before
  stdin write;
- at DEBUG emit one structured
  `claude_child_boundary monotonic_ns=<int> pid=<int>` record using that same value;
- first-byte timeout continues to use the same value;
- log must precede stdin write and contain no prompt/cwd/env/session/provider output;
- do not call `on_progress` and do not alter child stdout/stderr/JSONL behavior;
- missing PID or malformed clock fails through existing safe adapter error/cleanup
  semantics, not a second provider attempt.

Freeze the event-loop clock in tests and prove the logged integer corresponds to that
exact value and ordering.

### D. Package 3 verify controller

`scripts/p9-3c0-local-verify.sh` implements the reviewed durable phase machine. It must
be source-testable through injected seams and, in real mode:

1. require root controller plus exact non-root unit user/group;
2. create only the reviewed `/var/tmp/multinexus-p9-3c0/<run-id>` namespaces and exact
   ownership/modes;
3. capture the exact production read-only baseline for
   `coordinate.service`, `multinexus-discord-bridge.service`, and
   `kook-nexus-hermes.service`, canonical hashes, DB counts/source hashes, and no
   fixture unit/process;
4. create the fresh isolated wrapper/manifest/DB/work/harness/context/evidence through
   `runuser`, never initialize/mutate DB as root;
5. register workspace/host-profile/E1/E2; verify auto-created agentd runners; sync
   immutable executor v1-disabled -> capacity v1 -> executor v2-enabled;
6. start exact E1/E2 units; submit exact complete envelopes; capture initial lease
   before `acquired_at+30`, require `expires_at=acquired_at+120`, two later deadlines,
   two matching DEBUG renewals, TTL/renew 120/30, exact typed result and lease release;
7. submit exact E1 hold/descendant envelope, correlate exact adapter boundary log with
   ledger cgroup/PID/cmdline/environ/process hierarchy, freeze intake, stop at 80 s,
   accept only 75-85 s, and finish cleanup before anchor+88 s;
8. keep E2/canonical services intact until their explicit exact stop; compare production
   read-only fingerprints without a paid real-executor request;
9. after exact stop and recorded expiry, prove literal isolated quiescence sets, reap
   exactly one N, start second-run recovery with all evidence flags, establish running
   N+1, send stale N report, and prove nonzero/no row/event/delivery mutation;
10. stop N+1 recovery hold, wait/reap exactly once, then hand off to cleanup;
11. append bounded JSONL/ledger evidence after every verified phase; traps freeze intake
    and exact-stop ledger units but never guess, rerun the scenario, or reap early.

All origin/reply values use current literal JSON CLI fields and exact ids/idempotency.
The prompt is the strict compact fixture object, never prose/ellipsis/`@file`.

### E. Cleanup controller

`scripts/p9-3c0-cleanup.sh` is independently callable and idempotently resumes from
any durable phase. It:

- freezes intake only if not already frozen;
- stops/statuses/proves cgroup-empty only for exact ledger units;
- preserves an unexpired attempt until recorded expiry; reaps only under exact literal
  quiescence;
- requires zero active lease/pending/running job before every catalog mutation;
- syncs executor v3-disabled -> capacity v2-empty -> executor v4-empty;
- verifies zero definition/binding/policy and retains exactly v4/v2 empty source
  metadata plus dormant E1/E2 agent/runner and timed-out recovery evidence;
- invokes helper exact cleanup, captures final isolated/production snapshots, and
  retains mode-restricted DB/wrapper/manifest/ledger/evidence until closeout review;
- never directly deletes a SQLite row, source metadata, or the evidence root.

### F. Zero-provider/environment/process proof

Implement plan §11 exactly:

- root clean environment + `env -i`;
- enumerate matching variable names only, never values, union with fixed known-key
  denylist, and emit exact-name `UnsetEnvironment=` entries (literal wildcard fails);
- exact unit effective properties and agentd `/proc` environment;
- exact fixture child PATH/PWD-only environment;
- process tree distinguishes agentd MainPID, fixture adapter child, one `/bin/sleep 300`
  descendant, and only bounded wrapper/Coordinate CLI descendants;
- no provider/model/resume/dangerous flag, home/proxy/cloud/provider/Discord/KOOK key,
  non-AF_UNIX network, or production fixture identity.

## 6. Tests

Use only the existing interpreter:

`/Users/yinxin/projects/multinexus/.venv/bin/python`

Set `PYTHONDONTWRITEBYTECODE=1` and use pytest `-p no:cacheprovider`. Tests must not
create repo-root cache/SQLite artifacts. At minimum implement and run:

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/yinxin/projects/multinexus/.venv/bin/python \
  -m pytest tests/test_p9_3c0_fixture_assets.py \
  tests/test_p9_3c0_package3_scripts.py \
  tests/test_agentd_recovery_evidence.py \
  tests/test_claude_adapter.py -p no:cacheprovider -q

PYTHONDONTWRITEBYTECODE=1 /Users/yinxin/projects/multinexus/.venv/bin/python \
  -m pytest tests/test_agentd_execution_context.py \
  tests/test_agentd_execution_lease.py \
  tests/test_executor_capacity_authority.py \
  tests/test_registry_authority.py \
  tests/test_deploy_contract.py \
  -p no:cacheprovider -q

PYTHONDONTWRITEBYTECODE=1 /Users/yinxin/projects/multinexus/.venv/bin/python \
  -m pytest -p no:cacheprovider -q

bash -n multinexus/fixture/bin/p9-3c0-unit.sh \
  scripts/p9-3c0-local-verify.sh scripts/p9-3c0-cleanup.sh

PYTHONDONTWRITEBYTECODE=1 /Users/yinxin/projects/multinexus/.venv/bin/python \
  -m compileall -q multinexus/agentd/__main__.py \
  multinexus/adapters/claude.py tests/test_p9_3c0_package3_scripts.py
```

Additionally run `git diff --check`, exact allowlist/mode checks, and inspect all tests
for actual behavioral assertions rather than source-string-only claims. The test matrix
must cover every success/failure row in plan §12, including source-safe import (no main
execution), fake systemd 255 encodings, wrapper self-checks, clock ordering, interrupted
phase recovery, stale DB/event immutability, and unknown evidence failures.

Do not use a real 75-second wait in unit tests; inject the clock/sleeper while preserving
the production code's immutable 75-second constant and real-hook binding.

## 7. Commit and handoff

- Keep the worktree clean except exact allowlist changes.
- Produce exactly one implementation commit on the worker branch; do not amend after
  reporting it, push, merge, deploy, or edit main.
- Commit message: `feat(fixture): add p9-3c0 package 3 sidecar verifier`.
- Report exact base, commit SHA, changed paths/modes, test commands/results, assumptions,
  and any residual concern.
- Never claim Package 3 execution/production success. This worker proves code and
  mocked/local tests only; Codex result review, merged-main verification, inert deploy,
  and operator sidecar execution are separate gates.

If any required contract cannot be implemented safely inside this allowlist, stop with
`BLOCKED` and the exact code/plan conflict. Do not improvise a bypass.
