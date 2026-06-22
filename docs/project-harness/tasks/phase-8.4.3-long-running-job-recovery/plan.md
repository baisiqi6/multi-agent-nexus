# Phase 8.4.3: Long-Running Job Recovery And Delivery Reliability

## Objective

Make coordinate + multinexus long-running coding jobs observable and recoverable. A fixed total timeout must not silently discard useful progress, lose the resumable Claude session, strand the user-facing failure response, or make a late terminal result impossible to reason about.

This task was opened from the Phase 8.4.2 dogfood incident where `mac-claude` made two coordinate commits and left a valid multinexus worktree diff, but the runtime job hit the 1800 second outer timeout, became terminal `failed`, returned an empty session id, and left its timeout response as a pending `platform=discord` delivery.

## Worker And Branch

- Worker: `mac-codex`
- Reviewer: `codex`
- Coordinate branch: `agents/mac-codex/phase-8.4.3-long-running-job-recovery`
- Multinexus branch: `agents/mac-codex/phase-8.4.3-long-running-job-recovery`
- Use only the dedicated worktrees named in `worker-bootstrap.md`; do not switch or clean `/Users/yinxin/projects/coordinate` or `/Users/yinxin/projects/multinexus`, which contain active Phase 8.4.2 work.

## Confirmed Incident

- Request event: `adb14f7c-88e7-4b0a-9ae1-a0104ef7615f`.
- Job: `request:adb14f7c-88e7-4b0a-9ae1-a0104ef7615f`.
- Claimed at `2026-06-22T06:25:54Z`, failed at `2026-06-22T06:55:56Z`.
- Stored result: `Agent error: timed out after 1800s`, empty `session_id`.
- Timeout delivery: `6f2da74a-795f-4c58-90b0-5a9d7b97b661`, still pending because it used `platform=discord` while the coordinate daemon pumps `discord_webhook`.
- Durable filesystem progress survived, but coordinator had no stage checkpoint or structured partial result.

## Required Invariants

1. A coding job has separate inactivity and absolute-budget semantics. Activity may renew the execution lease; a hard safety ceiling may still exist but must be explicit and testable.
2. Progress is durable enough to answer: last activity, current stage/summary, resumable session id, and whether filesystem work may exist.
3. Timeout is represented as a recoverable terminal/intermediate outcome with an explicit retry/resume path. It is not indistinguishable from an ordinary permanent failure.
4. A retry for the same task/session scope resumes the recorded agent session when safe and does not silently start a duplicate fresh execution.
5. Result races have deterministic rules. A result arriving after timeout is either accepted under an explicit recoverable transition or recorded with the full late-result payload for operator reconciliation; it must not be reduced to an empty replay marker.
6. Cancellation always cleans up the spawned Claude process. Cleanup must run for timeout, cancellation, parse errors, and unexpected exceptions.
7. Every terminal or recoverable timeout response reaches the configured visible Discord destination through a transport that is actually pumped.
8. Existing short request behavior, job claim idempotency, successful result delivery, and human merge/deploy gates remain unchanged.

## Workstream A: Runtime Job State And Recovery Contract (`coordinate`)

### A1. Model recoverable timeout explicitly

- Add the smallest schema/model change needed to distinguish `timed_out`/recoverable from permanent `failed`.
- Preserve backward compatibility for existing `done` and `failed` rows.
- Record structured timeout facts: timeout kind, configured budget, last activity time, session id when known, partial/progress summary, and `resume_allowed`.
- Do not encode these facts only inside an error string.

### A2. Deterministic late-result and resume rules

- Define allowed transitions and enforce them atomically.
- A normal completed/failed job remains immutable and idempotent.
- A recoverable timed-out job may be reclaimed/resumed through an explicit API/CLI path or accepted late according to the chosen contract.
- `job.result_replayed` must retain the submitted result payload and explain why it was not applied.
- Prevent two workers from simultaneously reclaiming the same timed-out job.

### A3. Progress/checkpoint recording

- Add a narrow runtime progress API used by agentd to persist last activity, stage/summary, and session id without marking the job complete.
- Progress updates must be idempotent and valid only for the assigned/running job.
- Avoid writing every token; throttle/coalesce updates and store bounded summaries.

### A4. Delivery transport normalization

- Runtime response delivery must resolve the workspace/reply destination to a live transport (`discord_webhook` in the current deployment) or the daemon must pump both supported Discord platforms.
- Do not require the SSH CLI environment to possess the Discord bot token.
- Existing pending runtime deliveries should be recoverable by the normal pump after deployment; document any one-time reconciliation command if migration is needed.

## Workstream B: Agentd Lease, Progress And Cancellation (`multinexus`)

### B1. Remove competing equal-budget timeouts

- Establish one owner for the absolute execution deadline.
- Keep first-byte and activity timeouts in the adapter.
- The worker must not cancel the adapter at the same instant as the adapter's own deadline.
- Prefer a renewable lease driven by meaningful activity/checkpoints rather than an unobservable fixed 1800 second wall clock.

### B2. Stream durable progress

- Parse Claude stream events sufficiently to capture session id and bounded human-readable progress without exposing private chain-of-thought.
- Invoke `on_progress` for safe result/progress text only.
- Agentd forwards throttled progress/checkpoint updates to coordinate.
- Ensure session id is persisted as soon as the init event arrives, not only after the final result.

### B3. Cancellation-safe subprocess lifecycle

- Wrap the Claude subprocess lifecycle in `try/finally` or equivalent ownership logic.
- On `CancelledError`, timeout, or exception, terminate and reap the exact child process.
- Add a regression test proving cancellation invokes cleanup and does not leave the fake subprocess running.

### B4. Resume behavior

- When coordinate provides a recoverable timed-out job with a stored session scope/session id, resume it.
- If resume is unavailable or rejected, fail closed with an operator-visible reason; do not silently duplicate work.
- Preserve dirty worktree and committed work. Never reset or clean as part of recovery.

## Workstream C: End-To-End Dogfood And Operational UX

1. Reproduce a short-budget long-running fake job that emits progress, exceeds its first lease, is marked recoverable, resumes, and finishes.
2. Verify coordinator events include claimed, progress/checkpoint, timeout/recovery, resumed, and completed transitions.
3. Verify exactly one final Discord-visible delivery is sent and no timeout/final response remains indefinitely pending.
4. Verify a genuine inactivity timeout terminates/reaps the subprocess and produces a visible recoverable error.
5. After automated tests pass, resume the real Phase 8.4.2 Claude task using its existing task/session scope. Do not discard its two coordinate commits or multinexus worktree changes.
6. Record every incident or manual step in `docs/project-harness/progress.md`.

## Compatibility And Non-Goals

- Do not merge, deploy, restart services, or create a PR without operator/human approval.
- Do not change Phase 8.4.2 source files or clean its worker checkouts.
- Do not broaden this into a generic distributed workflow engine.
- Do not persist raw model chain-of-thought or unbounded token streams.
- Do not solve reliability by only increasing `timeout = 1800`.
- Do not redesign all message buses; make the current Discord response path correct and covered.

## Tests

### Coordinate targeted tests

- runtime progress/checkpoint validation and idempotency;
- recoverable timeout transition;
- atomic reclaim/resume and double-claim prevention;
- late result accepted/rejected behavior including retained payload;
- response delivery transport normalization;
- legacy done/failed replay behavior;
- schema migration from the current deployed version.

### Multinexus targeted tests

- Claude adapter calls progress callback with bounded safe content;
- session id checkpoint occurs before terminal result;
- outer worker timeout does not race adapter deadline;
- cancellation always kills/reaps subprocess;
- timeout reports structured facts;
- retry resumes the recorded session and never resets worktree state.

### Full verification

```bash
# coordinate
python -m unittest discover -s tests -p 'test_*.py'

# multinexus
python -m unittest discover -s tests -p 'test_*.py'

# both repositories
scripts/harness/harnessctl validate
git diff --check
```

## Commit Plan

1. `feat(coordinate): add recoverable runtime job checkpoints`
2. `fix(coordinate): make runtime response delivery pumpable`
3. `fix(multinexus): make agentd timeout and cancellation recoverable`
4. `test(runtime): cover timeout resume and late results`
5. `docs: record Phase 8.4.3 dogfood recovery`

Keep logical commits separate. Push both worker branches. Do not force-push.

## Closeout

- Worker runs `assignment closeout discord-nexus --task-id phase-8.4.3-long-running-job-recovery --reviewer codex --actor mac-codex`.
- Worker must not run `assignment mark-done`.
- Reviewer verifies code, migrations, full tests, event history, delivery state, and the recovery dogfood before approval.
- Merge and deploy remain explicit human/operator gates.
