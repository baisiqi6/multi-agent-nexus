# Phase 7.1 Review Feedback Round 3

Reviewer: `codex-operator`
Date: 2026-06-08
Decision: changes requested

## Summary

The latest rework moved the topology in the right direction:

```text
bridge -> coordinate runtime request -> agentd worker claim/report
```

However, the runtime path still has two blocker-level issues that prevent approving Phase 7.1.

## Findings

### 1. Bridge polling cannot observe completed coordinate jobs

`CoordinateRuntimeClient._get_job()` currently runs:

```text
coordinate job list --status all
```

and then reads:

```python
result.get("result", {}).get("jobs", [])
```

But coordinate's `job list` command returns top-level `{"jobs": [...]}`, not `{"result": {"jobs": [...]}}`. Also `--status all` is not an "all statuses" sentinel in coordinate; it is passed through as an exact SQL status filter (`status = "all"`), so it returns no normal `done` / `failed` jobs.

Impact: Discord/KOOK bridge can submit a request and agentd can report a result, but the bridge-side `wait_for_job_result()` will not find it and will eventually time out.

Required fix:

- Either add a coordinate runtime `job get` command and use it, or call `job list` without a status filter and parse the top-level `jobs` field.
- Add a regression test where `_run_cli()` returns coordinate's real `{"jobs": [...]}` output and `_get_job()` finds the completed job.
- Add a test that does not rely on `--status all` unless coordinate implements that sentinel.

Relevant code:

- `multinexus/agentd/coordinate_client.py`
- coordinate reference: `src/coordinate/cli.py::handle_job_list`, `src/coordinate/db.py::list_jobs`

### 2. Task/channel session behavior is not preserved in agentd worker mode

Legacy Discord bridge mode used the session store to resume existing sessions by canonical scope and legacy channel scope before falling back to a fresh adapter call.

The new `AgentdWorker` always calls:

```python
self.adapter.call(prompt, work_dir=self.config.work_dir)
```

It writes `result.session_id` back to `SessionStore`, but it never reads the store, never calls `adapter.resume()`, and the bridge does not submit `session_scope_id` / `legacy_scope_ids` through coordinate payload.

Impact: Phase 7.1 acceptance says existing task-scoped session behavior must be preserved or covered by an equivalent new test. The current implementation loses that behavior in `agentd_mode=true`.

Required fix:

- Include `session_scope_id`, `legacy_scope_ids`, `context_channel_id`, and `work_dir` in the coordinate runtime request payload.
- Make `AgentdWorker` use the same call/resume logic as legacy `DiscordClient._run_adapter_for_scope()` or reuse the existing `AgentDaemon` processing logic behind the coordinate worker.
- Add tests proving a second request for the same scope calls `adapter.resume()` and stale legacy scope handling still works.

Relevant code:

- `multinexus/client.py::_handle_via_agentd`
- `multinexus/agentd/worker.py::_process_job`

## Validation Observed

- `.venv/bin/python -m unittest discover tests/` passed: 247 tests, 2 skipped.
- `scripts/harness/harnessctl validate` passed.
- `git diff --check` passed.

These validations are useful, but the current test suite does not cover the two runtime failures above.

## Closeout Requirements

Before requesting review again:

1. Fix bridge polling so completed coordinate jobs are observed.
2. Preserve session resume behavior in coordinate agentd mode.
3. Add targeted regression tests for both issues.
4. Re-run multinexus tests and harness validation.
5. Request structured closeout again.
