# P9-3C0 Package 2 — Worker Bootstrap Review

Review date: 2026-07-15 Asia/Shanghai

## Exact review target

- Reviewed MultiNexus revision:
  `53f8807f42743d79f2cbffe61b62a59e0047f309`.
- Future worker implementation base:
  `7e887cbc24a7e38f268e6eb8ba656ac69c11905d`.
- Reviewed bootstrap:
  `p9-3c0-fixture-package2-worker-bootstrap.md`.
- Bootstrap SHA-256:
  `91e0e1cc14b8ee71c411231b0c13c7294a33eb42450ef396d94d39bf1dbe81e0`.
- Approved plan SHA-256:
  `282f2c92d09325486245d021349c0689bb92fa05e62a43a3a4e803d27ccf3d93`.
- The reviewer verified `HEAD == origin/main`, a clean worktree, and that
  `7e887cb..53f8807` added only the Round 2 plan review and worker bootstrap.

## Independent reviewer routing

- Claude Code session: `b2ec7801-d3eb-4401-a7bb-580702253a57`.
- Outer model: `claude-sonnet-4-6`; Opus was not used.
- Provider-native JSONL model: `kimi-for-coding`.
- Stream:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-package2-bootstrap-review-claude-kimi/reviewer-stream.jsonl`.

The provider claim comes from structured JSONL, not a UI label. During review, one
local probe attempted to create a temporary-looking path below `/opt/multinexus` and
failed with `PermissionError`; no file was created and the repository remained clean.
That failed write attempt is not used as review evidence.

## Independent evidence

- Adjacent focused baseline reproduced:
  `89 passed, 20 subtests passed`.
- Current authority parsers accepted equivalent in-memory fixture executor/capacity
  schemas and produced distinct version hashes.
- ClaudeAdapter's current argv, line-oriented stream JSON handling, result semantics,
  and 90-second first-byte behavior match the bootstrap contract.
- The repository remained clean after review.

## Findings

No P0 or P1 findings.

### P2 — real-Claude fallback remains a required negative test

`multinexus.config._first_existing_command` can resolve the last candidate `claude`
when the rendered absolute fixture executable is missing. This is non-blocking only
because the approved bootstrap requires the helper to load both rendered agents and
independently assert that both resolved `claude_bin` values equal the exact expected
absolute fixture executable.

The worker must prove both sides:

- an existing reviewed fixture path resolves exactly and is accepted;
- a missing/raw/partial path that would fall back to real Claude is rejected after
  load, before unit start.

## Accepted boundaries

The reviewer accepted the eleven-file allowlist and file modes, executable
argv/input/result/signal contract, seven unique config placeholders, immutable
executor/capacity schemas and staging order, synthetic parser-only ids, exact helper
CLI/ledger/isolation gates, systemd 255 fail-closed properties, 75/80/85/90 timing
contract, cleanup-before-failure, virtual/local-only tests, inert deployment assertion,
and Package 2/Package 3/P9-3C1 separation.

Package 3 must still bind its fixture-start monotonic evidence to the adapter's
first-byte clock with a bounded offset; Package 2 does not claim that runtime proof.

## Authorization boundary

This review authorizes one isolated worker from base
`7e887cbc24a7e38f268e6eb8ba656ac69c11905d`, changing only the eleven bootstrap files
and producing one local commit.

It does not authorize push, merge, deploy, SSH, real systemd, catalog sync, job/lease
creation, Package 3 execution, production DB access, or fixture activation. Codex must
verify worker JSONL and Git state separately, followed by a fresh exact-revision result
review.

`APPROVED_FOR_P9_3C0_FIXTURE_PACKAGE2_WORKER_LAUNCH`
