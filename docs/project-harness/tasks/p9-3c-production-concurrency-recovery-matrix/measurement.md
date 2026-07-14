# P9-3C Production Concurrency/Recovery Matrix — Measurement

Status: draft correction incorporated; production execution blocked pending P9-3C0
fixture closure and independent review.
Date: 2026-07-14 Asia/Shanghai

## Revisions and service state

- Measurement captured as input to a draft plan, not authorization for production
  mutation.
- Reviewed plan SHA-256 and measurement SHA-256 recorded in
  `plan-review-round1.md`; verdict: changes requested, no production authorization.
- Coordinate main/upstream/deployed implementation:
  `3eaa7bfdeb0f660da46bd7fe6003231822c9658c`.
- MultiNexus main/upstream/doc deployment head:
  `e925dab5524de93304d33f3a83b544c0802e3e53`; P9-3B code integration merge
  `6bc1adfd30fc46911e320f52506b9d50f0032663`.
- `coordinate.service` and `multinexus-discord-bridge.service`: both active;
  `NRestarts=0` for both.
- Latest P9-3B backup:
  `/var/lib/coordinate/backups/coord.sqlite3.p9-3b.20260714T184701Z`, mode 600,
  SHA-256 `5a6e3faae9593ad8f152d1d15034174a78280b7ee4f20ab83e5ba7c89b5ddf3b`,
  integrity `ok`.

## Production DB

- DB: `/var/lib/coordinate/coord.sqlite3`.
- `PRAGMA user_version`: 13. There is no `schema_version` table.
- `PRAGMA integrity_check`: `ok`; P9-3B final FK violations: 0.
- Jobs: 151 `done`, 20 `failed`; no pending/running/timed_out rows.
- `execution_attempt_leases`: no rows; active/total `0/0`.
- Relevant real tables include `jobs`, `execution_attempt_leases`,
  `executor_capacity_policies`, `events`, `runner_profiles`, `tasks`.

## P9-3C0 fixture contract (local/sidecar prerequisite)

P9-3C0 must close before P9-3C1. All items below are `unverified` as of this
measurement. If any item cannot be satisfied by an existing configuration, it
requires a separate implementation plan, result review, deployment decision, and
updated plan review; this plan does not authorize new code.

1. **No-paid-provider quiet fixture** — `unverified`
   A runner profile and job payload that produces a quiet, long-running job
   without invoking a paid external provider. Must remain `running` with no
   progress/output for at least two automatic renewal intervals.

2. **Typed context/binding/worktree lease** — `unverified`
   Proof that `coordinate job create` plus `coordinate runtime job claim` yields
   a typed execution context, binding, route evidence, and resource-key lease
   without relying on bridge payload fields.

3. **Two capacity-1 executors** — `unverified`
   Two distinct agent_ids each with `max_concurrent_jobs=1` in the deployed
   capacity policy, available on the same local/sidecar host.

4. **Exact process handle/stop/status** — `unverified`
   An auditable method to stop the exact provider process tree and verify its
   termination, without `pkill` or guessed PID.

5. **Scoped queue isolation** — `unverified`
   Ability to confirm the selected executor has no other pending/recoverable
   jobs and to freeze new submissions for that executor during the test window.

## P9-3C1 production matrix scope

- Core semantics:
  - capacity saturation/release (A),
  - cross-executor worktree concurrency/exclusion (B),
  - automatic quiet renewal (C),
  - chained stop/expiry/reap/recovery/stale-rejection (D/E/F),
  - zero-active-lease restart integrity (G0),
  - active quiet-lease restart contract (G1, gated).
- A–G core semantics are mandatory; Windows/Pad variants are optional only.
- Bounded ledger: max 8 distinct jobs, ≤2 concurrent fixture processes,
  ≤12 total processes, zero paid-provider calls.
- Namespace prefix and evidence ledger path must be defined before execution.

## Capacity/executor authority

- Capacity source `multinexus.discord.capacity`, version 1, catalog hash
  `3c5b31d17424f3dc12b56d5e0d545f5a46b7d212193465d79c874cb82a9a918d`.
- Eight policies: `mac-claude`, `mac-codex`, `mac-omp`, `mac-opencode`,
  `pad-jarvis`, `win-claude`, `win-openclaw`, `win-opencode`; each currently has
  `max_concurrent_jobs=1`.
- Executor catalog source `multinexus.discord`, version 2, hash
  `f4cdf79897755c173e97ddae1dfd88047436039f3447d4d6257105715ba5551d`.
- P9-3C1 requires two capacity-1 executors from the P9-3C0 fixture. Windows/Pad
  availability is optional and unverified.
- `coordinate runtime capacity show <agent>` returns only `{agent_id, policy}`.
  Active usage and resource concurrency must be derived from
  `execution_attempt_leases` filtered by test id/agent/status, not from
  `capacity show`.

## Real installed CLI surface

Top-level runtime job:

```text
coordinate runtime job {claim,report,progress,lease}
coordinate runtime job lease {renew,reap}
```

The spelling is nested `lease renew` / `lease reap`, not `lease-renew`.

```text
coordinate runtime job claim --agent-id AGENT_ID
  [--recoverable --recovery-reason REASON --prior-process-stopped]

coordinate runtime job report JOB_ID --agent-id AGENT_ID
  --status {done,failed,timed_out} --result-json RESULT_JSON
  [--attempt-token TOKEN] [--lease-id LEASE_ID] [--actor ACTOR]

coordinate runtime job progress JOB_ID --agent-id AGENT_ID
  [--stage STAGE] [--summary SUMMARY] [--session-id SESSION]
  [--attempt-token TOKEN] [--lease-id LEASE_ID] [--actor ACTOR]

coordinate runtime job lease renew JOB_ID --agent-id AGENT_ID
  --attempt-token TOKEN --lease-id LEASE_ID [--actor ACTOR]

coordinate runtime job lease reap [--actor ACTOR] [--batch-size N]
```

Job management:

```text
coordinate job create WORKSPACE_ID --runner-profile-id PROFILE
  [--task-id ID] [--prompt-path PATH] [--branch BRANCH]
  [--worktree-path PATH] [--terminal-session-id ID]
  [--logs-path PATH] [--result-path PATH]
  [--timeout-seconds N] [--payload-json JSON]
coordinate job list [--workspace-id ID] [--status STATUS]
coordinate job cancel JOB_ID [--reason REASON]
coordinate job retry JOB_ID [--reason REASON]
```

Capacity inspection is `coordinate runtime capacity {sync,list,show}`; P9-3C1
uses `list/show` for policy only, not `sync`, during preflight/evidence.

## P9-3B accepted behavior and boundaries

- A managed claim atomically reserves capacity/worktree and returns a strict
  execution lease envelope. Managed report/progress/renew require exact agent,
  attempt token, and lease id; stale identities fail closed.
- The MultiNexus worker runs renewal independently of provider output and owns
  provider process groups; lease loss triggers cancellation and awaited cleanup.
- Reap is the expiry authority and makes a job recoverable; explicit recovery
  requires `--recoverable`, audited reason, and `--prior-process-stopped`.
- Local tests prove these contracts, POSIX process-tree cleanup, and Windows API
  calls. P9-3C1 must obtain runtime production evidence using disposable jobs.
- P9-4 provider-native JSONL/liveness and P9-5 multi-line/provider matrix are
  excluded.
- P9-3B local lifecycle events were not mirrored to the production event store.
  P9-3C1 evidence must distinguish local lifecycle state from production
  event-plane state and must not assume lifecycle events are mirrored.

## Unresolved/unverified surfaces blocking production matrix execution

All are `unverified` until this measurement is updated with focused proof.

1. **P9-3C0 fixture contract** — all five sub-items above unverified.
2. **Global quiescence/intake guard** — `unverified`; P9-3C1 must prove there are
   no non-test nonterminal jobs or active leases before each mutating row and must
   prevent new submissions to E1/E2 for the bounded window. The global reap command
   must never be treated as test-id scoped.
3. **Maintenance window / operator gate** — unverified for G0/G1 restart rows.
4. **Unique namespace and evidence ledger** — unverified.
5. **Independent review of corrected plan** — unverified.
