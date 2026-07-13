# Slice 4D Post-Deploy Correction Result Review — Round 4

## Decision

**CHANGES_REQUESTED** for the combined correction through
`b84e03b6f2234fadec53623f8d6f7488fb364dc5`.

PD-R3-1 is closed: `lease` is now explicitly evidenced and permitted, the current
canonical checklist has no unknown top-level keys, and independent lease/unknown/
artifacts reproductions have the expected opposite outcomes. The combined correction
is still not authorized for merge, push, deploy, production, or closeout because the
new default non-split `plan.ready` writer can emit a non-canonical null plan SHA.

## Verified progress

- Current canonical checklist keys minus recognized keys: empty set.
- Independent lifecycle lease reproduction: clean.
- Independent arbitrary unknown field reproduction: `operation_envelope_drift`.
- Independent `artifacts.plan` tamper reproduction: `operation_envelope_drift`.
- Combined projection/split verification: `234 passed, 43 subtests passed`.
- Full independent suite: `1860 passed, 449 subtests passed, 9 failed`; the nine are
  the same historical eight CLI-contract fixture hashes plus one issue-CLI AST hash.
- Changed-path ruff, compileall, diff check, `cli.py` byte check, and `events.jsonl`
  diff check passed.

## Must-fix finding

### PD-R4-1 — Default non-split ready emits `plan_sha256=null` (P1)

The approved Standard plan-ready provenance contract says every newly emitted
`plan.ready` payload includes a canonical full `plan_sha256`. In
`create_plan_task_record`, the new code does this:

```python
plan_content_hash = _plan_content_hash(plan_abs)
plan_sha256 = compute_plan_sha256(plan_abs) if plan_abs.is_file() else None
```

The function then upserts the task mirror and emits `plan.ready` even when the plan
does not exist or is not a regular readable file.

Independent reproduction against `b84e03b`:

```text
create_plan_task_record(..., plan_doc="plans/missing.md")
observed event_created=True
observed plan_sha256=None
```

This creates new legacy-style evidence that the corrected doctor intentionally treats
as insufficient. It also hashes the readable file twice through two separate helpers,
so a concurrent file change can make `plan_content_hash` disagree with
`plan_sha256[:16]`.

## Required correction

1. Before any task/event DB write in the non-split path, require the resolved plan to
   be a regular readable file. Missing, directory, or unreadable input must fail closed
   with a stable `ValueError` suitable for the existing CLI error path.
2. Compute the full SHA-256 once through the neutral helper and derive
   `plan_content_hash = plan_sha256[:16]`; do not read the plan twice and do not retain
   the `nohash` path for a newly emitted non-split ready event.
3. Add tests proving missing and directory plan inputs create neither task mirror nor
   `plan.ready` event. Add an unreadable/read-failure test through a deterministic mock
   rather than relying on local filesystem permissions.
4. Preserve the existing two-revision full-SHA/supersedes test and exact retry
   behavior.
5. Re-run focused onboarding/projection tests, combined projection/split tests,
   changed-path ruff, compileall, full suite with historical-failure comparison,
   `git diff --check`, `cli.py` byte check, and repository `events.jsonl` diff check.

## Boundary

Continue from `b84e03b` on the same branch. This correction should touch only
`onboarding.py` and focused tests. Do not edit MultiNexus, project `events.jsonl`,
production, DB schema, receipt code, CLI facade, or lifecycle state. Do not push or
deploy. A fifth Codex post-deploy result review is required.

Provider evidence: the worker used `kimi-code/kimi-for-coding-highspeed`; no Kimi
quota/auth/provider failure occurred, so GLM fallback was not used.
