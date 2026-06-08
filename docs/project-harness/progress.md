# Project Harness Progress

Harness root: `docs/project-harness/`

## 2026-06-08

### Phase 7.1: 单机 N+M 运行架构 — blocker fix

- Fixed reviewer blocker: removed embedded `AgentDaemon` from both `DiscordClient` and `KookBridge`.
- Both bridges now connect to a standalone agentd via `AgentdClient` (HTTP client only).
- Created `multinexus/agentd/__main__.py`: standalone agentd launcher (`python -m multinexus.agentd --agent <id> --port <port>`).
- One agentd process per agent identity, shared by all bridges. Prevents duplicate adapter instances.
- `agentd_mode=true` now requires `agentd_port` to be set in config — fails fast if missing.
- `khl>=0.4.0` already in requirements.txt (reviewer finding was stale).
- Full suite 224/224 pass. 1 new commit.

### Phase 7.1: 单机 N+M 运行架构 — review blocker

- Reviewed `agents/mac-claude/phase-7.1-single-host-n-plus-m-runtime` after Claude's Discord completion report.
- Validation observed: `.venv/bin/python -m unittest discover tests/` passed 224 tests; `scripts/harness/harnessctl validate` passed after checklist repair; `git diff --check` passed.
- Blocker recorded through coordinate as `blocker.raised` event `3c28dada-bfa2-4d60-a04c-438673caae04`.
- Blocking findings:
  - The implementation starts an embedded `AgentDaemon` inside each bridge process. If Discord and KOOK bridges both run for the same agent, they can still create two adapter/agentd instances, so the acceptance goal "only one agentd per agent identity shared by all IM bridges" is not met.
  - The actual chain is `bridge -> local HTTP agentd -> adapter`; it bypasses the planned `bridge -> coordinate -> agentd` control-plane boundary for Phase 7.1 dogfood.
  - `multinexus.kook.bot` cannot import in the current environment because `khl` is not in `requirements.txt`; current tests cover KOOK mention parsing but not KOOK bridge startup/import.
- Also repaired missing Phase 7 checklist metadata: added `phase-7-n-plus-m-runtime`, `phase-7.1-single-host-n-plus-m-runtime`, and `phase-7.2-multi-host-agent-runtime` to `mvp-checklist.json` so future assignment/review/blocker transitions can be tracked.

### Phase 7.1: 单机 N+M 运行架构 — rework handoff

- Added reviewer feedback at `docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/review-feedback-2026-06-08-codex.md`.
- Unblocked the task through coordinate and re-handed it to `mac-claude` with `task handoff --target-agent mac-claude`.
- Confirmed agent-specific Discord handoff was sent with `<@1507329791982833775>` and bootstrap path `docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/worker-bootstrap.md`.
- `mac-claude` auto-accepted; checklist is now `status=doing`, `workflow.status=running`, owner `mac-claude`.
- Dogfood issue found during handoff: public `[HANDOFF]` status text triggered duplicate accept before the agent-specific `[handoff]` message. Fixed in coordinate by changing public handoff status rendering to `[HANDOFF_STATUS]` while keeping agent-specific protocol messages unchanged.

### Phase 7.1: 单机 N+M 运行架构 — implementation

- Created `multinexus/protocol.py`: platform-agnostic `AgentRequest`/`AgentResponse` envelope with `Platform` enum, `PlatformOrigin`/`PlatformDestination` for cross-platform routing. JSON serialization round-trip tested.
- Created `multinexus/agentd/server.py`: `AgentDaemon` HTTP server (aiohttp) that accepts `AgentRequest` via POST, processes through existing adapters, manages session lifecycle, returns `AgentResponse`. One agentd per agent identity. Includes health check endpoint.
- Created `multinexus/agentd/client.py`: `AgentdClient` HTTP client for bridges to submit requests to agentd.
- Modified `multinexus/client.py`: added bridge mode (`agentd_mode=true`). When enabled, `DiscordClient` no longer calls `make_adapter()` directly — it submits `AgentRequest` to local agentd. Legacy mode preserves existing behavior.
- Created `multinexus/kook/`: KOOK bridge module ported from kook-nexus.
  - `kook/bot.py`: `KookBridge` — WebSocket + HTTP polling, message dedup, transient filtering, handoff dedup. Submits to agentd in bridge mode.
  - `kook/mentions.py`: `KookMentionRouter` — KMarkdown `(met)ID(met)` / `(rol)ID(rol)` parsing, agent addressing, outbound mention conversion.
- Updated `multinexus/models.py`: added `agentd_mode`, `agentd_port`, `agentd_host`, `kook_poll_*` fields.
- Updated `multinexus/config.py`: parse new fields from TOML.
- Updated `docs/project-harness/architecture.md`, `domain-model.md`, `scope.md` for N+M architecture.
- 41 new tests: 10 protocol, 9 agentd HTTP, 21 KOOK mentions + 1 lazy import. Full suite 224/224 pass.
- 5 commits on `agents/mac-claude/phase-7.1-single-host-n-plus-m-runtime`.

## 2026-06-03

### Phase 6.1: omp Adapter 基础接入 — implementation

- Created `multinexus/adapters/omp.py`: `OmpAdapter(AgentAdapter)` with `call()`, `resume()`, `health_check()`.
  - Uses `omp -p --auto-approve` for non-interactive mode.
  - `resume()` passes `--resume <session_id>`.
  - Optional `--model` and `--thinking` flags via `omp_model` / `omp_thinking` config.
  - Simple subprocess communicate (no streaming), with timeout via `asyncio.wait_for`.
- Extended `multinexus/models.py`: added `omp_bin`, `omp_model`, `omp_thinking`, `omp_auto_approve` fields to `AgentConfig`.
- Updated `multinexus/config.py`: parse omp fields from TOML with `_first_existing_command` for `omp_bin`.
- Registered in `multinexus/adapters/factory.py`: `adapter == "omp"` → `OmpAdapter(config)`.
- Added mac-omp config block to `agents.toml` (local, gitignored) with `omp_model = "opus"`, `omp_thinking = "high"`.
- 16 new tests in `tests/test_omp_adapter.py`: CLI arg construction (auto-approve, model, thinking, resume), call/resume/failure/timeout/missing CLI/health check/factory.
- Full test suite: 183/183 pass (167 existing + 16 new).

### Phase 6.1: mac-omp Smoke Test — verification

- **omp CLI**: `omp/15.7.6` available at `/Users/yinxin/.bun/bin/omp`
- **Health check**: `{"adapter": "omp", "bin": "omp", "available": true, "path": "/Users/yinxin/.bun/bin/omp"}` — PASS
- **Real call**: `omp -p --auto-approve "Reply with exactly: OK smoke-test-passed"` returned "OK smoke-test-passed" — PASS
- **Unit tests**: 16/16 omp adapter tests pass; full suite 183/183 pass
- **plist**: `com.multinexus.mac-omp.plist` validated with `plutil -lint` — OK
- **Shell scripts**: `bash -n` all pass; `launchd.sh` AGENTS includes `mac-omp`
- **Known gap**: `session_id` is not captured from `omp -p` output (omp print mode does not output session IDs); resume support is limited without interactive mode
- All Phase 6.1 acceptance criteria met:
  1. OmpAdapter constructable via `make_adapter()` ✅
  2. `--auto-approve` in call/resume CLI args ✅
  3. `--resume <session_id>` passed correctly ✅
  4. Health check format correct ✅
  5. All omp adapter tests pass ✅
  6. No existing test regression (183/183) ✅

## 2026-06-01

### Phase 5.4: Workspace Doctor And Full Harness Init — implementation

- Created `src/multi_agent_coordinator/doctor.py`: workspace harness diagnostics module with `diagnose_workspace()` function. Produces a `DoctorReport` that checks workspace path, harness root, harnessctl availability/executability, required and optional file presence, checklist validity, harnessctl validate/doctor health, and distinguishes between `none`, `minimal_file_backed`, and `full_harness_runtime` modes.
- Added `workspace doctor <workspace_id>` CLI subcommand. Returns exit 0 for full_harness_runtime, 1 otherwise.
- Enhanced `init_file_harness()` in `onboarding.py` with `init_full_harness()`: copies `scripts/harness/` runtime from a `--source` directory, creates protocol file stubs (scope.md, architecture.md, domain-model.md, runbook.md), ensures minimal harness files exist. Supports `--dry-run`, never overwrites existing files, validates harness_root is within workspace path (security boundary), updates workspace `harnessctl_path` when harnessctl is created.
- Updated `workspace init-harness` CLI to accept `--mode full|minimal`, `--source`, and `--dry-run` flags. Full mode requires `--source`, minimal mode requires `--root`/`--task-id`/`--plan-doc`.
- 22 new tests in `tests/test_doctor.py`: doctor (missing path, missing root, missing harnessctl, not executable, healthy full, invalid checklist, bus note, to_dict), full init (dry-run, creates files, no overwrite, updates harnessctl_path, missing source, root outside workspace, unknown workspace, empty source, to_dict), CLI integration (doctor unknown/minimal, init full requires source, init minimal requires root).
- Coordinator test suite: 664/664 pass (642 existing + 22 new).
- Updated `docs/project-harness/runbook.md` with new workspace onboarding order (register → doctor → init-harness full → doctor verify → task create → audit).

### Phase 5.3: Agent Registry Auto-Sync — implementation

- Created `src/multi_agent_coordinator/agent_registry.py`: TOML parser for `[[agents]]` and `[[external_agents]]` that extracts `id`, `display_name`, `discord_user_id`, and `agent_type`. Skips entries missing `discord_user_id`, fails closed on duplicate IDs or Discord user IDs.
- Added `sync_workspace_agents` batch helper to `db.py` with merge (default, preserves manual overrides) and `--replace` (replaces entire registry) semantics.
- Added `workspace agent sync` CLI subcommand with `--source` and `--replace` flags. Outputs JSON summary: `added`, `updated`, `unchanged`, `skipped`, `removed` (replace only).
- 16 new tests: 6 TOML parsing, 6 DB sync, 4 CLI integration (including token leak prevention).
- Coordinator test suite: 640/640 pass. multinexus test suite: 165/165 pass.
- End-to-end verified: synced 8 agents from real `agents.toml` to coordinator DB.
- Updated `agents.toml.example` to mark `discord_user_id` as required for registry sync.
- Updated runbook with `workspace agent sync` commands.

### Phase 5.2: Task-Scoped Session Lifecycle — implementation

- Added canonical session scope helpers for `channel:<channel_id>`, `thread:<thread_id>`, and `task:<workspace_id>:<task_id>`, with legacy numeric scope fallback for existing sessions.
- Extended `SessionStore` with active lookup fallback, scope-prefix/task queries, and task stale/archive lifecycle operations.
- Updated coordinator handoff runtime so accepted task handoffs use task scope, resume the same task session, isolate different tasks, and archive local task sessions on coordinator closeout/done lifecycle notices without executing coordinator mutations from Discord text.
- Updated text and slash session status/reset output to show scope type.
- Updated session persistence design and runbook with task scope priority, archive semantics, and contamination troubleshooting.
- Validation: targeted session/command/handoff tests passed; full suite `.venv/bin/python -m unittest discover tests/` passed with 161 tests.

### Phase 5.1: Handoff Runtime Hardening — runtime tests and protocol docs

- Added 12 runtime tests in `tests/test_coordinator_handoff_runtime.py` covering:
  - Accept failure: sends `[agent-report] action=blocker`, adapter NOT called.
  - Accept success: sends accept report, reads bootstrap, calls adapter with bootstrap prompt.
  - Bootstrap missing: adapter still called, prompt notes bootstrap missing.
  - All report sends use `AllowedMentions.none()`.
  - Action scope: only `assignment.accept` auto-executed; `mark-done`, `closeout`, `merge`, `deploy`, `pr` all rejected.
- Created `docs/agent-report-protocol.md`: documents report format, supported actions, auto-accept behavior, and when to use Discord report vs coordinator CLI.
- Full test suite: 134 pass (122 existing + 12 new).

## 2026-05-29

### Round 1 — Initial implementation

- Worker implemented all Phase 3.3 launchd artifacts:
  - 3 plist templates (`launchd/com.multinexus.mac-{claude,codex,opencode}.plist`)
  - Shared lib (`scripts/lib/launchd.sh`)
  - 4 management scripts (`scripts/{start,stop,status,uninstall}.sh`)
- Fixed `start.sh` plist update semantics: `bootout` + `bootstrap` cycle replaces `kickstart -k` so launchd reloads changed plists.
- Added launchd documentation section to `docs/platform-setup.md`.
- Static validation passed: `plutil` 3/3, `bash -n` all pass, 106 tests OK.
- Submitted for review.

### Round 2 — Review findings addressed

- **Finding 1**: `check_manual_process` in `scripts/lib/launchd.sh` used a narrow `pgrep -f "multinexus.py --agent $agent"` pattern that missed invocations with intervening flags (e.g. `python multinexus.py --config agents.toml --agent mac-claude`). Fixed to `nexus\.py.*--agent[= ]${agent}\>` which matches `--agent X` and `--agent=X` regardless of flag order.
- **Finding 2**: Closeout file list was incomplete (omitted 5 of 9 artifacts). Corrected.
- Re-validated: `bash -n` all pass. (plutil and tests unchanged from round 1.)

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
- Synced wording around coordinator Discord daemon, targeted agent handoff delivery, multinexus coordinator handoff auto-accept, and the rule that task lifecycle state changes go through coordinator CLI rather than direct harness JSON edits.
- Sanity-checked documented coordinator commands against current `mac.sh --help` output.
- Validation: `git diff --check` passed; `scripts/harness/harnessctl validate` passed; `scripts/harness/harnessctl doctor` exited 0 with existing optional/current file misses (`current/task_plan.md`, `init.sh`).
