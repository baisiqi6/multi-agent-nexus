# Phase 3.3 Runtime Launchd Task

Canonical plan: `docs/discord-multibot-plan/phase3.3-runtime-launchd-plan.md`

Do not copy the plan body into this task file. The source plan remains the authority for scope, non-goals, implementation steps, risks, validation, and acceptance criteria.

## Scope

- Implement user-level launchd persistence for `mac-claude`, `mac-codex`, and `mac-opencode`.
- Add the launchd plist templates and start/stop/status/uninstall scripts described by the source plan.
- Keep tokens, `.env`, `agents.toml`, and real webhook URLs out of committed files and command output.

## Non-Goals

- No multinexus coordinator integration in this phase.
- No `/task` commands.
- No Hermes or OpenClaw launchd work.
- No handoff protocol, session persistence schema, or slash command behavior changes.
- No merge or deploy without human approval.

## Acceptance

Use `docs/discord-multibot-plan/phase3.3-runtime-launchd-plan.md#验收标准`.

## Expected Validation

```bash
plutil -lint launchd/*.plist
bash -n scripts/*.sh scripts/lib/*.sh
.venv/bin/python -m unittest discover tests/
```

Manual launchd and Discord checks are also required by the source plan before final human approval.
