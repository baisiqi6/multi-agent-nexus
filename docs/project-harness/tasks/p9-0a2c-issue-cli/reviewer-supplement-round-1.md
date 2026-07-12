# P9-0A2c Plan Reviewer Supplement — Round 1

This supplement overrides generic or stale paths in `reviewer-bootstrap.md`.

## Exact authority

- Review only this canonical plan:
  `docs/project-harness/tasks/p9-0a2c-issue-cli/plan.md`
- Required full SHA-256:
  `d5ff4620afc7799bcc050c960bd1491f82a136ec829431f92d04e021bb88d444`
- Plan commit: `3fef5b17a32865f25a6a411ded1f8b52d02d91ef`
- Coordinate code snapshot to verify read-only:
  `/Users/yinxin/projects/coordinate` at
  `38da30f8bb508638e0cc30c301968153a420bdb7`
- MultiNexus review cwd: `/Users/yinxin/projects/multinexus`

There is no `openspec/changes/p9-0a2c-issue-cli` proposal. Do not search for or review
that generated fallback. `feature/multi-bot` and `/opt/multinexus` are control-plane
metadata/deployment paths, not review checkout authority.

## Role and permissions

- You are an independent **plan reviewer**, not the coding worker.
- Strictly read-only: do not edit, format, commit, push, deploy, invoke lifecycle
  commands, create a worktree, switch branches, or contact GitHub/production services.
- Read-only shell inspection, SHA calculation, AST/source measurement, and test
  execution against the canonical Coordinate checkout are allowed.
- Run tests from `/Users/yinxin/projects/coordinate`, never from MultiNexus by mistake.

## Adversarial review focus

1. Verify current Coordinate identity, 2,115-line root, five issue leaves, 107 moved
   handler lines, 21/75/99 contract, fixture SHA `adddac8...`, focused 265 and full
   1,411 baselines.
2. Verify the single registrar can stay exactly after merge and before job.
3. Challenge whether the allowed paths are sufficient while keeping `issues.py`
   unchanged and preserving direct root aliases.
4. Verify three-layer rewind proof is strong: C -> `adddac8...`, C+B ->
   `652a77d5...`, C+B+A2a -> `83c4c181...`, including negative non-handler drift.
5. Verify the plan protects `--event-cli-path` from local DB use and keeps combined,
   files-only, and record-only responsibilities unchanged.
6. Look for tests that patch the wrong symbol after `_conn` alias binding, live GitHub/
   DB leakage, import cycles, contract self-blessing, or scope creep into Slice 4.

## Required verdict

Return exactly one machine-readable block with `decision=approve` or
`decision=reject`, `workspace_id=discord-nexus`, and `task_id=p9-0a2c-issue-cli`.
Approval means no must-fix remains; nonblocking notes must be explicitly labeled.
