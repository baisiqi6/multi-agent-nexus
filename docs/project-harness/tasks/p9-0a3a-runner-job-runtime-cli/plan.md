# P9-0A3a Runner, Job, and Runtime CLI Extraction

> **Status:** in_review
>
> This plan does not authorize implementation. A worker bootstrap may be generated only
> after an independent non-Codex reviewer approves this exact plan revision and
> Coordinate records a fresh `plan.approved` event.

## Identity

- Parent stage: `phase-9-execution-isolation` / `P9-0A`
- Refinement parent: former `P9-0A3 execution/delivery CLI`
- Package id: `p9-0a3a-runner-job-runtime-cli`
- Plan author / architect: Codex
- Intended plan reviewer: independent Kimi Code Highspeed session through Oh-My-Pi;
  GLM is the explicit fallback on Kimi quota/auth/provider failure
- Intended coding worker: a fresh non-Codex OMP session, preferring Kimi Highspeed and
  falling back to GLM only with explicit JSONL/provider transition evidence
- Intended code/result reviewer: Codex
- Operator: Codex under the user's durable goal/gate delegation
- Plan path:
  `docs/project-harness/tasks/p9-0a3a-runner-job-runtime-cli/plan.md`
- Approval authority: latest Coordinate `plan.ready` plus full SHA-256 of this file

P9-0A1 and P9-0A2a/b/c are durably closed. P9-0A3a moves only runner/job/runtime CLI
ownership. P9-0A3b delivery/policy/worker and every later package remain gated.

## Measured refinement

The roadmap formerly grouped runner/job/runtime with delivery/policy/worker. Fresh
measurement shows two different stable authorities:

- runner/job/runtime: 16 leaves, 159 handler lines, runner/job/runtime services, and
  three non-contiguous parser positions;
- delivery/policy/worker: 10 leaves, 114 handler lines, bus/policy/worker services, and
  one contiguous parser range.

Moving all 26 handlers in one package would combine two service seams, four registrar
positions, 273 handler lines, and unrelated failure contracts. P9-0A3 is therefore
refined into P9-0A3a and P9-0A3b without changing parent scope or stage order.

## Refreshed preflight

Snapshot on 2026-07-12:

- Coordinate canonical `main == origin/main`:
  `10135bc3a49365a6c79d2088f4e3ff4b8015f27a`.
- Coordinate canonical checkout has only unrelated untracked `.qoder/`; it is outside
  scope and must remain untouched.
- MultiNexus canonical start:
  `882b6ebe394452a6856ecc520226118462274daf`.
- P9-0A2c is `done/closed` through receipt
  `2ce2cedc-33ca-4f4f-b66f-c9d6034c262a`.
- `src/coordinate/cli.py`: 1,909 lines.
- Current deterministic contract:
  - 21 ordered top-level commands;
  - 75 ordered leaves;
  - 99 parser nodes;
  - fixture SHA-256
    `dde4c0d7d8ac2b732be8cd3d2f915c880019c93ca993783c7a8cd0a1bd104c5f`.
- Earlier accepted fixture layers remain:
  - P9-0A2b `adddac8bd623b20a1f8b0f931e0ae83a45148315652c220d6f70c276f0f7cc74`;
  - P9-0A2a `652a77d5ee7ab2239b7e2a406560ae21ada4d93b7f7c076fa7c65d6e0aa3f048`;
  - P9-0A1 `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.
- P9-0A3a owns exactly 16 leaves:
  - `runner add`, `runner list`, `runner examples`, `runner example`;
  - `job create`, `job list`, `job run`, `job cancel`, `job retry`, `job pump`;
  - `runtime agent register`, `runtime agent heartbeat`, `runtime request submit`,
    `runtime job claim`, `runtime job report`, `runtime job progress`.
- Handler movement is exactly 159 lines:
  - runner: 33;
  - job: 56;
  - runtime: 70.
- Parser positions are intentionally non-contiguous:
  - runner follows planning and precedes reconcile;
  - job follows issue and precedes delivery;
  - runtime follows worker and precedes assignment.
- Refreshed focused baseline:
  `tests.test_cli tests.test_cli_contract tests.test_jobs tests.test_runtime
  tests.test_runner_examples` = 241 tests passed.
- Combined P9-0A3 service baseline including delivery/policy/worker = 427 tests passed.
- Refreshed full baseline: 1,434 tests passed on the same Coordinate tip.

No implementation, schema, DB, runtime, delivery, deploy, or remote mutation occurred
while preparing this plan.

## Problem

The root CLI still owns runner profile configuration, generic subprocess jobs, and the
bridge/agentd runtime protocol. These are the execution-control commands Phase 9 will
extend with execution context, attempts, routing, provider observation, and leases.
Leaving their argparse ownership and 16 handlers in the root would cause Slice 4 and
P9-1+ changes to re-concentrate in `cli.py`.

The three families are related but not contiguous. A single registrar would reorder
public commands or hide position-sensitive callbacks. Three explicit registrar
functions in one static `execution_cli` module preserve order and make the composition
boundary visible.

## Goal

In one behavior-preserving worker session:

1. add `coordinate.execution_cli` as the static owner of runner/job/runtime registration
   and exactly 16 handlers;
2. keep `coordinate.cli` as the public console/composition facade;
3. preserve every parser/action/help/output/exit/error/DB/subprocess/runtime behavior;
4. preserve all 16 root handler names as direct object aliases;
5. change only the 16 approved handler-owner strings relative to P9-0A2c; and
6. extend the full-baseline contract proof through all prior migration layers.

## Non-goals

- No delivery/policy/worker extraction; that is P9-0A3b.
- No job attempt, execution context, provider session, routing, capacity, lease,
  recovery, fairness, or scheduler behavior. Those belong to Slice 4/P9-1+.
- No changes to `db.py`, `jobs.py`, `runtime.py`, `runner_examples.py`, runner profile
  schema, job lifecycle, runtime attempt token rules, or subprocess execution.
- No command/order/flag/default/help/stdout/stderr/JSON/exception/exit/idempotency/DB
  schema change.
- No plugin discovery, dynamic registrar registry, command classes, DI container,
  package split, or dependency addition.
- No deploy, restart, SSH, live DB/runtime/job, push, merge, or lifecycle mutation by
  the worker.

## Authority and dependency boundaries

- `coordinate.cli:main` and `coordinate.cli:build_parser` remain public.
- `coordinate.cli` remains the explicit static composition root.
- `execution_cli` may import `cli_support`, the exact runner/job/runtime DB helpers,
  `jobs`, `runner_examples`, and `runtime` services needed by moved handlers. It must
  not import `coordinate.cli`, delivery/policy/worker CLI/services, or another CLI
  registrar.
- Business services must not import `execution_cli`.
- Root directly imports and re-exports all 16 handlers plus three registrars.
- Root must retain `JobError` because `main()` catches it after dispatch. Do not remove
  an error-class import merely because no moved handler references it.
- Root may remove the unused imported `coordinate.runtime.RuntimeError`; runtime
  service errors remain covered by their existing `ValueError` hierarchy and current
  `main()` behavior. This must be source-verified before removal.
- Root keeps `json`, `sys`, `_conn`, `_print_json`, `row_to_dict`, and delivery-related
  DB/services because unmoved delivery/workflow/completion handlers still require them.
- Tests patch the actually invoked `coordinate.execution_cli._conn` and service names,
  never root aliases or live DB/subprocess/runtime boundaries.
- Tests use temp/in-memory state and mocks only. They must not claim or run a real job,
  spawn a real provider process, use registered workspaces, or contact production.

## Proposed implementation

### 1. Add `execution_cli.py`

Add `src/coordinate/execution_cli.py` with three explicit registrar functions:

```python
def register_runner_commands(subcommands) -> None: ...
def register_job_commands(subcommands) -> None: ...
def register_runtime_commands(subcommands) -> None: ...
```

Move exactly these handlers without cleanup or semantic rewrite:

- runner: `handle_runner_add`, `handle_runner_list`, `handle_runner_examples`,
  `handle_runner_example`;
- job: `handle_job_create`, `handle_job_list`, `handle_job_run`, `handle_job_cancel`,
  `handle_job_retry`, `handle_job_pump`;
- runtime: `handle_runtime_agent_register`, `handle_runtime_agent_heartbeat`,
  `handle_runtime_request_submit`, `handle_runtime_job_claim`,
  `handle_runtime_job_report`, `handle_runtime_job_progress`.

Handlers may alias `open_connection`/`print_json` to `_conn`/`_print_json` to preserve
AST bodies. Do not introduce a context/service object or normalize JSON parsing.

### 2. Keep root facade and exact positions

Update `src/coordinate/cli.py` to:

- directly import all three registrars and 16 handlers;
- replace the runner block at its exact position with
  `register_runner_commands(subcommands)`;
- replace the job block at its exact position with `register_job_commands(subcommands)`;
- replace the runtime block at its exact position with
  `register_runtime_commands(subcommands)`;
- remove the 16 moved handler bodies;
- remove only service imports proven unused after movement, preserving `JobError` and
  every root dependency still required by unmoved code.

Do not move delivery/policy/worker blocks or another registrar.

### 3. Extend layered contract proof

Relative to the P9-0A2c fixture, the only expected delta is exactly 16 handler strings:

```text
coordinate.cli.handle_<name>
  -> coordinate.execution_cli.handle_<name>
```

Add an explicit P9-0A3a rewind helper that validates exclusive ownership and rewrites
only those 16 strings. Full serialized bytes must then match P9-0A2c SHA `dde4c0d7...`.
Retain cumulative checks in this exact order:

1. A3a rewind -> P9-0A2c `dde4c0d7...`;
2. then issue rewind -> P9-0A2b `adddac8...`;
3. then planning rewind -> P9-0A2a `652a77d5...`;
4. then workspace rewind -> P9-0A1 `83c4c181...`.

Reject missing/duplicate approved paths, unexpected `execution_cli` ownership, and
non-handler drift at each layer. Fixture regeneration or prefix counting is not proof.

### 4. Add execution CLI boundary tests

Add `tests/test_execution_cli.py` proving:

- 16 root aliases are object-identical to `execution_cli` handlers;
- root source contains no moved handler definitions or execution-only service imports;
- root still exposes/catches `JobError` as before;
- `execution_cli` does not import root or delivery CLI/services;
- clean import orders across support/workspace/planning/issue/execution/PR/root succeed;
- runner, job, and runtime registrars remain in exact top-level positions and preserve
  all 16 leaf paths/order/owners; no unapproved leaf is owned by `execution_cli`;
- all 16 handler bodies match stable per-handler AST SHA-256 constants computed once
  from reviewed start `10135bc`; permanent tests must not run `git show` or depend on
  repository history;
- runner invalid/non-object env JSON and representative add/list/example delegation;
- job invalid/non-object payload JSON, result-path merge, and create/list/run/cancel/
  retry/pump delegation use `_conn` and mocked service seams;
- runtime capabilities/origin/reply/result JSON parsing and agent/request/job
  register/heartbeat/submit/claim/report/progress delegation remain unchanged;
- mocks patch the actually called module-level alias and assert calls, so tests cannot
  silently fall through to real SQLite, subprocesses, or runtime jobs.

Existing `test_jobs.py`, `test_runtime.py`, and `test_runner_examples.py` remain primary
business-semantic authorities; the new file focuses on ownership and delegation.

## Allowed paths

Production:

- `src/coordinate/cli.py`
- `src/coordinate/execution_cli.py` (new)

Contract/tests:

- `tests/test_cli_contract.py`
- `tests/fixtures/cli_contract.json`
- `tests/test_execution_cli.py` (new)
- `tests/test_cli.py` only if a narrow facade compatibility assertion cannot live in
  the new boundary file

Any need to change a service module, existing service test, packaging, schema, or
harness file stops the worker and returns the plan for review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Top-level/leaf/node/order/help bytes change | Restore exact three registrar call positions. |
| A3a rewind misses `dde4c0d7...` | Treat as regression; do not bless a new fixture. |
| Any cumulative layer misses its accepted SHA | Restore ordered rewinds; do not erase history. |
| Root alias missing or not object-identical | Restore direct compatibility import. |
| `execution_cli -> cli` or service -> CLI edge | Remove backedge; no lazy indirection. |
| Root loses `JobError` dispatch catch | Restore error import/behavior and add regression. |
| Runner/job/runtime handler behavior changes | Restore original body and add focused proof. |
| Test reaches real job/subprocess/runtime/DB | Stop and redesign with mocks/temp state. |
| Another path is required | Stop and request plan revision. |
| Kimi quota/auth/provider fails before edits | Preserve evidence and restart with GLM. |
| Provider fails after partial edits | Correlate JSONL/process/diff; switch only inside approved paths with attribution. |

## Acceptance matrix

| Case | Expected evidence |
|---|---|
| Public contract | 21 top-level, 75 leaves, 99 nodes; only 16 owner strings differ |
| Layered contract | A3a -> `dde4c0d7`; +C -> `adddac8`; +B -> `652a77d5`; +A -> `83c4c181` |
| Registration | runner/job/runtime remain at exact three positions with 16 ordered leaves |
| Ownership | handlers owned by `execution_cli`; root aliases identical; no unapproved leaf |
| Error boundary | root `main()` retains existing `JobError` dispatch behavior |
| Behavior | runner/job/runtime JSON/output/error/delegation unchanged |
| Import direction | no execution-to-root/delivery edge; clean import orders |
| Scope | approved paths only; no service/schema/runtime/harness change |
| Regression | focused does not drop from 241; full does not drop from 1,434 |
| Privacy | no secret, live payload, raw reasoning, checkout path, or DB row in fixtures/tests |

## Validation

Worker preflight:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_cli_contract tests.test_jobs tests.test_runtime \
  tests.test_runner_examples
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Required after implementation:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_execution_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_jobs tests.test_runtime tests.test_runner_examples
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Record start/worker commits, exact paths, old/new fixture SHA, four rewind hashes,
21/75/99, focused/full counts, 16 stable AST hashes, alias/import/order/error-boundary
results, provider session/JSONL, and any Kimi-to-GLM transition.

No runtime deployment or multi-host smoke is required for implementation acceptance.
Lifecycle closeout may deploy canonical harness state after code review; that is an
Operator action, not worker authority.

## Worker boundaries

- Fresh isolated Coordinate worktree from exact reviewed canonical main.
- One logical implementation at a time; no subagent scope expansion.
- Read/edit/test only allowed paths; create one local commit after validation.
- Do not amend, push, merge, deploy, restart, SSH, mutate lifecycle, run real jobs,
  clean `.qoder/`, or self-approve.
- Report exact contract/AST/import/error/test evidence plus one `[agent-report]` block.

## Review and bootstrap gate

- Review artifact/reviewer/verdict: pending.
- Any material plan edit changes its hash and requires fresh review.
- Before worker bootstrap:
  1. exact plan hash is independently approved;
  2. Coordinate main still matches `10135bc...` or drift is reviewed;
  3. fresh worktree/branch is recorded;
  4. bootstrap/supplement names exact repo, paths, four-layer proof, stable AST hashes,
     validation, Kimi-to-GLM fallback, and stop conditions;
  5. P9-0A3b and later packages remain unauthorized.
