# Detailed Execution Plan: slice-3-c2-local-integration

> **Status:** in_review
>
> This plan may be reviewed now. It does not authorize a coding-worker bootstrap,
> cherry-pick, Coordinate `main` update, push, deploy, service control, production DB
> mutation, or real multi-host smoke until an independent reviewer approves this exact
> revision.

## Identity and revision

- Parent stage: `slice-3-completion-closeout` / `S3-C2`
- Package id: `slice-3-c2-local-integration`
- Plan author / architect: Codex
- Intended plan reviewer: independent Claude Code CLI session; record the effective
  response model reported by provider JSONL instead of assuming the requested alias
- Intended coding worker: unassigned until approval; prefer OpenCode or Oh-My-Pi in an
  isolated Coordinate worktree, distinct from the plan-review session
- Intended code/result reviewer: Codex
- Plan path:
  `docs/project-harness/tasks/slice-3-c2-local-integration/plan.md`
- Plan revision authority: latest Coordinate `plan.ready` event and its
  `plan_content_hash`
- Supersedes: the proposed method in
  `docs/project-harness/tasks/slice-3-completion-closeout/integration-decision.md`
  only as the executable S3-C2 plan; the decision artifact remains historical evidence

## Refreshed preflight

Snapshot refreshed on 2026-07-12:

- Coordinate repository: `/Users/yinxin/projects/coordinate`
- Coordinate base branch: `main`
- Current Coordinate `main`:
  `8fadd687d68032cf656291e6bf537ec481fb3e25`, four local commits ahead of
  `origin/main`; unrelated `.qoder/` is untracked and must remain untouched.
- Reviewed Slice 3 branch:
  `agents/mac-claude/slice-3-completion-receipt`
- Reviewed Slice 3 commit:
  `1b862129897be001e5a9078b7b4fad48d90d89c2`
- Common ancestor:
  `a2ad92d2bf13ec894979c082897a713f3870d130`
- Source stable patch ID:
  `eb204296bd6a09e4caccabfe4bb05802e7ef7b37`
- Current main-side changes after the ancestor affect only:
  `docs/operator-needs-backlog.md`,
  `skills/coordinate-operator/SKILL.md`, and
  `skills/coordinate-operator/references/worker-observation.md`.
- Slice 3 affects exactly eight paths:
  `docs/runbook.md`, `src/coordinate/cli.py`,
  `src/coordinate/completion.py`, `src/coordinate/db.py`,
  `src/coordinate/transitions.py`, `tests/test_cli.py`,
  `tests/test_completion.py`, and `tests/test_transitions.py`.
- The two changed-path sets do not overlap. Applying the exact source patch to current
  `main` passes `git apply --check`; this is textual preflight evidence, not proof of a
  future cherry-pick result.
- Fresh full baselines with `PYTHONDONTWRITEBYTECODE=1`:
  - current Coordinate `main`: 1,263 tests passed in 61.306 seconds;
  - reviewed Slice 3 branch: 1,347 tests passed in 70.545 seconds.
- The Slice 3 `db.py` change adds event-query helpers only. It does not add or modify DDL,
  schema version, migration, or table ownership.
- MultiNexus local `main`: `79f73e7907f5bb4c48e4d10909eaebe62dcf7ae`
  before this plan draft; no push is authorized.
- Accepted local-review evidence:
  `docs/project-harness/tasks/slice-3-completion-closeout/local-code-review.md` and
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/outputs/slice3-review-report.md`.
- No integration branch/worktree has been created for S3-C2, no cherry-pick has been
  attempted, and no runtime/deployment state has changed.

All Git identities, changed paths, test baselines, and patch IDs must be refreshed again
immediately before a coding-worker bootstrap. Relevant drift invalidates this plan
approval and returns the package to review.

## Problem and evidence

Slice 3 is code-review accepted only. Its single reviewed commit is not an ancestor of
Coordinate `main`, so the completion receipt implementation is absent from the active
local integration branch. S3-C1 documented a controlled cherry-pick method, but that
documentation deliberately did not authorize the Git operation or validate the result
against the newer `8fadd68` main snapshot.

The primary risks are not speculative merge complexity. They are:

1. integrating a stale or substituted commit instead of the reviewed patch;
2. silently resolving a conflict or accepting an unexpected diff;
3. treating green source-branch tests as proof of the integrated result;
4. changing Coordinate `main` before independent result review; and
5. conflating local integration PASS with deployment or real multi-host PASS.

## Goal

In one bounded worker session, create an isolated integration branch from the refreshed
Coordinate `main`, apply exactly the reviewed `1b86212` patch without manual conflict
resolution, and produce independently verifiable local integration evidence. Leave
Coordinate `main`, all remotes, services, databases, and host runtimes unchanged.

## Non-goals

- Do not modify the reviewed receipt design or add new functionality.
- Do not refactor `completion.py`, split `cli.py`, optimize `latest_event()`, or begin
  Slice 4 or Phase 9 work.
- Do not edit files outside the eight reviewed Slice 3 paths.
- Do not resolve cherry-pick conflicts, amend/reword/squash the integrated commit, or
  make follow-up fixes in the integration session.
- Do not fast-forward or merge the integration result into Coordinate `main`.
- Do not push, open a PR, deploy, restart services, access a production DB, send a real
  Discord/KOOK delivery, or run real `coord-ssh`/multi-host smoke.
- Do not update MultiNexus checklist JSON directly or mark S3-C2/Slice 3 done.

## Invariants and authority boundaries

- Git owns commit, ancestry, changed-path, content, and patch-identity facts.
- `1b86212` is the only authorized source commit. A different commit with similar files
  is not an implicit substitute.
- Source and integrated stable patch IDs must match. The integrated commit SHA may differ
  because its parent differs.
- The integration worker may create only the isolated branch/worktree and the automatic
  cherry-pick commit. It may not change `main` or repair conflicts.
- Tests and adversarial probes establish local behavior only; they do not establish
  deployment, SSH, remote-database, or multi-host behavior.
- Existing `events` storage remains the receipt authority. No DDL or migration may appear
  in the integrated diff.
- `.qoder/` and all user/unrelated files remain untouched.
- Provider-native JSONL/session events are liveness evidence. Git diff, patch identity,
  tests, and reviewer verification are correctness evidence.
- The coding worker cannot approve its own result. Codex reviews the integration result;
  a separate human gate is required before any local `main` fast-forward.

## Proposed execution

### 1. Operator pre-bootstrap refresh

Before generating a coding-worker bootstrap:

- re-resolve `main`, source commit, merge base, source patch ID, and both changed-path sets;
- require Coordinate `main` to be clean except for the known untracked `.qoder/`;
- rerun `git diff 1b86212^ 1b86212 | git apply --check -` against current `main`;
- verify no active S3-C2 assignment/lease or pre-existing integration worktree exists;
- if any relevant source/main path changed, stop, revise this plan, emit a new
  `plan.ready`, and obtain a new independent approval.

### 2. Isolated worker materialization

- Create a fresh Coordinate worktree from the then-current `main` on branch
  `agents/<worker>/slice-3-c2-local-integration`.
- Record the exact base SHA and worktree path in the bootstrap.
- The worker verifies branch, base, clean status, source SHA, and plan/review references
  before accepting the assignment.

### 3. Controlled integration

- Run exactly one `git cherry-pick 1b862129897be001e5a9078b7b4fad48d90d89c2` in the
  isolated worktree.
- If Git reports a conflict, empty patch, hook failure, or unexpected state, stop and
  report `blocked`. Do not continue, abort, resolve, stage, commit, or edit files unless
  the Operator gives a separately reviewed recovery instruction.
- On success, record the resulting commit SHA and parent SHA.

### 4. Structural equivalence checks

- Recompute source and integrated stable patch IDs and require equality.
- Require the integrated commit to change exactly the eight reviewed paths.
- Require `git diff <base>..<integrated>` content to equal the reviewed source patch
  modulo commit metadata, as evidenced by stable patch identity and explicit diff review.
- Reject any DDL/schema-version/migration change or any file outside the allowed set.
- Run `git diff --check <base>..<integrated>`.

### 5. Local behavioral validation

Run from the isolated integration worktree with bytecode writes disabled:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_completion tests.test_transitions tests.test_cli
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover \
  -s tests -p 'test_*.py'
scripts/harness/validate_checklist.py docs/mvp-checklist.json
```

Focused minimums are completion 42, transitions 131, and CLI 169. The full integrated
suite must pass with no regression; raw count drift is acceptable only if explained by a
fresh, reviewed baseline change, otherwise stop.

The focused suites must exercise the accepted adversarial matrix rather than relying on
a manually mutated production-like workspace:

- actor mismatch and cross-workspace/cross-task receipt rejection;
- missing/unreadable harness and failed/pending forge evidence;
- before/after fingerprint drift and fail-before-write behavior;
- receipt expiry and malformed expiry;
- claim/apply/consume ordering;
- replay and callback-loss idempotency;
- drift under prior claimed/applied states, including
  `before_fingerprint_mismatch` without canonical closeout;
- repair-only reason enforcement; and
- atomic `task.done + completion.consumed` terminal behavior.

No real DB, daemon, delivery, SSH, or multi-host command is part of S3-C2 validation.

### 6. Worker return and independent result review

The worker returns:

- base, source, integrated, and parent SHAs;
- source and integrated stable patch IDs;
- exact changed paths and diff stat;
- focused/full test commands, counts, durations, and exit status;
- checklist validation result;
- absence of out-of-scope changes and all remaining risks;
- one provider JSONL/session handle when available; and
- exactly one parseable `[agent-report]` result block.

Codex independently inspects the commit/diff and reruns proportionate structural,
focused, full-suite, and adversarial checks. Reviewer approval accepts only the isolated
integration branch. Advancing Coordinate `main` remains a later explicit human gate.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| `main`, source SHA, merge base, patch ID, or relevant changed paths drift before bootstrap | Invalidate approval, revise/re-register the plan, and repeat plan review. |
| Worktree/branch already exists or has an active foreign lease | Stop; do not reuse or take over another session. |
| Cherry-pick conflicts, becomes empty, or a hook changes/fails the result | Stop `blocked`; preserve evidence and request a reviewed recovery plan. No manual resolution. |
| Integrated patch ID differs from source | Reject the result; do not repair or accept by visual similarity. |
| Changed path escapes the exact eight-file allowlist | Reject the result and inspect source/base substitution or hook behavior. |
| DDL, migration, schema version, or unexpected DB authority change appears | Reject and return to architecture review. |
| Focused/adversarial test fails | Report exact failing case and stop; do not patch in the integration session. |
| Full suite fails or count unexpectedly drops | Report failure and baseline delta; no `main` advancement. |
| Provider fails before cherry-pick | Preserve clean worktree and safely retry with another approved non-Codex worker. |
| Provider fails after cherry-pick | Inspect Git and JSONL before deciding whether to resume review or rerun from a fresh worktree. |
| Reviewer requests code changes | Do not edit the integrated branch; revise the source implementation through a separate reviewed correction package. |
| Main advancement is requested after result approval | Stop for explicit human authorization; no automatic fast-forward. |

## Acceptance matrix

| Case | Setup | Expected result | Evidence |
|---|---|---|---|
| Source identity | Resolve reviewed branch and commit | Exactly `1b86212`, merge base and stable patch ID match | Git commands and worker report |
| Conflict-free application | Fresh worktree from approved base | Single cherry-pick succeeds without manual resolution | Git status/log and commit parent |
| Patch equivalence | Compare source and integrated commits | Stable patch IDs and exact eight-file set match | `git patch-id --stable`, name-status, diff review |
| Schema compatibility | Inspect integrated DB changes | Event helpers only; no DDL/migration/version change | Diff inspection and full suite |
| Authorization/isolation | Run completion focused tests | Actor/workspace/task/gate/fingerprint/expiry boundaries fail closed | Test output |
| Retry/replay | Exercise claim/apply/consume retry cases | No duplicate terminal event and no drifted idempotent closeout | Focused tests and adversarial reviewer check |
| Failure-before-write | Drift before/after fingerprint | Canonical item remains nonterminal; expected rejection is returned | Focused tests |
| Repair compatibility | Invoke service/CLI tests without receipt | Normal path rejects; repair path requires and records non-empty reason | Transition/CLI tests |
| Full compatibility | Run full repository suite | All tests pass with explained count | Full-suite output |
| Scope | Inspect worktree and commit | No changes outside eight files; `.qoder/` untouched | Status and changed-path evidence |
| Authority boundary | Inspect actions/events | No `main`, remote, runtime, deployment, DB, or delivery mutation | Git/process/event evidence |

## Validation gates

- **Before coding-worker bootstrap:** exact approved plan hash, fresh Git/drift/apply-check,
  clean/isolated worktree target, no active lease.
- **Before worker closeout request:** successful cherry-pick, patch/path/schema
  equivalence, focused/full tests, checklist validation, JSONL/session handle.
- **Before result approval:** independent Codex diff review and rerun of proportionate
  checks; worker report alone is insufficient.
- **Before Coordinate `main` advancement:** explicit human authorization after result
  approval; update must be a reviewed fast-forward or an equally reviewed method.
- **Before deployment/multi-host smoke:** separate S3-C3 detailed plan, independent plan
  review, host-aware preflight, and explicit runtime/deploy authority.

## Rollout and rollback

- Landing order: plan approval -> fresh worktree -> non-Codex worker cherry-pick ->
  worker validation -> Codex result review -> human decision on local `main` advancement.
- No schema migration, package migration, protocol redesign, or service restart occurs.
- Before `main` advancement, rollback is deletion of the isolated branch/worktree only
  after preserving required review evidence and receiving Operator authorization.
- After a later approved fast-forward, rollback must use a separately reviewed revert;
  never reset shared history.
- Stop immediately on relevant drift, conflict, patch mismatch, unexpected paths, test
  failure, authority ambiguity, or any production/runtime request.

## Worker boundaries

- Allowed worktree: fresh Operator-created isolated Coordinate worktree only.
- Allowed branch: `agents/<worker>/slice-3-c2-local-integration`, based on the exact
  pre-bootstrap `main` SHA.
- Allowed source change: the automatic cherry-pick of `1b86212` only.
- Allowed commands: read-only Git inspection, the single cherry-pick, repository tests,
  checklist validation, and non-mutating diagnostics within the worktree.
- Forbidden: manual edits, conflict resolution, additional commits, amend/rebase/squash,
  `main` mutation, push/PR/merge, deploy, service/process control, real DB/SSH/coord-ssh,
  real delivery, direct harness JSON edits, lifecycle closeout, mark-done, and
  self-approval.
- Progress reporting must include current phase and operational evidence without private
  reasoning, prompts, tokens, or sensitive command arguments.
- Final report must include all identity/equivalence/test evidence listed above.

## Plan review record

- Review artifact:
  `docs/project-harness/tasks/slice-3-c2-local-integration/plan-review-round-1.md`
- Reviewer: pending independent review
- Verdict: pending
- Reviewed plan revision: pending latest `plan.ready` event/hash
- Must-fix findings: pending
- Resolution revision: pending

Any material edit after approval creates a new `plan.ready`, invalidates the old
approval and reviewer bootstrap, and requires a new plan-review round.

## Bootstrap gate

Before approval, generate only a `review-type=plan` reviewer bootstrap. Do not create a
coding-worker worktree, branch, bootstrap, or assignment. After approval, re-run the
operator pre-bootstrap refresh; relevant drift requires a new plan revision and review.
