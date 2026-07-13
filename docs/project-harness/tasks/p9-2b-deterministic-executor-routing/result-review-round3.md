# P9-2B Result Review — Round 3

Status: `changes_requested`

## Reviewed authority

- Approved plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate Round 2 correction: `7139728435e842e8728739ec6246b5b8eeb17407`
- MultiNexus Round 2 report: `3c8863c16a5d5dba84c046cdd1d693db4e15dda1`
- Worker model: ordinary `kimi-code/kimi-for-coding` (no highspeed)

## What now passes

The five original Round 2 direct-probe classes now reject as required:

- stored ineligible candidate with a recomputed decision digest;
- forged routed decision-to-binding link;
- forged exact stored-job prompt;
- forged routed stored-job prompt;
- forged routed event-row `task_id`.

The reviewer gate also passed the repaired concurrent-loser test and the full
16-case claim zero-mutation matrix:

```text
7 passed, 16 subtests passed in 0.06s
```

The duplicate-test AST detector reports no duplicate test methods in
`tests/test_runtime.py` or `tests/test_executor_routing.py`.

## R3-1 — exact typed replay still accepts forged event content

Round 2's bootstrap required exact and routed replay to verify the stored
event and derived job's `prompt`, `origin`, `reply`, and task links, while
preserving the accepted exact typed `execution_context conflicts` ordering.

`_replay_exact_request()` now validates the stored job correctly, but in the
typed-context branch it no longer validates the event payload's `origin`,
`reply`, or payload `task_id`. A stored event can therefore be forged while
the derived job and current replay request remain unchanged. Three independent
reviewer probes returned success:

```text
EXACT_EVENT_ORIGIN_FORGERY_ACCEPTED
EXACT_EVENT_REPLY_FORGERY_ACCEPTED
EXACT_EVENT_TASK_ID_FORGERY_ACCEPTED
```

This also makes the Round 2 implementation report's claim that exact replay
validates all event/job content links inaccurate.

### Required correction

After the typed execution-context comparison succeeds, validate the stored
event payload's `origin`, `reply`, and payload `task_id` against the current
request and the stored job authority. Keep the execution-context comparison
before those checks so the accepted compatibility error ordering remains
unchanged. Apply equivalent fail-closed event-content checks to the legacy
branch without weakening any existing assertion.

Add a permanent exact-event mutation matrix covering at least `origin`,
`reply`, and payload `task_id`; each case must assert rejection and zero changes
to event count, job status, attempt count, and stored payload.

## Validation integrity

The worker's JSONL shows the reported final pytest commands were executed with
`2>&1 | tail -30`, although the Round 2 bootstrap required final commands to be
unpiped. The next correction must run its final focused gate unpiped and record
the command exactly as executed. Codex will independently run the final full
gates before integration.

Do not push, cherry-pick, deploy, restart services, mutate production, or close
the P9-2B lifecycle until a later Codex review returns `approved`.
