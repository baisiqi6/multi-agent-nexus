# Review Feedback: Phase 4 Coordinator Integration

Reviewer: reviewer-codex
Coordinator event: `plan.rejected` `cd73f54a-da81-47e7-ae5a-346046cf7b02`
Scope: `implementation plan`
Decision: rejected

## Summary

The Phase 4 direction is sound: add a coordinator-side Discord webhook delivery bus for visible status broadcasts, and teach managed coding agents how to use coordinator CLI for task state. However, the implementation plan needs revision before worker implementation because it currently has secret-handling and command-usability issues.

## Required Changes

### 1. Do not store Discord webhook URLs in coordinator workspace config

The plan says to run `workspace add discord-nexus --default-bus discord_webhook --default-destination <url>`.

That stores the webhook URL in coordinator SQLite and may expose it through `workspace list`, delivery rows, logs, debug output, or copied handoff text. A Discord webhook URL is a bearer secret and must not be stored as a destination.

Use a non-secret label instead, for example:

```bash
--default-bus discord_webhook --default-destination discord-nexus-status
```

The real webhook URL must only come from the environment variable:

```bash
DISCORD_WEBHOOK_URL=...
```

`WebhookBus.send()` can continue to ignore `destination`, since the webhook URL already binds the channel.

### 2. Fix coordinator CLI examples in system prompt

The plan's system prompt examples omit the required `workspace_id` positional argument.

Incorrect:

```text
assignment accept --task-id <id> --owner <agent> --session <sid>
branch allocate --task-id <id> --owner <agent>
pr link --task-id <id> --pr-url <url>
```

Correct:

```text
assignment accept discord-nexus --task-id <id> --owner <agent> --session <sid>
branch allocate discord-nexus --task-id <id> --owner <agent>
pr link discord-nexus --task-id <id> --pr-url <url>
ci check discord-nexus --task-id <id>
merge gate discord-nexus --task-id <id>
assignment closeout discord-nexus --task-id <id> --reviewer <name>
assignment mark-done discord-nexus --task-id <id>
```

Agents should be able to copy the examples directly without rediscovering CLI argument order.

### 3. Do not tell ordinary agents to use harnessctl for state changes

The plan currently says state changes can go through coordinator CLI or harnessctl. That conflicts with the coordinator/harness boundary.

Required wording:

```text
Default rule: use coordinator CLI for task lifecycle state. Do not edit harness JSON directly. Do not call harnessctl unless a human/operator explicitly asks you to repair or maintain the harness runtime.
```

Harnessctl is a lower-level repair/maintenance interface. Ordinary coding agents should not bypass coordinator when accepting tasks, handing off, raising blockers, linking PRs, checking CI, or closing out.

### 4. Update a tracked template or documentation file, not only local agents.toml

`agents.toml` is local and ignored by git. It can be updated for the operator's machine, but that alone is not reviewable or reproducible.

The plan should also update one tracked source of truth, such as:

- `agents.toml.example`
- `docs/agents.md`
- `docs/project-harness/runbook.md`

That tracked file should contain the coordinator system prompt snippet or a clear reference to it.

## Non-Blocking Notes

- `WebhookBus` design is otherwise reasonable: `DISCORD_WEBHOOK_URL`, `?wait=true`, `username="coordinator"`, and `allowed_mentions={"parse":[]}` are the right defaults.
- `discord_webhook` should be a status broadcast path, not an agent-trigger path. Do not send `[handoff] @Bot` messages through this bus in Phase 4.1-4.4.
- Add tests for destination being ignored without leaking the destination into the outgoing HTTP request body.

## Re-Review Criteria

Before requesting another review:

1. Update `plan.md` and `review-handoff.md` to reflect the required changes above.
2. Ensure examples include `discord-nexus` as workspace id.
3. Ensure no webhook URL appears in tracked files or coordinator workspace examples.
4. If `agents.toml` is changed locally, also update a tracked template/doc.
5. Ask reviewer to approve the implementation plan again through coordinator.
