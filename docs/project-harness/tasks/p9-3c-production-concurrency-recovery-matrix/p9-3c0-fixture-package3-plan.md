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

Round 1 reviewed exact revision `2e91e6c` and returned `REQUEST_CHANGES`; see
`p9-3c0-fixture-package3-plan-review-round1.md`. That verdict authorizes no bootstrap.
This revision incorporates the accepted findings and explicitly rejects the impossible
requirement to mark a runtime-agent row offline: Coordinate exposes no such transition,
and the row is not process-liveness authority.

## 3. Exact implementation allowlist

The implementation worker may modify only:

- `multinexus/fixture/bin/p9-3c0-unit.sh`;
- `multinexus/fixture/docs/runbook.md`;
- `multinexus/agentd/__main__.py`;
- `multinexus/adapters/claude.py`;
- `scripts/p9-3c0-local-verify.sh` (new, executable);
- `scripts/p9-3c0-cleanup.sh` (new, executable);
- `tests/test_p9_3c0_fixture_assets.py`;
- `tests/test_p9_3c0_package3_scripts.py` (new);
- `tests/test_agentd_recovery_evidence.py`;
- `tests/test_claude_adapter.py`.

No Coordinate file, deploy script, canonical config, fixture executable, fixture
authority TOML, other adapter/worker implementation, or other test may change. If
the worker needs another path, it must stop for plan revision and re-review.

The runbook change is restricted to replacing the unauthorized Package 3 preview with
the finally reviewed Package 3 execution/cleanup contract. The Package 2 inert-deploy,
P9-3C1, and forbidden-operation sections may not be weakened or rewritten.

The execution/closeout operator may later add only Package 3 report/review documents
under the existing harness task directory and append the harness progress log.

## 4. Minimal runtime changes

### 4.1 Portable mandatory sandbox gate

Delete the unsupported `systemd-run --dry-run` branch completely; it must not remain
reachable or appear in the helper. `render`/`preflight` must instead
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
unit launch. `systemd-analyze verify` is the only static pre-launch capability gate.
After launch, the helper must query the exact unit using canonical `systemctl show`
property names and property-specific semantic normalization:

- `RuntimeMaxUSec` parses to exactly `300000000` microseconds;
- `TimeoutStopUSec` parses to exactly `30000000` microseconds;
- `KillMode` is exactly `control-group` and `UMask` is octal `0077`;
- `NoNewPrivileges`, `PrivateTmp`, and `ProtectHome` normalize to true;
- `ProtectSystem` normalizes to `strict`;
- `ReadWritePaths` tokenizes to one canonical real path equal to the approved state
  root, with no additional writable path;
- `RestrictAddressFamilies` is a positive allow-set containing only `AF_UNIX` (a
  complement/`~` set is rejected);
- `IPAddressDeny` semantically covers all IPv4 and IPv6 addresses: accept only the
  manager's `any` form or its complete canonical `0.0.0.0/0` plus `::/0` expansion;
  an empty, partial, unparsable, or additional allow result is rejected.

The normalizer must accept systemd 255 display encodings such as human duration
strings while comparing the canonical values above; it must not use one literal input
string for every property. Any unknown encoding or mismatch forces exact stop and
cgroup proof before failure. Static verification is not a substitute for this
post-start semantic gate.

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
recovery evidence forwarding. They must also load every deployed launch surface that
starts `python -m multinexus.agentd` (launchd/systemd/NSSM templates or their generated
argv fixtures), invoke the equivalent existing argv with no `--log-level`, and prove
config load plus worker startup still receive INFO. No canonical service definition is
changed, and inert deployment must not restart any service.

### 4.4 First-byte clock evidence seam

In `ClaudeAdapter._run`, retain the exact `loop.time()` value assigned to
`last_activity` immediately before stdin write. When DEBUG is enabled, emit one
bounded structured log containing:

```text
claude_child_boundary monotonic_ns=<integer> pid=<integer>
```

`monotonic_ns` is derived from that same `last_activity` value, not a later clock read.
The first-byte timeout must continue to use the same value. The record contains no
prompt, environment, cwd, credential, session id, or provider output; it must not call
the progress callback or write child stdout/stderr. Tests freeze the loop clock and
prove byte-for-byte that the logged boundary equals the timer anchor and precedes the
stdin write.

The verifier correlates this one record with the preceding exact-unit `Processing job`
record, its PID in the ledger-recorded cgroup, and the reviewed fixture cmdline. A
missing, duplicate, malformed, wrong-PID, or wrong-order boundary fails closed. Later
cgroup observation is identity/environment evidence only and is never the timing
authority.

## 5. Sidecar state and wrapper contract

The verification/cleanup scripts require `EUID=0`, accept an exact non-root
`--unit-user`/`--unit-group`, verify both identities exist and match the requested
numeric ids, and validate a fixed production-host state prefix:

```text
/var/tmp/multinexus-p9-3c0/<run-id>/...
```

They refuse root as the unit user, `/var/lib`, `/opt`, home directories, the production DB, production
wrapper, symlink/resolved aliases of either, path traversal, wrong ownership/modes,
pre-existing unknown files, and run ids outside the helper's safe namespace.

Ownership/mode matrix:

- state-prefix: root-owned `0755`; each per-run root: root:`<unit-group>` `0750` so
  the unit can traverse only its exact namespace; root-only control/lock/ledger/
  evidence subdirectories: root-owned `0700`;
- generated Coordinate wrapper: root:`<unit-group>`, regular file `0750`;
- wrapper manifest at the per-run root: root:`<unit-group>`, regular file `0640`;
- isolated DB parent, worktree, harness, and context-DB parents:
  `<unit-user>:<unit-group>`, `0700`;
- isolated DB/context DB files: unit user, `0600` when created;
- rendered agent config: root:`<unit-group>`, `0640`;
- verification definition, values, ledger, phase, journal extracts, and evidence:
  root, `0600`.

The root controller invokes every Coordinate command through a fixed argv
`runuser --user <unit-user> -- <wrapper> ...` with a minimal environment. It never
initializes or mutates the isolated DB as root. systemd/cgroup/journal/proc inspection
and evidence writes remain root-only. Helper render/start/stop/cleanup must preserve
this matrix rather than relying on the caller's umask.

Under the exclusive run lock, preparation creates:

- fresh isolated Coordinate DB;
- exact wrapper root:`<unit-group>` mode `0750` that executes
  `/opt/coordinate/.venv/bin/coordinate --db <isolated-db> "$@"`;
- isolated workspace/worktree and harness directories;
- rendered fixture agent config and separate context DB paths;
- evidence JSONL/ledger files mode `0600`;
- a monotonic phase state controlling `intake=open|frozen`.

The wrapper's raw and resolved path must be under the exact state prefix, and its
embedded Coordinate executable and DB paths are absolute and separately rejected if
they resolve to the production wrapper/DB. At creation, the root ledger records its
device, inode, size, owner/group, mode, and SHA-256. Before every controller or agentd
Coordinate invocation and immediately before each unit start, revalidate the same
regular-file path, device/inode/hash/metadata and embedded DB value. The wrapper also
self-checks those fields and its SHA against a root-owned, group-readable `0640`
manifest before every agentd-originated invocation, then uses fixed argv without
`eval`. Replacement,
hard-link count other than one, symlink, mode/owner drift, or hash drift fails before
invocation. Root ownership prevents the non-root agentd from replacing it. No
production DB is copied.

## 6. Preparation and authority order

The script must capture a read-only production baseline first: integrity/schema,
canonical source versions/hashes, job/lease counts, fixture counts, exact three
service states/MainPIDs/NRestarts, canonical config hashes, and absence of fixture
units/processes.

The exact canonical services are:

- `coordinate.service`;
- `multinexus-discord-bridge.service`;
- `kook-nexus-hermes.service`.

`multinexus-discord.service` and any pattern-derived name are invalid. Every pre/post
snapshot queries those three literal ids individually.

It then uses only `runuser` plus the integrity-checked isolated wrapper:

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
cgroup, and journal identities. It begins bounded polling immediately after submit and
must observe `status=running` within five seconds. Before `acquired_at+30s`, it records
the first lease row and requires its first observed `expires_at` to equal
`acquired_at+120s`; otherwise the initial deadline was missed and the row fails rather
than inferring a baseline. While each job runs it records every distinct later
`expires_at`; success requires two strictly later values, each extending from an
accepted renewal. The exact unit journal must independently contain at least two
successful renewal DEBUG records for the same lease. Approximately 30/60-second timing
is checked against `acquired_at` with a documented scheduler tolerance; TTL and renew
interval remain exactly 120/30.

Both jobs must become `done`, release their active leases, and report exact
`response_text="fixture complete"` plus matching executor/context evidence. Any first
byte before the 75-second boundary, timeout, failed result, missing renewal, or extra
provider/session identity fails closed.

## 8. Hold, intake freeze, exact stop, and cgroup proof

With E2 still running, submit one E1 request whose exact prompt changes only to
`mode="hold", spawn_descendant=true`. The verifier obtains the timing boundary only
from the exact structured ClaudeAdapter DEBUG record described in 4.4 and converts its
monotonic nanoseconds to the helper's integer milliseconds. It then validates the
recorded PID solely through the E1 unit's ledger-recorded cgroup and
`/proc/<pid>/cmdline`.

At a bounded sample away from the 30-second renewal boundary, the cgroup process tree
must contain the exact agentd `MainPID`, exactly one fixture adapter child matching the
boundary PID/reviewed absolute fixture path, and exactly one `/bin/sleep 300`
descendant of that fixture. A Coordinate CLI child is allowed only as a short-lived
descendant of agentd with the exact integrity-checked wrapper/isolated DB argv; the
verifier retries for a bounded quiescent sample and fails if it persists or if any
other binary/process appears. PID reuse, a process outside the recorded cgroup,
ambiguous fixture PID, wrong parentage, unreadable cmdline/environ, or a later
observation substituted for the adapter boundary fails closed.

It then atomically changes the script ledger to `intake=frozen`; all subsequent submit
subcommands must refuse before Coordinate invocation. The already-submitted hold job
continues and renews. At target 80 seconds after the recorded adapter boundary, call
the helper's exact E1 stop with both timing evidence fields. Accepted evidence is
`75000 <= elapsed < 85000` ms. Even early/late/invalid evidence must still stop the
exact unit, wait inactive, and prove the recorded cgroup absent or empty before
returning nonzero.

The preceding paragraph's timing origin is the 4.4 adapter timer anchor, not cgroup
discovery time. Stop initiation targets 80 seconds, and complete
stop/cgroup verification must return before anchor+88 seconds; reaching that absolute
margin fails the row after still completing exact cleanup.

`intake=frozen` blocks only the verifier's submit path. Exact helper `status`, `stop`,
and ledger-based cleanup remain independently callable after verifier interruption.
Both scripts install failure traps that freeze intake and stop every exact ledger unit
without guessing state; they do not retry the full scenario or reap before the
recorded expiry/quiescence gate.

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

Before each global reap, all ledger units must be inactive with cgroup-empty proof and
the isolated DB must satisfy these literal read-only expected sets (queries use exact
ids, never `LIKE` as mutation authority):

- `agents`: exactly E1/E2, both `client_type=agentd`, exact measured `host_id`; their
  persisted `online_state` may remain `online` and is explicitly not liveness proof;
- `runner_profiles`: exactly E1/E2, both `runner_type=agentd`;
- executor/capacity source and policy/binding rows: exactly executor v2-enabled,
  capacity v1, and their E1/E2 rows; no other source or entry;
- `jobs WHERE status IN ('pending','running')`: exactly target hold job N in `running`
  before the first reap (N+1 before the second), with no other row;
- `execution_attempt_leases WHERE status='active'`: exactly target N lease before the
  first reap (N+1 before the second), with `expires_at < server_now`, and no other row;
- no other workspace, host profile, agent, runner, executor definition/binding,
  capacity policy, job, or lease identity.

The production read-only snapshot independently requires zero fixture row and its
baseline canonical sets. The global operation is safe because the wrapper and URI are
revalidated as the isolated DB. Invoke exactly one `runtime job lease reap`, require
`due_found=1`, `reaped_count=1`, empty errors, only the exact lease to become expired,
and its exact job to become `timed_out+recoverable`; preserve the expiry event.

Render a second run namespace against the same isolated DB and start exact E1 with:

```text
--recoverable
--recovery-reason p9-3c0-expired-after-exact-unit-stop
--prior-process-stopped
```

Require attempt N+1, a new lease id/token, previous status `timed_out`, and recovery
evidence in `job.claimed`. Prior-process authority is the first unit's exact inactive/
cgroup-empty proof, not the persisted agent `online_state`. Before sending the stale
report, require the job row `status=running`, `attempt_count=N+1`, unchanged exact
host id, and the new lease active/unexpired.

Snapshot the full job row, N+1 lease row, relevant delivery/event counts and maximum
row ids. Then send one exact old-N report using the old lease/token. It must return
nonzero with bounded stdout/stderr matching stale authority; afterward the job and N+1
lease rows must be field-for-field unchanged and no terminal, replayed, delivery, or
other event row may have been appended. A failure exit with any durable mutation is a
run failure.

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
4. query and require zero `status='active'` lease and zero pending/running job, then
   executor v3 disabled sync;
5. repeat the same zero-active/in-flight query and additionally require no active lease
   references either fixture capacity policy id, then capacity v2 empty sync;
6. repeat both guards once more, require disabled bindings and empty capacity source,
   then executor v4 empty sync;
7. verify zero fixture bindings/definitions/policies and no active lease; retain only
   the empty fixture executor source at reviewed v4 and empty capacity source at
   reviewed v2, because sync has no source-unregister operation;
8. run helper exact cleanup for each ledger unit;
9. capture final isolated DB and production read-only snapshots.

Because Coordinate has no unregister commands, the isolated DB may retain exactly two
dormant fixture agents, two same-id runner profiles, and the two versioned empty source
metadata rows described above. They must have no definition, binding, capacity policy,
active unit, pending/running job, or active lease. The isolated DB,
wrapper, ledgers, journals, hashes, and report inputs remain mode-restricted under the
state root until closeout review; cleanup must not delete SQLite rows or the evidence
root directly.

The cleanup script is the supported interrupted-run recovery entrypoint. Given a valid
root ledger it may be invoked without completing `local-verify`; it freezes intake if
needed, stops only exact recorded units, preserves an unexpired abandoned lease until
its recorded expiry, proves the literal quiescence set, reaps, then resumes the fixed
catalog cleanup sequence. Re-invocation after any completed step must verify and reuse
the durable phase record rather than repeat a non-idempotent mutation.

## 11. Zero-provider/network proof

Primary evidence for every exact unit:

- `systemd-analyze verify` success before launch;
- post-start `systemctl show` equality for every mandatory sandbox property;
- `IPAddressDeny=any` and `RestrictAddressFamilies=AF_UNIX` effective;
- systemd unit uses both `env -i` and exact-name `UnsetEnvironment=` entries for
  `ANTHROPIC_*`, `CLAUDE_*`, `OPENAI_*`, `CODEX_*`, `KIMI_*`, `MOONSHOT_*`,
  `AWS_*`, `AZURE_*`, `GOOGLE_*`, `VERTEX_*`, `DISCORD_*`, `KOOK_*`,
  `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and lowercase proxy variants;
- agentd environment from the exact unit contains only the approved minimal PATH;
- fixture child `/proc/<pid>/environ` contains only the expected minimal inherited
  fields such as PATH/PWD and no provider, Discord, KOOK, proxy, home, or cloud key;
- exact child cmdline resolves to the reviewed fixture executable and contains no
  provider/model/resume/dangerous flag;
- production provider/service logs and canonical DB show no fixture identity.

Packet capture is optional supplemental evidence only. A missing/unsupported runtime
sandbox property fails the entire run; packet capture cannot waive it.

`filtered_env` is not credential authority: it strips only KOOK/Discord prefixes and
adds PWD. The proof depends on the root controller's clean environment plus the
systemd unset denylist, and exact `/proc` observation after adapter inheritance.
Because systemd does not treat `*` as a wildcard in `UnsetEnvironment`, the controller
expands the policy prefixes above into exact variable names (without reading/logging
their values), unions them with a fixed known-key denylist, and emits one exact entry
per name. Tests reject a literal wildcard entry.

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

The matrix also requires: systemd 255 duration/set/path/IP normalization encodings and
unknown encodings; total removal of `systemd-run --dry-run`; root-controller/non-root
unit ownership and `runuser` argv; wrapper symlink/hardlink/inode/hash/owner/mode and
self-check failures; initial-expiry-missed failure; exact quiescence-set extras;
fixture/sleep/agentd/ephemeral-Coordinate process hierarchy; adapter boundary equal to
the frozen first-byte clock before stdin write; no progress emission; launchd/systemd/
NSSM default-INFO argv; exact-name credential unset expansion; stale-report event/row
immutability; and cleanup entry after interruption at every durable phase.

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
- root/unit ownership, wrapper manifest/inode/hash, privilege-drop, or state-path drift;
- ambiguous/missing cgroup child identity;
- missing/mismatched adapter first-byte clock record or hold cleanup reaching
  anchor+88 seconds;
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
- final isolated catalog entries are empty with only documented v4/v2 empty source
  metadata, dormant agent/runner, and timed-out recovery evidence allowed;
- production DB/config/source/service fingerprints are unchanged;
- cleanup and rerun-safety checks pass;
- an independent reviewer approves the exact implementation/execution evidence.

This closes P9-3C0 only. P9-3C1 production catalog activation remains blocked and
requires a new exact-revision plan, bootstrap, and authorization.
