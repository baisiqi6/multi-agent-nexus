# P9-3C Production Concurrency/Recovery Matrix — Detailed Plan

Status: draft correction incorporated, blocked pending independent review and
P9-3C0 fixture closure.
Date: 2026-07-14 Asia/Shanghai
Measurement: `measurement.md`
Review: `plan-review-round1.md` (changes requested; no production authorization)

## 1. Goal

Split into two stages:

- **P9-3C0**: Establish a local or sidecar runtime fixture that proves a
  no-paid-provider quiet job, typed context/binding/worktree lease, two
  capacity-1 executors, exact process handle/stop/status, and scoped queue
  isolation. If the fixture does not already exist, it must be delivered through
  a separate implementation plan, result review, and deployment decision; this
  plan does not authorize that implementation.
- **P9-3C1**: Use the closed P9-3C0 fixture to obtain production runtime
  evidence that the P9-3B lease authority enforces capacity saturation/release,
  cross-executor worktree concurrency/exclusion, automatic quiet-job renewal,
  stop/expiry/reap, explicit recovery to attempt `N+1`, stale-attempt `N`
  rejection, and service-restart integrity/residue behavior. All evidence comes
  from bounded, disposable, non-user jobs; zero paid-provider calls; no real
  user job affected.

## 2. Non-goals

- No new Coordinate or MultiNexus implementation in P9-3C1 (P9-3B is closed).
  P9-3C0 implementation, if required, is a separate work package.
- No provider-native JSONL/session/process observation contract (P9-4).
- No multi-project/provider dogfood matrix (P9-5).
- No dynamic capacity-policy change, priority system, or preemption.
- No automatic ordinary-agent reclaim of recoverable jobs.
- No mixed-version rollout; all consumers are already at P9-3B.
- No Windows/Pad matrix rows unless availability and real process-tree stop are
  independently verified as optional variants before execution.
- No manual `lease renew` used as evidence for automatic renewal.
- No whole-DB restore for ordinary matrix failures.

## 3. Authority and invariants

- Coordinate remains the sole lease authority. MultiNexus remains the execution
  fabric.
- P9-3C1 executes only after the P9-3C0 fixture contract is named, implemented
  if necessary, reviewed, deployed, and its exact stop/status helper is
  verified.
- Every production matrix row uses only the installed CLI; no direct SQLite
  mutation.
- Every row must include precondition, action, evidence, pass-fail, cleanup,
  and rollback-stop.
- Every `unverified` surface from `measurement.md` is a hard prerequisite gate.
  This plan does not approve its own execution.
- Zero residue means no active test leases, no running test processes, no
  temporary test files, and no nonterminal test jobs after cleanup. It does not
  require deleting audit rows from `jobs`, `events`, or
  `execution_attempt_leases`.
- **Zero paid-provider budget**: P9-3C0 and P9-3C1 must not invoke any paid
  external provider. If a real provider is unavoidable, stop and require a new
  human gate; do not silently permit it.

## 4. Terminology and bounded ledger

- `E1`, `E2`: two distinct disposable executors, each with
  `max_concurrent_jobs=1` in the deployed capacity policy.
- `W1`, `W2`: two distinct normalized worktrees available to the disposable
  executors.
- **Namespace prefix**: `p9-3c1-<YYYYMMDD>-<row>-<seq>-`. Apply it to the
  controllable `task-id`, actor/idempotency fields, fixture names, and temp paths.
  Coordinate-generated job/lease ids are not assumed to contain the prefix; every
  returned id, attempt token, process handle, and temp path is recorded in the ledger.
- **Per-row operation key**: `p9-3c1-<row>`. Use it as an idempotency key only where
  the live CLI actually exposes one; otherwise record it in the ledger and use the
  namespaced `task-id`/`actor` fields that are supported. `job create` is not claimed
  to have an idempotency flag.
- **Evidence ledger**: durable file at
  `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/evidence-<timestamp>.md`
  (created at execution time). Contains only identifiers, timestamps, status
  transitions, CLI exit codes, and filtered counts; never payload, prompt,
  result text, environment, credentials, or user messages.
- **Bounded maximum budget for P9-3C1**:
  - Jobs: 8 distinct job ids (A:2, B:3, C:1, D/E/F:1, G0:0, G1:1).
  - Concurrent fixture processes: 2 (Row B).
  - Processes total: ≤12 (including recovery restart).
  - Temporary files/directories: one per worktree use, cleaned per row.
  - Paid provider calls: 0.
- `capacity show` returns only policy (`agent_id`, `policy`). Active usage and
  resource concurrency evidence come from `execution_attempt_leases` counts
  filtered by test agent/status/lease id.

## 5. Executor selection

- **Mandatory**: a reviewed P9-3C0 fixture providing two capacity-1 executors on
  the same host (preferred Mac) with exact process stop/status.
- **Global quiescence**: before every P9-3C1 mutating row, prove the production DB
  has no non-test `pending/running/timed_out+recoverable` job and no non-test active
  lease; freeze new submissions to E1/E2 for the bounded row window. Stop if this
  changes. `lease reap` is global and is never represented as test-id scoped.
- **Optional variants**: `win-*` and `pad-jarvis` rows are blocked until host
  availability and real process-tree stop are independently verified; they are
  not required for acceptance.

## 6. Matrix rows

### Row A — Capacity saturation and release on one executor

**precondition**
- P9-3C0 fixture closed and verified.
- Production DB integrity `ok`, schema 13, zero active test leases.
- `coordinate runtime capacity list` shows E1 `max_concurrent_jobs=1`;
  `execution_attempt_leases` filtered by test id shows 0 active for E1.
- Two disposable jobs queued: `J1`, `J2` for E1 with same runner profile and
  namespace.

**action**
1. Claim `J1` as E1. Expect `claimed=true`, lease `L1`.
2. Immediately claim `J2` as E1. Expect `claimed=false`, reason
   `capacity_exhausted`.
3. Wait for `J1` to perform at least one automatic renewal.
4. Report `J1` done with `L1`.
5. Claim `J2` again as E1. Expect `claimed=true`, lease `L2`.
6. Report `J2` done with `L2`.

**evidence**
- `coordinate job list --status running` shows at most one running job for E1
  at any time.
- `execution_attempt_leases` filtered by test id shows exactly one active row
  during steps 1–3 and zero active rows after step 4.
- `coordinate runtime capacity show E1` shows policy only; active usage derived
  from lease count is 1/1 during saturation and 0/1 after release.
- Claim response for `J2` (step 2) includes `capacity_exhausted` and no lease.

**pass-fail**
- Pass: both jobs eventually complete; capacity blocks `J2` until `J1`
  released.
- Fail: both jobs run concurrently, `J2` rejected without cause, or a lease
  remains active after both terminal.

**cleanup**
- Confirm zero active test leases, zero running test jobs, no orphan processes,
  no temp files.
- Do not delete `jobs`/`events`/`execution_attempt_leases` rows; record ids in
  the evidence ledger.

**rollback-stop**
- If `J1` cannot be reported done, stop the exact provider process tree using
  the verified P9-3C0 helper, run explicit `lease reap`, then recovery only via
  explicit `--recoverable --prior-process-stopped` with audited reason.
- Ordinary failures do not restore the whole DB; use process cleanup, supported
  API cleanup, code/service rollback, or forensic stop/copy as appropriate.

### Row B — Cross-executor worktree concurrency and exclusion

**precondition**
- P9-3C0 fixture closed; E1 and E2 each `max_concurrent_jobs=1`; zero active
  test leases.
- `W1`, `W2` distinct worktrees available to both executors.

**action**
1. Create `J1` for E1 on `W1`; create `J2` for E2 on `W2`.
2. Claim `J1` as E1. Expect lease `L1` for `W1`.
3. Claim `J2` as E2. Expect lease `L2` for `W2`.
4. Record the concurrent `L1/W1 + L2/W2` evidence, then report `J2` done with
   `L2`, freeing E2 capacity while `L1/W1` remains active.
5. Create `J3` for E2 on `W1`.
6. Claim `J3` as E2. Expect `claimed=false`, reason `resource_blocked` (same
   worktree `W1` already held by E1).
7. Report `J1` done with `L1`.
8. Claim `J3` again as E2. Expect `claimed=true`, lease `L3`.
9. Report `J3` done with `L3`.

**evidence**
- `execution_attempt_leases` filtered by returned test lease ids shows `L1/W1`
  and `L2/W2` active concurrently after step 3, then only `L1/W1` active before
  the step-6 exclusion claim.
- Claim response for `J3` shows `resource_blocked` and names blocking resource
  `W1`.
- `J3` succeeds only after `J1` releases `W1`.

**pass-fail**
- Pass: different worktrees run concurrently across executors; same worktree is
  exclusive across executors.
- Fail: same worktree allows two leases, different worktrees are serialized, or
  the blocked reason is missing/wrong.

**cleanup**
- Confirm zero active test leases, no running jobs, no orphan processes, no
  temp files.
- Preserve ids in the evidence ledger.

**rollback-stop**
- If a same-worktree duplicate lease is observed, stop both exact process trees
  using the verified helper, run explicit `lease reap`, capture a forensic DB
  copy, and halt the matrix. Do not restore the whole DB unless the incident
  gate is met.

### Row C — Automatic quiet-job renewal

**precondition**
- P9-3C0 quiet fixture verified; zero active test leases.
- Quiet job configured to produce no progress events/output for at least two
  automatic renewal intervals.

**action**
1. Create `Jq` for E1.
2. Claim `Jq` as E1. Expect lease `Lq` with `ttl_seconds` and
   `renew_interval_seconds`.
3. Do not send progress, result, or manual `lease renew` for a period exceeding
   two `renew_interval_seconds` but less than `ttl_seconds`.
4. Observe `execution_attempt_leases.expires_at` advance monotonically at least
   twice via read-only queries.
5. Verify worker/agentd logs (filtered by job/lease id) show automatic renew
   activity and no progress/output events.
6. Report `Jq` done with `Lq`.

**evidence**
- `expires_at` and `renewed_at` advance at least twice during the quiet window.
- No progress events emitted by the job during the quiet window.
- Job remains `running` throughout.
- Manual `lease renew` is forbidden; if used, this row is invalid.

**pass-fail**
- Pass: quiet job survives solely on automatic heartbeats for ≥2 intervals.
- Fail: lease expires during quiet window, renewal fails with valid identity,
  progress is required, or any manual renewal is used as evidence.

**cleanup**
- Confirm lease release and zero active test leases.

**rollback-stop**
- If renewal stops, stop the exact process tree, run explicit `lease reap`, do
  not report from a stale lease.

### Row D/E/F — Chained expiry/reap, recovery N+1, stale-N rejection

**precondition**
- P9-3C0 fixture closed; exact stop helper verified; zero active test leases.
- **Queue freeze**: before step 1, confirm E1 has no other `pending` or
  `recoverable` jobs and hold new submissions for E1 until this chain
  completes.
- Reap uses explicit `coordinate runtime job lease reap`; automatic reaper is
  not assumed.

**action**
1. Create `Jc` for E1. Record expected job id.
2. Claim `Jc` as E1. Expect `claimed=true`, lease `Lc`, attempt token `N`.
3. Stop the exact provider process tree for `Jc` without reporting a result.
4. Do not send further renewals.
5. Wait for `Lc.expires_at` to pass plus a bounded buffer.
6. Run `coordinate runtime job lease reap --batch-size 100`.
7. Inspect `Jc`: expect `status=timed_out`, `recoverable=1`, attempt token `N`.
8. Inspect `Lc`: expect status `expired`.
9. (Recovery) Run
   `coordinate runtime job claim --agent-id E1 --recoverable --recovery-reason "P9-3C1 D/E/F recovery" --prior-process-stopped`.
10. Verify returned job id equals `Jc`; if not, stop and cleanup.
11. Expect `claimed=true`, lease `Lc2`, attempt token `N+1`.
12. Report `Jc` done with `Lc2`.
13. (Stale-N rejection) Attempt `progress` for `Jc` using attempt token `N` and
    lease `Lc`.
14. Attempt `report done` for `Jc` using attempt token `N` and lease `Lc`.
15. Attempt `lease renew` for `Lc`.

**evidence**
- `Lc` transitions to `expired`; `Jc` shows `timed_out` + `recoverable=1`,
  attempt `N`.
- Reap command output shows at least one due lease processed.
- Recovery claim returns job id equal to `Jc`; `Lc2` active for attempt `N+1`;
  `Lc` remains `expired`.
- `Jc` completes at attempt `N+1`.
- Stale attempts at steps 13–15 fail closed; compare bounded before/after
  authoritative fields (`jobs.status`, `jobs.attempt_token`,
  `execution_attempt_leases.status`). No mutation to authoritative job/lease
  state. Audit denial events, if appended, are not counted as mutations.
- No normal result/delivery for attempt `N`.

**pass-fail**
- Pass: expiry, reap, recovery, and stale rejection all behave as specified.
- Fail: any authoritative mutation by stale attempt `N`, recovery job-id
  mismatch, or old lease reused.

**cleanup**
- Confirm process tree gone, zero active test leases, no temp files.
- Record all job/lease/attempt ids in the evidence ledger.

**rollback-stop**
- If stale mutation succeeds, stop services if needed, capture a forensic copy,
  and halt. Whole-DB restore only via the incident gate.
- If the returned job id at step 10 does not equal `Jc`, stop and cleanup; do
  not proceed.

### Row G0 — Zero-active-lease service restart and integrity

**precondition**
- Zero active test leases; fresh P9-3B backup integrity-verified; maintenance
  window approved; no real user jobs running.

**action**
1. Record pre-restart service identity (`ActiveEnterTimestamp`, main PID) via
   `systemctl show coordinate.service`.
2. Run `PRAGMA integrity_check`, `user_version`, FK violation count.
3. Restart `coordinate.service` manually (e.g.,
   `systemctl restart coordinate.service`).
4. Verify service returns active with a new `ActiveEnterTimestamp`/PID.
5. Run `PRAGMA integrity_check`, `user_version`, FK violation count.
6. Verify `execution_attempt_leases` filtered by test id shows zero active
   rows.

**evidence**
- Service restart completes and returns active with changed identity.
- DB integrity `ok`, schema 13, FK violations 0 before and after.
- Zero active test leases after restart.
- `NRestarts` is not used as proof of manual restart.

**pass-fail**
- Pass: restart is safe and DB consistent with no active leases.
- Fail: service fails to restart, DB integrity degrades, or test lease/job
  state is inconsistent.

**cleanup**
- None beyond recording evidence.

**rollback-stop**
- If restart fails or integrity degrades, capture a forensic copy and halt.
  Whole-DB restore only via the incident gate.

### Row G1 — Active quiet-lease service restart (gated)

**precondition**
- P9-3C0 has measured and approved the exact downtime/transport-failure/TTL
  contract for this service restart.
- Zero other active test leases; maintenance window approved; no real user jobs
  running.
- Decide and document expected behavior before execution: which service(s)
  restart, expected worker response, whether cancellation is accepted, renewal
  behavior, stop/copy plan.

**action**
1. Create `Jr1` for E1 and claim to obtain lease `Lr1`.
2. While `Jr1` is running and within TTL, restart the approved service(s).
3. Record before/after service identity, restart duration, worker log window
   (filtered by job/lease id).
4. Observe whether the worker cancels the provider, renews after restart, or
   loses the lease.
5. Stop the exact process tree if still running; run explicit `lease reap` if
   the lease is not already released.
6. Run `PRAGMA integrity_check`, `user_version`, FK violation count.

**evidence**
- Exact restart duration versus TTL/renew interval documented.
- Worker behavior (cancel/renew/lease-loss) matches pre-approved expectation.
- DB integrity `ok`, schema 13, FK violations 0.
- No duplicate/orphan lease rows for `Jr1`.

**pass-fail**
- Pass: behavior matches approved contract and DB consistent.
- Fail: behavior deviates from approved contract without documented stop gate,
  or DB integrity degrades.

**cleanup**
- Confirm zero active test leases, no orphan processes.

**rollback-stop**
- Capture a forensic copy and halt if contract violated or integrity fails.
  Whole-DB restore only via the incident gate.

## 7. Prerequisite gates

### P9-3C0 fixture gates (must close before P9-3C1)

1. **No-paid-provider quiet fixture** — identify or implement a runner profile
   and payload that creates a quiet, long-running job without paid provider
   invocation. Record exact profile id and payload path.
2. **Typed context/binding/worktree lease** — prove `coordinate job create`
   plus `coordinate runtime job claim` yields a typed execution context,
   binding, route evidence, and resource-key lease.
3. **Two capacity-1 executors** — confirm two distinct agent_ids each with
   `max_concurrent_jobs=1` in the deployed capacity policy.
4. **Exact process handle/stop/status** — identify or implement an auditable
   stop method for the exact provider process tree. Record exact helper/script.
5. **Scoped queue isolation** — prove the selected executor has no other
   pending/recoverable jobs and can be frozen from new submissions during the
   test window.
6. **Result review and deployment decision** — if any code/helper is
   implemented, it must pass result review and a deployment decision before use
   in P9-3C1.

### P9-3C1 production gates (must close after P9-3C0)

7. **Maintenance window / operator gate** — explicit approval for G0/G1 and
   defined stopped window; fresh backup taken immediately before any restart
   row.
8. **Global quiescence/intake guard** — exact preflight query and intake-freeze
   procedure prove no non-test nonterminal jobs or active leases before every
   mutating row; any drift stops the row before claim/reap/restart.
9. **Unique namespace and evidence ledger** — defined prefix and durable ledger
   path.
10. **Independent review** — this corrected plan must be reviewed and approved
   by someone other than the planning writer.

## 8. Test strategy and evidence rules

- Use only the installed production CLI for mutations; exact read-only SQLite
  queries are allowed for bounded evidence. No direct SQLite mutation.
- Record every command, job id, attempt token, lease id, timestamp, status
  transition, CLI exit code, and error class in the evidence ledger.
- Do not query/print job payload, prompt, result text, environment, credential,
  or user message fields.
- Use `coordinate runtime capacity list/show` for policy only; derive
  usage/resource evidence from `execution_attempt_leases` filtered by test
  agent/status/lease id.
- Reap evidence uses explicit `coordinate runtime job lease reap` result plus
  resulting rows. If an automatic reaper exists, it must be separately proven
  and cited; otherwise assume none.
- Capture `PRAGMA integrity_check`, `user_version`, and FK violation count
  before and after the matrix.
- Distinguish local lifecycle state from production event-plane state; event
  mirroring is not a prerequisite for lease correctness, and checklist
  projections do not prove event existence.

## 9. Rollback and halting conditions

Distinguish recovery options in order:

1. **Exact test-process termination** using the verified P9-3C0 helper.
2. **Bounded test-row state cleanup** through supported APIs (`job cancel`,
   `lease reap`, `job retry` only where appropriate).
3. **Code/service rollback** to the P9-3B deployed state if a helper/code change
   was deployed.
4. **Forensic stop/copy** — stop the affected service, copy DB/journal to a
   forensic path, investigate.
5. **Whole-DB restore** — last-resort incident operation only: requires fresh
   maintenance-window backup, explicit human gate, proof of no intervening
   writes, and a documented recovery decision.

Halting rules:

- Any DB integrity failure → halt, capture forensic copy, investigate; whole-DB
  restore only via incident gate.
- Any stale mutation accepted → halt, capture forensic copy; whole-DB restore
  only via incident gate.
- Any duplicate active lease for the same resource → halt, stop exact process
  trees, run explicit `lease reap`, capture forensic copy.
- Any real user job affected → halt immediately and escalate.
- Any P9-3C0 or P9-3C1 gate still open → do not execute the corresponding row.

## 10. Acceptance criteria

1. P9-3C0 fixture gates closed and recorded.
2. P9-3C1 production gates closed and recorded.
3. Core A–G semantics execute with command transcripts and DB-state evidence.
   Windows/Pad variants are optional and do not block acceptance.
4. Zero active test leases, zero running test jobs, zero orphan test processes,
   zero temp residue after cleanup.
5. DB integrity `ok`, schema 13, FK violations 0 after the matrix.
6. Stale attempt `N` mutations rejected for every post-recovery job;
   authoritative fields unchanged.
7. Independent reviewer approves the evidence and plan revision.
8. Durable measurement, plan, evidence ledger, and closeout present before P9-3
   stage closeout.

## 11. P9-3 stage handoff

P9-3C1 evidence feeds the P9-3 stage closeout. P9-4 provider observation and
P9-5 multi-line matrix remain out of scope.
