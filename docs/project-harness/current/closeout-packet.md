# Closeout Packet

## Subject

- Checklist item: `dogfood-doc-sync`
- Reviewer: `operator`
- Updated at: `2026-05-31`
- Canonical plan path: `docs/project-harness/tasks/dogfood-doc-sync/plan.md`

## Item Snapshot

- Title: Dogfood: sync coordinator integration docs
- Status: doing
- Workflow status: closeout_requested
- Priority: p1
- Owner: mac-codex
- Session: auto-mac-codex-1780240587
- Dependencies: None

## Acceptance

Use the plan acceptance criteria as source of truth: docs/project-harness/tasks/dogfood-doc-sync/plan.md

## Verification



## Handoff

{'from': None, 'to': None, 'reason': None}

## Review Inputs

- Scope: `docs/project-harness/scope.md`
- Architecture: `docs/project-harness/architecture.md`
- Domain model: `docs/project-harness/domain-model.md`
- Progress: `docs/project-harness/progress.md`
- Review output target: `docs/project-harness/current/review.md`

## Canonical Plan Content

```md
# Dogfood Task: Coordinator Integration Documentation Sync

## Context

Phase 4 coordinator integration is now implemented and closed, but some long-form planning docs still describe coordinator integration as future work or webhook-only. This task is intentionally small so the next worker can validate the coordinator-driven task lifecycle without risking runtime behavior.

## Goal

Update documentation so it reflects the current state:

- coordinator has a Discord bot daemon for visible delivery and command ingestion.
- coordinator can generate targeted agent handoff deliveries.
- discord-nexus can auto-accept coordinator handoffs for managed agents.
- harness state is managed through coordinator/harnessctl, not by direct JSON edits.

## Scope

Primary files to inspect:

- `docs/discord-multibot-plan/multi-bot-refactor-plan.md`
- `docs/multi-agent-collaboration.md`
- `docs/multi-agent-harness-overview.md`
- `docs/project-harness/runbook.md`
- `docs/project-harness/scope.md`

Update only documentation. Do not change runtime code, tokens, local config, launchd scripts, adapter behavior, or coordinator DB state.

## Non-Goals

- No code changes.
- No Discord bot restart.
- No live Discord message send.
- No schema changes.
- No rewrite of old historical acceptance docs unless they are actively misleading as current-state docs.

## Validation

Run:

```bash
git diff --check
scripts/harness/harnessctl validate
scripts/harness/harnessctl doctor
```

If documentation references commands, sanity-check command names against current source or `--help` output where practical.

## Done Criteria

- Stale “coordinator integration is future work” wording is either updated or clearly marked as historical.
- Current coordinator/discord-nexus boundary is documented consistently.
- No generated state noise remains in git status.
- Worker reports changed files, validation output, and any remaining documentation drift.
```

## Recent Progress Context

```md
### Manual validation

Human performed terminal and Discord validation:

- `scripts/start.sh mac-claude` → loaded, Gateway connected.
- `scripts/status.sh mac-claude` → pid visible.
- `scripts/stop.sh mac-claude` → stopped.
- `scripts/uninstall.sh mac-claude` → plist removed.
- `scripts/start.sh` (all 3) → mac-claude, mac-codex, mac-opencode all loaded.
- Discord health check → mac-codex responded with adapter/bin/available fields.

### Current status

- Task status: **done** — all static, terminal, and Discord validation passed.
- Human gate: **passed**.
- Ready for commit and merge at human's discretion.

## 2026-05-31

### Dogfood doc sync — coordinator integration docs

- Read harness state, progress, scope, architecture, domain model, and `dogfood-doc-sync` plan before editing.
- Confirmed the task already had an active coordinator lease for `mac-codex` / `auto-mac-codex-1780240587`; a duplicate `assignment accept` attempt through coordinator CLI failed because of that active lease.
- Updated current-state docs for Phase 4 coordinator integration:
  - `docs/discord-multibot-plan/multi-bot-refactor-plan.md`
  - `docs/multi-agent-harness-overview.md`
  - `docs/project-harness/runbook.md`
  - `docs/project-harness/scope.md`
- Synced wording around coordinator Discord daemon, targeted agent handoff delivery, discord-nexus coordinator handoff auto-accept, and the rule that task lifecycle state changes go through coordinator CLI rather than direct harness JSON edits.
- Sanity-checked documented coordinator commands against current `mac.sh --help` output.
- Validation: `git diff --check` passed; `scripts/harness/harnessctl validate` passed; `scripts/harness/harnessctl doctor` exited 0 with existing optional/current file misses (`current/task_plan.md`, `init.sh`).
```

## Current Review Content

```md

```

## Closeout Questions

1. 当前实现是否已经覆盖 acceptance
2. verification 是否足以支持从 `doing` 进入 `done`
3. 还有没有阻止 closeout 的高优先级问题
4. 如果不能 done，最关键的剩余工作是什么

