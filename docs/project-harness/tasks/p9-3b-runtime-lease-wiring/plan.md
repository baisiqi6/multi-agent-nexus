# P9-3B Runtime Lease Wiring — Detailed Plan

Status: revision 2 ready for independent review  
Date: 2026-07-14  
Measurement: `measurement.md`

## 1. Goal

Make a Coordinate-managed execution attempt authoritative only while the worker
possesses one exact active lease. Claiming a job and reserving executor/worktree
capacity must be one transaction. Managed progress, renewal, terminal report,
release, expiry, and recovery must all be fenced by the same
`job_id + attempt_token + agent_id + lease_id` identity.

P9-3B is successful when two concurrent workers cannot exceed an executor policy
or enter the same normalized worktree, a quiet provider remains authorized through
an independent heartbeat, and a stale worker cannot mutate a job after lease loss.

## 2. Non-goals

- No provider JSONL/session/process observation contract (P9-4).
- No correctness judgment from heartbeats or progress.
- No general distributed scheduler, priority system, preemption, or speculative
  work stealing.
- No automatic ordinary-agent reclaim of recoverable jobs.
- No dynamic capacity-policy update while active leases exist.
- No full production concurrency/crash matrix or P9-3 closeout (P9-3C).
- No broad `runtime.py`, `policy.py`, or `transitions.py` decomposition.
- No new control plane or direct MultiNexus writes to Coordinate SQLite.

## 3. Authority and invariants

### 3.1 One atomic claim

For every successful managed claim, one `BEGIN IMMEDIATE` transaction must contain:

1. one bounded global due-lease reconciliation batch through the single reap
   authority described in section 8;
2. deterministic candidate selection;
3. execution-context/binding/routing validation and any pre-upgrade context backfill;
4. job CAS to `running` with incremented attempt token;
5. capacity/resource lease reserve for that exact new attempt;
6. `job.claimed` event carrying bounded lease evidence;
7. one final commit.

Any error or capacity/resource conflict before selection completion rolls back all
job, lease, context-backfill, and event writes. A successful response is never
returned unless the committed job and active lease both exist.

### 3.2 Exact lease possession

The managed mutation identity is the tuple:

```text
(lease_id, job_id, attempt_token, agent_id)
```

The active lease row must also continue to match its immutable runner, host,
normalized resource, resource digest, capacity-policy digest, and capacity snapshot.
All stored snapshot validation remains fail closed.

Attempt token alone is no longer sufficient for a P9-3B-managed attempt. It remains
only a compatibility fence for legacy attempts that provably have no lease row.
There is no flag that lets a caller bypass lease possession for an attempt that has
or had a managed lease.

The managed-attempt predicate is exact and shared by every mutation path:

```text
EXISTS execution_attempt_leases
WHERE job_id = JOB_ID AND attempt_token = ATTEMPT_TOKEN
```

Because v13 enforces `UNIQUE(job_id, attempt_token)`, any row in any status makes the
attempt managed. `report_job_result`, `record_job_progress`, and
`_accept_late_result` must all apply this predicate before their existing CAS. A
managed row requires the exact active/unexpired lease tuple; only an attempt with no
lease row may enter the bounded legacy path.

### 3.3 Lease is liveness authority, not correctness evidence

Renewal means only that the managed worker still controls the attempt. It does not
prove useful model activity, valid JSONL progress, file mutation, task correctness,
or completion. Those observations remain separate and are routed to P9-4.

## 4. Cross-repository lease contract

Add a versioned claim `execution_lease` envelope. Coordinate produces it and
MultiNexus consumes it without importing Coordinate Python code. The v1 envelope
has an exact key set and includes at least:

- `contract_version`;
- `lease_id`, `job_id`, `attempt_token`, and `agent_id`;
- `runner_profile_id`, `host_id`;
- `resource_kind`, `resource_key`, and `normalized_path`;
- `capacity_policy_id` and `max_concurrent_jobs`;
- `acquired_at`, `expires_at`;
- Coordinate `server_now` for clock-independent remaining-budget calculation;
- `ttl_seconds` and `renew_interval_seconds`.

Coordinate must build this envelope from the committed lease row and fixed runtime
policy, not from caller input. MultiNexus validates exact keys, strict types, UUID/
digest/timestamp shapes, positive attempt, supported version, TTL bounds, renewal
interval `< TTL`, and every available cross-link to the job, execution context,
and executor binding before invoking a provider.

Coordinate owns the canonical contract fixtures because it produces the envelope.
MultiNexus carries a reviewed mirror plus an executable committed-SHA/raw-byte
equality check against Coordinate. The two repositories receive byte-identical positive and
negative fixtures for missing/extra keys, wrong identity, stale token, bad digest,
bad timestamps, invalid TTL/interval, and context/resource mismatch.

## 5. Deterministic claim and fairness rule

Inside one write transaction, candidates are ordered only by:

```text
created_at ASC, id ASC
```

The v1 fixed scan limit is 256 candidates. It selects
the first candidate whose validated resource is not actively leased and for which
the executor has capacity. Rules:

- capacity exhaustion for the executor stops selection immediately;
- a resource-blocked candidate may be skipped so a later different-worktree job
  can run;
- an invalid/corrupt authority snapshot is an error, not a skippable candidate;
- no random ordering, provider preference, or hidden priority is introduced;
- ordinary mode considers only `pending`; explicit recovery mode considers
  `pending` and `timed_out + recoverable` in the same stable ordering;
- reaching the scan bound returns `claimed=false` with a bounded machine-readable
  reason and oldest-blocked evidence; it does not mutate queue state.

The limit is a deliberate safety bound, not a claim of starvation freedom. Jobs
behind 256 continuously blocked older candidates can remain blocked longer than one
TTL when those leases keep renewing. This condition must be visible through
`scan_limit_reached`, queue depth, oldest blocked job/resource, and doctor output;
v1 does not silently rotate or reorder the queue. The initial production policy keeps
capacity at 1 and the rollout gate rejects a pre-existing pending backlog, making this
path exceptional rather than normal scheduling behavior.

The claim response distinguishes at least `queue_empty`, `capacity_exhausted`,
`resource_blocked`, and `scan_limit_reached`. Repeated poll events are not persisted,
avoiding event spam. Operator listing/doctor output must expose enough lease/job
identity to diagnose starvation without exposing prompts or secrets.

## 6. Renewal lifecycle

### 6.1 Runtime commands

Add a managed renewal operation equivalent to:

```text
coordinate runtime job lease-renew JOB_ID \
  --agent-id AGENT_ID \
  --attempt-token N \
  --lease-id LEASE_ID
```

The runtime chooses the approved TTL; workers cannot extend it arbitrarily. Renewal
runs in `BEGIN IMMEDIATE`, validates the exact active and unexpired lease plus the
exact running job attempt, advances expiry monotonically, and commits once.

Renewals are stored in the durable lease row and do not append ordinary renewal
events. Lifecycle events are limited to claim, release, expiry, and recovery so the
event stream is not flooded; `renewed_at`, `expires_at`, and the exact lease row are
the renewal evidence.

### 6.2 Worker heartbeat

`AgentdWorker` starts a dedicated asynchronous renewal task after the entire claim
envelope is validated and before provider invocation. It is independent of adapter
progress callbacks, JSONL activity, file changes, or model output.

The provider task and renewal task are supervised together:

- provider completion cancels and joins the renewal task before terminal report;
- authoritative renewal rejection marks the lease lost, cancels and joins the
  provider task, and forbids normal progress/result reporting;
- transport renewal failure is fail closed. The implementation may perform bounded
  retries only inside the last confirmed lease budget; it must never assume renewal;
- each Coordinate response supplies `server_now + expires_at`. Agentd converts their
  difference into a local monotonic hard deadline with a fixed five-second safety
  margin; it never derives authority from unsynchronized local wall time;
- cancellation must be awaited. P9-3B must reproduce cancellation against every
  configured generic provider adapter and ensure its owned subprocess/process group
  is terminated and joined. If an adapter cannot prove this, the implementation is
  not accepted; lease fencing alone is insufficient because an orphan can still edit
  the worktree;
- shutdown/cancellation does not claim successful release. If an exact terminal
  report cannot be committed, the reaper remains authoritative.

Progress callbacks continue to report bounded provider progress, but progress does
not renew the lease and cannot substitute for the dedicated heartbeat.

## 7. Lease-fenced progress and terminal report

### 7.1 Progress

Managed progress requires `lease_id` and the exact attempt tuple. Coordinate validates
an active, unexpired lease and the running job in one transaction before updating
`last_activity_at` / `progress_json` and appending `job.progress`. Wrong, released,
expired, mismatched, or missing managed lease identity produces zero mutation/event.

### 7.2 Terminal result and release

For `done`, `failed`, or worker-reported `timed_out`, one transaction must:

1. validate the exact active/unexpired lease and running attempt;
2. normalize and CAS the job to the requested terminal/recoverable state;
3. release that exact lease with a deterministic bounded reason;
4. append terminal, agent-report, optional review, and lease-release events;
5. create the response delivery when applicable;
6. commit once.

No terminal job commit may precede lease release or its event/delivery. Any failure
rolls back every part. Exact replay may return the prior committed result, but a
conflicting replay or a stale/released/expired lease cannot create a new event or
delivery.

If claim validation fails before any lease tuple can be trusted, MultiNexus invokes
no provider and does not mutate the job with untrusted raw fields; expiry recovery
cleans the attempt. If lease identity is already independently validated but context,
payload, or binding validation fails, agentd reports `failed` with that exact lease,
allowing atomic release.

## 8. Expiry, reap, and recovery

Add a bounded global runtime reap operation and call one batch at the start of every
claim. Install a production Coordinate lease-reaper timer with a 15-second cadence so
an idle executor's expired lease does not leave its job running forever. Each run uses
the `idx_execution_attempt_leases_expires` order and processes at most 100 due leases;
subsequent timer ticks drain a backlog. Reap is the only authority allowed to change
an active lease to expired.

Remove `_expire_due_for_agent_or_resource()` from `reserve_attempt_lease`. Reserve
must never perform lease-only expiry; after the caller's reap batch it either reserves
or returns a distinct due-active/reap-backlog conflict without changing that lease.
Update the existing primitive test that currently expects reserve to expire due rows.

For each due lease, one transaction must:

1. revalidate the stored lease/resource snapshot;
2. require the matching job to still be `running` at the same attempt and agent;
3. mark the lease `expired`;
4. CAS the job to `timed_out`, `recoverable=1`, with a bounded
   `execution_lease_expired` timeout result;
5. append idempotent expiry/timeout events;
6. commit once.

The expiry lifecycle event includes the authoritative reap timestamp in addition to
the lease's scheduled `expires_at`, so v13 does not need an `expired_at` column.

An inconsistent active lease/job pair is a doctor-visible integrity error and is not
silently repaired or skipped as if healthy. Reap is idempotent and bounded.

Ordinary agentd still claims only pending jobs. An Operator must explicitly start
recovery mode to reclaim `timed_out + recoverable`; reclaim creates attempt `N+1`
and a new lease. Any result/progress/renewal from expired attempt `N` is rejected,
even if attempt `N+1` has not yet been claimed. The existing late-result acceptance
path remains only for provably legacy, unleased attempts.

For a managed expired attempt, recovery additionally requires an audited Operator
reason and explicit confirmation that the prior provider process/session is stopped.
P9-3B cannot infer that evidence from heartbeat or JSONL without entering P9-4, so it
must not automatically reclaim merely because wall-clock expiry occurred.

## 9. Code boundaries

### Coordinate

- Extend the existing lease primitive module only for reusable strict validation and
  full-envelope reads; keep it transaction-owned and commit-free.
- Add one focused runtime-lease orchestration/contract module for lease tuple
  validation, envelope construction, targeted reap, and bounded selection support.
- Keep public runtime entry points and existing report/event semantics in
  `runtime.py`, delegating lease-specific decisions to the focused module.
- Use existing `append_event(..., commit=False)` and
  `create_delivery(..., commit=False)` seams. Do not create a second database or
  repository abstraction merely for this package.
- Explicitly remove or transaction-gate the current internal commits in
  `claim_job`, `_apply_terminal_job_update`, `record_job_progress`, and
  `_accept_late_result`. The orchestration layer owns one
  `BEGIN IMMEDIATE` and one final commit; every event/delivery call inside uses
  `commit=False`.
- Extend `execution_cli.py` only with static registrations/handlers for renew/reap
  and the new exact lease arguments.

### MultiNexus

- Add a focused strict `execution_lease` parser/contract module beside
  `execution_context.py` and `executor_binding.py`.
- Extend `CoordinateRuntimeClient` with exact lease arguments and renewal/reap-facing
  calls; it remains CLI transport only.
- Add a small worker lease supervisor rather than embedding retry/cancellation state
  throughout provider adapters.
- Provider adapters remain unchanged unless a concrete awaited-cancellation defect is
  reproduced. No provider-specific lease branches are allowed.

## 10. Compatibility and rollout

Newly claimed P9-3B attempts are always leased. Legacy rows that have no lease may
retain the old explicit Operator/report behavior, but an attempt with any lease row
can never use that path.

Because old agentd cannot safely consume the new protocol, production uses a
coordinated maintenance window rather than a mixed-version rolling claim window:

1. verify local full/focused suites and exact cross-repo fixtures;
2. push reviewed commits and verify `HEAD == origin/main` in both repositories;
3. require zero production pending/running jobs and zero active leases;
4. back up the Coordinate DB, record mode/owner/size/SHA/integrity/schema;
5. pause every managed production consumer in scope;
6. deploy Coordinate, confirm schema remains v13, and run integrity plus
   installed-source SHA checks;
7. deploy MultiNexus consumers and verify deployed-source SHA/contract parity;
8. restart consumers, run bounded empty-queue and one disposable leased-job smoke;
9. verify the disposable job releases its lease, services are healthy, restart counts
   are stable, and no temporary artifacts remain;
10. write deployment/dogfood evidence before durable P9-3B completion.

If all managed consumers cannot be paused or proven upgraded, activation is blocked;
the plan does not silently permit a mixed-version window.

The rollout must first inventory server systemd consumers and local/remote launchd
agentd consumers from the accepted executor registry; pausing only the Discord bridge
is insufficient. Production DB connections receive an explicit 30-second
`busy_timeout`, with lock-timeout failures classified separately from an empty or
blocked queue. WAL is deliberately not enabled in P9-3B: changing journal mode would
alter backup/sidecar/rollback operations and is not required for the bounded serialized
writer design. Read/write contention is measured again in P9-3C.

P9-3B uses schema v13 without migration. It is a coordinated code/unit deployment;
rollback redeploys the prior Coordinate and MultiNexus revisions after consumers are
paused and DB integrity/version are rechecked. The DB backup remains mandatory because
runtime rows/events/leases can be written after activation even without a schema bump.

Jobs with a null/missing `runner_profile_id` fail closed before claim. Production's
zero-pending/running preflight prevents legacy pending rows from entering that path.

## 11. Test strategy

### Coordinate focused tests

- two SQLite connections racing one executor at capacity 1: exactly one claim/lease;
- two executors or one capacity>1 executor racing the same normalized resource:
  exactly one active worktree lease;
- different resources up to capacity succeed; capacity+1 does not;
- job/context/event/lease all commit or all roll back under injected failures;
- failure injection is attached to each former internal-commit boundary in
  `claim_job`, `_apply_terminal_job_update`, `record_job_progress`, and
  `_accept_late_result`;
- exact `claimed=false` reasons and deterministic bounded oldest-eligible order;
- invalid context/binding/routing/resource/policy data is not skipped or mutated;
- renew exact success, monotonic expiry, wrong tuple, stale, released, expired, and
  concurrent terminal races;
- progress requires active exact lease and commits with its event atomically;
- terminal status, release, events, review projection, and delivery are atomic;
- replay is idempotent; conflicting/stale replay has zero writes;
- due reap atomically expires lease and makes the exact job recoverable;
- stale old worker is rejected before and after explicit recovery claim;
- managed late result is rejected even before attempt `N+1` is reclaimed;
- legacy unleased late-result behavior remains bounded to legacy attempts;
- CLI contract and malformed-argument coverage.

### MultiNexus focused tests

- exact lease contract positive and adversarial fixture matrix;
- no provider invocation for any invalid composite claim;
- trusted lease plus bad context/payload/binding reports failed and releases exactly;
- dedicated renewal continues while an adapter emits no progress;
- progress does not renew;
- renewal authority loss cancels/joins provider execution and suppresses normal result;
- provider completion stops heartbeat before exact terminal report;
- cancellation, report failure, and shutdown leave recovery to expiry without false
  release claims;
- claim/report/progress CLI commands carry the exact tuple;
- local hard deadline uses Coordinate `server_now`, TTL budget, and safety margin;
- every configured provider adapter cancellation kills/joins its owned process group;
- sequential worker behavior and P9-1/P9-2 context/binding invariants remain intact.

### Full/regression gates

- Coordinate focused lease/runtime/CLI/schema suites pass.
- Coordinate full suite has no failures beyond the exact reviewed historical baseline.
- MultiNexus focused agentd/context/binding/contract/deploy suites pass.
- MultiNexus full suite passes with only accepted skips/warnings.
- `git diff --check`, Python compile checks, shell syntax checks, fixture byte equality,
  harness validation, and doctor checks pass or retain only documented historical
  warnings.

## 12. P9-3B acceptance criteria

1. Successful claim implies one committed exact active lease; unsuccessful claim
   leaves no partial job/event/context/lease mutation.
2. Capacity and same-worktree exclusion hold under real two-connection races.
3. Managed progress/result/renewal require exact active lease possession.
4. Quiet provider execution is kept alive by a dedicated renewal loop, not JSONL or
   progress callbacks.
5. Lease loss stops provider execution and stale workers cannot mutate the job.
6. Terminal transition and lease release are atomic with events/delivery.
7. Expiry and recoverable job transition are atomic; reclaim remains Operator-only.
8. Queue selection is deterministic, bounded, and exposes blocking reasons.
9. Cross-repository v1 contract fixtures and adversarial validation pass.
10. Production is synchronously upgraded under the maintenance contract, with backup,
    integrity, version, SHA, service, smoke, zero-residue, and zero-active-lease-at-end
    evidence.
11. Durable plan review, worker bootstrap, implementation report, Codex result review,
    deployment record, dogfood note, receipt, and closeout are present.
12. Reap is the only expiry authority; no code path can commit an expired lease while
    leaving its exact managed attempt running.

## 13. P9-3C handoff

P9-3B closeout authorizes only the already planned P9-3C detailed-plan gate. P9-3C
must freshly measure and then prove on disposable production jobs:

- capacity saturation and release;
- same-worktree exclusion and different-worktree concurrency;
- quiet-job renewals;
- worker crash/lease expiry/reap;
- explicit recovery to attempt `N+1`;
- stale attempt `N` progress/result rejection;
- service restart and residue/data-integrity behavior.

P9-3C does not begin until its detailed plan is independently reviewed and receives
a new exact-revision bootstrap.
