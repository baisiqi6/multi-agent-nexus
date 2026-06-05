# Round 2 Hardening Closeout — 2026-06-05

## Baseline

| metric | discord-nexus | multi-agent-coordinator |
|---|---|---|
| tests | 184/184 | 719/719 |
| harness validate | 0 warnings | 0 warnings |

## Changes

### High: mark-done gate semantics (`transitions.py`)

**Before**: `coarse_status == "done"` unconditionally passed the mark-done gate, allowing hand-edited done state to bypass closeout/review flows.

**After**: workflow-first. When a workflow entry exists, only `review_approved` and `closed` are trusted. Coarse status `done` is only used as a fallback for legacy items without a workflow field.

```
Prior gate:
  if wf_status in ALLOWED or coarse_status == "done" → pass

New gate:
  if wf_status is not None:
    only ALLOWED_MARK_DONE_STATUSES (review_approved, closed)
  else (no workflow):
    coarse_status == "done" → pass
```

Test: `test_gate_passed_coarse_done_overrides_workflow_todo` → renamed and flipped to `test_gate_rejected_coarse_done_workflow_todo` (expects REJECT).

### Medium: OMP adapter returncode handling (`omp.py`)

**Before**: `not response_text and proc.returncode != 0` — non-zero exit with stdout was treated as success.

**After**: `proc.returncode != 0` unconditionally returns error result. stdout included in error text when present.

Test added: `test_nonzero_exit_with_stdout_returns_error`.

### Medium: OMP adapter health check (`omp.py`)

**Before**: `shutil.which(bin_path)` only — could report "available" for binaries that fail at runtime (e.g. bun shim without PATH).

**After**: actually runs `omp --version` with `filtered_env()`, returns `available: proc.returncode == 0`.

### Medium: OMP adapter `--no-session` flag (`omp.py`)

`call()` now passes `--no-session` to prevent session file leakage on one-shot invocations. `resume()` does not pass the flag (needs session persistence).

### Medium: All managed agent system prompts (`agents.toml`)

Added lifecycle decision rules to all 7 managed agents:

1. Smoke test / 验证类 task → directly `mark-done`, no closeout
2. 正式实现 task → `closeout --reviewer <name>`, wait for reviewer `mark-done`
3. Already in `closeout_requested` → don't touch, send progress only

Added missing prompts for win-claude, win-opencode, win-openclaw.

### Medium: Coordinator auto-mark-done on done report (`daemon.py`)

`_do_ingest` now calls `transitions.mark_done_task()` when `action=done` in agent report (idempotent, uses per-agent idempotency key).

### Low: Harness state consistency

Both mvp-checklist.json items (`phase-6.1-omp-smoke`, `phase-6.1-auto-mark-done`) pushed through proper closeout → review-approve → mark-done flow. `workflow.status` set to `closed` in both `harness-state.json` and `mvp-checklist.json`.

### Low: Missing plan.md

Created `docs/project-harness/tasks/phase-6.1-omp-smoke/plan.md` symlink → `phase-6-fleet-expansion/plan.md`.

### Low: launchd plist tracking

`launchd/com.discord-nexus.mac-omp.plist` added to git.

## Files changed

### discord-nexus
| file | change |
|---|---|
| `discord_nexus/adapters/omp.py` | returncode handling, health check, --no-session |
| `tests/test_omp_adapter.py` | nonzero+stdout regression test |
| `agents.toml` | lifecycle decision rules ×7; win agent prompts |
| `scripts/lib/launchd.sh` | mac-omp in AGENTS array |
| `launchd/com.discord-nexus.mac-omp.plist` | new (tracked) |
| `docs/project-harness/harness-state.json` | workflow→closed |
| `docs/project-harness/mvp-checklist.json` | workflow→closed |
| `docs/project-harness/tasks/phase-6.1-omp-smoke/plan.md` | new symlink |
| `docs/project-harness/current/closeout-packet.md` | removed (stale) |
| `docs/project-harness/current/handoff-packet.md` | removed (stale) |

### multi-agent-coordinator
| file | change |
|---|---|
| `src/multi_agent_coordinator/transitions.py` | workflow-first gate |
| `src/multi_agent_coordinator/daemon.py` | auto-mark-done on done report |
| `tests/test_transitions.py` | gate test flipped |
| `tests/test_daemon.py` | ingest tests for auto-mark-done |
| `docs/harness-state.json` | workflow→closed |
| `docs/mvp-checklist.json` | workflow→closed |

## Known remaining items

Listed in `docs/project-harness/tasks/phase-6-fleet-expansion/plan.md`:

- dogfood #2: historical lifecycle re-delivery
- dogfood #16: blocker missing adapter error summary
- dogfood #19: cross-workspace bootstrap path
- dogfood #20: worker may not send done report
- Phase 6.2: cross-device orchestration design
- Phase 6.3: Windows/Linux agent deployment
