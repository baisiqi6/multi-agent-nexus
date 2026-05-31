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
