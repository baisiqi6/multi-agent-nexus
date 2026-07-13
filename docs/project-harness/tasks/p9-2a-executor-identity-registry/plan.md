# Detailed Execution Plan: P9-2A Executor Identity Registry

> This is the identity/authority half of P9-2. It introduces durable logical executor
> definitions and concrete instance bindings. It does **not** choose among eligible
> instances; deterministic routing is the separately reviewed P9-2B package.

## Package identity and immutable baselines

- Package: `p9-2a-executor-identity-registry`.
- Parent: `phase-9-execution-isolation` / P9-2.
- Coordinate start:
  `b732159c4a1bbced39dc6ab9cde8841e7959a8cb` on `main == origin/main`.
- MultiNexus start:
  `1d29774016432cf2fbe204ec9d5dc0f1a55ba6ad` on `main == origin/main`.
- Existing Coordinate exception: user-owned untracked `.qoder/` remains untouched.
- Production at planning time:
  - Coordinate deployed/installed `b732159`, schema code/DB `11/11`;
  - MultiNexus deployed `1d29774`;
  - `coordinate.service`, `multinexus-discord-bridge.service`, and four local managed
    agentd services active;
  - server smoke OK;
  - production doctor `projection_ok=true`, `errors=0`, two known superseded-unused
    receipt warnings;
  - P9-1 terminal receipt `e7feda4e-e0d7-4115-9cd0-fe713f87b5d8` consumed.
- Test baselines after P9-1:
  - Coordinate focused P9-1 set: `525 passed, 88 subtests passed`;
  - Coordinate full: `1944 passed, 449 subtests passed` plus exactly nine historical
    CLI-contract/AST failures;
  - MultiNexus full: `461 passed, 2 skipped, 26 subtests passed`.
- Architect/operator/result reviewer: Codex.
- Independent plan reviewer: fresh GLM 5.2 reviewer-only session first; if it does not
  produce a bounded verdict in the configured time window, use a fresh Kimi Highspeed
  reviewer as explicitly authorized by the user.
- Coding worker: a different fresh Kimi Highspeed session in isolated worktrees.
- Provider-native JSONL is primary reviewer/worker activity evidence.

## Why P9-2 is split

The Phase 9 overview combines two changes that have different failure surfaces:

1. define and deploy the identity/authority model;
2. select one eligible instance deterministically.

P9-2A completes (1) and makes existing exact-instance jobs carry an immutable executor
binding. P9-2B will consume that accepted catalog to implement candidate filtering,
load ordering, host preference, and Operator override. This prevents one package from
simultaneously changing schema, registry source hashes, instance identity, routing
selection, replay semantics, and production dispatch.

## Goal

Represent these identities without conflation:

- `ExecutorDefinition`: logical provider/adapter capability, for example
  `omp-code`, `claude-code`, or `opencode-code`.
- `ExecutorInstance`: an existing concrete Coordinate `agents.id`, for example
  `mac-omp`, bound to one logical definition.
- `RunnerProfile`: existing invocation/transport mechanics, referenced explicitly by
  the instance binding instead of being inferred forever from the agent id.
- `ExecutionContext`: P9-1 host/worktree/session authority, unchanged at contract v1.

The accepted end state is:

1. one secret-free MultiNexus authority file defines the Discord roster **and** the
   executor catalog/bindings;
2. Coordinate schema v12 stores an atomically versioned catalog plus instance bindings;
3. existing exact `--target-agent` submission snapshots a versioned executor binding
   when the target is typed;
4. claim validates that immutable binding before status/attempt mutation;
5. MultiNexus strictly consumes the optional binding for typed jobs and confirms that
   the concrete instance and runner profile agree with the claim envelope;
6. legacy untyped exact-instance jobs remain compatible until P9-2B completes catalog
   adoption; they are never eligible for future automatic routing.

## Current-state evidence

### Coordinate

- `agents` already stores concrete id, `host_id`, `capabilities_json`,
  `online_state`, `current_load`, `client_type`, and `last_seen_at`.
- `runner_profiles` is already a separate table, but `register_agent()` creates a
  profile with the same id and `submit_request()` sets both `assigned_agent` and
  `runner_profile_id` to the target agent. The relationship is implicit.
- `jobs` already stores `assigned_agent`, `runner_profile_id`, and JSON payload, so an
  immutable executor-binding snapshot needs no job column.
- Workspace authorization already comes from the effective agent registry; it must not
  be duplicated in a new routing ACL.
- P9-1 context resolution correctly starts from a concrete target instance. P9-2A must
  preserve this path and add identity validation around it, not fold routing into the
  context object.
- `online_state` and `current_load` exist, but temporal heartbeat freshness and
  provider/process liveness are not reliable authorities yet. P9-4 owns that contract.

### MultiNexus

- `config/agent-registry.toml` is the single source-controlled, secret-free roster
  authority; deploy verifies it against private runtime configuration and projects it
  into Coordinate.
- The current authority schema knows only id/display name/Discord id/type. It has no
  logical executor definitions or instance-to-runner binding.
- `AgentConfig.adapter` and private provider/model/bin fields are runtime mechanics, not
  a durable cross-project routing authority.
- Agentd validates the P9-1 claim envelope but currently has no executor binding to
  compare with its concrete identity.

## Contract decisions

### 1. One source file, two canonical projections

Extend `config/agent-registry.toml`; do not create a second project-level config.

```toml
[registry]
id = "multinexus.discord"
version = 2

[[executor_definitions]]
id = "omp-code"
provider = "kimi-code"
adapter = "omp"
capabilities = ["coding", "review"]

[[agents]]
id = "mac-omp"
display_name = "Mac OMP"
discord_user_id = "..."
executor_definition_id = "omp-code"
runner_profile_id = "mac-omp"
```

- Existing roster projection/hash remains backward-compatible and continues to drive
  workspace Discord authorization.
- A new `executor_catalog_hash` is canonical JSON over definitions and managed
  instance bindings. It is not a second source of truth; it is a second projection
  from the same versioned file.
- `[registry].version` is incremented to `2`. Same-version/different-hash and version
  downgrade fail closed independently for the executor catalog.
- External agents may remain visible roster entries but may not carry executor
  bindings in P9-2A.

### 2. Coordinate schema v12

Add exactly three tables; do not alter `jobs`, `agents`, or `runner_profiles` columns:

```text
executor_catalog_sources
  source_id PK, source_version, catalog_hash, source_path, updated_at

executor_definitions
  id PK, source_id, provider, adapter, capabilities_json, metadata_json,
  created_at, updated_at

executor_instance_bindings
  agent_id PK, source_id, executor_definition_id, runner_profile_id, enabled,
  created_at, updated_at
```

Requirements:

- foreign keys bind definitions to their catalog source and bindings to existing
  agents/definitions/runner profiles;
- definitions and bindings are replaced atomically per source;
- a source may update only rows it owns; id/source takeover fails closed;
- duplicates, unknown keys, missing referenced agents/profiles/definitions, external
  bindings, non-agentd instances, version downgrade, or same-version hash conflict
  cause zero mutation;
- schema migration is `11 -> 12`, atomic and idempotent, with fresh/install/upgrade
  tests and no migration-time inference from private config.

### 3. `ExecutorBinding` v1 snapshot

Coordinate owns serialization; MultiNexus owns an independent strict consumer.

```json
{
  "contract_version": 1,
  "binding_id": "sha256:<canonical digest>",
  "source_id": "multinexus.discord",
  "source_version": 2,
  "catalog_hash": "<64-hex>",
  "executor_definition_id": "omp-code",
  "executor_instance_id": "mac-omp",
  "runner_profile_id": "mac-omp",
  "provider": "kimi-code",
  "adapter": "omp",
  "capabilities": ["coding", "review"]
}
```

- Stable digest excludes `binding_id`; keys/types are exact; capabilities are a sorted,
  unique, bounded list.
- The snapshot is stored at `jobs.payload_json.executor_binding` next to the P9-1
  execution context.
- Existing context v1 bytes/digest remain unchanged.
- For a typed target, submit validates the current catalog and snapshots the binding
  before `request.received` or job creation.
- Idempotent replay compares the original exact target/prompt/origin/reply plus stored
  binding request; it returns the original snapshot and never silently upgrades to a
  newer catalog.
- Claim validates the stored binding against job `assigned_agent` and
  `runner_profile_id`, then verifies the current binding still has the same source,
  definition, instance, runner profile, and catalog hash. Mismatch fails before CAS.
- `job.claimed` records binding id, definition id, instance id, runner profile, and
  source version/hash without secrets.
- Legacy exact targets with no catalog binding keep `executor_binding=null`; this is a
  deliberate migration compatibility path and is excluded from P9-2B auto routing.

## Implementation stages

### Stage A — Coordinate identity catalog authority

Create `src/coordinate/executor_identity.py` containing:

- immutable definition/binding v1 value objects and canonical digest helpers;
- strict catalog input validation;
- atomic `sync_executor_catalog()`;
- definition/binding reads;
- `resolve_exact_executor_binding()` and persisted-binding validation.

This is the concrete P9-2 consumer that justifies an agent-registry repository seam.
Keep SQL owned by this module; do not introduce a generic repository framework, ORM,
plugin loader, or dependency-injection layer. `db.py` remains a compatibility facade
only where existing imports require it.

Add execution CLI leaves under the already extracted `execution_cli` composition:

- `runtime executor sync --source-json ...` (server-side, atomic projection sink);
- `runtime executor list` (redacted definitions/bindings/source metadata);
- `runtime executor show <instance-id>`.

CLI rules:

- stdout remains one JSON document on success/failure paths owned by the command;
- no secrets or private command/env/model fields are accepted;
- existing parser order/help bytes remain unchanged except for deliberate new leaves;
- sync returns source/version/catalog hash plus added/updated/removed/unchanged ids.

### Stage B — Exact-instance job binding

Update `runtime.submit_request()` and `claim_job()`:

- preserve `--target-agent` as the required exact-instance API in P9-2A;
- resolve an optional typed binding before any event/job write;
- persist and return `executor_binding` beside `execution_context`;
- bind job `runner_profile_id` to the catalog binding for typed targets instead of
  assuming it equals the instance id;
- preserve legacy behavior when the exact target is untyped;
- make replay/current-binding mismatch rules explicit and fail closed before mutation;
- add executor identity evidence to `job.claimed`.

Do not add `--executor-definition`, capability selection, host preference, candidate
ranking, rerouting, capacity checks, or leases in this package.

### Stage C — MultiNexus single-authority projection

Extend `multinexus/registry_authority.py` and
`config/agent-registry.toml`:

- strict `executor_definitions` root schema;
- managed-entry definition/profile binding fields;
- independent roster and executor-catalog canonical projections/hashes;
- registry version `2`;
- deterministic errors for duplicate definition ids, capability duplicates,
  missing bindings, unknown references, external bindings, and secret-bearing keys.

Update `scripts/agent_registry_deploy_verify.py` and `scripts/deploy-server.sh` so a
deployment:

1. validates the one source file locally;
2. preserves existing roster parity;
3. syncs the executor catalog through the new Coordinate CLI;
4. re-reads Coordinate and proves source id/version/catalog hash plus exact binding
   parity before writing `VERSION_DEPLOYED` or restarting.

The private `agents.toml` is not rewritten and gains no new required secret or routing
fields in P9-2A. The canonical binding references existing concrete ids/profile ids.

### Stage D — MultiNexus typed-claim validation

Create `multinexus/agentd/executor_binding.py` with an independent strict v1 parser.

- A typed claim must match job assigned agent, runner profile, and configured agent id
  before adapter invocation.
- A malformed or mismatched binding fails the job closed with a bounded error and the
  current attempt token.
- An absent binding remains accepted only for a legacy exact-instance job.
- Result JSON includes `executor_binding_id`, definition id, and runner profile for
  typed jobs; no provider credentials or command/env details.
- Do not change adapter interfaces or P9-1 execution-context bytes.

### Stage E — Contract, deployment, and dogfood

- Add byte-identical `executor_binding_v1.json` fixtures to both repositories and pin
  their SHA-256.
- Add schema v11->v12 upgrade/failure atomicity tests.
- Add source authority, deploy parity, exact typed/legacy submit, replay, claim, and
  consumer mutation matrices.
- Back up production DB, deploy Coordinate with a full reinstall, and independently
  verify:
  - source SHA;
  - installed package path;
  - code schema `12`;
  - DB `PRAGMA user_version=12`;
  - new tables/foreign keys;
  - service restart boundary.
- Deploy MultiNexus and require catalog parity before restart.
- Production dogfood:
  1. existing untyped/exact compatibility probe in isolated data;
  2. real typed `mac-omp` exact-instance job;
  3. assert request/job/claim/result binding id and P9-1 context id remain stable;
  4. exact sentinel delivery;
  5. current binding tamper/mismatch fails before claim CAS in an isolated sidecar DB.
- Finish with source/deployed fingerprint equality, production doctor, terminal
  receipt, and durable closeout docs.

## Required tests and adversarial probes

### Coordinate

- schema fresh v12, upgrade v11->v12, repeated initialize, rollback on invalid legacy
  state, foreign keys/indexes/user_version;
- catalog strict key/type/length/duplicate/reference matrix;
- atomic source version/hash/ownership conflict matrix;
- typed exact submit preflight has zero event/job mutation on failure;
- typed snapshot digest and byte fixture;
- legacy exact target remains accepted with null binding;
- replay returns original binding after catalog remains identical and rejects changed
  exact request without rerouting/upgrading;
- claim rejects missing/extra/wrong-type/digest/job-instance/runner/current-catalog
  mismatch before attempt/status mutation;
- job.claimed evidence contains no prompt, command, env, token, or credentials;
- old public imports and full CLI contract baseline remain unchanged.

### MultiNexus

- strict source authority matrix and both canonical hashes;
- deploy preflight blocks source/runtime/catalog mismatch before version write/restart;
- strict binding parser mutation matrix and byte-identical fixture;
- typed worker no-adapter failure for instance/profile/digest mismatch;
- legacy null-binding exact job compatibility;
- P9-1 cwd/session assertions remain intact.

### Cross-repository/static

- Coordinate production modules do not import MultiNexus;
- MultiNexus does not import Coordinate Python modules or read Coordinate SQLite in
  the managed path;
- no provider-specific branches in Coordinate route/binding core;
- no candidate selection or lease/capacity behavior in the P9-2A diff;
- both full suites, compileall, diff check, schema/source/installed/deployed gates.

## Compatibility and rollback

- Existing exact `--target-agent` callers, Discord mentions, handoffs, lifecycle,
  receipt, P9-1 context v1, and provider adapters remain compatible.
- Typed catalog adoption is additive. Untyped exact targets remain valid only as the
  documented migration path; P9-2B will decide the final enforcement date.
- Registry source remains one file; old roster projection is preserved.
- Rollback requires restoring both deployed commits and the pre-deploy DB backup.
  Because schema v12 adds tables only, old code may ignore them, but rollback evidence
  must still verify installed package and DB identities explicitly.

## Non-goals

- Automatic executor selection, capability routing, host preference, load ordering,
  Operator override routing, rerouting, or queueing (P9-2B).
- Capacity, attempt/worktree leases, fairness, or stale-lease recovery (P9-3).
- Heartbeat freshness, provider JSONL/process liveness, or failure taxonomy (P9-4).
- Provider/model/bin/credential cataloging in Coordinate.
- Adapter redesign, vendor subagent introspection, scheduler frameworks, plugin
  discovery, ORM, or a second control plane.

## Acceptance and stop conditions

Accept only when:

1. schema v12 and the one-source executor catalog are atomic and independently tested;
2. typed exact jobs carry one immutable binding from submit through claim/result;
3. legacy exact jobs remain compatible but are visibly untyped;
4. MultiNexus rejects malformed typed bindings before provider invocation;
5. deployment proves source/installed/schema/DB/catalog parity;
6. real typed production job and sentinel delivery pass;
7. production doctor has no new errors, terminal receipt is consumed, and docs are
   durably closed.

Stop and return `changes_requested` if the implementation introduces automatic
selection, duplicates workspace authorization, stores secrets/provider commands in
Coordinate, changes P9-1 context bytes, silently infers catalog identity from private
runtime config, weakens replay/claim CAS, or exceeds the listed files/contracts without
a revised and re-reviewed plan.

## P9-2B handoff

After P9-2A closes, P9-2B may add deterministic routing over typed instances only:
workspace authorization, recorded health, host readiness/preference, effective load,
stable tie-break, and exact Operator override. It must not begin before this catalog,
binding snapshot, deployment parity, and compatibility path are accepted.
