# Phase 7.1 Review Feedback Round 2

Reviewer: `codex-operator`
Date: 2026-06-08
Decision: changes requested

## Summary

The rework fixed one important issue: Discord and KOOK bridges no longer embed `AgentDaemon`; they now connect to a standalone HTTP agentd port.

That is necessary but still not sufficient for Phase 7.1. The phase plan and prior review feedback require the control-plane path:

```text
bridge -> coordinate -> standalone agentd
```

The current rework is:

```text
bridge -> standalone agentd
```

Coordinate is still bypassed for runtime request ingest, job claim, result reporting, and response delivery metadata.

## Required Changes

### 1. Implement the coordinate runtime boundary, not just direct HTTP agentd

Current bridge mode submits directly to `AgentdClient.submit(... agentd_port ...)`.

Required:

- Bridge mode should submit normalized requests to coordinate using the available runtime CLI/API shim.
- Standalone agentd should register/heartbeat with coordinate, claim jobs, execute the adapter, and report results.
- Response routing metadata should be stored through coordinate so the result can be delivered back to the original Discord/KOOK target.

At minimum, tests must exercise the available coordinate runtime flow:

```bash
coordinate runtime request submit ...
coordinate runtime job claim --agent-id ...
coordinate runtime job report ...
```

The existing `tests/test_n_plus_m_invariant.py` comment says "via coordinate runtime", but the test only performs direct HTTP agentd round-trip. That test name/comment is currently misleading.

### 2. Commit dependency/install changes

`requirements.txt` contains `khl>=0.4.0` in the working tree, but it is not included in the latest committed rework commit.

Required:

- Include the dependency change in the worker commit, or intentionally implement optional-import behavior with clear tests.
- Do not request closeout with required runtime dependency changes left uncommitted.

### 3. Fix standalone agentd shutdown

`multinexus/agentd/__main__.py` handles SIGINT/SIGTERM by scheduling `daemon.stop()`, but it does not call `loop.stop()`.

Impact:

- On SIGTERM/SIGINT, the server may stop accepting requests while the process keeps running in `loop.run_forever()`.

Required:

- Ensure signal handling stops the daemon and exits the event loop cleanly.
- Add a small test for the shutdown callback or refactor the runner so shutdown behavior is testable without sending real OS signals.

## Validation Already Observed

- `.venv/bin/python -m unittest discover tests/` passed: 238 tests, 2 skipped.
- `scripts/harness/harnessctl validate` passed.
- `git diff --check` passed.

These validations are useful but do not close the architecture gap above.

## Closeout Requirements

Before requesting review again:

1. Implement `bridge -> coordinate -> standalone agentd`.
2. Commit all runtime dependency changes.
3. Fix standalone agentd shutdown.
4. Update tests so the coordinate runtime flow is actually exercised.
5. Re-run multinexus tests and harness validation.
6. Request coordinate closeout again with a structured `[agent-report] action=done`.

