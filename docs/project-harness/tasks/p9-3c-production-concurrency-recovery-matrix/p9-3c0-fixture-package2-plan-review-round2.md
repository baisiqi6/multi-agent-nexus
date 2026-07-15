# P9-3C0 Package 2 — Plan Review Round 2

Review date: 2026-07-15 Asia/Shanghai

## Exact review target

- Exact MultiNexus revision:
  `7e887cbc24a7e38f268e6eb8ba656ac69c11905d`.
- Reviewed plan:
  `p9-3c0-fixture-package2-plan.md`.
- Reviewed plan SHA-256:
  `282f2c92d09325486245d021349c0689bb92fa05e62a43a3a4e803d27ccf3d93`.
- Original plan revision:
  `5d44cc7ed2585332a74c365abc7b84d34470e4b0`.
- The reviewer verified `HEAD == origin/main`, a clean worktree, and that
  `5d44cc7..7e887cb` changed only the revised plan and added the Round 1 review
  record.

## Independent reviewer routing

- Valid reviewer session: `37579392-8be2-4a1a-9b6c-9ae65e0c766f`.
- Claude Code outer model: `claude-sonnet-4-6`; Opus was not used.
- Provider-native JSONL model: `kimi-for-coding`.
- Valid review stream:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-package2-plan-review-round2b-claude-kimi/reviewer-stream.jsonl`.

An earlier fresh attempt, session `cd007f64-f01e-452e-bac4-c0b94025e145`, was
unable to run the required read-only Git/hash commands because local Claude Bash
permission was denied. It produced no review verdict and is excluded from this gate.
Its stream remains at:
`/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-package2-plan-review-round2-claude-kimi/reviewer-stream.jsonl`.

## Verdict

`APPROVE` — no P0 or P1 findings remain.

### Round 1 P0 — synthetic parser identities

`RESOLVED`.

The current registry authority validator accepts quoted positive decimal strings, so
the fixed values `"1"` and `"2"` are parseable without a runtime change. The revised
plan marks them non-production and parser-only, forbids roster/workspace sync, and
requires exact uniqueness/non-collision checks against canonical authority.

### Round 1 P1 — silent hold stop window

`RESOLVED`.

The revised contract defines a target stop at 80 seconds, accepts only
`75 <= elapsed < 85`, and remains below ClaudeAdapter's 90-second first-byte timeout.
It also makes `RuntimeMaxSec=300` a last-resort safety ceiling rather than a valid hold
window, and requires exact-unit/cgroup cleanup before a late or invalid timing row
returns failure.

## Non-blocking Package 3 carry-forward

The Package 3 controller must anchor its monotonic fixture-start boundary at or before
the same point where `ClaudeAdapter._run` begins the first-byte clock. The offset
between those two clocks must not remain unbounded. Package 2 must preserve a strict
input/ledger contract for the boundary, while Package 3 owns the real timing and lease
evidence.

## Authorization boundary

This review authorizes Codex to write the Package 2 worker bootstrap. It does not
authorize worker launch, coding, push, merge, deployment, SSH, systemd launch, catalog
sync, job/lease creation, isolated Package 3 execution, or production activation. The
bootstrap itself requires a fresh independent exact-revision review.

`APPROVED_FOR_P9_3C0_FIXTURE_PACKAGE2_BOOTSTRAP_AUTHORING`
