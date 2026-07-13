# Detailed Execution Plan: P9-2B Deterministic Executor Routing

> P9-2B consumes the accepted P9-2A executor catalog and selects one concrete typed
> instance for an explicitly routed request. It is a deterministic submission policy,
> not a general scheduler. Capacity leases, stale-health authority, automatic reroute,
> and resource exclusion remain P9-3/P9-4 work.

## Package identity and accepted baselines

- Package: `p9-2b-deterministic-executor-routing`.
- Parent: `phase-9-execution-isolation` / P9-2.
- Coordinate start:
  `eec9b233f6c797c73aec9d535fa723e037a0af65` on `main == origin/main`.
- MultiNexus start:
  `7a06573f8c17c4376c272a68b1201d5c4320675d` on `main == origin/main`.
- Existing Coordinate exception: user-owned untracked `.qoder/` remains untouched.
- Accepted runtime baseline:
  - Coordinate schema/code/production DB v12;
  - one source-controlled executor authority, source `multinexus.discord`, version 2,
    catalog hash
    `f4cdf79897755c173e97ddae1dfd88047436039f3447d4d6257105715ba5551d`;
  - P9-1 immutable `ExecutionContext` v1 and P9-2A immutable
    `executor_binding` v1 are deployed and dogfooded;
  - P9-2A terminal receipt `56addb44-f72b-4e31-bdab-a230c59fe9d6` is consumed;
  - production doctor is `projection_ok=true`, errors 0, with two known superseded
    unused historical receipt warnings;
  - Coordinate and `multinexus-discord-bridge` are active with `NRestarts=0`.
- Accepted test baseline:
  - Coordinate full: 1998 passed, 461 subtests, plus exactly the same nine historical
    CLI-contract/AST baseline failures;
  - Coordinate focused P9-2A recurrence: 250 passed, 43 subtests;
  - MultiNexus full: 503 passed, 2 skipped, 36 subtests.
- Architect/operator/result reviewer: Codex.
- Independent plan reviewer: fresh GLM 5.2 reviewer-only session first; use ordinary
  `Kimi for Coding` if GLM does not produce a bounded verdict, then the agreed lower
  priority fallback chain.
- Coding worker: a separate fresh ordinary `Kimi for Coding` session
  (`kimi-code/kimi-for-coding`). The `highspeed` variant is forbidden for this and
  later packages unless the user explicitly changes the preference.
- Provider-native JSONL/session events are primary live-activity evidence. Process
  state and repository artifacts corroborate activity; a quiet diff alone does not
  prove inactivity.

## Current-state audit

### Accepted authority already present

- `executor_catalog_sources`, `executor_definitions`, and
  `executor_instance_bindings` are the durable P9-2A identity projection.
- Every enabled managed binding resolves to one concrete `agents.id`, one logical
  definition, and one `runner_profile_id`.
- Exact `runtime request submit --target-agent ...` snapshots both the P9-1 execution
  context and P9-2A executor binding before the first durable write.
- Claim validates the stored binding and context before its status/attempt CAS.
- MultiNexus agentd validates the same claim envelope before provider invocation.
- `resolve_effective_agents()` is the existing workspace authorization authority; no
  routing ACL may duplicate it.

### Gaps P9-2B owns

- `submit_request()` requires one concrete target and has no explicit routed mode.
- No canonical routing-request or routing-decision envelope exists.
- No policy filters typed bindings by required capabilities and workspace authority.
- No stable candidate order combines explicit host preference and recorded load.
- Idempotency keys for exact requests include the concrete target. A routed request
  needs a key that is stable before a target is selected and must replay the original
  decision without rerouting.

### Facts P9-2B must not misrepresent

- `agents.current_load` is initialized to zero and currently has no writer. It is not
  an accepted load authority.
- `last_seen_at` exists, but P9-4 has not defined freshness windows or provider/process
  liveness. P9-2B must not invent a stale-heartbeat cutoff.
- P9-3 has not added capacity, attempt leases, queue fairness, or worktree exclusion.
  Routing to the lowest observed load is an ordering policy only, not a concurrency
  guarantee.
- Exact assignment remains immutable after submission. P9-2B does not reassign a
  pending/running/timed-out job when state changes.

## Goal

Add one explicit deterministic routed-submission mode that:

1. accepts bounded required capabilities plus optional definition and host preference;
2. filters only typed, enabled, workspace-authorized, structurally ready, recorded-
   online agentd instances;
3. ranks candidates by explicit host preference, Coordinate-derived nonterminal job
   load, then stable identity;
4. supports an exact Operator override among the same eligible candidates without
   bypassing authorization, binding, health, or host readiness;
5. snapshots the request, complete candidate evidence, selected decision, P9-2A
   binding, and P9-1 context into one atomic event/job creation;
6. replays the original decision by idempotency key without consulting current load or
   selecting again;
7. leaves the exact `--target-agent` path and MultiNexus claim contract compatible.

## Contract decisions

### 1. Routed mode is explicit and mutually exclusive with exact mode

The public CLI keeps exact mode:

```text
coordinate runtime request submit <workspace> --target-agent <agent-id> ...
```

and adds routed mode:

```text
coordinate runtime request submit <workspace> \
  --route-capability coding [--route-capability review] \
  [--route-definition <definition-id>] \
  [--preferred-host <host-id>] \
  [--override-agent <agent-id> --override-reason <text>] ...
```

Rules:

- exactly one of `--target-agent` or one-or-more `--route-capability` is required;
- route capabilities are bounded labels, sorted and unique after normalization;
- `--route-definition` and `--preferred-host` are optional bounded labels;
- `--override-agent` is valid only in routed mode and requires an audit reason whose
  stripped UTF-8 text is 1–512 Unicode characters with no control characters;
- exact mode does not silently become routed when an agent is missing/offline;
- routed mode never infers requirements from prompt text, Discord mentions, private
  `agents.toml`, provider/model settings, or task owner.

The Python API adds one optional validated routing request while preserving keyword
compatibility for all exact callers. It must reject exact-plus-routed and neither-mode
calls before writes.

### 2. Canonical `routing_request` v1

The stored request is exact-shape canonical JSON:

```json
{
  "contract_version": 1,
  "mode": "deterministic",
  "required_capabilities": ["coding"],
  "executor_definition_id": null,
  "preferred_host_id": "macbook-local",
  "operator_override_agent_id": null,
  "operator_override_reason": null,
  "policy_version": 1,
  "routing_request_id": "sha256:<digest>"
}
```

- `routing_request_id` is SHA-256 over canonical UTF-8 JSON excluding its own field,
  with sorted object keys and `separators=(",", ":")`.
- Override id and reason must both be null or both non-null.
- The reason follows the exact 1–512-character rule above and is audit text, not a
  command, prompt, credential, or policy expression.
- Unknown/missing keys, booleans-as-integers, unsafe labels, duplicate capabilities,
  invalid digests, and unsupported versions fail closed.

### 3. Hard eligibility filters

Build candidates from Coordinate tables at submission time. An automatic or override
candidate is eligible only when all conditions hold:

1. an enabled `executor_instance_bindings` row exists;
2. its definition exists and contains every required capability;
3. it matches optional `executor_definition_id` exactly;
4. its concrete `agent_id` is present in the workspace's current
   `resolve_effective_agents()` result;
5. the runtime agent exists, has `client_type='agentd'`, and
   `online_state='online'`;
6. `host_id` is nonempty and the workspace has a host profile for it;
7. the bound runner profile exists, has `runner_type='agentd'`, and the full P9-2A
   binding snapshot resolves successfully.

`last_seen_at` freshness is intentionally not a P9-2B filter. The selected decision
records it as non-authoritative evidence when present. P9-4 will define whether and how
freshness becomes a liveness gate.

No candidate means a machine-readable `executor_route_no_candidate` error before any
event/job mutation. An override outside the eligible set returns
`executor_route_override_ineligible`, also before writes. Operator override changes
selection, not eligibility.

### 4. Deterministic load and ordering

P9-2B derives `routing_load` from Coordinate-owned jobs rather than the unwritten
`agents.current_load` field:

```text
routing_load = count(jobs assigned to candidate where
                     status in {pending, running} or
                     (status == timed_out and recoverable == 1))
```

Automatic candidates sort by this exact tuple:

```text
(
  0 if candidate.host_id == preferred_host_id else 1,
  routing_load,
  executor_definition_id,
  agent_id,
)
```

When no preferred host is supplied, every candidate receives host rank zero. The
lexicographically first tuple wins. An exact override selects the named eligible
candidate and records that load/host ordering was overridden.

This snapshot is deterministic for one observed DB state. Concurrent submissions may
legitimately observe the same pre-P9-3 load and select the same instance; P9-2B must
not claim capacity or fairness guarantees.

### 5. Canonical `routing_decision` v1

Persist enough secret-free evidence to audit selection without reconstructing mutable
runtime state. The exact-shape decision contains:

- `contract_version=1`, `policy_version=1`, and `routing_request_id`;
- `selection_kind` as `automatic` or `operator_override`;
- `selected_agent_id`, `selected_host_id`, `selected_runner_profile_id`,
  `selected_executor_definition_id`, and `selected_binding_id`;
- `eligible_candidates`, already sorted by the policy tuple, each with exactly:
  - agent/host/runner/definition/binding ids;
  - source id/version and catalog hash;
  - sorted capabilities;
  - recorded `online_state` and optional `last_seen_at`;
  - `preferred_host` boolean and integer `routing_load`;
- `routing_decision_id=sha256:<digest>` over the canonical decision excluding its own
  id.

The candidate list is capped at 256 entries. Exceeding the cap fails closed before
writes rather than truncating audit evidence. No prompt, environment, command, token,
provider-native session id, or secret runtime field enters this envelope.

### 6. Atomic creation and immutable replay

For a first routed request:

1. validate workspace, prompt, destinations, and routing request;
2. resolve and validate the complete candidate/decision snapshot before writes;
3. resolve the selected P9-2A binding and P9-1 execution context before writes;
4. append `request.received` and create the pending job in the existing transaction;
5. commit both or neither.

The event target and compatibility `payload.target_agent` are the selected concrete
agent. Both event and job payload add the exact same `routing_request` and
`routing_decision`; the job also retains its binding/context snapshots.

The default routed idempotency key is computed from workspace + origin identity +
`routing_request_id`, never from the selected agent. On replay:

1. look up the existing request event before reading candidates or current load;
2. require exact prompt/origin/reply/task/routing-request equality;
3. load the existing derived job and validate its stored decision/binding/context
   shape and internal links;
4. return the original event/job with `created=false` and do not reroute, rewrite, or
   append another decision event.

Reusing an explicit idempotency key across exact/routed modes or different request
content is a conflict with zero mutation. A malformed stored routing envelope fails
closed; it is never repaired implicitly during replay or claim.

### 7. Assignment and claim remain concrete

- `jobs.assigned_agent` and `runner_profile_id` store the selected concrete values.
- Claim remains agent-scoped and does not execute routing.
- `job.claimed` adds `routing_request_id`, `routing_decision_id`, and
  `selection_kind` when a routed snapshot exists; exact jobs remain byte-compatible.
- Report/progress/delivery retain the selected assignment and existing attempt-token
  authority.
- Same-job timed-out recovery never reroutes and retains the same concrete assignment,
  decision, binding, context, and attempt-token authority. The generic `job retry`
  command creates a new job id and therefore cannot safely copy a P9-1 context snapshot;
  it must reject routed runtime jobs with
  `routed_runtime_retry_requires_explicit_resubmission` before writes. A new routed
  submission with a new idempotency identity is the only P9-2B retry path.
- MultiNexus receives the already accepted P9-1/P9-2A claim contract plus additive
  redacted route ids. It neither filters candidates nor reads Coordinate SQLite.

## Module and repository boundary

### Coordinate

Add `src/coordinate/executor_routing.py` as the sole owner of:

- routing request/decision contracts and canonical hashes;
- workspace-authorized candidate resolution;
- deterministic load calculation and ordering;
- stored decision validation and claim evidence.

Keep `executor_identity.py` authoritative for catalog/binding identity. It may expose a
small public bounded-capability/label validator rather than duplicating grammar.

Keep `runtime.py` as orchestration only:

- distinguish exact versus routed submission;
- call the routing resolver;
- preserve atomic event/job creation and immutable replay;
- attach additive claim evidence.

Keep `execution_cli.py` as parsing/printing only. Do not move policy into CLI handlers.
No new schema table or column is planned. Do not add routing logic to MultiNexus.

Expected Coordinate files:

- `src/coordinate/executor_routing.py` (new);
- `src/coordinate/runtime.py`;
- `src/coordinate/executor_identity.py` only for a minimal shared public validator;
- `src/coordinate/execution_cli.py`;
- `tests/test_executor_routing.py` (new);
- focused additions to `tests/test_runtime.py`, `tests/test_execution_cli.py`, and CLI
  contract fixtures/tests;
- cross-repository claim fixture only if the additive route ids alter the accepted
  envelope fixture.

### MultiNexus

No runtime implementation change is expected. If Coordinate's claim fixture gains
additive route ids, update only the shared fixture/consumer validation tests and prove
that existing exact typed and legacy claims remain accepted. Product/harness docs are
updated after implementation acceptance.

Any need for schema v13, MultiNexus candidate logic, direct DB reads, new registry
authority, or a broader runtime refactor requires a revised plan and independent
re-review before implementation continues.

## Implementation stages

### Stage A — Contract and pure selector

1. Add exact routing dataclasses/validators/canonical hash helpers.
2. Add candidate query using existing catalog, runtime agent, workspace registry,
   runner profile, host profile, and job tables.
3. Add automatic ordering and exact eligible override.
4. Add stored request/decision link validation and redacted claim evidence.
5. Prove all invalid/no-candidate/override failures are zero-write.

### Stage B — Runtime submission and replay

1. Extend `submit_request()` with explicit mutually exclusive modes.
2. Add routed default idempotency and lookup-before-selection replay.
3. Store one decision consistently in event/job/binding/context links.
4. Keep exact submission behavior and legacy untyped exact compatibility unchanged.
5. Add additive route ids to claim evidence; do not move selection to claim.

### Stage C — CLI and compatibility surface

1. Add the mutually exclusive routed flags and override reason gate.
2. Update CLI handler ownership/hash/contract fixtures intentionally.
3. Update runbook examples and machine-readable output expectations.
4. If required, update the MultiNexus claim fixture and consumer tests without adding
   routing policy there.

### Stage D — Integration, deployment, and dogfood

1. Run focused, full, compile, diff, harness, and cross-repository gates.
2. Backup production DB even though schema stays v12.
3. Deploy/install/restart Coordinate first; deploy MultiNexus only if its accepted
   consumer fixture/code changed.
4. Prove source/deployed/installed module hashes and schema/catalog parity.
5. Submit a real routed request without `--target-agent`, record its selected candidate,
   binding/context/decision ids, exact sentinel, completed event, and sent platform
   delivery.
6. Run a second bounded Operator-override routed request only if it can use an already
   proven healthy non-Codex instance without consuming scarce Codex quota.
7. Re-run production doctor, service/restart/log breakers, then normal closeout review
   and host-aware terminal receipt.

## Required tests

### Pure contract and candidate tests

- exact canonical request/decision bytes and digests;
- unknown/missing keys, invalid versions/digests/types/labels, duplicate or unsorted
  capabilities, overlong reason, and candidate cap;
- capability superset and optional definition filters;
- workspace authorization, binding enabled, agentd type, online state, host profile,
  runner profile, and resolvable binding hard filters;
- `last_seen_at` is recorded but does not create an undeclared freshness gate;
- routing load includes pending/running/recoverable-timed-out and excludes terminal or
  nonrecoverable timed-out jobs;
- preferred-host, load, definition, and agent stable tie ordering;
- override selects only an eligible candidate and records the reason/kind;
- zero-candidate and ineligible-override failures mutate no event/job state.

### Runtime and replay tests

- exact mode remains unchanged for typed and untyped targets;
- exact-plus-route and neither-mode fail before writes;
- first routed submit atomically stores identical request/decision in event and job,
  selected concrete assignment, binding, and execution context;
- route event/job/binding/context ids cross-link exactly;
- default routed key is target-independent and request-dependent;
- exact replay returns original selection after load/host preference changes and
  creates no new event/job;
- prompt/origin/reply/task/request/idempotency conflicts fail with zero mutation;
- malformed stored request/decision/digest/candidate/selected links fail closed;
- claim validates route links before CAS and emits additive redacted ids;
- claim mismatch does not change status/attempt or invoke MultiNexus;
- same-job recovery preserves the original concrete decision and stale-attempt rules;
- generic `job retry` rejects routed runtime jobs before creating an invalid new-job/
  old-context combination.

### CLI and cross-repository tests

- argparse mutual exclusion and conditional override reason;
- CLI JSON exposes selected assignment and immutable decision without secrets;
- CLI contract fixtures and handler ownership hashes update intentionally;
- MultiNexus existing P9-1/P9-2A validation remains green;
- if route ids are consumed, missing legacy ids remain compatible while malformed
  present ids fail before adapter invocation;
- exact typed, exact legacy, routed typed, and replay fixtures are covered.

## Review and acceptance gates

### Plan gate

- Independent reviewer returns bounded `approved` or actionable
  `changes_requested` against this exact plan SHA.
- Reviewer must challenge authority duplication, load/health claims, replay ordering,
  override bypasses, race/capacity overclaims, event/job atomicity, and P9-3/P9-4 scope.
- Only an approved plan may produce `worker-bootstrap.md` and task assignment.

### Result gate

Codex reviews the complete diff and must verify:

- routing is explicit and absent from exact mode/claim/MultiNexus policy;
- every hard filter uses an existing authority and fails closed;
- `agents.current_load` and heartbeat freshness are not falsely promoted to authority;
- selection ordering and canonical envelopes are exact and deterministic;
- replay looks up the old decision before current candidate selection;
- override cannot bypass eligibility;
- no capacity, lease, fairness, or automatic reroute claim leaked from P9-3/P9-4;
- full baselines, cross-repo tests, deployment parity, dogfood, doctor, and receipt pass.

Any `changes_requested` round returns to a fresh worker correction bootstrap. Codex does
not approve its own unreviewed plan amendment or silently widen scope.

## Deployment and rollback

- Capture Coordinate/MultiNexus SHAs, dirty-state exceptions, schema/catalog hashes,
  service state, and production doctor before mutation.
- Create a fresh mode-600 SQLite backup and verify checksum, integrity, and schema.
- Deploy Coordinate with full install/restart because runtime/CLI code changes.
- If MultiNexus has no runtime diff, sync only accepted docs/fixtures and do not restart
  its service unnecessarily.
- Bounded post-deploy checks: CLI help/contract, exact request smoke, routed request,
  claim/provider result/delivery, doctor, integrity, service `NRestarts`, and logs.
- Code rollback redeploys Coordinate `eec9b23` and the accepted MultiNexus baseline.
- No schema rollback is expected. Before code rollback, drain or terminally resolve any
  routed pending/running jobs because old code does not validate their routing envelope.
- If a routed production job has not been claimed, cancellation is preferred over
  editing its immutable assignment or payload.

## Non-goals

- Capacity limits, executor/worktree leases, fair queues, or concurrent selection
  serialization (P9-3).
- Heartbeat freshness, provider process/session liveness, JSONL activity semantics, or
  provider failure taxonomy (P9-4).
- Automatic reroute, failover, speculative execution, hedging, or dynamic workflows.
- Prompt classification, model selection, price/latency optimization, or provider-
  specific policy in Coordinate.
- Rewriting the source-controlled catalog, private runtime config, P9-1 context, P9-2A
  binding, or lifecycle/receipt authorities.
- Treating executor-internal subagents as Coordinate-managed jobs.

## Package acceptance

P9-2B is complete only when all are true:

1. detailed plan and any amendments have independent approval;
2. explicit routed mode selects only eligible typed instances with exact deterministic
   evidence and zero-write failures;
3. immutable replay returns the original selection before consulting current routing
   state;
4. exact typed and legacy paths remain compatible;
5. Coordinate and MultiNexus focused/full/cross-repository gates pass against accepted
   baselines;
6. producer-first deployment proves source/installed/schema/catalog parity;
7. a real no-`--target-agent` routed job completes through a non-Codex executor and its
   visible delivery is sent;
8. production doctor has zero errors, services are stable, docs are durable, and the
   terminal receipt is consumed.

## P9-3 handoff boundary

After P9-2B closes, P9-3 may replace observed-load ordering with explicit capacity and
resource leases, define same-worktree mutual exclusion, serialize/queue contending
attempts, and recover stale leases. It must consume the immutable P9-2B decision and
P9-1 context rather than creating a second routing or workspace authority.
