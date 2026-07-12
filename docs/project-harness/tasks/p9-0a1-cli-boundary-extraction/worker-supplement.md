# P9-0A1 Worker Supplement

This supplement overrides conflicting generic text in `worker-bootstrap.md`. The
generated bootstrap correctly proves the Coordinate approval gate, but its primary repo,
worktree, deploy, progress-file, and worker-lifecycle instructions are not valid for this
cross-repo structural package.

## Exact gate and worktree

- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a1-cli-boundary-extraction/plan.md`
- Plan SHA-256:
  `00a52ea12a85f8e18aa6b9e56224ea5478b0ca7e21d3d2fc7e1ead0f540a3796`
- Approval artifact:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a1-cli-boundary-extraction/plan-review-round-4.md`
- Coordinate `plan.approved`: `b293eaac-5e12-4aab-bb11-e36c07a377dd`
- Coordinate implementation worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a1-kimi`
- Branch: `agents/mac-omp/p9-0a1-cli-boundary-extraction`
- Required start SHA: `e0cc1561cd20b0f22389234aefe92d01273860e4`
- Lifecycle session label: `p9-0a1-kimi-20260712T0915Z`

Stop immediately if `pwd`, branch, start SHA, or clean status differs. Do not switch or
repair branches. The canonical Coordinate checkout's unrelated `.qoder/` is outside this
worktree and outside scope.

## Implementation boundary

Read the approved plan and Round 4 artifact first. Implement the full approved P9-0A1
scope, not a smaller substitute:

1. add `src/coordinate/cli_support.py` with exact current `DEFAULT_DB_PATH`, connection
   context-manager, and JSON printing semantics;
2. import it from `coordinate.cli` while preserving root `_conn`, `_print_json`, and
   `DEFAULT_DB_PATH` compatibility names and leaving handler bodies in place;
3. add `tests/test_cli_contract.py` and the required deterministic
   `tests/fixtures/cli_contract.json` covering all 99 parser nodes, 21 ordered top-level
   commands, 75 ordered leaves, every action field, help, and exactly one leaf handler;
4. implement the exact environment allowlist, `MULTI_AGENT_COORDINATOR_DB` omission,
   temporary cwd, direct `build_parser()` call, `<DEFAULT_DB_PATH>` semantic token,
   stable action/callable identity, and fixed JSON bytes approved in the plan;
5. prove helper success/exception close semantics, Unicode JSON bytes, import order, no
   `cli_support -> cli` edge, and existing PR compatibility.

Allowed paths only:

- `src/coordinate/cli.py`
- `src/coordinate/cli_support.py`
- `tests/test_cli_contract.py`
- `tests/fixtures/cli_contract.json`
- `tests/test_cli.py` only if a narrow compatibility assertion is genuinely required

Do not modify `pr_cli.py`, another production/test module, packaging metadata, schema,
business logic, harness files, docs, `.qoder/`, or runtime configuration. Do not invoke a
subagent. Stop and report if another path appears necessary.

## Execution and validation

Before edits:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_cli
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

After edits run exactly the plan validation, including two byte-identical clean contract
generations, then:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_cli tests.test_pr_cli
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
git status --short
git diff --name-only
```

Create exactly one local commit after all checks pass. Do not amend, push, merge, deploy,
restart, SSH, access a live DB/workspace/delivery, invoke Coordinate/harness lifecycle,
or mark done. The Operator already owns assignment acceptance, closeout, and review.

## Required report

Report start/commit SHA, exact changed paths, contract hash from each clean generation,
21/75/99 counts, pre/post focused and full test counts, import-order/cycle results,
compatibility aliases, remaining risks, OMP session/JSONL handle, and exactly one block:

```text
[agent-report]
action=done
workspace_id=discord-nexus
task_id=p9-0a1-cli-boundary-extraction
summary="Implemented the approved P9-0A1 contract and support seam; tests: <exact>; risks: <none-or-list>"
```

Worker completion is not acceptance. Codex will independently review the committed diff
and rerun validation before any integration or lifecycle closeout.
