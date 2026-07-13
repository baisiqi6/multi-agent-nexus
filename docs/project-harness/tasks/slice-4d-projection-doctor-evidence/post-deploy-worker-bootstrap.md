# Slice 4D Post-Deploy Correction Worker Bootstrap

## Authorization

- Parent task: `slice-4d-projection-doctor-evidence`.
- Coordinate start: `0563cc01f9b12d5c196f59aaece8d81d1d5e5bc5`.
- Plan: `post-deploy-correction-plan.md`.
- Exact approved plan SHA-256:
  `635b54c74e7705aaa469e06e6bf1609027251b75ffa7319e4b9ceba0ef39be94`.
- Round 2 plan review: `post-deploy-plan-review-round2.md`.
- Review artifact commit: `fbbbdd41a2e061bde32024ae7632206eb28417f9`.
- Verdict: APPROVE, 0 P0, 0 P1.

Before editing, verify the plan hash and read the plan plus both review rounds in full.

## Worker role and provider

- Worker: OMP `kimi-for-coding-highspeed`, high thinking.
- Do not start nested agents.
- Do not switch providers. Stop only for an explicit Kimi quota/auth/provider failure;
  Codex alone decides whether to restart with GLM.
- JSONL is the primary live-activity evidence.

## Worktree and branch

- Worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-s4d-kimi`.
- Existing branch: `agents/mac-omp/slice-4d-projection-doctor-evidence`.
- Confirm clean `HEAD=0563cc0` before editing.

## Required implementation

Implement every approved plan requirement, especially:

1. historical task-create input/after proof from immutable record event + neutral
   `split_operations.py` helpers;
2. current immutable creation identity vs allowed lifecycle evolution;
3. exact approved plan supersession through full SHA, explicit supersedes chain,
   exact `plan.approved.plan_ready_event_id`, and rowid-based rejection invalidation;
4. full `plan_sha256` and `supersedes_plan_ready_event_id` on future split and
   non-split `plan.ready` write paths, with idempotent retries;
5. legacy missing evidence remains fail-closed;
6. no doctor writes, subprocess, shell-out, repair, hard-coded task/event/SHA exception,
   or `--no-projections` acceptance.

Update/replace the two known inadequate production-like tests and implement the full
positive/negative matrix from the plan.

## Allowed paths

Only the paths authorized by the approved plan. Keep `src/coordinate/cli.py` exact to
`0563cc0`; do not edit MultiNexus, receipt code, DB schema, or unrelated CLI routing.

## Verification and end protocol

- focused projection/split/onboarding/plan-gate tests;
- production-shape lifecycle and plan-supersession fixtures;
- no-write proof;
- full suite with no failure beyond the same historical nine;
- ruff, compileall, `git diff --check`;
- exact `cli.py` byte check;
- complete diff review and one worker commit;
- no push, deploy, production, lifecycle mutation, or closeout.

Return commit SHA, changed paths, exact test counts, residual risks, JSONL session, and
one `[agent-report]` marker.

