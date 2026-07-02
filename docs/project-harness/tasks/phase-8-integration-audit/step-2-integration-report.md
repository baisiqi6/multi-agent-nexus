# Phase 8 Integration Audit — Step 2 Report

**Status:** code-integrated + validated; NOT merged, NOT deployed, NOT marked done.
**Branches:** `agents/mac-codex/phase-8-integration` (local-only, on both repos), created off
the 8.4.2 long integration branch.
**Date:** 2026-07-01.

Step 2 of the integration plan (see `plan.md` §5): bring the 8.4.3 long-running-job-recovery
fixes onto the Phase 8 long integration branch via cherry-pick (not whole-branch merge), on a
feature branch, with full validation. This document records what was integrated, the one
conflict resolved, the validation results, and 8.4.3 invariant coverage.

## 1. What was integrated

### coordinate — 4 commits cherry-picked (all recovery; no noise on this side)

Base: `cbab1c5` (8.4.2 long branch HEAD). Integration HEAD: `4ac774e`.

| upstream (8.4.3) | integrated as | summary |
|---|---|---|
| `baacc0f` | `5620059` | feat: add recoverable runtime job checkpoints (A1/A3: schema + progress) |
| `161d941` | `f1b51e7` | P1 #1: claim_job defaults to non-recoverable |
| `e37f16a` | `5f0aecc` | P1 #2: attempt-token atomic CAS on report/progress |
| `16a0b81` | `4ac774e` | P1 #4: reply platform resolved per-workspace (A4) |

### multinexus — 5 recovery commits cherry-picked, 3 noise commits skipped

Base: `1c5c798` (8.4.2 long branch HEAD). Integration HEAD: `c91631a`.

| upstream (8.4.3) | integrated as | summary |
|---|---|---|
| `bc90695` | `2473883` | make agentd recovery progress resumable (B1–B4 foundation) |
| `b659b0f` | `7cfde2d` | P1 #2: thread attempt_token claim→progress/report |
| `5b69e61` | `343fa64` | P1 #3: recovery_session_id always wins, fail-closed |
| `19298e3` | `159c3b3` | P1 #3: explicit `--recoverable` operator recovery mode |
| `04aee04` | `c91631a` | P1 #3: _is_error recognizes "Codex resume failed" |

Skipped (8.4.3 lifecycle/docs noise — would drag stale task state onto the integration branch):
- `4b28c5f` plan: define Phase 8.4.3 recovery task (task plan doc)
- `c57acc5` harness: materialize Phase 8.4.3 recovery task (mvp-checklist mutation)
- `3e1fdba` docs(8.4.3): closeout packet + P1-fix implementation plan

## 2. Conflict resolution

**One conflict, coordinate only.** `tests/test_runtime.py` during `161d941` (P1 #1): both the
8.4.2 long branch and the 8.4.3 commit appended new test blocks at the same end-of-class
anchor. 8.4.2 added Phase 8.6/8.8 `agent.reported` / review-decision tests; 8.4.3 added
`test_claim_default_does_not_pick_up_recoverable_timed_out` and
`test_claim_recoverable_true_reclaims_timed_out`. Resolution: kept both blocks (independent
additions), removed the three conflict markers. No production-code conflict.

**multinexus: zero conflicts.** `client.py` auto-merged (changes in disjoint regions); all
`agentd/*` and `adapters/*` files are untouched by 8.4.2 (confirmed in `plan.md` §2), so the
recovery hunks applied cleanly.

## 3. Validation (integration branch)

| check | result |
|---|---|
| coordinate full suite | **1200 passed**, 58 subtests passed (28.7s) |
| multinexus full suite | **341 passed, 2 skipped**, 12 subtests passed (0.7s) |
| `harnessctl validate` (coordinate) | passed, 0 warnings |
| `harnessctl validate` (multinexus) | passed, 4 warnings (pre-existing `review.decision` gaps on done items — unchanged from 8.4.2 base; recovery did not touch `mvp-checklist.json`) |
| `harnessctl doctor` (both) | complete; only pre-existing MISS/warnings (e.g. `current/task_plan.md`, `round-2-hardening/plan.md`) — not introduced by recovery |

Source resolution verified before running: coordinate suite ran against the integration
`src/` via PYTHONPATH (`claim_job` shows `recoverable: bool = False`, `report_job_result`
shows `attempt_token`); multinexus suite ran from the integration worktree cwd
(`worker.run` shows `recoverable: bool = False`, `_resume_recoverable_session` present,
`"Codex resume failed"` in `_ERROR_PREFIXES`).

Baseline delta: coordinate 1182→1200 (+18 recovery tests), multinexus 331→341 (+10 recovery
tests). The 2 multinexus skips are pre-existing platform-conditional tests.

## 4. 8.4.3 invariant coverage

| # | invariant | where covered | evidence |
|---|---|---|---|
| 1 | separate inactivity / absolute-budget semantics | B1 (`bc90695`) | claude adapter + worker lease; `test_claude_adapter.py` green |
| 2 | durable progress (activity, stage/summary, session id) | A3 + B2 | `record_job_progress` + agentd progress callback (`2473883`) |
| 3 | timeout = recoverable outcome with explicit resume path | A1 (`5620059`) | `recoverable` flag + `timed_out` status; schema/db tests green |
| 4 | retry resumes recorded session, no silent duplicate | B4 + P1 #3 fail-closed (`343fa64`/`159c3b3`/`c91631a`) | `test_worker_existing_session_plus_recovery_is_fail_closed`; recovery smoke (separate session) |
| 5 | result races deterministic | A2 + P1 #2 CAS (`5f0aecc`/`7cfde2d`) | `_accept_late_result` + report/progress CAS; rowcount==0 → rollback tests green |
| 6 | cancellation reaps spawned process | B3 (`2473883`) | `test_claude_adapter.py` cleanup test green |
| 7 | terminal/recoverable response reaches pumped Discord transport | A4 (`4ac774e`) | `_normalize_reply_platform` per-workspace; delivery tests green |
| 8 | existing claim/delivery/gates unchanged | P1 #1 (`f1b51e7`) | `claim_job` default `recoverable=False`; pre-existing `test_claim_job_moves_next_pending_job_to_running_once` and delivery tests still green within 1200 |

## 5. Prohibitions honored

- No merge to `main`. No merge of 8.4.3 into the 8.4.2 long branch directly (cherry-pick onto
  a feature branch only).
- No rebase.
- No deploy.
- No task mark-done / closeout (this is an audit report, not a task closeout event).
- Integration branches are **local-only** (not pushed); pending Step 4 merge-strategy decision.

## 6. Hand-off to Step 3 / Step 4

- **Step 3** (lightweight recovery smoke re-verify on integrated code): the recovery smoke
  was previously validated on the standalone 8.4.3 branches (real codex resume timeout →
  fail-closed; fake-codex "Codex resume failed" → fail-closed; stale attempt-1 report/progress
  rejected by server CAS). Step 3 should re-run one focused smoke against the **integrated**
  branches to confirm the cherry-picks did not regress the fail-closed path.
- **Step 4** (merge-strategy decision): choose whole-Phase-8 integration merge into `main` vs
  batched split. The integration branches (`4ac774e` coordinate / `c91631a` multinexus) are
  the candidate merge source for the 8.4.3 portion.
