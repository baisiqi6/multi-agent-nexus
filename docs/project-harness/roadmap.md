# Coordinate + MultiNexus Roadmap

> **Status: canonical roadmap-level plan.**
>
> This file defines sequencing, boundaries, dependencies, and gates. It does not
> authorize implementation. Every executable work package requires its own
> detailed plan, independent plan review, approved plan evidence, and only then a
> worker bootstrap.

## Planning snapshot

Planning snapshot recorded on 2026-07-11:

- MultiNexus `main`: `4e2fa4671aeb0985739d9ef2d16df5bae9b36a77`.
- Coordinate `main`: `46a75dab8de77d147ceff817241cfc49a495e4ca`.
- Coordinate Slice 3 worker branch
  `agents/mac-claude/slice-3-completion-receipt`:
  `1b862129897be001e5a9078b7b4fad48d90d89c2`.
- Slice 3 code correctness has reviewer approval for a local checkpoint. Durable
  audit update, integration, deployment, and real multi-host smoke remain separate
  gates.

Every detailed plan must refresh these facts. This snapshot is historical evidence,
not permission to reuse stale branches, paths, services, or runtime state.

## Current status (2026-07-12)

Slice 3 now has separately attributable code-review, local-integration, control-plane,
worker-execution (real five-case receipt matrix), and dogfood evidence sufficient for
S3-C4 durable closeout review:

- S3-C1 and S3-C2 are durably closed locally (done/closed, reviewer-approved).
- S3-C3 deployed the exact approved SHAs (Coordinate `e0cc1561`, MultiNexus `82c5613`)
  and passed the real isolated-boundary receipt smoke; independent result review round 2
  approved. The checklist still records S3-C3 `todo`/`review.decision=null`; the Operator
  performs public `mark-done` after result review.
- S3-C4 documentation is ready for Operator closeout; the worker does not mark itself done.

The umbrella `slice-3-completion-closeout` and S3-C3/S3-C4 lifecycle are closed only by
the Operator through public Coordinate assignment commands in dependency order, after
independent result review. The retained smoke sidecar and all accepted residual risks
(stale interrupted-recovery projection, deploy non-atomicity, smoke-window false positive,
CLI ergonomics, missing workspace delete, missing full-dogfood host profile) remain
routed to their named later packages; see
[tasks/slice-3-completion-closeout/closeout.md](tasks/slice-3-completion-closeout/closeout.md).

After the Operator durably closes Slice 3, the active architecture alignment governs:

1. **Slice 3 durable closeout** (Operator-only lifecycle closeout after result review).
2. **P9-0A bounded structural decoupling** (beginning with
   `p9-0a1-cli-boundary-extraction`) **before** Slice 4 implementation, so Slice 4
   CLI/projection changes land in the extracted modules instead of enlarging the
   monolithic CLI again.
3. **Slice 4 projection/split-operation hardening** after P9-0A.
4. **Phase 9 runtime isolation packages (P9-1+)** after Slice 4 acceptance.

The existing `p9-0a1-cli-boundary-extraction` detailed plan, review, and bootstrap were
drafted under the older gate that placed worker execution after Slice 4 acceptance. That
ordering is now superseded by the split above. Those plan bytes, the review verdict, and
the generated bootstrap must be refreshed against the current ordering and independently
re-reviewed before any worker bootstrap; the prior approval must not be silently reused as
authorization for execution under the new sequence.

## Authority hierarchy

1. `product-definition.md` owns the shared product position and role boundaries.
2. This roadmap owns cross-stage order, dependencies, and phase boundaries.
3. `tasks/<stage-id>/plan.md` owns the roadmap-level goal, scope, and work-package
   decomposition for one stage.
4. `tasks/<package-id>/plan.md` owns the executable plan for one bounded
   implementation or validation package. Every package is a separate checklist item;
   stage overview plans reference package IDs instead of nesting another task model.
5. Review artifacts, bootstraps, implementation diffs, test results, and closeout
   packets are evidence; they do not redefine an approved plan.
6. `mvp-checklist.json` stores coarse status and artifact pointers. It must not copy
   detailed plan prose.
7. `harness-state.json` is derived and must not be hand-edited.

The temporary planning files under the Codex session workspace are tactical history,
not a second cross-repository roadmap.

## Mandatory plan gate

Every executable work package follows this order:

```text
roadmap boundary
  -> detailed plan draft
  -> independent plan review
  -> changes_requested loop, if needed
  -> explicit approved verdict bound to the reviewed plan revision
  -> worker bootstrap generated from that approved revision
  -> worker assignment
  -> implementation and self-test
  -> independent code/result review
  -> local checkpoint
  -> integration/runtime gates explicitly authorized for that package
  -> durable closeout
```

Rules:

- A roadmap-level plan is never sufficient for worker handoff.
- The plan reviewer must not be the intended coding worker. Prefer a different
  executor from the plan author when practical; the Operator retains the final gate.
- Review must produce an artifact with `approved`, `changes_requested`, or `blocked`.
- Approval evidence records the plan path plus a stable revision identifier such as
  Git commit or SHA-256. A material plan edit invalidates the approval.
- Bootstrap generation happens only after approval. It must cite the approved plan,
  review artifact, revision identifier, repository/worktree/branch, permissions,
  non-goals, validation commands, reporting format, and stop conditions.
- Worker completion is not closeout. Code/result review, integration, deployment,
  runtime smoke, and durable closeout remain separate when applicable.
- Worker, plan reviewer, code reviewer, and Operator decisions must remain
  attributable even when one executor internally uses subagents or agent teams.

Detailed plans use
[`templates/detailed-execution-plan.md`](templates/detailed-execution-plan.md).

## Dependency order

```text
Slice 3 durable closeout
        |
        v
P9-0A bounded structural decoupling
(beginning with p9-0a1-cli-boundary-extraction)
        |
        v
Slice 4 projection and split-operation hardening
        |
        v
Phase 9 runtime isolation (P9-1+)
```

P9-0A structural decoupling precedes Slice 4 so that Slice 4 CLI/projection changes land
in the extracted modules rather than re-enlarging the monolithic CLI. Phase 9 runtime
isolation (P9-1+) follows Slice 4 acceptance and must not bypass the Slice 4 authority,
registry, and partial-operation foundations.

## Stage map

### 1. Slice 3 completion authorization closeout

Canonical overview:
`tasks/slice-3-completion-closeout/plan.md`.

Outcome: integrate and validate the completion authorization receipt without
conflating local code approval, deployment, multi-host smoke, and durable closeout.
Status (2026-07-12): evidence sufficient for S3-C4 review; durable roll-up at
`tasks/slice-3-completion-closeout/closeout.md`. Operator-only lifecycle closeout pending.

### 2. Slice 4 projection and split-operation hardening

Canonical overview:
`tasks/slice-4-projection-hardening/plan.md`.

Outcome: remove stale authorization projections and ambiguous partial operations
before increasing execution concurrency.

### 3. Phase 9 multi-project execution isolation

Canonical overview:
`tasks/phase-9-execution-isolation/plan.md`.

Outcome: safely run multiple projects, task lines, providers, and executor instances
without session, worktree, queue, log, authority, or result contamination.

## Scheduling model

Scheduling is dependency- and gate-based, not a promise of calendar dates:

| Stage | Expected planning/review windows | Expected execution/validation windows |
|---|---:|---:|
| Slice 3 closeout | 1 | 1-2 plus an explicitly authorized runtime window |
| Slice 4 | 1 per work package | 3-5 across four packages |
| Phase 9 architecture | 1-2 | none until the contract is approved |
| Phase 9 implementation and dogfood | 1 per work package | 5-8 across foundation and dogfood packages |

Provider availability, multi-host access, human gates, and review corrections can
change elapsed time without changing dependency order.

## Global acceptance

The roadmap is complete only when:

- every stage has a durable closeout record and no unresolved high-priority drift;
- Coordinate and MultiNexus still preserve their documented responsibility boundary;
- multiple project lines can run with evidence-backed isolation and recovery;
- provider-native capabilities remain composable behind a managed executor boundary;
- no visible transcript, provider session, task mirror, or generated state file has
  silently become a competing source of truth.
