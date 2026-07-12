# P9-0A5 Codex Result Review

## Verdict

`APPROVE_AFTER_CORRECTION`

- Reviewed start: `882c2a1487e4102d35c3c1f5b18b4a542be2d3bc`.
- Worker commit: `fa79fa6`.
- Reviewer correction commit: `084419c`.
- Worker provider/model: `kimi-code/kimi-for-coding-highspeed` through Oh-My-Pi.
- Worker provider session: `019f5760-6411-7000-8b40-45d5cd2e7ec7`.
- Worker JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-p9-0a5-kimi/2026-07-12T17-29-22-705Z_019f5760-6411-7000-8b40-45d5cd2e7ec7.jsonl`.

## Findings and correction

No correctness or architecture blocker remained after review. Codex found two worker
closeout-quality defects:

1. two untracked shell-redirection artifacts named `!` and `1` remained even though
   the worker reported a clean worktree; Codex removed both artifacts; and
2. `_fake_row` in the new boundary test did not close its in-memory SQLite connection,
   producing a `ResourceWarning`; correction commit `084419c` closes the connection.

The correction changes test hygiene only and stays inside the approved path set.

## Independent evidence

- Exact changed paths relative to `882c2a1`:
  `src/coordinate/policy.py`, `src/coordinate/event_presentation.py`, and
  `tests/test_event_presentation.py`.
- The worker generated all 44 function hashes and one registry hash before the first
  source edit; the pre-edit values are preserved in provider JSONL and permanent
  tests use the approved `ast.iter_fields` projection without `_attributes`.
- All 44 moved facade names, the registry, and the explicit-unstyle set are
  object-identical between `policy` and `event_presentation`.
- Registry and supported sets both contain 34 keys; Discord styling contains 31; the
  exact three unstyled keys are disjoint and complete the supported partition.
- `PolicyError`, support authority, JSON validation, embed enrichment, message-key,
  DB, delivery, skip and pump behavior remain in `policy.py`.
- `event_presentation.py` imports only `sqlite3` and typing; cold imports succeed in
  all three approved orders.
- `git diff --check` passes and the worktree is clean after correction.

## Validation

Using the project's known-good Python 3.14 interpreter:

```text
264 focused tests passed
1,572 full tests passed
ResourceWarning promoted to error: passed after correction
```

The 1,572 count is the reviewed 1,555-test baseline plus 17 new boundary tests.

The Kimi process used Python 3.12 and observed seven interpreter-specific CLI fixture
failures, one historical issue-CLI witness failure and one polluted `tests` namespace
error. Codex did not treat those results as green; it repeated the same package under
the known-good interpreter and obtained the clean counts above.

## Residual operational note

The Coordinate-generated generic worker handoff still described the deployed
MultiNexus checkout instead of the isolated Coordinate implementation worktree.
This package remained safe because the source-controlled bootstrap was declared the
only implementation authority. The identity/projection gap belongs to Slice 4 or a
subsequent handoff-hardening package, not this movement-only extraction.
