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

### S4-C — Bound split operations

Add stable `operation_id` and before/after fingerprints to host-aware file/record
pairs. Group purely DB-side writes transactionally. Make retry distinguish not
started, partially applied, already applied, and conflicting drift.

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
