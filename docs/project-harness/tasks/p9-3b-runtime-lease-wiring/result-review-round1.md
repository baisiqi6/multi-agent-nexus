# P9-3B Result Review — Round 1

Status: changes_requested  
Date: 2026-07-14  
Reviewer: Codex  
Coordinate worker commit: `559e202`  
MultiNexus worker commit: `78af200`

## Verdict

The worker produced substantial implementation and test coverage, but the two
commits are not safe to integrate or deploy. The following findings are
blocking against the approved P9-3B plan.

## Blocking findings

1. **P0 — Typed claim can apply one candidate's context to another job.**
   `runtime.claim_job()` selects and validates a candidate outside the write
   transaction, then `claim_leased_job()` starts from a fresh deterministic
   selection inside `BEGIN IMMEDIATE`. Resource blocking or a concurrent state
   change can make the inner selection choose a different job. The inner code
   then uses the caller-provided `ExecutionContextV1`, so job B can receive job
   A's context/worktree lease. Selection, backfill, binding/routing validation,
   job CAS, and lease reserve must operate on one row inside one transaction.

2. **P0 — Managed progress is neither lease-atomic nor event-atomic.**
   `record_job_progress()` validates the lease before `BEGIN IMMEDIATE`, commits
   the job update, then appends `job.progress` in a second transaction. Lease
   expiry can race the validation, and event failure can leave progress without
   its event. Exact lease validation, CAS, progress update, and event append
   must share one transaction and one final commit.

3. **P0 — Managed terminal validation has a validation-to-write race.**
   `report_job_result()` validates the lease before starting its transaction.
   Move exact active/unexpired lease validation into the same transaction as
   terminal CAS, release, events, review projection, and delivery.

4. **P0 — Missing or malformed leases can invoke a typed provider.**
   `AgentdWorker._process_job()` only validates `execution_lease` when it is a
   dict. `None` or another type falls through as legacy, even when an executor
   binding identifies a typed P9-3B claim. A typed/bound claim must require one
   valid lease envelope before provider invocation; malformed composite claims
   must invoke no provider.

5. **P0 — Managed recovery lacks required Operator evidence.**
   Recovery remains a boolean `recoverable` mode. The approved plan requires a
   bounded audited Operator reason and explicit confirmation that the prior
   provider process/session is stopped before reclaiming an expired managed
   attempt. Carry, validate, and persist both fields through CLI/client/claim
   and `job.claimed` evidence; ordinary agentd remains unable to auto-reclaim.

6. **P1 — Public claim diagnostics are discarded.**
   The internal selector computes `capacity_exhausted`, `resource_blocked`,
   `scan_limit_reached`, and oldest-blocked evidence, but `RuntimeClaimResult`
   exposes only `claimed=false`. Preserve the bounded machine-readable reason
   and evidence through Coordinate CLI and the MultiNexus client/operator
   surface.

7. **P1 — Invalid routing evidence is silently downgraded.**
   `claim_leased_job()` catches routing evidence errors and substitutes `{}`.
   The approved plan requires corrupt authority snapshots to fail closed and
   roll back, not claim without routing evidence.

8. **P1 — Canonical negative fixture matrix is incomplete.**
   Only missing-keys, bad-identity, and context-mismatch negative files exist.
   Add byte-identical Coordinate-owned/MultiNexus-mirrored fixtures for extra
   keys, stale token, bad digest, bad timestamps, invalid TTL/interval, and
   resource mismatch, with executable raw-byte equality checks for every file.

## Required regression evidence

- Inject failure after progress CAS and before event append: zero writes.
- Race reaper/renewal against progress and terminal report: stale mutation is
  impossible.
- Reproduce resource-blocked candidate A with selectable candidate B and prove
  B receives only B's context/resource/binding.
- Missing, non-object, and malformed lease on typed claim: provider call count
  remains zero.
- Managed recovery without either evidence field fails with zero mutation;
  valid recovery records both bounded fields.
- Public claim response retains all bounded blocking reasons/evidence.
- Re-run focused/full suites and static/fixture gates after corrections.

