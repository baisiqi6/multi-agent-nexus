# Worker Bootstrap: slice-4c2-issue-materialize-operation-adoption

## Mandatory start checks

You are the coding worker, not the architect, plan reviewer, operator, deployer or result
reviewer. Work only in the Coordinate worktree supplied by Codex.

Before editing, verify:

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
shasum -a 256 \
  /Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4c2-issue-materialize-operation-adoption/plan.md
```

Required values:

- Worktree: Codex-created dedicated Coordinate worktree
- Branch: `agents/mac-omp/slice-4c2-issue-materialize-operation-adoption`
- Start SHA: `1cbb547d7966c83c198125370f46bddc2d8640c9`
- Plan SHA-256:
  `7ed001a5f200109016d79298a5cd5dc86fe995d2964559808e6178db01be7dda`
- Plan review: `plan-review-round1.md`, approved with no P0/P1
- Coordinate approval: `2fa76501-8a52-48d1-83bc-9bb06a0d282f`

If any required identity differs, stop without editing and report the mismatch.

## Read first

Read the complete approved plan. It is the source of truth:

```bash
cat /Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4c2-issue-materialize-operation-adoption/plan.md
cat /Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4c2-issue-materialize-operation-adoption/plan-review-round1.md
```

Then inspect only the relevant current Coordinate code/tests before designing edits:

- `src/coordinate/split_operations.py`
- `src/coordinate/issues.py`
- `src/coordinate/issue_cli.py`
- focused delivery seams in `src/coordinate/db.py` and `src/coordinate/policy.py`
- `tests/test_split_operations.py`, `tests/test_issues.py`, `tests/test_issue_cli.py`,
  `tests/test_cli_contract.py`, policy/delivery tests.

## Implementation assignment

Implement the approved C2 adoption completely:

1. extend the shared C1 contract neutrally for `issue.materialize` source binding while
   preserving every C1 hash, wrapper and behavior;
2. make `materialize-files` require caller-owned workspace/operation/triage-event ids
   and use the shared lock/atomic envelope path;
3. make `materialize-record` verify the accepted triage event and exact deployed C2
   envelope before DB writes;
4. commit ledger, task, operation-bound `plan.ready`, operation-bound
   `issue.materialized`, final mirror link, ledger event link and optional rendered
   delivery in one savepoint/commit;
5. add minimum `commit=True` delivery seams with unchanged defaults, including explicit
   forwarding through `create_delivery_for_event` (plan-review P2); and
6. make exact retry compare immutable task/event/delivery intent, preserve progressed
   delivery status, and reject all partial-state/idempotency collisions.

Both `plan.ready` and `issue.materialized` idempotency keys must visibly include
`operation_id` (plan-review P2).

## Hard correctness boundaries

- Do not add schema v12 or a C2-only table/fingerprint/envelope.
- Do not trust file-host claims that the triage event is accepted; DB record preflight
  is authoritative.
- The accepted triage task mirror exists before materialization. Every injected failure
  must restore it byte/column-for-column; do not assert an empty tasks table.
- No record-before-deploy.
- No implicit operation UUID.
- No host-absolute path in canonical fingerprints.
- No repair of an existing operation-bound event/delivery without an exact ledger.
- No reset of sent/failed delivery operational fields on replay.
- Do not modify combined `issue materialize`, issue scan/triage, mark-done, S4-D,
  delivery pump leases, Phase 9, MultiNexus files or production state.
- If the shared C1 design cannot safely support C2 without changing C1 hashes or schema,
  stop and request plan revision.

## Test requirements

Implement every item in the plan's Tests and acceptance section, including:

- stable C1 witnesses plus new C2 source-bound witnesses;
- cross-second file retry and shared atomic/lock conflicts;
- all triage/deploy/envelope/fingerprint/source/target preflight refusals;
- failure injection after all seven DB/delivery steps with original accepted mirror
  restored;
- exact replay with no delivery and with a progressed `sent` delivery;
- pre-existing plan/materialized/delivery key collisions;
- same source/target conflict and independent issue operations;
- CLI help/JSON/errors and a C2-only fixture rewind to exact post-C1 bytes;
- combined materialize, C1, completion, handoff, event presentation, policy/delivery and
  full regression suites.

Use:

```bash
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest ...
```

The active Python 3.12 environment has nine known pre-existing CLI/AST historical
baseline failures. Do not rebaseline them or change historical SHA constants. The new
C2-only rewind proof itself must pass.

## Provider and evidence rules

- Model: `kimi-for-coding-highspeed` with high thinking.
- If Kimi returns a documented quota/auth/provider failure, stop; Codex may restart with
  GLM. Do not switch providers silently.
- Provider-native JSONL is primary activity evidence. Keep tool calls explicit and do
  not launch nested agents.

## Delivery and end protocol

1. Run focused tests, `ruff` on touched paths when available, `compileall`, full tests
   and `git diff --check`.
2. Review the complete diff against allowed paths and non-goals.
3. Update Coordinate `docs/progress.md` with session, tests and known pre-existing
   failures.
4. Commit all task-relevant Coordinate changes in one implementation commit. Do not
   deploy, SSH, push MultiNexus, call closeout/review/mark-done or mutate production DB.
5. Return commit SHA, changed paths, exact tests, remaining risk and exactly one block:

```text
[agent-report]
action=done
workspace_id=discord-nexus
task_id=slice-4c2-issue-materialize-operation-adoption
summary="Implemented S4-C2 on <sha>; <test evidence>; no deploy"
```
