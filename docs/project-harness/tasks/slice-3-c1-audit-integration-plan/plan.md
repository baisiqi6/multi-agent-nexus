# Detailed Execution Plan: slice-3-c1-audit-integration-plan

> **Status:** in_review
>
> This is an executable documentation work-package plan. It does not authorize
> Coordinate branch integration, deployment, service restart, remote smoke, or a
> coding-worker handoff until an independent plan reviewer approves the current
> `plan.ready` revision.

## Identity and revision

- Parent stage: `slice-3-completion-closeout`
- Package id: `slice-3-c1-audit-integration-plan`
- Plan author / architect: Codex
- Intended plan reviewer: Claude Code Sonnet, read-only plan review
- Intended coding worker: unassigned until plan approval
- Intended code/result reviewer: Codex
- Plan path: `docs/project-harness/tasks/slice-3-c1-audit-integration-plan/plan.md`
- Plan revision authority: latest Coordinate `plan.ready` event and its
  `plan_content_hash`; the review artifact must record both
- Supersedes: none

## Refreshed preflight

Snapshot refreshed on 2026-07-12:

- MultiNexus repository: `/Users/yinxin/projects/multinexus`
- MultiNexus `main`: `bfc902fc6acf421f2a5884ec4367ca2a7414b80c`
  before this detailed-plan draft; branch was clean and two commits ahead of
  `origin/main`.
- Coordinate repository: `/Users/yinxin/projects/coordinate`
- Coordinate `main`: `46a75dab8de77d147ceff817241cfc49a495e4ca`,
  two commits ahead of `origin/main`; unrelated `.qoder/` remains untracked and
  must not be added.
- Slice 3 source worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-slice3-claude`
- Slice 3 source branch: `agents/mac-claude/slice-3-completion-receipt`
- Slice 3 source commit: `1b862129897be001e5a9078b7b4fad48d90d89c2`
- Common ancestor of Coordinate `main` and Slice 3 source:
  `a2ad92d2bf13ec894979c082897a713f3870d130`.
- Stable patch ID for the Slice 3 source commit:
  `eb204296bd6a09e4caccabfe4bb05802e7ef7b37`.
- Coordinate `main` changes after the common ancestor affect only two
  `skills/coordinate-operator/` files; Slice 3 changes affect eight
  completion/CLI/DB/transition/runbook/test files. There is no changed-path overlap
  in the refreshed snapshot, but S3-C2 must still inspect the actual cherry-pick
  result instead of treating this observation as a future guarantee.
- Local Coordinate workspace id for the MultiNexus harness is the compatibility
  id `discord-nexus`, not `multinexus`.
- Local reviewer CLI: Claude Code `2.1.197`.
- Production server SHA, deployed schema, live daemon state, and real `coord-ssh`
  path were not inspected for this documentation-only package.

Accepted local evidence to preserve, not re-label:

- Slice 3 reviewer verdict: approve for local checkpoint only.
- Full local suite: `1347 passed, 58 subtests passed`.
- Focus counts: transitions 131, CLI 169, completion 42.
- `git diff --check` and Coordinate checklist validation passed.
- Final adversarial retry returned `before_fingerprint_mismatch` and left the
  canonical item `doing/blocked`.
- Local review source:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/outputs/slice3-review-report.md`.
- Claude worker session handle:
  `631e2d45-e9dc-4304-aa95-2aeeab515714`; raw JSONL is operational evidence and
  must not be copied wholesale into the repository.

## Problem and evidence

The durable cross-repository audit still presents Slice 3 only as a proposed
three-step remediation. It does not record the accepted local implementation,
the three adversarial correction rounds, the checkpoint commit, or the explicit
boundary that deployment and multi-host behavior remain unverified.

The full local reviewer report currently lives in a Codex session workspace rather
than the active project harness. The next integration method is also only present in
conversation and temporary progress files. A later session could therefore either
repeat completed review work or overstate local acceptance as deployed completion.

## Goal

In one documentation-only worker session, create durable and reviewable evidence for
the accepted Slice 3 local checkpoint, update the source-of-truth audit to its exact
current boundary, and record an integration decision that S3-C2 can turn into a
separately reviewed execution plan.

## Non-goals

- Do not cherry-pick, merge, rebase, push, or otherwise integrate `1b86212`.
- Do not edit Coordinate source, tests, schema, CLI, or current `main`.
- Do not deploy, restart services, access production DB state, or run real
  `coord-ssh` smoke.
- Do not implement Slice 4 or Phase 9.
- Do not redesign or simplify `completion.py`; its maintainability notes remain
  follow-up evidence, not S3-C1 scope.
- Do not mark the Slice 3 umbrella or S3-C1 package done. Lifecycle transitions
  remain Operator actions after code/result review.

## Invariants and authority boundaries

- `source-of-truth-audit.md` owns the durable cross-repository authority finding
  and remediation status.
- The new local code-review artifact owns the durable summary of reviewer evidence;
  it references but does not duplicate raw provider JSONL.
- The new integration-decision artifact owns the proposed S3-C2 method and its
  preconditions. It does not assert that integration occurred.
- Coordinate job/events remain runtime authority. This package must not write or
  fabricate runtime completion events.
- Harness checklist status is mutated only through Coordinate/harness services by
  the Operator. The worker must not edit `mvp-checklist.json` directly.
- Git owns branch and commit facts. Every SHA and patch ID included in a durable
  artifact must be rechecked from the repositories during the worker session.
- Local code acceptance, local integration, deployment, multi-host smoke, and
  durable closeout remain separate verdicts.
- Secrets, raw prompts, private reasoning, tokens, and sensitive JSONL arguments
  must not enter durable artifacts.

## Proposed changes

The worker may modify or create only these files in an isolated MultiNexus worktree:

1. `docs/project-harness/source-of-truth-audit.md`
   - Change Slice 3 from proposal-only wording to an evidence-backed status:
     local code accepted and checkpointed, not integrated/deployed/smoked.
   - Add concise acceptance criteria and evidence for the receipt lifecycle,
     authorization binding, expiry/replay/fingerprint behavior, repair-only paths,
     correction rounds, test results, and residual limitations.
   - Preserve Slice 4 ordering and avoid claiming its findings are resolved.
2. `docs/project-harness/tasks/slice-3-completion-closeout/local-code-review.md`
   - Record source/baseline/checkpoint SHAs, reviewed file set, accepted protocol,
     adversarial rounds, independent verification, reviewer verdict, and remaining
     deployment boundary.
   - Reference the provider session ID and local review source path without copying
     private chain-of-thought or raw JSONL bodies.
3. `docs/project-harness/tasks/slice-3-completion-closeout/integration-decision.md`
   - Propose that S3-C2 create a fresh isolated Coordinate integration branch from
     the then-current `main` and apply the single reviewed Slice 3 commit through a
     controlled cherry-pick.
   - Record that the refreshed snapshot has no changed-path overlap, while still
     requiring inspection of the actual cherry-pick and resulting diff.
   - Require source and integrated stable patch IDs, changed-file equivalence,
     focused/full tests, schema compatibility, harness validation, and adversarial
     probes before local integration acceptance.
   - State that S3-C2 must refresh all SHAs and receive its own plan review; this
     document does not authorize the cherry-pick.

The worker must not update `progress.md`, checklist lifecycle, roadmap status, or
generated `harness-state.json`; the Operator records those after result review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| A recorded SHA/path no longer exists | Stop and report `blocked`; do not substitute a remembered SHA. |
| Current branches moved after this snapshot | Refresh facts and report the drift; do not silently rewrite the integration decision beyond this package. |
| Reviewer evidence conflicts with Git/tests | Treat the durable artifact as unverified and report `changes_requested`/`blocked`. |
| A later main change creates a cherry-pick conflict or semantic overlap | Stop S3-C2 integration, record the exact conflict, and return for a revised plan. |
| Audit update would imply deployed success | Rewrite the wording to preserve local/integration/deployment boundaries. |
| Raw JSONL contains prompts/secrets/private reasoning | Extract only bounded operational facts and redact sensitive data. |
| Worker accidentally changes runtime code or checklist JSON | Revert only the worker's out-of-scope change and report the boundary violation. |
| Provider/reviewer is unavailable | Preserve the draft and stop before coding-worker bootstrap or assignment. |

## Acceptance matrix

| Case | Setup | Expected result | Evidence |
|---|---|---|---|
| Durable local verdict | Read Git commits and reviewer report | Harness records local checkpoint approval without deployed claim | `local-code-review.md` plus audit diff |
| Receipt authority | Review accepted protocol and correction rounds | Audit describes authorize/claim/apply/consume and repair-only compatibility | Exact audit section |
| Integration method | Compare `46a75da`, `1b86212`, merge base, files, patch ID | Decision recommends a bounded S3-C2 method, records current non-overlap, and still requires actual-result inspection | `integration-decision.md` |
| Source-of-truth boundary | Compare roadmap, audit, evidence artifact | No second editable product definition or duplicate lifecycle authority is created | Link and wording review |
| Privacy | Inspect durable artifacts | No raw prompt, token, private reasoning, or JSONL body is copied | Reviewer inspection |
| Scope | Inspect Git diff | Only the three allowed documentation artifacts change | `git diff --name-only` |
| Compatibility | Run harness checks | Checklist and canonical plan links remain valid | `jq`, `git diff --check`, `harnessctl validate/doctor` |

## Validation

Worker self-test requirements:

```bash
git status --short
git diff --check
jq empty docs/project-harness/mvp-checklist.json
bash scripts/harness/harnessctl validate
bash scripts/harness/harnessctl doctor
git -C /Users/yinxin/projects/coordinate cat-file -e 46a75da^{commit}
git -C /Users/yinxin/projects/coordinate cat-file -e 1b86212^{commit}
git -C /Users/yinxin/projects/coordinate merge-base 46a75da 1b86212
git -C /Users/yinxin/projects/coordinate show 1b86212 --pretty=email --patch | git patch-id --stable
```

The worker must also verify that its diff contains only the three allowed paths.
No Coordinate test suite or runtime smoke is required for this documentation-only
package; S3-C2 owns fresh implementation tests and adversarial probes.

Reviewer requirements:

- Re-check every durable claim against Git or the accepted local review artifact.
- Reject wording that conflates local PASS with integration, deployment, or E2E PASS.
- Reject an integration decision that assumes future non-overlap or fails to address
  actual-result inspection, patch identity, or the isolated worktree requirement.
- Confirm Slice 4 and Phase 9 scope did not leak into the package.

## Rollout and rollback

- Landing order: plan approval -> isolated docs worker -> result review -> local
  MultiNexus documentation checkpoint -> Operator lifecycle update.
- No schema or protocol migration.
- No deployment or host restart.
- Rollback is a local revert of the documentation checkpoint if result review later
  identifies a false durable claim.
- Stop immediately on stale/missing commit evidence, unexpected dirty files, authority
  ambiguity, or any request for production mutation.

## Worker boundaries

- Worktree/branch: to be allocated after plan approval from the current MultiNexus
  `main`; never work directly in `/Users/yinxin/projects/multinexus`.
- Allowed files: exactly the three paths listed under Proposed changes.
- Allowed commands: read-only Git inspection, text searches, JSON validation, harness
  validate/doctor, and documentation editing inside the isolated worktree.
- Forbidden: Coordinate or MultiNexus runtime code changes, direct checklist JSON edits,
  coordinator lifecycle commands, commit, push, merge, rebase, deploy, service control,
  remote DB access, real Discord/KOOK delivery, real `coord-ssh`, mark-done, and
  self-approval.
- Progress report: identify current phase and durable artifact paths without copying
  raw JSONL.
- Final report: exact changed paths, evidence refreshed, validation output, open risks,
  and one parseable result summary.
- Observation: return a Claude session ID/JSONL handle when available; JSONL is
  operational evidence, not correctness evidence.

## Plan review record

- Review artifact:
  `docs/project-harness/tasks/slice-3-c1-audit-integration-plan/plan-review-round-1.md`
- Reviewer: pending Claude Code Sonnet review
- Verdict: pending
- Reviewed plan revision: pending latest `plan.ready` event/hash
- Must-fix findings: pending
- Resolution revision: pending

Any material edit after approval creates a new `plan.ready`, invalidates the old
approval and reviewer bootstrap, and requires a new plan-review round.

## Bootstrap gate

Generate only a `review-type=plan` reviewer bootstrap before approval. Do not generate
the coding-worker bootstrap until the current plan revision has an explicit approved
review artifact and Coordinate `plan.approved` event with scope
`implementation plan`.
