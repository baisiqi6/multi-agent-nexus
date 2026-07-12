# Detailed Execution Plan: p9-0a1-cli-boundary-extraction

> **Status:** in_review
>
> This revision supersedes the previously approved P9-0A1 plan bytes and bootstrap.
> The old revision required Slice 4 to run first; the active roadmap now requires the
> bounded P9-0A structural seam before Slice 4. No worker bootstrap, assignment, code
> edit, push, deploy, or lifecycle closeout is authorized until an independent reviewer
> approves this exact revision and Coordinate records a fresh `plan.approved` event.

## Identity and revision

- Parent stage: `phase-9-execution-isolation` / `P9-0A`
- Package id: `p9-0a1-cli-boundary-extraction`
- Package role: CLI contract snapshot and shared-support seam; first package of the
  staged CLI boundary extraction
- Plan author / architect: Codex
- Intended plan reviewer: independent non-Codex read-only reviewer
- Intended coding worker after approval: Kimi Code Highspeed through Oh-My-Pi, or
  OpenCode/Claude Code if provider availability requires a reviewed fallback
- Intended code/result reviewer: Codex
- Plan path:
  `docs/project-harness/tasks/p9-0a1-cli-boundary-extraction/plan.md`
- Plan revision authority: latest Coordinate `plan.ready` event plus full SHA-256
- Supersedes:
  - plan SHA-256 `44caed57423bba8bb6cfc83b5a0b8db9703cb9e3e7570e320b109cd816976a11`;
  - `plan-review-round-1.md` approval tied to the old Slice-4-first gate;
  - the old reviewer/worker bootstrap generated from that revision.

The historical review artifact remains immutable evidence. It is not approval for this
revision.

## Refreshed preflight

Snapshot refreshed on 2026-07-12 after durable Slice 3 closeout:

- Coordinate canonical repository: `/Users/yinxin/projects/coordinate`
- Coordinate `main`, `origin/main`, and deployed Coordinate source identity:
  `e0cc1561cd20b0f22389234aefe92d01273860e4`
- Coordinate worktree has only unrelated untracked `.qoder/`; it must remain untouched.
- MultiNexus canonical `main` and `origin/main`:
  `b09a99475989fe1239e2cbc3aaa3900b1f8ef342`
- Slice 3 S3-C3, S3-C4, and umbrella are all reviewer-approved and `done/closed` through
  separate host-aware completion receipts. P9-0A no longer depends on Slice 4.
- `src/coordinate/cli.py`: 2,700 lines, 83 top-level functions, one parser builder from
  line 238 through the shared-connection seam at line 1,034, and imports from 25
  Coordinate modules.
- Current parser contract: 21 top-level commands and 75 ordered leaf command paths.
- `tests/test_cli.py`: 5,360 lines; refreshed focused baseline is 169 tests passed.
- Current accepted full Coordinate baseline is 1,347 tests on the same `e0cc1561`
  source identity. The worker must rerun it before and after implementation.
- Shared CLI helpers are still private functions in the root module:
  `DEFAULT_DB_PATH`, `_conn(args)`, and `_print_json(value)`.
- Existing precedent: `pr_cli.py` owns static PR registration behind
  `register_pr_commands()` while `coordinate.cli` preserves compatibility exports.
- Current package import graph has no known cycle. P9-0A addresses change concentration,
  not service or authority decomposition.

No code, schema, runtime, service, production DB, delivery, or remote-host state changed
while refreshing this plan.

## Problem and evidence

The old P9-0A1 plan attempted to move six command families and 67 handlers in one worker
session. Slice 3 then added seven completion-receipt leaf commands and approximately 600
CLI lines. A single extraction would now combine three different risks:

1. defining what public argparse behavior must remain stable;
2. creating a shared dependency direction that extracted registrars can safely import;
3. mechanically moving workspace, planning, issue, execution, delivery, workflow, and
   completion parser/handler families.

Doing all three at once makes a green full suite weak evidence: it becomes difficult to
distinguish a missing command/flag/default from an import-cycle or monkeypatch-ownership
regression. The smallest safe first package is therefore a contract-and-support seam,
not the entire CLI move.

## Goal

In one bounded, behavior-preserving worker session:

1. capture the current 75-leaf argparse contract in deterministic test evidence;
2. extract only the root CLI's generic database/JSON helpers into a tiny
   `coordinate.cli_support` module with an acyclic dependency direction; and
3. preserve `coordinate.cli` as the public facade, including `main`, `build_parser`,
   current compatibility exports, private aliases used by current handlers, and every
   observable command behavior.

This package prepares later command-family moves; it does not move a domain registrar or
handler yet.

## Non-goals

- No workspace/planning/issue/execution/delivery/workflow/completion handler movement.
- No `policy.py`, `discord_rendering.py`, `transitions.py`, `completion.py`, `db.py`,
  `pr_cli.py`, business-service, schema, migration, or runtime change.
- No command name, nesting, order, flag, alias, positional, requiredness, choice,
  default, metavar, help text, parser destination, output JSON, stdout/stderr routing,
  exit code, exception policy, idempotency key, or lifecycle semantics change.
- No plugin framework, dynamic discovery, command class hierarchy, DI container,
  entry-point scanning, package split, or third-party dependency.
- No live workspace command, platform delivery, job execution, harness mutation,
  production/local control-plane DB mutation, deploy, restart, SSH, push, merge, or
  package mark-done by the worker.
- No rewriting of the historical old plan review; this revision records supersession.

## Invariants and authority boundaries

- `coordinate.cli:main` remains the console entry point declared by `pyproject.toml`.
- `coordinate.cli:build_parser` remains importable and returns the same public tree.
- Parser registration stays explicit, static, and deterministically ordered.
- Business services remain behavioral authorities. `cli_support` may import only Python
  standard-library modules and the minimum persistence initializer required by the
  existing `_conn` behavior; it must not import `coordinate.cli` or domain registrars.
- `coordinate.cli` retains compatibility aliases `_conn`, `_print_json`, and
  `DEFAULT_DB_PATH` so existing internal callers/tests do not silently lose patch points.
- The contract snapshot is test evidence, not a second command registry. Runtime parser
  construction remains authoritative.
- Snapshot normalization must exclude unstable implementation identity such as function
  object repr/address while retaining public parser behavior.
- Tests and validation use temporary/in-memory DBs or parser-only invocations. They must
  not use the registered live `discord-nexus` workspace or default delivery platform.
- Provider JSONL establishes worker activity only; Codex independently reviews the diff,
  contract fixture, import graph, and test outcomes.
- Unrelated `.qoder/` remains untouched.

## Proposed changes

### 1. Deterministic CLI contract snapshot

Add both `tests/test_cli_contract.py` and
`tests/fixtures/cli_contract.json`.

The normalized snapshot must cover:

- root parser metadata and ordered top-level command names;
- all nested parser nodes and the exact ordered 75 leaf paths;
- for every parser action: positional/option strings, destination, action class,
  `nargs`, requiredness, choices, normalized default/const, metavar, type name, and help
  text;
- each leaf has exactly one callable handler;
- every parser node's `format_help()` output, including root, intermediate nodes,
  top-level commands, and leaves, after stable `prog` normalization and with
  `COLUMNS=100` pinned before formatting;
- no duplicate command path.

Normalization rules must be explicit in the test:

- action classes use `type(action).__name__`, never class repr;
- callable handler/default/type identity uses `__module__ + "." + __qualname__` when it
  is part of the recorded contract, never object repr;
- a default equal to the exact current `str(DEFAULT_DB_PATH)` is recorded as the
  semantic token `<DEFAULT_DB_PATH>`, and a separate assertion proves both that the
  parser default equals `str(DEFAULT_DB_PATH)` and that `DEFAULT_DB_PATH` resolves to
  `<coordinate checkout>/data/coordinator.sqlite3`;
- no other arbitrary local path, repr value, memory address, locale-dependent value, or
  environment-dependent wrapping may enter the fixture;
- both clean contract-generation subprocesses call `build_parser()` directly rather
  than `main()`, use an explicit environment allowlist, omit
  `MULTI_AGENT_COORDINATOR_DB`, set `COLUMNS=100`, `LANG=C`, `LC_ALL=C`,
  `PYTHONDONTWRITEBYTECODE=1`, and an absolute Coordinate `PYTHONPATH`, and run from a
  temporary working directory with no parent `.env`;
- contract JSON bytes use `json.dumps(..., ensure_ascii=False, sort_keys=True,
  indent=2) + "\n"` in both generation and fixture comparison.

Function/callable defaults may be excluded only when they are implementation-only
handler wiring already covered by the one-callable-per-leaf assertion. The test must fail
when a public flag/default/help/ordering value changes.

The fixture is a reviewed baseline, not auto-regenerated during ordinary test runs. A
future intentional CLI change updates it only through a separately reviewed contract
change.

### 2. Shared support seam

Add `src/coordinate/cli_support.py` owning exactly:

- `DEFAULT_DB_PATH`;
- `open_connection(args)` with the current `initialize(Path(args.db).expanduser())`,
  yield, and close behavior;
- `print_json(value)` with the current UTF-8-preserving, two-space, sorted-key JSON
  serialization.

Update `src/coordinate/cli.py` to import these names and retain compatibility aliases:

```python
_conn = open_connection
_print_json = print_json
```

The existing root handlers continue using those aliases in this package. Do not move or
otherwise rewrite handler bodies. Do not introduce a generalized context/service object.
`pr_cli.py` remains unchanged and retains its existing private `_conn`/`_print_json`
helpers in this package; sharing those helpers is outside P9-0A1 and requires a later
reviewed package if still worthwhile.

### 3. Boundary tests

The new test module must additionally prove:

- `cli_support` does not import `coordinate.cli`;
- importing `coordinate.cli`, `coordinate.cli_support`, and `coordinate.pr_cli` in clean
  subprocesses succeeds in more than one order;
- `coordinate.cli._conn`, `_print_json`, and `DEFAULT_DB_PATH` remain present and point
  to the support seam;
- the root parser `--db` default remains exactly `str(DEFAULT_DB_PATH)`, while the
  committed fixture contains only `<DEFAULT_DB_PATH>` and no checkout-specific path;
- connection close-on-success and close-on-exception behavior is unchanged;
- JSON output bytes for representative Unicode/nested values are unchanged;
- the existing `pr_cli` lazy compatibility surface still passes its focused tests.

## Allowed paths

Production:

- `src/coordinate/cli.py`
- `src/coordinate/cli_support.py` (new)

Tests/fixture:

- `tests/test_cli_contract.py` (new)
- `tests/fixtures/cli_contract.json` (new)
- `tests/test_cli.py` only if a compatibility assertion must follow the extracted helper
  owner; broad test rewriting is forbidden

Any need to touch another production file, `pr_cli.py`, packaging metadata, schema,
business service, or more existing test modules stops the worker and returns the plan for
review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Snapshot omits a current leaf/action/help surface | Correct the normalizer/fixture before support extraction; do not weaken acceptance. |
| Snapshot contains function repr, path noise, address, or order instability | Normalize only the unstable implementation identity and add a determinism test; do not sort away public order. |
| Current parser produces different snapshots across two clean runs | Stop and identify the nondeterministic field before committing a baseline. |
| Helper extraction changes JSON bytes, DB path expansion, initialize call, yield/close, exception propagation, or exit behavior | Restore exact current semantics and add a focused regression. |
| Import cycle or `cli_support -> cli` edge appears | Stop; remove the back edge. Dynamic/lazy imports are not an approved workaround. |
| Existing monkeypatch/injection test fails | Preserve the root compatibility alias; do not silently retarget broad tests or expose business services through support. |
| Diff escapes the allowed paths | Stop and return `changes_requested`; do not expand scope ad hoc. |
| Any test touches a live DB/workspace/delivery/runtime | Stop, preserve evidence, and redesign the test around temp/in-memory/parser-only state. |
| Provider fails before edits | Verify a clean worktree and retry with another approved non-Codex provider. |
| Provider fails after partial edits | Inspect JSONL/process/diff, preserve partial work, and resume only within the approved paths. |

## Acceptance matrix

| Case | Setup | Expected result | Evidence |
|---|---|---|---|
| Current tree inventory | Build parser from clean `e0cc1561` | 21 top-level commands, 75 ordered leaf paths, no duplicates | committed contract snapshot + test |
| Determinism | Generate normalized contract twice in clean subprocesses | Byte-identical normalized JSON/help evidence | focused test |
| Public parser coverage | Inspect every parser action and help surface | Flags/defaults/order/help represented; one callable per leaf | contract test/fixture review |
| Support behavior | Exercise Unicode JSON and temp DB success/exception paths | Exact serialization and close semantics preserved | focused tests |
| Compatibility facade | Import/use `coordinate.cli` aliases | `_conn`, `_print_json`, `DEFAULT_DB_PATH`, `main`, and `build_parser` remain available | boundary tests |
| Import direction | Import modules in varied orders and inspect source/import graph | no `cli_support -> cli`, no new cycle | tests + reviewer inspection |
| Existing CLI behavior | Run current focused CLI/PR suites | no failures or test-count loss | unittest output |
| Full regression | Run full Coordinate suite | no failure relative to refreshed baseline | unittest output |
| Scope/privacy | Inspect commit and JSON fixture | only allowed paths; no local paths, secrets, DB rows, raw prompts, or private reasoning | Git/reviewer inspection |

## Validation

Worker preflight before any edit:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_cli
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Required after implementation:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_cli tests.test_pr_cli
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Also record:

- exact start/worker commit SHAs and changed paths;
- pre/post 21 top-level and 75 leaf counts;
- two independently generated contract hashes;
- pre/post focused and full test counts;
- clean import-order subprocess results and import-graph cycle result;
- root compatibility aliases retained;
- provider session/JSONL handle and any provider transition.

No deploy or multi-host smoke is required for this behavior-preserving structural seam.
Push, merge, lifecycle closeout, and real runtime/DB/delivery work remain Operator-only.

## Rollout and rollback

- Land this package in a fresh isolated Coordinate worktree from exact current `main`.
- Worker creates one local behavior-preserving commit only after all tests pass; no
  amend/push/merge.
- Codex independently reviews fixture coverage, helper semantics, exact scope, focused
  and full regression, and import direction.
- After approval, the Operator may fast-forward the reviewed commit to Coordinate
  `main`, rerun validation, checkpoint harness evidence, and close the package through
  the public receipt-aware lifecycle.
- Rollback before integration is branch deletion; after integration it is a normal revert
  of the single package commit. No DB/runtime recovery should be needed.
- The next CLI-family package receives a new detailed plan against the resulting main;
  this plan does not authorize it.

## Worker boundaries

- Worktree/branch: allocate only after fresh plan approval from Coordinate `main`, using
  `agents/<worker>/p9-0a1-cli-boundary-extraction`.
- Allowed work: read-only inspection, edits to the exact allowed paths, temp/in-memory
  tests, one local commit, and a structured report.
- Forbidden: subagent scope expansion, business logic cleanup, style-only churn,
  `.qoder/`, direct harness JSON edit, Coordinate lifecycle mutation, push, merge,
  deploy, restart, SSH, production/local live DB access, delivery, sidecar cleanup, or
  self-approval.
- Required report: exact path/commit/contract/test/import evidence, remaining risks, and
  one `[agent-report]` block.

## Plan review record

- Historical approval artifact: `plan-review-round-1.md`, explicitly stale for execution
- Round 2 artifact: `plan-review-round-2.md`
- Round 2 reviewer: Kimi Code Highspeed through Oh-My-Pi
- Round 2 verdict: `changes_requested` on SHA-256
  `167ef44cfc48db5b74a99db811a9e8847e2740c07fee4fbe9c2d2bf869c95a8a`
- Round 2 must-fix resolution in this revision:
  - corrected the measured top-level command count from 22 to 21;
  - defined semantic normalization plus an independent assertion for the
    checkout-dependent `DEFAULT_DB_PATH`;
  - pinned `COLUMNS`, locale, action-class identity, and callable identity for
    deterministic contract generation;
  - explicitly retained `pr_cli.py` private helpers outside this package.
- Round 3 artifact: `plan-review-round-3.md`
- Round 3 reviewer: fresh Kimi Code Highspeed session through Oh-My-Pi
- Round 3 verdict: `changes_requested` on SHA-256
  `fed690eacb2fc99eba07899a803633a44f0dd3090422db6d71e8c777bfbca61e`
- Round 3 must-fix resolution in this revision:
  - contract subprocesses use an explicit environment allowlist and omit
    `MULTI_AGENT_COORDINATOR_DB`;
  - they call `build_parser()` directly from a temporary cwd, so `.env` loading through
    `main()` cannot alter defaults;
  - every intermediate parser help surface is included;
  - JSON bytes and callable `type` identity are deterministic.
- Current revision review artifact/reviewer/verdict: pending fresh `plan.ready` and
  independent Round 4 review

Any material edit after approval creates a new `plan.ready`, invalidates the current
review/bootstrap, and requires fresh independent review.

## Bootstrap gate

Before coding-worker bootstrap, all conditions must hold:

1. Slice 3 remains durably closed and MultiNexus `main` contains the final closeout;
2. Coordinate `main` still matches the reviewed start SHA or drift is assessed and the
   plan is revised/re-reviewed;
3. this exact plan revision has independent `approved` evidence;
4. the stale old blocker/approval/bootstrap is superseded through supported Coordinate
   lifecycle/events rather than direct JSON/SQLite edits;
5. the isolated worktree/branch and exact allowed paths are recorded;
6. the bootstrap includes the contract snapshot requirements, no-live-side-effect rule,
   JSONL observation, validation, report format, and stop conditions.

Plan approval alone does not authorize later P9-0A2+ packages.
