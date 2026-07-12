# P9-0A4b Workflow and Assignment CLI Extraction

> **Status:** in_review
>
> This plan does not authorize implementation. A worker bootstrap may be generated only
> after an independent non-Codex reviewer approves this exact plan revision and
> Coordinate records a fresh `plan.approved` event.

## Identity

- Parent stage: `phase-9-execution-isolation` / `P9-0A`.
- Refinement parent: `P9-0A4 workflow/completion CLI`.
- Package id: `p9-0a4b-workflow-assignment-cli`.
- Plan author / architect: Codex.
- Intended plan reviewer: independent Kimi Code Highspeed through Oh-My-Pi; GLM is the
  explicit fallback on Kimi quota/auth/provider failure.
- Intended coding worker: a fresh non-Codex OMP session, preferring Kimi Highspeed and
  falling back to GLM only with explicit JSONL/provider transition evidence.
- Intended code/result reviewer and Operator: Codex.
- Plan path:
  `docs/project-harness/tasks/p9-0a4b-workflow-assignment-cli/plan.md`.
- Approval authority: latest Coordinate `plan.ready` plus full SHA-256 of this file.

P9-0A1, P9-0A2a/b/c, P9-0A3a/b, and P9-0A4a are durably closed. This package moves
only branch/CI/review/merge and non-receipt assignment CLI ownership. P9-0A5, Slice 4,
and every runtime-isolation package remain gated.

## Refreshed preflight

Snapshot on 2026-07-13:

- Coordinate reviewed start / `main == origin/main`:
  `4526d098ba4edcdcf669c41b6b6d827373088e5a`.
- Clean planning worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a4-plan`, branch
  `operator/p9-0a4-plan`, at the reviewed start.
- The shared Coordinate checkout's unrelated `.qoder/` and two named concurrent-edit
  safety stashes are outside scope and must remain untouched.
- MultiNexus canonical `main == origin/main`:
  `a457fbc7580a73e9d8ff4c10d4819017ba0fe7d8`.
- P9-0A4a is `done/closed` through receipt
  `23b7563a-89c7-4642-992f-5d50ebdefca0`.
- `src/coordinate/cli.py`: 730 lines.
- Current deterministic contract:
  - 21 ordered top-level commands;
  - 75 ordered leaves;
  - 99 parser nodes;
  - fixture SHA-256
    `a7c6e955062078bd67795f45dcdc27d82d076b31084e38ed1e459b8d4f758aca`.
- Earlier accepted fixture layers remain P9-0A3b `0bb76d48...`, P9-0A3a
  `fbdb5064...`, P9-0A2c `dde4c0d7...`, P9-0A2b `adddac8...`, P9-0A2a
  `652a77d5...`, and P9-0A1 `83c4c181...`.
- P9-0A4b owns exactly 12 leaves:
  - `branch allocate`;
  - `ci check`, `review check`, `merge gate`;
  - `assignment request`, `accept`, `handoff`, `blocker`, `unblock`, `closeout`,
    `review-result`, and legacy `mark-done`.
- Handler movement is exactly 12 functions / 254 source-span and nonblank lines:
  - branch 22;
  - CI/review/merge 45;
  - assignment 187.
- Parser movement has three required static seams, 117 span / 102 nonblank lines:
  - branch block: 9 / 8, immediately before the existing PR registrar;
  - CI/review/merge block: 29 / 24, immediately after PR and before issue;
  - assignment block: 79 / 70, immediately after runtime and before operator, including
    the existing `register_completion_commands(assignment_subcommands)` call.
- Refreshed focused baseline:
  `tests.test_cli tests.test_cli_contract tests.test_assignments tests.test_branches
  tests.test_ci tests.test_reviews tests.test_transitions tests.test_completion`
  = 472 tests passed.
- Refreshed full baseline: 1,523 tests passed on the same Coordinate tip.

## Problem and evidence

Root still owns workflow control commands even though their business authorities are
already separated across branches, CI, reviews, assignments, transitions, handoff, and
completion services. These commands are the remaining large domain boundary in
`cli.py`, and Slice 4 will harden their projections and split operations.

A single registrar cannot own all three parser ranges without reordering PR and the
issue/job/delivery/runtime families. The behavior-preserving design therefore uses
three explicit static calls in root. `workflow_cli` owns the assignment parser and
invokes P9-0A4a's completion registrar with its subparser. The dependency direction is
final and acyclic: `cli -> workflow_cli -> completion_cli`; completion never imports
workflow or root.

## Goal

In one behavior-preserving worker session:

1. add `coordinate.workflow_cli` as the owner of the 12 measured handlers;
2. add three static registrars at the exact current parser seams;
3. make `register_assignment_commands` own the assignment parser and delegate only the
   six receipt leaves to `register_completion_commands`;
4. keep `coordinate.cli` as public console/composition facade and direct alias source;
5. preserve every command/order/help/action/output/error/exit/DB/harness/idempotency
   behavior; and
6. extend contract proof through P9-0A4a and every prior accepted layer.

## Non-goals

- No receipt/completion semantic change and no modification to `completion_cli.py`.
- No PR CLI movement; `pr_cli` remains its existing owner and registrar.
- No changes to assignments, branches, CI, reviews, transitions, handoff, completion,
  DB, harness, schema, daemon, delivery, or runtime services.
- No P9-0A5 event presentation, Slice 4 projection/split-operation behavior, or P9-1+.
- No command/order/flag/default/dest/help/stdout/stderr/JSON/exception/exit/harness/
  idempotency/DB change.
- No plugin discovery, dynamic registry, command classes, DI container, package split,
  dependency addition, or opportunistic import cleanup.
- No deploy, restart, SSH, GitHub call, production DB/harness mutation, push, merge, or
  lifecycle mutation by the worker.

## Authority and dependency boundaries

- `coordinate.cli:main` and `coordinate.cli:build_parser` remain public.
- Root remains the explicit static composition root and retains all global dispatch
  exceptions.
- `workflow_cli` may import `cli_support`, assignments, branches, CI, reviews,
  transitions, handoff, and `completion_cli.register_completion_commands` only.
- `workflow_cli` must not import root, PR/issue/execution/delivery registrars, policy,
  runtime, daemon, or DB internals not already used by moved handlers.
- `completion_cli` and all lower services remain free of workflow/root imports.
- Root directly imports/re-exports all 12 handlers and three registrars.
- Root keeps `register_pr_commands` between branch and CI, all middle domain registrar
  calls between merge and assignment, and operator/serve after assignment.
- Do not remove pre-existing unused compatibility imports merely because movement makes
  them redundant. Any removal requires a separate reviewed cleanup package.

## Proposed changes

### 1. Add `workflow_cli.py`

Add `src/coordinate/workflow_cli.py` with exactly three registrars:

```python
def register_branch_command(subcommands) -> None: ...
def register_forge_commands(subcommands) -> None: ...
def register_assignment_commands(subcommands) -> None: ...
```

`register_forge_commands` adds CI, review, then merge in that order.
`register_assignment_commands` adds the eight non-receipt leaves in current order and
then calls `register_completion_commands(assignment_subcommands)` for the six receipt
leaves. Move exactly the 12 handlers listed in preflight without cleanup or semantic
rewrite. Preserve `_conn = open_connection` and `_print_json = print_json` so canonical
handler bodies stay stable.

### 2. Keep root facade and exact static call positions

Update `src/coordinate/cli.py` to:

- directly import the three registrars and 12 handlers;
- replace only current branch lines 273-281 with `register_branch_command(subcommands)`;
- leave `register_pr_commands(subcommands)` in place;
- replace only current CI/review/merge lines 285-313 with
  `register_forge_commands(subcommands)`;
- leave issue/job/delivery/runtime calls in place;
- replace only current assignment lines 323-401 with
  `register_assignment_commands(subcommands)`;
- leave operator and serve in place; and
- remove only the 12 moved bodies.

### 3. Extend layered contract proof

Relative to the P9-0A4a fixture, only exactly 12 handler strings may change from
`coordinate.cli.<handler>` to `coordinate.workflow_cli.<handler>`.

Add an A4b rewind helper that validates exclusive ownership and rewrites only those 12
strings. Full serialized bytes must then match P9-0A4a SHA `a7c6e955...`. Retain
cumulative checks in exact order:

1. A4b workflow rewind -> P9-0A4a `a7c6e955...`;
2. completion rewind -> P9-0A3b `0bb76d48...`;
3. delivery rewind -> P9-0A3a `fbdb5064...`;
4. execution rewind -> P9-0A2c `dde4c0d7...`;
5. issue rewind -> P9-0A2b `adddac8...`;
6. planning rewind -> P9-0A2a `652a77d5...`;
7. workspace rewind -> P9-0A1 `83c4c181...`.

Reject missing/duplicate approved paths, unexpected workflow ownership, and any
non-handler drift. Fixture regeneration or prefix counting is not proof.

### 4. Add workflow CLI boundary tests

Add `tests/test_workflow_cli.py` proving:

- root aliases are object-identical to all 12 handlers and three registrars;
- root has no moved definitions and retains `serve`, `main`, `build_parser`, global
  exception dispatch, PR/issue/execution/delivery/completion registrar aliases;
- no `workflow_cli -> cli/pr/issue/execution/delivery/runtime` backedge and no lower
  service imports workflow CLI;
- clean import orders across completion/workflow/root;
- three registrar calls remain at the exact seams and own exactly the 12 ordered leaves;
- assignment keeps all 14 leaves in exact order, with receipt leaves still owned by
  `completion_cli` and legacy mark-done owned by `workflow_cli`;
- all 12 handler bodies match constants generated once from reviewed start `4526d09`
  using the accepted canonical AST projection; no git history, `ast.unparse`, or
  whole-version-sensitive `ast.dump` in permanent tests;
- branch/CI/review/merge service argument forwarding and ValueError envelopes use mocks;
- assignment result envelopes, bootstrap lookup, gate failures, harness mutation
  failures, self-test evidence, and legacy mark-done exits use mocks; and
- no test opens production DB, runs harnessctl/coord-ssh, calls GitHub, or mutates a
  real harness.

Update the existing
`tests/test_completion_cli.py::CompletionCLIOwnershipTests::test_root_retains_legacy_mark_done_and_workflow_handlers`
boundary assertion: after A4b it must no longer require the three workflow handlers to
be literal root `FunctionDef` nodes. Instead, prove that root still exposes
object-identical aliases owned by `workflow_cli`, while receipt handlers remain
object-identical aliases owned by `completion_cli`. Do not change receipt behavior,
order, hashes, or completion delegation tests.

Existing service tests remain semantic authorities; the new file proves ownership and
delegation only.

## Allowed paths

Production:

- `src/coordinate/cli.py`;
- `src/coordinate/workflow_cli.py` (new).

Contract/tests:

- `tests/test_cli_contract.py`;
- `tests/fixtures/cli_contract.json`;
- `tests/test_workflow_cli.py` (new);
- `tests/test_completion_cli.py` only for the narrow root-definition-to-alias ownership
  assertion described above;
- `tests/test_cli.py` only if a narrow facade assertion cannot live in the new file.

Any need to modify `completion_cli.py`, a service, an existing service-semantic test,
another completion boundary test, packaging, schema, daemon, harness, or P9-0A5 path
stops the worker and returns the plan for review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Command/leaf/node/order/help bytes drift | Restore all three calls at exact seams. |
| A4b rewind misses `a7c6e955...` | Treat as regression; do not bless a new fixture. |
| Cumulative layer misses accepted SHA | Restore ordered rewinds; do not erase history. |
| Receipt leaf changes owner/args/order | Restore completion registrar delegation unchanged. |
| PR or middle domain registrar moves | Restore root ordering; outside scope. |
| Root alias missing or not identical | Restore direct compatibility import. |
| workflow imports root or completion imports workflow | Stop and remove the backedge. |
| Test touches real DB/harness/GitHub/SSH | Stop and redesign with mocks. |
| Another path is required | Stop and request plan revision. |
| Kimi quota/auth/provider fails before edits | Preserve evidence and restart with GLM. |
| Provider fails after partial edits | Correlate JSONL/process/diff; switch only in approved paths with attribution. |

## Acceptance matrix

| Case | Expected evidence |
|---|---|
| Public contract | 21 top-level, 75 leaves, 99 nodes; only 12 owner strings differ |
| Layered contract | workflow -> `a7c6e955`; +completion -> `0bb76d48`; +delivery -> `fbdb5064`; +execution -> `dde4c0d7`; +issue -> `adddac8`; +planning -> `652a77d5`; +workspace -> `83c4c181` |
| Registration | three static seams preserve branch/PR/forge/middle/assignment/operator order |
| Assignment | eight workflow leaves then six completion leaves; exact args/help/defaults |
| Ownership | 12 handlers in workflow CLI; root aliases identical; completion remains separate |
| Error/output | ValueError, mutation failure, gate, bootstrap, self-test, JSON and exits unchanged |
| Import direction | `cli -> workflow -> completion`; no backedge |
| Isolation | mocks only; no production DB, harness, GitHub, SSH, or lifecycle side effect |
| Scope | approved paths only; no service/completion/schema/runtime/harness change |
| Regression | focused does not drop from 472; full does not drop from 1,523 |

## Validation

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_workflow_cli tests.test_completion_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_assignments tests.test_branches tests.test_ci \
  tests.test_reviews tests.test_transitions tests.test_completion
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Record exact commits/paths, old/new fixture SHA, seven rewinds, 21/75/99, focused/full
counts, 12 canonical AST hashes, registrar/alias/import/order/error/delegation evidence,
provider session/JSONL, and any Kimi-to-GLM transition.

No runtime deploy or live workflow smoke is required for implementation acceptance.
Receipt-aware lifecycle closeout may deploy canonical harness state after code review;
that is an Operator action, not worker authority.

## Rollout, rollback, and worker boundaries

- Fresh isolated Coordinate worktree from exact reviewed `4526d09...`.
- One local worker commit; Codex may require attributed correction commits.
- Fast-forward integration only from the reviewed start; rollback is a normal revert.
- Worker edits/tests only allowed paths; no subagent, push, merge, deploy, restart, SSH,
  lifecycle, GitHub, or live harness action.
- Stop on contract drift, receipt change, service-file need, real side effect, unexpected
  provider transition, or non-fast-forward integration state.
