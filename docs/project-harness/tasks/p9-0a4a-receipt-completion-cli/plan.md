# P9-0A4a Receipt Completion CLI Extraction

> **Status:** in_review
>
> This plan does not authorize implementation. A worker bootstrap may be generated only
> after an independent non-Codex reviewer approves this exact plan revision and
> Coordinate records a fresh `plan.approved` event.

## Identity

- Parent stage: `phase-9-execution-isolation` / `P9-0A`.
- Refinement parent: `P9-0A4 workflow/completion CLI`.
- Package id: `p9-0a4a-receipt-completion-cli`.
- Plan author / architect: Codex.
- Intended plan reviewer: an independent Kimi Code Highspeed session through Oh-My-Pi;
  GLM is the explicit fallback on Kimi quota/auth/provider failure.
- Intended coding worker: a fresh non-Codex OMP session, preferring Kimi Highspeed and
  falling back to GLM only with explicit JSONL/provider transition evidence.
- Intended code/result reviewer: Codex.
- Operator: Codex under the user's durable goal/gate delegation.
- Plan path:
  `docs/project-harness/tasks/p9-0a4a-receipt-completion-cli/plan.md`.
- Approval authority: latest Coordinate `plan.ready` plus full SHA-256 of this file.

P9-0A1, P9-0A2a/b/c, and P9-0A3a/b are durably closed. Fresh measurement splits the
former P9-0A4 into P9-0A4a receipt completion and P9-0A4b workflow/assignment. This
package moves only the receipt-aware completion CLI. P9-0A4b, P9-0A5, Slice 4, and
every runtime-isolation package remain gated.

## Refreshed preflight

Snapshot on 2026-07-12:

- Coordinate reviewed start / `origin/main`:
  `cfcb56f6605b381d54d6a9ca335b602c41e6e8ab`.
- Planning worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a4-plan`, branch
  `operator/p9-0a4-plan`, clean at the reviewed start.
- The shared Coordinate checkout's unrelated `.qoder/` and named safety stash are
  outside scope and must remain untouched.
- MultiNexus canonical `main == origin/main`:
  `923385cf30169534a3df8460ff613bb7c3c74445`.
- P9-0A3b is `done/closed` through receipt
  `63c3543b-bf56-45f2-bb40-8c2a805ed883`.
- `src/coordinate/cli.py`: 1,369 lines.
- Current deterministic contract:
  - 21 ordered top-level commands;
  - 75 ordered leaves;
  - 99 parser nodes;
  - fixture SHA-256
    `0bb76d483de6fcc122e82e5f242d34d326abc57e02b4647478320555dc5bc0bb`.
- Earlier accepted fixture layers remain:
  - P9-0A3a `fbdb5064f1d4870e5ee3ae68628c7cd8be618c37d085530f03336899a82e949c`;
  - P9-0A2c `dde4c0d7d8ac2b732be8cd3d2f915c880019c93ca993783c7a8cd0a1bd104c5f`;
  - P9-0A2b `adddac8bd623b20a1f8b0f931e0ae83a45148315652c220d6f70c276f0f7cc74`;
  - P9-0A2a `652a77d5ee7ab2239b7e2a406560ae21ada4d93b7f7c076fa7c65d6e0aa3f048`;
  - P9-0A1 `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.
- P9-0A4a owns exactly six leaves, in their current order:
  - `assignment mark-done-prepare`;
  - `assignment mark-done-preflight`;
  - `assignment mark-done-claim`;
  - `assignment mark-done-apply`;
  - `assignment mark-done-files`;
  - `assignment mark-done-record`.
- Movement is exactly 14 functions: 510 source-span lines / 491 nonblank lines:
  - six public handlers above;
  - `_run_mark_done_files_receipt`;
  - `_stamp_repair_verification`;
  - `_lookup_receipt_for_preflight`;
  - `_build_mark_done_event_cli_argv`;
  - `_forward_mark_done_preflight`;
  - `_forward_mark_done_claim`;
  - `_forward_mark_done_apply`;
  - `_run_remote_cli_json`.
- The receipt parser block is one contiguous 120-line range inside the existing
  assignment parser, immediately after legacy `assignment mark-done` and before the
  operator registrar.
- The remaining P9-0A4b scope is separately measured as 12 workflow/assignment
  handlers and 254 handler lines; it is not authorized here.
- Refreshed focused baseline:
  `tests.test_cli tests.test_cli_contract tests.test_completion tests.test_transitions`
  = 371 tests passed.
- Refreshed full baseline: 1,493 tests passed on the same Coordinate tip.

## Problem and evidence

The root CLI currently owns the most security-sensitive orchestration code in the
project: receipt issuance, preflight, atomic claim, canonical file application, apply
acknowledgement, deployed verification, consumption, repair-only stamping, and remote
CLI JSON failure translation. This is a cohesive completion authority but not the same
authority as branch/CI/review/assignment workflow commands.

Moving all of P9-0A4 at once would combine 491 nonblank receipt lines with another 254
workflow handler lines and two parser seams. The split reduces proof size while
preserving the final architecture: P9-0A4a introduces `completion_cli` with a registrar
that accepts an assignment subparser; P9-0A4b later moves ownership of that assignment
parser into `workflow_cli` and invokes the same registrar.

## Goal

In one behavior-preserving worker session:

1. add `coordinate.completion_cli` as the static owner of receipt-aware completion
   registration and exactly the 14 measured functions;
2. replace only the contiguous six-leaf receipt block with one explicit registrar call;
3. keep the assignment parser and all non-receipt workflow handlers in root;
4. keep `coordinate.cli` as the public console/composition facade;
5. preserve root aliases for all moved names and every parser/action/help/output/error/
   exit/subprocess/receipt/idempotency behavior; and
6. extend the full-baseline contract proof through P9-0A3b and all prior layers.

## Non-goals

- No change to receipt states, evidence gathering, fingerprints, expiry, actor binding,
  two-phase claim/apply ordering, deployed verification, consumption, or repair mode.
- No P9-0A4b branch/CI/review/merge/assignment extraction and no P9-0A5 renderer work.
- No Slice 4 projection/split-operation semantic change and no P9-1+ isolation.
- No changes to `completion.py`, `transitions.py`, `db.py`, `harness.py`, schemas,
  daemon, service, deployment, or provider behavior.
- No command/order/flag/default/dest/help/stdout/stderr/JSON/exception/exit/subprocess/
  idempotency/DB/filesystem change.
- No plugin discovery, dynamic registrar registry, command classes, DI container,
  package split, dependency addition, or opportunistic import cleanup.
- No deploy, restart, SSH, live production DB, real receipt mutation, push, merge, or
  lifecycle mutation by the worker.

## Authority and dependency boundaries

- `coordinate.cli:main` and `coordinate.cli:build_parser` remain public.
- `coordinate.cli` remains the explicit static composition root.
- `completion_cli` may import `cli_support`, `completion`, `transitions`, and the exact
  standard-library/DB helpers used by the moved functions. It must not import
  `coordinate.cli`, `workflow_cli`, another CLI registrar, or runtime/delivery modules.
- `completion.py`, `transitions.py`, and lower services must not import
  `completion_cli`.
- `register_completion_commands(assignment_subcommands)` adds only the six measured
  leaves and assumes the caller owns the assignment parser.
- Root directly imports/re-exports the registrar, all six public handlers, and all eight
  moved private helpers so existing import identities remain available.
- Root retains legacy `handle_assignment_mark_done`, `mark_done_task`, all non-receipt
  assignment handlers, and all top-level branch/CI/review/merge parser ownership.
- Root `main()` retains the existing global exception tuple, including `HarnessError`,
  `JobError`, `BusError`, `PolicyError`, `ValueError`, and `KeyError`.
- Do not remove pre-existing unused compatibility imports merely because movement makes
  them look redundant. Any import removal must be required for the new module boundary,
  source-verified, and covered by an explicit compatibility assertion.

## Proposed changes

### 1. Add `completion_cli.py`

Add `src/coordinate/completion_cli.py` with:

```python
def register_completion_commands(assignment_subcommands) -> None: ...
```

Move the exact six parser leaves and 14 functions listed in preflight without cleanup
or semantic rewrite. Preserve `_conn = open_connection` and `_print_json = print_json`
aliases so canonical handler bodies can remain stable. Preserve:

- preflight before claim, claim before local write, and apply after verified write;
- authoritative remote claim fields as the only `ReceiptEvidence` source;
- fail-closed handling for missing fields, non-zero exits, empty stdout, invalid JSON,
  missing result objects, mismatched fingerprints, expiry, actor, workspace, and task;
- `.py` wrapper dispatch through `sys.executable`;
- exact subprocess argv ordering and `capture_output/text/encoding` settings;
- repair-only mutual exclusion and audit stamp; and
- exact JSON envelopes, reason strings, and return codes.

### 2. Keep root facade and exact parser position

Update `src/coordinate/cli.py` to:

- directly import the registrar and all 14 moved names;
- replace only lines 401-520's receipt-leaf block with
  `register_completion_commands(assignment_subcommands)`;
- leave legacy `assignment mark-done` immediately before that call;
- leave `register_operator_command(subcommands)` immediately after the assignment
  family;
- remove the 14 moved bodies; and
- leave branch/PR/CI/review/merge, assignment ownership, `serve`, and `main` otherwise
  unchanged.

### 3. Extend layered contract proof

Relative to the P9-0A3b fixture, the only expected delta is exactly six handler strings:

```text
coordinate.cli.handle_assignment_mark_done_<suffix>
  -> coordinate.completion_cli.handle_assignment_mark_done_<suffix>
```

where `<suffix>` is `prepare`, `preflight`, `claim`, `apply`, `files`, or `record`.
Add an explicit A4a rewind helper that validates exclusive ownership and rewrites only
those six strings. Full serialized bytes must then match P9-0A3b SHA `0bb76d48...`.
Retain cumulative checks in this exact order:

1. A4a rewind -> P9-0A3b `0bb76d48...`;
2. delivery rewind -> P9-0A3a `fbdb5064...`;
3. execution rewind -> P9-0A2c `dde4c0d7...`;
4. issue rewind -> P9-0A2b `adddac8...`;
5. planning rewind -> P9-0A2a `652a77d5...`;
6. workspace rewind -> P9-0A1 `83c4c181...`.

Reject missing/duplicate paths, unexpected `completion_cli` ownership, and non-handler
drift at every layer. Fixture regeneration or prefix counting is not proof.

### 4. Add receipt completion CLI boundary tests

Add `tests/test_completion_cli.py` proving:

- all 14 root aliases are object-identical to `completion_cli` names;
- root has no moved function definitions and retains legacy mark-done/workflow bodies;
- no `completion_cli -> cli/workflow/delivery/execution` backedge;
- clean import orders across support/completion/workflow-root boundaries;
- registrar owns exactly six ordered leaves after legacy mark-done;
- all 14 moved function bodies match constants generated once from reviewed start
  `cfcb56f` using the accepted canonical AST projection: preserve node types, non-empty
  fields, scalar values, contexts, and list order while dropping only `None`/empty
  list/tuple fields; permanent tests must not use `git show`, repository history,
  `ast.unparse`, or whole-version-sensitive `ast.dump` output;
- all remote CLI process outcomes are mocked: success, non-zero JSON error, non-zero
  false result, stderr-only, empty stdout, invalid JSON, and missing result object;
- files path proves preflight -> claim -> local write -> apply order with mocks and
  proves no local mutation occurs before a successful claim;
- prepare/preflight/claim/apply/record and repair-mode delegations preserve exact
  arguments, envelopes, reason strings, and exit codes; and
- no test opens the production DB, invokes `coord-ssh`, or mutates a real checklist.

Existing `test_completion.py` and `test_transitions.py` remain service semantic
authorities. The new file proves ownership/delegation and critical orchestration order.

## Allowed paths

Production:

- `src/coordinate/cli.py`;
- `src/coordinate/completion_cli.py` (new).

Contract/tests:

- `tests/test_cli_contract.py`;
- `tests/fixtures/cli_contract.json`;
- `tests/test_completion_cli.py` (new);
- `tests/test_cli.py` only if a narrow facade assertion cannot live in the new boundary
  file.

Any need to change a service module, existing service test, packaging, schema, daemon,
harness file, or P9-0A4b path stops the worker and returns the plan for review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Top-level/leaf/node/order/help bytes change | Restore the registrar at the exact legacy-mark-done/operator seam. |
| A4a rewind misses `0bb76d48...` | Treat as regression; do not bless a new fixture. |
| Any cumulative layer misses its accepted SHA | Restore ordered rewinds; do not erase history. |
| Root alias missing or not object-identical | Restore direct compatibility import. |
| Receipt state/order/reason/argv/output changes | Restore the exact moved body; no cleanup. |
| Local write can occur before remote claim | Stop; this is a security regression. |
| Apply uses a local rather than authoritative claim field | Stop; restore remote evidence binding. |
| Test reaches production DB/SSH/coord-ssh/checklist | Stop and redesign with mocks/temp files. |
| Another path is required | Stop and request plan revision. |
| Kimi quota/auth/provider fails before edits | Preserve evidence and restart with GLM. |
| Provider fails after partial edits | Correlate JSONL/process/diff; switch only inside approved paths with attribution. |

## Acceptance matrix

| Case | Expected evidence |
|---|---|
| Public contract | 21 top-level, 75 leaves, 99 nodes; only six owner strings differ |
| Layered contract | A4a -> `0bb76d48`; +delivery -> `fbdb5064`; +execution -> `dde4c0d7`; +issue -> `adddac8`; +planning -> `652a77d5`; +workspace -> `83c4c181` |
| Registration | six leaves remain ordered after legacy mark-done inside assignment |
| Ownership | 14 functions owned by `completion_cli`; root aliases identical |
| Security order | preflight -> claim -> local write -> apply; record consumes only valid applied receipt |
| Error contract | subprocess/JSON/mismatch/expiry/repair reasons and exits unchanged |
| Import direction | no completion-CLI backedge; lower services remain CLI-free |
| Isolation | mocks/temp files only; no production DB, SSH, wrapper, receipt, or checklist |
| Scope | approved paths only; no service/schema/runtime/harness/P9-0A4b change |
| Regression | focused does not drop from 371; full does not drop from 1,493 |

## Validation

Worker preflight and required post-implementation commands:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_completion_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_completion tests.test_transitions
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Record start/worker commits, exact paths, old/new fixture SHA, six rewind hashes,
21/75/99, focused/full counts, 14 canonical AST hashes, alias/import/order/security/
error/argv results, provider session/JSONL, and any Kimi-to-GLM transition.

No runtime deployment or live receipt smoke is required for implementation acceptance
because this package is specified as behavior-preserving source movement. Receipt-aware
lifecycle closeout may deploy canonical harness state after code review; that remains an
Operator action, not worker authority.

## Rollout, rollback, and worker boundaries

- Worker uses a fresh isolated Coordinate worktree from exact reviewed start
  `cfcb56f...` and creates one local implementation commit.
- Codex reviews and may request attributed correction commits before integration.
- Integration is fast-forward only from the exact reviewed Coordinate start.
- Rollback is a normal revert before later packages build on it; never rewrite shared
  history.
- Worker edits/tests only allowed paths; no subagent scope expansion, push, merge,
  deploy, restart, SSH, lifecycle mutation, or live receipt operation.
- Stop on contract/security drift, service-file need, real side effect, unexpected
  provider transition, or non-fast-forward integration state.
