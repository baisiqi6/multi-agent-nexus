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

## Harness Operations

```bash
# Validate checklist schema
bash scripts/harness/harnessctl validate

# Run full diagnostic
bash scripts/harness/harnessctl doctor

# Regenerate harness-state.json
bash scripts/harness/harnessctl state
```

## Coordinator Operations

```bash
MAC_SH=~/projects/multi-agent-coordinator/skills/multi-agent-coordinator-operator/scripts/mac.sh
DB=~/.multi-agent-coordinator/coordinator.sqlite3

# Sync coordinator with harness state
$MAC_SH --db $DB reconcile discord-nexus

# Check for drifts
$MAC_SH --db $DB workspace audit discord-nexus

# View current state
$MAC_SH --db $DB state discord-nexus
```

## Troubleshooting

**Agent won't start**: Check `logs/<agent>.err.log` for import errors or missing env vars. Verify token in `.env` matches `token_env` in `agents.toml`.

**Dual process conflict**: `start.sh` refuses if a manual process exists. Run `scripts/stop.sh` first, or kill the manual process: `pgrep -f "nexus.py.*--agent <id>"`.

**Session stuck**: Use `/session reset` or `session reset` text command in Discord to mark the session stale.

**Harness drift**: Run `$MAC_SH reconcile discord-nexus` then `$MAC_SH workspace audit discord-nexus`.
