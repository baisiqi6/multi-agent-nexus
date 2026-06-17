# Phase 8.3.1: Harness Source Boundary and Sidecar Workspace Rules

## Objective

Codify and verify the source-of-truth boundary for harness files across internal
projects and external/upstream projects.

Phase 8.3 introduced host-aware materialization:

- `issue materialize-files` runs on a coding host and writes harness files.
- `issue materialize-record` runs through the remote coordinate DB and writes
  control-plane events only.
- Server `/opt/*` deployment copies are runtime derivatives, not source
  checkouts.

This task turns that decision into documented, tested, worker-facing rules.

## Source-Of-Truth Rules

Internal/managed repos:

- Harness files live inside the repo.
- Example: `/Users/yinxin/projects/multinexus/docs/project-harness`.
- Harness files are committed and versioned with the repo.

External/upstream repos:

- Harness files live in a sidecar workspace outside the target repo.
- Example:
  - code checkout: `/Users/yinxin/projects/opencode`
  - harness root: `/Users/yinxin/projects/harness-workspaces/opencode`
- PRs to upstream projects must not include our harness files.

Coordinate model:

- `workspace.path` is the code checkout path.
- `workspace.harness_root` is the harness state path.
- These paths may be the same repo tree for internal projects, or separate
  directories for external projects.

## Scope

Implement the smallest useful hardening/documentation slice:

1. Document the internal-vs-external harness placement rule in coordinate docs
   and multinexus dogfood/progress docs.
2. Add or update tests proving `issue materialize-files` supports a sidecar
   `harness_root` outside `workspace.path`.
3. Inspect worker bootstrap text and tests to confirm it treats code repo path
   and harness root as separate values. If it already does, document that
   evidence; if not, fix it.
4. Make sure no workflow implies server `/opt/multinexus` is the harness
   source of truth.

## Non-Goals

- Do not implement operator bot automation.
- Do not implement PR/CI/review automation.
- Do not deploy to the server.
- Do not modify tokens, `agents.toml`, systemd, launchd, mihomo, or live service
  configuration.
- Do not create a real external `opencode` checkout unless needed for a local
  smoke; prefer temp directories in tests.

## Acceptance Criteria

- Documentation explicitly states:
  - internal repos keep harness in repo and commit it;
  - external/upstream repos use sidecar harness outside the target repo;
  - `workspace.path` and `workspace.harness_root` are intentionally separate
    concepts;
  - server `/opt/*` copies are deploy artifacts and must not be used as harness
    source of truth.
- Tests cover sidecar materialization:
  - code checkout path and harness root are different directories;
  - `materialize-files` writes the sidecar checklist;
  - the target code checkout remains free of harness files.
- Worker bootstrap / handoff guidance clearly exposes both code checkout and
  harness root to the worker.
- Existing Phase 8.3 host-aware materialization tests still pass.
- Full relevant suites pass:
  - coordinate targeted issue/handoff tests.
  - coordinate full discover if practical.
  - multinexus full discover if multinexus files changed.

## Suggested Files To Inspect

Coordinate:

- `/Users/yinxin/projects/coordinate/src/coordinate/issues.py`
- `/Users/yinxin/projects/coordinate/src/coordinate/handoff.py`
- `/Users/yinxin/projects/coordinate/tests/test_issues.py`
- `/Users/yinxin/projects/coordinate/tests/test_handoff.py`
- `/Users/yinxin/projects/coordinate/docs/progress.md`
- `/Users/yinxin/projects/coordinate/docs/runbook.md`
- `/Users/yinxin/projects/coordinate/docs/coordinator-architecture.md`

MultiNexus:

- `/Users/yinxin/projects/multinexus/docs/project-harness/dogfood-feedback.md`
- `/Users/yinxin/projects/multinexus/docs/project-harness/progress.md`
- `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/phase-8.3.1-harness-source-boundary/plan.md`

## Worker Instructions

- Work on branch `agents/mac-claude/phase-8-preflight-dogfood-cleanup`.
- Keep changes narrow and source-of-truth focused.
- If a path or command is host-specific, use the current host profile rather
  than hard-coding server `/opt` paths.
- Do not hand off to another worker unless blocked.
- Report any dogfood issue encountered, especially if Discord, coordinate, or
  bootstrap paths still imply `/opt` is the development source.
