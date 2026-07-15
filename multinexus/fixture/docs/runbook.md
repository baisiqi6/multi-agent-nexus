# P9-3C0 Package 2 — Zero-Provider Fixture Assets Operator Runbook

This runbook covers three separated tracks:

1. Package 2 inert deployment verification only.
2. Unauthorized-until-approved Package 3 isolated preview.
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

## 2. Package 3 isolated sidecar preview (UNAUTHORIZED until approved)

> **The commands below are informational only.** Do not run them until a fresh
> Package 3 bootstrap is independently reviewed and approved.

### 2.1 Immutable forward/cleanup catalog order

Forward:

1. `coordinate runtime executor sync --source /isolated/root/executor.fixture.v1-disabled.toml`
2. `coordinate runtime capacity sync --source /isolated/root/capacity.fixture.v1.toml`
3. `coordinate runtime executor sync --source /isolated/root/executor.fixture.v2-enabled.toml`

Cleanup:

1. `coordinate runtime executor sync --source /isolated/root/executor.fixture.v3-disabled.toml`
2. `coordinate runtime capacity sync --source /isolated/root/capacity.fixture.v2-empty.toml`
3. `coordinate runtime executor sync --source /isolated/root/executor.fixture.v4-empty.toml`

### 2.2 Runner/agent registration (placeholder values)

```bash
# Replace <isolated-db>, <isolated-wrapper>, and <isolated-root> with approved
# Package 3 isolated paths only. Replace <host-id> with the approved host
# identifier for the isolated runtime. Do not run these commands until Package 3
# is approved.
coordinate runner add p9-3c-fixture-e1 \
  --runner-type agent \
  --command '<isolated-wrapper> --db <isolated-db> ...'
coordinate runtime agent register \
  --agent-id p9-3c-fixture-e1 \
  --host-id <host-id>
coordinate runner add p9-3c-fixture-e2 \
  --runner-type agent \
  --command '<isolated-wrapper> --db <isolated-db> ...'
coordinate runtime agent register \
  --agent-id p9-3c-fixture-e2 \
  --host-id <host-id>
```

### 2.3 Exact request envelope and unit lifecycle

The fixture control envelope is:

```json
{
  "contract_version": 1,
  "mode": "hold",
  "quiet_seconds": 75,
  "spawn_descendant": true
}
```

Timing boundaries for Package 3 hold stop evidence:

- Operator target elapsed time: `80000` ms after recorded fixture-start boundary.
- Accepted interval: `75000 <= elapsed < 85000` ms.
- Absolute adapter `first_byte_timeout` is `90` s; the entire hold stop must
  complete well before that.

The `p9-3c0-unit.sh` helper records the Package 3 fixture-start boundary and
validates the monotonic elapsed interval. A late or malformed boundary still
forces exact unit stop, inactive wait, and cgroup-empty cleanup before the
command returns nonzero.

### 2.4 Submit target request

```bash
# Unauthorized until Package 3 approval. Replace <workspace-id> with the
# approved isolated workspace identifier. Do not run these commands until
# Package 3 is independently reviewed and approved.
coordinate runtime request submit <workspace-id> \
  --target-agent p9-3c-fixture-e1 \
  --prompt '...' \
  --origin-json '{"field": "<origin-value>"}' \
  --reply-json '{"field": "<reply-value>"}'
```

> **Do not use `--origin-json @<file>` or `--reply-json @<file>`.** The fixture
> helper parses these values as literal JSON strings, not as file references.

### 2.5 Evidence and cleanup

Preserve the ledger, unit show output, and cgroup `cgroup.procs` emptiness
proof. Run `p9-3c0-unit.sh stop` and `p9-3c0-unit.sh cleanup` for each exact
unit. Do not use wildcard units, `pkill`, or guessed PIDs.

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
