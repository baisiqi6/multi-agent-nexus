# Worker Bootstrap: dogfood-doc-sync

## Session Startup

### Step 1: Confirm working directory

```bash
pwd
```

You should be at `/Users/yinxin/projects/multinexus`. If not, `cd /Users/yinxin/projects/multinexus`.

### Step 2: Check workspace state (read-only)

```bash
git status --short
git branch --show-current
git log --oneline -10
```

Rule: do not overwrite/revert changes that are not yours. If you find unrelated dirty files, log them but do not clean up.

### Step 3: Read project state

Read these files:
- `docs/project-harness/harness-state.json` — current_item, checklist_summary, recent_events
- `docs/project-harness/progress.md` — recent session logs

### Step 4: Read project boundaries

- `docs/project-harness/scope.md` — goals, non-goals, constraints
- `docs/project-harness/architecture.md` — module boundaries
- `docs/project-harness/domain-model.md` — core entities

### Step 5: Read assigned task plan

```bash
cat docs/project-harness/tasks/dogfood-doc-sync/plan.md
```

Follow this plan step by step.

## Your Assignment

- **Task**: dogfood-doc-sync
- **Title**: Dogfood: sync coordinator integration docs
- **Branch**: feature/multi-bot
- **Plan**: docs/project-harness/tasks/dogfood-doc-sync/plan.md
- **Phase**: approved

## Coordinator CLI

All state changes MUST go through coordinator CLI.
Do NOT call harnessctl directly.
Do NOT modify harness JSON files directly.
harnessctl is only for operator/harness repair.

```bash
cd /Users/yinxin/projects/multi-agent-coordinator
PYTHONPATH=src python3 -m multi_agent_coordinator --db /Users/yinxin/projects/multi-agent-coordinator/data/coordinator.sqlite3 <command> multinexus [options]
```

Commands:
- `assignment accept multinexus --task-id <id> --owner <agent> --session <sid>`
- `branch allocate multinexus --task-id <id> --owner <agent>`
- `pr link multinexus --task-id <id> --pr-url <url>`
- `ci check multinexus --task-id <id>`
- `merge gate multinexus --task-id <id>`
- `assignment closeout multinexus --task-id <id> --reviewer <name>`
- `assignment mark-done multinexus --task-id <id>`

## Implementation Protocol

- Work on ONE feature at a time
- Commit with descriptive messages after each logical change
- Run tests after every change
- Update progress.md with what you did

## Session End Protocol

1. Run tests to verify clean state
2. Update progress.md with session summary
3. Commit only task-relevant changes — do not commit secrets, local config, or generated noise
4. Report: what changed, test results, remaining risks, files modified

## Constraints

- Human gate: no merge without explicit approval
- No deploy without approval
- No out-of-scope changes without asking
- If stuck 3+ attempts on the same issue: stop and report blocker via coordinator CLI
