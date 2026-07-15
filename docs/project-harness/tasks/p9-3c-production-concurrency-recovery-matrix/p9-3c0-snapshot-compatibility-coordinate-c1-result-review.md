# P9-3C0 Snapshot/Restore Compatibility — Coordinate C1 Result Review

Review date: 2026-07-15 Asia/Shanghai

## Exact review target

- Repository: `/Users/yinxin/projects/coordinate`
- Base: `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`
- Reviewed commit: `1e36d9b6ccd26a331ed655806f1c9ef735453685`
- Worker branch: `agents/mac-claude/p9-3c0-snapshot-compatibility-coordinate-c1`
- Changed files:
  - `src/coordinate/executor_capacity.py`
  - `tests/test_executor_capacity.py`
- Worker routing evidence:
  - Claude Code outer model: `claude-sonnet-4-6`;
  - provider-native JSONL `message.model`: `kimi-for-coding`;
  - session: `39569b37-3ea8-451c-aeed-61ff042b99e6`.

The worker worktree was clean at the reviewed revision. The changed-file set exactly
matches the independently approved C1 bootstrap. The user-owned `.qoder/` entry in the
Coordinate main checkout was not read, staged, copied, or modified.

## Accepted behavior

- `SNAPSHOT_CONTRACT_VERSION` is `2`.
- A v2 envelope contains the target source in `captured_state` and a digest-bound,
  deterministic `preserved_state` witness for every non-target source and policy.
- Capture validates the complete current projection under `BEGIN IMMEDIATE`, writes
  canonical bytes with mode `0600`, and removes the output on failure.
- Restore accepts strict v1 and v2 shapes. A v1 artifact remains valid only on a
  single-source database; it fails closed on a multi-source database.
- `contract_version` uses an exact integer type guard. Boolean, float, string, null,
  zero, and unknown-version values are rejected before database mutation.
- Restore validates the complete current projection, rejects an active lease on any
  source, checks witness equality and proposed-union invariants before any `DELETE`,
  and deletes/reinserts only the target source.
- `preserved_state` is a witness only and is never written to the database.
- Target and witness states are verified after writes; every post-write failure rolls
  back the transaction.
- Successful restore returns the original envelope without silently rewriting a v1
  artifact into v2.

## Reviewer red-team corrections

The result review required four corrections before acceptance:

1. Production projection validation was kept strict and ordered before witness
   equality. Invalid test fixtures were corrected instead of weakening or reordering
   the production invariant.
2. The parser was hardened from value equality to an exact integer type check so JSON
   `true`, `1.0`, and `2.0` cannot masquerade as supported contract versions.
3. The malformed-witness matrix gained an explicit canonical envelope whose witness
   value is changed while the original digest is retained; it must fail with
   `snapshot digest mismatch` and zero database mutation.
4. Witness-drift fixtures were made internally valid by updating source and policy
   fields together and recomputing policy ids, so the tests exercise witness drift
   rather than earlier projection corruption.

## Independent evidence

- Focused candidate suite:
  `128 passed, 21 subtests passed`.
- Full base suite:
  `2415 passed, 493 subtests passed, 9 failed`.
- Full candidate suite:
  `2452 passed, 514 subtests passed, 9 failed`.
- The candidate has no new failure and suppresses none of the nine historical
  failures: eight CLI contract fixture/hash failures and one issue CLI AST failure.
- `python -m compileall`: pass.
- `git diff --check`: pass.
- Changed-file allowlist: exact two-file match.
- Canonical JSON and digest semantics: independently checked.

The independent exact-revision reviewer used a new Claude Code session:

- outer model: `claude-sonnet-4-6`;
- provider-native `message.model`: `kimi-for-coding`;
- session: `887582cf-419d-4c72-9cae-5c0520c2a785`;
- verdict: `APPROVE`;
- no findings.

Provider-native evidence:

- worker and reviewer stream directory:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-snapshot-c1-bootstrap-kimi/`;
- worker stream: `coding-worker-narrow-fix-stream.jsonl`;
- independent reviewer stream: `result-reviewer-stream.jsonl`.

## Deployment boundary

This approval authorizes fast-forward merge, push, and an inert Coordinate production
deployment while production still has exactly the canonical
`multinexus.discord.capacity` source and eight policies.

Production verification is deliberately bounded to:

- pre-deploy database backup and integrity/readback evidence;
- deploy of the exact reviewed Coordinate revision;
- post-deploy service, version, source/policy, lease, job, and fixture-residue checks;
- a v2 capture whose mode, canonical bytes, digest, target state, empty witness, and
  database non-mutation are verified.

Do not run a live-production restore. Do not add a second capacity source, fixture
agent, fixture executor source, fixture unit, fixture job, or fixture lease in C1.
A real two-source capture/mutate/restore proof remains isolated/local and is gated by
C2 plus the later P9-3C1 activation plan.

## Final decision

`APPROVED_FOR_P9_3C0_SNAPSHOT_COMPATIBILITY_C1_MERGE_AND_INERT_DEPLOY`
