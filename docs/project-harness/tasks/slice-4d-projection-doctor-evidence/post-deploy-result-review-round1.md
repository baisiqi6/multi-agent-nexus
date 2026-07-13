# Slice 4D Post-Deploy Correction Result Review — Round 1

## Decision

**CHANGES_REQUESTED** for sanitized worker commit
`f481b9f041984ee7e98b9fc91d2791fb976db65f` on top of `0563cc0`.

The worker's original commit also added an unauthorized repository `events.jsonl`
RESULT line. Codex removed that worker-owned line and amended the unpushed commit to
`f481b9f`; only the four approved Coordinate paths remain. The implementation is not
authorized for merge, push, deploy, production, or closeout because exact-retry
verification trusts a tamperable stored supersedes link.

## Verified progress

- Creation-time task-create proof is separated from current lifecycle state.
- Current immutable task identity is checked while representative supported lifecycle
  changes are permitted.
- Approved plan revision, rejection, missing approval, cross-task link, cycle, legacy
  missing evidence, and immutable-field cases have focused coverage.
- Future split/non-split ready payloads carry full `plan_sha256` and a supersedes link.
- Focused worker evidence: `220 passed, 43 subtests passed`.
- Full worker evidence: `1846 passed, 449 subtests passed, 9 failed`; the failures are
  the same historical eight CLI-contract hashes plus one issue-CLI AST hash.
- Changed-path ruff, compileall, diff check, and `cli.py` byte check passed.

## Must-fix finding

### PD-R1-1 — Exact retry accepts a forged supersedes link (P1)

Both `_check_ledger_idempotency` and
`_check_issue_materialize_ledger_idempotency` read the stored ready payload and then
overwrite the independently built expected payload:

```python
expected_payload["supersedes_plan_ready_event_id"] = stored_payload.get(
    "supersedes_plan_ready_event_id"
)
```

The following independent reproduction succeeds when it must fail closed:

```text
1. apply a task.create record;
2. mutate its bound plan.ready payload so
   supersedes_plan_ready_event_id="forged-cross-task-event-id";
3. retry the exact operation;
4. observed: retry_accepted, event_created=False.
```

This normalizes the expected value to the untrusted stored value and defeats the new
provenance contract. The same pattern exists on issue-materialize retry.

## Required correction

1. Never copy `supersedes_plan_ready_event_id` from the stored payload into expected
   intent.
2. For an existing ledger row, obtain the bound ready event and independently derive
   the expected supersedes link as the latest same-workspace/same-task `plan.ready`
   whose rowid is strictly before that bound ready event's rowid. Exclude the current
   split operation/event and reject cross-task/missing/malformed targets.
3. Compare the stored full payload to expected intent containing that independently
   derived link.
4. Preserve exact retry after later unrelated ready events by using the historical
   rowid cutoff, not current latest state.
5. Apply the same rule to task-create and issue-materialize split retries.
6. Add tests for forged id, cross-task id, missing link when a prior ready existed,
   spurious link when none existed, and later unrelated ready not breaking an exact
   retry.
7. Keep the correction within `split_operations.py` and focused split-operation tests
   unless a genuinely necessary shared helper requires another already-approved path.

## Boundary

Continue on the same branch from `f481b9f`. Do not edit MultiNexus, project
`events.jsonl`, production, DB schema, receipt code, CLI facade, or lifecycle state. Do
not push or deploy. A second Codex result review is required.

Provider evidence: both coding sessions used
`kimi-code/kimi-for-coding-highspeed`; no Kimi quota/auth/provider failure occurred and
GLM was not used.
