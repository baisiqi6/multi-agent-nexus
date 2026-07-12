# Worker Bootstrap: slice-4b2-deployed-agent-registry-authority

## Session Startup

### Step 1: Confirm working directory

```bash
pwd
```

You should be at
`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-s4b2-kimi`.
If not, stop and report the actual directory; do not switch the canonical checkout.

### Step 2: Check workspace state (read-only)

```bash
git status --short
git branch --show-current
git log --oneline -10
```

Rule: do not overwrite/revert changes that are not yours. If you find unrelated dirty files, log them but do not clean up.

Worktree guard: if `pwd` is not
`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-s4b2-kimi` or
`git branch --show-current` is not
`agents/mac-omp/slice-4b2-deployed-agent-registry-authority`, stop and report a blocker
instead of switching branches.
Never run `git reset`, `git rebase`, `git checkout`, `git switch`, `git cherry-pick`, or `git push --force` to repair this workspace unless the operator explicitly asks you to.

### Step 3: Read project state

Read these files from the current worktree:
- `docs/project-harness/harness-state.json` — current_item, checklist_summary, recent_events
- `docs/project-harness/progress.md` — recent session logs

### Step 4: Read project boundaries

- `docs/project-harness/scope.md` — goals, non-goals, constraints
- `docs/project-harness/architecture.md` — module boundaries
- `docs/project-harness/domain-model.md` — core entities

### Step 5: Read assigned task plan

```bash
cat docs/project-harness/tasks/slice-4b2-deployed-agent-registry-authority/plan.md
```

Follow this plan step by step.

## Your Assignment

- **Task**: slice-4b2-deployed-agent-registry-authority
- **Title**: Slice 4B2 Deployed Agent Registry Authority
- **Branch**: agents/mac-omp/slice-4b2-deployed-agent-registry-authority
- **Plan**: docs/project-harness/tasks/slice-4b2-deployed-agent-registry-authority/plan.md
- **Phase**: approved
- **Approved plan SHA-256**: `b9cd5c80b8d84c3e011863a7f2b526ab72c2ec083d664c46b76ad00345299811`
- **Coordinate approval event**: `7485d430-0c7b-43da-9fd1-ba69655627f7`
- **Implementation model**: `kimi-for-coding-highspeed`; GLM fallback is permitted
  only when the Codex operator records a Kimi quota/auth/provider failure. Do not
  silently switch provider or model.

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

Additional required checks from the independent reviewer:

- strict committed-state parity must fail when an active override changes the
  effective roster; and
- a focused fixture must prove MultiNexus canonical SHA-256 is byte-for-byte identical
  to Coordinate v10's canonical contract.

Implement only the approved allowed paths. Do not edit Coordinate production code,
real `agents.toml`, `.env`, provider configuration, tokens or production state.

## Visible Discord Updates

You, the worker agent, own execution updates in Discord. The coordinator should stay as the control plane; do not rely on coordinator event echoes as the human-readable collaboration thread.

Send concise human-readable updates in the channel at these points:
- **Start**: say you accepted `slice-4b2-deployed-agent-registry-authority` and list the 2-3 concrete steps you will do first.
- **Milestone**: when a meaningful sub-step is complete, summarize what changed, tests run, and next step.
- **Blocker**: if you need operator/reviewer input, mention `@Coordinator`, `@Codex`, or the assigned reviewer/operator if visible in the channel.
- **Done / review needed**: mention `@Coordinator` and `@Codex` (or the assigned reviewer) with changed files, tests, risks, and review request.

Keep each visible update short. Do not stream private reasoning or every command.
Each progress/blocker/done update should end with one machine-readable block so coordinator can ingest it:

```text
[agent-report]
action=progress
workspace_id=discord-nexus
task_id=slice-4b2-deployed-agent-registry-authority
summary="Completed <milestone>; tests: <result>; next: <next step>"

[agent-report]
action=blocker
workspace_id=discord-nexus
task_id=slice-4b2-deployed-agent-registry-authority
reason="Need <decision/input>"

[agent-report]
action=done
workspace_id=discord-nexus
task_id=slice-4b2-deployed-agent-registry-authority
summary="Implemented <scope>; tests: <result>; risks: <risk-or-none>"
```

Use exactly one report block per visible update. The `[agent-report]` marker must start at the beginning of its own line.

## Self-Test Before Closeout

**Package override**: the worker performs local and isolated tests only. Codex is the
result reviewer/operator and owns push, SSH, production DB backup/sync, service actions,
server sidecar and live smoke after accepting the implementation. Do not deploy from
this worker session and do not access production.

### When deploy is required

- Run focused parity/deploy/smoke contract tests and the full MultiNexus suite.
- Run focused Coordinate B1 registry/daemon tests read-only against the existing
  Coordinate checkout if the environment supports them.
- Run `git diff --check` and report the exact commit SHA.

### Deploy + e2e smoke

Do not run `scripts/deploy-server.sh`, `ssh`, production `coord-local`, service-manager
commands or any command against `/var/lib/coordinate/coord.sqlite3`.

### Self-test evidence

Report local self-test evidence to Codex; do not call closeout yourself:

Include focused/full test counts, diff check, commit SHA, changed paths, and any
remaining risk. Codex will perform the formal closeout transition after result review
and production evidence.

### Cross-repo coordination

If this task spans multiple repositories, verify the correct branch in each:
- Primary: `/Users/yinxin/projects/multinexus` branch `agents/mac-omp/slice-4b2-deployed-agent-registry-authority`
- Coordinate (if applicable): `~/projects/coordinate` — confirm which branch the coordinator handoff/bootstrap code lives on before modifying it

## Session End Protocol

1. Run tests to verify clean state
2. Update progress.md with session summary
3. Do not run `assignment closeout` or mark the task done; return the committed branch
   to Codex for review
4. Commit only task-relevant changes — do not commit secrets, local config, or generated noise
5. Your final visible Discord message MUST include exactly one parseable `[agent-report]` block with `action=done`; natural-language completion alone is not enough for the operator
6. Report: what changed, test results, remaining risks, files modified

## Constraints

- Human gate: no merge without explicit approval
- No deploy without approval
- No out-of-scope changes without asking
- If stuck 3+ attempts on the same issue: stop and report blocker via coordinator CLI
