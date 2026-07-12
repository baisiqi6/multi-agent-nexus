# Worker Bootstrap: p9-0a2b-event-task-plan-operator-cli

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

Shared-worktree guard: this checkout may be used by other agents. If `pwd` is not `/Users/yinxin/projects/multinexus` or `git branch --show-current` is not `agents/mac-omp/p9-0a2b-event-task-plan-operator-cli`, stop and report a blocker instead of switching branches.
Never run `git reset`, `git rebase`, `git checkout`, `git switch`, `git cherry-pick`, or `git push --force` to repair this workspace unless the operator explicitly asks you to.

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
cat docs/project-harness/tasks/p9-0a2b-event-task-plan-operator-cli/plan.md
```

Follow this plan step by step.

## Your Assignment

- **Task**: p9-0a2b-event-task-plan-operator-cli
- **Title**: P9-0A2b Event Task Plan Operator CLI Extraction
- **Branch**: agents/mac-omp/p9-0a2b-event-task-plan-operator-cli
- **Plan**: docs/project-harness/tasks/p9-0a2b-event-task-plan-operator-cli/plan.md
- **Phase**: approved

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
- **Start**: say you accepted `p9-0a2b-event-task-plan-operator-cli` and list the 2-3 concrete steps you will do first.
- **Milestone**: when a meaningful sub-step is complete, summarize what changed, tests run, and next step.
- **Blocker**: if you need operator/reviewer input, mention `@Coordinator`, `@Codex`, or the assigned reviewer/operator if visible in the channel.
- **Done / review needed**: mention `@Coordinator` and `@Codex` (or the assigned reviewer) with changed files, tests, risks, and review request.

Keep each visible update short. Do not stream private reasoning or every command.
Each progress/blocker/done update should end with one machine-readable block so coordinator can ingest it:

```text
[agent-report]
action=progress
workspace_id=discord-nexus
task_id=p9-0a2b-event-task-plan-operator-cli
summary="Completed <milestone>; tests: <result>; next: <next step>"

[agent-report]
action=blocker
workspace_id=discord-nexus
task_id=p9-0a2b-event-task-plan-operator-cli
reason="Need <decision/input>"

[agent-report]
action=done
workspace_id=discord-nexus
task_id=p9-0a2b-event-task-plan-operator-cli
summary="Implemented <scope>; tests: <result>; risks: <risk-or-none>"
```

Use exactly one report block per visible update. The `[agent-report]` marker must start at the beginning of its own line.

## Self-Test Before Closeout

**Rule**: before requesting closeout, you MUST deploy and self-test when your changes touch server, daemon, or bridge code. Closeout without self-test evidence hides integration bugs — unit tests alone cannot catch daemon/bridge long-process defects (phase-8.5 KeyError / phase-8.6 dedup precedent).

### When deploy is required

- **Server / daemon / bridge code changes** → `scripts/deploy-server.sh` + live e2e smoke through the new code path
- **Pure doc / test / config changes** → skip deploy; self-test = run the full test suite

### Deploy + e2e smoke

```bash
scripts/deploy-server.sh
```

Then run through the new code path end-to-end in production and verify it works correctly.

### Self-test evidence

When calling `assignment closeout`, fill `--self-test-evidence` with what you did:

```bash
assignment closeout discord-nexus --task-id p9-0a2b-event-task-plan-operator-cli --reviewer <reviewer> \
  --self-test-evidence "Deploy SHA: <sha>; E2E: <result>; Bugs found: <list or none>"
```

**Empty `--self-test-evidence` → reviewer will see a warning. Do not skip this step.**

### Cross-repo coordination

If this task spans multiple repositories, verify the correct branch in each:
- Primary: `/Users/yinxin/projects/multinexus` branch `agents/mac-omp/p9-0a2b-event-task-plan-operator-cli`
- Coordinate (if applicable): `~/projects/coordinate` — confirm which branch the coordinator handoff/bootstrap code lives on before modifying it

## Session End Protocol

1. Run tests to verify clean state
2. Update progress.md with session summary
3. For implementation tasks, run `assignment closeout discord-nexus --task-id p9-0a2b-event-task-plan-operator-cli --reviewer <reviewer>`; do not mark your own implementation done
4. Commit only task-relevant changes — do not commit secrets, local config, or generated noise
5. Your final visible Discord message MUST include exactly one parseable `[agent-report]` block with `action=done`; natural-language completion alone is not enough for the operator
6. Report: what changed, test results, remaining risks, files modified

## Constraints

- Human gate: no merge without explicit approval
- No deploy without approval
- No out-of-scope changes without asking
- If stuck 3+ attempts on the same issue: stop and report blocker via coordinator CLI
