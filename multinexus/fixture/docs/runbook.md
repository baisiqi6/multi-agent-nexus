# P9-3C0 Package 2 — Zero-Provider Fixture Assets Operator Runbook

This runbook covers three separated tracks:

1. Package 2 inert deployment verification only.
2. Reviewed Package 3 isolated-sidecar operator workflow.
3. P9-3C1 production activation outline.

Package 2 assets are deliberately inert. They do not sync catalogs, start real
units, create jobs/leases, or access production credentials.

---

## 1. Package 2 inert verification/deployment

### 1.1 Parse and verify fixture assets locally

```bash
# Executor authorities
.venv/bin/python -m multinexus.registry_authority show \
  --authority multinexus/fixture/config/executor.fixture.v1-disabled.toml
.venv/bin/python -m multinexus.registry_authority show \
  --authority multinexus/fixture/config/executor.fixture.v2-enabled.toml
.venv/bin/python -m multinexus.registry_authority show \
  --authority multinexus/fixture/config/executor.fixture.v3-disabled.toml
.venv/bin/python -m multinexus.registry_authority show \
  --authority multinexus/fixture/config/executor.fixture.v4-empty.toml

# Capacity authorities
.venv/bin/python -m multinexus.executor_capacity_authority \
  multinexus/fixture/config/capacity.fixture.v1.toml
.venv/bin/python -m multinexus.executor_capacity_authority \
  multinexus/fixture/config/capacity.fixture.v2-empty.toml
```

### 1.2 Run Package 2 tests

```bash
.venv/bin/python -m pytest tests/test_p9_3c0_fixture_assets.py -v
```

### 1.3 Deploy assets inertly

Deploy copies the repository tree. Fixture files land at
`/opt/multinexus/multinexus/fixture/`. Nothing under that path is executed
automatically by the deploy script or canonical services.

```bash
git status --short
git add ...
git commit -m "p9-3c0: add fixture package 2 assets"
git push
scripts/deploy-server.sh multinexus
```

### 1.4 Verify no fixture activation occurred

After deploy, confirm:

- `config/agent-registry.toml` still contains no `p9-3c-fixture-e1/e2` entries.
- Coordinate DB has no new `p9-3c-fixture-*` agents, runners, executor sources,
  capacity policies, active leases, or jobs.
- No `p9-3c-fixture-*` systemd units are active.

---

## 2. Package 3 isolated sidecar operator contract

Package 3 is executable only after its exact implementation commit has passed
review, merged-main validation, inert deployment, and deployed SHA/mode parity.
It never activates fixture identities in the production Coordinate DB or canonical
`agents.toml`/registry. Production services, configs, and DB are read-only baseline
authority.

### 2.1 Prepare a fresh namespace

Choose a new lowercase run id of at most 61 characters. The verifier derives the
exact `<run-id>-r2` recovery namespace, so neither namespace may already exist.
Use the reviewed non-root fixture account; never use `root`.

```bash
sudo /opt/multinexus/scripts/p9-3c0-local-verify.sh prepare \
  --run-id <run-id> \
  --unit-user <fixture-user> \
  --unit-group <fixture-group> \
  --agent local-operator
```

`prepare` creates only `/var/tmp/multinexus-p9-3c0/<run-id>`, the isolated DB
parents, work/harness/context directories, root-sealed wrapper and manifest,
rendered fixture config, static systemd definition, locks, ledger, and evidence.
It performs no catalog sync, job submission, or unit start.

### 2.2 Run or resume the bounded verification

```bash
sudo /opt/multinexus/scripts/p9-3c0-local-verify.sh verify \
  --run-id <run-id> \
  --unit-user <fixture-user> \
  --unit-group <fixture-group>
```

The durable phase machine performs, in order:

1. exact read-only production DB/config/service baseline;
2. isolated workspace, host profile, agentd runners, and immutable catalog sync
   `executor v1 disabled -> capacity v1 -> executor v2 enabled`;
3. two concurrent exact 75-second complete requests, each with initial TTL 120,
   renew interval 30, two observed later deadlines, two matching DEBUG journal
   renewals, and exact `fixture complete` result;
4. E1 hold/descendant process-tree proof, atomic intake freeze, and exact crash stop
   (`systemctl kill --kill-whom=all --signal=SIGKILL` for the ledger-bound unit,
   followed by exact `systemctl stop` and recorded-cgroup-empty proof) at
   the adapter monotonic 80-second target (`75000 <= elapsed < 85000`, complete
   cleanup before 88 seconds);
5. exact expiry/reap of attempt N, `<run-id>-r2` recovery against the same isolated
   DB, rejection and immutability proof for one old-N stale report, then the same
   exact crash stop, expiry, and reap of N+1;
6. production-baseline comparison and idempotent cleanup in the fixed order
   `executor v3 disabled -> capacity v2 empty -> executor v4 empty`.

Re-run the same `verify` command after interruption. Completed verification phases
are not repeated. Cleanup has its own adjacent durable phase record and resumes from
the last verified transition. A failed pre-cleanup scenario is evidence-preserving
and is not automatically retried.

### 2.3 Independent cleanup entrypoint

If verification has frozen intake but was interrupted, cleanup may be invoked
directly with the same sealed identity:

```bash
sudo /opt/multinexus/scripts/p9-3c0-cleanup.sh cleanup \
  --run-id <run-id> \
  --unit-user <fixture-user> \
  --unit-group <fixture-group>
```

Cleanup follows only exact primary/recovery ledger links and unit names. It waits
past ledgered active-lease expiry, reaps through the isolated wrapper, proves every
recorded cgroup empty, checks zero active/in-flight work before every catalog sync,
and retains the isolated DB, wrappers, manifests, ledgers, and evidence for review.
Cleanup and failure traps use graceful exact stop; they never opt into `--crash`.
It never uses wildcard units, direct SQLite writes/deletes, `pkill`, `pgrep`, guessed
PIDs, mutable TOML edits, provider credentials, or network access.

### 2.4 Expected retained residue

Success retains exactly two dormant fixture agent/agentd-runner rows, executor source
v4, capacity source v2, two completed base jobs with released leases, and one
recoverable timed-out hold job with expired N/N+1 leases. Definitions, bindings,
capacity policies, active leases, and pending/running jobs are empty. Production must
still contain zero fixture identity and the three canonical services must match their
captured `MainPID`, `NRestarts`, state, and fragment hashes.

---

## 3. P9-3C1 P2 inert production controller

P9-3C1 P2 adds a separate production-authorized helper surface and a sealed
controller, but deployment remains inert. The old P9-3C0
`render/preflight/start/status/stop/cleanup` surface still rejects
`/var/lib/coordinate/coord.sqlite3` and `/usr/local/bin/coord-local`; only the new
`production-*` subcommands can use the manifest-bound production identities.

The P2 deploy gate must use a clean, reviewed revision and must not restart a
service:

```bash
scripts/deploy-server.sh multinexus \
  --host kook-hermes-admin \
  --no-restart
```

The deploy script installs these assets and runs the existing canonical registry
parity/smoke path. That path may issue idempotent roster/executor/capacity syncs;
acceptance requires no added/removed/updated entries and no fixture source. It
never invokes `p9-3c1-production-verify.sh`, any `production-*` helper command,
job submission, or fixture unit creation.

### 3.1 Create one inert sealed run

Choose a fresh id matching
`^p9-3c1-prod-[0-9]{8}t[0-9]{6}z-[a-f0-9]{8}$`:

```bash
sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh prepare \
  --run-id <p9-3c1-run-id> \
  --unit-user coord \
  --unit-group coord
```

`prepare` requires the shared production mutation lock to be free. It creates a
fresh root under `/var/tmp/multinexus-p9-3c1/<run-id>`, performs read-only schema,
integrity, FK, due-lease and canonical-projection gates, creates an online SQLite
backup, and seals installed revisions, file identities, budgets, config hashes and
the controller manifest. It does not acquire the lock, render agent config, create
Coordinate rows, sync catalogs, submit requests, or start units.

### 3.2 Repeat the read-only inert gates

Run both commands twice and compare their canonical JSON plus a byte-level tree
snapshot before and after:

```bash
sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh preflight \
  --run-id <p9-3c1-run-id>
sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh status \
  --run-id <p9-3c1-run-id>
```

Acceptance requires phase `sealed`, no
`control/live-authorization.json`, no `control/production-lock.token`, lock free,
DB `integrity=ok/user_version=13/FK=0`, zero due active leases, canonical projection
equal to the sealed hash, no P9-3C1 workspace/agent/source/job/lease/delivery rows,
no fixture unit/process/cgroup, and unchanged service PID/restart evidence.

Do not invoke `run` or `cleanup` for a P2 inert run. Keep the sealed run root as
audit evidence. P3 uses a new run id and a new exact-revision `prepare`.

### 3.3 P3-only live boundary

The installed controller contains locally tested P3 machinery, but `run` requires
a separate root-owned mode `0600` canonical authorization artifact binding the
exact run, manifest, revisions, hashes, approved review artifacts, expiry, nonce,
five-request budget and maximum-two-active-unit budget. The controller revalidates
that copy, its exact P0 lock token, ledger/phase agreement and expiry before every
forward phase.

Actual jobs are claimed only by the two agentd units with sealed
`--reap-mode none`; the controller may issue only the reviewed negative claim
probe. J3 uses explicit `production-stop --crash`, exact lease expiry/reap, then a
same-unit `hold` recovery generation. The two-unit budget counts the two distinct
sealed identities E1/E2, while the helper uses the latest ledgered cgroup for the
reviewed E1 recovery generation. Three stale N operations (`progress`, `report`,
`lease renew`) must fail without authoritative mutation before the current N+1
empty report. Only the four non-J3 stdout deliveries may be sent.

P3 live execution still requires a fresh independently reviewed operator bootstrap
and exact deployed-evidence approval. P2 deployment or this runbook does not grant
that authorization.

---

## 4. Forbidden operations

Never perform these with an inert P2 run:

- Direct SQLite writes or deletes in Coordinate DB.
- Mutable TOML edits between staging versions.
- `workspace agent sync` or roster verification using fixture executor files.
- `pkill`, wildcard systemd units, or guessed PID cleanup.
- Canonical authority mutation without a reviewed commit.
- `run`, `cleanup`, `production-render`, `production-start`, `production-stop`,
  `production-cleanup`, catalog sync, job claim/reap/report, delivery send, or
  service restart.
- Reuse of an old run root, authorization nonce, lock token, manifest, backup, or
  P3 review artifact.
