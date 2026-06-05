# Worker Bootstrap: phase-6.1-omp-smoke

## Session Startup

### Step 1: Confirm working directory

```bash
pwd
```

You should be at `/Users/yinxin/projects/discord-nexus`. If not, `cd /Users/yinxin/projects/discord-nexus`.

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
cat docs/project-harness/tasks/phase-6-fleet-expansion/plan.md
```

Follow this plan step by step.

## Your Assignment

- **Task**: phase-6.1-omp-smoke
- **Title**: mac-omp smoke test: 验证 omp agent 端到端链路
- **Branch**: feature/multi-bot
- **Plan**: docs/project-harness/tasks/phase-6-fleet-expansion/plan.md
- **Phase**: approved

## Coordinator CLI

All state changes MUST go through coordinator CLI.
Do NOT call harnessctl directly.
Do NOT modify harness JSON files directly.
harnessctl is only for operator/harness repair.

```bash
cd /Users/yinxin/projects/multi-agent-coordinator
PYTHONPATH=src python3 -m multi_agent_coordinator --db /Users/yinxin/projects/multi-agent-coordinator/data/coordinator.sqlite3 <command> discord-nexus [options]
```

Commands:
- `assignment accept discord-nexus --task-id <id> --owner <agent> --session <sid>`
- `branch allocate discord-nexus --task-id <id> --owner <agent>`
- `pr link discord-nexus --task-id <id> --pr-url <url>`
- `ci check discord-nexus --task-id <id>`
- `merge gate discord-nexus --task-id <id>`
- `assignment closeout discord-nexus --task-id <id> --reviewer <name>`
- `assignment mark-done discord-nexus --task-id <id>`

## Implementation Protocol

- Work on ONE feature at a time
- Commit with descriptive messages after each logical change
- Run tests after every change
- Update progress.md with what you did

## Visible Discord Updates

You, the worker agent, own execution updates in Discord. The coordinator should stay as the control plane; do not rely on coordinator event echoes as the human-readable collaboration thread.

Send concise human-readable updates in the channel at these points:
- **Start**: say you accepted `phase-6.1-omp-smoke` and list the 2-3 concrete steps you will do first.
- **Milestone**: when a meaningful sub-step is complete, summarize what changed, tests run, and next step.
- **Blocker**: if you need operator/reviewer input, mention `@Coordinator`, `@Codex`, or the assigned reviewer/operator if visible in the channel.
- **Done / review needed**: mention `@Coordinator` and `@Codex` (or the assigned reviewer) with changed files, tests, risks, and review request.

Keep each visible update short. Do not stream private reasoning or every command.
Each progress/blocker/done update should end with one machine-readable block so coordinator can ingest it:

```text
[agent-report]
action=progress
workspace_id=discord-nexus
task_id=phase-6.1-omp-smoke
summary="Completed <milestone>; tests: <result>; next: <next step>"

[agent-report]
action=blocker
workspace_id=discord-nexus
task_id=phase-6.1-omp-smoke
reason="Need <decision/input>"

[agent-report]
action=done
workspace_id=discord-nexus
task_id=phase-6.1-omp-smoke
summary="Implemented <scope>; tests: <result>; risks: <risk-or-none>"
```

Use exactly one report block per visible update. The `[agent-report]` marker must start at the beginning of its own line.

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
