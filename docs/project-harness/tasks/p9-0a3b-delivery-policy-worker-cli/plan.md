# P9-0A3b Delivery, Policy, and Worker CLI Extraction

> **Status:** in_review
>
> This plan does not authorize implementation. A worker bootstrap may be generated only
> after an independent non-Codex reviewer approves this exact plan revision and
> Coordinate records a fresh `plan.approved` event.

## Identity

- Parent stage: `phase-9-execution-isolation` / `P9-0A`.
- Refinement parent: former `P9-0A3 execution/delivery CLI`.
- Package id: `p9-0a3b-delivery-policy-worker-cli`.
- Plan author / architect: Codex.
- Intended plan reviewer: independent Kimi Code Highspeed session through Oh-My-Pi;
  GLM is the explicit fallback on Kimi quota/auth/provider failure.
- Intended coding worker: a fresh non-Codex OMP session, preferring Kimi Highspeed and
  falling back to GLM only with explicit JSONL/provider transition evidence.
- Intended code/result reviewer: Codex.
- Operator: Codex under the user's durable goal/gate delegation.
- Plan path:
  `docs/project-harness/tasks/p9-0a3b-delivery-policy-worker-cli/plan.md`.
- Approval authority: latest Coordinate `plan.ready` plus full SHA-256 of this file.

P9-0A1, P9-0A2a/b/c, and P9-0A3a are durably closed. P9-0A3b moves only the
contiguous delivery/policy/worker CLI boundary. P9-0A4, P9-0A5, Slice 4, and every
runtime-isolation package remain gated.

## Refreshed preflight

Snapshot on 2026-07-12:

- Coordinate canonical `main == origin/main`:
  `533ffcb1be17c6a26e8d5acf31e9c3c05da1ef63`.
- Coordinate canonical checkout has only unrelated untracked `.qoder/`; it is outside
  scope and must remain untouched.
- MultiNexus canonical `main == origin/main`:
  `d477122f3545f83e2d1d6cacab42bcad38948de3`.
- P9-0A3a is `done/closed` through receipt
  `19d917fb-fb66-49f8-91ad-92d95b8cc93f`.
- `src/coordinate/cli.py`: 1,590 lines.
- Current deterministic contract:
  - 21 ordered top-level commands;
  - 75 ordered leaves;
  - 99 parser nodes;
  - fixture SHA-256
    `fbdb5064f1d4870e5ee3ae68628c7cd8be618c37d085530f03336899a82e949c`.
- Earlier accepted fixture layers remain:
  - P9-0A2c `dde4c0d7d8ac2b732be8cd3d2f915c880019c93ca993783c7a8cd0a1bd104c5f`;
  - P9-0A2b `adddac8bd623b20a1f8b0f931e0ae83a45148315652c220d6f70c276f0f7cc74`;
  - P9-0A2a `652a77d5ee7ab2239b7e2a406560ae21ada4d93b7f7c076fa7c65d6e0aa3f048`;
  - P9-0A1 `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.
- P9-0A3b owns exactly 10 leaves:
  - `delivery create`, `delivery list`, `delivery send`, `delivery pump`,
    `delivery recover-sending`;
  - `policy render-event`, `policy create-delivery`, `policy create-deliveries`,
    `policy pump-events`;
  - `worker delivery`.
- Handler movement is exactly 114 lines:
  - delivery: 56;
  - policy: 44;
  - worker: 14.
- Parser registration is one contiguous range after `register_job_commands` and before
  `register_runtime_commands`; delivery, policy, and worker retain that exact order.
- Refreshed focused baseline:
  `tests.test_cli tests.test_cli_contract tests.test_bus tests.test_policy
  tests.test_worker` = 382 tests passed.
- Refreshed full baseline: 1,467 tests passed on the same Coordinate tip.

The most recent remote deploy breaker scan observed one transient race on delivery
`5eed424d-2006-4139-9bfc-643b7bdaf13a`: one pump saw `sending` while another sender
completed it. The row is authoritatively `sent`, no later pump error exists, and this
behavior bug is evidence for Slice 4/P9 runtime hardening. It is explicitly not a
license to change bus behavior in this structural package.

## Problem and evidence

The root CLI still owns the complete user-facing delivery pipeline: delivery row
creation/sending/recovery, event-to-delivery policy orchestration, and the long-running
delivery worker loop. These ten handlers are a distinct authority from P9-0A3a's
execution-control commands and are one contiguous parser seam.

Slice 4 will harden projections and split operations, while P9-5 will exercise visible
multi-line delivery. Leaving this entire seam in root would re-concentrate those
changes in `cli.py`. A static `delivery_cli` owner makes the boundary explicit without
changing bus, policy, worker, lifecycle, or DB behavior.

## Goal

In one behavior-preserving worker session:

1. add `coordinate.delivery_cli` as the static owner of delivery/policy/worker
   registration and exactly ten handlers;
2. replace the one contiguous root parser range with one explicit registrar call;
3. keep `coordinate.cli` as the public console/composition facade;
4. preserve all ten root handler names as direct object aliases;
5. preserve every parser/action/help/output/exit/error/DB/bus/worker behavior; and
6. extend the full-baseline contract proof through P9-0A3a and all prior layers.

## Non-goals

- No fix for the observed concurrent-pump `sending` race, delivery recovery semantics,
  retry policy, worker loop, daemon behavior, or platform adapter.
- No P9-0A4 workflow/completion CLI extraction or P9-0A5 presentation registry.
- No Slice 4 projection/partial-operation change and no P9-1+ execution isolation.
- No changes to `bus.py`, `policy.py`, `worker.py`, `db.py`, delivery schema,
  transaction boundaries, event rendering, or Discord payloads.
- No command/order/flag/default/help/stdout/stderr/JSON/exception/exit/idempotency/DB
  change.
- No plugin discovery, dynamic registrar registry, command classes, DI container,
  package split, or dependency addition.
- No deploy, restart, SSH, live DB/delivery/pump, push, merge, or lifecycle mutation by
  the worker.

## Authority and dependency boundaries

- `coordinate.cli:main` and `coordinate.cli:build_parser` remain public.
- `coordinate.cli` remains the explicit static composition root.
- `delivery_cli` may import `cli_support`, the exact delivery DB helpers, `bus`,
  `policy`, and `worker` services used by the moved handlers. It must not import
  `coordinate.cli`, `execution_cli`, workflow/completion CLI modules, or another CLI
  registrar.
- Business services must not import `delivery_cli`.
- Root directly imports and re-exports all ten handlers plus the registrar.
- Root must retain `BusError` and `PolicyError` because `main()` catches them after
  dispatch even though moved handlers no longer reference those names in root.
- Root removes only `pump_deliveries`, `send_delivery`, `create_delivery`,
  `list_deliveries`, `recover_sending_deliveries`, policy orchestration functions, and
  `run_delivery_worker` after source verification proves no unmoved caller remains.
- Root retains `json`, `sys`, `_conn`, `_print_json`, and `row_to_dict`; unmoved
  workflow/completion/assignment handlers still use them.
- Tests patch the actually invoked `coordinate.delivery_cli._conn`, service names, and
  output streams. They must never send a real delivery, pump a registered platform,
  recover production rows, open the production DB, or run a live worker loop.

## Proposed changes

### 1. Add `delivery_cli.py`

Add `src/coordinate/delivery_cli.py` with one registrar:

```python
def register_delivery_commands(subcommands) -> None: ...
```

The registrar adds three top-level families in the exact current order: `delivery`,
`policy`, then `worker`. Move exactly these handlers without cleanup or semantic
rewrite:

- delivery: `handle_delivery_create`, `handle_delivery_list`, `handle_delivery_send`,
  `handle_delivery_pump`, `handle_delivery_recover_sending`;
- policy: `handle_policy_render_event`, `handle_policy_create_delivery`,
  `handle_policy_create_deliveries`, `handle_policy_pump_events`;
- worker: `handle_worker_delivery`.

Handlers may alias `open_connection`/`print_json` to `_conn`/`_print_json` to preserve
their canonical AST bodies. Preserve `sys.stderr` forwarding and the worker's
`once -> max_iterations=1` rule exactly.

### 2. Keep root facade and exact position

Update `src/coordinate/cli.py` to:

- directly import the registrar and all ten handlers;
- replace only the contiguous delivery/policy/worker block after job and before runtime
  with `register_delivery_commands(subcommands)`;
- remove the ten moved handler bodies;
- remove only service imports proven unused after movement;
- retain `BusError`, `PolicyError`, root helper aliases, and every dependency still
  required by unmoved workflow/completion handlers.

Do not move job, runtime, assignment, or any other parser block.

### 3. Extend layered contract proof

Relative to the P9-0A3a fixture, the only expected delta is exactly ten handler strings:

```text
coordinate.cli.handle_<name>
  -> coordinate.delivery_cli.handle_<name>
```

Add an explicit P9-0A3b rewind helper that validates exclusive ownership and rewrites
only those ten strings. Full serialized bytes must then match P9-0A3a SHA
`fbdb5064...`. Retain cumulative checks in this exact order:

1. A3b rewind -> P9-0A3a `fbdb5064...`;
2. then execution rewind -> P9-0A2c `dde4c0d7...`;
3. then issue rewind -> P9-0A2b `adddac8...`;
4. then planning rewind -> P9-0A2a `652a77d5...`;
5. then workspace rewind -> P9-0A1 `83c4c181...`.

Reject missing/duplicate approved paths, unexpected `delivery_cli` ownership, and
non-handler drift at every layer. Fixture regeneration or prefix counting is not proof.

### 4. Add delivery CLI boundary tests

Add `tests/test_delivery_cli.py` proving:

- ten root aliases are object-identical to `delivery_cli` handlers;
- root source has no moved handler definitions or delivery-only service imports;
- root still imports/catches `BusError` and `PolicyError` exactly as before;
- `delivery_cli` has no root/execution/workflow/completion backedge;
- clean import orders across support/workspace/planning/issue/execution/delivery/root;
- the registrar remains between job and runtime and owns exactly the ten ordered leaves;
- all ten handler bodies match constants generated once from reviewed start `533ffcb`
  using the accepted canonical AST projection from P9-0A3a: retain node types,
  non-empty fields, scalar values, contexts, and list order while dropping only
  `None`/empty list/tuple fields; permanent tests must not use `git show`, repository
  history, or `ast.unparse`;
- delivery invalid/non-object payload, create/list/send/pump/recover delegation and
  exact `sys.stderr` forwarding use mocks;
- policy render/create/create-many/pump argument forwarding uses mocks;
- worker `once`, interval, limit, max-iterations, recovery, and output forwarding use
  mocks and cannot enter a real loop.

Existing `test_bus.py`, `test_policy.py`, and `test_worker.py` remain the business
semantic authorities. The new file proves ownership and delegation only.

## Allowed paths

Production:

- `src/coordinate/cli.py`;
- `src/coordinate/delivery_cli.py` (new).

Contract/tests:

- `tests/test_cli_contract.py`;
- `tests/fixtures/cli_contract.json`;
- `tests/test_delivery_cli.py` (new);
- `tests/test_cli.py` only if a narrow facade compatibility assertion cannot live in
  the new boundary file.

Any need to change a service module, existing service test, packaging, schema, daemon,
or harness file stops the worker and returns the plan for review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Top-level/leaf/node/order/help bytes change | Restore the registrar at the exact job/runtime seam. |
| A3b rewind misses `fbdb5064...` | Treat as regression; do not bless a new fixture. |
| Any cumulative layer misses its accepted SHA | Restore ordered rewinds; do not erase history. |
| Root alias missing or not object-identical | Restore direct compatibility import. |
| Root loses `BusError` or `PolicyError` dispatch | Restore imports/catch behavior and regression proof. |
| `delivery_cli` imports root/execution/workflow | Remove backedge; keep services below CLI. |
| Test sends/pumps/recovers real delivery or opens production DB | Stop and redesign with mocks. |
| Worker starts a real loop | Stop immediately; assert `run_delivery_worker` through a mock. |
| Concurrent-pump race appears | Record as pre-existing runtime evidence; do not change behavior here. |
| Another path is required | Stop and request plan revision. |
| Kimi quota/auth/provider fails before edits | Preserve evidence and restart with GLM. |
| Provider fails after partial edits | Correlate JSONL/process/diff; switch only inside approved paths with attribution. |

## Acceptance matrix

| Case | Expected evidence |
|---|---|
| Public contract | 21 top-level, 75 leaves, 99 nodes; only ten owner strings differ |
| Layered contract | B -> `fbdb5064`; +A -> `dde4c0d7`; +issue -> `adddac8`; +planning -> `652a77d5`; +workspace -> `83c4c181` |
| Registration | delivery/policy/worker remain one ordered contiguous seam between job/runtime |
| Ownership | handlers owned by `delivery_cli`; root aliases identical; no unapproved leaf |
| Error boundary | root retains `BusError` and `PolicyError` dispatch behavior |
| Behavior | JSON/error/output-stream/recovery/worker delegation unchanged |
| Import direction | no delivery-to-root/execution/workflow edge; clean import orders |
| Isolation | mocks prove no real DB, send, pump, recovery, platform, or worker loop |
| Scope | approved paths only; no service/schema/runtime/harness change |
| Regression | focused does not drop from 382; full does not drop from 1,467 |
| Privacy | no secret, live payload, raw reasoning, checkout path, or DB row in fixture/tests |

## Validation

Worker preflight:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_cli_contract tests.test_bus tests.test_policy tests.test_worker
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Required after implementation:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_delivery_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_bus tests.test_policy tests.test_worker
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Record start/worker commits, exact paths, old/new fixture SHA, five rewind hashes,
21/75/99, focused/full counts, ten canonical AST hashes, alias/import/order/error/output
results, provider session/JSONL, and any Kimi-to-GLM transition.

No runtime deployment or multi-host smoke is required for implementation acceptance.
Lifecycle closeout may deploy canonical harness state after code review; that is an
Operator action, not worker authority.

## Rollout and rollback

- Worker produces one isolated local commit; Codex reviews and may request attributed
  correction commits before integration.
- Integration is fast-forward only from the exact reviewed Coordinate start.
- This is behavior-preserving source movement with no migration or compatibility mode.
- Rollback is a normal revert of the integrated commit before later packages build on
  it; never rewrite shared history.
- Stop on contract drift, service-file need, real delivery side effect, unexpected
  provider transition, or any non-fast-forward integration state.

## Worker boundaries

- Fresh isolated Coordinate worktree from exact reviewed canonical `533ffcb...`.
- One logical implementation at a time; no subagent scope expansion.
- Read/edit/test only allowed paths; create one local commit after validation.
- Do not amend, push, merge, deploy, restart, SSH, mutate lifecycle, send/pump/recover
  live deliveries, clean `.qoder/`, or self-approve.
- Report exact contract/AST/import/error/output/test evidence plus one
  `[agent-report]` block.

## Plan review record

- Review artifact: pending.
- Reviewer: pending independent non-Codex reviewer.
- Verdict: pending.
- Reviewed plan revision: pending full SHA-256.
- Must-fix findings: pending.
- Resolution revision: pending.

Any material edit after approval resets status to `in_review` and requires a fresh
review artifact before bootstrap generation.

## Bootstrap gate

Before worker handoff:

1. exact plan hash is independently approved;
2. Coordinate main still matches `533ffcb...` or drift is reviewed;
3. fresh worktree/branch is recorded;
4. source-controlled bootstrap names exact repo, paths, five-layer proof, canonical AST
   projection, validation, Kimi-to-GLM fallback, and stop conditions;
5. P9-0A4, P9-0A5, Slice 4, and later packages remain unauthorized.
