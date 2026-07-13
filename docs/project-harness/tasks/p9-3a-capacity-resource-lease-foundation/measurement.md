# P9-3A Current-State Measurement

Date: 2026-07-13  
Scope: capacity authority, worktree resource identity, and attempt-lease foundation

## Baselines

- Coordinate `main == origin/main`:
  `90783b2c77933287ba163c4bb598f4a862e8b416`.
- MultiNexus `main == origin/main`:
  `ccb2b6aee4c66903ebabae2451c657cf815c36ab`.
- Coordinate schema/code/production DB: v12.
- Executor identity source: `multinexus.discord`, source version 2, catalog hash
  `f4cdf79897755c173e97ddae1dfd88047436039f3447d4d6257105715ba5551d`.
- P9-2B terminal receipt:
  `a2a23a06-f551-404b-b917-9e29278c2809`.
- Production jobs at measurement: 150 `done`, 20 `failed`, zero pending/running/
  recoverable-timeout jobs.
- Accepted test baseline: Coordinate 2,156 passed plus exactly nine historical
  CLI-fixture/AST failures; MultiNexus 503 passed, 2 skipped.

## Existing behavior that must be preserved

- P9-1 stores an immutable host-resolved execution context and absolute worktree path.
- P9-2A stores an immutable executor binding; claim and agentd validate it before
  provider invocation.
- P9-2B selects a deterministic concrete instance and stores its complete request and
  decision. `routing_load` is an observed nonterminal job count, not a capacity claim.
- Phase 8.4.3 attempt fencing increments `jobs.attempt_count`; managed agentd requires
  and forwards the positive attempt token; SQL CAS rejects stale progress/results after
  reclaim.
- Recoverable timeout is explicit. Normal agentd polls pending jobs only; an Operator
  starts `--recoverable` mode to reclaim a timed-out recoverable job.
- One `AgentdWorker` process executes sequentially, but Coordinate does not prevent a
  second process with the same identity from claiming another job.

## Reproduced gap

An in-memory current-code probe submitted two exact-target jobs to one `mac-omp`
instance and called `claim_job` twice. Both claims succeeded, both jobs became
`running` at attempt token 1, and both execution contexts resolved to the same
worktree. The final running count was 2.

Therefore process topology currently supplies accidental capacity 1 only when exactly
one process exists. Coordinate has no durable capacity reservation or same-worktree
exclusion.

## Existing primitives that are not P9-3 lease authority

- Harness checklist `lease` protects task ownership/lifecycle.
- `ChecklistLock` protects split-operation file mutation.
- Provider adapter total/first-byte/activity timeouts are execution observations.
- `agents.online_state`, stale `last_seen_at`, and local process count do not reserve
  capacity.
- Completion receipts protect host-aware checklist closeout.

None may be silently reused as an execution attempt/resource lease.

## Size and concentration

- Coordinate measured modules: 4,795 lines / 129 top-level definitions;
  `runtime.py` alone is 1,735 lines.
- MultiNexus measured modules: 2,054 lines / 54 top-level definitions;
  `registry_authority.py` is 680 lines.
- New authority, normalization, and lease transaction code should live in focused
  modules. P9-3A must not deepen these existing concentration points unnecessarily.

## Accepted package split

P9-3 is divided into three reviewed packages:

1. **P9-3A** — independently versioned capacity authority, normalized worktree resource
   identity, schema/transactional lease primitives, deploy parity, and isolated proof;
2. **P9-3B** — atomic claim/reserve, mandatory managed lease token, renew/release,
   expiry/reap, recoverable transition, and deterministic oldest-eligible queue rule;
3. **P9-3C** — production concurrency/recovery matrix and P9-3 stage closeout.

P9-3A does not change runtime claim or MultiNexus provider execution behavior.
