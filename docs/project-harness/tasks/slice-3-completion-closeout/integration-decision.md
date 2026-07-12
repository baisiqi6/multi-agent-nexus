# Slice 3 Integration Decision (Proposed S3-C2 Method)

> **Status: proposed integration method and preconditions.** This document does not
> authorize a cherry-pick, merge, push, deploy, or any runtime mutation. S3-C2 must
> refresh all SHAs, write its own detailed plan, and receive its own independent plan
> review before any integration action.

## Scope of this decision

This artifact owns the proposed local integration method for the reviewed Slice 3
checkpoint and the checks S3-C2 must satisfy before accepting local integration. It does
not assert that integration occurred. Deployment, real multi-host smoke, and durable
closeout (S3-C3, S3-C4) are out of scope here.

## Reviewed checkpoint identity (refreshed during S3-C1, 2026-07-12)

- Slice 3 source commit: `1b862129897be001e5a9078b7b4fad48d90d89c2`
  on `agents/mac-claude/slice-3-completion-receipt`.
- Source stable patch ID: `eb204296bd6a09e4caccabfe4bb05802e7ef7b37`.
- Common ancestor of Coordinate `main` and the Slice 3 source:
  `a2ad92d2bf13ec894979c082897a713f3870d130`.
- Coordinate `main` at the S3-C1 reviewed plan snapshot:
  `46a75dab8de77d147ceff817241cfc49a495e4ca`.
- Coordinate `main` at this audit session:
  `b1e9af1f43a0cfbe142747e10fc2c8d2e9cff703`, drifted from the plan snapshot only by the
  documentation-only operator-backlog checkpoint (`docs/operator-needs-backlog.md`).

S3-C2 must re-resolve every SHA above from the repositories at execution time. The values
here are a refreshed snapshot, not a forward guarantee.

## Current changed-path non-overlap (snapshot evidence, not a guarantee)

In the refreshed snapshot there is no changed-path overlap between Coordinate `main` and
the Slice 3 checkpoint, measured from the shared ancestor `a2ad92d2`:

- Coordinate `main` (`46a75da` vs ancestor): `skills/coordinate-operator/SKILL.md`,
  `skills/coordinate-operator/references/worker-observation.md`. The `b1e9af1` checkpoint
  adds only `docs/operator-needs-backlog.md`.
- Slice 3 source (`1b86212` vs ancestor): `docs/runbook.md`, `src/coordinate/cli.py`,
  `src/coordinate/completion.py`, `src/coordinate/db.py`, `src/coordinate/transitions.py`,
  `tests/test_cli.py`, `tests/test_completion.py`, `tests/test_transitions.py`.

This observation reduces the likelihood of a textual cherry-pick conflict but does not
remove the requirement to inspect the actual cherry-pick result. Any later `main` change
that touches these eight files, or a semantic interaction with the operator-skill files,
must be treated as a real conflict and resolved by a revised plan, not by assumption.

## Proposed S3-C2 method

1. From the then-current Coordinate `main`, create a fresh isolated integration branch
   (for example `integration/slice-3-receipt`) in a dedicated worktree. Do not integrate
   on `main` directly.
2. Apply the single reviewed Slice 3 commit through a controlled cherry-pick of
   `1b86212`. Do not squash, reword, or rebase other history onto the integration branch.
3. Inspect the resulting diff and the cherry-pick commit identity before running any
   tests. If the cherry-pick conflicts or produces an unexpected diff, stop and return for
   a revised plan.

## Preconditions for accepting local integration

S3-C2 must satisfy all of the following before local integration is accepted:

- **Patch identity:** the integrated commit's stable patch ID equals the source patch ID
  `eb204296bd6a09e4caccabfe4bb05802e7ef7b37` (recompute with
  `git patch-id --stable`); record both the source and integrated patch IDs.
- **Changed-file equivalence:** the integrated diff touches exactly the eight reviewed
  files with equivalent content; record the changed-file set.
- **Focused tests:** transition, CLI, and completion suites pass with at least the
  checkpoint counts (transitions 131, CLI 169, completion 42 — prior-review evidence
  rechecked against the report, not rerun by this document).
- **Full suite:** the full local suite passes (checkpoint baseline
  `1347 passed, 58 subtests passed` — prior-review evidence, not rerun here).
- **Schema compatibility:** no unapproved schema migration; `db.py` changes remain
  compatible with the running schema.
- **Harness validation:** `git diff --check` and checklist validation pass, and
  `harnessctl validate` passes; `harnessctl doctor` introduces no new invalid/missing
  items beyond the recorded S3-C1 baseline (which already has optional MISS items such
  as `harness-state.json`, `events.jsonl`, `current/task_plan.md`,
  `round-2-hardening/plan.md`, and `init.sh`).
- **Adversarial probes:** receipt forgery, actor binding, fingerprint drift, expiry,
  replay, fail-after-write, and idempotent retry drift are re-probed and behave as
  accepted at the checkpoint; the final retry returns `before_fingerprint_mismatch` and
  leaves the canonical item `doing/blocked`.

Local integration acceptance is still not deployment or multi-host PASS. S3-C3 owns the
explicitly authorized deploy and real `coord-ssh` smoke; S3-C4 owns durable closeout.

## Authority and rollback

- This document proposes a method; Coordinate job/events and the Operator remain the
  runtime authority for integration, deployment, and closeout.
- S3-C2 must receive its own independent plan review and approved plan evidence before any
  cherry-pick. A material change to this method invalidates that review.
- Rollback for the local integration is a revert of the integration branch only; it must
  not touch `main`, runtime state, or the reviewed checkpoint commit.
- Stop immediately on a cherry-pick conflict, an unexpected diff, a patch-ID mismatch, a
  test regression, a schema incompatibility, or any request for production mutation.
