# P9-0A2c Issue CLI Extraction

> **Status:** in_review
>
> This plan does not authorize implementation. A worker bootstrap may be generated only
> after an independent non-Codex reviewer approves this exact plan revision and
> Coordinate records a fresh `plan.approved` event.

## Identity

- Parent stage: `phase-9-execution-isolation` / `P9-0A`
- Refinement parent: `P9-0A2 workspace/planning/issue CLI`
- Package id: `p9-0a2c-issue-cli`
- Plan author / architect: Codex
- Intended plan reviewer: independent Kimi Code Highspeed session through Oh-My-Pi;
  GLM is the explicit fallback if Kimi quota/auth/provider availability fails
- Intended coding worker after approval: a separate non-Codex OMP worker, preferring
  Kimi Highspeed and falling back to GLM only with explicit JSONL/provider evidence
- Intended code/result reviewer: Codex
- Operator: Codex under the user's durable goal/gate delegation
- Plan path: `docs/project-harness/tasks/p9-0a2c-issue-cli/plan.md`
- Approval authority: latest Coordinate `plan.ready` plus full SHA-256 of this file

P9-0A1, P9-0A2a, and P9-0A2b are durably closed. P9-0A2c moves only issue CLI
ownership. P9-0A3 and every later package remain separately gated.

## Refreshed preflight

Snapshot on 2026-07-12:

- Coordinate canonical `main == origin/main`:
  `38da30f8bb508638e0cc30c301968153a420bdb7`.
- Coordinate canonical checkout has only unrelated untracked `.qoder/`; it is outside
  scope and must remain untouched.
- MultiNexus canonical `main == origin/main`:
  `1c1e389f7b3698573b6032be62281924a72f4bd7`.
- P9-0A2b is `done/closed` through receipt
  `4c85dd46-97b7-415f-85a1-450107e30112`.
- `src/coordinate/cli.py`: 2,115 lines.
- Current deterministic contract:
  - 21 ordered top-level commands;
  - 75 ordered leaves;
  - 99 parser nodes;
  - fixture SHA-256
    `adddac8bd623b20a1f8b0f931e0ae83a45148315652c220d6f70c276f0f7cc74`.
- Earlier accepted fixture layers remain:
  - P9-0A2a: `652a77d5ee7ab2239b7e2a406560ae21ada4d93b7f7c076fa7c65d6e0aa3f048`;
  - P9-0A1: `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.
- P9-0A2c owns exactly five leaves:
  - `issue scan`
  - `issue triage`
  - `issue materialize`
  - `issue materialize-files`
  - `issue materialize-record`
- The issue parser block is contiguous after merge and before job. One static registrar
  preserves its exact top-level position.
- Measured handler movement is 107 lines: 23 + 22 + 23 + 17 + 22.
- Refreshed focused baseline:
  `tests.test_cli tests.test_cli_contract tests.test_planning_cli tests.test_issues`
  = 265 tests passed.
- Refreshed full baseline: 1,411 tests passed on the same Coordinate tip.

No implementation, schema, DB, service, runtime, delivery, deploy, or remote mutation
occurred while preparing this plan.

## Problem

After P9-0A2b, the root CLI still owns the complete GitHub issue ingress and
materialization command family even though business behavior already lives in
`coordinate.issues`. The root therefore imports seven issue-only service symbols and
contains five handlers plus roughly one hundred lines of argparse registration.

This boundary is especially important before Slice 4: `materialize` has a combined
same-host operation while `materialize-files` and `materialize-record` are the explicit
host-aware split pair. Moving their CLI ownership without changing behavior creates a
stable place for later projection/partial-operation hardening. This package must not
attempt that hardening itself.

## Goal

In one behavior-preserving worker session:

1. add `coordinate.issue_cli` as the static owner of issue registration and exactly
   five handlers;
2. keep `coordinate.cli` as the public console/composition facade;
3. preserve every parser/action/help/output/exit/error/DB/filesystem/event-CLI behavior;
4. preserve the five public root handler names as direct object aliases;
5. change only the five approved handler-owner strings relative to the accepted
   P9-0A2b contract; and
6. extend cumulative contract proof so C rewinds to B, C+B rewinds to A2a, and
   C+B+A2a rewinds to A1.

## Non-goals

- No change to `src/coordinate/issues.py` or its GitHub/event/materialization semantics.
- No repair of split-operation projection order, deployed-harness freshness, global
  reconcile conflict isolation, pending delivery cancellation, or bootstrap routing.
- No runner/job/runtime/delivery/policy/worker/workflow/completion/PR extraction.
- No command, order, flag, default, help, stdout/stderr, JSON, exception, exit code,
  idempotency, platform delivery, DB schema, or persistence change.
- No plugin discovery, command classes, DI container, dynamic registrar lookup,
  package split, or new dependency.
- No deploy, restart, SSH, live GitHub/API/DB/workspace/delivery, push, merge, or
  lifecycle mutation by the worker.

## Authority and dependency boundaries

- `coordinate.cli:main` and `coordinate.cli:build_parser` remain public.
- `coordinate.cli` remains the explicit static composition root.
- `issue_cli` may import `cli_support` and `coordinate.issues`; it must not import
  `coordinate.cli`, another CLI registrar, GitHub adapters directly, or persistence
  internals not already used by the moved handlers.
- `coordinate.issues` and other business modules must not import `issue_cli`.
- Root re-exports all five moved handlers by direct import. Do not preserve issue-only
  service aliases in the root merely for hypothetical monkeypatching.
- Tests patch moved service calls in `coordinate.issue_cli`, not through a callback or
  backedge into the root.
- `handle_issue_scan --event-cli-path` must remain the host-aware remote-event path and
  must not open the local DB. The no-event-cli path must keep its current DB behavior.
- `materialize-files` remains filesystem-only and keeps the `/opt` runtime-copy guard;
  `materialize-record` remains DB/event-only. The combined `materialize` behavior is
  unchanged.
- Tests use temp/in-memory state and mocked GitHub/event CLI boundaries only. They must
  not contact GitHub, SSH, registered workspaces, production DBs, or live platforms.

## Proposed implementation

### 1. Add `issue_cli.py`

Add `src/coordinate/issue_cli.py` with one explicit registrar:

```python
def register_issue_commands(subcommands) -> None: ...
```

It registers the existing `issue` parser and all five leaves in their existing order.
Do not use a private argparse type annotation.

Move exactly these handlers without cleanup or semantic rewrite:

- `handle_issue_scan`
- `handle_issue_triage`
- `handle_issue_materialize`
- `handle_issue_materialize_files`
- `handle_issue_materialize_record`

Handlers may alias `open_connection`/`print_json` to `_conn`/`_print_json` so their AST
bodies remain identical. Do not introduce a context object or wrapper service.

### 2. Keep the root facade and order

Update `src/coordinate/cli.py` to:

- directly import `register_issue_commands` and the five handlers;
- replace only the issue parser block with `register_issue_commands(subcommands)` at
  the exact current position after merge and before job;
- remove the five moved handler bodies;
- remove only imports proven issue-only and unused after movement.

Do not reorder the PR, merge, job, planning, workspace, or other registrars. Root
utilities remain if any non-moved handler still uses them.

### 3. Extend layered contract proof

Update the contract fixture only after all comparisons pass. Relative to P9-0A2b, the
expected delta is exactly five strings:

```text
coordinate.cli.handle_issue_<name>
  -> coordinate.issue_cli.handle_issue_<name>
```

Add an explicit P9-0A2c rewind helper that:

1. requires exactly the five approved leaf paths to be owned by `issue_cli`;
2. rejects any unapproved `issue_cli` leaf owner;
3. rewrites only those five owner strings to `coordinate.cli`; and
4. requires full serialized bytes to hash to the P9-0A2b fixture
   `adddac8bd623b20a1f8b0f931e0ae83a45148315652c220d6f70c276f0f7cc74`.

Then retain cumulative checks:

- rewind C then B -> P9-0A2a SHA `652a77d5...`;
- rewind C then B then A2a -> P9-0A1 SHA `83c4c181...`.

Each layer must preserve all unrelated bytes and have a negative non-handler drift
test. Fixture regeneration, current-fixture equality, or module-prefix counts alone are
not acceptance evidence.

### 4. Add issue CLI boundary tests

Add `tests/test_issue_cli.py` proving:

- five root compatibility aliases are object-identical to `issue_cli` handlers;
- `issue_cli` does not import `coordinate.cli`;
- clean import orders across cli/support/workspace/planning/issue/PR modules succeed;
- the registrar adds exactly `issue` at the supplied position and preserves five leaf
  order/handler ownership;
- no unapproved leaf is owned by `issue_cli`;
- the root has no moved definitions or issue-only service imports;
- all five handler AST bodies match the start revision;
- scan with `--event-cli-path` calls only the remote event-CLI service seam and scan
  without it uses the DB seam;
- representative success/error behavior remains for scan, triage decisions and errors,
  combined materialize, files-only `/opt` guard/success, and record-only errors/success;
- tests patch the actually invoked module-level aliases (including `_conn` when used),
  so isolation assertions cannot silently fall through to real SQLite.

Existing `tests/test_issues.py` remains the primary authority for business semantics.
New tests should emphasize ownership, parser composition, delegation, and the split
operation boundary instead of duplicating the full service suite.

## Allowed paths

Production:

- `src/coordinate/cli.py`
- `src/coordinate/issue_cli.py` (new)

Contract/tests:

- `tests/test_cli_contract.py`
- `tests/fixtures/cli_contract.json`
- `tests/test_issue_cli.py` (new)
- `tests/test_cli.py` only if a narrow compatibility assertion cannot live in the new
  boundary test

Any need to change `issues.py`, another production module, an existing service test,
packaging, schema, or harness file stops the worker and returns the plan for review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Top-level/leaf/node order or parser bytes change | Stop; restore exact registrar position and arguments. |
| C rewind does not hash to `adddac8...` | Treat as regression; do not bless a regenerated fixture. |
| C+B or C+B+A2a misses an older hash | Restore layered proof; do not erase prior evidence. |
| Root alias is absent or not object-identical | Restore direct compatibility import. |
| `issue_cli -> cli` or service -> CLI edge appears | Remove the backedge; do not add lazy indirection. |
| event-CLI scan opens local DB | Restore the mutually exclusive host-aware path and add a regression. |
| files-only writes DB or record-only writes harness | Stop; restore split-operation boundary. |
| Test reaches live GitHub/SSH/DB/platform | Stop, preserve evidence, and redesign with temp/mocked seams. |
| Existing test patches issue services through root | Prove caller; retarget to new owner or revise plan, never add root backedge. |
| Another path is required | Stop and request plan revision. |
| Kimi quota/auth/provider fails before edits | Record failure and retry with GLM in a fresh provider interval. |
| Provider fails after partial edits | Correlate JSONL/process/diff; resume or switch only within approved paths and record attribution. |

## Acceptance matrix

| Case | Expected evidence |
|---|---|
| Public CLI contract | 21 top-level, 75 leaves, 99 nodes; only five owner strings differ from P9-0A2b |
| Layered contract | C -> `adddac8...`; C+B -> `652a77d5...`; C+B+A2a -> `83c4c181...` |
| Registration | one issue registrar remains after merge and before job; five leaves retain order |
| Handler ownership | five leaves owned by `coordinate.issue_cli`; root aliases identical |
| Split boundary | event-CLI scan avoids local DB; files-only and record-only responsibilities remain disjoint |
| Import direction | no issue_cli-to-root or service-to-CLI edge; clean import orders |
| Behavior | existing issue outputs/exits/errors/delegation unchanged |
| Scope | only approved paths; no service/schema/runtime/harness change |
| Regression | focused count does not drop from 265; full count does not drop from 1,411 |
| Privacy | fixture/tests contain no secret, raw reasoning, checkout path, live issue body, or DB row |

## Validation

Worker preflight before edits:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_cli_contract tests.test_planning_cli tests.test_issues
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Required after implementation:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_issue_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_planning_cli tests.test_issues
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Also record exact start/worker commits, changed paths, before/after fixture hashes,
three rewind hashes, 21/75/99 counts, focused/full counts, five AST comparisons, root
alias/import-order results, split-operation delegation evidence, provider session/JSONL,
and any Kimi-to-GLM transition.

No runtime deployment or multi-host smoke is required for implementation acceptance.
Lifecycle closeout may deploy the canonical harness solely to align the control-plane
projection; that is an Operator action after code review, not worker authority.

## Worker boundaries

- Fresh isolated Coordinate worktree from the exact reviewed canonical `main`.
- One logical implementation at a time; no subagent scope expansion.
- Read/edit/test exact allowed paths and create one local commit after checks.
- Do not amend, push, merge, deploy, restart, SSH, mutate lifecycle, use live GitHub/
  DB/delivery, clean `.qoder/`, or self-approve.
- Report exact scope/contract/test/import/split-boundary evidence and one
  `[agent-report]` block.

## Review and bootstrap gate

- Review artifact/reviewer/verdict: pending.
- Any material plan edit creates a new hash and requires fresh `plan.ready` and review.
- Before worker bootstrap:
  1. this exact plan hash is independently approved;
  2. Coordinate `main` still matches `38da30f...` or drift is reviewed;
  3. a fresh isolated worktree/branch is recorded;
  4. bootstrap/supplement names exact paths, three-layer proof, split boundaries,
     validation, JSONL observation, Kimi-to-GLM fallback, and stop conditions;
  5. P9-0A3 and all later packages remain unauthorized.
