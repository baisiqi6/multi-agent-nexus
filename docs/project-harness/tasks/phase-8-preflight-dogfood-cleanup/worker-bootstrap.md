# Worker Bootstrap: Phase 8 Preflight Dogfood Cleanup

You are implementing:

```text
workspace_id=discord-nexus
task_id=phase-8-preflight-dogfood-cleanup
```

## Read First

```bash
cd /Users/yinxin/projects/multinexus
cat docs/project-harness/tasks/phase-8-preflight-dogfood-cleanup/plan.md
cat docs/project-harness/dogfood-feedback.md

cd /Users/yinxin/projects/coordinate
sed -n '390,550p' docs/operator-needs-backlog.md
```

Also inspect the relevant code before editing:

```bash
cd /Users/yinxin/projects/coordinate
rg -n "pump-events|create-deliveries|handoff|worker.handoff.prepared|harness" src tests
```

## Scope

Implement only the three work items from the plan:

1. Safer `policy pump-events`.
2. `task handoff` preflight for checklist item existence / harness mutability.
3. Conservative status sync in `multinexus/docs/project-harness/dogfood-feedback.md`.

Do not implement GitHub issue scan, PR creation, KOOK bridge, deployment changes, service restarts, token changes, or real `agents.toml` changes.

## Repository Discipline

Use separate branches if you touch both repos:

```text
/Users/yinxin/projects/coordinate
/Users/yinxin/projects/multinexus
```

Before editing:

```bash
git status --short
git branch --show-current
```

Do not reset, rebase, clean, or force-push unless the operator explicitly asks. Preserve unrelated dirty files if any appear.

## Implementation Notes

For `policy pump-events`:

- Prefer explicit filters and/or an `--allow-backfill` guard over silent broad live delivery.
- Keep `policy create-deliveries <event-id>` as the recommended one-event live smoke command.
- Tests should prove `--limit 1` alone is not treated as a safe "latest event" live delivery selector.

For `task handoff`:

- Fail before event creation if the target task is missing from the registered workspace harness.
- The failure should be clear enough for an operator to know whether to add the checklist item or repair harness state.
- Tests should verify no `worker.handoff.prepared` event exists after a failed preflight.

For dogfood docs:

- Keep original problem descriptions.
- Update statuses and add "current handling" evidence.
- Mark unresolved progress streaming and KOOK work as deferred/open rather than hiding them.

## Validation

Run targeted tests first:

```bash
cd /Users/yinxin/projects/coordinate
PYTHONPATH=src python3 -m unittest tests.test_policy tests.test_cli tests.test_handoff -v
git diff --check

cd /Users/yinxin/projects/multinexus
python3 -m json.tool docs/project-harness/mvp-checklist.json >/dev/null
scripts/harness/harnessctl validate
git diff --check
```

Then run the full coordinate suite if feasible:

```bash
cd /Users/yinxin/projects/coordinate
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```

## Closeout Format

Your final Discord-visible response must end with exactly one structured block:

```text
[agent-report]
action=done
workspace_id=discord-nexus
task_id=phase-8-preflight-dogfood-cleanup
summary="Implemented dogfood cleanup; tests: <exact results>; risks: <remaining risks or none>"
```

If blocked:

```text
[agent-report]
action=blocker
workspace_id=discord-nexus
task_id=phase-8-preflight-dogfood-cleanup
reason="<specific blocker and what operator must decide>"
```
