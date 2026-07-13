# Detailed Execution Plan: P9-3A Capacity and Resource Lease Foundation

> P9-3A creates the authority and transaction primitives required by P9-3B. It does
> not change runtime claim behavior, start lease heartbeats, reap live jobs, or claim
> that concurrency is already safe.

## Package identity and accepted baselines

- Package: `p9-3a-capacity-resource-lease-foundation`.
- Parent: `phase-9-execution-isolation` / P9-3.
- Measurement:
  `docs/project-harness/tasks/p9-3a-capacity-resource-lease-foundation/measurement.md`.
- Coordinate start:
  `90783b2c77933287ba163c4bb598f4a862e8b416` on `main == origin/main`.
- MultiNexus implementation-code start (before this plan-package commit):
  `ccb2b6aee4c66903ebabae2451c657cf815c36ab`; the plan/checklist package itself is
  committed later and must not be mistaken for an implementation baseline change.
- Existing Coordinate exception: user-owned untracked `.qoder/` remains untouched.
- Schema/code/production DB baseline: v12.
- Executor catalog baseline: source `multinexus.discord`, version 2, hash
  `f4cdf79897755c173e97ddae1dfd88047436039f3447d4d6257105715ba5551d`.
- Test baseline: Coordinate 2,156 passed plus exactly the same nine historical
  CLI-fixture/AST failures; MultiNexus 503 passed, 2 skipped.
- Architect/operator/result reviewer: Codex.
- Independent plan reviewer: fresh GLM 5.2 reviewer-only session. If GLM does not
  produce a bounded verdict in the observation window, use a fresh ordinary
  `kimi-code/kimi-for-coding` reviewer; DeepSeek V4 Pro or Minimax are lower-priority
  fallbacks only.
- Coding worker: a different fresh ordinary `kimi-code/kimi-for-coding` session.
  `highspeed` is forbidden unless the user explicitly changes the preference.
- Provider-native JSONL is preferred live evidence when available; process, job/event,
  log, repository, and test evidence remain required corroboration.

## Goal

Create one source-controlled, independently versioned capacity projection and one
Coordinate-owned execution resource/lease foundation that:

1. assigns an explicit bounded `max_concurrent_jobs` to every enabled typed executor
   instance without changing P9-2A binding ids or catalog hash;
2. derives an exact host-scoped normalized worktree resource identity;
3. stores immutable capacity-policy and resource snapshots on attempt leases;
4. provides transaction-aware reserve, renew, release, and expire primitives with
   database constraints and idempotent replay;
5. deploys schema v13 and capacity parity with zero production lease rows;
6. leaves claim/report/progress/agentd behavior unchanged until P9-3B.

## Contract decisions

### 1. One source file, separate versioned projection

`config/agent-registry.toml` remains the only source-controlled executor authority
file, but capacity is not added to P9-2A identity binding fields. Add two distinct root
sections:

```toml
[capacity_registry]
id = "multinexus.discord.capacity"
version = 1

[[executor_capacities]]
agent_id = "mac-omp"
max_concurrent_jobs = 1
```

Rules:

- every enabled `executor_instance_binding` has exactly one capacity entry;
- external/untyped/disabled entries have none unless separately enabled and typed;
- `agent_id` uses the existing bounded identity grammar;
- `max_concurrent_jobs` is an integer from 1 through 32; booleans are rejected;
- entries are unique and canonicalized in `agent_id` order;
- unknown/missing keys, duplicate entries, coverage mismatch, secret-bearing keys,
  unsupported versions, and unsafe values fail closed;
- the existing `[registry].version` remains 2 because roster/executor identity bytes
  are unchanged; the new projection has its own version 1;
- P9-2A parsers explicitly allow and ignore the two capacity roots. Existing executor
  catalog fixture bytes, catalog hash, binding ids, and roster hash must remain exact.

The capacity catalog canonical object is:

```json
{
  "contract_version": 1,
  "source_id": "multinexus.discord.capacity",
  "source_version": 1,
  "policies": [
    {"agent_id": "mac-omp", "max_concurrent_jobs": 1}
  ]
}
```

`catalog_hash` is SHA-256 over canonical UTF-8 JSON. Each policy id is SHA-256 over
the canonical UTF-8 JSON object below, with sorted keys and compact separators:

```json
{
  "agent_id": "mac-omp",
  "catalog_hash": "<64 lowercase hex>",
  "contract_version": 1,
  "max_concurrent_jobs": 1,
  "source_id": "multinexus.discord.capacity",
  "source_version": 1
}
```

The stored form is `capacity_policy_id=sha256:<64 lowercase hex>`. No source path,
timestamp, display text, executor definition, or current binding row participates.

### 2. Coordinate schema v13

Add `executor_capacity_sources`:

- `source_id` primary key;
- `source_version`, `catalog_hash`, optional `source_path`, `updated_at`.

Add `executor_capacity_policies`:

- `agent_id` primary key;
- `source_id`, `source_version`, `catalog_hash`, `capacity_policy_id`;
- `max_concurrent_jobs` with SQL `CHECK` 1..32;
- timestamps and a foreign key to the capacity source;
- intentionally no SQL foreign key to `executor_instance_bindings`: the current
  executor sync replaces binding rows, and a cross-projection FK would either break
  that transaction or make safe executor removal impossible to stage. Capacity sync
  instead validates complete enabled-typed binding coverage inside its own transaction,
  and deploy/doctor parity fails closed on drift.

Add `execution_attempt_leases`:

- `lease_id` primary key and immutable `job_id + attempt_token` unique pair;
- `agent_id`, `runner_profile_id`, `host_id`;
- `resource_kind='worktree'`, `resource_key`, and bounded normalized resource path;
- snapshotted `capacity_policy_id` and `max_concurrent_jobs`;
- `status` in `active|released|expired`;
- `acquired_at`, `renewed_at`, `expires_at`, optional `released_at` and
  `release_reason`;
- SQL checks for positive attempt, bounded capacity, legal state/timestamp shape;
- one partial unique index on active `resource_key`;
- indexes for active agent count, expiry scan, job/attempt lookup, and resource lookup.

Lease foreign-key rules are explicit:

- `job_id REFERENCES jobs(id) ON DELETE RESTRICT`;
- `agent_id REFERENCES agents(id) ON DELETE RESTRICT`;
- `runner_profile_id REFERENCES runner_profiles(id) ON DELETE RESTRICT`;
- no foreign key from snapshotted `capacity_policy_id` to the mutable current capacity
  policy row, so terminal historical leases survive later policy version replacement.

Historical leases snapshot capacity/resource data and do not change when a later
capacity source version syncs. Capacity sync may not delete a policy referenced by an
active lease; a coverage/removal conflict rolls back the whole sync.

Migration v12 -> v13 is atomic and idempotent. Existing jobs and identity tables are
not rewritten. Empty or historical production DBs produce zero lease rows.

### 3. Host-scoped normalized worktree resource v1

Create a focused Coordinate module for execution resource identity. Input is the
already host-resolved P9-1 `host_id + worktree_path`, not a prompt, control-host path,
current cwd, or filesystem probe.

Canonical resource object:

```json
{
  "contract_version": 1,
  "resource_kind": "worktree",
  "host_id": "macbook-local",
  "normalized_path": "/Users/yinxin/projects/example"
}
```

`resource_key=sha256:<digest>` over canonical UTF-8 JSON.

Normalization rules:

- reject relative, empty, NUL/control-bearing, or over-4096-character paths;
- POSIX: require `/`, apply lexical `posixpath.normpath` and Unicode NFC, preserve
  case, and preserve root semantics;
- Windows drive/UNC: accept either separator, apply `ntpath.normpath`, canonicalize
  separators, Unicode NFC plus `casefold`, and preserve drive/UNC root semantics;
- include bounded `host_id`, so equal spellings on different hosts are distinct;
- equivalent Windows case/separator spellings collide; equivalent POSIX dot/trailing-
  slash spellings collide;
- do not call `realpath`, access a remote filesystem, resolve symlinks/junctions, or
  infer shared network storage. Host profiles must provide canonical physical paths;
  aliasing outside lexical normalization remains an explicit non-goal.

Stored resource objects are strict exact-shape contracts with version/digest
validation; malformed stored state fails closed.

### 4. Transaction-aware lease primitives

Create a focused Coordinate lease module. P9-3A exposes internal service functions,
not a public claim/heartbeat CLI:

- resolve current capacity policy by typed agent id;
- count active, unexpired leases for one agent;
- reserve one attempt lease for an already existing job/attempt/context;
- renew one exact active lease;
- release one exact lease with bounded reason;
- expire exact or due leases without mutating job state.

Rules:

- reserve/renew/release/expire accept caller-owned transactions and never perform a
  hidden commit. Test-only/convenience wrappers may open `BEGIN IMMEDIATE`, but P9-3B
  must be able to combine job CAS and lease mutation in one transaction;
- reserve first marks due `status='active'` leases for the target agent or target
  resource as `expired` inside that same transaction, without changing job state. This
  is the complete set that can affect the current capacity/resource decision and avoids
  an unrelated global expiry scan while keeping the partial unique index and capacity
  count consistent;
- reserve requires job/attempt/agent/runner/context cross-links to match current rows;
- reserve uses the same bounded TTL contract as renewal: integer 30..600 seconds,
  rejecting booleans and out-of-range values before any write;
- reserve counts remaining active leases, then rejects capacity exhaustion and active
  resource collision before insert;
- the database partial unique index is the final race fence for the same resource;
- an exact reserve retry returns the original lease only when every immutable field
  matches; conflicting replay rolls back;
- renewal requires exact lease/job/attempt/agent identity, active status, and a current
  unexpired lease. It advances `renewed_at/expires_at` monotonically within bounded TTL
  30..600 seconds;
- release and expiry are idempotent only for the same final state/reason. They never
  release or expire a newer attempt's lease;
- P9-3A expiry changes the lease row only. Moving a running job to recoverable timeout
  is P9-3B and must be atomic with expiry there;
- no event is appended for periodic renewal in P9-3A. The lease table is authority;
  P9-4 later defines bounded observation events/log handles.

### 5. Sync, visibility, and deployment parity

Add a separate Coordinate runtime capacity surface under `runtime capacity`:

- `sync --source <agent-registry.toml>`;
- `list` and `show <agent-id>`.

Sync is atomic, exact-retry idempotent, version monotonic, same-version conflict
rejecting, strict-coverage validating, and secret-free. It does not rewrite the P9-2A
catalog.

MultiNexus owns a focused capacity-authority parser/module. Registry deploy verification
and server smoke verify all three projections independently:

1. roster revision/hash;
2. P9-2A executor source/version/catalog hash and binding ids;
3. P9-3A capacity source/version/catalog hash and complete policy parity.

Deployment order is source file -> existing roster/executor sync -> capacity sync ->
parity verification. A capacity failure leaves no partial capacity projection and
must make deployment/smoke fail closed.

Roster/executor sync and capacity sync are deliberately separate transactions, so a
bounded transitional mismatch can exist between their commits. In P9-3A this is not a
runtime safety authority because claim/agentd do not consume capacity yet, but it is
never an accepted deployed state:

- the deploy script must not write `VERSION_DEPLOYED`, restart the bridge, report
  success, authorize a worker, or run the final smoke until all three projections pass;
- immediately after capacity sync it must run `runtime capacity list` plus the extended
  registry deploy verifier and require exact source/version/hash/policy coverage;
- a verifier failure emits a distinct capacity-parity stage/error, leaves services on
  the previously accepted runtime, and redeploys/resyncs the previously accepted source
  projection before retry; schema rollback follows the backup rules below;
- before overwriting the source, the deploy path captures both the previous authority
  file and an internal canonical capacity-projection snapshot from Coordinate. The
  snapshot is a strict, digest-bound, secret-free v1 object containing either the one
  accepted source plus its complete policy rows, or an explicit `source=null` absence
  marker. It is written outside the repository with mode 0600 and never appears in
  CLI output, events, logs, or implementation fixtures;
- `executor_capacity.py` owns focused internal capture/restore functions. Capture is
  read-only and validates source/policy ids, hashes, coverage, exact policy ids, and
  row shape before emitting canonical bytes. Restore owns one `BEGIN IMMEDIATE`
  transaction, validates the snapshot digest and expected source id, rejects any active
  production lease, then exactly restores the prior source/policies or deletes the
  just-created projection when the snapshot records prior absence. Restore never
  rewrites roster, executor identity, jobs, events, or leases and is not exposed as a
  general public `runtime capacity` subcommand;
- on any post-overwrite remote-parity, roster-sync, executor-sync, capacity-sync,
  capacity-list, or committed-verifier failure, deploy restores the previous authority
  file, replays the previous roster/executor projection, invokes only that Coordinate
  capacity-snapshot restore helper, and verifies the restored three-way state before
  returning nonzero. Missing snapshot, digest mismatch, active lease, restore failure,
  or restored parity mismatch is a separate hard failure and may never be suppressed;
- the initial v1 rollout may observe `capacity source absent` only inside this guarded
  deploy window. A verifier failure after the first successful capacity sync must use
  the explicit absence snapshot to remove the new projection before command exit;
- P9-3B must revisit this window before capacity becomes claim authority and require a
  drained/coordinated update contract rather than inheriting the P9-3A zero-active-lease
  snapshot-restore assumption.

## Module and repository boundary

### Coordinate

Expected new focused modules:

- `src/coordinate/executor_capacity.py` — capacity contract/parser/hash/sync/read;
- `src/coordinate/execution_resources.py` — host-scoped resource normalization;
- `src/coordinate/execution_leases.py` — transaction-aware lease primitives.

Expected focused edits:

- `schema.py` for v13 only;
- `executor_identity.py` only to allow/ignore separately versioned capacity roots;
- `execution_cli.py` and root composition only for `runtime capacity` leaves;
- focused tests/fixtures for capacity, resources, leases, migration, CLI boundary, and
  unchanged P9-2A bytes.

Do not add lease policy to `runtime.py` in P9-3A. No claim/report/progress signature or
behavior changes are allowed.

### MultiNexus

Expected new focused module:

- `multinexus/executor_capacity_authority.py` — capacity projection/parser/hash.

Expected focused edits:

- `config/agent-registry.toml` and capacity fixture;
- `registry_authority.py` only to allow the separate roots while preserving roster and
  executor outputs byte-for-byte;
- deploy verification/sync/smoke scripts and focused tests;
- docs after acceptance.

No agentd worker/client/adapter/session behavior changes are allowed in P9-3A.

## Implementation stages

### Stage A — Authority and unchanged-identity proof

1. Add exact capacity registry/policy contracts in both repositories.
2. Add all current enabled typed instances at capacity 1.
3. Produce byte-identical cross-repository capacity fixture/hash.
4. Prove roster hash, P9-2A executor fixture/hash, every binding id, and exact/routed
   pending-job validation remain unchanged.

### Stage B — Schema and resource identity

1. Add atomic v13 migration and all constraints/indexes.
2. Add strict POSIX/Windows resource normalization and canonical digest.
3. Add migration/rollback/tamper/boundary tests.

### Stage C — Lease primitives and capacity CLI

1. Add transaction-aware reserve/retry/renew/release/expire operations.
2. Prove capacity and same-resource conflicts under two SQLite connections with
   `BEGIN IMMEDIATE` and database constraints.
3. Add atomic capacity sync/list/show CLI and handler ownership/contract tests.
4. Add a deploy fault-injection test that fails between executor and capacity sync,
   proves the capacity-parity stage is explicit, no version/restart/success is emitted,
   and the previous accepted projection is restored before retry.
5. Add strict internal capacity-projection snapshot capture/restore primitives and
   fault injection after a successful first capacity sync but before accepted parity;
   prove the prior-absence snapshot removes the new projection atomically with zero
   active leases and does not add a public restore CLI.

### Stage D — Integration, deploy, and isolated proof

1. Run focused/full/compile/diff/cross-repository/harness gates.
2. Back up production DB, install/migrate Coordinate to v13, and verify deployed source,
   installed import, code schema, DB schema, integrity, and zero lease rows.
3. Sync capacity source v1 and prove roster/P9-2 identity parity unchanged.
4. On a disposable DB, prove capacity 2 permits two distinct resources, rejects a
   third, rejects duplicate resource, renews/replays/releases/expires exactly, and
   rolls back conflicts.
5. Re-run doctor, services/restarts, bounded logs, server smoke, closeout review, and
   terminal host-aware receipt.

## Required tests

### Capacity authority

- exact canonical bytes/hash/policy ids and cross-repository fixture parity;
- strict keys/types/bounds/coverage/duplicates/version/same-version conflict;
- secret-bearing field rejection and redacted CLI output;
- identity roster/catalog/binding hashes unchanged after capacity roots appear;
- exact retry no-write, forward version update, active-lease policy removal rollback.
- snapshot canonical bytes/digest, exact existing-projection restore, prior-absence
  restore, wrong source/tamper/malformed snapshot rejection, active-lease rejection,
  and transaction rollback with no roster/executor/job/event mutation.

### Resource identity

- POSIX dot segments, duplicate/trailing separators, root, Unicode NFC, case behavior;
- Windows drive/UNC, slash direction, casefold, root, dot segments, Unicode NFC;
- same host/equivalent spelling same key; different host different key;
- relative/empty/control/NUL/overlong/unsupported stored version/digest fail closed;
- no filesystem/symlink/environment/current-cwd dependency.

### Schema and lease primitives

- clean v12 -> v13 migration, exact retry, rollback, constraints/indexes/FKs;
- reserve success with exact snapshots and TTL bounds;
- same job/attempt exact replay idempotent; conflicting replay zero-write;
- capacity exhaustion and same-resource collision under separate DB connections;
- distinct resources up to capacity succeed;
- renew only exact active/unexpired lease and move expiry monotonically;
- release/expire idempotency, wrong token/agent/job/lease rejection, newer attempt safety;
- lease expiry alone does not change job state in P9-3A;
- production-style historical terminal jobs produce zero leases.

### Compatibility and boundary

- existing exact/routed submit, claim, progress, result, timeout/recovery suites pass
  without changed runtime behavior;
- P9-2B request/decision/binding/context replay remains exact;
- root CLI remains composition only; new functions live in focused modules;
- MultiNexus agentd/provider/session tests remain byte/behavior compatible;
- full suites add no new baseline failure.

## Review and acceptance gates

### Plan gate

The independent reviewer must challenge:

- whether capacity introduces a second executor identity authority;
- whether adding capacity changes P9-2 catalog/binding bytes;
- migration and active-policy removal behavior;
- path normalization differences across POSIX/Windows and alias limitations;
- transaction ownership, two-connection races, partial unique indexes, and replay;
- premature claim/recovery/heartbeat/P9-4 behavior leaking into P9-3A;
- production install/migration/parity/rollback evidence.

Only an explicit approval of this exact plan SHA-256 may authorize the worker bootstrap.

### Result gate

Codex must independently reproduce canonical hashes, migration, two-connection races,
tamper/replay failures, unchanged P9-2 bytes, full tests, deploy parity, isolated lease
proof, doctor, smoke, and terminal receipt. Worker green tests alone are insufficient.

Any material plan change invalidates approval/bootstrap and returns to plan review.

## Deployment and rollback

- Capture source/upstream SHAs, dirty exceptions, service state, schema/import paths,
  registry/catalog/capacity hashes, and doctor before mutation.
- Create a fresh mode-600 production DB backup and verify checksum/integrity/schema.
- Deploy Coordinate with full install, explicit migration when required, and service
  restart. Verify source SHA, installed package import path, `SCHEMA_VERSION=13`, and
  `PRAGMA user_version=13` independently.
- Deploy MultiNexus capacity authority/parity scripts after Coordinate can consume it.
- Do not create a production execution lease in P9-3A; use a disposable DB sidecar.
- Immediately before the MultiNexus guarded source/sync window, capture the mode-0600
  capacity-only rollback snapshot through the installed Coordinate module and verify
  its digest. This targeted snapshot is the automatic rollback mechanism for the
  separately versioned capacity projection; the full DB backup remains the disaster
  rollback boundary and must not be restored automatically while writers are live.
- Code rollback removes capacity sync from deploy and redeploys the accepted starts.
  Data rollback uses the fresh backup only after stopping writers and assessing events
  after backup. Empty v13 lease/policy tables may remain only if old code tolerates
  them; otherwise restore the backup rather than hand-edit schema/data.

## Non-goals

- Runtime claim/reserve integration, queue scanning, or capacity-aware P9-2 routing;
- managed lease token in claim/progress/report;
- lease heartbeat loop, provider cancellation, or last-activity observation;
- automatic expiry -> recoverable timeout, stale-session resume, or reroute;
- cross-host shared filesystem/symlink/junction physical identity;
- changing executor definition capabilities, P9-2 binding ids, or lifecycle authority;
- production concurrency dogfood (P9-3C/P9-5).

## Stop conditions

Stop and return to Codex if implementation requires any of the following without a
revised independently approved plan:

- changing P9-2 executor catalog hash/binding ids as a consequence of capacity;
- editing `runtime.py` claim/report/progress or MultiNexus agentd/provider behavior;
- direct production JSON/SQLite edits, repair bypass, or legacy mark-done;
- widening path identity to filesystem probes or shared-network assumptions;
- weakening strict authority, migration, transaction, or compatibility gates;
- touching user-owned `.qoder/`, unrelated tasks, or unapproved deployment targets.
