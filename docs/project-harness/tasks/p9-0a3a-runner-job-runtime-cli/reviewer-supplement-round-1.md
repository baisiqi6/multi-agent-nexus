# P9-0A3a Plan Reviewer Supplement — Round 1

This supplement overrides generic or stale paths in `reviewer-bootstrap.md`.

## Exact authority

- Review only:
  `docs/project-harness/tasks/p9-0a3a-runner-job-runtime-cli/plan.md`
- Required SHA-256:
  `9118489edcbcbf8fe18943658c83f706c2c9d441fc9f58ba5a68fac277763c1a`
- Plan commit: `eaa74a5da953799f4a73c7b40e7ae6d0b98aecc7`
- Coordinate read-only snapshot:
  `/Users/yinxin/projects/coordinate` at
  `10135bc3a49365a6c79d2088f4e3ff4b8015f27a`
- MultiNexus review cwd: `/Users/yinxin/projects/multinexus`

There is no `openspec/changes/p9-0a3a-runner-job-runtime-cli`. `/opt/multinexus` and
`feature/multi-bot` are control/deploy metadata, not review checkout authority.

## Role and permissions

- Independent plan reviewer only; never act as worker.
- Strictly read-only: no edits, format, commit, push, deploy, lifecycle, worktree, branch
  switch, live DB/runtime/job, GitHub, or SSH mutation.
- Read-only source/AST/hash/test commands are allowed. Run Coordinate tests only from
  `/Users/yinxin/projects/coordinate`.

## Adversarial review focus

1. Verify the 0A3a/b refinement is justified by current code rather than arbitrary:
   16 execution leaves/166 lines/three positions vs 10 delivery leaves/107 lines/one
   contiguous range.
2. Verify all 16 leaves, 166 handler lines, 1,909-line root, 21/75/99 contract, fixture
   `dde4c0d7...`, focused 241 and full 1,434 baselines.
3. Verify three registrar positions are sufficient and exact without reordering any
   delivery/workflow family.
4. Challenge allowed paths and service-import cleanup. In particular, root `main()`
   must retain `JobError`, `BusError`, and `PolicyError` catches while unused runtime
   `RuntimeError` may be removed only if behavior is unchanged.
5. Verify four-layer full-baseline rewind cannot self-bless fixture drift.
6. Verify permanent AST proof uses stable constants, not `git show` or checkout history.
7. Challenge mock isolation for job execution/runtime claim/report/progress so no test
   can spawn subprocesses, claim real jobs, or touch a live DB.
8. Reject any P9-0A3b delivery change or Slice 4/P9-1 behavior creep.

## Required verdict

Return must-fix findings and clearly labeled nonblocking notes. End with exactly one
`[agent-report]` block containing `decision=approve` or `decision=reject`,
`workspace_id=discord-nexus`, and
`task_id=p9-0a3a-runner-job-runtime-cli`.
