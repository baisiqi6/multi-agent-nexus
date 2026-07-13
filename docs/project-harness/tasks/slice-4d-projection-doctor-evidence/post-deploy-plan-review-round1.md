# Slice 4D Post-Deploy Correction Plan Review — Round 1

**Reviewer:** independent non-Codex Kimi reviewer  
**Review date:** 2026-07-13  
**Verdict:** **REJECT**

## Reviewed artifacts

| Artifact | Path | SHA-256 |
|---|---|---|
| Post-deploy correction plan | `docs/project-harness/tasks/slice-4d-projection-doctor-evidence/post-deploy-correction-plan.md` | `466c8a0cca20332e584b73f3c82b5a6d7bef96c31bf4ae5ad472621d3b9e10eb` |
| Original S4-D plan | `docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan.md` | `4a16f55005567a6640b98130ec9cf83391224b8e5f25622bf17cac0b0c6d4c64` |
| Round 5 result review | `docs/project-harness/tasks/slice-4d-projection-doctor-evidence/result-review-round5.md` | `b6907fd0ee086d35e053f0764e75abe9d935f712f58de08318ed625d264245d8` |

## Inspected commits and code

- **MultiNexus `main`:** `4facf668d739bbc7d44c0609e74b0a6a69a352a7`
- **Coordinate `main`:** `0563cc01f9b12d5c196f59aaece8d81d1d5e5bc5`
- Coordinate worktree: clean except pre-existing untracked `.qoder/`
- Inspected files:
  - `src/coordinate/projection_doctor.py`
  - `src/coordinate/split_operations.py`
  - `src/coordinate/plan_gate.py`
  - `tests/test_projection_doctor.py`
  - `src/coordinate/doctor.py` (integration surface)
  - `src/coordinate/completion_cli.py` (preflight surface)

## Provider / session evidence

- OMP model/provider: `kimi-code/kimi-for-coding-highspeed`
- No Kimi quota/auth/provider failure occurred; no GLM fallback was used.

## Review scope

Assessed against the six bootstrap questions:

1. creation-time operation proof vs. current lifecycle state
2. approved plan supersession grounded in exact event links/hashes
3. rejection / cross-task / wrong-SHA / cycle / later invalidation fail-closed
4. allowed paths and no-write/no-shell-out boundaries
5. implementability without DB mutations or hard-coded production exceptions
6. tests sufficient to reproduce the two observed production errors

## What the plan gets right

- The creation-time authority is correctly identified as the ledger `record_event_id` and its immutable `plan.ready` payload, not the current checklist item.
- The fail-closed matrix for rejection, cross-task, wrong-SHA, supersession cycle, and broken receipt chains is comprehensive.
- The no-write boundary is clear: no `INSERT/UPDATE/DELETE`, no harness mutation, no `subprocess`, no repair execution.
- Required test list covers both observed production scenarios (lifecycle-owned fields and approved plan revision) plus negative cases.
- Receipt preflight fix is already implemented in `completion_cli.py` (`_lookup_receipt_for_preflight`) at `0563cc0`, so no additional receipt code change is needed.
- `doctor.py` / `workspace_cli.py` integration already exists and is exercised by existing tests.

## P0 findings — must fix before approval

### P0-1: `plan_sha256` required by the plan is not present in existing `plan.ready` events

The correction plan requires:

> "its `plan_sha256` exactly equals the current file SHA"

and expects the creation-time payload to carry `plan_sha256`. However, the current Coordinate code at `0563cc0` writes `plan.ready` events with only a 16-character `plan_content_hash`; the full SHA-256 of the plan bytes is **not** stored in the event payload or the ledger.

Evidence from current code (`src/coordinate/split_operations.py`, `apply_task_create_record`):

```python
plan_content_hash = plan_sha256[:16]
event_payload = {
    **task_payload,
    ...
    "plan_content_hash": plan_content_hash,
}
```

The actual `plan.ready` payload keys observed at runtime are:

```text
['absolute_plan_doc', 'allocated_branch', 'current_branch', 'phase',
 'plan_content_hash', 'plan_doc', 'priority', 'split_operation', 'status',
 'task_id', 'title', 'workspace_path']
```

`plan_sha256` is absent. Because the input fingerprint is a one-way SHA-256 over a JSON blob containing the full `plan_sha256`, the doctor cannot recover the historical plan SHA from the ledger or envelope. Without storing the full SHA, exact supersession verification is impossible.

**Required correction:** Either
- (a) explicitly authorize mutation-service changes (e.g., `onboarding.py`, `split_operations.py` record-half) to persist full `plan_sha256` in new `plan.ready` / `plan.approved` event payloads, or
- (b) relax the plan to a verification mechanism that does not require recovering the full historical plan SHA.

### P0-2: "Explicit supersession" linkage does not exist in current event vocabulary

The plan requires:

> "it explicitly supersedes the earlier ready event, directly or through a valid acyclic supersession chain"

Current `plan.ready` events carry no `supersedes_ready_event_id` or equivalent field. The only ordering authority in Coordinate is `events.rowid`, as correctly noted elsewhere in the original plan. Since SQLite `rowid` is monotonic per task, a later `plan.ready` is already unambiguously later; cycles are impossible. Requiring an explicit supersession link introduces a data model dependency that does not exist.

**Required correction:** Replace "explicitly supersedes" with rowid-order inference, or explicitly authorize adding a `supersedes_ready_event_id` field to `plan.ready` payloads and require cycle detection for it.

### P0-3: Allowed paths forbid the changes required by P0-1/P0-2

The correction plan states:

> "Allowed Coordinate paths: `src/coordinate/projection_doctor.py`. `src/coordinate/split_operations.py` only for neutral pure reconstruction/verification helpers."
> "Do not change CLI routing, receipt code, DB schema/migrations, mutation services, `src/coordinate/cli.py`, or MultiNexus runtime code."

Adding `plan_sha256` or `supersedes_ready_event_id` to `plan.ready` payloads requires modifying the mutation path (`split_operations.py` `apply_task_create_record` / `onboarding.py` `create_plan_task_record`), which is currently disallowed. The plan is therefore internally inconsistent.

**Required correction:** Amend the allowed-path and no-change sections to explicitly permit the minimal mutation-service changes needed to persist the new payload fields, or remove those field requirements.

### P0-4: Production acceptance gate cannot be met without legacy-event handling

Production events for the S4-D task were created by the deployed `0563cc0` code and therefore lack `plan_sha256`. The plan’s acceptance gate demands:

> "Production `workspace doctor discord-nexus` without `--no-projections` returns exit 0, zero error findings, explicit plan-supersession info for the reviewed S4-D revision"

If the doctor requires full `plan_sha256` in the superseding `plan.ready` event, this gate cannot pass without re-creating or back-filling production events, which is a direct DB/lifecycle mutation and explicitly prohibited.

**Required correction:** Define a backward-compatible fallback for legacy events that lack `plan_sha256` (e.g., treat the absence as insufficient evidence and fail-closed, or use the existing 16-character `plan_content_hash` with documented weaker assurance), and separately require full `plan_sha256` for newly created events.

## P1 findings — significant risk, must be addressed before worker handoff

### P1-1: `result-review-round5.md` approval is inconsistent with current code

Round 5 approves correction commit `0563cc0` and the branch `a21d946..0563cc0`, claiming the S4-D correction is complete. However, `0563cc0` is the current `HEAD` and `projection_doctor.py` still validates split-operation fingerprints against the **current** checklist item, producing the exact `operation_envelope_drift` errors observed in production.

Evidence:

```text
Scenario1 lifecycle mutation error kinds: ['operation_envelope_drift']
Scenario2 plan change error kinds: ['operation_envelope_drift'] info kinds: []
```

The correction plan must not rely on the Round 5 approval as evidence that the fix is already present. A fresh independent worker bootstrap from `0563cc0` is required.

**Required correction:** Remove reliance on Round 5 as an implementation approval; treat `0563cc0` only as the post-deploy baseline and require a new worker commit + independent Codex result review after the correction is implemented.

### P1-2: Current tests do not yet reproduce the two production errors under the new semantics

`tests/test_projection_doctor.py` at `0563cc0` passes 98 tests, but the relevant tests are:

- `test_production_like_c1_and_later_task_done_is_clean`: only appends a `task.done` event and updates `last_event_id`; it does **not** mutate lifecycle-owned checklist fields (`status`, `owner`, `workflow`, etc.), so it does not reproduce production error #1.
- `test_deployed_s4d_task_with_plan_bytes_changed_after_record_reports_drift`: asserts an `operation_envelope_drift` **error**, whereas the corrected semantics should emit an `operation_plan_superseded` **info** finding.

The plan’s required test list is correct, but the existing tests must be updated/extended during implementation.

**Required correction:** Keep the required test list, and explicitly state that existing `test_production_like_c1...` and `test_deployed_s4d_task...` must be replaced or augmented by tests that exercise the corrected semantics.

### P1-3: Ambiguous worker start commit

The correction plan cites `0563cc0` as the approved/deployed commit but does not explicitly state the worker start commit. The original plan required `a21d946` as the Coordinate start.

**Required correction:** State unambiguously that the worker branch starts from `0563cc0` (not `a21d946`) and that `src/coordinate/cli.py` must remain byte-identical to `0563cc0` rather than to `a21d946`.

## P2 findings — should be clarified

### P2-1: Missing detail on how creation-time after-fingerprint is reconstructed

The plan says:

> "reconstructing the creation-time checklist projection from historical payload, envelope, and `files_applied_at` equals the stored after fingerprint"

It does not specify whether this reconstruction belongs in `projection_doctor.py` or as a new neutral helper in `split_operations.py`, nor which lifecycle fields are excluded. This is implementable, but the plan should make the boundary explicit to avoid duplicating private contract logic.

### P2-2: Plan rejection semantics rely on rowid order only

`reject_plan` in `src/coordinate/plan_gate.py` does not reference a specific `plan_ready_event_id`. The plan’s condition 5 ("no later `plan.rejected` invalidates that same ready revision") will therefore reject any later rejection, even one targeting a different intermediate revision. Document that this is the intended fail-closed behavior.

## Residual risks if approved without fixes

- The worker will either (a) implement the supersession logic with data that does not exist, producing false negatives/positives, or (b) silently relax the requirements, breaking the exact-SHA contract.
- Production `workspace doctor` may continue to fail on the S4-D task because legacy events lack `plan_sha256`.
- A worker may attempt to modify `split_operations.py` record-half code without explicit plan authorization, causing the implementation to exceed its allowed boundary and fail result review.

## Exact required corrections summary

1. **Data model:** decide whether to persist full `plan_sha256` in event payloads. If yes, amend allowed paths to authorize mutation-service changes and require backward compatibility for legacy events. If no, remove the exact-SHA requirement from the supersession algorithm.
2. **Supersession linkage:** replace "explicit supersession" with `events.rowid` monotonic ordering, or add a `supersedes_ready_event_id` field and cycle detection and authorize the corresponding payload change.
3. **Worker baseline:** clearly state worker starts from `0563cc0`; do not rely on Round 5 approval as evidence of completion.
4. **Tests:** require the existing two production-like tests to be updated to the corrected semantics; add the missing lifecycle-mutation and plan-supersession-info tests.
5. **Legacy production events:** specify how the doctor handles `plan.ready` events created before the payload extension.

## Evidence commands

```bash
# Coordinate HEAD
git -C /Users/yinxin/projects/coordinate rev-parse HEAD
# 0563cc01f9b12d5c196f59aaece8d81d1d5e5bc5

# MultiNexus HEAD
git -C /Users/yinxin/projects/multinexus rev-parse HEAD
# 4facf668d739bbc7d44c0609e74b0a6a69a352a7

# Current focused tests pass, but do not cover corrected semantics
pytest tests/test_projection_doctor.py -q
# 98 passed
```

## Conclusion

The post-deploy correction plan correctly identifies the two production misclassifications and the desired read-only semantics, but it requires event payload fields (`plan_sha256`, explicit supersession link) that do not exist and forbids the mutation-service changes needed to create them. Until these contradictions are resolved, the plan is **REJECT**.
