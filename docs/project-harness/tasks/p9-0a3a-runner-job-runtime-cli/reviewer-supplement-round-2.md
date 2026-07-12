# P9-0A3a Plan Reviewer Supplement — Round 2

This supplement overrides generic or stale paths in `reviewer-bootstrap.md` and
supersedes the Round 1 supplement wherever the two differ.

## Exact authority

- Review only:
  `docs/project-harness/tasks/p9-0a3a-runner-job-runtime-cli/plan.md`
- Required SHA-256:
  `66784772f8b356018bdb1674b56c00bf602bb76ce226c8acb0b789e52cf49b9b`
- Plan commit: `d5b9783995496c70e07a3db319610f88c8e21210`
- Superseded SHA-256:
  `9118489edcbcbf8fe18943658c83f706c2c9d441fc9f58ba5a68fac277763c1a`
- Coordinate read-only snapshot:
  `/Users/yinxin/projects/coordinate` at
  `10135bc3a49365a6c79d2088f4e3ff4b8015f27a`
- MultiNexus review cwd: `/Users/yinxin/projects/multinexus`

There is no `openspec/changes/p9-0a3a-runner-job-runtime-cli`. `/opt/multinexus` and
`feature/multi-bot` are control/deploy metadata, not review checkout authority.

## Round 2 change scope

Round 1 found that the 273 total handler lines were attributed to the two packages
incorrectly. The corrected measured split is:

- P9-0A3a: 16 execution leaves and 159 handler lines:
  runner 33 + job 56 + runtime 70.
- P9-0A3b: 10 delivery/policy/worker leaves and 114 handler lines:
  delivery 56 + policy 44 + worker 14.
- Total remains 26 leaves and 273 handler lines.

Re-review the exact corrected plan hash. Do not approve the superseded Round 1 hash.
Confirm that the correction is complete and did not accidentally change scope,
registrar positions, contract proof, allowed paths, test baselines, or permissions.

## Role and permissions

- Independent plan reviewer only; never act as worker.
- Strictly read-only: no edits, format, commit, push, deploy, lifecycle, worktree,
  branch switch, live DB/runtime/job, GitHub, or SSH mutation.
- Read-only source/AST/hash/test commands are allowed. Run Coordinate tests only from
  `/Users/yinxin/projects/coordinate`.

## Required verdict

Return must-fix findings and clearly labeled nonblocking notes. End with exactly one
`[agent-report]` block containing `decision=approve` or `decision=reject`,
`workspace_id=discord-nexus`, and
`task_id=p9-0a3a-runner-job-runtime-cli`. An approval must explicitly name the
corrected SHA-256 above.
