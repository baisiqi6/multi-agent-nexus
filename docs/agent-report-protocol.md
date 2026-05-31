# Agent-Report Protocol

Structured progress reports emitted by discord-nexus managed agents during coordinator handoff execution.

## Format

All reports are single-line messages sent to Discord:

```
[agent-report] action=<action> workspace_id=<workspace> task_id=<task> [summary=<text>] [reason=<text>]
```

Fields:
- `action` — report type (required)
- `workspace_id` — coordinator workspace identifier (required, shell-quoted)
- `task_id` — task identifier (required, shell-quoted)
- `summary` — human-readable status (optional, shell-quoted)
- `reason` — error or blocker explanation (optional, shell-quoted)

## Supported Actions

| Action | When | Lifecycle effect |
|--------|------|-------------------|
| `accept` | Auto-accept succeeded | Marks assignment accepted |
| `progress` | Worker hits a milestone | Visible only, no lifecycle change |
| `blocker` | Worker cannot proceed | Logs blocker, may require operator |
| `done` | Worker finishes task | Triggers closeout review |

## Auto-Accept Behavior

When a coordinator handoff arrives:

1. `DiscordClient.on_message` detects `[handoff]` from the coordinator bot
2. `_try_coordinator_handoff` runs `assignment.accept` via coordinator CLI **before** the adapter starts
3. On accept success → sends `action=accept` report, reads bootstrap, calls adapter
4. On accept failure → sends `action=blocker` report, does **not** call adapter
5. Bootstrap missing → adapter is still called, prompt notes bootstrap is missing

The managed agent never runs `assignment.accept` a second time. The bootstrap prompt explicitly states that the accept already happened.

## Action Scope

Only `assignment.accept` is auto-executed by the runtime. Other lifecycle actions (`mark-done`, `closeout`, `merge`, `deploy`, `pr`) are rejected by `parse_coordinator_handoff` and must be initiated by the agent through the coordinator CLI.

## Report Delivery

All `[agent-report]` messages are sent with `AllowedMentions.none()` to avoid triggering other bots.

## When to Use Discord Report vs Coordinator CLI

| Scenario | Mechanism |
|----------|-----------|
| Auto-accept result | `[agent-report]` (automatic) |
| Milestone reached mid-task | `[agent-report] action=progress` (agent emits in output) |
| Blocked on external dependency | `[agent-report] action=blocker` (agent emits in output) |
| Task complete | `[agent-report] action=done` (agent emits in output) |
| Branch allocation | Coordinator CLI (`branch allocate`) |
| PR link | Coordinator CLI (`pr link`) |
| CI status | Coordinator CLI (`ci check`) |
| Closeout review | Coordinator CLI (`assignment closeout`) |
| Mark done | Coordinator CLI (`assignment mark-done`) |

Discord reports are for **visibility** — they appear in the task channel and are ingested by the coordinator daemon. Coordinator CLI commands are for **lifecycle mutations** — they change assignment state in the database.
