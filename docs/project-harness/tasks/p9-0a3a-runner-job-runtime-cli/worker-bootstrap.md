# P9-0A3a Worker Bootstrap

This source-controlled bootstrap supersedes the generic text emitted by
`worker.handoff.prepared` event `b1930c57-1439-4203-aa55-1c7fca12ca1f` wherever
paths or permissions differ.

## Authority

- Task: `p9-0a3a-runner-job-runtime-cli`.
- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a3a-runner-job-runtime-cli/plan.md`.
- Required plan SHA-256:
  `66784772f8b356018bdb1674b56c00bf602bb76ce226c8acb0b789e52cf49b9b`.
- Plan approval event: `2680cf63-1947-4945-964b-c5f352ca0181`.
- Coordinate start: `10135bc3a49365a6c79d2088f4e3ff4b8015f27a`.
- Worker checkout:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a3a-kimi`.
- Required branch: `agents/mac-omp/p9-0a3a-runner-job-runtime-cli`.

The implementation repository is Coordinate, not MultiNexus. Do not edit either
canonical checkout under `/Users/yinxin/projects`; edit only the isolated Coordinate
worker checkout above.

## Startup gate

Before editing, verify:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
shasum -a 256 /Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a3a-runner-job-runtime-cli/plan.md
```

Stop and report a blocker if the checkout, branch, start commit, or plan SHA differs.
Read the full approved plan and `plan-review-round-2.md` before implementation.

## Authorized implementation

Perform only P9-0A3a:

- add `src/coordinate/execution_cli.py`;
- move the exact 16 runner/job/runtime handlers and their required service imports;
- add `register_runner_commands`, `register_job_commands`, and
  `register_runtime_commands` at the three approved parser positions;
- retain direct aliases from root `coordinate.cli` to all moved handlers;
- update the stable AST contract proof and approved fixtures/tests;
- preserve CLI behavior, JSON shape, exit codes, argument defaults, ordering, and root
  error boundary.

Allowed paths are exactly those listed in the approved plan. Do not implement
P9-0A3b delivery/policy/worker extraction, Slice 4, or P9-1+ behavior.

## Verification

Run the approved structural tests, the 241-test focused baseline, the four-layer
contract rewind proof, and the 1,434-test full baseline. Tests must mock job execution
and runtime effects; do not claim real jobs, spawn real worker subprocesses, touch live
DB state, deploy, or mutate lifecycle state.

Commit only task changes on the worker branch with a descriptive commit. Do not merge,
push, deploy, close out, mark done, modify MultiNexus harness files, or call coordinator
state transitions. Those remain Operator responsibilities.

## Report

Return:

- commit SHA and changed files;
- exact test commands and counts;
- contract counts, fixture SHA, and rewind hashes;
- any assumptions or remaining risk;
- exactly one final block:

```text
[agent-report]
action=done
workspace_id=discord-nexus
task_id=p9-0a3a-runner-job-runtime-cli
summary="Implemented P9-0A3a on <commit>; tests: <counts>; risks: <none-or-list>"
```

If blocked, do not improvise outside the plan. Report the exact blocker and stop.
