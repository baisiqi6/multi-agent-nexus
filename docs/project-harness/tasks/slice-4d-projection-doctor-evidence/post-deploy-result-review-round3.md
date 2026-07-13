# Slice 4D Post-Deploy Correction Result Review — Round 3

## Decision

**CHANGES_REQUESTED** for worker commit
`726d876ea519f493a0833e3c4df515ddd6eb1376` on top of
`f481b9f` + `05bf282`.

PD-R2-1 and PD-R2-2 are substantially implemented: arbitrary unknown top-level
fields now fail closed, and both `plan_path` and `artifacts.plan` are validated.
The commit is not authorized for merge, push, deploy, production, or closeout because
its explicit allowlist rejects a real supported lifecycle field that the approved
plan specifically requires it to permit.

## Must-fix finding

### PD-R3-1 — Legitimate lifecycle `lease` is rejected as unknown (P1)

`STANDARD_CREATION_ITEM_FIELDS` is derived from `_build_checklist_item`, which does
not create a `lease` field. `LIFECYCLE_OWNED_ITEM_FIELDS` adds only
`completion_receipt`. Consequently the doctor reports every legitimate top-level
`lease` written later by the harness as unknown.

This is not hypothetical:

- the approved correction plan explicitly names `lease` as lifecycle-owned;
- MultiNexus `scripts/harness/harness_common.py` writes `item["lease"]` in the
  supported lease transitions;
- the current canonical `docs/project-harness/mvp-checklist.json` contains top-level
  `lease` fields.

Independent reproduction against `726d876`:

```text
1. create a clean split task operation;
2. add a supported lifecycle lease object to the checklist item;
3. run diagnose_projections;
4. observed: report_ok=False;
5. observed identity error: unknown top-level field: 'lease'.
```

This would replace the original false-positive drift with a new production false
positive and would prevent the post-deploy doctor gate from passing.

## Required correction

1. Add exactly `lease` to the named lifecycle-owned top-level field allowlist, with
   a comment referencing the supported harness lease mutation contract. Do not widen
   the allowlist beyond fields evidenced by supported transitions.
2. Extend the production-like lifecycle test with representative `lease` state and
   prove it remains clean.
3. Keep the arbitrary unknown-field failure test red/green and all PD-R2 plan-path
   tests green.
4. Run focused projection tests, combined projection/split tests, changed-path ruff,
   compileall, full suite with historical-failure comparison, `git diff --check`,
   `cli.py` byte check, and repository `events.jsonl` diff check.

## Boundary

Continue from `726d876` on the same branch. This correction should touch only the
allowlist definition and focused projection-doctor lifecycle test. Do not edit
MultiNexus, project `events.jsonl`, production, DB schema, receipt code, CLI facade,
onboarding, or lifecycle state. Do not push or deploy. A fourth Codex post-deploy
result review is required.

Provider evidence: the worker used `kimi-code/kimi-for-coding-highspeed`; no Kimi
quota/auth/provider failure occurred, so GLM fallback was not used.
