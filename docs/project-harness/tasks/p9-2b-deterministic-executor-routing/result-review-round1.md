# P9-2B Codex result review — Round 1

Date: 2026-07-13
Reviewer: Codex operator/result reviewer
Worker: ordinary Kimi `kimi-code/kimi-for-coding`
Worker JSONL session: `019f5aff-9634-7000-9cc0-94b76aec5989`
Reviewed plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
Verdict: **REJECT — correction required before commit, integration, deploy, or lifecycle closeout**

## What passed

- The worker stayed in the two isolated P9-2B worktrees and did not push, deploy,
  cherry-pick, or modify either `main` checkout.
- Routing policy is located in the new Coordinate module
  `src/coordinate/executor_routing.py`; MultiNexus did not acquire candidate selection
  or Coordinate routing policy.
- Candidate discovery uses typed enabled bindings, workspace authorization, agentd
  online state, host profiles, runner profiles, and the P9-2A binding resolver.
- Routing load is derived from Coordinate jobs rather than `agents.current_load`, and
  no P9-4 heartbeat-freshness threshold was introduced.
- Routed replay performs its initial idempotency-event lookup before candidate/load
  resolution.
- The worker reported:
  - focused Coordinate: `177 passed, 17 subtests passed`;
  - full Coordinate: `2043 passed, 461 subtests passed` plus the same nine historical
    CLI-contract/AST failures proven against `main`;
  - focused MultiNexus claim/context tests: `98 passed, 2 skipped`;
  - full MultiNexus: `503 passed, 2 skipped, 36 subtests passed`.

Passing tests do not clear the fail-closed and immutable-link blockers below.

## Must-fix findings

### R1-1 — caller normalization has weakened strict stored-request validation

`build_routing_request()` and `parse_routing_request()` currently share the same
sorting/deduplication helper. The builder should normalize API/CLI input, but a stored
canonical envelope must reject noncanonical bytes and booleans-as-integers.

Direct probes were all accepted:

```text
REQUEST_ACCEPTED bool_contract_version
REQUEST_ACCEPTED unsorted_capabilities
REQUEST_ACCEPTED duplicate_capabilities
REQUEST_ACCEPTED noncanonical_reason
```

Required correction:

- Separate caller-input normalization from strict stored-envelope parsing.
- API/CLI input may be in any order and may repeat capabilities; persist one sorted,
  unique canonical list.
- Stored `routing_request` parsing must require exact canonical order/uniqueness and
  exact canonical stripped reason text, reject `bool` for integer fields, and reject
  all noncanonical types/values even if a digest over normalized content would match.
- Validate a passed `RoutingRequest` object through the same strict canonical round
  trip; a manually constructed dataclass must not bypass validation.
- Add a mutation matrix covering every key, type, version, digest, label, pair,
  whitespace, duplicate, and order rule.

### R1-2 — stored routing decisions are not exact-shape or policy-link validated

`validate_routing_decision()` checks the outer keys and digest but does not validate
the exact candidate schema, scalar types, candidate order, capability canonicality,
selection-kind/request relationship, or most selected links. Recomputing the digest
made all of these malformed envelopes pass:

```text
DECISION_ACCEPTED unknown_candidate_key
DECISION_ACCEPTED boolean_routing_load
DECISION_ACCEPTED selection_kind_request_mismatch
```

`Candidate.sort_key(None)` also assigns host rank `1`, while the approved contract
requires rank `0` for every candidate when no preferred host is supplied.

Required correction:

- Validate exact candidate keys, types, nullability, safe labels, source version,
  catalog hash, sorted unique capabilities, `online_state`, optional `last_seen_at`,
  real nonnegative integer load, and real boolean `preferred_host`.
- Reject duplicate candidates and require the complete list to be in the exact policy
  order for the stored request; require one and only one selected candidate.
- Bind `selection_kind` to the request's override pair and require the selected agent
  to equal the override when present.
- Validate every top-level selected field against the selected candidate.
- Make serialization self-contained so passing a different preferred-host argument
  cannot produce candidate bytes that disagree with the already-computed decision
  digest.
- Fix and test no-preference host rank zero plus definition-id and agent-id tie breaks.

### R1-3 — claim accepts forged decision-to-binding and decision-to-context links

The P9-2A binding and P9-1 context are each validated, but routing evidence only
compares the decision's selected agent and runner to the job row. A recomputed valid
decision digest can therefore point at a different binding or host while claim still
crosses the CAS:

```text
CLAIM_ACCEPTED_FORGED_BINDING True
CLAIM_ACCEPTED_FORGED_HOST True
```

Required correction:

- Before claim CAS, bind selected binding/definition/runner/agent/source/catalog
  fields to the stored P9-2A binding snapshot.
- Bind selected host/agent/job/workspace/task fields to the stored P9-1 context and
  current claimed job envelope.
- Validate the selected candidate's full public identity evidence against those same
  snapshots.
- Treat either one-sided routing field, any malformed envelope, or any cross-link
  mismatch as a zero-status/zero-attempt/zero-event failure.
- Add adversarial claim tests for every link and prove no CAS or `job.claimed` event.

### R1-4 — explicit idempotency keys can cross exact/routed modes, and replay misses immutable links

The exact path does not reject a routed event/job when an explicit key is reused. A
direct routed-then-exact probe returned the original routed job as a successful exact
replay:

```text
EXACT_AFTER_ROUTED_ACCEPTED False False True True
```

Routed replay also accepted both a forged event target and a forged
`job.payload.request_event_id`:

```text
REPLAY_ACCEPTED_FORGED_EVENT_TARGET ...
REPLAY_ACCEPTED_FORGED_REQUEST_EVENT_ID ...
```

Required correction:

- Reusing an explicit idempotency key across exact/routed modes must conflict in both
  directions before mutation, even when the exact target equals the routed selection.
- Routed replay must validate event workspace/type/target/task and compatibility
  `payload.target_agent`, job workspace/task/request-event id/assignment/runner, and
  route-to-binding/context links before returning the original result.
- If `append_event()` loses a concurrent idempotency race and returns
  `event.created=False`, immediately replay the stored event/job; do not compare it to
  a decision computed from current candidate/load state.
- Add exact/routed collision, malformed stored link, and concurrent-loser replay tests.

### R1-5 — route-only CLI flags are silently accepted in exact mode

The argparse mutually-exclusive group contains only `--target-agent` and
`--route-capability`. The handler ignores the other routed fields whenever a target is
present. All four probes parsed successfully:

```text
CLI_ACCEPTED_EXACT_WITH --route-definition
CLI_ACCEPTED_EXACT_WITH --preferred-host
CLI_ACCEPTED_EXACT_WITH --override-agent
CLI_ACCEPTED_EXACT_WITH --override-reason
```

Required correction:

- Reject every route-only flag in exact mode rather than silently discarding it.
- In routed mode require the override id/reason pair together and reject reason-only,
  id-only, blank, control-character, and overlong reasons.
- Add direct parser/handler tests for exact/routed mutual exclusion, conditional
  fields, caller normalization, JSON output, and zero calls to `submit_request()` on
  invalid CLI combinations.

### R1-6 — required atomicity, recovery, and malformed-state tests remain incomplete

The current tests cover happy-path creation/replay and a small subset of filters, but
the approved plan requires permanent adversarial proof rather than inference from the
implementation.

Required correction:

- Add event-insert/job-create rollback tests proving both-or-neither mutation.
- Add malformed stored request/decision/digest/candidate/selected-link replay tests.
- Add explicit-idempotency content/mode conflicts with event/job deltas asserted zero.
- Prove same-job timed-out recovery retains assignment, route decision, binding,
  context, and stale-attempt rules.
- Prove generic routed retry rejection occurs before any new job/event.
- Preserve exact typed and exact legacy byte/behavior compatibility tests.

## Revalidation gate

After correction, run unpiped focused tests, full Coordinate and MultiNexus baselines,
compile/static/diff gates, and exact CLI-contract/AST comparisons. Return exact
commands, counts, changed paths, and both worktree statuses. Create the required
MultiNexus `implementation-report.md`, then make one isolated Coordinate implementation
commit and one isolated MultiNexus report commit. Do not push, cherry-pick, deploy,
restart services, mutate production/lifecycle state, or touch either `main` checkout.
