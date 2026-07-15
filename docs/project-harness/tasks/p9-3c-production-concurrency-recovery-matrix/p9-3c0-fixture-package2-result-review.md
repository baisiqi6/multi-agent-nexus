# P9-3C0 Package 2 — Fixture Assets Result Review

Review date: 2026-07-15 Asia/Shanghai

## Exact review target

- Implementation base:
  `7e887cbc24a7e38f268e6eb8ba656ac69c11905d`.
- Reviewed candidate:
  `efc75c9610c95b933bed45312bb33c446cd33051`.
- Branch: `agents/mac-claude/p9-3c0-fixture-package2`.
- Base-to-candidate history: exactly one commit.
- Worktree: clean at the accepted revision.
- Approved plan SHA-256:
  `282f2c92d09325486245d021349c0689bb92fa05e62a43a3a4e803d27ccf3d93`.
- Approved bootstrap SHA-256:
  `91e0e1cc14b8ee71c411231b0c13c7294a33eb42450ef396d94d39bf1dbe81e0`.

The candidate added exactly the eleven approved Package 2 files. Both files under
`multinexus/fixture/bin/` have Git mode `100755`; the eight config/runbook files and
`tests/test_p9_3c0_fixture_assets.py` have mode `100644`. No existing runtime,
canonical authority, adapter, deploy, or Coordinate file changed.

## Worker route and corrective history

Accepted worker rounds used Claude Code with outer `claude-sonnet-4-6`, never Opus.
Provider-native JSONL reported `message.model = kimi-for-coding`.

The final corrective session was
`41b8649d-bd2a-4bad-8974-d036802cc866`, with stream:

`/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-package2-worker-corrective5-claude-kimi/worker-stream.jsonl`.

Earlier corrective streams remain under the adjacent `worker-corrective2` through
`worker-corrective4` session directories. They established the initial one-commit
candidate and then closed reviewer-found fail-closed gaps. The final correction added
a replaceable `cgroup.procs` read seam and proved that a real read-command failure
after a successful `-f/-r` precheck cannot be converted into `cgroup-empty`.

Codex independently verified provider JSONL, commit ancestry, index/HEAD blobs, exact
file set/modes, clean status, and the critical stop/cgroup code path before launching
the final review.

## Accepted implementation contract

- The fixture executable accepts only the reviewed Claude no-model/no-resume argv,
  validates the strict stdin envelope, remains quiet for the bounded 75-second
  contract, emits the exact success result in complete mode, and contains no provider,
  credential, network, shell-expansion, or real-Claude fallback path.
- The rendered two-agent config is secret-free, uses explicit 240/90/90 timeouts,
  distinct context DBs, and requires both resolved `claude_bin` values to equal the
  reviewed fixture executable.
- Immutable executor v1/v2/v3/v4 and capacity v1/v2 assets parse through current
  authority loaders, have distinct hashes, encode the reviewed forward/cleanup order,
  and remain disjoint from canonical identities.
- The helper enforces exact E1/E2/run/unit identity, isolated path containment,
  `0700`/`0600` state modes, exclusive locking, raw and realpath production
  DB/wrapper rejection, mandatory systemd sandbox properties, exact stop, and
  start-ledger cgroup cleanup proof.
- Missing/duplicate/near-match ledger rows, malformed cgroups, path traversal,
  non-regular or unreadable `cgroup.procs`, actual read-command failure, non-empty
  cgroups, and inactive timeout all fail closed.
- The runbook uses literal JSON for `--origin-json`/`--reply-json`, preserves current
  Coordinate CLI spelling, and marks Package 3 commands unauthorized.
- Deployment copies the assets but does not invoke, register, sync, start, submit, or
  lease them.

## Verification evidence

Worker verification on the accepted candidate:

- focused: `72 passed, 26 subtests passed`;
- adjacent six-file suite: `161 passed, 46 subtests passed`;
- full: `735 passed, 2 skipped, 81 subtests passed`;
- `bash -n`, `compileall`, and `git diff --check`: pass.

Codex independently reproduced focused
`72 passed, 26 subtests passed in 10.38s` and inspected the committed critical paths.

The accepted independent result reviewer was session
`4f147e75-3ca9-4984-b73f-c7d2d39d158d`, stream:

`/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-package2-result-review-round2-claude-kimi/reviewer-stream.jsonl`.

It independently reproduced:

- focused: `72 passed, 26 subtests passed in 10.36s`;
- combined focused/authority/adapter/deploy/smoke: `161 passed, 46 subtests passed`;
- exact one-commit/eleven-file boundary, file modes, plan/bootstrap hashes, and clean
  worktree.

The reviewer reported no P0, P1, or P2 findings. Its two P3 notes were the helper's
unqualified `python3` use for monotonic/flock/path-normalization helpers and one
unconventionally grouped cleanup assertion in the test file. Neither changes the
reviewed security boundary or blocks inert integration.

## Discarded review attempt

The first result-review attempt, session
`cff1ae86-2b49-4c52-adf2-b54d3468e4ad`, was terminated and its verdict discarded
after it tried to create `/tmp/p9c0-venv` and install test dependencies instead of
using the existing reviewed environment. It changed no tracked repository or
production state. Codex removed only the bounded artifacts created by that attempt,
verified a clean worktree, and launched the fresh accepted reviewer with the exact
existing interpreter and explicit no-install boundary.

## Residual Package 3 boundary

Package 2 does not prove the real 75-second quiet/renewal row, live transient-unit and
`cgroup.procs` behavior, the fixture-start monotonic binding to adapter first-byte
evidence, isolated Coordinate executor/capacity/request transitions, or real
90-second first-byte scheduling margin. Those remain Package 3 gates.

## Final decision

`APPROVED_FOR_P9_3C0_FIXTURE_PACKAGE2_INTEGRATION`
