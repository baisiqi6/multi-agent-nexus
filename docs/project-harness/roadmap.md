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
Slice 4 projection and split-operation hardening
        |
        v
Phase 9 multi-project execution isolation
```

Phase 9 architecture exploration may begin while Slice 4 is being implemented, but
Phase 9 runtime implementation must not bypass the Slice 4 authority, registry, and
partial-operation foundations.

## Stage map

### 1. Slice 3 completion authorization closeout

Canonical overview:
`tasks/slice-3-completion-closeout/plan.md`.

Outcome: integrate and validate the completion authorization receipt without
conflating local code approval, deployment, multi-host smoke, and durable closeout.

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
