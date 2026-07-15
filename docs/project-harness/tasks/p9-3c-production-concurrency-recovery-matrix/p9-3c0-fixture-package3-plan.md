# P9-3C0 Package 3 — Isolated Sidecar Detailed Plan

> **Plan only.** This exact revision does not authorize implementation, deployment,
> transient-unit creation, fixture catalog sync, job/lease creation, or service
> restart. A fresh independent plan review must approve the committed plan revision;
> only then may a worker bootstrap be generated and independently reviewed.

## 1. Base, objective, and hard boundary

- MultiNexus planning base:
  `3cb0e4e1d52f205e532d44808b91448d1065feb2`.
- Deployed Package 2 code:
  `619aa0ec1c0d3a77d1ef0fe7ea03fd8332f8f93d`.
- Coordinate source/deployed dependency:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.
- Refreshed facts:
  `p9-3c0-fixture-package3-measurement.md`.

Package 3 will implement, deploy inertly, and then run one bounded production-host
isolated sidecar proof. It closes the fixture itself: two typed capacity-1 executors,
real 75-second quiet windows, automatic renewals, exact stop/cgroup cleanup, expiry,
explicit reap, recovery, stale-attempt rejection, and zero-provider/network evidence.

It must not modify or sync canonical `config/agent-registry.toml`, production
`agents.toml`, production executor/capacity sources, `/var/lib/coordinate/coord.sqlite3`,
or `/usr/local/bin/coord-local`; submit a real-provider request; restart a canonical
service; or authorize P9-3C1.

## 2. Gate sequence

The sequence is immutable:

1. commit this measurement and detailed plan only;
2. independent exact-revision plan review;
3. if approved, generate an exact worker bootstrap;
4. independent bootstrap review;
5. worker implementation in a clean worktree;
6. Codex result review and corrections;
7. merge/push and inert deploy of code/scripts only;
8. merged/deployed preflight with no fixture state;
9. operator executes the isolated sidecar;
10. operator writes closeout evidence;
11. independent Package 3 result/closeout review.

No later gate inherits approval from an earlier gate.

## 3. Exact implementation allowlist

The implementation worker may modify only:

- `multinexus/fixture/bin/p9-3c0-unit.sh`;
- `multinexus/fixture/docs/runbook.md`;
- `multinexus/agentd/__main__.py`;
- `scripts/p9-3c0-local-verify.sh` (new, executable);
- `scripts/p9-3c0-cleanup.sh` (new, executable);
- `tests/test_p9_3c0_fixture_assets.py`;
- `tests/test_p9_3c0_package3_scripts.py` (new);
- `tests/test_agentd_recovery_evidence.py`.

No Coordinate file, deploy script, canonical config, fixture executable, fixture
authority TOML, general adapter/worker implementation, or other test may change. If
the worker needs another path, it must stop for plan revision and re-review.

The execution/closeout operator may later add only Package 3 report/review documents
under the existing harness task directory and append the harness progress log.

## 4. Minimal runtime changes

### 4.1 Portable mandatory sandbox gate

Replace the unsupported `systemd-run --dry-run` probe. `render`/`preflight` must
generate an inert service definition inside the locked run state and execute
`systemd-analyze verify <exact-file>`. The definition includes the same mandatory
properties used for launch:

- `IPAddressDeny=any`;
- `RestrictAddressFamilies=AF_UNIX`;
- `NoNewPrivileges=yes`;
- `PrivateTmp=yes`;
- `ProtectSystem=strict`;
- `ProtectHome=yes`;
- exact `ReadWritePaths` state root;
- `KillMode=control-group`;
- `RuntimeMaxSec=300`, `TimeoutStopSec=30`, and `UMask=0077`.

Any parse warning/error, missing executable, or nonzero verifier result fails before
unit launch. After launch, the helper must continue comparing every effective value
using exact-unit `systemctl show`; mismatch forces exact stop and cgroup proof before
failure. Static verification is not a substitute for the post-start gate.

The generated verification file is ledger-listed, mode `0600`, state-root-contained,
and removed only by exact cleanup.

### 4.2 Recovery argument group

Extend `p9-3c0-unit.sh start` with these optional flags:

```text
--recoverable
--recovery-reason <bounded text>
--prior-process-stopped
```

All three must be present together. Normal start rejects either evidence flag without
`--recoverable`; recovery rejects missing, blank, control-character, or over-512-byte
reason and missing prior-process confirmation. The command is constructed as a Bash
array; no `eval` or shell interpolation. The ledger records recovery mode and a digest
of the reason, not unbounded input. Normal launches must still contain none of these
arguments.

Recovery uses a second validated run id and exact unit name while pointing to the same
isolated Coordinate DB. This preserves the original unit/cgroup ledger and avoids
reusing or guessing unit identity.

### 4.3 Opt-in renewal logging

Add `agentd --log-level {DEBUG,INFO,WARNING,ERROR}` with default `INFO`. Argument
parsing must occur before `logging.basicConfig`; invalid levels fail through argparse
before config load or worker creation. The fixture helper launches only Package 3
units with `--log-level DEBUG`, exposing the already-existing successful-renewal log.
Canonical agentd behavior remains INFO by default.

Tests must prove the default, DEBUG selection, invalid-value rejection, and unchanged
recovery evidence forwarding.

## 5. Sidecar state and wrapper contract

The verification scripts accept explicit absolute paths and validate a fixed
production-host state prefix:

```text
/var/tmp/multinexus-p9-3c0/<run-id>/...
```

They refuse `/var/lib`, `/opt`, home directories, the production DB, production
wrapper, symlink/resolved aliases of either, path traversal, wrong ownership/modes,
pre-existing unknown files, and run ids outside the helper's safe namespace.

Under the exclusive run lock, preparation creates:

- fresh isolated Coordinate DB;
- exact wrapper mode `0700` that executes
  `/opt/coordinate/.venv/bin/coordinate --db <isolated-db> "$@"`;
- isolated workspace/worktree and harness directories;
- rendered fixture agent config and separate context DB paths;
- evidence JSONL/ledger files mode `0600`;
- a monotonic phase state controlling `intake=open|frozen`.

The wrapper is a real regular file, not a symlink. Its embedded DB path is compared to
the rendered helper value before each mutation. No production DB is copied.

## 6. Preparation and authority order

The script must capture a read-only production baseline first: integrity/schema,
canonical source versions/hashes, job/lease counts, fixture counts, exact three
service states/MainPIDs/NRestarts, canonical config hashes, and absence of fixture
units/processes.

It then uses only the isolated wrapper:

1. initialize/migrate the fresh DB;
2. `workspace add p9-3c0-sidecar --path <work-dir> --harness-root <harness-dir>`;
3. `workspace host-profile set p9-3c0-sidecar --host-id <hostname> --workspace-path
   <work-dir> --harness-root <harness-dir> --coordinator-cli-path <wrapper>
   --coordinator-db-path <isolated-db>`;
4. register E1/E2 as exact `client-type=agentd` on that hostname and verify the
   automatically created same-id agentd runner profiles;
5. executor v1 disabled sync;
6. capacity v1 sync;
7. executor v2 enabled sync;
8. verify two enabled typed bindings and two capacity-1 policies, with no other
   agent/source/job/lease in the isolated DB.

Every authority input path and SHA-256 is compared to the reviewed deployed Package 2
asset before sync. Mutable TOML editing is forbidden.

## 7. Base quiet-renew scenario

Start exact E1/E2 normal units through the helper. Submit one exact request per agent
while `intake=open`. Each prompt is exactly this compact semantic object with
`spawn_descendant=false`:

```json
{"contract_version":1,"mode":"complete","quiet_seconds":75,"spawn_descendant":false}
```

Each request uses unique bounded `origin.message_id`, `origin.session_scope_id`, and
explicit idempotency key; origin/reply platform is `local-fixture` and destination is
the exact agent id.

The verifier captures exact job, attempt, lease, policy, binding, context, unit,
cgroup, and journal identities. While each job runs it polls the isolated DB read-only
and records every distinct `expires_at`; success requires initial expiry plus at least
two strictly later expiry values. The exact unit journal must independently contain at
least two successful renewal DEBUG records for that lease. Approximately 30/60-second
timing is checked with a documented scheduler tolerance; TTL and renew interval must
remain exactly 120/30.

Both jobs must become `done`, release their active leases, and report exact
`response_text="fixture complete"` plus matching executor/context evidence. Any first
byte before the 75-second boundary, timeout, failed result, missing renewal, or extra
provider/session identity fails closed.

## 8. Hold, intake freeze, exact stop, and cgroup proof

With E2 still running, submit one E1 request whose exact prompt changes only to
`mode="hold", spawn_descendant=true`. The verifier discovers its child solely from
the E1 unit's ledger-recorded cgroup and `/proc/<pid>/cmdline`, requires exactly one
reviewed fixture executable, and records monotonic milliseconds on first observation.

It then atomically changes the script ledger to `intake=frozen`; all subsequent submit
subcommands must refuse before Coordinate invocation. The already-submitted hold job
continues and renews. At target 80 seconds after the recorded child observation, call
the helper's exact E1 stop with both timing evidence fields. Accepted evidence is
`75000 <= elapsed < 85000` ms. Even early/late/invalid evidence must still stop the
exact unit, wait inactive, and prove the recorded cgroup absent or empty before
returning nonzero.

After E1 stop:

- E2 exact unit remains active until deliberately stopped;
- the three canonical services retain their baseline MainPID/NRestarts and active
  state;
- production DB/config fingerprints remain unchanged;
- no wildcard unit command, `pkill`, `pgrep`, guessed PID, or direct DB write occurs.

## 9. Expiry, reap, recovery, and stale attempt

Record hold attempt N's exact lease/token and latest `expires_at`. Stop E2 and prove
both base cgroups empty. Wait using wall-clock comparison until strictly past the
recorded UTC expiry; do not shorten TTL or mutate timestamps.

Before the global reap, prove isolated global quiescence: no running agentd unit,
no non-fixture identity, no other active lease, and no other pending/running job. The
global operation is safe because its DB is the isolated DB. Invoke exactly one
`runtime job lease reap`, require only N to become expired and its job to become
`timed_out+recoverable`, and preserve its expiry event.

Render a second run namespace against the same isolated DB and start exact E1 with:

```text
--recoverable
--recovery-reason p9-3c0-expired-after-exact-unit-stop
--prior-process-stopped
```

Require attempt N+1, a new lease id/token, previous status `timed_out`, and recovery
evidence in `job.claimed`. Only after N+1 exists, send one exact old-N report using the
old lease/token. It must fail nonzero and leave N+1/job/lease state unchanged.

The recovered prompt remains `hold`, so stop the recovery unit exactly (no hold-timing
claim is needed), prove its cgroup empty, wait past N+1 expiry, and reap once more under
the same quiescence gate. Final recovery-row state may be `timed_out+recoverable`; it
must not be described as completed. Package success's “two completed jobs” refers to
the two base complete-mode jobs.

## 10. Cleanup and retained evidence

`scripts/p9-3c0-cleanup.sh` is idempotent and accepts only a fully ledgered state. It
must refuse while intake is open, a fixture unit/cgroup survives, a pending/running
job exists, or any active lease exists. Cleanup order is fixed:

1. verify `intake=frozen`;
2. drain/expire/reap authorized fixture attempts;
3. exact stop/status/cgroup proof for every ledger unit;
4. executor v3 disabled sync;
5. capacity v2 empty sync;
6. executor v4 empty sync;
7. verify zero fixture bindings/definitions/policies/sources and no active lease;
8. run helper exact cleanup for each ledger unit;
9. capture final isolated DB and production read-only snapshots.

Because Coordinate has no unregister commands, the isolated DB may retain exactly two
dormant fixture agents and two same-id runner profiles. They must have no binding,
capacity policy, active unit, pending/running job, or active lease. The isolated DB,
wrapper, ledgers, journals, hashes, and report inputs remain mode-restricted under the
state root until closeout review; cleanup must not delete SQLite rows or the evidence
root directly.

## 11. Zero-provider/network proof

Primary evidence for every exact unit:

- `systemd-analyze verify` success before launch;
- post-start `systemctl show` equality for every mandatory sandbox property;
- `IPAddressDeny=any` and `RestrictAddressFamilies=AF_UNIX` effective;
- agentd environment from the exact unit contains only the approved minimal PATH;
- fixture child `/proc/<pid>/environ` contains only the expected minimal inherited
  fields such as PATH/PWD and no provider, Discord, KOOK, proxy, home, or cloud key;
- exact child cmdline resolves to the reviewed fixture executable and contains no
  provider/model/resume/dangerous flag;
- production provider/service logs and canonical DB show no fixture identity.

Packet capture is optional supplemental evidence only. A missing/unsupported runtime
sandbox property fails the entire run; packet capture cannot waive it.

## 12. Tests and validation gates

Worker validation, with no real systemd/SSH/provider/DB mutation:

- focused Package 2/3 fixture and script tests;
- agentd recovery/log-level tests;
- adjacent agentd execution-context, binding, lease, recovery, Claude adapter, config,
  authority, and deploy-contract tests;
- `bash -n` on all three fixture/Package 3 shell scripts;
- `python -m compileall` for changed Python;
- full MultiNexus pytest suite;
- exact allowlist/mode/diff and clean-worktree checks.

Tests must inject fake `systemctl`, `systemd-analyze`, Coordinate wrapper, monotonic
clock, `/proc`/cgroup reader, journal, and read-only snapshot data. They cover success
and fail-closed cases for unsupported directives, post-start mismatch, recovery flag
grouping, wrong DB/wrapper/path, unknown files, early/late timing, ambiguous child PID,
renewal evidence count, stale report unexpectedly accepted, cleanup ordering, active
lease, production drift, and interrupted rerun.

Merged-main validation repeats focused, adjacent, full, shell, compile, and diff gates.
Deployment then copies the reviewed scripts inertly. Before sidecar execution, SHA/mode
parity and the Package 2 inert production snapshot must pass again.

## 13. Stop conditions and rollback boundary

Immediately stop exact ledger units and preserve evidence if any of these occurs:

- production DB/config/source/service fingerprint changes;
- canonical service restart, failure, or PID change;
- a fixture id appears in production DB/canonical config;
- a real provider binary, credential, proxy, or network-capable address family appears;
- sandbox parse/effective-property mismatch;
- ambiguous/missing cgroup child identity;
- wrong TTL/renew interval, missing two renewals, first-byte timeout, or non-exact result;
- stale N report is accepted or mutates N+1;
- catalog order/ownership/active-lease guard fails;
- any required cleanup cannot prove exact cgroup emptiness.

Rollback is scoped to the isolated sidecar: freeze intake, stop only exact ledger units,
reap only through the isolated wrapper after recorded expiry/quiescence, and execute the
reviewed cleanup catalog order. Never repair with direct SQLite writes/deletes, wildcard
process commands, canonical service restart, or production source mutation.

## 14. Success and closeout

Package 3 succeeds only if:

- both complete-mode typed jobs finish with exact `fixture complete`;
- each proves at least two real 30-second renewals during the 75-second quiet window;
- hold stop timing, exact unit status, and cgroup/descendant cleanup pass;
- expiry/reap/recovery creates N+1 and old-N stale report is rejected;
- no paid provider, credential, or non-AF_UNIX network path is available;
- final isolated catalogs are empty with only documented dormant agent/runner and
  timed-out recovery evidence allowed;
- production DB/config/source/service fingerprints are unchanged;
- cleanup and rerun-safety checks pass;
- an independent reviewer approves the exact implementation/execution evidence.

This closes P9-3C0 only. P9-3C1 production catalog activation remains blocked and
requires a new exact-revision plan, bootstrap, and authorization.
