# Phase 5 Hardening Roadmap

## Context

Phase 4 proved that coordinator can drive a real Discord task flow:

1. coordinator bot sends a targeted handoff.
2. discord-nexus managed agent auto-accepts the assignment.
3. the agent reads task-scoped `worker-bootstrap.md`.
4. the agent reports back through structured `[agent-report]` messages.
5. coordinator records events, pumps visible Discord updates, and mirrors harness state.

The next work should harden this path before adding broader platform/deployment features.

## Goal

Make the coordinator + discord-nexus collaboration loop reliable enough for long-running multi-agent engineering work.

Prioritize the runtime path that is already in use:

- coordinator targeted handoff
- managed agent auto-accept
- task-scoped bootstrap and session state
- structured progress/blocker/done/review reports
- operator observability and new-project onboarding

## Execution Model

Default execution model for these phases:

- Worker implementation can be delegated to a coding agent such as Claude Code.
- Codex/operator reviews plans, diffs, tests, and protocol boundaries before accepting.
- Each phase should be a small, separately reviewable slice.
- Do not merge, deploy, or start long-running services without explicit human approval.
- Do not edit harness JSON directly. Use coordinator or harnessctl only through the appropriate service/tooling path.
- Keep protocol tokens stable: `[handoff]`, `[agent-report]`, `workspace_id=`, `task_id=`, `action=...`, `bootstrap=...`.

## Phase 5.1: Handoff Runtime Hardening And Agent-Report Protocol

### Objective

Make the existing coordinator handoff runtime path testable and documented.

### Scope

`discord-nexus`:

- Add runtime unit tests around `DiscordClient._try_coordinator_handoff`.
- Verify accept failure sends `[agent-report] action=blocker` and does not call the adapter.
- Verify accept success sends an accept report, reads bootstrap, and calls the adapter with bootstrap prompt.
- Verify missing bootstrap still calls the adapter with the explicit missing-bootstrap prompt.
- Assert report sends use `AllowedMentions.none()`.
- Keep auto-action scope limited to `assignment.accept`.

`multi-agent-coordinator`:

- Document accepted `[agent-report]` formats.
- Verify daemon ingest for `progress`, `blocker`, `done`, and review-related reports where supported.
- Keep `progress.reported` visible but non-lifecycle-changing.

Docs:

- Add or update an agent-report protocol document.
- Document that runtime auto-accept has already happened before the worker prompt starts.
- Document when to use Discord report vs coordinator CLI.

### Non-Goals

- Do not auto-run `mark-done`, `closeout`, merge, deploy, or PR operations from Discord text.
- Do not change session persistence design.
- Do not change plan gate or merge gate semantics.
- Do not add new production dependencies.

### Acceptance

- `discord-nexus` tests cover handoff success/failure/missing-bootstrap runtime behavior.
- `multi-agent-coordinator` tests cover supported report ingestion and visible progress rendering.
- Agent-report format is documented in tracked docs.
- Full tests pass in both repos.

## Phase 5.2: Task-Scoped Session Lifecycle

### Objective

Prevent long-running task sessions from growing indefinitely or leaking context across completed tasks.

### Scope

`discord-nexus`:

- Define task scope rules:
  - channel/thread scope remains useful for normal chat.
  - coordinator handoff should prefer task scope when `workspace_id` + `task_id` are present.
  - task-scoped sessions are archived/staled when task reaches closeout/done.
- Add task-scoped session status/reset support where practical.
- Update session status output to distinguish channel/thread scope vs task scope.
- Add tests for task closeout/done session archive/stale behavior.

`multi-agent-coordinator`:

- Ensure task lifecycle events are observable enough for discord-nexus to know when to stale/archive sessions.
- Prefer explicit event-driven behavior over polling when possible.

Docs:

- Update `docs/agent-session-persistence-design.md`.
- Document when task scope, thread scope, and channel scope are used.

### Non-Goals

- Do not delete CLI-native session history from Claude/Codex/OpenCode.
- Do not change adapter resume flags unless a bug is found.
- Do not introduce a remote session service.

### Acceptance

- Closing/done task sessions no longer get reused accidentally.
- Operator can inspect/reset task-scoped sessions.
- Existing channel/thread session behavior remains compatible.
- Tests cover stale/archive behavior.

## Phase 5.3: Agent Registry Auto-Sync

### Objective

Reduce drift between discord-nexus `agents.toml` / `external_agents` and coordinator workspace agent registry.

### Scope

`multi-agent-coordinator`:

- Add a command or service to sync workspace agent registry from a discord-nexus TOML file.
- Preserve manual overrides unless explicitly replaced.
- Validate missing/duplicate `discord_user_id` values.
- Report what changed without printing tokens or ignored config secrets.

`discord-nexus`:

- Ensure `agents.toml.example` documents the fields needed for coordinator sync.
- Avoid committing real `agents.toml`.

Docs:

- Add runbook steps for syncing registry before targeted handoff tests.

### Non-Goals

- Do not require coordinator to import discord-nexus runtime modules.
- Do not store Discord bot tokens in coordinator DB.
- Do not auto-sync continuously in the background for this phase.

### Acceptance

- One command can sync managed and external agent IDs into coordinator.
- Handoff fails closed if a target agent is not registered.
- Tests cover add/update/no-op and invalid config cases.

## Phase 5.4: Workspace Doctor And Full Harness Init

### Objective

Make new project onboarding less error-prone.

### Scope

`multi-agent-coordinator`:

- Improve `workspace add` or `workspace doctor` output to show:
  - harness root exists
  - `harnessctl` exists and is executable
  - checklist/state files are valid
  - mutation lifecycle is available
  - default bus/destination is configured
- Add a full harness initialization path that can instantiate `scripts/harness/` runtime from the known harness template.
- Keep the existing minimal file-backed harness path as a fallback.

Docs:

- Update coordinator operator docs and discord-nexus runbook with the recommended onboarding sequence.

### Non-Goals

- Do not silently rewrite existing harness state.
- Do not hide validation failures behind green status.
- Do not require Discord config for non-Discord workspaces.

### Acceptance

- A new workspace can be initialized and diagnosed without hand-copying harness runtime files.
- Doctor output makes missing capabilities obvious.
- Tests cover missing harnessctl, invalid checklist, and healthy workspace.

## Maintenance Sweep

These are valuable small slices to run between major Phase 5 work:

### SQLite ResourceWarning Cleanup

- Fix unclosed sqlite connection warnings in the coordinator full test suite.
- Keep this as a separate small commit.
- Acceptance: full tests pass without ResourceWarning noise.

### Operator Backlog Triage

- Review `/Users/yinxin/projects/multi-agent-coordinator/docs/operator-needs-backlog.md`.
- Mark entries as `done`, `partial`, `superseded`, or `open`.
- Link completed entries to commits or docs when known.

### Documentation Sync

- Update stale docs that still describe coordinator integration as future work.
- Especially review:
  - `docs/discord-multibot-plan/multi-bot-refactor-plan.md`
  - `docs/multi-agent-harness-overview.md`
  - `docs/project-harness/runbook.md`
  - coordinator operator skill docs if workflow changed

## Deferred Until Needed

These are real needs, but should wait until the core loop is stable:

- systemd cloud deployment
- Windows service/startup scripts
- logs rotation and richer status scripts
- long-running coordinator job worker

## Suggested Order

1. Phase 5.1: Handoff Runtime Hardening And Agent-Report Protocol
2. Maintenance: SQLite ResourceWarning cleanup
3. Phase 5.2: Task-Scoped Session Lifecycle
4. Maintenance: Operator backlog triage
5. Phase 5.3: Agent Registry Auto-Sync
6. Maintenance: Documentation sync
7. Phase 5.4: Workspace Doctor And Full Harness Init
8. Re-evaluate systemd / Windows / long-running job worker

## Review Gates

Each phase should have:

- plan review before worker implementation
- code review after implementation
- full relevant tests
- no secrets in diff
- no direct harness JSON mutation unless explicitly scoped as harness maintenance
- Discord runtime behavior validated manually only when the user approves live testing

