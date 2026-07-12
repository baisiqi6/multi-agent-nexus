# Reviewer Supplement: slice-3-c2-local-integration

This supplement corrects the generic generated bootstrap. It is authoritative when the
two artifacts conflict.

## Canonical inputs

There is no OpenSpec proposal for this package. Read these files instead:

1. `docs/project-harness/tasks/slice-3-c2-local-integration/plan.md`
2. `docs/project-harness/tasks/slice-3-completion-closeout/plan.md`
3. `docs/project-harness/tasks/slice-3-completion-closeout/integration-decision.md`
4. `docs/project-harness/tasks/slice-3-completion-closeout/local-code-review.md`
5. `/Users/yinxin/Documents/Codex/2026-07-10/ni/outputs/slice3-review-report.md`
6. Current read-only Git facts in `/Users/yinxin/projects/coordinate`

Reviewed plan identity:

- `plan.ready` event: `01f7dd53-2336-46a2-9d4e-f76908ecf038`
- Full plan SHA256:
  `aea8b2dd7a8348904fd1ffadc3a649c79355c76eba9c2d806d8adbff78e898ee`
- Coordinate source: `1b862129897be001e5a9078b7b4fad48d90d89c2`
- Current base snapshot: `8fadd687d68032cf656291e6bf537ec481fb3e25`

## Review constraints

- Strictly read-only. Do not edit files, branches, worktrees, DB state, lifecycle state,
  deliveries, processes, or remotes.
- Do not run tests that write repository artifacts. Prior baselines are evidence to
  assess; the plan requires fresh post-integration tests from the coding worker and
  independent result reviewer.
- Read-only Git commands are allowed. If shell permissions are denied, use file reads and
  report the limitation rather than broadening permissions.
- Do not approve any coding worker, cherry-pick, `main` advancement, push, deployment, or
  multi-host smoke. This review decides only whether the plan is safe and executable.

## Required review questions

1. Is a single automatic cherry-pick with stop-on-conflict the smallest safe integration
   method for this reviewed single-commit patch?
2. Do patch-ID equality, exact eight-path equivalence, diff inspection, and schema checks
   adequately prevent source substitution or hook-induced drift?
3. Are focused/full tests and the adversarial receipt matrix sufficient to distinguish
   source-branch PASS from integrated-branch PASS?
4. Are provider failure, partial session recovery, conflict handling, and reviewer-
   requested correction paths fail-closed without destructive Git recovery?
5. Are the worker, result-reviewer, human `main` gate, and later S3-C3 deployment gate
   clearly separated?
6. Is any allowed command or path broader than necessary?

Return `approve`, `changes_requested`, or `blocked`. Separate must-fix findings from
optional observations. Include exactly one report block:

```text
[agent-report]
decision=<approve|changes_requested|blocked>
workspace_id=discord-nexus
task_id=slice-3-c2-local-integration
summary="<bounded verdict>"
```

