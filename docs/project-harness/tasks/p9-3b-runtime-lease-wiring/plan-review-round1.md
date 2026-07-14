# P9-3B Independent Plan Review — Round 1

Verdict: `changes_requested`  
Reviewer: GLM-5.2 through Oh My Pi  
Provider/model: `zhipu-coding-plan/glm-5.2`  
Session: `019f5e98-90c7-7000-84a4-aa0db1e65eb7`  
Reviewed plan SHA-256:
`f6bcf98467c022f3c8098f27ef0460519eccec128010d3f0fd4c538c4696ee01`

The reviewer independently verified both repository revisions and the plan digest,
then inspected the runtime, lease/resource/capacity, DB/event/delivery, schema, CLI,
agentd worker/client/context/binding, and focused race tests.

## Must-fix findings

### P0 — lease-only inline expiry can orphan a running job

`reserve_attempt_lease()` currently calls
`_expire_due_for_agent_or_resource()`. That helper changes a due active lease to
`expired` without changing its exact job. A later claim for another agent but the same
resource can therefore free the partial unique index while leaving the former job
`running`.

Required correction:

- make bounded global reap the only expiry authority;
- reap must atomically expire the lease, CAS its exact running attempt to
  `timed_out + recoverable`, and append its lifecycle evidence;
- remove inline expiry from reserve; reserve returns a distinct conflict when reap
  backlog remains;
- provide a periodic production reaper so an idle agent is not required to claim
  again before its expired job becomes recoverable.

### P1 — managed lease gate must cover all three mutation paths

The plan's possession rule was not expressed as an executable predicate. It must cover
`_apply_terminal_job_update`, `record_job_progress`, and `_accept_late_result`.

Required correction:

- an attempt is managed whenever any lease row exists for
  `(job_id, attempt_token)`, regardless of lease status;
- every managed mutation requires the exact active/unexpired
  `(lease_id, job_id, attempt_token, agent_id)` tuple;
- attempt-token-only legacy behavior is available only when no lease row exists;
- an expired attempt's late result is rejected even before `N+1` is reclaimed.

### P1 — current runtime commits must be explicitly removed or gated

The plan referenced `commit=False` DB seams but did not enumerate runtime's existing
intermediate commits in `claim_job`, `_apply_terminal_job_update`,
`record_job_progress`, and `_accept_late_result`.

Required correction:

- one orchestration-owned `BEGIN IMMEDIATE` and one final commit;
- every nested event/delivery write uses `commit=False`;
- failure injection at each former commit boundary proves all-or-nothing
  job/context/lease/event/delivery state.

## Should-fix findings accepted into the revision

- Set an explicit production `busy_timeout`; evaluate WAL explicitly instead of
  relying on sqlite3's implicit timeout.
- Define Coordinate as the canonical lease-contract fixture source and verify the
  MultiNexus mirror by committed SHA/raw bytes.
- Resolve event volume now: ordinary renewals update the lease row but do not emit
  high-volume events.
- Prove provider subprocess/process-group cancellation and join; control-plane
  fencing alone cannot stop an orphan from editing the worktree.
- Derive the worker hard deadline from Coordinate `server_now + expires_at` using a
  monotonic clock and safety margin.
- State the bounded-scan starvation limitation and expose it rather than claiming
  starvation freedom.
- Put authoritative reap time in the expiry event instead of adding schema solely for
  `expired_at`.
- State that P9-3B remains on schema v13 and uses a code rollback.
- Fail closed on legacy pending jobs without a runner profile; production zero-pending
  preflight prevents such rows from entering activation.

## Verified strengths

- Existing event/delivery helpers already support caller-owned transactions.
- Schema v13 is sufficient for one lease per attempt, active-resource exclusion,
  immutable capacity snapshots, and timestamp constraints; no v14 is justified.
- Lease primitives are commit-free and validate stored resource digests on every
  consuming path.
- Existing two-connection tests prove `BEGIN IMMEDIATE` serialization is viable.
- Dedicated renewal independent of progress/JSONL remains correctly outside P9-4.
- The coordinated maintenance window eliminates mixed-version claims if every managed
  consumer is inventoried and paused.
- Recovery remains Operator-only and the strict failure direction is safe.

## Round-1 disposition

All must-fix findings and accepted should-fix findings are routed into plan revision 2.
No implementation or Coding worker bootstrap is authorized until an independent
round-2 review approves the revised exact digest.
