# P9-3C Plan Review — Round 1

Reviewer: Codex architect/operator  
Date: 2026-07-14  
Verdict: **changes requested; no production authorization**

- Reviewed plan SHA-256:
  `f4b15bbfd95db1991e217047f42090ef253da245fc3a5df0a470f63b7cf52c09`.
- Reviewed measurement SHA-256:
  `742b55c649c2124ecac77ccf73c20b71dd8ebdb08fe59844e7fc84b70864ffbf`.
- Both hashes were independently recomputed before review.

## Must-fix findings

### 1. [P0] Whole-production-DB restore is an unsafe default rollback

Evidence: plan Rows A/B/F and section 8 direct the Operator to restore the P9-3B
backup on capacity inconsistency, duplicate resource lease, stale mutation, or DB
integrity failure. That backup predates the P9-3C window and therefore also predates
any legitimate production events, tasks, deliveries, and audit history created after
P9-3B.

Failure mode: a test assertion failure can trigger a blind replacement of the live DB
with an older copy, silently deleting unrelated post-backup production state. A stale
mutation being accepted is not undone safely by restoring a database that may be hours
old.

Required change: distinguish (a) exact test-process termination, (b) bounded test-row
state cleanup through supported APIs, (c) code/service rollback, (d) forensic copy and
service stop, and (e) whole-DB restore as a last-resort incident operation requiring a
fresh maintenance-window backup, explicit human gate, proof of no intervening writes,
and a documented recovery decision. No ordinary matrix failure may automatically
authorize whole-DB replacement.

### 2. [P1] Row B cannot prove different-worktree concurrency with one capacity-1 executor

Evidence: plan section 4 selects one `EXECUTOR`; Row B claims `J1/W1` and `J2/W2`
concurrently through that same executor. Every deployed policy has
`max_concurrent_jobs=1`. Coordinate checks agent capacity before resource selection in
`runtime_lease.py::select_claim_candidate` (current lines 622-632), so the second claim
must return `capacity_exhausted` before worktree identity is considered.

Failure mode: the expected `L1 + L2` concurrent state is unreachable. The row would
misclassify correct capacity enforcement as a resource-concurrency failure.

Required change: define a reviewed two-executor fixture with both capacities fixed at
1, and use `E1/W1`, `E2/W2` for different-worktree concurrency plus `E1/W1`, `E2/W1`
for cross-executor same-worktree exclusion. If no zero-cost two-executor fixture exists,
make that a P9-3C0 implementation prerequisite and block the production matrix. Do not
mutate the deployed capacity catalog ad hoc inside the experiment.

### 3. [P1] The plan lacks an executable zero-cost runtime fixture and contradicts its own scope

Evidence: section 2 says “No new Coordinate or MultiNexus implementation”, while
measurement gates 1-3 and plan section 6 allow an unspecified quiet runner, exact
process-tree stop helper, and typed `job create` proof. A generic `job create` sets the
agent from the runner profile, but P9-3B claim also validates a typed execution context,
binding, route evidence, and resource key. `runtime job claim` accepts only
`--agent-id`; it cannot target a job id (`execution_cli.py` current lines 236-256).

Failure mode: production execution starts before anyone has proven that the created
job reaches the managed MultiNexus path, receives a typed worktree lease, remains quiet,
and exposes an exact kill handle. Operators then improvise payloads or process commands
on production.

Required change: split the work into an explicit P9-3C0 local/sidecar prerequisite and
P9-3C1 production matrix. P9-3C0 must either identify an existing no-provider fixture or
implement the smallest test-only/sidecar adapter and exact stop/status helper, with
tests, result review, deployment decision, and a revised exact plan review. P9-3C1
remains blocked until the fixture contract is named and proven.

### 4. [P1] Row C can accidentally test manual renewal instead of worker renewal

Evidence: Row C action requires the worker to renew automatically, but its evidence
lists success of `coordinate runtime job lease renew`. The automatic behavior under
test is `AgentdWorker._renewal_supervisor`, started independently of provider progress
in `multinexus/agentd/worker.py` current lines 409-443 and renewing at lines 541-625.
Defaults are TTL 120 seconds and renew interval 30 seconds; worker safety margin is 5
seconds.

Failure mode: an Operator-issued CLI renew makes the lease advance even if the worker
heartbeat loop is dead, creating a false pass.

Required change: forbid manual renew during the observation window. Record pre/post
lease timestamps and bounded worker/service logs keyed only by test job/lease id; prove
no progress event/output occurred and at least two automatic expiry advances happened.
Activity remains liveness evidence, not correctness or completion. Manual renew may be
used only as an explicitly labelled cleanup/emergency action and invalidates this row.

### 5. [P1] Row G conflates restart, renewal transport failure, crash, and reap

Evidence: Row G restarts only `coordinate.service` while an active worker is renewing,
then separately kills the provider and expects timeout/reap. The worker treats any
renew transport error as authoritative lease loss and cancels the provider immediately
(`worker.py` current lines 590-601); the plan has no measured restart duration versus
30-second interval, 120-second TTL, or client error behavior. `NRestarts` is a systemd
automatic-restart counter, not proof that an Operator `systemctl restart` occurred.

Failure mode: normal brief downtime can intentionally cancel the job, or a restart row
can pass only because the later crash/reap path masks what happened during restart.

Required change: split restart into (G0) no-active-lease service restart/integrity and
(G1) active quiet-lease restart only after a measured timing/failure contract is
approved. G1 must state which service(s) restart, expected worker response, exact
before/after service identity (`ActiveEnterTimestamp`, main PID, journal window),
renewal behavior, and whether cancellation is the accepted result. Do not combine G1
with the crash row, and do not require `NRestarts` to increment for a manual restart.

### 6. [P1] Recovery cannot claim a named job without queue isolation

Evidence: Rows D/E refer to reclaiming `Jc`, but `runtime job claim --recoverable`
selects the oldest matching recoverable job for an agent; the CLI has no job-id
argument. Selection is ordered by `created_at,id` and bounded by scan limit in
`runtime_lease.py::select_claim_candidate` (current lines 606-617).

Failure mode: another recoverable job for the chosen executor can be claimed as attempt
`N+1`, while the evidence is attributed to `Jc`.

Required change: preflight must prove the selected disposable executor has no other
pending/recoverable jobs; freeze new submissions for that test executor during the
window; verify the returned job id equals `Jc` before any provider launch; otherwise
stop and cleanup. If that isolation cannot be guaranteed, P9-3C0 needs a scoped claim
surface rather than a production guess.

### 7. [P1] Several evidence fields are not exposed by the named CLI

Evidence: Rows A/B expect `runtime capacity show` to report usage 0/1 or 1/1. The
handler returns only `{agent_id, policy}` (`execution_cli.py` current lines 96-104).
The draft also assumes an automatic reaper timer merely because
`coordinate.service` is active, but the verified installed surface only proves the
explicit `runtime job lease reap` command.

Failure mode: an Operator either cannot collect the acceptance evidence or invents a
query/field during production execution.

Required change: enumerate exact read-only evidence queries derived from the live
schema: policy from `capacity show`, active usage from counts in
`execution_attempt_leases` filtered by the test agent/status, resource concurrency from
test lease ids/resource keys, and reap from the explicit CLI result plus resulting
rows. If an automatic reaper exists, cite and separately prove its deployed scheduler;
otherwise remove the timer claim.

### 8. [P1] The matrix job invariant and acceptance set are internally inconsistent

Evidence: section 3 says every row creates exactly one disposable job. Row A creates
two, Row B three, and Rows D/E/F intentionally share one job/attempt history. Section 9
allows “A-G (or the subset permitted by verified executors)”, which can skip required
P9-3 capacity/recovery proofs without defining a mandatory core.

Failure mode: cleanup accounting and acceptance can declare success despite missing a
required concurrency/recovery row.

Required change: replace the one-job rule with a bounded matrix ledger and explicit
maximum counts. Define A-G core semantics as mandatory, allowing Windows/Pad host
variants to be optional only. D/E/F must be one chained scenario with one job id and
attempts N/N+1; each other row must list its exact job/process/temp-file budget.

## Should-fix findings

1. Correct both document dates from `2026-07-15` to the measured local date
   `2026-07-14` (Asia/Shanghai).
2. Row F should require zero authoritative job/lease mutation, not necessarily zero
   audit events unless current code proves failed requests append none. Record error
   class/exit status and compare bounded before/after job/lease fields.
3. Define an explicit zero paid-provider-call budget for P9-3C0/P9-3C1. If a real
   provider is unavoidable, state provider, maximum calls/tokens/wall time, quota stop,
   and require a new human gate.
4. Define one durable evidence ledger path, per-row idempotency keys, exact namespace,
   before/after counts, and a final cleanup manifest. Never print payload, prompt,
   result text, environment, or user message content.
5. Record the local lifecycle versus production event-plane boundary as evidence, but
   do not make event mirroring a prerequisite for lease correctness or claim that a
   checklist projection proves an event exists.

## Verified strengths

- The draft correctly excludes P9-4 provider observation and P9-5 multi-line/provider
  orchestration.
- It preserves audit rows instead of defining “zero residue” as history deletion.
- It recognizes Windows real process-tree behavior as unverified.
- It includes stale N fencing, explicit N+1 recovery, exact lease identity, integrity,
  FK, service, and cleanup checks as separate concerns.
- The production baseline and installed nested `lease renew/reap` spelling are
  accurately recorded.

## External reviewer attempts

- Exact `zhipu-coding-plan/glm-5.2` session
  `019f620e-d7bf-7000-b9b5-6f4970f6ca79` produced no file reads or verdict within the
  bounded window and was stopped; it is not an approval.
- A separate Claude Sonnet-routed `kimi-for-coding` review independently recomputed the
  hashes and inspected relevant code, but did not emit a final report within its
  bounded window and was stopped; it is not an approval.

## Scope and authorization verdict

Draft revision 1 is rejected for production execution. The next allowed action is a
planning correction only: revise measurement/plan to close every must-fix, then submit
the new exact SHA to a fresh independent review. Do not register the checklist item,
generate a production/coding bootstrap, create disposable jobs, change capacity, or
restart services before that approval.
