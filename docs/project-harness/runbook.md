# Runbook

## Process Management (macOS)

### Start Agents

```bash
scripts/start.sh                # All managed agents
scripts/start.sh mac-claude     # Single agent
```

Pre-flight checks: verifies `agents.toml` and `.env` exist, detects conflicting manual processes, bootout + re-bootstrap if already loaded.

### Stop Agents

```bash
scripts/stop.sh                 # All
scripts/stop.sh mac-codex       # Single
```

### Check Status

```bash
scripts/status.sh               # All: loaded/PID/exit status/log paths
scripts/status.sh mac-opencode  # Single
```

### Uninstall

```bash
scripts/uninstall.sh            # Stop + remove plist from ~/Library/LaunchAgents/
scripts/uninstall.sh mac-codex  # Single
```

## Managed Agents

| ID | Adapter | launchd label |
|----|---------|---------------|
| mac-claude | claude | com.discord-nexus.mac-claude |
| mac-codex | codex | com.discord-nexus.mac-codex |
| mac-opencode | opencode | com.discord-nexus.mac-opencode |

All plists: RunAtLoad=true, KeepAlive=true, ThrottleInterval=30.

## Log Locations

| What | Path |
|------|------|
| Agent stdout | `logs/<agent>.log` |
| Agent stderr | `logs/<agent>.err.log` |
| Context + Sessions DB | `data/discord_context.sqlite3` |
| Harness state | `docs/project-harness/harness-state.json` |
| Harness events | `docs/project-harness/events.jsonl` |

## In-Discord Commands

| Command | Slash | Description |
|---------|-------|-------------|
| `session status` | `/session status` | Show active session for current scope |
| `session reset` | `/session reset` | Mark session stale, next call starts fresh |
| `agents` | `/agents` | List managed and external agents |
| `health` | `/health` | Check adapter binary availability |

All gated by `allowed_user_ids` from `agents.toml`.

Session status output includes the current scope type:

- `channel scope`: regular channel messages, stored as `channel:<channel_id>`.
- `thread scope`: Discord thread messages, stored as `thread:<thread_id>`.
- `task scope`: coordinator handoffs, stored as `task:<workspace_id>:<task_id>`.
- `legacy channel scope`: pre-Phase 5.2 numeric scope retained only for compatibility.

## Harness Operations

```bash
# Validate checklist schema
bash scripts/harness/harnessctl validate

# Run full diagnostic
bash scripts/harness/harnessctl doctor

# Regenerate harness-state.json (operator/repair only)
bash scripts/harness/harnessctl state
```

Ordinary worker agents should not use `harnessctl` for lifecycle transitions and should never edit harness JSON directly. Task state changes go through the coordinator CLI, which calls harnessctl through its mutation service.

## Coordinator Operations

```bash
MAC_SH=~/projects/multi-agent-coordinator/skills/multi-agent-coordinator-operator/scripts/mac.sh
export MAC_DB=~/projects/multi-agent-coordinator/data/coordinator.sqlite3

# Sync coordinator with harness state
$MAC_SH reconcile discord-nexus

# Check for drifts
$MAC_SH workspace audit discord-nexus

# View current state
$MAC_SH state discord-nexus

# Generate a worker bootstrap and targeted agent handoff
$MAC_SH task handoff discord-nexus --task-id <task-id> --role worker --target-agent mac-codex --write-bootstrap

# Sync agent registry from agents.toml before targeted handoff
$MAC_SH workspace agent sync discord-nexus --source ~/projects/discord-nexus/agents.toml

# Sync and replace entire registry (removes agents not in TOML)
$MAC_SH workspace agent sync discord-nexus --source ~/projects/discord-nexus/agents.toml --replace

# Create visible deliveries for supported events
$MAC_SH policy pump-events --workspace-id discord-nexus --platform discord_webhook --destination discord-nexus-status

# Send queued Discord deliveries when not using the daemon
DISCORD_WEBHOOK_URL=<webhook-url> $MAC_SH delivery pump --platform discord_webhook

# Run the coordinator Discord bot daemon
COORDINATOR_BOT_TOKEN=<token> COORDINATOR_CHANNEL_ID=<channel-id> \
  COORDINATOR_ALLOWED_USER_IDS=<user-id> $MAC_SH serve
```

The daemon can also be mentioned in Discord for `status`, `task list`, `task show <workspace> <task-id>`, `handoff <workspace> <task-id> <agent>`, and `pump`. Handoff deliveries mention only the target bot; status deliveries do not trigger managed agents.

## Troubleshooting

**Agent won't start**: Check `logs/<agent>.err.log` for import errors or missing env vars. Verify token in `.env` matches `token_env` in `agents.toml`.

**Dual process conflict**: `start.sh` refuses if a manual process exists. Run `scripts/stop.sh` first, or kill the manual process: `pgrep -f "nexus.py.*--agent <id>"`.

**Session stuck**: Use `/session reset` or `session reset` text command in Discord to mark the session stale.

**Task session contamination**:

1. In Discord, run `/session status` in the current channel/thread and confirm whether the scope type is `channel scope`, `thread scope`, or `task scope`.
2. Inspect `data/discord_context.sqlite3` if needed:

```bash
sqlite3 data/discord_context.sqlite3 \
  "SELECT scope_id, agent_id, session_id, status, turn_count, datetime(updated_at, 'unixepoch') FROM sessions ORDER BY updated_at DESC LIMIT 20;"
```

3. Coordinator handoffs should use `task:<workspace_id>:<task_id>`. If two coordinator tasks share one session, check for legacy numeric scopes and stale them with `/session reset` from the affected visible scope.
4. After coordinator `assignment.closeout`, `assignment.mark-done`, or `task.done` notices, the matching local task session should become `archived`; archived sessions are not resumed.

**Harness drift**: Run `$MAC_SH reconcile discord-nexus` then `$MAC_SH workspace audit discord-nexus`.

## New Workspace Onboarding

To connect a new workspace to the coordinator harness:

### 1. Register workspace

```bash
$MAC_SH workspace add <workspace-id> \
  --path /path/to/project \
  --harness-root docs/project-harness \
  --base-branch main \
  --branch-namespace agents
```

### 2. Diagnose current state

```bash
$MAC_SH workspace doctor <workspace-id>
```

This shows whether the workspace has `none`, `minimal_file_backed`, or `full_harness_runtime` capability. A fresh workspace will show `none`.

### 3. Initialize full harness runtime

```bash
# From an existing reference workspace (e.g. discord-nexus)
$MAC_SH workspace init-harness <workspace-id> \
  --mode full \
  --source /path/to/discord-nexus/scripts/harness

# Dry-run first to see what would be created
$MAC_SH workspace init-harness <workspace-id> \
  --mode full \
  --source /path/to/discord-nexus/scripts/harness \
  --dry-run
```

This copies `scripts/harness/` runtime from the source and creates protocol files (`scope.md`, `architecture.md`, `domain-model.md`, `runbook.md`) under the harness root. Existing files are never overwritten.

### 4. Verify full harness status

```bash
$MAC_SH workspace doctor <workspace-id>
```

Should now report `full_harness_runtime` with `harnessctl_available: true`.

### 5. Create and assign first task

```bash
# Write plan to docs/project-harness/tasks/<task-id>/plan.md
$MAC_SH task create <workspace-id> \
  --task-id <task-id> \
  --plan-doc docs/project-harness/tasks/<task-id>/plan.md \
  --title "Task title"

# Generate worker bootstrap and targeted agent handoff
$MAC_SH task handoff <workspace-id> \
  --task-id <task-id> \
  --role worker \
  --target-agent mac-claude \
  --write-bootstrap
```

### 6. Verify no drift

```bash
$MAC_SH workspace audit <workspace-id>
```

### Minimal init (alternative)

If you only need file-backed state without harnessctl runtime:

```bash
$MAC_SH workspace init-harness <workspace-id> \
  --mode minimal \
  --root docs/project-harness \
  --task-id <task-id> \
  --plan-doc docs/project-harness/tasks/<task-id>/plan.md
```

This creates a minimal harness structure but cannot support mutation lifecycle (assignment accept, handoff, closeout, mark-done).
