# Slice 3 Completion Authorization Closeout

> **Plan level: roadmap overview.** This file defines boundaries and work packages;
> it is not an executable worker plan and must not be used directly as a bootstrap.

## Goal

Durably close the completion authorization receipt work while preserving separate
verdicts for code correctness, local integration, deployment, real multi-host
execution, and project closeout.

## Current accepted evidence

- Coordinate Slice 3 worker checkpoint: `1b86212` on
  `agents/mac-claude/slice-3-completion-receipt`.
- Coordinate `main` includes the worker-observation protocol at `46a75da`.
- Independent full validation reported `1347 passed, 58 subtests passed`.
- Independent adversarial review covered receipt forgery, actor binding,
  fingerprint drift, expiry, replay, fail-after-write, and idempotent retry drift.

These are local planning facts. They do not assert that the branch is integrated,
deployed, or proven through real `coord-ssh` execution.

## Work packages

### S3-C1 — Durable audit and integration plan

Refresh current SHAs and diffs; update the cross-repository source-of-truth audit;
define the exact local integration method and compatibility checks. This package is
documentation/integration planning only.

### S3-C2 — Local integration and regression validation

Integrate the approved Slice 3 checkpoint with current Coordinate `main` in an
isolated branch or worktree. Re-run focused/full tests, schema compatibility,
`git diff --check`, harness validation, and adversarial receipt probes.

### S3-C3 — Authorized deployment and multi-host smoke

Only after separate Operator authorization, deploy the reviewed integration and run
the real host/server receipt sequence: prepare, files apply, record consume, replay,
expiry, fingerprint drift, and interrupted recovery. Preserve control-plane PASS and
worker-execution PASS as separate results.

### S3-C4 — Durable closeout

Record exact deployed SHAs, runtime evidence, residual risks, and reviewer verdict;
then update checklist/progress/audit without claiming more than the evidence proves.

## Mandatory gates

- Each work package becomes its own checklist item with a detailed plan at
  `tasks/<package-id>/plan.md`, matching the existing harness tooling contract.
- Each detailed plan is independently reviewed before bootstrap generation.
- S3-C2 cannot begin from chat memory or stale branch assumptions.
- S3-C3 requires explicit deploy/runtime authority and host-aware preflight.
- No worker may mark Slice 3 done; the Operator performs durable closeout only after
  reviewer acceptance.

## Non-goals

- Slice 4 projection hardening.
- Phase 9 routing or concurrency changes.
- Broad completion framework abstraction beyond the reviewed receipt protocol.
- Push, merge, deploy, production DB mutation, service restart, or real remote smoke
  merely because this overview exists.

## Stage acceptance

- Slice 3 is integrated on the intended branch with a reviewed commit identity.
- Local and real multi-host evidence are separately recorded.
- Repair-only compatibility paths remain explicit and cannot bypass receipt authority.
- The durable audit, progress, checklist, and runtime facts agree.
- Reviewer and Operator verdicts are attributable and no open P0/P1 finding remains.
