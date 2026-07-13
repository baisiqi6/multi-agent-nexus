# P9-1 Codex result review — Round 1

Date: 2026-07-13  
Reviewer: Codex operator/reviewer  
Worker: Kimi `kimi-code/kimi-for-coding-highspeed`  
Worker JSONL session: `019f5991-928c-7000-bb18-b8395db4e9d9`  
Verdict: **REJECT — correction required before commit, deploy, or lifecycle closeout**

## What passed

- Both isolated worktrees stayed inside the approved path boundary and remained
  uncommitted.
- Coordinate job CRUD was extracted behind static compatibility re-exports.
- Cross-repository fixture bytes currently match at
  `975be64ca2cba84530cf969038cce4c5fb74df0b5f33aed86df9352ec9d12786`.
- Worker verification reported Coordinate `1894 passed, 449 subtests passed` plus the
  same nine historical failures, and MultiNexus `409 passed, 2 skipped, 26 subtests
  passed`.
- Managed adapter invocation and session-store writes use the claimed context cwd and
  scope in the happy path.

Passing tests do not clear the blockers below; several required adversarial cases were
not tested.

## Must-fix findings

### R1-1 — rejected requests still write authority evidence, and missing tasks are not rejected

`coordinate/runtime.py:308-335` appends `request.received` before resolving the host
profile, task mirror, scope, and paths. A missing host profile therefore rejects the
job but leaves a durable request event. Direct probe: `event delta on rejected request
= 1`, latest type `request.received`.

Also, `_task_mirror()` returning `None` is treated as a non-task request. A request for
`task_id=does-not-exist` creates a job whose row has that task id while its context has
`task_id=null` and a channel scope. This violates the fail-before-write and task-scope
contract.

Required correction:

- Resolve and validate all authority inputs before the first event/job write.
- Explicitly reject a supplied task id with no task mirror.
- Preserve idempotent event/job identity without introducing orphan events; use a
  transaction or an equivalent no-partial-write sequence.
- Add tests asserting zero event/job delta for every precondition failure and exact
  job/context task identity.

### R1-2 — idempotent replay accepts different prompt/reply payloads

`coordinate/runtime.py:352-379` compares only the recomputed context for v1 jobs.
Replaying the same idempotency key with a different prompt and reply returns the
original job without an error. Direct probe returned `job_created=False` while the
stored prompt/reply remained the first payload.

Required correction: compare the complete semantic request authority (`workspace`,
target agent, task, prompt, origin, reply, and resulting context) and reject every
conflict. Do not rely on the idempotency key alone.

### R1-3 — the v1 parsers are not strict and unsafe paths can become adapter cwd

Both parsers coerce required fields with `str(...)`, accept unknown keys, accept
relative/traversal-capable paths, and do not validate the exact `log_handle` schema.
MultiNexus additionally validates `session_scope_id` only as a non-empty string.

Adversarial probes accepted all of the following when the digest was recomputed:

- `worktree_path="relative"`, `session_scope_id="scope with spaces"`;
- `log_handle={"anything":"accepted"}` plus an extra top-level field;
- integer `job_id` and `workspace_id`, coerced to strings.

`_map_foreign_path()` also returns absolute paths outside the control workspace as-is
and permits `..` segments instead of failing closed.

Required correction:

- Define one exact v1 key/type/nullability schema and enforce it independently in
  both repos; reject missing and extra keys.
- Validate primary and legacy scopes, exact `log_handle` keys/kind/job identity, and
  a full 64-hex `context_id`.
- Require host-absolute, control-mapped paths; reject NUL/newline, traversal, relative
  authority paths, and absolute control paths outside the workspace root.
- Keep foreign path handling lexical; never use local `Path.resolve()` on a foreign
  root.
- Make the Coordinate value object deeply immutable or otherwise prevent nested
  `log_handle` mutation after digest binding.
- Expand the fixture mutation matrix to prove each rejection.

### R1-4 — claim validation does not bind context to the full job envelope

`multinexus/agentd/execution_context.py:258-263` checks context job id and agent, but
does not compare context workspace/task/assigned-agent fields to the returned job.
Direct probe accepted a job with `workspace_id=OTHER`, `task_id=DIFFERENT` and a
context with `workspace_id=ws`, `task_id=null`.

Required correction: validate job id, workspace id, task id, assigned agent, and the
attempt token against the claim envelope before provider invocation. Add mutation
tests proving every mismatch invokes no adapter and reports one bounded failure with
the current token when a valid job/token is available.

### R1-5 — Discord machine handoff does not carry v1 fields; managed fallback is not fail-closed

The actual webhook renderer remains unchanged at `coordinate/policy.py:374-380` and
emits only workspace, task, bootstrap, and action. The new fields were appended to the
human `handoff_text`, which `_agent_handoff_delivery()` does not send. A direct render
probe confirmed no `context_version`, `workspace_path`, `harness_root`, or `branch`.

MultiNexus `coordinator_handoff.py:44-45` also falls back to
`coordinator_workspace_path` in `agentd_mode` when the v1 handoff is missing. The plan
requires managed mode to fail closed; legacy fallback is allowed only outside
`agentd_mode`.

Required correction:

- Add safely quoted v1 fields to the real `[handoff]` machine message from the event's
  execution profile/task branch.
- Preserve the legacy required fields byte-for-byte before the appended fields.
- In managed mode, accept bootstrap text returned by `assignment accept`, otherwise
  require a valid v1 handoff context; do not use configured path or Coordinate SQLite
  fallback.
- Add end-to-end renderer-to-parser tests for worker and reviewer, POSIX/Windows
  paths, spaces/quotes/backslashes, missing v1 context, and legacy non-agentd behavior.

### R1-6 — malformed/non-JSON Coordinate responses can still crash or silently empty-poll agentd

`coordinate_client.py` raises only when `_run_cli()` returns an `error` dict.
`json.loads(proc.stdout)` errors and OS execution errors escape, while a structurally
invalid success object can be treated as `None`. `AgentdWorker.run()` catches only
`CoordinateRuntimeError`.

Required correction: normalize non-zero, timeout, non-JSON, OS, and malformed claim
envelopes into bounded `CoordinateRuntimeError`; log and back off without spinning or
invoking an adapter. Add loop-level tests, not only a mocked `{"error": ...}` test.

### R1-7 — required permanent tests and progress claims are incomplete

Add the missing permanent coverage from the approved plan, including request
pre-write failures, missing task mirror, unsafe mapping, full replay semantics,
recovery snapshot reuse, claim CAS single-winner, schema-v11/no-migration assertion,
actual policy handoff rendering, strict mutation matrix, all claim identity
mismatches, progress/final resume cwd, and managed worker/reviewer no-fallback flows.

Correct `docs/project-harness/progress.md`: it currently overclaims strict mutation
rejection, semantic replay detection, real handoff fields, non-JSON error handling,
and fields (`worktree_path`, `host_id`) that are not emitted by the machine handoff.

## Revalidation gate

After corrections, rerun every approved-plan validation command, both full suites,
cross-repo fixture byte/SHA comparison, CLI/AST gates, and managed-path static gates.
Return exact outputs and dirty-path boundaries. Stop again for Codex Round 2; do not
commit, push, deploy, mutate lifecycle, or touch production.
