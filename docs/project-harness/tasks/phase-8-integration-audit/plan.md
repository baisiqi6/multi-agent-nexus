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
- `main` (origin) = `595d6ea` (was recorded as `6e8a4a1`; main advanced — local main ref stale)
- long  = `cbab1c5`  (`agents/mac-claude/phase-8.4.2-contracts-function-decomposition`)
- INT   = `4ac774e`  (`agents/mac-codex/phase-8-integration` = long + 4 recovery; long is an ancestor of INT)
- 8.4.3 (orig, superseded by Step 2 cherry-pick) = `16a0b81`
- long ahead of main: **+131**; INT ahead of main: **+135**
- main↔long divergence (main's own commits not in long): **0** → main is a pure ancestor of long/INT
- long history main..long: **0 merge commits** (fully linear)
- (historical 8.4.2↔8.4.3) merge-base: `63cdafb5c`; 8.4.3 unique vs 8.4.2: 4 commits

### multinexus
- `main` (origin) = `28fd018`
- long  = `57083c9` + Step 4 docs-only fact commits (`agents/mac-claude/phase-8.4.2-contracts-function-decomposition`; was `3ffd93a` — advanced via Step 1/2/3 audit docs and Step 4 pre-state docs)
- INT   = `c91631a`  (`agents/mac-codex/phase-8-integration` = `1c5c798` + 5 recovery)
- 8.4.3 (orig, superseded by Step 2 cherry-pick) = `04aee04`
- long ahead of main: **+230**; INT ahead of main: **+230**
- main↔long divergence: **0** → main is a pure ancestor of long
- long history main..long: 4 merge commits / 230
- INT↔long DIVERGED from `1c5c798` (see Step 4 wrinkle): INT has 5 recovery long lacks; long has 6 audit-docs/proposal commits INT lacks
- (historical 8.4.2↔8.4.3) merge-base: `2cc9b21b5`

### Merge conflict risk — 8.4.2 ↔ 8.4.3 only (RESOLVED in Step 2)

The files below are where the 8.4.2 long branch and the 8.4.3 branch BOTH touched. Step 2
already resolved these during cherry-pick onto the INT branch. **This is NOT a main-merge
risk**: main is a pure ancestor of long/INT on both repos (0 divergence), so merging
long/INT into main is a fast-forward with no possible main-side conflicts.
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
2. ✅ **Bring 8.4.3 recovery commits** onto the long integration branch — DONE
   2026-07-01. Cherry-picked onto feature branch `agents/mac-codex/phase-8-integration`
   (pushed to origin): coordinate `baacc0f`/`161d941`/`e37f16a`/`16a0b81` → HEAD `4ac774e`;
   multinexus `bc90695`/`b659b0f`/`5b69e61`/`19298e3`/`04aee04` → HEAD `c91631a`. Skipped 3
   multinexus noise commits (`4b28c5f` plan, `c57acc5` task-materialize, `3e1fdba` docs).
   One conflict (coordinate `tests/test_runtime.py`, both-sides test additions → kept both).
   Validation: coordinate 1200 passed, multinexus 341 passed/2 skipped, `harnessctl
   validate`/`doctor` clean (only pre-existing warnings). Details:
   `step-2-integration-report.md`. Step 2 milestone closed.
3. ✅ **Full validation on the integration branch** — DONE 2026-07-01 (as part of Step 2).
   coordinate full suite 1200 passed, multinexus full suite 341 passed/2 skipped, `harnessctl
   validate`/`doctor` clean. See `step-2-integration-report.md` §3.
4. ✅ **Lightweight re-verify** recovery smoke on the integrated code — DONE 2026-07-01.
   All 7 conditions pass on `4ac774e`/`c91631a`: default poll never reclaims timed_out;
   `--recoverable` resumes recorded session; resume failure fails closed (no fresh duplicate,
   no `job.completed`); stale attempt-token report/progress rejected by SQL CAS (job not
   overwritten). No code modified (smoke-only). Production launchd restored, no `--recoverable`
   lingering. Details: `step-3-recovery-smoke-report.md`.
5. ✅ **Decide and execute merge strategy** — DONE 2026-07-02. Strategy selected:
   whole-branch single landing; `multinexus` INT → long; both repos landed on `main`
   with `--no-FF` merge commits. Details in Step 4 execution record below.

### Step 4 decision inputs (historical git facts — resolved 2026-07-02)

Verifiable git facts (not preferences), recorded now so the next round does not start
from a stale plan.md. The strategy decisions and execution record are appended below.

- **main is a pure ancestor of long/INT on both repos** (`merge-base --is-ancestor`
  rc=0; main's own commits not in long = 0 on both). Merging long/INT into main is
  mechanically a **fast-forward** — no possible main-side conflicts.
- coordinate: INT (`4ac774e`) = long (`cbab1c5`) + 4 recovery; long is an ancestor of
  INT (no divergence). INT is the complete branch; main can FF directly to INT (+135).
- multinexus: long history has 4 merge commits; INT (`c91631a`) and long (`525eba6`)
  **diverged** from `1c5c798`.
- The §2 "merge conflict risk" files were 8.4.2↔8.4.3 overlap, resolved in Step 2 —
  not a main-merge risk.

**multinexus wrinkle (must resolve before merging to main):** INT and long diverged
from `1c5c798`. INT has 5 recovery commits long lacks (`2473883`/`7cfde2d`/`343fa64`/
`159c3b3`/`c91631a`); long has 6 audit-docs/proposal commits INT lacks
(`dc47361`/`f70fc24`/`57083c9`/`ff14aab`/`525eba6`/`e730807`).
Neither alone FFs to a complete state. Reconcile first, then land main.

**Three decisions resolved in the execution record below:**
1. Whole-branch FF vs batched FF (staging/risk-appetite, not conflict-avoidance —
   there are no main-side conflicts either way).
2. multinexus INT↔LONG reconciliation method (merge INT→long / merge docs→INT / rebase
   INT's recovery onto long).
3. FF vs `--no-FF` (linear history vs an explicit integration merge commit for audit/rollback).

### Step 4 decision and execution record — DONE 2026-07-02

Executed after explicit human approval to follow the proposal and use `--no-FF`. Scope:
merge/reconcile and push only. No deploy, no mark-done, and 8.4.3 orig branches were not
deleted.

**Layer 1 — Git facts (VERIFIED 2026-07-02):**
- main is a pure ancestor of long/INT on both repos; main-side divergence = 0; merge to
  main is mechanically a fast-forward with no main-side conflicts.
- coordinate: INT (`4ac774e`) = long (`cbab1c5`) + 4 recovery; long is an ancestor of INT
  (no INT↔LONG divergence). INT history is fully linear (0 merge commits).
- multinexus: INT (`c91631a`) ↔ long (`e730807`) diverged from `1c5c798`; INT has 5
  recovery commits long lacks, long has 6 audit-docs/proposal commits INT lacks. The two sets touch
  **disjoint files** (recovery = code under `agentd/`/`adapters/`/`client.py`/tests; docs =
  `project-harness/*.md`), so merging them is conflict-free (verified via file-intersection).

**Layer 2 — Final decision:**
1. **Whole-branch single landing** (not batched). main is a pure ancestor (0 divergence ⇒
   no conflict risk for batching to reduce); the long branch is one coherent validated unit
   (all Phase 8 tasks durable-done; 8.4.2 lifecycle closed Step 1; 8.4.3 recovery cherry-picked
   + smoke-validated Steps 2/3). Batched FF does not improve bisect (history preserved either
   way) and only adds operational surface. Batching is justified only for staged deploy +
   observation — a separate (prohibited here) deploy decision.
2. **multinexus: merge INT → long** (feature recovery returns to the durable integration
   trunk; not docs→INT, not rebase/cherry-pick). Conflict-free (disjoint files); reuses the
   exact Step-2-validated recovery SHAs; consistent with long's existing merge-commit style.
3. **main landing: `--no-FF` merge commit** (both repos). For a +131/+230 milestone on shared
   `origin/main`, `git revert -m 1 <merge>` is the only clean non-destructive post-push
   rollback; cost is one merge commit per repo.
   - **Caveat / fallback:** if a repo or its branch protection enforces linear history, use
     **FF + annotated tag** (`git tag -a phase-8-integration <HEAD>`) as the audit/rollback
     anchor (rollback = reset to pre-tag). **Default remains `--no-FF`** — non-destructive
     rollback of a large shared main outweighs linear-history purity.
- Trunk tidiness (optional): advance `long` to include recovery first (coordinate: trivial
  `--ff-only` since long is INT's ancestor; multinexus: the INT→long merge above), then land
  main from `long`, so `long` stays the canonical integration source that production tracks.

**Executed commands / commits:**
- coordinate: long fast-forwarded to INT (`4ac774e`), then `main` landed via `--no-FF`
  merge commit `1810fd5` (`Merge Phase 8 integration (8.4.2 trunk + 8.4.3 recovery) into main`).
- multinexus: long reconciled with INT via `--no-FF` merge commit `1a77c65`
  (`merge Phase 8.4.3 recovery into integration trunk`), then `main` landed via `--no-FF`
  merge commit `d405ccd` (`Merge Phase 8 integration (8.4.x trunk + 8.4.3 recovery) into main`).

**Gates run before push:**
- multinexus reconcile gate: full suite **343 tests OK, 2 skipped**; `harnessctl validate`
  passed with the known 4 pre-existing warnings; `harnessctl doctor` completed with known
  optional/current MISS entries; `origin/main` remained an ancestor.
- coordinate main-tip gate: full suite **1200 passed, 58 subtests passed**; `harnessctl
  validate` passed with 0 warnings; `harnessctl doctor` completed with known optional/current
  MISS entries.
- multinexus main-tip gate: full suite **343 tests OK, 2 skipped**; `harnessctl validate`
  passed with the known 4 pre-existing warnings; `harnessctl doctor` completed with known
  optional/current MISS entries.
- `origin/main` ancestry was rechecked immediately before push; both repos remained safe to push.

**Rollback / stop conditions:**
- Any gate red → stop, do not push main.
- Unexpected conflict in multinexus reconcile (disjoint files, should not happen) → stop.
- Pre-push rollback: `git reset --hard origin/main` (discards local merge commit).
- Post-push rollback: `git revert -m 1 <merge-commit>` (the --no-FF benefit; non-destructive).
- Deploy is a separate gated step (`deploy-server.sh`); main merge does NOT auto-deploy.

**Layer 3 — Execution status: COMPLETE for merge-to-main.**
Long branches and `main` were pushed. Deploy and task lifecycle actions remain separate:
no deploy, no mark-done, no branch deletion.

### Post-state after Step 4 execution

- coordinate `origin/main` = `1810fd5`; coordinate long = `4ac774e`; INT remains `4ac774e`.
- multinexus main includes `d405ccd` (the `--no-FF` integration merge) plus this execution
  record commit; multinexus long = `1a77c65`; INT remains `c91631a`.
- Both main landings used `--no-FF`. Long branches were pushed before main pushes.
- Nothing deployed; nothing marked done; 8.4.3 orig branches not deleted.
- Next: any deployment or lifecycle closeout must be a separate explicit decision.

## 6. Remaining prohibitions after Step 4 execution

Step 4 main integration is complete. Remaining actions are still explicitly out of scope
unless separately approved:
- no deploy
- no mark-done / closeout
- no branch deletion
- no rebase / history rewrite
- no additional main merges beyond this recorded Step 4 execution

**Next step (separate approval):** decide whether to deploy and/or close the 8.4.2
lifecycle. Do not continue from chat context alone — drive it from this document.
