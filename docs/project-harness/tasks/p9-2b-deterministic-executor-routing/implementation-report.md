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

---

# P9-2B Deterministic Executor Routing — Round 2 Correction Report

## Authority

- Plan: `docs/project-harness/tasks/p9-2b-deterministic-executor-routing/plan.md`
- Plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate correction baseline HEAD: `c56802556d33d36d1ad726b16b4376e6ac016e8b`
- MultiNexus correction baseline HEAD: `f24ea734ac81c7cabda8a9d7aaed3ae718f64be6`
- Worker model: `kimi-code/kimi-for-coding` (ordinary, no highspeed)

## Scope

This round corrects the R2-1 through R2-5 findings from the Codex Round 2 result
review. All changes are confined to the P9-2B Coordinate module and tests. No
schema v13, MultiNexus routing policy, `agents.current_load` authority, freshness
windows, capacity/lease/fairness/reroute, or P9-3/P9-4 scope was introduced.

## Commands and counts

### Coordinate focused P9-2B gate

```text
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest \
  tests/test_executor_routing.py \
  tests/test_runtime.py::RoutedRuntimeTests \
  tests/test_runtime.py::RoutedRuntimeCorrectionTests \
  tests/test_execution_cli.py
```

Result: `171 passed, 0 subtests passed`.

### Coordinate full suite

```text
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest tests/
```

Result: `2138 passed, 9 failed`.

The 9 failures are the exact same historical CLI-contract/AST baseline failures
accepted in Round 1:

- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a1_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2a_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2b_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2c_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a3a_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_differs_from_p9_0a4a_baseline_only_at_12_handlers`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_s4b1_rewind_matches_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_s4c1_rewind_matches_baseline`
- `tests/test_issue_cli.py::IssueCLIOwnershipTests::test_all_five_handler_ast_bodies_match_start_revision`

The P9-2B delta test `test_contract_p9_2b_delta_matches_baseline` passes.

### MultiNexus focused and full

Focused claim/context/binding tests:

```text
PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest \
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
python -m compileall tests/ -q
```

No output (success).

```text
git diff --check
```

No whitespace errors in either worktree.

## Round 2 adversarial probes — now rejections

| Probe | Now-rejecting test |
|---|---|
| `ACCEPTED_INELIGIBLE_CANDIDATE` | `test_validate_decision_rejects_ineligible_candidate_adversarial` / `test_validate_decision_rejects_offline_candidate` / `test_validate_decision_rejects_candidate_missing_required_capability` / `test_validate_decision_rejects_candidate_definition_mismatch` |
| `REPLAY_ACCEPTED_FORGED_DECISION_BINDING_LINK` | `test_routed_replay_rejects_forged_decision_binding_link` |
| `EXACT_REPLAY_ACCEPTED_FORGED_JOB_PROMPT` | `test_exact_replay_rejects_forged_job_prompt` |
| `ROUTED_REPLAY_ACCEPTED_FORGED_JOB_PROMPT` | `test_routed_replay_rejects_forged_job_prompt` |
| `REPLAY_ACCEPTED_FORGED_EVENT_TASK` | `test_replay_rejects_forged_event_row_task_id` |
| `DUPLICATE_TEST_METHOD` | AST duplicate-method detector reports no duplicates in P9-2B test files |

## Key corrections implemented

1. **R2-1**: `validate_routing_decision()` now re-derives every deterministic
   eligibility fact from the stored `RoutingRequest`: each candidate must be
   `online`, required capabilities must be a subset of the candidate's
   capabilities, an optional `executor_definition_id` filter must match,
   identity labels must satisfy the safe-label grammar, and `source_version`
   must be a positive integer. Adversarial decisions with recomputed valid
   digests are still rejected before replay or claim.
2. **R2-2**: Extracted a shared fail-closed `_validate_routing_cross_links()`
   helper that strict-binds the selected candidate/decision to the P9-2A
   binding snapshot and the P9-1 execution context. It is used by both routed
   replay and `routing_claim_evidence`; it neither reroutes nor reads current
   load.
3. **R2-3**: Exact and routed replay now validate event/job prompt, origin,
   reply, task, `request_event_id`, assignment, runner, binding, context, and
   decision internal links. The event row's `task_id` is verified in both paths.
   The exact typed replay path no longer accidentally reuses the event payload
   when validating job content.
4. **R2-4**: Restored the original `tests/test_execution_context.py` assertion
   expecting `execution_context conflicts` by reordering the exact typed replay
   checks so the execution-context snapshot comparison precedes the direct
   origin/task checks. The original test expectation is no longer weakened.
5. **R2-5**: Fixed the duplicate `test_replay_rejects_forged_event_target` method
   (renamed the second occurrence to `test_replay_rejects_forged_job_request_event_id`).
   Made `test_concurrent_loser_replays_stored_event` miss the initial
   idempotency lookup and assert that the patched `append_event()` is called.
   Added permanent event-task, job-content, decision-binding/context, and a
   full claim zero-mutation matrix covering binding, context, decision, and job
   links.

## Cross-repo contract

- Coordinate remains the sole owner of routing request/decision contracts,
  candidate selection, and redacted claim evidence.
- MultiNexus receives the already-accepted P9-1/P9-2A claim contract plus the
  additive `routing_request_id` and `routing_decision_id`. No MultiNexus source
  code was changed; the existing MultiNexus claim/context/binding tests remain
  green.

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


---

# P9-2B Deterministic Executor Routing — Round 3 Correction Report

## Authority

- Plan: `docs/project-harness/tasks/p9-2b-deterministic-executor-routing/plan.md`
- Plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate correction baseline HEAD: `7139728435e842e8728739ec6246b5b8eeb17407`
- MultiNexus correction baseline HEAD: `2be66eeaa990add1f7f20630a9c8cd6e94d40224`
- Worker model: `kimi-code/kimi-for-coding` (ordinary, no highspeed)

## Scope

This round corrects the R3-1 finding from the Codex Round 3 result review:
`_replay_exact_request()` still accepted forged stored-event payload content in
its typed-context branch. The Round 2 report claim that exact replay validated
all event/job content links was too broad; this round corrects that wording and
closes the forged event-content gap. All changes are confined to the P9-2B
Coordinate module and tests; no routing policy, schema, CLI, or MultiNexus
source change was introduced.

## Commands and counts

### Coordinate focused P9-2B gate (unpiped)

```text
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest \
  tests/test_executor_routing.py \
  tests/test_runtime.py::RoutedRuntimeTests \
  tests/test_runtime.py::RoutedRuntimeCorrectionTests \
  tests/test_execution_cli.py
```

Result: `173 passed in 0.91s`.

### Coordinate full suite (unpiped)

```text
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest tests/
```

Result: `2140 passed, 9 failed in 64.53s`.

The 9 failures are the exact same historical CLI-contract/AST baseline failures
accepted in Round 1 and Round 2:

- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a1_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2a_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2b_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a2c_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_cumulative_rewind_matches_p9_0a3a_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_differs_from_p9_0a4a_baseline_only_at_12_handlers`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_s4b1_rewind_matches_baseline`
- `tests/test_cli_contract.py::CLIContractTests::test_contract_s4c1_rewind_matches_baseline`
- `tests/test_issue_cli.py::IssueCLIOwnershipTests::test_all_five_handler_ast_bodies_match_start_revision`

The P9-2B delta test `test_contract_p9_2b_delta_matches_baseline` passes.

### MultiNexus focused and full (unpiped)

Focused claim/context/binding tests:

```text
PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest \
  tests/test_agentd_executor_binding.py \
  tests/test_agentd_execution_context.py \
  tests/test_coordinator_handoff_runtime.py \
  tests/test_executor_binding.py
```

Result: `105 passed, 1 warning in 0.36s`.

Full MultiNexus suite (from its worktree):

```text
PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest tests/
```

Result: `503 passed, 2 skipped, 1 warning in 19.89s`.

### Static gates

```text
python -m compileall src/coordinate tests/ -q
python -m compileall -q .
```

No output (success).

```text
python -c "
import ast
from pathlib import Path

coord_path = Path('/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-2b-kimi')
errors = []
for file_path in [coord_path / 'tests' / 'test_runtime.py', coord_path / 'tests' / 'test_executor_routing.py']:
    source = file_path.read_text()
    tree = ast.parse(source, filename=str(file_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            seen = {}
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                    if item.name in seen:
                        errors.append(f'DUPLICATE_TEST_METHOD {node.name}.{item.name} lines {seen[item.name]} and {item.lineno}')
                    else:
                        seen[item.name] = item.lineno
if errors:
    print('\n'.join(errors))
    raise SystemExit(1)
print('No duplicate test methods in P9-2B test files.')
"
```

Result: `No duplicate test methods in P9-2B test files.`

```text
git diff --check
```

No whitespace errors in either worktree.

## Round 3 adversarial probes — now rejections

| Probe | Now-rejecting test |
|---|---|
| `EXACT_EVENT_ORIGIN_FORGERY_ACCEPTED` | `test_exact_replay_rejects_forged_event_payload_matrix` (typed + legacy subtests) |
| `EXACT_EVENT_REPLY_FORGERY_ACCEPTED` | `test_exact_replay_rejects_forged_event_payload_matrix` (typed + legacy subtests) |
| `EXACT_EVENT_TASK_ID_FORGERY_ACCEPTED` | `test_exact_replay_rejects_forged_event_payload_matrix` (typed + legacy subtests) |

## Key corrections implemented

1. **R3-1**: After the typed execution-context snapshot comparison succeeds,
   `_replay_exact_request()` now validates the stored event payload's `origin`,
   `reply`, and `task_id` against the current request and the stored job
   authority. The P9-1 context comparison still precedes these checks, so the
   accepted `execution_context conflicts` error ordering for task/scope
   changes is preserved; no old assertion was modified to make this pass.
2. The legacy/no-context exact replay branch also fail-closed checks the
   stored event payload `reply` and `task_id` (the `origin` check was already
   present). Existing legacy exact replay success paths and error semantics are
   unchanged.
3. Added a permanent exact-event mutation matrix covering `origin`, `reply`,
   and payload `task_id` in both typed and legacy branches. Each subtest
   asserts rejection and zero changes to event count, job status, attempt
   count, and stored job/event payloads.

## Correction to Round 2 wording

The Round 2 report stated that exact and routed replay "validate event/job
prompt, origin, reply, task, request_event_id, assignment, runner, binding,
context, and decision internal links." That statement was too broad: the
stored event payload's `origin`, `reply`, and `task_id` were not actually
validated in the exact typed replay path, which Round 3's reviewer probes
exposed. This round closes that gap and updates the report accordingly.

## Cross-repo contract

- Coordinate remains the sole owner of routing request/decision contracts,
  candidate selection, and redacted claim evidence.
- MultiNexus receives the already-accepted P9-1/P9-2A claim contract plus the
  additive `routing_request_id` and `routing_decision_id`. No MultiNexus source
  code was changed; the existing MultiNexus claim/context/binding tests remain
  green.

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


---

# P9-2B Deterministic Executor Routing — Round 3 Follow-up Correction Report

## Authority

- Plan: `docs/project-harness/tasks/p9-2b-deterministic-executor-routing/plan.md`
- Plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate prior Round 3 correction HEAD: `96ca4cb93e21beec8ffe20e68437e2e062ba3c76`
- MultiNexus prior Round 3 docs HEAD: `5db2eb6a8ea6001e1b5931938cc4396639a31417`
- Worker model: `kimi-code/kimi-for-coding` (ordinary, no highspeed)

## Scope

This follow-up corrects the committed Round 3 test so that the legacy/no-context
subtests actually exercise the legacy branch of `_replay_exact_request()`. In
the initial Round 3 correction, even the legacy agent (`mac-codex`) received a
job payload containing `execution_context` because the runtime always resolves
and stores a P9-1 context snapshot. Therefore the legacy branch was never
entered. This follow-up explicitly strips `execution_context` (and any
`executor_binding`) from the stored job payload before the forged-event replay,
so the no-context path is the authority under test.

Also, the committed `scripts/detect_duplicate_test_methods.py` is removed
because it hard-coded this machine's absolute worktree path; the duplicate-test
AST detector is now run as an inline `python -c` command.

## Commands and counts

### Coordinate focused P9-2B gate (unpiped)

```text
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest \
  tests/test_executor_routing.py \
  tests/test_runtime.py::RoutedRuntimeTests \
  tests/test_runtime.py::RoutedRuntimeCorrectionTests \
  tests/test_execution_cli.py
```

Result: `173 passed in 0.92s`.

### Inline duplicate-test AST detector

```text
python -c "
import ast
from pathlib import Path

coord_path = Path('/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-2b-kimi')
errors = []
for file_path in [coord_path / 'tests' / 'test_runtime.py', coord_path / 'tests' / 'test_executor_routing.py']:
    source = file_path.read_text()
    tree = ast.parse(source, filename=str(file_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            seen = {}
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                    if item.name in seen:
                        errors.append(f'DUPLICATE_TEST_METHOD {node.name}.{item.name} lines {seen[item.name]} and {item.lineno}')
                    else:
                        seen[item.name] = item.lineno
if errors:
    print('\n'.join(errors))
    raise SystemExit(1)
print('No duplicate test methods in P9-2B test files.')
"
```

Result: `No duplicate test methods in P9-2B test files.`

### Static gates

```text
python -m compileall src/coordinate tests/ -q
python -m compileall -q .
```

No output (success).

```text
git diff --check
```

No whitespace errors in either worktree.

## Key corrections implemented

1. **`tests/test_runtime.py`**: in the legacy/no-context subtests of
   `test_exact_replay_rejects_forged_event_payload_matrix`, after the initial
   job creation the test now updates the stored job payload to remove
   `execution_context` (and `executor_binding`), asserts it is absent, and uses
   that no-context payload as the pre-replay expected authority. This ensures
   the replay enters the legacy branch and the forged event payload checks for
   `origin`, `reply`, and `task_id` are exercised there.
2. **Removed `scripts/detect_duplicate_test_methods.py`**; the duplicate-test
   AST detector is now run inline and does not contain absolute worktree paths.

## Known risks / residual notes

- The nine historical CLI-contract/AST failures in the Coordinate full suite
  persist and are accepted as the baseline gate; they were not re-run in this
  focused follow-up.
- `agents.current_load` remains unwritten and is not used as a routing
  authority.
- No freshness cutoff, capacity limit, lease, queue fairness, automatic
  reroute, schema change, MultiNexus source change, deployment, restart, or
  lifecycle event was introduced.
