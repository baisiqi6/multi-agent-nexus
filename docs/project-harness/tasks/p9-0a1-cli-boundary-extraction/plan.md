# Detailed Execution Plan: p9-0a1-cli-boundary-extraction

> **Status:** in_review
>
> This plan may be reviewed now, but it does not authorize worker bootstrap or
> implementation until `slice-4-projection-hardening` is accepted and a refreshed
> pre-execution drift check confirms the reviewed boundaries remain current.

## Identity and revision

- Parent stage: `phase-9-execution-isolation` / `P9-0A`
- Package id: `p9-0a1-cli-boundary-extraction`
- Plan author / architect: Codex
- Intended plan reviewer: Claude Code Sonnet, read-only plan review
- Intended coding worker: unassigned; prefer Oh-My-Pi or OpenCode after approval and
  dependency release
- Intended code/result reviewer: Codex
- Plan path:
  `docs/project-harness/tasks/p9-0a1-cli-boundary-extraction/plan.md`
- Plan revision authority: latest Coordinate `plan.ready` event and its
  `plan_content_hash`
- Supersedes: none

## Refreshed preflight

Snapshot refreshed on 2026-07-12:

- Coordinate repository: `/Users/yinxin/projects/coordinate`
- Coordinate `main`: `8fadd687d68032cf656291e6bf537ec481fb3e25`, four local
  commits ahead of `origin/main`; unrelated `.qoder/` is untracked and must remain
  untouched.
- MultiNexus local `main`: `e5b08a0` after S3-C1 local closeout; no push occurred.
- `src/coordinate` is one Python distribution package with no internal import cycle.
- `src/coordinate/cli.py`: 2,071 lines, 71 top-level functions, 25 internal-module
  dependencies, one 699-line `build_parser()`, and 71 leaf command paths.
- `tests/test_cli.py`: 4,751 lines; focused current baseline is 149 tests passed in
  20.620 seconds with `PYTHONPATH=src python3 -m unittest tests.test_cli`.
- In the last 87 commits touching `src/coordinate`, `cli.py` changed 32 times and
  co-changed broadly with policy, PR, handoff, runtime, DB, transition, issue, and daemon
  modules. This is a change-concentration seam, not evidence of circular authority.
- Existing extraction precedent: `src/coordinate/pr_cli.py` owns PR command registration
  and handlers behind `register_pr_commands()`. Its runtime compatibility hook lazily
  resolves selected functions through the root CLI facade; current tests rely on that
  injection surface.
- Accepted full-suite baseline before this planning package is 1,263 tests from Slice 2;
  it was not rerun during this architecture-plan draft. A worker preflight must refresh
  focused and full baselines after Slice 4.
- No runtime, daemon, deployment, service, production DB, delivery, or remote-host state
  was changed for this plan.

## Problem and evidence

`cli.py` currently combines four responsibilities:

1. process startup, dotenv loading, global error handling, and the public console facade;
2. registration of every top-level and nested argparse command;
3. 71 command handlers spanning workspace, planning, execution, delivery, runtime, and
   assignment domains; and
4. imports of 25 internal modules required by those handlers.

Adding Phase 9 execution identity, job context, routing, and lease surfaces directly to
this file would amplify merge conflicts, test concentration, and accidental coupling.
The package otherwise has no import cycles, and persistence/lifecycle authority remains
clear, so a multi-package or service rewrite would be larger than the proven pain.

## Goal

In one behavior-preserving worker session, make `coordinate.cli` a thin composition
facade whose parser is assembled from domain registrars and whose domain handlers live
with those registrars, while preserving the exact 71-command contract and all existing
observable behavior.

## Non-goals

- Do not add Phase 9 executor, context, routing, capacity, or lease features.
- Do not change command names, nesting, flags, defaults, help intent, JSON shape,
  stdout/stderr routing, exit codes, or exception policy.
- Do not change Coordinate DB schema, events, idempotency keys, lifecycle transitions,
  completion receipts, delivery defaults, platform behavior, or runtime processes.
- Do not refactor business services, `completion.py`, `db.py`, `transitions.py`,
  `policy.py`, `discord_rendering.py`, PR publishing stages, or test style beyond what is
  required to preserve CLI compatibility.
- Do not introduce a plugin framework, command class hierarchy, dependency-injection
  container, dynamic discovery, entry-point scanning, or new third-party dependency.
- Do not deploy, restart services, access production DB state, send real Discord/KOOK
  messages, push, merge, or mark the package done.

## Invariants and authority boundaries

- `coordinate.cli:main` remains the public console entry point declared by
  `pyproject.toml`; `build_parser()` remains importable for tests and tooling.
- Domain services remain the authority for behavior. CLI modules parse, call one service
  boundary, serialize results, and choose an exit code; they do not own workflow state.
- Coordinate DB and harness mutations remain behind existing services and adapters.
- Static registration is explicit and deterministic. No runtime module scanning or
  provider-specific branching enters the composition root.
- Existing test/operator injection seams through `coordinate.cli` and the lazy
  `pr_cli -> cli` facade must be inventoried before movement. Preserve a narrow explicit
  compatibility alias only where a current caller proves it is needed.
- Imports must remain acyclic. Domain CLI modules may import business services and shared
  CLI helpers; business services must not import domain CLI modules.
- No command invocation in validation may use a live workspace/default platform when it
  could create a delivery or mutate runtime state. Tests use temporary/in-memory DBs.
- The unrelated `.qoder/` path is outside scope.

## Proposed changes

Allowed production changes are limited to the CLI composition layer:

1. Keep `src/coordinate/cli.py` responsible for dotenv fallback, `main()`, global parser
   options, global exception handling, `serve`, compatibility aliases proven necessary,
   and ordered calls to domain registrars.
2. Add explicit modules following the existing `pr_cli.py` pattern:
   - `src/coordinate/workspace_cli.py`: `workspace`, `state`, and `reconcile`;
   - `src/coordinate/planning_cli.py`: `event`, `task`, `plan`, and `operator`;
   - `src/coordinate/execution_cli.py`: `runner`, `job`, and `runtime`;
   - `src/coordinate/workflow_cli.py`: `branch`, `ci`, `review`, `merge`, and
     `assignment`;
   - `src/coordinate/issue_cli.py`: `issue`;
   - `src/coordinate/delivery_cli.py`: `delivery`, `policy`, and `worker`.
3. Keep `src/coordinate/pr_cli.py` as the PR registrar. Change its compatibility hook
   only if required to remove a verified cycle or preserve current injection behavior;
   otherwise leave it untouched.
4. Add `tests/test_cli_boundaries.py` to lock the composition contract, including the
   71 leaf command paths, registrar uniqueness, import direction, and supported
   compatibility aliases.
5. Modify only the directly affected existing CLI tests when import/patch targets must
   follow the extracted owner:
   - `tests/test_cli.py`
   - `tests/test_pr_cli.py`
   - `tests/test_pr_publish.py`
   - `tests/test_issues.py`
   - `tests/test_doctor.py`

The worker must stop and request a plan revision if another production module or a schema
change appears necessary.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| A command path or option disappears/duplicates | Stop; restore exact parser registration and add a regression case. |
| JSON, stdout/stderr, or exit-code behavior changes | Treat as a regression, not cleanup; restore the baseline behavior. |
| A moved handler bypasses its existing service | Stop and return the call to the current business-service boundary. |
| A circular import appears | Remove the CLI-to-CLI back edge or use a narrow explicit compatibility facade; do not add dynamic imports broadly. |
| Existing monkeypatch/injection tests fail | Inventory the caller and preserve only the proven compatibility alias or update an internal-only patch target with reviewer evidence. |
| Validation creates a live delivery or runtime mutation | Stop, record the exact command/effect, and return for review; never clean the DB directly. |
| Slice 4 changes relevant CLI files or semantics before execution | Invalidate the stale bootstrap/approval and revise/re-review this plan against then-current `main`. |
| Worker changes business logic or schema | Revert only the worker's out-of-scope lines and request changes. |
| Provider/CLI fails before edits | Preserve the clean worktree and retry/fallback as an execution failure, not a design failure. |

## Acceptance matrix

| Case | Setup | Expected result | Evidence |
|---|---|---|---|
| Public command tree | Build parser before and after | Same 71 ordered leaf command paths; no duplicate registrar ownership | Boundary test and captured command list |
| Parse compatibility | Representative success/error arguments for every registrar | Same parsed destinations/defaults and argparse exit behavior | Focused parser tests |
| Handler compatibility | Existing CLI suites with temp/in-memory DBs | Same service calls, JSON, stdout/stderr, and exit codes | Existing focused suites |
| Import boundary | Import every CLI/business module and inspect internal edges | No cycle; root facade depends on registrars, business modules do not depend on CLI modules | Architecture test/report |
| Injection compatibility | Current PR/issue/doctor monkeypatch paths | Proven seams still intercept the same call; obsolete internal seams are documented if moved | Compatibility tests |
| Scope | Inspect diff | Only allowed CLI composition/test files change; no schema/business/harness mutation | `git diff --name-only` |
| Regression | Run full suite | Refactor introduces no failure or test-count loss | Full unittest result |

## Validation

Worker preflight, after Slice 4 and before edits:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
PYTHONPATH=src python3 -m unittest tests.test_cli
PYTHONPATH=src python3 -m unittest discover tests
```

Required after implementation:

```bash
git diff --check
PYTHONPATH=src python3 -m unittest tests.test_cli_boundaries
PYTHONPATH=src python3 -m unittest tests.test_cli tests.test_pr_cli tests.test_issues tests.test_doctor
PYTHONPATH=src python3 -m unittest discover tests
```

Also verify:

- the exact ordered leaf-command list matches the refreshed pre-change snapshot;
- `coordinate --help` and every top-level `<command> --help` return the same exit code;
- the internal import graph has no strongly connected component larger than one;
- `cli.py` imports registrar modules rather than 25 business modules;
- no live delivery, runtime DB, service, or harness lifecycle mutation occurred;
- `git diff --name-only` is within the allowed production/test paths.

No deployment or multi-host smoke is required because this package is a structural CLI
refactor. Deployment remains forbidden in this package.

## Rollout and rollback

- Architecture review may complete before Slice 4, but worker bootstrap is forbidden
  until Slice 4 acceptance and a refreshed source/test drift check.
- Implement in a fresh isolated Coordinate worktree from then-current local `main`.
- Land as one local behavior-preserving checkpoint only after independent code review.
- Do not combine this refactor with P9-0A2, P9-1, schema changes, or feature work.
- Rollback is a local revert of the single refactor checkpoint. No data migration or
  runtime recovery should be necessary because behavior and schema do not change.
- Stop on relevant Slice 4 drift, command-contract mismatch, import cycle, full-suite
  regression, unexpected file scope, or any request for external side effects.

## Worker boundaries

- Worktree/branch: allocate only after dependency release from then-current Coordinate
  `main`, using an isolated `agents/<worker>/p9-0a1-cli-boundary-extraction` branch.
- Allowed production components: `src/coordinate/cli.py`, the six named new CLI modules,
  and `src/coordinate/pr_cli.py` only if compatibility evidence requires it.
- Allowed tests: `tests/test_cli_boundaries.py` and the five named existing CLI-facing
  test modules above.
- Allowed commands: read-only Git/code inspection and temporary/in-memory test commands.
- Forbidden: unrelated cleanup, `.qoder/`, commit, push, merge, deploy, service control,
  real platform delivery, production/remote DB access, lifecycle commands, mark-done,
  and self-approval.
- Required report: exact changed files, baseline/current command counts, focused/full
  test counts, import-cycle result, compatibility aliases retained, and remaining risks.
- Return provider session/JSONL/log handles when available. They prove activity, not
  correctness.

## Plan review record

- Review artifact: pending
- Reviewer: pending Claude Code Sonnet
- Verdict: pending
- Reviewed plan revision: pending latest `plan.ready` event/hash
- Must-fix findings: pending
- Resolution revision: pending

Any material edit after approval resets this plan to `in_review`, invalidates the prior
bootstrap, and requires a new `plan.ready` plus review. Relevant Slice 4 drift is material
even if this file did not change.

## Bootstrap gate

Before coding-worker bootstrap, all conditions must hold:

1. the exact plan revision has independent `approved` evidence;
2. `slice-4-projection-hardening` is accepted/closed;
3. a fresh Coordinate baseline records current SHA, 71-command equivalence or an
   explicitly reviewed contract change, focused/full test counts, import graph, and dirty
   paths;
4. no relevant drift requires plan revision;
5. the bootstrap names the allocated worktree/branch, approved review artifact, exact
   allowed paths, validation, JSONL observation, and stop conditions.

No worker bootstrap or assignment is authorized by plan approval alone.
