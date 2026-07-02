# Worker Bootstrap: phase-7.1.1-single-platform-bridge-process

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

Shared-worktree guard: this checkout may be used by other agents. If `pwd` is not `/Users/yinxin/projects/multinexus` or `git branch --show-current` is not `agents/mac-claude/phase-7.1.1-single-platform-bridge-process`, stop and report a blocker instead of switching branches.
Never run `git reset`, `git rebase`, `git checkout`, `git switch`, `git cherry-pick`, or `git push --force` to repair this workspace unless the operator explicitly asks you to.

### Step 3: Read project state

Read these files:
- `docs/project-harness/harness-state.json` — current_item, checklist_summary, recent_events
- `docs/project-harness/progress.md` — recent session logs

### Step 4: Read project boundaries

- `docs/project-harness/scope.md` — goals, non-goals, constraints
- `docs/project-harness/architecture.md` — module boundaries
- `docs/project-harness/domain-model.md` — core entities

### Step 5: Read assigned task plan + review context

```bash
cat docs/project-harness/tasks/phase-7.1.1-single-platform-bridge-process/plan.md
cat docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/review-feedback-2026-06-09-operator-postcloseout.md
cat docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/plan.md
```

The review feedback file is the post-closeout retrospective on Phase 7.1. The plan file is the source of truth for this task.

### Step 6: Read adjacent task context

Read these to understand what 7.1 round 1-3 changed (so you don't accidentally regress):
- `docs/project-harness/progress.md` 2026-06-08 section (dogfood feedback, session resume / shutdown / ingest parser fixes)
- `multinexus/agentd/worker.py` (this is the 1 agent 1 process worker; do not modify)
- `multinexus/agentd/coordinate_client.py` (this is the `bridge -> coord -> agentd` boundary; do not modify)

## Your Assignment

- **Task**: phase-7.1.1-single-platform-bridge-process
- **Title**: Phase 7.1.1 Single Platform Single Bridge Process
- **Branch**: agents/mac-claude/phase-7.1.1-single-platform-bridge-process
- **Plan**: docs/project-harness/tasks/phase-7.1.1-single-platform-bridge-process/plan.md
- **Phase**: approved
- **Owner before closeout**: mac-claude

## Coordinator CLI

All state changes MUST go through coordinator CLI.
Do NOT call harnessctl directly.
Do NOT modify harness JSON files directly.
harnessctl is only for operator/harness repair.

```bash
cd /Users/yinxin/projects/coordinate
PYTHONPATH=src python3 -m coordinate --db /Users/yinxin/projects/coordinate/data/coordinator.sqlite3 <command> discord-nexus [options]
```

Commands:
- `assignment accept discord-nexus --task-id <id> --owner <agent> --session <sid>`
- `assignment closeout discord-nexus --task-id <id> --reviewer <reviewer-name>`
- `assignment mark-done discord-nexus --task-id <id>`
- `branch allocate discord-nexus --task-id <id> --owner <agent>`
- `pr link discord-nexus --task-id <id> --pr-url <url>`
- `ci check discord-nexus --task-id <id> --pr-url <url>`
- `merge gate discord-nexus --task-id <id> --pr-url <url>`

## Implementation Protocol

- Work on ONE feature at a time
- Commit with descriptive messages after each logical change
- Run tests after every change
- Update progress.md with what you did
- The `multinexus/agentd/` directory is **out of scope** (already correct from 7.1 round 2-3)
- The `multinexus/adapters/` directory is **out of scope** (claude / codex / omp / opencode adapters are correct as-is)

## Visible Discord Updates

You, the worker agent, own execution updates in Discord. The coordinator should stay as the control plane; do not rely on coordinator event echoes as the human-readable collaboration thread.

Send concise human-readable updates in the channel at these points:
- **Start**: say you accepted `phase-7.1.1-single-platform-bridge-process` and list the 2-3 concrete steps you will do first.
- **Milestone**: when a meaningful sub-step is complete, summarize what changed, tests run, and next step.
- **Blocker**: if you need operator/reviewer input, mention `@Coordinator`, `@Codex`, or the assigned reviewer/operator if visible in the channel.
- **Done / review needed**: mention `@Coordinator` and `@Codex` (or the assigned reviewer) with changed files, tests, risks, and review request.

Keep each visible update short. Do not stream private reasoning or every command.
Each progress/blocker/done update should end with one machine-readable block so coordinator can ingest it:

```text
[agent-report]
action=progress
workspace_id=discord-nexus
task_id=phase-7.1.1-single-platform-bridge-process
summary="Completed <milestone>; tests: <result>; next: <next step>"

[agent-report]
action=blocker
workspace_id=discord-nexus
task_id=phase-7.1.1-single-platform-bridge-process
reason="Need <decision/input>"

[agent-report]
action=done
workspace_id=discord-nexus
task_id=phase-7.1.1-single-platform-bridge-process
summary="Implemented <scope>; tests: <result>; risks: <risk-or-none>"
```

Use exactly one report block per visible update. The `[agent-report]` marker must start at the beginning of its own line.

## Session End Protocol

1. Run tests to verify clean state (`multinexus` 258+ tests, `coordinate` 731+ tests, new bridge multi-agent tests)
2. Update `progress.md` with session summary (mention this is a 7.1 closeout补完 task, not a new architecture)
3. For implementation tasks, run `assignment closeout discord-nexus --task-id phase-7.1.1-single-platform-bridge-process --reviewer operator`; do not mark your own implementation done
4. Commit only task-relevant changes — do not commit secrets, local config, or generated noise
5. Your final visible Discord message MUST include exactly one parseable `[agent-report]` block with `action=done`; natural-language completion alone is not enough for the operator
6. Report: what changed, test results, remaining risks, files modified, ps 拓扑截图 (1 coord + 1 discord-bridge + 4 agentd = 6 进程)

## Constraints

- Human gate: no merge without explicit approval
- No deploy without approval
- No out-of-scope changes without asking
- Do not modify `multinexus/agentd/*` (correct from 7.1 round 2-3)
- Do not modify `multinexus/adapters/*`
- Do not modify `multinexus/agentd/coordinate_client.py` (`bridge -> coord -> agentd` boundary is correct)
- 1 bridge 进程崩溃 = 全部 agent 的 Discord 入口同时断（这是 N+M 的有意取舍，要在 progress.md / runbook 里写清楚）
- If stuck 3+ attempts on the same issue: stop and report blocker via coordinator CLI
