# S3-C1 Worker Supplement

This supplement is the task-specific authority for the documentation worker. It
corrects stale generic fields in the generated `worker-bootstrap.md` without
editing that generated evidence artifact.

## Execution identity

- Worker provider: OpenCode
- Operator / result reviewer: Codex
- Approved plan event: `e1b0e261-f852-4d30-b5e1-aba984e77f33`
- Approved `plan.ready` event: `b403c8ce-4a91-4e12-9e52-263d5c699e8b`
- Full plan SHA-256:
  `b8e342648a434b85266abe292e277a220d50564a28126021ffe163461baf2d73`
- Plan review: `plan-review-round-1.md`, verdict `approved`, must-fix `none`

## Worktree authority

The generated bootstrap's `/Users/yinxin/projects/multinexus` and
`feature/multi-bot` worktree guard is stale. Do not work in that checkout and do
not switch it. The Operator will start OpenCode with this isolated worktree as
its current directory:

- Worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-s3-c1-opencode`
- Branch: `agents/mac-opencode/slice-3-c1-audit-integration-plan`
- Worktree base: MultiNexus `0dc4185578a758764367dbd2e19cb06b3b009b5e`

Stop and report a blocker if `pwd`, branch, or base does not match. Do not run
`git switch`, `git checkout`, `git reset`, `git rebase`, or `git cherry-pick`.

## Exact assignment

Read, in order:

1. `worker-bootstrap.md` as generated control-plane evidence;
2. this supplement, which overrides conflicting generic bootstrap fields;
3. `plan.md` and `plan-review-round-1.md`;
4. the project harness scope, architecture, domain model, roadmap, source-of-truth
   audit, and Slice 3 closeout overview.

Modify or create exactly these three paths:

1. `docs/project-harness/source-of-truth-audit.md`
2. `docs/project-harness/tasks/slice-3-completion-closeout/local-code-review.md`
3. `docs/project-harness/tasks/slice-3-completion-closeout/integration-decision.md`

Do not update `progress.md`, `mvp-checklist.json`, `roadmap.md`,
`harness-state.json`, runtime code, tests, or Coordinate files. Do not commit,
push, merge, rebase, deploy, restart services, access a remote DB, use real
Discord/KOOK delivery, run real `coord-ssh`, call lifecycle commands, request
closeout, or mark the task done.

The current Coordinate `main` is
`b1e9af1f43a0cfbe142747e10fc2c8d2e9cff703`, moved from the approved plan's
`46a75da` snapshot only by the documentation-only operator-backlog checkpoint.
Preserve the reviewed historical snapshot and explicitly state that S3-C2 must
refresh then-current `main`; do not claim that future non-overlap is guaranteed.

Run all validation listed in `plan.md`, plus verify that
`git diff --name-only` contains only the three allowed paths. Return exact changed
paths, refreshed evidence, validation results, remaining risks, and the OpenCode
session/log handle if exposed. A clean diff is not permission to broaden scope.
