# Slice 4 Projection and Split-Operation Hardening

> **Plan level: roadmap overview.** Each package below requires a separate detailed
> plan, independent plan review, and approved bootstrap before implementation.

## Goal

Remove stale authorization projections and ambiguous partial operations before the
system increases multi-project routing and concurrency.

## Dependency

Runtime implementation starts after Slice 3 local integration is accepted. Detailed
planning and read-only review may begin earlier, but must refresh the post-integration
code paths before approval.

## Work packages

### S4-A — Deterministic latest-event reads

Audit and correct the remaining timestamp-only latest-event queries, including daemon
task-status display and policy owner fallback. Use insertion order (`rowid`) as the
tie-breaker where the current SQLite event ledger is authoritative.

### S4-B — Versioned replace-sync agent registry

Declare the approved deployed roster authority; record source identity/version/hash;
make authoritative sync remove absent identities; keep manual additions as explicit,
auditable overrides with reason/expiry; define reload and reconciliation behavior.

S4-B is executed as two reviewed packages:

- **S4-B1 Coordinate registry model** — normalized authoritative roster, auditable
  overrides, version/hash rules, effective resolver, compatibility projection, and
  daemon refresh without restart. **Completed and deployed at Coordinate
  `ff6b8bf`; receipt `dca68d10-f805-4cbf-af35-1ac73a8f86d4` consumed.**
- **S4-B2 deployed authority integration** — version the deployed MultiNexus roster,
  wire authoritative sync into deployment/operations, verify live removal/reload, and
  update cross-repository runbooks. **Completed and deployed at MultiNexus `ac12396`;
  source `multinexus.discord` v1, revision 1, ten authoritative identities.**

This split prevents host-specific deployment mechanics and real ignored configuration
from being mixed into the schema/resolver transaction package.

The next Slice 4 package is **S4-C bound split operations**.

### S4-C — Bound split operations

Add stable `operation_id` and before/after fingerprints to host-aware file/record
pairs. Group purely DB-side writes transactionally. Make retry distinguish not
started, partially applied, already applied, and conflicting drift.

S4-C is executed as two reviewed packages:

- **S4-C1 task-create operation contract** — schema/ledger, canonical operation and
  checklist-item fingerprints, atomic file projection, and transactional binding for
  `task create-files/create-record`. **Completed and terminally closed.**
- **S4-C2 issue-materialize adoption** — adopt the same contract for
  `issue materialize-files/materialize-record`, include delivery creation in the DB
  transaction, and run host-aware interruption/retry dogfood. **Next package; detailed
  plan review required before worker authorization.**

`assignment mark-done-files/record` already has the stronger completion receipt,
claim/apply and before/after-fingerprint protocol. S4-C treats it as a reference and
compatibility boundary rather than replacing it with a weaker generic operation.

### S4-D — Doctor and repair evidence

Detect stale registry projections, partial operations, orphan operations, projection
version mismatch, and task-mirror drift. Doctor reports by default; repair requires an
explicit, auditable Operator action and must not invent canonical state.

## Cross-package rules

- One package per worker branch/worktree and one detailed plan per package.
- S4-B and S4-C require failure/recovery matrices and migration compatibility.
- S4-D consumes contracts established by S4-B/S4-C; it must not create a competing
  repair authority.
- Any cross-repository contract change requires Coordinate and MultiNexus tests.
- No drive-by Phase 9 scheduler, service API, or provider routing work.

## Non-goals

- Replacing SQLite or the file-backed harness.
- Rewriting Coordinate/MultiNexus boundaries.
- Automatic product-level Operator judgment.
- Multi-project capacity scheduling, worktree leases, or executor pools; those belong
  to Phase 9.

## Stage acceptance

- Latest-event reads used for decisions are deterministic.
- Removed roster identities cannot remain silently authorized.
- Every supported split operation is retryable and diagnosable after interruption.
- Doctor reports all defined drift classes with actionable evidence.
- Full and cross-repository tests pass, and the durable audit is updated.
