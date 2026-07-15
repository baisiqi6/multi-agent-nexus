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

## 3. P9-3C1 production activation outline

Production activation is blocked in Package 2. Prerequisites for a future P9-3C1
review:

1. Independent approval of a production-capable bootstrap.
2. Fixture ids added to canonical `config/agent-registry.toml` through the
   normal review process.
3. Production Coordinate DB and wrapper explicitly authorized for fixture use.

**Package 2's helper rejects the production DB `/var/lib/coordinate/coord.sqlite3`
and production wrapper `/usr/local/bin/coord-local`. There is no bypass token or
environment variable in Package 2.**

---

## 4. Forbidden operations

Never perform these with Package 2 assets:

- Direct SQLite writes or deletes in Coordinate DB.
- Mutable TOML edits between staging versions.
- `workspace agent sync` or roster verification using fixture executor files.
- `pkill`, wildcard systemd units, or guessed PID cleanup.
- Canonical authority mutation without a reviewed commit.
