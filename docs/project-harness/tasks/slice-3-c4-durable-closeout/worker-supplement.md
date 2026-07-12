# S3-C4 Worker Supplement

This supplement is authoritative when `worker-bootstrap.md` disagrees with it. The
generated bootstrap still assumes the historical shared checkout/`feature/multi-bot`
branch and suggests worker-owned lifecycle/deploy actions. Those instructions are not
valid for this package.

## Approved gate

- Canonical plan:
  `docs/project-harness/tasks/slice-3-c4-durable-closeout/plan.md`
- Full plan SHA-256:
  `6190b93f1ce28ed31d891019d758fddb01d1c7e01dda01b39fa2fb9b38cbe32b`
- Plan-ready event: `cb163ad0-9a34-4353-a585-dd954c325b0a`
- Plan-approved event: `67c0e2be-69e5-442f-913e-7eb88d26579e`
- Plan review:
  `docs/project-harness/tasks/slice-3-c4-durable-closeout/plan-review-round-1.md`
- Reviewer verdict: approved, no P0/P1 must-fix findings

Recompute the plan SHA before editing. Any mismatch stops the session.

## Exact workspace

- Worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-s3-c4-closeout`
- Branch: `agents/mac-omp/slice-3-c4-durable-closeout`
- Expected start: the Operator will fast-forward this worktree to the canonical
  bootstrap/supplement commit before invocation. Record and return the actual start SHA.
- The canonical checkout `/Users/yinxin/projects/multinexus` is read-only evidence for
  this worker. Do not edit or commit there.

Stop if `pwd`, branch, plan hash, plan-review artifact, or approved event references do
not match. Do not switch, reset, rebase, cherry-pick, or repair the worktree.

## Worker role and scope

You are a non-Codex documentation worker. Codex remains architect, Operator, and result
reviewer. You may create or modify exactly these six paths in the isolated worktree:

1. `docs/project-harness/tasks/slice-3-completion-closeout/closeout.md`
2. `docs/project-harness/source-of-truth-audit.md`
3. `docs/project-harness/tasks/slice-3-completion-closeout/plan.md`
4. `docs/project-harness/roadmap.md`
5. `docs/project-harness/progress.md`
6. `docs/project-harness/dogfood-feedback.md`

Follow the detailed content requirements in the canonical plan. Historical S3-C1,
S3-C2, and S3-C3 plans/reviews/reports are read-only evidence.

## Forbidden actions

- Do not edit `mvp-checklist.json`, `events.jsonl`, `harness-state.json`, current
  packets, runtime code, tests, config, deployment scripts, or proxy files.
- Do not invoke Coordinate lifecycle commands, `assignment accept`, `closeout`,
  `review-result`, receipt commands, or any `mark-done`; the Operator owns all of them.
- Do not use SSH, direct DB access, deploy/restart, Discord/KOOK delivery, sidecar
  cleanup, push, merge, or Phase 9/Slice 4 implementation.
- Do not run the generic bootstrap's full unit-test or deploy instructions. This is a
  documentation-only package; runtime-code drift is a scope violation, not a reason to
  broaden validation.
- Do not copy proxy config/node content, secrets, tokens, key paths, raw prompts,
  private reasoning, or unredacted DB rows into artifacts.

## Required evidence handling

- Distinguish local repository HEAD, upstream release identity, and deployed
  `VERSION_DEPLOYED` identities.
- Preserve separate code-review, local-integration, control-plane, worker-execution,
  dogfood, and closeout verdicts.
- Keep the retained sidecar and all failed drift-fixture evidence visible.
- Keep stale interrupted-recovery projection, deploy non-atomicity, smoke-window false
  positive, CLI ergonomics, missing workspace delete, and missing full-dogfood host
  profile routed as unresolved follow-up.
- S3-C4 worker documentation may say "ready for Operator closeout"; it must not claim
  S3-C3/S3-C4/Slice 3 lifecycle is already closed.

## Validation

Run from the isolated worktree:

```bash
git status --short
git diff --check
jq empty docs/project-harness/mvp-checklist.json
scripts/harness/harnessctl validate
scripts/harness/harnessctl doctor
git diff --name-only <start-sha>...HEAD
```

Validation must show only the six allowed paths in the worker commit, checklist
validation with no warnings beyond the recorded six, and no new doctor finding. Do not
edit baseline warnings or misses.

## Commit and return

- Make one local documentation commit on the isolated branch.
- Do not push or merge it.
- Return start/commit SHAs, exact changed paths, validation results, residual risks, and
  the provider-native OMP session/JSONL handle.
- Do not request lifecycle closeout. End with one report block for the Operator's
  result-review intake:

```text
[agent-report]
action=done
workspace_id=discord-nexus
task_id=slice-3-c4-durable-closeout
summary="Prepared bounded S3-C4 durable closeout documentation; lifecycle remains Operator-only."
```
