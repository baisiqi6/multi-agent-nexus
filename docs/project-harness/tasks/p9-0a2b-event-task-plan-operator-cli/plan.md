# P9-0A2b Event, Task, Plan, and Operator CLI Extraction

> **Status:** in_review
>
> This plan does not authorize implementation. A worker bootstrap may be generated only
> after an independent non-Codex reviewer approves this exact plan revision and
> Coordinate records a fresh `plan.approved` event.

## Identity

- Parent stage: `phase-9-execution-isolation` / `P9-0A`
- Refinement parent: `P9-0A2 workspace/planning/issue CLI`
- Package id: `p9-0a2b-event-task-plan-operator-cli`
- Plan author / architect: Codex
- Intended plan reviewer: independent Kimi Code Highspeed session through Oh-My-Pi;
  GLM is the explicit fallback if Kimi quota/auth/provider availability fails
- Intended coding worker after approval: a separate non-Codex worker session through
  Oh-My-Pi, preferring Kimi Highspeed and falling back to GLM on provider failure
- Intended code/result reviewer: Codex
- Operator: Codex under the user's durable goal/gate delegation
- Plan path:
  `docs/project-harness/tasks/p9-0a2b-event-task-plan-operator-cli/plan.md`
- Approval authority: latest Coordinate `plan.ready` plus full SHA-256 of this file

P9-0A2a is durably closed. P9-0A2b moves only event/task/plan/operator ownership.
P9-0A2c issue ownership and every later package remain separately gated.

## Refreshed preflight

Snapshot on 2026-07-12:

- Coordinate canonical `main` and `origin/main`:
  `10862d97d02d6e20b191005f02a732c6fa44ad59`.
- Coordinate canonical checkout has only unrelated untracked `.qoder/`; it is outside
  scope and must remain untouched.
- MultiNexus canonical `main` and `origin/main`:
  `a5e2f09b0f56240e6b6642ec586343a225129932`.
- P9-0A2a is `done/closed` through receipt
  `b2fedbf8-d54c-4586-b3f9-04d3b2e683b9`.
- `src/coordinate/cli.py`: 2,422 lines.
- Current deterministic contract:
  - 21 ordered top-level commands;
  - 75 ordered leaves;
  - 99 parser nodes;
  - fixture SHA-256
    `652a77d5ee7ab2239b7e2a406560ae21ada4d93b7f7c076fa7c65d6e0aa3f048`.
- The earlier P9-0A1 fixture SHA-256 remains
  `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.
- P9-0A2b owns exactly 10 leaves:
  - `event append`
  - `event list`
  - `task create`
  - `task create-files`
  - `task create-record`
  - `task handoff`
  - `plan review-request`
  - `plan approve`
  - `plan reject`
  - `operator pending`
- Measured handler movement is 178 lines. Event/task/plan parser registration is
  contiguous near the start; operator registration remains later between assignment
  and serve and therefore requires a separate registrar call site.
- Refreshed focused baseline:
  `tests.test_cli tests.test_cli_contract tests.test_onboarding tests.test_plan_gate
  tests.test_handoff tests.test_operator` = 289 tests passed.
- Refreshed full baseline: 1,384 tests passed on the same P9-0A2a code tip.

No code, DB, schema, service, runtime, delivery, or remote host changed while preparing
this plan.

## Problem

After P9-0A2a, the root CLI still owns event ingestion/listing, plan-backed task
creation/handoff, plan review transitions, and operator pending projection. These
commands form the control-plane planning/coordination boundary:

- events are normalized durable inputs;
- task creation binds plan identity to harness and coordinator mirrors;
- plan commands own the review/approval gate;
- operator pending reads the resulting action projection.

They share DB/onboarding/plan-gate/handoff/operator services but do not require runner,
execution, delivery, issue, workflow, completion, or runtime registrars. Keeping them in
the root continues change concentration before Slice 4 projection work.

The four command families are not contiguous in top-level order: event/task/plan are
before runner, while operator is after assignment and before serve. One registrar would
either reorder the public contract or hide an out-of-position callback. Two explicit
static registrars preserve the existing composition order.

## Goal

In one behavior-preserving worker session:

1. add `coordinate.planning_cli` as the static owner of event/task/plan/operator
   registration and the exact 10 handlers;
2. keep `coordinate.cli` as the public console/composition facade;
3. preserve every public parser/action/help/output/exit/error/DB/filesystem behavior;
4. preserve root imports of all 10 moved handler names as direct compatibility aliases;
5. change only the 10 new implementation-owner strings relative to the accepted
   P9-0A2a contract; and
6. retain cumulative proof that P9-0A2a and P9-0A2b changed only their explicitly
   approved handler identities relative to P9-0A1.

## Non-goals

- No issue extraction; P9-0A2c requires its own plan.
- No runner/job/runtime/delivery/policy/worker/workflow/completion/PR extraction.
- No behavior, command, order, flag, default, help, output JSON, stdout/stderr, exit code,
  exception, lifecycle, idempotency, delivery, DB schema, or persistence change.
- No change to generated bootstrap text, OpenSpec fallback, implementation-repo routing,
  host profiles, pending-delivery cancellation, plan-ready status wording, or provider
  selection. Those are dogfood backlog, even though `task handoff` moves owners here.
- No plugin discovery, registry framework, command class hierarchy, dependency-injection
  container, dynamic import, package split, or third-party dependency.
- No deploy, restart, SSH, live DB/workspace/delivery, push, merge, or lifecycle closeout
  by the worker.

## Authority and dependency boundaries

- `coordinate.cli:main` and `coordinate.cli:build_parser` remain public.
- `coordinate.cli` remains the explicit static composition root.
- `planning_cli` may import `cli_support` and the existing DB/onboarding/plan-gate/
  handoff/operator services needed by the 10 handlers. It must not import
  `coordinate.cli` or another CLI registrar.
- Business services must not import `planning_cli`.
- `coordinate.cli` re-exports all 10 moved `handle_*` functions by direct import, so
  existing handler imports remain valid. Service aliases in the root are not preserved
  solely for hypothetical monkeypatches.
- Tests patch moved dependencies in `coordinate.planning_cli`, never through a lazy
  callback into the root facade.
- `cli_support.DEFAULT_DB_PATH`, `open_connection`, and `print_json` remain unchanged.
- `handle_task_handoff` currently derives `coordinator_path` with
  `Path(__file__).resolve().parents[2]`. Moving from `cli.py` to the sibling
  `planning_cli.py` must preserve the exact resolved repository root; a dedicated test
  must lock this invariant.
- Tests use temp/in-memory state only. They must not use the registered `discord-nexus`
  workspace, canonical DB, live harness, platform delivery, or runtime process.

## Proposed implementation

### 1. Add `planning_cli.py`

Add `src/coordinate/planning_cli.py` with two explicit registrar functions:

```python
def register_planning_commands(subcommands) -> None: ...
def register_operator_command(subcommands) -> None: ...
```

The first registers `event`, `task`, and `plan` in their existing contiguous positions.
The second is called later at the current `operator` position, after assignment
registration and before serve. Do not use a private argparse type annotation.

Move exactly these handlers without cleanup or semantic rewrite:

- `handle_event_append`
- `handle_event_list`
- `handle_task_create`
- `handle_task_create_files`
- `handle_task_create_record`
- `handle_task_handoff`
- `handle_plan_review_request`
- `handle_plan_approve`
- `handle_plan_reject`
- `handle_operator_pending`

Handlers may import `open_connection as _conn` and `print_json as _print_json` to keep the
movement mechanical. Do not introduce a context/service object.

### 2. Keep root facade and order

Update `src/coordinate/cli.py` to:

- directly import both registrar functions and all 10 handlers;
- replace the existing event/task/plan parser block with
  `register_planning_commands(subcommands)`;
- replace only the existing operator parser block with
  `register_operator_command(subcommands)`;
- remove the moved handler bodies;
- remove only imports proven unused after movement.

Do not reorder another registrar or handler. Do not rename the root compatibility
imports. Root utilities such as `json`, `os`, `sys`, `Path`, `_conn`, `_print_json`, and
shared DB helpers remain if any non-moved handler still needs them.

### 3. Preserve layered contract proof

Update `tests/fixtures/cli_contract.json` only after all comparisons pass. Relative to
the P9-0A2a fixture, the expected delta is exactly 10 `defaults.handler` strings:

```text
coordinate.cli.handle_<name>
  -> coordinate.planning_cli.handle_<name>
```

All other normalized JSON bytes must remain identical; counts remain 21/75/99.

Refactor the current P9-0A2a contract helper only as needed to support explicit migration
layers without weakening it:

1. rewind exactly the 10 P9-0A2b mappings and require the full serialized contract to
   match P9-0A2a fixture SHA-256 `652a77d5...`;
2. then rewind exactly the 11 P9-0A2a mappings and require the full serialized contract
   to match P9-0A1 fixture SHA-256 `83c4c181...`;
3. reject missing/duplicate approved paths, unexpected ownership in either extracted
   module, and any other structural drift; and
4. retain a negative proof that a non-handler byte cannot reach either baseline hash.

Fixture regeneration alone, current-fixture self-consistency, or module-prefix counting
is not sufficient evidence.

### 4. Add planning CLI boundary tests

Add `tests/test_planning_cli.py` proving:

- root compatibility handler aliases are identical to `planning_cli` handlers;
- `planning_cli` does not import `coordinate.cli`;
- importing root/support/workspace/planning/PR modules in multiple clean orders succeeds;
- both registrar functions add the expected commands once and preserve their supplied
  parser position;
- all 10 leaves point to the moved callable handlers and no unapproved leaf does;
- `handle_task_handoff` derives the same repository root before and after movement;
- representative success/error behavior for event append/list, invalid payload JSON/
  object, task create/create-files/create-record, handoff gate errors, plan review/
  approve/reject gate errors, and operator pending remains unchanged with temp state;
- the root no longer contains moved handler definitions or now-unused planning-only
  service imports.

Existing service/unit tests remain authorities for onboarding, plan gate, handoff, event
storage, and operator projection semantics.

## Allowed paths

Production:

- `src/coordinate/cli.py`
- `src/coordinate/planning_cli.py` (new)

Contract/tests:

- `tests/test_cli_contract.py`
- `tests/fixtures/cli_contract.json`
- `tests/test_planning_cli.py` (new)
- `tests/test_cli.py` only if a narrow owner/compatibility assertion cannot live in the
  new boundary test

Any need to change another production module, existing service test, packaging metadata,
schema, or harness file stops the worker and returns the plan for review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Top-level order, node/leaf count, action/default/help bytes change | Stop; restore exact registrar call positions and parser arguments. |
| P9-0A2b rewind does not match `652a77d5...` | Treat as regression; do not approve fixture regeneration. |
| Cumulative rewind does not match `83c4c181...` | Restore layered proof; do not erase P9-0A2a evidence. |
| Root handler alias disappears or is not identical to new owner | Restore direct compatibility re-export. |
| Existing test patches a moved service through the root | Prove the caller; retarget internal test to the new owner or revise the plan. Do not add a lazy root backedge. |
| `planning_cli -> cli` or business-service -> CLI edge appears | Stop and remove the cycle/backedge. |
| `handle_task_handoff` derives a different coordinator root | Restore sibling-module path equivalence and add a regression. |
| Handler movement changes output/exit/error/DB/filesystem behavior | Restore the original body mechanically and add a regression. |
| Another path is required | Stop and request plan revision; do not expand scope ad hoc. |
| Test touches canonical DB/workspace/delivery/runtime | Stop, preserve evidence, and redesign around temp/parser-only state. |
| Kimi quota/auth/provider fails before edits | Preserve clean evidence and retry with GLM in a fresh recorded provider interval. |
| Provider fails after partial edits | Inspect JSONL/process/diff; resume or switch only within approved paths and record attribution. |

## Acceptance matrix

| Case | Expected evidence |
|---|---|
| Public CLI contract | 21 top-level, 75 leaves, 99 nodes; identical to P9-0A2a except exact 10 handler mappings |
| Cumulative contract | rewinding B reaches `652a77d5...`; rewinding B+A reaches `83c4c181...` |
| Registration order | event/task/plan and operator remain in original top-level positions |
| Handler ownership | 10 leaf handlers owned by `coordinate.planning_cli`; root direct aliases remain identical |
| Behavior | existing event/task/plan/operator success and error outputs/exits unchanged |
| Handoff path | sibling module derives the same repository root as the old root handler |
| Import direction | no `planning_cli -> cli`, no service -> CLI edge, clean import orders |
| Scope | only approved paths; no business/schema/runtime/harness change |
| Regression | focused count does not drop from 289; full count does not drop from 1,384 |
| Privacy | fixture/tests contain no secret, raw prompt/reasoning, checkout-specific path, or DB row |

## Validation

Worker preflight before edits:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_cli_contract tests.test_onboarding \
  tests.test_plan_gate tests.test_handoff tests.test_operator
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Required after implementation:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_planning_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_onboarding tests.test_plan_gate \
  tests.test_handoff tests.test_operator
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Also record:

- start/worker commit SHAs and exact changed paths;
- before/after fixture SHA-256;
- P9-0A2b and cumulative structural rewind hashes;
- pre/post 21/75/99 counts;
- focused/full counts;
- root alias identity, task-handoff repository-root, and import-order results;
- handler AST comparison against the start revision;
- source/import inspection for backedges and stale root definitions;
- provider session/JSONL and any Kimi-to-GLM transition.

No deployment or multi-host smoke is required. This package changes only static parser/
handler ownership and tests; runtime side effects remain forbidden.

## Worker boundaries

- Fresh isolated Coordinate worktree from exact reviewed canonical `main`.
- One logical implementation at a time; no subagent scope expansion.
- Read/edit/test exact allowed paths and create one local commit after all checks.
- Do not amend, push, merge, deploy, restart, SSH, mutate Coordinate/harness lifecycle,
  use a live DB/delivery, clean `.qoder/`, or self-approve.
- Report exact scope/contract/test/import evidence and one `[agent-report]` block.

## Review and bootstrap gate

- Review artifact/reviewer/verdict: pending.
- Any material plan edit creates a new hash and requires fresh `plan.ready` and review.
- Before worker bootstrap:
  1. this exact plan hash is independently approved;
  2. Coordinate `main` still matches the reviewed start SHA or drift is reviewed;
  3. a fresh isolated worktree/branch is recorded;
  4. bootstrap/supplement names exact paths, layered contract proof, validation, JSONL
     observation, Kimi-to-GLM fallback, and stop conditions;
  5. P9-0A2c and all later packages remain unauthorized.
