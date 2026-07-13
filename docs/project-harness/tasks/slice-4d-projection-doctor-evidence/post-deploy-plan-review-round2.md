# Slice 4D Post-Deploy Correction Plan Review — Round 2

**Reviewer:** independent non-Codex Kimi reviewer  
**Review date:** 2026-07-13  
**Verdict:** **APPROVE**

## Reviewed artifacts

| Artifact | Path | SHA-256 |
|---|---|---|
| Post-deploy correction plan (updated) | `docs/project-harness/tasks/slice-4d-projection-doctor-evidence/post-deploy-correction-plan.md` | `635b54c74e7705aaa469e06e6bf1609027251b75ffa7319e4b9ceba0ef39be94` |
| Original S4-D plan | `docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan.md` | `4a16f55005567a6640b98130ec9cf83391224b8e5f25622bf17cac0b0c6d4c64` |
| Round 5 result review | `docs/project-harness/tasks/slice-4d-projection-doctor-evidence/result-review-round5.md` | `b6907fd0ee086d35e053f0764e75abe9d935f712f58de08318ed625d264245d8` |

## Inspected commits and code

- **MultiNexus `main`:** `5256fbcf1e67a90e54e93f1263e67f47a5daa4f7`
- **Coordinate `main`:** `0563cc01f9b12d5c196f59aaece8d81d1d5e5bc5`
- Coordinate worktree: clean except pre-existing untracked `.qoder/`
- Inspected files:
  - `src/coordinate/projection_doctor.py`
  - `src/coordinate/split_operations.py`
  - `src/coordinate/onboarding.py`
  - `src/coordinate/plan_gate.py`
  - `tests/test_projection_doctor.py`
  - `src/coordinate/doctor.py` (integration surface)
  - `src/coordinate/completion_cli.py` (preflight surface)

## Provider / session evidence

- OMP model/provider: `kimi-code/kimi-for-coding-highspeed`
- No Kimi quota/auth/provider failure occurred; no GLM fallback was used.

## Round 1 closure verification

All Round 1 P0 and P1 findings are closed by the updated plan.

### P0 closure

| Finding | Status | Evidence |
|---|---|---|
| P0-1 `plan_sha256` missing from existing `plan.ready` payloads | Closed | Section 3A now standardizes full `plan_sha256` in every newly emitted `plan.ready`, keeps `plan_content_hash` for backward-compatible idempotency, and adds a legacy rule for events lacking the full SHA. |
| P0-2 Explicit supersession linkage missing | Closed | Section 3A now standardizes `supersedes_plan_ready_event_id` in later revisions and requires cross-task/workspace rejection. |
| P0-3 Allowed paths forbade the changes required by P0-1/P0-2 | Closed | Allowed paths now explicitly include `src/coordinate/split_operations.py` record-half and `src/coordinate/onboarding.py` for adding the two provenance fields. |
| P0-4 Production acceptance gate impossible without legacy handling | Closed | Section 3A states that legacy events missing full `plan_sha256` or an explicit supersedes link are insufficient for exact supersession proof and remain errors. |

### P1 closure

| Finding | Status | Evidence |
|---|---|---|
| P1-1 Round 5 approval treated as implementation completion | Closed | Plan now states: "Round 5 is evidence for the already-integrated S4-D baseline only; it is not approval of this post-deploy fix." |
| P1-2 Existing tests do not reproduce the two production errors under corrected semantics | Closed | Required tests #1 and #4-#13 explicitly cover lifecycle mutation, approved supersession, rejection, cross-task/wrong-SHA/older ready errors, and supersession cycles. The plan also states the two existing production-like tests must be replaced or augmented. |
| P1-3 Ambiguous worker start commit | Closed | Plan states: "Coordinate worker start commit is exactly `0563cc01f9b12d5c196f59aaece8d81d1d5e5bc5`." Acceptance gate requires `src/coordinate/cli.py` byte-identical to that commit. |

### P2 closure

| Finding | Status | Evidence |
|---|---|---|
| P2-1 Missing reconstruction helper boundary | Closed | Section 1 now places the helper in `split_operations.py` and requires it to reuse the canonical input builder and checklist-item constructor/projection. |
| P2-2 Rejection semantics rowid-only | Closed | Section 3A explicitly documents that `plan.rejected` has no `plan_ready_event_id`, so the fail-closed rule is rowid-based. |

## Current code observations at `0563cc0`

- `src/coordinate/split_operations.py::apply_task_create_record` computes `plan_sha256` but currently persists only `plan_content_hash = plan_sha256[:16]` in the `plan.ready` payload. The updated plan authorizes persisting the full `plan_sha256`.
- `src/coordinate/onboarding.py::create_plan_task_record` (non-split compatibility path) currently persists only `plan_content_hash`. The updated plan authorizes persisting the full `plan_sha256` and `supersedes_plan_ready_event_id`.
- `src/coordinate/plan_gate.py::approve_plan` stores `plan_ready_event_id` referencing the latest `plan.ready` by `rowid DESC`. `reject_plan` does not reference a specific ready event; the rowid-based fail-closed rule matches the updated plan.
- `src/coordinate/projection_doctor.py` at `0563cc0` contains no plan-supersession logic and recomputes input fingerprints from current plan bytes, which is exactly the production misclassification the correction targets.
- `tests/test_projection_doctor.py` passes 98 tests at `0563cc0`; the two production-like tests (`test_production_like_c1_and_later_task_done_is_clean` and `test_deployed_s4d_task_with_plan_bytes_changed_after_record_reports_drift`) still assert the old semantics, as noted in Round 1.

## New findings

### P0 — none

No blocking inconsistencies remain.

### P1 — none

No significant unaddressed risks remain.

### P2 — residual risks

1. **Production event payload assumption.** The plan asserts that existing production S4-C2 and S4-D operation record events include full `plan_sha256` and that the reviewed S4-D revision includes both full SHA and an explicit supersedes link. This cannot be verified from repository code alone; the production `workspace doctor discord-nexus` acceptance gate must confirm it from live data. If live events differ, the doctor will continue to fail until a separately reviewed repair/migration exists.

2. **Authorized mutation-service changes.** The plan permits `split_operations.py` and `onboarding.py` to write two new provenance fields into future `plan.ready` payloads. While the scope is narrowly bounded, any change to the record half carries regression risk. Required tests #12 and #13 must prove both split and non-split paths store full SHA, link prior ready events, remain idempotent, and do not duplicate events.

3. **Creation-time projection reconstruction.** The doctor must reconstruct the creation-time checklist projection from historical payload, envelope, and `files_applied_at` and prove it equals the stored after fingerprint. The correctness of this reconstruction depends entirely on reusing the exact canonical helpers in `split_operations.py`; any divergence will reintroduce false drift reports.

## Evidence commands

```bash
# MultiNexus HEAD
git -C /Users/yinxin/projects/multinexus rev-parse HEAD
# 5256fbcf1e67a90e54e93f1263e67f47a5daa4f7

# Coordinate HEAD
git -C /Users/yinxin/projects/coordinate rev-parse HEAD
# 0563cc01f9b12d5c196f59aaece8d81d1d5e5bc5

# Updated post-deploy correction plan SHA-256
sha256sum docs/project-harness/tasks/slice-4d-projection-doctor-evidence/post-deploy-correction-plan.md
# 635b54c74e7705aaa469e06e6bf1609027251b75ffa7319e4b9ceba0ef39be94

# Current focused tests pass, but still cover old semantics
pytest tests/test_projection_doctor.py -q
# 98 passed
```

## Conclusion

The updated post-deploy correction plan resolves every Round 1 P0/P1 finding, bounds the authorized write-path changes to the two provenance fields, defines a deterministic fail-closed supersession algorithm, and gates acceptance on live production verification. The residual risks are acceptable and are explicitly covered by the acceptance matrix and required tests. The plan is **APPROVED** for worker handoff.

[agent-report]
