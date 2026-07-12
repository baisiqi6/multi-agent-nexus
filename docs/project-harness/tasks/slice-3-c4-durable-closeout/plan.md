# Detailed Execution Plan: slice-3-c4-durable-closeout

> **Status:** in_review
>
> This is an executable documentation and lifecycle-closeout package. It does not
> authorize a worker bootstrap, checklist transition, sidecar cleanup, runtime repair,
> deployment, or Phase 9 implementation until an independent reviewer approves this
> exact plan revision.

## Identity and revision

- Parent stage: `slice-3-completion-closeout` / `S3-C4`
- Package id: `slice-3-c4-durable-closeout`
- Plan author / architect: Codex
- Intended plan reviewer: independent non-Codex read-only reviewer, distinct from the
  closeout worker
- Intended worker: unassigned until plan approval; prefer Oh-My-Pi, OpenCode, or Claude
  Code in the isolated MultiNexus worktree
- Intended code/result reviewer: Codex
- Plan path:
  `docs/project-harness/tasks/slice-3-c4-durable-closeout/plan.md`
- Plan revision authority: latest Coordinate `plan.ready` event and its
  `plan_content_hash`
- Supersedes: none; the roadmap overview at
  `tasks/slice-3-completion-closeout/plan.md` remains the stage boundary

## Refreshed preflight

Snapshot refreshed on 2026-07-12:

- MultiNexus canonical repository: `/Users/yinxin/projects/multinexus`
- MultiNexus base branch: `main`
- Base SHA for this isolated plan worktree:
  `61813b9` (`docs: preserve S3-C3 deployment and receipt evidence`)
- MultiNexus upstream remains at `82c5613`; local commits after it are documentation
  evidence and have not been pushed or deployed.
- Isolated worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-s3-c4-closeout`
- Isolated branch: `agents/mac-omp/slice-3-c4-durable-closeout`
- Coordinate `main` and `origin/main`:
  `e0cc1561cd20b0f22389234aefe92d01273860e4`; unrelated `.qoder/` is untracked
  and must remain untouched.
- Deployed runtime verified during S3-C3 result review:
  - Coordinate `e0cc1561cd20b0f22389234aefe92d01273860e4`;
  - MultiNexus `82c5613f9d8fcb25c5ca936a24c61536e567df50`;
  - services active with `NRestarts=0`, proxy probes HTTP 200, DB integrity `ok`,
    and fresh-window `server smoke OK`.
- S3-C3 approved plan SHA-256:
  `871664176c514bec7b9c32c8045d5368ff382e35d44ccff4eefc2b3d54e64ecb`.
- Final S3-C3 attempt-2 authorization pair:
  `plan.ready=ccdd2948-5f3d-4b16-b089-c4de7caac054`,
  `plan.approved=fb247f22-417f-47ad-babb-87589ee5ed66`.
- S3-C3 result review round 2: `approve`; runtime and all five receipt cases accepted.
- Retained sidecar:
  `s3c3-smoke-20260712T062036Z-e0cc1561`, with 6 namespaced tasks and 89 events.
- Canonical `discord-nexus` remained unchanged during smoke at 29 tasks and 851 events.
- Current harness validation passes with six pre-existing warnings. Doctor reports the
  known missing `current/task_plan.md`, historical `round-2-hardening/plan.md`, and
  optional `init.sh`; none is introduced by S3-C4.
- Current Slice 3 checklist facts remain deliberately incomplete: the umbrella and
  S3-C3 are not durably closed, and S3-C4 does not yet exist as a checklist item.

All Git, deployment, service, DB-integrity, plan-event, checklist, and result-review
facts must be refreshed before final Operator closeout. Drift in runtime code identity,
canonical harness counts, plan bytes, or reviewer verdict returns this package to review.

## Problem and evidence

Slice 3 now has separately attributable code-review, local-integration, deployment,
control-plane, and real multi-host receipt evidence, but the durable stage authorities do
not yet agree:

1. the overview plan and local review artifacts still stop at the pre-S3-C3 boundary;
2. `source-of-truth-audit.md` does not yet record deployed receipt evidence and accepted
   residual risks;
3. the checklist still leaves S3-C3 and the Slice 3 umbrella open;
4. no single closeout artifact binds exact deployed SHAs, plan/review identities,
   receipt matrix results, dogfood grading, and unresolved follow-up routing; and
5. the retained sidecar and stale interrupted-recovery projection could be silently
   cleaned or misreported unless closeout states their evidentiary role explicitly.

The missing work is durable reconciliation of evidence and lifecycle, not new receipt
code. Closing Slice 3 without this package would either lose provenance or overstate the
meaning of the passing smoke.

## Goal

In one bounded worker session, produce the durable Slice 3 closeout artifacts and update
the stage-level documentation so local, deployed, multi-host, dogfood, and residual-risk
facts agree. After independent result review, the Codex Operator—not the worker—uses the
public Coordinate assignment lifecycle to close S3-C3, S3-C4, and the Slice 3 umbrella
without deleting retained evidence or beginning Phase 9/Slice 4 implementation.

## Non-goals

- No Coordinate or MultiNexus runtime-code change.
- No `cli.py`, `policy.py`, `transitions.py`, completion-receipt, schema, migration,
  deployment-script, proxy, daemon, bridge, or harness-tool implementation.
- No sidecar deletion, direct DB edit, receipt repair, task-projection repair, or manual
  reconciliation intended to conceal the observed stale projection.
- No rewrite of historical S3-C1/S3-C2/S3-C3 plan or review artifacts.
- No push, deploy, service restart, production mutation, real Discord/KOOK delivery, or
  new multi-host smoke from the closeout worker.
- No Phase 9 0A or Slice 4 implementation. S3-C4 may only route accepted residual risks
  to their already named later packages.
- No direct edit of `mvp-checklist.json`, `events.jsonl`, or generated
  `harness-state.json`; lifecycle changes go through Coordinate/harness services.
- The worker may not approve its own result or run package/stage `mark-done`.

## Invariants and authority boundaries

- Git owns repository and commit identity; deployed `VERSION_DEPLOYED` files own the
  active release-copy identity.
- Coordinate SQLite events own plan approval, assignment, review, and terminal receipt
  facts. Harness files own durable project status and documentation.
- S3-C3 plan/result artifacts are immutable historical evidence. S3-C4 links and
  summarizes them rather than rewriting their verdicts.
- `source-of-truth-audit.md` owns the durable cross-repository authority conclusion.
- The new `closeout.md` owns the Slice 3 roll-up verdict and evidence index. It must
  preserve separate local-code, local-integration, control-plane, worker-execution,
  dogfood, and durable-closeout verdicts.
- Receipt event success does not imply the task projection is current. The stale
  interrupted-recovery projection remains an explicit unresolved Slice 4 risk.
- Full dogfood, semi-dogfood, and direct operational fallback remain distinct grades.
  Direct OMP worker dispatch must not be labeled full dogfood.
- The retained sidecar is evidence. Cleanup requires a later separately reviewed and
  explicitly authorized operation.
- Provider JSONL proves activity, not correctness. Codex independently reviews the diff,
  runtime facts, harness transitions, and final status.
- Secrets, proxy node contents, raw prompts, private reasoning, tokens, private-key
  paths, and unredacted DB rows must not enter repository artifacts.

## Proposed changes

### 1. Worker documentation scope

The worker may modify only these files in the isolated MultiNexus worktree:

1. `docs/project-harness/tasks/slice-3-completion-closeout/closeout.md` (new)
   - Bind exact S3-C1 through S3-C4 evidence paths and verdicts.
   - Record Coordinate/MultiNexus integrated, upstream, and deployed SHAs without
     conflating documentation-only commits with runtime releases.
   - Record the S3-C3 plan hash/event pair, worker session/JSONL handle, five-case
     receipt matrix, canonical zero-drift audit, retained sidecar, and result-review
     approval.
   - Record accepted residual risks and their destinations.
2. `docs/project-harness/source-of-truth-audit.md`
   - Update only the Slice 3 remediation/result boundary from locally accepted to
     deployed and real-boundary verified.
   - Preserve unresolved projection, deploy atomicity, CLI ergonomics, and full-dogfood
     gaps as later work; do not mark Slice 4 or Phase 9 complete.
3. `docs/project-harness/tasks/slice-3-completion-closeout/plan.md`
   - Append the executed S3-C3/S3-C4 status and exact closeout evidence pointer without
     rewriting the roadmap-level work-package contract.
4. `docs/project-harness/roadmap.md`
   - Add a current status note that Slice 3 has evidence sufficient for S3-C4 review;
     after Operator lifecycle closeout, record Slice 3 closed and make Phase 9 0A
     planning/execution order explicit according to the already approved architecture
     alignment. Preserve the original 2026-07-11 snapshot as historical.
5. `docs/project-harness/progress.md`
   - Append an attributable S3-C4 worker summary with exact artifacts, validation, and
     residual risks. Do not claim lifecycle closure before the Operator performs it.
6. `docs/project-harness/dogfood-feedback.md`
   - Ensure S3-C3/S3-C4 dogfood grading and backlog routing are complete; add only
     missing closeout-level findings and avoid duplicating the existing attempt reports.

The worker must not edit `mvp-checklist.json`; the Operator performs public lifecycle
transitions after result approval.

### 2. Worker validation and return

The worker verifies:

- all cited paths exist and all exact SHA/event/session/receipt claims match durable
  source artifacts;
- `git diff --name-only` is limited to the six allowed paths;
- `git diff --check` passes;
- `jq empty docs/project-harness/mvp-checklist.json` passes;
- `scripts/harness/harnessctl validate` passes with no new warnings;
- `scripts/harness/harnessctl doctor` introduces no new MISS/invalid finding;
- terminology searches do not conflate local, deployed, multi-host, or full-dogfood
  verdicts; and
- no secret/config content is copied.

The worker commits its bounded documentation result on the isolated branch, returns the
commit SHA, exact changed paths, validation outputs, residual risks, and provider
session/JSONL handle, then stops before closeout lifecycle mutation.

### 3. Independent Codex result review

Codex independently:

- inspects the worker commit and exact diff against the approved plan;
- rechecks every cited Git/event/report identity and the S3-C3 receipt counts;
- performs a bounded read-only runtime refresh of deployed versions, service restart
  counts, proxy probes, DB integrity, and fresh-window server smoke;
- confirms canonical `discord-nexus` task/event counts did not change unexpectedly;
- reruns harness validation/doctor and documentation consistency checks; and
- issues `approve`, `changes_requested`, or `blocked` in a result-review artifact.

### 4. Operator-only lifecycle closeout after approval

Only after Codex result approval, the Operator uses public Coordinate assignment
commands and their receipt-aware `mark-done` path, in dependency order:

1. finish S3-C3 with closeout evidence bound to result-review round 2;
2. finish `slice-3-c4-durable-closeout` with the approved worker commit and S3-C4 result
   review;
3. finish the umbrella `slice-3-completion-closeout` with the exact child-package
   evidence index;
4. reconcile/read state through supported commands and verify all three terminal events,
   checklist `done/closed` state, no unexpected pending Operator action, and no canonical
   task outside these IDs changed; and
5. append the final Operator closeout record and checkpoint the lifecycle-generated
   harness artifacts.

If the ordinary public lifecycle cannot represent the already executed S3-C3 state,
stop and record the exact gap. Do not directly edit JSON/SQLite or use a repair path merely
to force a green closeout.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Any cited SHA/event/report no longer exists or contradicts the closeout claim | Stop and return `blocked`; do not substitute chat memory. |
| Worker diff touches runtime code, checklist JSON, generated event/state files, or historical evidence | Revert only the worker's out-of-scope edits and return `changes_requested`. |
| Runtime refresh differs from approved deployed SHAs or services/proxy/DB/smoke are unhealthy | Stop before lifecycle closeout and reopen S3-C3 evidence review. |
| Canonical `discord-nexus` counts drift unexpectedly | Preserve evidence and stop; do not repair during S3-C4. |
| Harness warnings/MISS items increase | Treat as a regression and correct only the S3-C4 documentation cause. |
| Public lifecycle rejects closeout because prior state is missing or stale | Record the exact command/output and route a coordinator lifecycle gap; no direct JSON/DB repair. |
| Mark-done receipt expires or is interrupted | Inspect receipt/events/files and use only the reviewed idempotent recovery path; never mint a substitute receipt without determining prior state. |
| Provider fails before edits | Retry with another approved non-Codex executor after confirming a clean worktree. |
| Provider fails after edits | Inspect JSONL/process/diff, preserve partial work, and resume only after bounded review. |
| Secret or raw private reasoning appears in a draft | Remove it before commit and record the redaction; never copy it into review artifacts. |

## Acceptance matrix

| Case | Setup | Expected result | Evidence |
|---|---|---|---|
| Evidence identity | Compare Git, S3-C3 plans/reports/reviews, Coordinate events | Every SHA/hash/event/session is exact and attributable | `closeout.md`, reviewer queries |
| Verdict separation | Review local, deployed, multi-host, dogfood, closeout wording | No evidence level is promoted beyond what it proves | Diff and terminology audit |
| Receipt roll-up | Recount sidecar events and negative cases | Five planned cases pass; one terminal pair where required; none where forbidden | S3-C3 report plus independent event counts |
| Canonical isolation | Compare canonical counts before/after | No unrelated canonical task/event/file changes | read-only DB/harness audit |
| Residual risks | Compare S3-C3 reports and dogfood feedback | Projection, deploy atomicity, CLI ergonomics, host-profile gaps remain routed and open | closeout/audit/dogfood sections |
| Worker scope | Inspect commit | Only six allowed documentation paths change | `git diff --name-only` |
| Harness compatibility | Run validation/doctor | Validation passes with same six warnings; no new doctor finding | command output |
| Lifecycle closeout | Execute public lifecycle after result approval | S3-C3, S3-C4, umbrella become done/closed with attributable review/terminal events | Coordinate events + checklist/state |
| Evidence retention | Inspect sidecar and reports | Sidecar and historical reports remain intact | paths/DB rows exist |
| Privacy | Inspect diff and reports | No proxy config, token, key, raw prompt, or private reasoning is committed | reviewer inspection |

## Validation

Worker self-test:

```bash
git status --short
git diff --check
jq empty docs/project-harness/mvp-checklist.json
scripts/harness/harnessctl validate
scripts/harness/harnessctl doctor
git diff --name-only 61813b9...HEAD
```

Codex result review additionally refreshes:

- exact local/upstream/deployed SHAs;
- two service observations and `NRestarts`;
- Discord/PyPI proxy probes and production DB integrity;
- `server-smoke.sh --host kook-hermes-admin --since '<bounded fresh window>'`;
- S3-C3/sidecar/canonical event counts and terminal-pair invariants; and
- final lifecycle events/checklist/state after closeout.

No full Coordinate/MultiNexus unit-test rerun is required for a documentation-only
worker diff. If any runtime code changes, the package violates scope and returns to plan
review instead of expanding validation ad hoc.

## Rollout and rollback

- Landing order: approved S3-C4 plan -> worker documentation commit -> Codex result
  review -> public S3-C3 closeout -> public S3-C4 closeout -> public umbrella closeout ->
  harness checkpoint -> Phase 9 0A detailed package planning.
- No schema migration or runtime deployment belongs to S3-C4.
- Documentation rollback is a revert of the isolated worker commit before integration.
- Lifecycle events are append-only and are not deleted. A failed closeout is corrected by
  a later attributable event through supported commands, not history rewriting.
- Sidecar cleanup remains deferred and separately reviewed.
- Stop on runtime identity drift, canonical drift, missing receipt/review evidence,
  lifecycle rejection, new validation warnings, or out-of-scope worker changes.

## Worker boundaries

- Allowed worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-s3-c4-closeout`
- Allowed branch: `agents/mac-omp/slice-3-c4-durable-closeout`
- Allowed files: exactly the six documentation paths listed under Proposed changes.
- Allowed commands: read-only Git, file reads/searches, bounded edits to allowed files,
  validation/doctor, and one local documentation commit.
- Forbidden: direct checklist/event/state JSON edits; Coordinate lifecycle mutation;
  SSH, deploy, restart, DB mutation/read, receipt operations, push, merge, sidecar cleanup,
  Phase 9/Slice 4 implementation, or package/stage mark-done.
- Required reporting: changed files, exact evidence identities, commands/results,
  remaining risks, commit SHA, and provider-native session/JSONL handle.

## Plan review record

- Review artifact:
  `docs/project-harness/tasks/slice-3-c4-durable-closeout/plan-review-round-1.md`
- Reviewer: pending
- Verdict: pending
- Reviewed plan revision: pending Coordinate `plan.ready` hash/event
- Must-fix findings: pending
- Resolution revision: pending

Any material edit after `approved` creates a new `plan.ready`, invalidates the previous
review/bootstrap, and requires a fresh independent review.

## Bootstrap gate

After approval, generate
`docs/project-harness/tasks/slice-3-c4-durable-closeout/worker-bootstrap.md` through
Coordinate. Add a task-scoped supplement only if the generated bootstrap loses this
plan's exact allowed paths, evidence identities, dogfood classification, or lifecycle
boundary. Before handoff, verify the plan hash, review artifact, branch, worktree, and
bootstrap references still match.
