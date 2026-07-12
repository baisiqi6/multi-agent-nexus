# Worker Bootstrap: slice-4c1-task-create-operation-contract

## Session Startup

### Step 1: Confirm working directory

```bash
pwd
```

You should be at
`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-s4c1-kimi`.
If not, stop; do not switch the canonical Coordinate checkout.

### Step 2: Check workspace state (read-only)

```bash
git status --short
git branch --show-current
git log --oneline -10
```

Rule: do not overwrite/revert changes that are not yours. If you find unrelated dirty files, log them but do not clean up.

Worktree guard: `pwd` must be
`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-s4c1-kimi` and the branch
must be `agents/mac-omp/slice-4c1-task-create-operation-contract`. Otherwise stop.
Never run `git reset`, `git rebase`, `git checkout`, `git switch`, `git cherry-pick`, or `git push --force` to repair this workspace unless the operator explicitly asks you to.

### Step 3: Read project state

Read project state read-only from `/Users/yinxin/projects/multinexus/docs/project-harness/`.

### Step 4: Read project boundaries

- `/Users/yinxin/projects/multinexus/docs/project-harness/scope.md`
- `/Users/yinxin/projects/multinexus/docs/project-harness/architecture.md`
- `/Users/yinxin/projects/multinexus/docs/project-harness/domain-model.md`

### Step 5: Read assigned task plan

```bash
cat /Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4c1-task-create-operation-contract/plan.md
```

Follow this plan step by step.

## Your Assignment

- **Task**: slice-4c1-task-create-operation-contract
- **Title**: Slice 4C1 Task-Create Split Operation Contract
- **Branch**: agents/mac-omp/slice-4c1-task-create-operation-contract
- **Plan**: docs/project-harness/tasks/slice-4c1-task-create-operation-contract/plan.md
- **Phase**: approved
- **Primary implementation repo**: Coordinate only.
- **Approved plan SHA-256**: `e83024a5a125994bd5eee0c9de332d19d939cbf485da3e877c26aa5ba3e8b765`.
- **Approval event**: `1f07da08-3ed9-4576-9b46-10f5ee867c3e`.
- **Model**: `kimi-for-coding-highspeed`; stop on quota/auth/provider failure and let
  Codex record any GLM fallback. Never switch silently.

## Coordinator CLI

All state changes MUST go through coordinator CLI.
Do NOT call harnessctl directly.
Do NOT modify harness JSON files directly.
harnessctl is only for operator/harness repair.

```bash
# coordinator DB is configured by host profile: /Users/yinxin/projects/coordinate/data/coordinator.sqlite3
/Users/yinxin/projects/coordinate/skills/coordinate-operator/scripts/mac.sh <command> discord-nexus [options]
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

Do not edit MultiNexus or harness lifecycle files. Implement only the approved
Coordinate paths. The cross-platform lock is a hard stop condition: if exclusive
creation, bounded wait and live/stale-owner evidence cannot be made safe and tested,
report a blocker instead of shipping an unlocked read/replace.

## Visible Discord Updates

You, the worker agent, own execution updates in Discord. The coordinator should stay as the control plane; do not rely on coordinator event echoes as the human-readable collaboration thread.

Send concise human-readable updates in the channel at these points:
- **Start**: say you accepted `slice-4c1-task-create-operation-contract` and list the 2-3 concrete steps you will do first.
- **Milestone**: when a meaningful sub-step is complete, summarize what changed, tests run, and next step.
- **Blocker**: if you need operator/reviewer input, mention `@Coordinator`, `@Codex`, or the assigned reviewer/operator if visible in the channel.
- **Done / review needed**: mention `@Coordinator` and `@Codex` (or the assigned reviewer) with changed files, tests, risks, and review request.

Keep each visible update short. Do not stream private reasoning or every command.
Each progress/blocker/done update should end with one machine-readable block so coordinator can ingest it:

```text
[agent-report]
action=progress
workspace_id=discord-nexus
task_id=slice-4c1-task-create-operation-contract
summary="Completed <milestone>; tests: <result>; next: <next step>"

[agent-report]
action=blocker
workspace_id=discord-nexus
task_id=slice-4c1-task-create-operation-contract
reason="Need <decision/input>"

[agent-report]
action=done
workspace_id=discord-nexus
task_id=slice-4c1-task-create-operation-contract
summary="Implemented <scope>; tests: <result>; risks: <risk-or-none>"
```

Use exactly one report block per visible update. The `[agent-report]` marker must start at the beginning of its own line.

## Self-Test Before Closeout

**Package override**: worker runs local tests only. Codex owns result review, integration,
production backup/deploy/schema migration and server dogfood. Do not SSH or deploy.

### When deploy is required

- Run focused split-operation/schema/CLI/contract/failure-injection tests.
- Run the full Coordinate suite, CLI fixture rewind proof, schema reopen/migration,
  `git diff --check`, and report exact counts/commit.

### Deploy + e2e smoke

Do not run deploy, SSH, service-manager or production DB commands.

### Self-test evidence

Return test evidence to Codex. Do not call closeout or mark-done yourself.

```bash
assignment closeout discord-nexus --task-id slice-4c1-task-create-operation-contract --reviewer <reviewer> \
  --self-test-evidence "Deploy SHA: <sha>; E2E: <result>; Bugs found: <list or none>"
```

**Empty `--self-test-evidence` → reviewer will see a warning. Do not skip this step.**

### Cross-repo coordination

If this task spans multiple repositories, verify the correct branch in each:
- Primary: `/Users/yinxin/projects/multinexus` branch `agents/mac-omp/slice-4c1-task-create-operation-contract`
- Coordinate (if applicable): `~/projects/coordinate` — confirm which branch the coordinator handoff/bootstrap code lives on before modifying it

## Session End Protocol

1. Run tests to verify clean state
2. Update progress.md with session summary
3. Do not call closeout/mark-done; return the committed Coordinate branch to Codex
4. Commit only task-relevant changes — do not commit secrets, local config, or generated noise
5. Your final visible Discord message MUST include exactly one parseable `[agent-report]` block with `action=done`; natural-language completion alone is not enough for the operator
6. Report: what changed, test results, remaining risks, files modified

## Constraints

- Human gate: no merge without explicit approval
- No deploy without approval
- No out-of-scope changes without asking
- If stuck 3+ attempts on the same issue: stop and report blocker via coordinator CLI
