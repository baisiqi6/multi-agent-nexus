# Slice 4A Deterministic Latest-Event Reads

> Detailed implementation plan. This document does not authorize implementation until
> an independent non-Codex reviewer approves this exact revision, Coordinate records
> the approval, and a fresh worker bootstrap binds the approved SHA.

## Identity

- Package id: `slice-4a-deterministic-latest-event-reads`.
- Stage: Slice 4 projection and split-operation hardening, package A.
- Required Coordinate start:
  `084419c5b36b32a81a39634c7ebbbf8b8b71d04c`.
- Intended plan reviewer: Kimi Code Highspeed through Oh-My-Pi; GLM is fallback only
  after documented Kimi quota/auth/provider failure.
- Intended coding worker: Kimi Code Highspeed through Oh-My-Pi, with the same fallback
  rule.
- Operator and result reviewer: Codex.

## Goal

Make the two remaining event-ledger reads that claim to select recent/latest evidence
deterministic when several SQLite events share the same second-level `created_at`.
Insertion order (`rowid`) is the event-ledger authority already used by
`db.latest_event`, plan gates, handoff gates, CI/review evidence and the daemon pump.

This package changes ordering only. It does not change which event types are eligible,
how owners are authorized, how events are inserted, or any lifecycle transition.

## Reviewed current state

Coordinate `084419c` contains exactly two production event queries that order newest
evidence by `created_at DESC` without an insertion-order tie-breaker:

1. `src/coordinate/daemon.py::_do_task_show` selects the five most recent status events
   from an explicit event-type allowlist using only `ORDER BY created_at DESC`.
2. `src/coordinate/policy.py::_task_owner_for_event` falls back from a task mirror owner
   to `assignment.accepted` / `task_mirror.updated` payloads using only
   `ORDER BY created_at DESC LIMIT 20`.

All other production event-ledger latest/recent reads either use `rowid DESC`, use
`created_at DESC, rowid DESC`, or intentionally stream ascending rowid. The separate
daemon task-list query orders mutable `tasks` rows by `updated_at`; it is display order,
not a latest-event authority, and is outside this package.

Measured baseline at the required start:

- `daemon.py`: 584 lines;
- `policy.py`: 704 lines;
- `tests/test_daemon.py`: 1,055 lines / 38 tests;
- `tests/test_policy.py`: 4,324 lines / 151 tests;
- focused `tests.test_daemon tests.test_policy`: 189 passing;
- full discovery: 1,572 passing under the known-good Python 3.14 interpreter.

## Problem and failure mode

SQLite does not promise a stable order among rows whose explicit `ORDER BY` keys are
equal. Multiple lifecycle events routinely receive the same second-level timestamp.
Without `rowid DESC`:

- daemon task display may present a same-second status sequence in an arbitrary order
  or omit the truly newest row from its five-row window; and
- lifecycle delivery may mention a stale owner when the task mirror has no owner and
  same-second assignment/mirror events disagree.

Both are projection defects. The canonical ledger already defines later insertion as
the later event, so the fix is an additive SQL tie-breaker, not a new clock or source of
truth.

## Authorized implementation

### 1. Daemon status projection

In `_do_task_show`, change only the status-event ordering clause to:

```sql
ORDER BY created_at DESC, rowid DESC
LIMIT 5
```

Keep the event-type allowlist, selected columns, limit, formatting and DB lifecycle
unchanged.

Add one behavioral regression test that inserts at least six eligible status events for
the same workspace/task, forces the same `created_at` on all of them, and proves:

- the five later rowids are shown;
- the oldest rowid is excluded; and
- the displayed status lines are newest-rowid first.

The test must exercise `_do_task_show`; a source-text assertion alone is insufficient.

### 2. Policy owner fallback

In `_task_owner_for_event`, change only the fallback ordering clause to:

```sql
ORDER BY created_at DESC, rowid DESC
LIMIT 20
```

Keep task-mirror owner precedence, eligible event types, malformed/empty payload skip
behavior, owner lookup, Discord identity lookup and lifecycle delivery semantics
unchanged.

Add one behavioral regression test with an ownerless task mirror and two eligible
same-second fallback events carrying different valid owners. Register both owners and
prove the lifecycle delivery targets the later inserted event's owner. The assertion
must check the selected mention/agent identity, not only SQL text.

### 3. Boundary audit proof

Add a narrow source/AST or SQL-normalization assertion only if needed to prove that the
two approved clauses are the last remaining timestamp-only event-ledger newest reads.
Do not build a general SQL parser or rewrite unrelated tests. Behavioral tests are the
primary acceptance evidence.

## Allowed paths

- `src/coordinate/daemon.py`;
- `src/coordinate/policy.py`;
- `tests/test_daemon.py`;
- `tests/test_policy.py`.

Any need for another production/test/doc/schema path stops implementation and returns
the package for plan revision.

## Explicit non-goals

- No change to the daemon `tasks ORDER BY updated_at DESC` display query.
- No event schema, timestamp precision, migration, index or DB helper change.
- No change to `db.latest_event`, `find_events`, append order, cursors or delivery pump.
- No owner precedence change and no new owner/source authority.
- No completion receipt, split-operation, registry sync, doctor/repair, reconciliation,
  provider routing, scheduler or Phase 9 work.
- No refactor of `daemon.py`, `policy.py` or the new `event_presentation.py` boundary.

## Failure matrix

| Failure | Required response |
|---|---|
| Same-second daemon rows are not newest-first | Restore `created_at DESC, rowid DESC`; do not alter timestamps. |
| Daemon shows more/fewer than five eligible rows | Restore existing limit/allowlist. |
| Ownerless task targets earlier same-second owner | Restore the rowid tie-breaker and verify insertion order. |
| Task mirror owner no longer wins | Restore mirror-first precedence. |
| Malformed payload behavior changes | Restore existing skip/fallback loop. |
| Another timestamp-only event authority is found | Stop and revise the measured scope before editing it. |
| A non-event task display is merely nondeterministic | Record for a separate UX package; do not absorb it here. |
| Kimi quota/auth/provider fails before edits | Preserve JSONL evidence and restart with GLM. |
| Provider fails after partial edits | Correlate JSONL/process/diff, preserve attribution and restart only under Operator control. |

## Acceptance matrix

| Case | Required evidence |
|---|---|
| Scope | exactly the four allowed paths or a smaller subset |
| Daemon SQL | `created_at DESC, rowid DESC`, unchanged allowlist/limit |
| Daemon behavior | same-second six-row window selects later five, newest first |
| Policy SQL | `created_at DESC, rowid DESC`, unchanged types/limit |
| Owner behavior | mirror wins; otherwise later same-second valid owner wins |
| Regression | focused does not drop from 189; full does not drop from 1,572 |
| Isolation | no production DB, harness, delivery, network, deploy or lifecycle side effect |

## Validation

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_daemon tests.test_policy
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Run with the known-good Python 3.14 interpreter for the authoritative 189/1,572
comparison. If the worker runtime resolves Python 3.12, report interpreter-specific
baseline differences honestly and let Codex repeat the known-good baseline.

## Worker protocol

1. Create a fresh isolated Coordinate worktree from exact `084419c`.
2. Verify cwd, branch, HEAD, clean status and exact approved plan SHA before editing.
3. Touch only allowed paths and make only the two SQL tie-breaker changes plus the two
   behavioral tests.
4. Run focused/full validation and inspect warnings.
5. Create one local commit; do not push, merge, deploy, SSH or mutate Coordinate
   lifecycle/harness state.
6. Codex independently reviews behavior, SQL scope, tests, diff and JSONL before any
   fast-forward integration.

## Rollback and stop conditions

Rollback is a normal revert of the integrated package. Stop before integration if any
test requires a production DB/network, if task-mirror precedence changes, if another
path is required, if the full suite gains a failure, or if same-second behavioral proof
cannot distinguish rowid order from timestamp order.
