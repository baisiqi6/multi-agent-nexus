# P9-3B Codex Result Review

## Decision

**Approved for commit, push, and the reviewed production maintenance gate.**

This is not P9-3B durable closeout. Deployment, production smoke, zero-residue and
zero-active-lease evidence, dogfood receipt, and closeout documentation are still
required.

## Review findings resolved

1. Lease parsing is closed-schema and cross-checks exact job, attempt, agent, runner,
   host, worktree resource, time interval, and digest authority.
2. A managed claim without a valid lease cannot invoke a provider or manufacture a
   report from untrusted fields.
3. Recovery claims fail closed unless reason and prior-process-stopped evidence are
   both present and normalized.
4. Renewal authority loss cancels and joins provider execution before suppressing
   normal progress/result reporting.
5. Cleanup failure is explicit and attempted once; adapters do not swallow it or
   retry a second destructive cleanup.
6. All locally constructible provider adapters own their execution process group.
   `jarvis-local` no longer relies on an unkillable background thread.
7. Cross-repository fixtures match committed Coordinate revision `3eaa7bf` byte for
   byte.

## Adversarial checks

- Missing/extra/malformed lease keys and single-fault fixture mutations reject before
  provider invocation.
- Context, binding, resource, TTL, timestamp, digest, identity, and stale-token
  mismatches reject without borrowing authority from the payload.
- Quiet providers renew without progress callbacks; progress alone never renews.
- Transport/authority renewal failure cancels the provider and cannot report success.
- Timeout, cancellation, stdin failure, and ordinary exceptions converge on a single
  awaited cleanup path.
- Real POSIX descendants are removed and the leader is reaped; cancellation of the
  cleanup await cannot abandon the cleanup task.

## Accepted residuals

- Coordinate retains the exact nine reviewed historical full-suite failures. They are
  outside P9-3B and must not be silently rebaselined.
- MultiNexus harness doctor retains historical optional/runtime-pointer misses and
  four extended-workflow warnings.
- Real Windows process-tree proof is deferred to a Windows host; only the Windows API
  contract is locally unit-tested.
- Real production capacity, concurrency, crash/reap/recovery, and stale attempt N
  proofs belong to the independently reviewed P9-3C disposable-job gate after P9-3B
  deployment closeout.

## Reviewer authorization

The implementation may now be committed and pushed. Production synchronization must
still follow the approved maintenance contract: backup, integrity/version/SHA checks,
synchronous Coordinate and MultiNexus update, service health, bounded smoke,
zero-residue, zero-active-lease-at-end, and recorded rollback evidence.
