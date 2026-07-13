# P9-2B Deterministic Executor Routing — Round 1 Continuation Report

## Authority

- Plan: `docs/project-harness/tasks/p9-2b-deterministic-executor-routing/plan.md`
- Plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate HEAD: `eec9b233f6c797c73aec9d535fa723e037a0af65`
- MultiNexus HEAD: `b9416d9df81afb81051bfa19627bbe45d66852f0`
- Worker model: `kimi-code/kimi-for-coding` (ordinary, no highspeed)

## Scope

This round corrects the R1-1 through R1-6 findings from the Codex Round 1 result
review. All changes are confined to the P9-2B Coordinate module, CLI, and
tests. No schema v13, MultiNexus routing policy, `agents.current_load`
authority, freshness windows, capacity/lease/fairness/reroute, or P9-3/P9-4
scope was introduced.

## Commands and counts

### Coordinate focused P9-2B gate

```text
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest \
  tests/test_executor_routing.py \
  tests/test_runtime.py::RoutedRuntimeTests \
  tests/test_runtime.py::RoutedRuntimeCorrectionTests \
  tests/test_execution_cli.py
```

Result: `158 passed, 14 subtests passed`.

### Coordinate full suite

```text
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest tests/
```

Result: `2125 passed, 9 failed`.

The 9 failures are the historical CLI-contract/AST baseline failures:

- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a1_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2a_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2b_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2c_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a3a_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_differs_from_p9_0a4a_baseline_only_at_12_handlers`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_s4b1_rewind_matches_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_s4c1_rewind_matches_baseline`
- `tests/test_issue_cli.py::IssueCLIOwnershipTests::test_all_five_handler_ast_bodies_match_start_revision`

These match the accepted Round 1 historical gate; the P9-2B delta test
`test_contract_p9_2b_delta_matches_baseline` passes.

### MultiNexus focused and full

Focused claim/context/binding tests:

```text
PYTHONPATH=/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-2b-kimi \
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest \
  tests/test_agentd_executor_binding.py \
  tests/test_agentd_execution_context.py \
  tests/test_coordinator_handoff_runtime.py \
  tests/test_executor_binding.py
```

Result: `105 passed, 1 warning`.

Full MultiNexus suite (from its worktree):

```text
PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest tests/
```

Result: `503 passed, 2 skipped, 1 warning`.

### Static gates

```text
python -m compileall src/coordinate tests/ -q
```

No output (success).

```text
git diff --check
```

No whitespace errors in either worktree.

## Round 1 adversarial probes — now rejections

The R1 probes that previously returned `*_ACCEPTED` are now covered by passing
strict tests:

| Probe | Passing test |
|---|---|
| `REQUEST_ACCEPTED bool_contract_version` | `test_parse_rejects_bool_contract_version` |
| `REQUEST_ACCEPTED unsorted_capabilities` | `test_parse_rejects_unsorted_capabilities` |
| `REQUEST_ACCEPTED duplicate_capabilities` | `test_parse_rejects_duplicate_capabilities` |
| `REQUEST_ACCEPTED noncanonical_reason` | `test_parse_rejects_noncanonical_reason` |
| `DECISION_ACCEPTED unknown_candidate_key` | `test_validate_decision_rejects_unknown_candidate_key` |
| `DECISION_ACCEPTED boolean_routing_load` | `test_validate_decision_rejects_boolean_routing_load` |
| `DECISION_ACCEPTED selection_kind_request_mismatch` | `test_validate_decision_rejects_selection_kind_request_mismatch` |
| `CLAIM_ACCEPTED_FORGED_BINDING` | `test_forged_binding_rejected` / `test_forged_claim_evidence_zero_mutation` |
| `CLAIM_ACCEPTED_FORGED_HOST` | `test_forged_host_rejected` / `test_forged_claim_evidence_zero_mutation` |
| `EXACT_AFTER_ROUTED_ACCEPTED` | `test_explicit_idempotency_key_exact_then_routed_rejects` / `test_explicit_idempotency_key_routed_then_exact_rejects` |
| `REPLAY_ACCEPTED_FORGED_EVENT_TARGET` | `test_replay_rejects_forged_event_target` / `test_replay_rejects_forged_payload_target_agent` |
| `REPLAY_ACCEPTED_FORGED_REQUEST_EVENT_ID` | `test_replay_rejects_forged_request_event_id` |
| `CLI_ACCEPTED_EXACT_WITH --route-definition` | `test_exact_handler_rejects_route_definition` |
| `CLI_ACCEPTED_EXACT_WITH --preferred-host` | `test_exact_handler_rejects_preferred_host` |
| `CLI_ACCEPTED_EXACT_WITH --override-agent` | `test_exact_handler_rejects_override_agent` |
| `CLI_ACCEPTED_EXACT_WITH --override-reason` | `test_exact_handler_rejects_override_reason` |

## Key corrections implemented

1. **R1-1**: Separated caller-input normalization from strict stored-envelope
   parsing. Added a full mutation matrix for `routing_request` keys, types,
   versions, digests, labels, override pairs, whitespace, duplicates, and
   order. Manually constructed `RoutingRequest` objects are round-tripped through
   the strict parser and cannot bypass validation.
2. **R1-2**: Stored `routing_decision` validation now enforces exact candidate
   shape, scalar types, canonical sorted-unique capabilities, selection-kind /
   override binding, selected-link consistency, duplicate rejection, and exact
   policy order. The `preferred_host` boolean and host rank were separated: no
   preference means `preferred_host=false` for every candidate while rank is
   still zero.
3. **R1-3**: `routing_claim_evidence` now cross-binds the routing decision to
   the P9-2A binding snapshot and the P9-1 execution context. Tests prove forged
   binding, definition, source, catalog, host, context, and job links are
   rejected before the claim CAS, leaving status/attempt/event unchanged.
4. **R1-4**: Explicit idempotency keys conflict across exact/routed modes in
   both directions with zero mutation. Routed replay validates event target,
   payload target, `request_event_id`, workspace/task/assignment/runner links,
   and immutable binding/context snapshots. Concurrent idempotency losers reply
   the stored event/job instead of recomputing from current routing state.
5. **R1-5**: CLI handler rejects every route-only flag in exact mode and
   enforces override id/reason pairing, blank/control-char/overlong reason
   limits, and capability normalization. Invalid CLI combinations never call
   `submit_request()`.
6. **R1-6**: Added event-insert/job-create rollback tests (both exact and
   routed), same-job timed-out recovery tests preserving decision/assignment/
   binding/context/attempt authority, generic routed retry rejection before any
   write, and exact typed/legacy compatibility tests.

## Cross-repo contract

- Coordinate is the sole owner of routing request/decision contracts,
  candidate selection, and redacted claim evidence.
- MultiNexus receives the already-accepted P9-1/P9-2A claim contract plus the
  additive `routing_request_id` and `routing_decision_id`. No MultiNexus code
  was changed; the existing MultiNexus claim/context/binding tests remain green.

## Known risks / residual notes

- The nine historical CLI-contract/AST failures persist and are unrelated to
  P9-2B; they are accepted as the baseline gate.
- `agents.current_load` remains unwritten and is not used as a routing
  authority.
- No freshness cutoff or heartbeat window was introduced (P9-4 scope).
- No capacity limit, lease, queue fairness, or automatic reroute was introduced
  (P9-3 scope).
- No production DB migration, deployment, restart, or lifecycle event was
  performed.
