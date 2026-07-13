# Slice 4D Post-Deploy Correction Result Review — Round 2

## Decision

**CHANGES_REQUESTED** for worker commits
`f481b9f041984ee7e98b9fc91d2791fb976db65f` and
`05bf2823a2cb19b1ade868df213c490d42a7ccef` on top of `0563cc0`.

Round 2 closes PD-R1-1: task-create and issue-materialize exact retries now derive
the historical supersedes link independently using the bound ready event rowid, and
the independent forged-link reproduction now fails closed. The combined correction
is still not authorized for merge, push, deploy, production, or closeout because the
current checklist identity check silently accepts fields that the approved plan
explicitly requires it to validate or reject.

## Verified progress

- The exact-retry correction no longer copies the stored
  `supersedes_plan_ready_event_id` into expected intent.
- An independently forged stored supersedes link now raises
  `SplitOperationError(reason="operation_conflict")`.
- A later same-task `plan.ready` after the bound ready event does not break an exact
  retry.
- Focused combined verification passed: `230 passed, 43 subtests passed`.
- Changed-path ruff passed.
- Worker full-suite evidence is `1856 passed, 449 subtests passed, 9 failed`; the nine
  failures remain the historical eight CLI-contract hashes and one issue-CLI AST
  hash.

## Must-fix findings

### PD-R2-1 — Unknown checklist top-level fields are silently accepted (P1)

The approved plan states that the implementation **must not silently ignore unknown
top-level fields** and must add a failure test for immutable-field tampering.
`_immutable_identity_errors` currently compares only `id`, `title`, `phase`,
`priority`, `plan_path`, and envelope `operation_id`. It does not use an explicit
allowlist or reject an unrecognized top-level key.

Independent reproduction:

```text
1. create a clean split task operation;
2. add checklist item field
   unrecognized_creation_identity="tampered";
3. run diagnose_projections;
4. observed: report_ok=True, errors=[].
```

This makes future or corrupted state invisible to the doctor and directly violates
the approved correction contract.

### PD-R2-2 — `artifacts.plan` immutable plan identity is not checked (P1)

The approved plan requires comparison of the canonical plan document path in the
item/artifacts. `_plan_doc_from_envelope_or_item` reads only `item["plan_path"]`, and
`_immutable_identity_errors` never validates `item["artifacts"]["plan"]`.

Independent reproduction:

```text
1. create a clean split task operation with plan_doc="plans/plan.md";
2. change only checklist item artifacts.plan to "plans/other.md";
3. run diagnose_projections;
4. observed: report_ok=True, errors=[].
```

The current implementation therefore accepts two contradictory canonical plan
references.

## Required correction

1. Build the set of recognized creation and lifecycle-owned checklist top-level
   fields explicitly, preferably from the neutral creation-projection helper plus a
   small named allowlist for fields added by supported lifecycle transitions.
2. Emit an error for every unknown top-level field. Do not introduce a wildcard,
   prefix rule, or catch-all `artifacts` exemption.
3. Validate both `plan_path` and `artifacts.plan` against the recorded canonical
   `plan_doc`; malformed/missing/non-string/conflicting values fail closed.
4. Preserve the currently clean production-like lifecycle mutations (`status`,
   `owner`, `workflow`, `review`, `handoff`, `selected_in_session`, `updated_at`,
   `verification`, `completion_receipt`) and explicitly include only other fields
   demonstrably written by supported transitions.
5. Add focused failures for an arbitrary unknown top-level field, tampered
   `artifacts.plan`, missing `artifacts.plan`, and conflicting item/artifact plan
   paths. Keep the legitimate lifecycle-evolution test green.
6. Re-run focused projection tests, combined projection/split tests, changed-path
   ruff and compileall, and the full suite with the historical-failure comparison.

## Boundary

Continue on the same branch from `05bf282`. Keep the correction in
`projection_doctor.py` and focused projection-doctor tests unless a genuinely shared
neutral helper is required. Do not edit MultiNexus, project `events.jsonl`, production,
DB schema, receipt code, CLI facade, or lifecycle state. Do not push or deploy. A
third Codex post-deploy result review is required.

Provider evidence: all post-deploy coding sessions used
`kimi-code/kimi-for-coding-highspeed`; no Kimi quota/auth/provider failure occurred,
so GLM fallback was not used.
