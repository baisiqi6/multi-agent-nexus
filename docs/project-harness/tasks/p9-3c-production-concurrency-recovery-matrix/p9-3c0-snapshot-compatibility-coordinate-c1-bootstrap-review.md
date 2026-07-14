# P9-3C0 Snapshot/Restore Compatibility — Coordinate C1 Bootstrap Review

Reviewer: independent Claude Code session, outer `sonnet`, provider-native `kimi-for-coding`  
Session: `3b4cd1f2-16a2-43aa-949d-9b7ebd770ad4`  
Reviewed exact revision: `c91b025265fb6186a07246cb8373667fe1e8d122`  
Verdict: **APPROVED_FOR_P9_3C0_SNAPSHOT_COMPATIBILITY_C1_WORKER_LAUNCH**

## Exact revision evidence

- MultiNexus review worktree HEAD was exactly
  `c91b025265fb6186a07246cb8373667fe1e8d122` and the worktree was clean.
- The reviewed commit added exactly one file:
  `p9-3c0-snapshot-compatibility-coordinate-c1-bootstrap.md` (`298` lines).
- The approved planning base was
  `061746b3d6c7e232ee4afe936136b3d2a9a4460d`.
- The Coordinate implementation base was exactly
  `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`.
- The Coordinate main checkout had no tracked modifications, staged changes, or
  conflicts. Its only reported untracked entry was the user-owned `.qoder/`, which
  remains outside all worker authority.
- The reviewer read the bootstrap, measurement, approved plan, independent plan
  review, Coordinate implementation, relevant tests, and schema semantics. It did
  not modify any file.

## Blocking findings

None.

## Non-blocking guidance carried into worker launch

1. Reproduce focused and full-suite baselines at the exact Coordinate base before
   treating historical counts as authoritative.
2. Keep handcrafted v1 fixtures inside the allowlisted
   `tests/test_executor_capacity.py`; no separate fixture file is authorized.
3. Treat the live-production restore prohibition as a hard procedural guard.

## Coverage and accountability

| Gate | Bootstrap accountability |
|---|---|
| No coding before independent approval | Section 1 |
| Exact base, isolated worktree, `.qoder/` untouched | Section 2 |
| Two-file allowlist | Section 3 |
| v2 target state plus digest-bound preserved witness | Sections 4-5 |
| `BEGIN IMMEDIATE`, full projection, any-source lease gate | Sections 6-7 |
| Witness equality and witness-never-written rule | Sections 6 and 8 |
| v1 single-source compatibility and multi-source rejection | Sections 5-6 and test matrix |
| Global typed-binding union and ownership | Sections 6-7 and test matrix |
| Prior-absence target-only deletion | Restore flow and test matrix |
| Pre-delete zero mutation and post-write rollback | Test matrix |
| Existing `.venv` plus base-vs-worker comparison | Section 11 |
| Codex review plus independent result review | Section 12 |
| No live restore; C2/fixture/P9-3C1 remain blocked | Section 13 |

## Authorization boundary

This approval authorizes only a Coordinate C1 coding worker in the specified isolated
worktree, modifying only:

- `src/coordinate/executor_capacity.py`
- `tests/test_executor_capacity.py`

The worker may produce one local commit. This approval does not authorize push,
merge, deploy, SSH, production DB mutation, fixture activation, service restart,
schema/migration/CLI/doc/config changes, C2, or P9-3C1 execution.

`APPROVED_FOR_P9_3C0_SNAPSHOT_COMPATIBILITY_C1_WORKER_LAUNCH`
