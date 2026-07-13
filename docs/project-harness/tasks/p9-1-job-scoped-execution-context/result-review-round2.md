# P9-1 Codex result review — Round 2

Date: 2026-07-13  
Reviewer: Codex operator/reviewer  
Correction worker: Kimi `kimi-code/kimi-for-coding-highspeed`  
Correction JSONL session: `019f59b2-0f0e-7000-80a6-433c4a379627`  
Verdict: **REJECT — narrow correction required**

## Independently reproduced passing evidence

- Coordinate focused P9-1 suites: `251 passed`.
- Coordinate full suite: `1936 passed, 449 subtests passed`, plus exactly the nine
  historical CLI/AST failures.
- MultiNexus full suite: `437 passed, 2 skipped, 26 subtests passed`.
- Both fixture files remain byte-identical at
  `975be64ca2cba84530cf969038cce4c5fb74df0b5f33aed86df9352ec9d12786`.
- Both worktrees pass `git diff --check` and remain uncommitted.

## Must-fix findings

### R2-1 — Coordinate still creates unsafe/inconsistent contexts

`resolve_execution_context_v1()` validates stored snapshots but does not validate the
resolved profile paths before creating and persisting the initial snapshot. Direct
probe: a host profile with `workspace_path=relative/ws` and
`harness_root=relative/h` was accepted, and `submit_request()` created the job.

The pre-upgrade claim path also fails to reject a supplied job task id whose task
mirror is missing. Direct probe: a pending job with `task_id=ghost` was claimed with
`context.task_id=null` and channel scope.

Required correction:

- Validate every resolved workspace/worktree/harness/log path before digest/persist;
  unsafe host profiles must fail before event/job creation.
- In backfill, reject a non-null row task id with no task mirror before CAS mutation.
- Add zero-mutation tests for both cases.

### R2-2 — MultiNexus does not bind the full claim envelope

`validate_claim_response()` compares context job id/task id and context agent to the
configured agent, but not context workspace to `job.workspace_id`, context agent to
`job.assigned_agent`, or `attempt_token` to `job.attempt_count`.

Direct probes accepted all three mismatches:

- job workspace `JOB-WRONG` vs context workspace `ctx-ws`;
- job assigned agent `OTHER` vs context/config agent `a`;
- job attempt count `99` vs claim token `1`.

Required correction: require exact, correctly typed job id/workspace/task/assigned
agent/attempt identity before adapter invocation. Add one no-adapter/failure-report
test per mismatch and require `claimed is True`, not generic truthiness.

### R2-3 — machine handoff is not byte-compatible and can omit required v1 fields

The legacy machine block previously ended with `action=...`. The new renderer inserts
v1 fields before action, contradicting the approved requirement that existing fields
remain byte-compatible and v1 fields be appended.

If the execution profile has `harness_root=null`, the renderer simply omits
`harness_root`; direct render output confirmed this. A valid prepared handoff must
emit a canonical host harness path, not a partial v1 block.

Required correction:

- Preserve the exact legacy prefix through `action=...`, then append all v1 fields.
- Materialize a complete canonical handoff context during `prepare_handoff` (or an
  equivalent single authority point), including harness fallback and nullable branch.
- MultiNexus must validate `context_version`, host-absolute workspace/harness paths,
  and malformed/partial v1 blocks before using them.
- Upgrade renderer-to-parser tests to assert exact prefix bytes and required-field
  behavior, not only `assertIn` checks.

### R2-4 — valid metadata plus missing bootstrap content does not fail closed

In worker and reviewer managed handoff paths, a v1 handoff with a workspace path but a
missing/unreadable bootstrap is allowed to continue with `bootstrap_content=None`.
The approved plan requires missing required context/bootstrap to fail closed.

Required correction: after assignment-accept output/file resolution, managed mode
must stop with one bounded blocker if bootstrap content is still missing. Add worker
and reviewer integration tests proving no agentd submission/provider invocation.

### R2-5 — strict-schema and repository hygiene remain incomplete

- Coordinate required scalar parsing reuses a nullable helper; required fields should
  be explicitly non-null.
- Both parsers accept tuple `legacy_scope_ids` and silently canonicalize duplicates;
  the JSON v1 contract requires a unique list, so strict consumers should reject
  wrong container types and duplicate/primary duplicates.
- `tests/__init__.py` was added only to work around a local foreign-package issue.
  The authoritative repo venv already runs the full suite correctly; remove this
  unplanned file and verify with `/Users/yinxin/projects/coordinate/.venv/bin/python`.
- `coordinate_client.py` uses `Any` without importing it.
- `progress.md` overclaims job/event repository extraction, full claim binding,
  byte-compatible handoff ordering, unsafe-path rejection, and completed Round 2.

Correct code/tests/docs and rerun all gates. Stop again for Round 3; no commit, push,
deploy, lifecycle closeout, receipt, or production mutation.
