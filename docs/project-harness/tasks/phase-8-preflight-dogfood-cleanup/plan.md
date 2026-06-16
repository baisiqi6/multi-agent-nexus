# Phase 8 Preflight: Dogfood Cleanup

## Purpose

Close the dogfood gaps that can directly interfere with Phase 8 GitHub automation before implementing the GitHub issue -> operator -> worker -> PR loop.

This is a maintenance slice across two repositories:

- `/Users/yinxin/projects/coordinate`
- `/Users/yinxin/projects/multinexus`

Do this before Phase 8.1 issue intake work.

## Current Context

Phase 7.2 A0 is running with coordinate and the Discord bridge on Tencent Cloud. Mac and Windows hosts run agentd processes. Discord is the visible transcript; coordinate DB/events plus project harness files remain the source of truth.

Dogfood records show three categories that matter before GitHub automation:

1. `policy pump-events` can backfill old events or send a different event than the operator intended.
2. `task handoff` can reach Discord even when the target task is missing from `mvp-checklist.json`, making later closeout/review state impossible to write.
3. `dogfood-feedback.md` still marks some items open even though later work fixed or mitigated them.

## Non-Goals

- Do not implement GitHub issue scan or PR creation in this task.
- Do not change deployment services, systemd units, launchd plists, tokens, `.env`, or real `agents.toml`.
- Do not attempt to solve long-running worker progress streaming in this slice; keep it documented if still open.
- Do not enable KOOK bridge as part of this slice.

## Work Item 1: Safe `policy pump-events`

### Problem

Operators have used broad `policy pump-events` calls during live dogfood. This created deliveries for historical events or for a different event than expected.

Relevant backlog entries:

- `/Users/yinxin/projects/coordinate/docs/operator-needs-backlog.md`
  - `policy pump-events 会为历史 lifecycle 事件补发新协议 delivery`
  - `live smoke 缺少单事件安全投递路径`
  - `policy pump-events --limit 1 is not safe as latest-event delivery`

### Expected Direction

In `coordinate`, make live pump usage safer without breaking intentional backfill.

Acceptable implementation options:

- Add explicit filters such as `--created-after`, `--after-event-id`, `--task-id`, and/or `--event-type`.
- Add a guard for live platforms (`discord`, `discord_webhook`, `kook`) that refuses broad backfill unless `--allow-backfill` is set.
- Clarify in CLI help that `--limit` is not a latest-event selector.
- Prefer the already-existing `policy create-deliveries <event-id>` path for one-event smoke.

The exact combination is a worker design decision, but the final behavior must prevent accidental broad live Discord backfill.

### Acceptance

- A live-platform `policy pump-events` call without a safe filter or explicit backfill approval fails clearly.
- An intentional backfill remains possible with an explicit flag.
- A targeted pump/filter path has tests.
- Existing `policy create-deliveries <event-id>` behavior remains unchanged.
- Tests cover the historical misuse shape: `--limit 1` alone must not be described or accepted as "latest event" delivery for live platforms.

## Work Item 2: Handoff Preflight For Checklist Item Existence

### Problem

Phase 7.1 was handed off to a worker even though the target task was missing from `docs/project-harness/mvp-checklist.json`. The worker implemented code, but later assignment blocker/review state could not be written.

### Expected Direction

In `coordinate`, make `task handoff` fail before Discord delivery when the registered workspace harness cannot mutate or observe the target task.

Likely implementation points:

- `src/coordinate/handoff.py`
- `src/coordinate/cli.py`
- existing harness adapter / transition gate helpers
- tests around `task handoff`

The preflight should check the registered workspace harness for the task id before `worker.handoff.prepared` is appended and before any policy delivery can be created.

### Acceptance

- If the target task is missing from the workspace checklist/harness state, `task handoff` exits non-zero with a clear error.
- No `worker.handoff.prepared` event is appended in that failure case.
- No Discord delivery can be generated from a failed preflight.
- Existing successful handoff flow still works.
- Tests cover missing item, stale/missing harness state, and happy path.

## Work Item 3: Dogfood Feedback Status Sync

### Problem

`/Users/yinxin/projects/multinexus/docs/project-harness/dogfood-feedback.md` still has stale `open` entries. Some were fixed or mitigated later:

- Discord message rendering/embed work landed in coordinate.
- Phase 7.1 N+M topology was corrected by Phase 7.1.1 / Phase 7.2.
- `policy create-deliveries <event-id>` fixed the single-event multi-delivery gap on the coordinate side.

### Expected Direction

Update `dogfood-feedback.md` conservatively:

- Mark entries `fixed` only when verified by code/tests/progress.
- Mark entries `mitigated` when the sharp edge is reduced but not fully solved.
- Mark entries `deferred` when intentionally left for a later phase.
- Keep original observations; do not erase the audit trail.
- Link to coordinate backlog entries when the remaining work lives in coordinate.

Do not rewrite old historical task plans unless they are misleading as current source of truth.

### Acceptance

- The file clearly distinguishes:
  - still-open blockers before Phase 8,
  - fixed dogfood problems,
  - deferred UX improvements.
- Entries related to this task mention the commit/test evidence used for the new status.
- No runtime/generated harness state files are committed unless they are intentionally part of the plan.

## Suggested Branches

Use separate branches per repo:

```text
coordinate: agents/<agent-id>/phase-8-preflight-dogfood-cleanup
multinexus: agents/<agent-id>/phase-8-preflight-dogfood-cleanup
```

If one worker touches both repos, keep commits separate by repository and explain the cross-repo dependency in closeout.

## Validation

Coordinate:

```bash
cd /Users/yinxin/projects/coordinate
PYTHONPATH=src python3 -m unittest tests.test_policy tests.test_cli tests.test_handoff -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

Multinexus:

```bash
cd /Users/yinxin/projects/multinexus
python3 -m json.tool docs/project-harness/mvp-checklist.json >/dev/null
scripts/harness/harnessctl validate
git diff --check
```

If the full coordinate suite is slow, run targeted tests first, report targeted results, then run the full suite before closeout if feasible.

## Closeout Requirements

Worker closeout must include:

- files changed per repo,
- exact tests run and result counts,
- any behavior change to operator CLI commands,
- whether dogfood entries were marked `fixed`, `mitigated`, `open`, or `deferred`,
- explicit note that no token/env/deployment files were changed.

The final visible Discord message must include one parseable `[agent-report] action=done` block.
