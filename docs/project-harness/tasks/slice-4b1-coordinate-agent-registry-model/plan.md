# Slice 4B1 Coordinate Agent Registry Model

> Detailed implementation plan. Implementation remains unauthorized until an
> independent non-Codex reviewer approves this exact revision, Coordinate records the
> approval, and a fresh worker bootstrap binds the approved SHA.

## Identity

- Package: `slice-4b1-coordinate-agent-registry-model`.
- Stage: Slice 4B, first of two packages.
- Required Coordinate start:
  `5986cc38d8fa7a46c1cdd1dcb195fcc7043314d9`.
- Plan reviewer and coding worker: Kimi Code Highspeed through Oh-My-Pi; GLM is fallback
  only after documented Kimi quota/auth/provider failure.
- Operator and result reviewer: Codex.

## Goal

Replace the ambiguous `workspaces.agents_json` write model with one explicit registry
authority model:

1. one versioned authoritative roster projection per workspace;
2. separate manual overrides with actor, reason and optional expiry;
3. one deterministic effective resolver where an active same-name override shadows the
   authoritative entry;
4. immediate daemon authorization refresh after a committed registry revision; and
5. `agents_json` retained only as a generated compatibility projection for older
   binaries, never as the new write authority.

S4-B1 is Coordinate-only. It does not edit or deploy real `agents.toml`; S4-B2 wires
the deployed MultiNexus authority into this contract.

## Reviewed current state

At Coordinate `5986cc3`:

- `parse_agents_toml` extracts managed/external entries but records no source identity,
  version or hash;
- `set_workspace_agent` writes an indistinguishable mapping directly into
  `agents_json` with no actor/reason/expiry/history;
- `sync_workspace_agents(replace=False)` merges by default and can leave removed
  identities authorized forever;
- `replace=True` replaces manual and sourced entries together because provenance is
  absent;
- the daemon loads `agents_json` only in `on_ready`, so committed additions/removals do
  not affect authorization until restart;
- the deployed and local MultiNexus configs currently contain the same ten roster IDs
  but no `[registry]` metadata; one entry is skipped because it lacks
  `discord_user_id`, producing nine effective Discord identities;
- `agents_json` in the production control DB currently contains those same nine
  identities, but this equality is unversioned and not durable evidence.

Measured baseline:

- schema version: 9;
- focused tests: 14 agent-registry + 21 DB + 16 workspace-CLI + 39 daemon + 32 CLI
  contract + 169 root CLI = 291 passing;
- full discovery: 1,574 passing under `/opt/homebrew/bin/python3.14`;
- CLI contract: 21 top-level commands and fixture SHA-256
  `43e181046d3baa174199e3c02bcbc1ab1fedf83177d5c3725516a839bbb1f9e1`.

## Canonical model

### 1. Versioned schema

Advance SQLite schema to version 10 and add:

#### `workspace_agent_registry_sources`

One row per workspace:

- `workspace_id` primary/foreign key;
- `source_id` non-empty stable identity;
- `source_version` non-negative integer;
- `source_hash` lowercase 64-character SHA-256;
- `source_path` recorded evidence only, never compared as cross-host identity;
- `synced_by`, `synced_at`.

#### `workspace_agent_registry_entries`

Rows keyed by `(workspace_id, agent_name, entry_kind)` where `entry_kind` is one of
`authoritative`, `override`, or `legacy`:

- Discord id, display name and agent type;
- override-only `actor`, `reason`, `expires_at`;
- created/updated timestamps;
- workspace foreign key with cascade.

Add an index on `(workspace_id, entry_kind)`; the composite primary key already covers
same-workspace name/kind lookup.

Add `workspaces.agent_registry_revision INTEGER NOT NULL DEFAULT 0`.

Migration backfills current `agents_json` entries as `legacy`, preserving authorization
until the first authoritative sync. Exact migration rules:

- missing column, SQL `NULL`, or an empty JSON object means no legacy rows;
- top-level JSON must be an object; invalid JSON or another type fails migration with a
  clear error, writes no legacy rows and does not advance `user_version`;
- decode the top-level object with duplicate-key detection; duplicate agent names fail
  rather than silently taking the last value;
- each value must be an object with a non-empty valid Discord id; malformed entries
  fail the whole backfill rather than silently removing authorization;
- the top-level key is the agent name; unknown entry fields are ignored;
- missing/empty display name defaults to the agent name, and missing agent type becomes
  `legacy` metadata;
- v10 reopen creates no duplicate legacy rows or revision increment.

Validate all legacy rows before backfill writes. On failure, user version and legacy
rows remain unchanged even if idempotent empty v10 tables already exist. The first
accepted authoritative sync deletes all `legacy` and previous `authoritative` rows,
then writes the new roster. It never silently promotes legacy rows into overrides.

### 2. Source identity and canonical hash

Extend TOML parsing to accept:

```toml
[registry]
id = "multinexus.discord"
version = 1
```

Before hashing, normalize every parsed entry:

- `id`: `str(value).strip()`, non-empty;
- `discord_user_id`: `str(value).strip()`, ASCII decimal digits only and integer > 0;
- `display_name`: `str(value).strip()`, default to normalized id when missing/empty;
- `agent_type`: fixed lowercase literal `managed` or `external` selected by TOML
  section, never a free-form source value.

The canonical hash input is a top-level JSON list sorted by normalized `id` ascending
using Python Unicode code-point ordering. Each item is exactly an object with keys
`id`, `discord_user_id`, `display_name`, `agent_type`. Serialize with
`json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, encode
UTF-8, then SHA-256. Exclude source id/version/path, tokens, environment keys, prompts,
binary paths, work directories, channels, comments, unknown fields and raw file bytes.

For authoritative sync, missing/invalid id or version is an error. Rules for an existing
source:

- same source id, same version, same hash: idempotent no-op;
- same source id, same version, different hash: reject version conflict;
- same source id, lower version: reject rollback;
- same source id, higher version: accept;
- different source id: reject source takeover and require a separately reviewed
  migration package/operator repair path.

S4-B1 tests use temporary TOML with registry metadata. Updating real/example deployed
configuration belongs to S4-B2.

### 3. Authoritative sync and effective resolution

`workspace agent sync` becomes fail-closed authoritative replace:

- `--replace` remains in the parser for compatibility but is required by the handler;
  omission returns a clear error and performs no write;
- sync writes source metadata, replaces authoritative/legacy rows, preserves override
  rows, increments registry revision, regenerates compatibility `agents_json`, and
  appends one `workspace.agent_registry.synced` audit event in one transaction;
- result reports exact added, updated, removed, unchanged and shadowed agent-name lists,
  plus source id/version/hash and revision—not counts alone.

Effective resolution rules:

1. active override for the same name wins;
2. otherwise authoritative entry wins;
3. before the first authoritative sync only, legacy entry remains effective;
4. expired override is retained for audit but ignored;
5. duplicate effective Discord ids across different names reject the mutation before
   commit.

All Coordinate authorization consumers in this scope use the effective resolver rather
than decoding `agents_json`.

### 4. Auditable manual overrides

`workspace agent add` becomes an override upsert and requires:

- existing name/id arguments;
- `--reason` non-empty;
- `--actor` (default `operator`);
- optional UTC `--expires-at`.

Expiry uses exactly `YYYY-MM-DDTHH:MM:SSZ` UTC at whole-second precision. Other offsets,
fractional seconds, naive timestamps and malformed values are rejected. Add/update
rejects `expires_at <= utc_now()`. Effective resolution evaluates expiry at read time;
an override is inactive when `expires_at <= now`, remains stored for audit, and reveals
the same-name authoritative/legacy entry. Tests inject/control the clock rather than
sleeping.

The mutation writes/updates only `entry_kind=override`, increments revision,
regenerates the compatibility projection, and appends one
`workspace.agent_override.set` event atomically. Invalid/past expiry is rejected; an
explicit `workspace agent remove-override` command requires workspace, name, actor and
non-empty reason; it removes only the override row, reveals any same-name authoritative
entry, increments revision, regenerates projection and appends
`workspace.agent_override.removed` in one transaction. Removing a missing override
fails with non-zero CLI status and no mutation; it never deletes authoritative/legacy
rows.

The DB API used by production must require actor and reason; no new silent legacy write
path is allowed. Tests may use explicit fixture reasons.

### 5. Immediate daemon refresh

Before the `is_agent` branch for every inbound channel message, `on_message` performs
one `asyncio.to_thread` read that opens/migrates the DB, resolves all currently effective
workspace memberships using the current UTC clock, and atomically replaces the
in-memory map. This deliberately favors fail-closed correctness over a revision-only
cache: an override can expire without any DB write or revision change.

`on_ready` may still perform the initial load for observability, but cached membership
is never used for a later message without the per-message refresh. `_open_db` runs v10
migration before resolution. If migration or resolution fails, the daemon logs the
error and treats the author as unauthorized for that message; it must not fall back to
the previous cache. Refresh occurs before testing `author_id in registry`, not inside
`_ingest_agent_message` after classification.

Tests must prove:

- an added effective agent is accepted after revision change without calling
  `on_ready`/manual reload;
- a removed authoritative agent is rejected immediately;
- an expired override is rejected on the first message at/after expiry even if no
  revision changed and it existed in the previous cache; and
- cross-workspace membership remains scoped.

No background thread, signal handler, polling timer or deployment restart is required
by B1. `agent_registry_revision` remains audit/projection metadata for S4-D and API
results, not the sole cache invalidation clock.

## Compatibility projection

`workspaces.agents_json` remains populated with only currently effective entries so the
older deployed daemon can continue during rollout. It is generated transactionally from
the normalized model. New resolver/daemon code must never treat it as canonical.
S4-D will add explicit doctor comparison and repair evidence; B1 must expose enough
read-only metadata for that future check but must not implement doctor repair.

## CLI contract proof

Approved parser-tree changes are exactly: add `--reason`, `--actor` and `--expires-at`
to `workspace agent add`, and add the sibling `workspace agent remove-override` leaf
with `workspace_id`, `--name`, `--reason` and `--actor`. `workspace agent sync
--replace` remains present; other commands/arguments/order are unchanged.

Update the CLI fixture intentionally and add a permanent delta/rewind proof showing that
removing the new override-removal leaf and normalizing only the three new add options
restores the reviewed fixture SHA
`43e18104...f9e1`. Do not merely regenerate the fixture and bless it.

## Allowed paths

Production:

- `src/coordinate/schema.py`;
- `src/coordinate/db.py`;
- `src/coordinate/agent_registry.py`;
- `src/coordinate/workspace_cli.py`;
- `src/coordinate/daemon.py`.

Tests/fixture:

- `tests/test_agent_registry.py`;
- `tests/test_db.py`;
- `tests/test_workspace_cli.py`;
- `tests/test_daemon.py`;
- `tests/test_cli.py`;
- `tests/test_cli_contract.py`;
- `tests/fixtures/cli_contract.json`.

Any MultiNexus production/config/deploy path, real DB/config, policy/handoff module, or
other Coordinate path requires plan revision.

## Failure matrix

| Failure | Required response |
|---|---|
| Missing/invalid registry metadata | Reject before DB mutation. |
| Same version with different hash | Reject conflict; do not bless drift. |
| Lower version | Reject rollback. |
| Different source id | Reject takeover; require separate migration authority. |
| Parse errors/duplicate ids | Reject entire sync; no partial roster. |
| Removed source identity remains effective | Fix replace transaction/projection. |
| Override disappears during sync | Restore override preservation. |
| Expired override remains authorized | Fix effective resolver/cache refresh. |
| Override removal deletes roster entry | Restore kind-scoped removal and reveal roster. |
| Duplicate effective Discord id | Reject mutation before commit. |
| Audit event fails | Roll back source/entries/revision/projection together. |
| Daemon still authorizes removed cached id | Fix revision check; do not require restart. |
| Fixture changes outside three options | Stop and inspect parser drift. |
| Another path is required | Stop and revise plan. |
| Kimi provider failure | Preserve JSONL and restart with GLM under Operator control. |

## Explicit non-goals

- No real or example `agents.toml` edit; no token/config output.
- No MultiNexus deploy/start script, systemd/launchd, SSH or live sync.
- No source-id takeover/repair command and no automatic judgment about approved roster.
- No S4-C split-operation IDs/fingerprints or S4-D doctor/repair implementation.
- No capability/health/load registry, scheduler or Phase 9 executor selection.
- No removal of `agents_json` in this migration.

## Acceptance matrix

| Area | Required evidence |
|---|---|
| Migration | v9 registry preserved as legacy; v10 reopen idempotent |
| Provenance | source id/version/canonical roster hash stored and reported |
| Replace | absent authoritative/legacy rows removed; overrides preserved |
| Overrides | explicit actor/reason/expiry; active shadowing and expiry proven |
| Atomicity | source, entries, revision, projection, audit event commit/rollback together |
| Resolver | no duplicate effective Discord ids; workspace scoping intact |
| Reload | add/remove/expiry reflected without daemon restart |
| Compatibility | effective `agents_json` regenerated but never read as new authority |
| CLI | only approved add options + remove-override leaf; rewind returns old fixture hash |
| Regression | focused does not drop from 291; full does not drop from 1,574 |

## Validation

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_agent_registry.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_db.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_workspace_cli.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_daemon.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_cli_contract.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_cli.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests
```

## Worker protocol and stop conditions

Use a fresh Coordinate worktree from exact start, exact approved plan SHA and only the
allowed paths. One local commit; no push/merge/deploy/SSH/lifecycle/MultiNexus mutation.
Codex reviews schema migration, transaction rollback, effective resolution, cache
refresh, CLI delta and JSONL before integration.

Stop if migration cannot preserve existing authorization until first sync, if an audit
event cannot share the mutation
transaction, if any real config is required, or if full tests gain a failure.
