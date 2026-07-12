# P9-0A2b Coding Worker Supplement — Round 1

This supplement overrides conflicting generic workspace, branch, deployment,
cross-repository, progress-document, or closeout instructions in `worker-bootstrap.md`.

## Authoritative execution identity

- Role: coding worker only. Codex remains architect, operator, and result reviewer.
- Coordinate worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a2b-kimi`
- Required branch: `agents/mac-omp/p9-0a2b-event-task-plan-operator-cli`
- Required start SHA:
  `10862d97d02d6e20b191005f02a732c6fa44ad59`
- Canonical plan (read-only):
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a2b-event-task-plan-operator-cli/plan.md`
- Approved plan SHA-256:
  `b17714dc5d06a38363dfabdc1f66d4d684d312410f3ce11a1b054202830249d5`
- Plan review (read-only):
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a2b-event-task-plan-operator-cli/plan-review-round-1.md`
- Coordinate plan-approved event:
  `7ae48999-645f-4d29-a181-3b22cdf9630a`
- Assignment-requested event:
  `6834a2e8-02e5-422e-8bd7-1a80dead20de`
- Worker-handoff event:
  `9b08faee-a759-4571-a0ac-0d4f4534631d`
- Logical assignment session: `p9-0a2b-kimi-20260712T1040Z`

The implementation repository is Coordinate, not MultiNexus. Do not edit MultiNexus,
its harness, or generated bootstrap. The Operator owns lifecycle, delivery, review,
integration, push, and closeout.

## Exact task and hard scope

Implement the approved plan mechanically:

1. add `src/coordinate/planning_cli.py` with the two approved registrars and exactly the
   10 event/task/plan/operator handlers;
2. keep `coordinate.cli` as the static composition facade with direct handler aliases;
3. preserve the original registrar positions and all behavior;
4. add layered immediate/cumulative contract proof; and
5. add `tests/test_planning_cli.py` boundary/behavior tests.

Allowed production paths:

- `src/coordinate/cli.py`
- `src/coordinate/planning_cli.py`

Allowed test paths:

- `tests/test_cli_contract.py`
- `tests/fixtures/cli_contract.json`
- `tests/test_planning_cli.py`
- `tests/test_cli.py` only if an otherwise impossible narrow compatibility assertion is
  required

No other path is authorized. Stop if another path appears necessary.

## Required implementation details

- Preserve `latest_prepared_handoff_bootstrap` in root `cli.py`; a non-moved assignment
  handler still uses it. Move only `prepare_handoff` ownership.
- Lock that sibling `planning_cli.py` derives the same
  `Path(__file__).resolve().parents[2]` repository root for `handle_task_handoff`.
- Preserve the accepted P9-0A2a contract helper. Add a P9-0A2b layer so:
  - rewinding exactly the 10 planning handlers yields fixture SHA
    `652a77d5ee7ab2239b7e2a406560ae21ada4d93b7f7c076fa7c65d6e0aa3f048`;
  - rewinding those 10 and the prior 11 workspace handlers yields SHA
    `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.
- Reject missing/duplicate approved paths, unexpected planning/workspace ownership, and
  non-handler drift. Fixture self-consistency alone is insufficient.
- Generate the new fixture only from canonical output:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python3 tests/test_cli_contract.py --dump > /tmp/p9-0a2b-cli-contract.json
```

Inspect structural rewind evidence before replacing the tracked fixture; use a safe
file move/copy only after all non-fixture comparisons pass.
- Import-order tests must include root, support, workspace, planning, and PR CLI modules.

## Protocol

Before edits verify pwd/branch/start SHA/clean status/plan hash, then reproduce 289
focused and 1,384 full tests. Use `PYTHONDONTWRITEBYTECODE=1`.

After implementation run all plan commands, `git diff --check`, layered hash checks,
21/75/99 counts, 10/10 root alias identities, handoff-root equality, import orders, no
backedge/stale root bodies, and AST equality for all 10 moved handlers.

Create one local commit. Do not amend, push, merge, deploy, restart, SSH, invoke another
agent, touch live DB/delivery/runtime/harness state, edit docs, or perform closeout.
Return exact evidence and exactly one terminal `[agent-report]` block.

If Kimi quota/auth/provider fails, stop with `action=blocker` before guessing. The
Operator may resume or start GLM and will record the provider transition explicitly.
