# Phase 8 Integration Audit

## What this is

Source-of-truth for **Phase 8 mainline integration ordering**. Persisted as
docs-only — NOT a materialized harness task (no `plan.ready` / assignment yet).
It is intended to become an executable gate once integration work begins.

This document exists because the integration question is bigger than any single
task and will span sessions; without persistence the context will be lost.

## Hard prohibitions (this phase = audit persistence only)

- Do NOT merge 8.4.3 to `main` directly.
- Do NOT merge the 8.4.2 long branch to `main` directly.
- Do NOT rebase.
- Do NOT mark-done / closeout any task.
- Do NOT deploy.
- This document is audit persistence only.

---

## 1. Current conclusions

- `main` is severely behind on both repos.
- The branch named "8.4.2" is actually a **Phase 8 long-lived integration branch**:
  it has accumulated 8.4.2 + 8.4.4 + 8.5 + 8.6 + 8.7 + 8.8 + backlog +
  progress-archiving work on top of 8.4.2's own function decomposition. It is not
  a small 8.4.2-only branch.
- 8.4.2 and 8.4.3 are **parallel diverged branches, NOT parent/child**. Neither
  contains the other's work.
- 8.4.3 lifecycle is **done** (review.completed approved + task.done on 2026-06-30),
  but **mainline integration is not ready**.

## 2. Branch facts

### coordinate
- `main`  = `6e8a4a1`
- 8.4.2   = `cbab1c5`  (`agents/mac-claude/phase-8.4.2-contracts-function-decomposition`)
- 8.4.3   = `16a0b81`  (`agents/mac-codex/phase-8.4.3-long-running-job-recovery`)
- 8.4.2 ahead of main: **+90 commits**
- 8.4.3 ahead of main: **+64 commits**
- 8.4.2 unique (not in 8.4.3): **30 commits**
- 8.4.3 unique (not in 8.4.2): **4 commits**
- merge-base: `63cdafb5c` (`fix: reject harness publish identity rebind`)

### multinexus
- `main`  = `28fd018`
- 8.4.2   = `3ffd93a`
- 8.4.3   = `04aee04`
- 8.4.2 ahead of main: **+222 commits**
- 8.4.3 ahead of main: **+197 commits**
- 8.4.2 unique (not in 8.4.3): **33 commits**
- 8.4.3 unique (not in 8.4.2): **8 commits**
- merge-base: `2cc9b21b5` (`harness: materialize Phase 8.4.2 task files`)

### Merge conflict risk (files both branches touch)
- coordinate: `src/coordinate/cli.py`, `src/coordinate/runtime.py`,
  `tests/test_cli.py`, `tests/test_runtime.py`
- multinexus: `multinexus/client.py` (8.4.3's core `agentd/*` and `adapters/*`
  are NOT touched by 8.4.2)

## 3. Durable lifecycle status (per phase task)

| phase task | accepted | closeout | review | done | status |
|---|---|---|---|---|---|
| 8.3.1 harness-source-boundary | 06-17 | 06-17 | approved | 06-17 | ✅ durable done |
| 8.3.2 a0-materialization-dogfood | 06-18 | 06-18 | approved | 06-18 | ✅ durable done |
| 8.4 closeout-dogfood-refactor | — | 06-22 | approved | 06-22 | ✅ durable done |
| **8.4.2 contracts-function-decomposition** | 06-22 | — | — | — | ⚠️ code complete, lifecycle NOT closed |
| 8.4.3 long-running-job-recovery | 06-22 | 06-30 | approved | 06-30 | ✅ durable done |
| 8.4.4 host-aware-mark-done | 06-22 | 06-22 | approved | 06-23 | ✅ durable done |
| 8.5 reviewer-handoff-role | 06-23 | 06-23 | approved | 06-23 | ✅ durable done |
| 8.6 return-delivery | 06-23 | 06-23 | approved | 06-23 | ✅ durable done |
| 8.7 worker-self-test | 06-24 | 06-24 | approved | 06-24 | ✅ durable done |
| 8.8 daemon-decision-runtime | 06-24 | 06-25 | approved | 06-25 | ✅ durable done |
| phase-8-preflight-dogfood-cleanup | 06-16 | — | — | — | ⚠️ not closed (secondary) |

Also present: 3 empty / abandoned task mirrors with no lifecycle events —
`phase-8-2-triage-accept-smoke`, `phase-8-github-automation-loop`,
`phase-8.4-worker-push-pr-creation`.

## 4. 8.4.2 specific blocker

- `assignment.accepted` 2026-06-22; two jobs ran.
- First job: "completed without structured agent-report" (no `[agent-report]`
  block — adapter finished but produced no structured result).
- Second job: **failed — timed out after 1800s** (mac-claude agentd,
  2026-06-22 06:55 UTC; `request:adb14f7c`).
- No `closeout.requested` / `review.completed` / `task.done` was ever recorded.
- Code commits for all three workstreams exist:
  - A — PR contracts module: coordinate `d7959d2` (2026-06-22)
  - B — `publish_pr()` decomposition: coordinate `bd4f300` (2026-06-22)
  - C — `handle_agent_request()` decomposition: multinexus `b6ad160`
    (2026-06-25, three days after the timeout)
- Conclusion: **code appears complete, durable lifecycle never closed.**

## 5. Integration plan

1. ✅ **Close 8.4.2 lifecycle** — DONE 2026-06-30. A/B/C code verified coherent;
   test-isolation blocker fixed (multinexus `13a3d2e`, test-only). Durable:
   closeout.requested `785d4ed2` → review.completed approved `984d6339` →
   task.done `eb4ff989`. Step 1 milestone closed.
2. ⏳ **Bring 8.4.3 recovery commits** (coordinate `16a0b81`, multinexus `04aee04`)
   onto the long integration branch. **Open as a separate task next session.**
   Prefer cherry-pick of the actual recovery fixes over blind whole-branch merge
   (avoid dragging in 8.4.3's stale closeout/docs noise). Resolve conflicts on a
   **feature/integration branch, NOT on main**; expect to touch coordinate
   `runtime.py`/`cli.py` (CAS, claim, reply platform) and multinexus `agentd/*`
   (claim recoverable, attempt_token, fail-closed).
3. **Full validation on the integration branch** — coordinate full suite,
   multinexus full suite, harness `validate` / `doctor`.
4. **Lightweight re-verify** recovery smoke on the integrated code.
5. **Decide merge strategy** — whole Phase 8 integration merge into `main`, or
   split out already-done tasks and merge in batches.

### Pre-state for Step 2 (next session)

- Step 1 done: `phase-8.4.2-contracts-function-decomposition` durable done.
- coordinate 8.4.2 branch HEAD: `cbab1c5`
- multinexus 8.4.2 branch HEAD: `13a3d2e` (test-only fix applied; was `cc3d6ed`)
- 8.4.3 done branch: coordinate `16a0b81`, multinexus `04aee04` (parallel, not
  yet integrated)

## 6. Prohibitions (this task)

Audit persistence only. Do NOT:
- merge 8.4.3 to `main` directly
- merge the 8.4.2 long branch to `main` directly
- rebase
- mark-done / closeout any task
- deploy

**Next step (B, separate session, after this document lands):** close the 8.4.2
lifecycle. Do not continue integration on chat context alone — drive it from this
document.
