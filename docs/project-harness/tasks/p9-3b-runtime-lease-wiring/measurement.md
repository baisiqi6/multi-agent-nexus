# P9-3B Current-State Measurement

Date: 2026-07-14  
Scope: runtime claim/lease wiring, managed-worker lease possession, renewal,
terminal release, expiry recovery, and deterministic queue selection

## Baselines

- Coordinate `main == origin/main`:
  `af8461efdf6beb7c47560fe3d17b30f2ac6696ba`.
- MultiNexus `main == origin/main`:
  `3364db6b469ead6cf06c78fef0476fcec313a7c0`.
- Coordinate production schema: v13.
- Production Coordinate version:
  `af8461efdf6beb7c47560fe3d17b30f2ac6696ba`.
- Production MultiNexus version:
  `3364db6b469ead6cf06c78fef0476fcec313a7c0`.
- Production services `coordinate.service` and
  `multinexus-discord-bridge.service` are `active/running`, with
  `NRestarts=0` and `ExecMainStatus=0`.
- Production DB integrity is `ok`; it contains 151 `done`, 20 `failed`, zero
  nonterminal jobs, and zero total/active execution-attempt leases.

## P9-3A authority now present

Coordinate schema v13 and focused modules provide:

- independently versioned per-instance capacity policies;
- host-aware, lexical, normalized worktree resource keys;
- an `execution_attempt_leases` table with one row per job attempt, a partial
  unique active-resource index, capacity snapshots, TTLs, and strict state
  constraints;
- caller-owned transaction primitives to reserve, renew, release, explicitly
  expire, and expire due leases;
- source/deployed parity, guarded production projection restore, and isolated
  lease-lifecycle proof.

These primitives deliberately do not commit their caller's transaction. That
is the correct foundation for P9-3B, but they are not yet invoked by the runtime
claim/report/progress path.

## Current managed execution path

### Coordinate claim

`src/coordinate/runtime.py::claim_job` currently:

1. selects exactly one oldest `pending` job, or one oldest `pending` / explicit
   recoverable `timed_out` job;
2. resolves and validates the execution context and routing/binding snapshots;
3. updates the job to `running`, increments `attempt_count`, and commits;
4. appends `job.claimed` in a later transaction;
5. returns `job`, `attempt_token`, and `execution_context`.

It does not resolve a capacity policy, derive a resource key, reserve an attempt
lease, return a lease envelope, or distinguish queue-empty from capacity/resource
blocking. The status transition and event are not one atomic transaction.

### Coordinate progress and result

`record_job_progress` and `report_job_result` fence mutations with the optional
`attempt_token`. They do not require or validate possession of an active lease.
Progress commits before its event. Terminal job mutation commits before terminal
events and response-delivery creation. A terminal result does not release a
lease because no runtime lease is currently attached.

The legacy late-result path accepts an attempt result after a recoverable timeout
when the attempt has not yet been reclaimed. That is incompatible with lease
authority: after a managed lease expires, the old worker must no longer be able
to mutate the job, even before an Operator reclaims it.

### MultiNexus agentd

- `CoordinateRuntimeClient.claim_job()` preserves the raw claim result.
- `validate_claim_response()` strictly binds the execution context, job identity,
  and positive attempt token.
- `AgentdWorker` invokes one provider at a time per process and forwards the
  attempt token on progress and terminal report.
- Adapter progress can be quiet for an arbitrary period. It is provider
  observation, not a reliable lease heartbeat.
- There is no lease parser, lease token, dedicated renewal task, lease-loss
  cancellation path, or terminal release acknowledgement.

Therefore a second process using the same executor identity can still claim a
second job. If both contexts resolve to the same worktree, both can execute there.
P9-3A did not change this behavior by design.

## Transaction and coupling findings

- SQLite `BEGIN IMMEDIATE` is already used by other Coordinate split-operation
  authority paths and is suitable for serializing claim/reserve writers.
- `append_event()` and `create_delivery()` already support `commit=False`, so
  claim, job mutation, event, lease mutation, and terminal delivery can share a
  caller-owned transaction without inventing another database layer.
- `runtime.py` is 1,735 lines and owns claim/report/progress orchestration. P9-3B
  should add a focused runtime-lease service/contract module, but must not turn
  this package into a broad runtime rewrite or move cohesive code only to reduce
  line count.
- Existing `execution_leases.py` validates stored resource snapshots on every
  consuming path. New orchestration must preserve that fail-closed property and
  must not duplicate resource normalization.

## Queue and recovery gap

The current query uses `ORDER BY created_at, id LIMIT 1`. Once resource exclusion
exists, the oldest queued job may be blocked by a worktree lease while a later job
for another worktree is eligible. Selecting only one row creates unnecessary
head-of-line blocking; skipping without a bound or visibility creates unbounded
starvation and an unreviewable scheduler.

Expired lease primitives currently mutate only lease state. No transaction also
makes the exact corresponding `running` job `timed_out + recoverable`, and there is
no public runtime reap operation. Ordinary agentd correctly does not reclaim
recoverable jobs; that Operator gate must remain.

## Deployment compatibility finding

This is a cross-repository protocol change. Deploying Coordinate enforcement while
an old agentd can still claim work is unsafe: the old consumer ignores the lease
envelope, does not renew it, and cannot present its lease id on progress/report.

Production rollout therefore requires a coordinated maintenance window with:

1. zero running/pending jobs and zero active leases;
2. a verified DB backup;
3. managed consumers paused;
4. Coordinate and MultiNexus deployed as one compatibility unit;
5. schema/integrity/version/parity checks before consumers resume;
6. post-restart smoke and residue checks.

P9-3C will run the destructive-looking but disposable concurrency/crash matrix;
P9-3B must first make the synchronized production protocol safe and observable.

## Required P9-3B boundary

P9-3B must implement only:

- atomic claim plus lease reserve;
- a strict managed lease envelope and possession token;
- a provider-independent periodic lease renewal loop;
- lease-fenced progress and terminal report;
- atomic terminal transition plus exact lease release;
- atomic due-lease expiry plus recoverable job transition;
- explicit Operator recovery and stale-worker rejection;
- deterministic bounded oldest-eligible selection with blocking visibility;
- coordinated production rollout and bounded non-concurrency smoke.

Provider-native JSONL/session/process observation remains P9-4. The full production
concurrency/crash/recovery matrix and P9-3 closeout remain P9-3C.
