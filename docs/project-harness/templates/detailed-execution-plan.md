# Detailed Execution Plan: <package-id>

> **Status:** draft | in_review | approved | changes_requested | blocked | superseded
>
> This is an executable work-package plan. No worker bootstrap may be generated
> until an independent reviewer approves this exact revision.

## Identity and revision

- Parent stage: `<stage-id>`
- Package id: `<package-id>`
- Plan author / architect: `<actor>`
- Intended plan reviewer: `<actor, not the coding worker>`
- Intended coding worker: `<unassigned until plan approval is acceptable>`
- Intended code/result reviewer: `<actor>`
- Plan path: `<repo-relative-path>`
- Plan revision: `<git-commit-or-sha256>`
- Supersedes: `<revision-or-none>`

## Refreshed preflight

- Repository and current SHA:
- Base branch and upstream state:
- Existing worktree/branch state:
- Dirty or unrelated files to preserve:
- Current runtime/deployment state, if relevant:
- Current schema/protocol versions:
- Current test and harness baseline:
- Exact evidence paths and commands:

## Problem and evidence

State the concrete failure mode or missing capability. Cite current code paths,
runtime evidence, tests, or durable audit findings. Separate confirmed facts from
assumptions.

## Goal

One bounded outcome that a single worker session can implement and verify.

## Non-goals

- Explicit adjacent work that must not be included.
- Forbidden cleanup or speculative abstraction.
- Lifecycle actions requiring separate Operator authorization.

## Invariants and authority boundaries

- Facts and their authorities:
- Projection rules:
- Idempotency/retry requirements:
- Workspace/task/attempt isolation requirements:
- Security and secret boundaries:
- Human/Operator gates:

## Proposed changes

List exact repositories, modules, files, schemas, commands, and compatibility paths.
If multiple repositories are touched, state the contract and landing order.

## Failure and recovery matrix

Cover crashes, timeout, retry, replay, stale attempt, partial write, provider failure,
and rollback where applicable.

## Acceptance matrix

| Case | Setup | Expected result | Evidence |
|---|---|---|---|
| happy path | | | |
| authorization/isolation | | | |
| retry/replay | | | |
| failure/recovery | | | |
| compatibility | | | |

## Validation

- Focused regression tests:
- Full repository tests:
- Cross-repository contract tests:
- Harness validate/doctor:
- Runtime/multi-host smoke:
- Negative/adversarial probes:

State which checks are mandatory for worker handoff, local checkpoint, integration,
deployment, and durable closeout.

## Rollout and rollback

- Integration order:
- Migration/backward compatibility:
- Deployment/restart scope by host:
- Rollback procedure:
- Stop conditions:

## Worker boundaries

- Allowed worktree and branch:
- Allowed files/components:
- Allowed commands and side effects:
- Forbidden commit/push/merge/deploy/mark-done actions unless explicitly delegated:
- Required progress and final report format:
- Required JSONL/session/log handle when available:

## Plan review record

- Review artifact: `<path>`
- Reviewer:
- Verdict:
- Reviewed plan revision:
- Must-fix findings:
- Resolution revision:

Any material edit after `approved` resets the status to `in_review` and requires a
new review artifact before bootstrap generation.

## Bootstrap gate

After approval, generate `worker-bootstrap.md` in this package directory. The
bootstrap must include the approved plan path/revision and review artifact. Before
handoff, verify that those references still match the current plan.
