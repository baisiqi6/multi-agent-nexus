# P9-3C0 Package 3 — Isolated Sidecar Measurement

Measured on 2026-07-15 before any Package 3 implementation or fixture execution.
This document is evidence only; it does not authorize a catalog sync, transient
unit, isolated job/lease, service restart, or production activation.

## Exact revisions and host

- MultiNexus source/planning head: `3cb0e4e1d52f205e532d44808b91448d1065feb2`.
- MultiNexus code deployed on `kook-hermes-admin`: `619aa0ec1c0d3a77d1ef0fe7ea03fd8332f8f93d`.
- Coordinate source and deployed dependency:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.
- Host: `VM-0-15-ubuntu`, systemd `255 (255.4-1ubuntu8.15)`.
- Deployed fixture executable:
  `/opt/multinexus/multinexus/fixture/bin/p9-3c0-fixture.py`, mode `0755`.
- Deployed Coordinate entrypoint: `/usr/local/bin/coord-local`, version
  `coordinate 0.1.0`.

The production DB was opened with SQLite URI `mode=ro`. It reported integrity
`ok`, schema `13`, one executor source, one capacity source, zero pending/running
jobs, zero active leases, and zero fixture agents/runners/jobs/leases. Exact fixture
unit and process counts were also zero.

Production service names are:

- `coordinate.service`;
- `multinexus-discord-bridge.service`;
- `kook-nexus-hermes.service`.

All three were active/running with `NRestarts=0` at measurement time. The shorthand
`multinexus-discord.service` is not the deployed unit name and must not be used by
Package 3 evidence checks.

## Current runtime facts

1. `coordinate --db <new-path> ...` creates the parent directory, opens SQLite,
   and migrates a fresh isolated DB automatically. No production snapshot copy is
   required or allowed.
2. A non-task exact request requires:
   - a registered workspace;
   - a host profile for the target agent's exact `host_id`;
   - `origin.platform`, `origin.destination`, and
     `origin.session_scope_id`;
   - `reply.platform` and `reply.destination`;
   - either `origin.message_id` or an explicit idempotency key.
3. `runtime agent register --client-type agentd` automatically creates a same-id
   `runner_type=agentd` profile when absent. The Package 2 runbook preview's
   `runner add ... --runner-type agent` placeholder is therefore both unnecessary
   and inconsistent with typed executor validation.
4. Executor catalog sync requires the two runtime agents and their agentd runner
   profiles to exist before the disabled binding source is staged.
5. The accepted lease constants remain TTL `120` seconds and renewal interval `30`
   seconds. A typed claim requires the exact workspace host profile, executor
   binding snapshot, and capacity policy.
6. `agentd` writes the exact request prompt to the Claude adapter child's stdin.
   Therefore the prompt for the fixture must be the complete strict control JSON,
   not an ellipsis, file reference, or prose wrapper.
7. A recovery-mode agentd already accepts and forwards
   `--recoverable --recovery-reason ... --prior-process-stopped`. With no provider
   session id (the fixture intentionally emits none before the crash), recovery
   performs a fresh adapter call for attempt N+1. Once N+1 exists, an old N
   token/lease report is rejected by Coordinate's stale-attempt gate.
8. Coordinate has no runtime-agent/runner unregister command. The isolated DB may
   retain dormant namespaced rows for evidence. Direct SQLite writes/deletes remain
   forbidden.

## Gaps between Package 2 assets and a real Package 3 run

### 1. The current systemd capability probe cannot run on the measured host

`p9-3c0-unit.sh` calls `systemd-run --dry-run ...`. The measured systemd 255
`systemd-run` rejects that option with:

```text
systemd-run: unrecognized option '--dry-run'
```

The manager does expose `IPAddressDeny`, `RestrictAddressFamilies`,
`ProtectSystem`, `ProtectHome`, `PrivateTmp`, `NoNewPrivileges`, `KillMode`, and
`RuntimeMaxUSec` through `systemctl show`. Package 3 needs a portable two-stage
gate: parse a generated inert service definition with `systemd-analyze verify`
before launch, then verify every effective property on the exact started unit.
No unsupported-property downgrade is acceptable.

### 2. The helper cannot start the required recovery unit

The current `start` command always launches normal agentd and explicitly contains no
`--recoverable` argument. Package 3 needs a fail-closed, array-based recovery option
group that accepts all three evidence fields together or none of them.

### 3. Successful renewals are not visible at the default log level

`AgentdWorker._renewal_supervisor` already logs every accepted new deadline, but at
DEBUG. `agentd.__main__` fixes the process logger at INFO and exposes no log-level
override. DB polling can independently observe deadline changes, but the parent plan
also requires agentd log evidence. Package 3 therefore needs an opt-in DEBUG launch
for fixture units while leaving the normal default at INFO.

### 4. The existing ledger does not prove the fixture child start boundary

The helper records monotonic time before `systemd-run`, which is earlier than the
adapter child's stdin/start boundary. Its `stop` command correctly accepts an external
`--fixture-start-monotonic-ms`, but Package 3 currently has no reviewed producer for
that value. Polling the exact ledger-recorded cgroup can prove PID/cmdline identity but
occurs after the adapter timer starts and is not a valid timing anchor. The adapter
must expose the exact monotonic value used by its first-byte timer; cgroup observation
then cross-checks the recorded PID only. Neither path may use `pgrep`, wildcard unit
names, or a guessed PID.

### 5. Queue freeze and real-executor non-interference need an honest boundary

The Package 3 DB is fresh and contains only fixture identities, so it has no real
executor queue to exercise. Submitting a paid real-provider request merely to prove
non-interference would contradict the zero-provider objective. The valid proof is:

- an exclusive, ledgered fixture intake state that refuses further submissions;
- already-submitted fixture work continues under its lease;
- read-only production DB/source/service fingerprints are byte-for-byte or
  field-for-field unchanged before and after the sidecar run.

This proves isolation without claiming a paid production request was sent.

### 6. System unit privilege and isolated-state ownership are not yet defined

The deployed helper invokes the system manager, while its transient unit sets a
non-root `User=`/`Group=`. Running the whole helper as that user may fail system-manager
authorization; running everything as root would create an isolated DB/config tree the
unit user cannot safely write/read. Package 3 therefore needs an explicit privilege
split: root-only controller and systemd/cgroup/journal operations, a root-owned
non-replaceable wrapper, and Coordinate/DB/work/context operations executed as the
exact non-root unit user.

### 7. The adapter has no machine-readable first-byte clock anchor

`ClaudeAdapter._run` sets `last_activity = loop.time()` before writing stdin and uses
that value for the first-byte timeout. It does not currently log or export the value.
The later appearance of a fixture PID in the unit cgroup proves identity but cannot
reconstruct this earlier clock exactly. Package 3 needs an opt-in DEBUG record carrying
the same monotonic value and child PID, without emitting provider stdout/progress or
changing the default production log level.

## Resulting Package 3 boundary

Package 3 is a production-host **isolated sidecar**, not production runtime
activation:

- fresh DB, wrapper, work directory, context DBs, evidence, and locks all live under
  one approved `/var/tmp/multinexus-p9-3c0/...` state root;
- the generated wrapper always injects the isolated `--db` before Coordinate
  subcommands and must not be a symlink to `/usr/local/bin/coord-local`;
- production DB and canonical configs are read-only evidence inputs only;
- fixture sources sync only into the isolated DB;
- exact transient units use the deployed fixture assets but never canonical agent
  config or provider credentials;
- P9-3C1 production catalog activation remains a separate blocked gate.
