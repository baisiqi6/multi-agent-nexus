# P9-0A2a Workspace, State, and Reconcile CLI Extraction

> **Status:** in_review
>
> This plan does not authorize implementation. A worker bootstrap may be generated only
> after an independent non-Codex reviewer approves this exact plan revision and
> Coordinate records a fresh `plan.approved` event.

## Identity

- Parent stage: `phase-9-execution-isolation` / `P9-0A`
- Refinement parent: `P9-0A2 workspace/planning/issue CLI`
- Package id: `p9-0a2a-workspace-state-reconcile-cli`
- Plan author / architect: Codex
- Intended plan reviewer: independent Kimi Code Highspeed session through Oh-My-Pi
- Intended coding worker after approval: a separate non-Codex worker session, preferably
  Kimi Code Highspeed through Oh-My-Pi
- Intended code/result reviewer: Codex
- Operator: Codex under the user's durable goal/gate delegation
- Plan path:
  `docs/project-harness/tasks/p9-0a2a-workspace-state-reconcile-cli/plan.md`
- Approval authority: latest Coordinate `plan.ready` plus full SHA-256 of this file

P9-0A2 was split after measuring the post-P9-0A1 source. P9-0A2a moves only
workspace/state/reconcile; P9-0A2b will move event/task/plan/operator; P9-0A2c will move
issue. Each receives a separate plan, reviewer, worker, result review, integration, and
closeout.

## Refreshed preflight

Snapshot on 2026-07-12:

- Coordinate canonical `main` and `origin/main`:
  `947368a4c278aa847b40eea20a7088c5cb28446f`
  - accepted P9-0A1 production/code tip: `117ff5d9f98272ff0d740588708b357dc955b205`
  - `947368a` adds only the reviewed operator-backlog record
- Coordinate canonical checkout has only unrelated untracked `.qoder/`; it is outside
  scope and must remain untouched.
- MultiNexus canonical `main` and `origin/main`:
  `239c1cfe126ce6dfc95a5ac52fc5dc7261357b99`
- P9-0A1 is durably `done/closed` through receipt
  `f1f8da57-57c9-4bc4-8f40-76e0c8158f4c`.
- `src/coordinate/cli.py`: 2,688 lines.
- Current deterministic contract:
  - 21 ordered top-level commands;
  - 75 ordered leaves;
  - 99 parser nodes;
  - fixture SHA-256
    `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.
- P9-0A2a owns exactly 11 current leaves:
  - `workspace add`
  - `workspace list`
  - `workspace audit`
  - `workspace doctor`
  - `workspace init-harness`
  - `workspace agent add`
  - `workspace agent sync`
  - `workspace host-profile set`
  - `workspace host-profile list`
  - `state`
  - `reconcile`
- Measured movement is approximately 178 handler lines plus 91 parser-registration
  lines. Event/task/plan/operator/issue are intentionally excluded.
- Refreshed focused baseline:
  `tests.test_cli tests.test_cli_contract tests.test_agent_registry tests.test_doctor
  tests.test_reconcile` = 231 tests passed.
- Refreshed full baseline: 1,366 tests passed on the same P9-0A1 code tip.

No code, DB, schema, service, runtime, delivery, or remote host changed while preparing
this plan.

## Problem

P9-0A1 made the root CLI contract deterministic and extracted generic connection/JSON
support, but `coordinate.cli` still owns all registration and 83 top-level functions.
Workspace/state/reconcile form one coherent boundary:

- workspace registry and harness onboarding;
- workspace agent/host-profile registry;
- harness health/state projection;
- reconciliation from harness state to the task mirror.

They depend on workspace/onboarding/audit/doctor/reconcile services and do not need the
planning, execution, delivery, workflow, or completion registrars. Keeping them in the
root file preserves avoidable change concentration before Slice 4 adds projection and
partial-operation work.

The former combined P9-0A2 package would also move event/task/plan/operator/issue,
roughly tripling parser/handler migration risk and mixing three different service
authorities. The measured split is therefore a safety refinement, not scope reduction:
all original P9-0A2 domains remain scheduled as P9-0A2a/b/c.

## Goal

In one behavior-preserving worker session:

1. add `coordinate.workspace_cli` as the static owner of workspace/state/reconcile
   registration and handlers;
2. keep `coordinate.cli` as the public console/composition facade;
3. preserve every public parser/action/help/output/exit/error/DB behavior;
4. preserve root imports of the 11 moved handler names as compatibility aliases;
5. change only the 11 implementation-only handler qualified names in the contract
   fixture; and
6. remove only now-unused workspace-specific service imports from the root module.

## Non-goals

- No event/task/plan/operator/issue extraction; those require P9-0A2b/c plans.
- No runner/job/runtime/delivery/policy/worker/workflow/completion/PR extraction.
- No behavior, command, order, flag, default, help, output JSON, stdout/stderr, exit code,
  exception, lifecycle, idempotency, delivery, DB schema, or persistence change.
- No fix for host-profile onboarding, pending-delivery cancellation, cross-repo bootstrap,
  receipt preflight projection, relative harness-root UX, workspace delete, or other
  dogfood backlog items.
- No plugin discovery, registry framework, command class hierarchy, dependency-injection
  container, dynamic import, package split, or third-party dependency.
- No deploy, restart, SSH, live DB/workspace/delivery, push, merge, or lifecycle closeout
  by the worker.

## Authority and dependency boundaries

- `coordinate.cli:main` and `coordinate.cli:build_parser` remain public.
- `coordinate.cli` remains the explicit static composition root.
- `workspace_cli` may import `cli_support` and current workspace/onboarding/audit/doctor/
  reconcile business services. It must not import `coordinate.cli` or another CLI
  registrar.
- Business services must not import `workspace_cli`.
- `coordinate.cli` re-exports all 11 moved `handle_*` functions by direct import, so
  existing handler imports remain valid. Service-function aliases in `coordinate.cli`
  are not a compatibility contract and must not be retained solely for hypothetical
  monkeypatches.
- `workspace_cli` owns parser registration and handler globals. Tests that need to patch
  a moved handler dependency patch its new owning module; broad lazy callbacks into the
  root facade are forbidden.
- `cli_support.DEFAULT_DB_PATH`, `open_connection`, and `print_json` remain unchanged.
- Tests use temp/in-memory state only. They must not use the registered `discord-nexus`
  workspace, the canonical DB, a live harness, a platform delivery, or runtime process.

## Proposed implementation

### 1. Add `workspace_cli.py`

Add `src/coordinate/workspace_cli.py` with two explicit registrar functions:

```python
def register_workspace_commands(subcommands: argparse._SubParsersAction) -> None: ...
def register_reconcile_command(subcommands: argparse._SubParsersAction) -> None: ...
```

The first registers `workspace` and `state` in their existing positions. The second is
called later at the current `reconcile` position, after runner registration and before
branch registration. This preserves ordered top-level command bytes.

Move exactly these handlers without cleanup or semantic rewrite:

- `handle_workspace_add`
- `handle_workspace_list`
- `handle_workspace_audit`
- `handle_workspace_doctor`
- `handle_workspace_init_harness`
- `handle_workspace_agent_add`
- `handle_workspace_agent_sync`
- `handle_workspace_host_profile_set`
- `handle_workspace_host_profile_list`
- `handle_state`
- `handle_reconcile`

Handlers may import `open_connection as _conn` and `print_json as _print_json` to keep the
movement mechanical. Do not introduce a context/service object.

### 2. Keep root facade and order

Update `src/coordinate/cli.py` to:

- directly import both registrar functions and all 11 handlers;
- replace the existing workspace/state parser block with
  `register_workspace_commands(subcommands)`;
- replace only the existing reconcile parser block with
  `register_reconcile_command(subcommands)`;
- remove the moved handler bodies;
- remove only imports proven unused after movement.

Do not reorder another registrar or handler. Do not rename the root compatibility
imports.

### 3. Update the exact contract

Regenerate `tests/fixtures/cli_contract.json` only after all public contract comparisons
pass. The expected fixture delta is exactly 11 `defaults.handler` strings:

```text
coordinate.cli.handle_<name>
  -> coordinate.workspace_cli.handle_<name>
```

All other normalized JSON bytes must be identical to the P9-0A1 fixture. The test/report
must implement an explicit structural comparison that permits only the exact path→handler
mapping and rejects any other difference.

### 4. Add workspace CLI boundary tests

Add `tests/test_workspace_cli.py` proving:

- root compatibility handler aliases are identical to `workspace_cli` handlers;
- `workspace_cli` does not import `coordinate.cli`;
- importing `coordinate.cli`, `coordinate.workspace_cli`, `coordinate.cli_support`, and
  `coordinate.pr_cli` in multiple clean orders succeeds;
- both registrar functions add the expected commands once and preserve their supplied
  parser position;
- all 11 leaves point to the moved callable handlers;
- representative success/error behavior for workspace add/list, unknown workspace
  doctor/state/reconcile, metadata JSON failure, init-harness validation, agent sync, and
  host-profile list remains unchanged with temp state;
- the root module no longer contains moved handler definitions or now-unused
  workspace-only service imports.

Existing service/unit tests remain authorities for audit, doctor, onboarding, agent
registry, host profiles, and reconciliation behavior.

## Allowed paths

Production:

- `src/coordinate/cli.py`
- `src/coordinate/workspace_cli.py` (new)

Contract/tests:

- `tests/test_cli_contract.py` only if needed for the exact handler-migration verifier
- `tests/fixtures/cli_contract.json`
- `tests/test_workspace_cli.py` (new)
- `tests/test_cli.py` only if a narrow owner/compatibility assertion cannot live in the
  new boundary test

Any need to change another production module, existing service test, packaging metadata,
schema, or harness file stops the worker and returns the plan for review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Top-level order, node/leaf count, action/default/help bytes change | Stop; restore exact registration position and parser arguments. |
| Fixture differs beyond the exact 11 handler identities | Treat as a regression; do not approve fixture regeneration. |
| Root handler import disappears or is not identical to new owner | Restore direct compatibility re-export. |
| Existing test patches a moved service through the root | Prove the caller; retarget internal test to the new owner or revise the plan. Do not add a lazy root backedge. |
| `workspace_cli -> cli` or business-service -> CLI edge appears | Stop and remove the cycle/backedge. |
| Handler movement changes output/exit/error/DB behavior | Restore the original body mechanically and add a regression. |
| Another path is required | Stop and request plan revision; do not expand scope ad hoc. |
| Test touches canonical DB/workspace/delivery/runtime | Stop, preserve evidence, and redesign around temp/parser-only state. |
| Provider fails before edits | Confirm clean worktree and retry/fallback as provider failure. |
| Provider fails after partial edits | Inspect JSONL/process/diff and resume only within approved paths. |

## Acceptance matrix

| Case | Expected evidence |
|---|---|
| Public CLI contract | 21 top-level, 75 leaves, 99 nodes; identical normalized bytes except exact 11 handler mappings |
| Registration order | `workspace`, `state`, and `reconcile` remain in original top-level positions |
| Handler ownership | 11 leaf handlers owned by `coordinate.workspace_cli`; root direct aliases remain identical |
| Behavior | Existing workspace/state/reconcile CLI success and error outputs/exits unchanged |
| Import direction | no `workspace_cli -> cli`, no service -> CLI edge, clean import orders |
| Scope | only approved paths; no business/schema/runtime/harness change |
| Regression | focused count does not drop from 231; full count does not drop from 1,366 |
| Privacy | fixture/tests contain no secret, raw prompt/reasoning, checkout-specific path, or DB row |

## Validation

Worker preflight before edits:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_cli_contract tests.test_agent_registry \
  tests.test_doctor tests.test_reconcile
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Required after implementation:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_workspace_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_agent_registry tests.test_doctor tests.test_reconcile
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Also record:

- start/worker commit SHAs and exact changed paths;
- before/after fixture SHA-256;
- structural diff proving only 11 handler identities changed;
- pre/post 21/75/99 counts;
- focused/full counts;
- root alias identity and import-order results;
- source/import inspection for backedges and stale root definitions;
- provider session/JSONL and any provider transition.

No deployment or multi-host smoke is required. This package changes only static parser/
handler ownership and tests; runtime side effects remain forbidden.

## Worker boundaries

- Fresh isolated Coordinate worktree from exact reviewed canonical `main`.
- One logical implementation at a time; no subagent scope expansion.
- Read/edit/test the exact allowed paths and create one local commit after all checks.
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
  4. bootstrap/supplement names exact paths, the 11-handler-only contract delta,
     validation, JSONL observation, and stop conditions;
  5. P9-0A2b/c and all later packages remain unauthorized.
