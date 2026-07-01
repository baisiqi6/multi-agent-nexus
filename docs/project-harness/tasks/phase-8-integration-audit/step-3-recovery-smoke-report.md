# Phase 8 Integration Audit — Step 3 Recovery Smoke Report

**Result: PASS** — all 7 conditions satisfied on the integrated feature branches. No code
regression from the Step 2 cherry-picks. No code was modified (smoke-only).
**Branches under test:** `agents/mac-codex/phase-8-integration` coordinate `4ac774e` /
multinexus `c91631a` (the Step 2 integration branches).
**Date:** 2026-07-01.

Step 3 re-verifies the 8.4.3 recovery / fail-closed path against the **integrated** code
(Step 2 cherry-picked the fixes onto the Phase 8 long branch). The fail-closed path was
previously validated only on the standalone 8.4.3 branches; this confirms the cherry-picks
did not regress it.

## Setup (fully isolated)

- Temp coord/context SQLite DBs under `/var/folders/.../step3-smoke-*/` (never the
  production DB). Production `com.multinexus.mac-codex.agentd` launchd job **unloaded** for
  the duration, **restored** after (try/finally).
- A `coord-wrapper.sh` mimics the production coord-local/coord-ssh contract: reads
  `MAC_DB` (which agentd sets from `agents.toml coordinator_db_path`) and forces `--db` on
  the integration coordinate CLI (`python -m coordinate`). This is the same wrapper layer
  production relies on — the agentd sets `MAC_DB`, the wrapper translates to `--db`. (The
  bare CLI reads `MULTI_AGENT_COORDINATOR_DB`; the env-name divergence is pre-existing from
  the rename commit `058059b`, not introduced by integration, and is bridged by the wrapper
  in both production and this smoke.)
- `fake-codex.sh` stands in for the codex binary: logs every invocation, exits 2 on
  `exec resume <sid>` (→ codex adapter emits `Codex resume failed (2): …`), exits 3 on the
  call path. Drains stdin. This deterministically exercises the `_is_error("Codex resume
  failed")` → fail-closed branch (the last cherry-pick, `c91631a`).
- Temp agentd process from the multinexus integration worktree
  (`python -m multinexus.agentd --config <temp agents.toml> --agent mac-codex`), so `import
  multinexus` resolves to integration code.

## Conditions and evidence

| # | condition | result | evidence |
|---|---|---|---|
| 1 | attempt 1 reaches `timed_out + recoverable` | PASS | Job1 `request:34f3116d…` pre-state: `status=timed_out, attempt_count=1, recoverable=1, terminal_session_id=fake-recovery-step3-session` |
| 2 | recovery agentd uses explicit `--recoverable` | PASS | log: `Agentd worker started in RECOVERY mode: agent=mac-codex (will claim timed_out+recoverable jobs)` |
| 3 | attempt_count 1 → 2 | PASS | Job1 `attempt_count` 1 (pre) → 2 (final after recovery claim) |
| 4 | `recovery_session_id` path taken | PASS | log: `Resuming recoverable session fake-recovery-step3-session` |
| 5 | resume failure is fail-closed | PASS | Job1 final `status=failed`; `result.response_text="Agent error: recoverable session resume failed; not starting duplicate fresh execution"`; fake-codex invoked **exactly once** with `exec resume fake-recovery-step3-session …` (no `exec -C` call fallback, no second invocation); no `job.completed` event |
| 6 | stale attempt-1 report/progress rejected by SQL CAS; job not overwritten | PASS | `runtime job report … --attempt-token 1` → rc=1, stderr `… report rejected: CAS failed — not running as attempt 1 (status=running attempt_count=2; stale attempt or reclaimed)`; `runtime job progress … --attempt-token 1` → rc=1, same CAS message; Job2 stayed `running@attempt_count=2`, `result.response_text` unchanged (`"j2 timeout"`, NOT the stale `"stale attempt1"`) |
| 7 | normal agentd default mode carries no `--recoverable` | PASS | default-mode log: `agentd worker starting: agent=mac-codex recoverable=False`; ran 3.5 s against the timed_out+recoverable job → did not claim it (Job1 stayed `timed_out@attempt 1`), fake-codex invoked 0 times |

### Event chain (Job1, in order)

```
request.received → job.claimed → job.progress → job.timed_out → agent.reported
→ job.claimed → job.failed → agent.reported
```

Exactly two `job.claimed` events (attempt 1 seed + attempt 2 recovery); terminal is
`job.failed`, **no** `job.completed`/`job.done`. This is the fail-closed shape: the recoverable
resume failed and the worker reported `failed` rather than starting a fresh duplicate.

### Stale CAS commands and stderr (condition 6)

```
$ coord-wrapper.sh runtime job report request:0792750c… --agent-id mac-codex \
    --status done --result-json '{"response_text":"stale attempt1"}' --attempt-token 1
→ rc=1  stderr: error: job request:0792750c… report rejected: CAS failed — not running
        as attempt 1 (status=running attempt_count=2; stale attempt or reclaimed)

$ coord-wrapper.sh runtime job progress request:0792750c… --agent-id mac-codex \
    --stage stale --attempt-token 1
→ rc=1  stderr: error: job request:0792750c… progress rejected: CAS failed — not running
        as attempt 1 (status=running attempt_count=2; stale attempt or reclaimed)
```

After both rejections, Job2 remained `running@attempt_count=2` with its result unchanged
(`response_text="j2 timeout"`), proving the stale attempt-1 writes did not land.

### Recovery agentd log snippet (condition 2/4/5)

```
… WARNING Agentd worker started in RECOVERY mode: agent=mac-codex (will claim timed_out+recoverable jobs)
… INFO    Processing job request:34f3116d-2ece-4738-aa7d-8d3de9002e88: agent=mac-codex prompt_len=8
… INFO    Resuming recoverable session fake-recovery-step3-session
… INFO    Job request:34f3116d-2ece-4738-aa7d-8d3de9002e88 complete: status=failed duration=351ms
```

### fake-codex invocation log (proves no fresh duplicate)

Exactly one entry — the resume, with the recovery session id and NO call-path fallback:

```
[invocation] argv: exec resume fake-recovery-step3-session --json --skip-git-repo-check -c sandbox_permissions=["danger-full-access"] --model smoke-model -
```

## Production restore + cleanup

- Production `com.multinexus.mac-codex.agentd` reloaded; `launchctl list` shows it running
  again (PID assigned, exit status 0).
- `ps` scan for `multinexus.agentd` + `--recoverable`: **none lingering** (the temp agentd
  processes were terminated; production runs default mode with no `--recoverable`).
- Temp DBs / fake-codex / wrapper / logs left under the temp dir for reference; they are
  outside both repos and were never committed.

## Code modifications

**None.** This step was smoke-only (temp harness + temp agentd). No file in either
integration worktree was changed. The integrated code passed as-is.

## Note on the in-harness c6 check expression

The smoke driver's boolean for condition 6 initially reported False due to an over-strict
sub-clause in the *check* (`not result.response_text`), not a code defect: a reclaim
legitimately carries the prior attempt's timed_out result forward, so `result.response_text`
is non-empty ("j2 timeout"). A direct DB read confirmed the stale report was rejected and
the result was NOT overwritten by the stale payload. The integrated CAS behavior is correct;
only the harness assertion was too narrow. All 7 conditions pass on their substantive merits.

## Conclusion

Step 3 PASS. The 8.4.3 recovery fixes behave identically on the Phase 8 long integration
branch as on the standalone 8.4.3 branch: ordinary polls never reclaim stuck timed_out jobs,
explicit `--recoverable` recovery resumes the recorded session, resume failure fails closed
without a fresh duplicate, and stale attempt-token writes are rejected by SQL CAS. Ready for
codex review to decide whether to push the integration branches (Step 4 merge-strategy
decision still pending).
