# P9-1 Job-Scoped Execution Context — Independent Plan Review Round 1

## Review identity

- Provider / model: `kimi-code/kimi-for-coding-highspeed`
- JSONL session id: `019f598b-6caf-7000-9bf3-c412a01f6405`
- Reviewer role: independent plan reviewer only (no implementation, no deployment, no lifecycle mutation)
- Review date: 2026-07-13

## Reviewed artifact

- Plan: `docs/project-harness/tasks/p9-1-job-scoped-execution-context/plan.md`
- Exact SHA-256: `c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e`
- Plan-ready event: `9e70e470-da68-4264-a066-36e63dfe1667`
- Plan-review-requested event: `5845d3fd-2574-4904-8cc5-314a84227930`
- Split operation: `7aa8b1f2-d5c7-4c6a-b12e-4ae9bd2fbf89`

## Verdict

**APPROVE_WITH_NON_BLOCKING_NOTES**

The approved plan revision SHA-256 `c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e` may be used as the implementation gate for the P9-1 worker bootstrap.

## Baseline verification

| Item | Value | Notes |
|---|---|---|
| Coordinate HEAD | `15020c2204e8e05c6304f6ed83a5fed83ad12eae` | matches plan start; `origin/main` identical; only dirty entry is untracked `.qoder/` |
| MultiNexus HEAD | `d827d2f3cc624aaf3c4e0e69cef9fb87e0bfa8e4` | `origin/main` identical; the two commits above plan baseline `0d7c716b7dc3620767069e61c3ad168ca78b78dd` are docs/bootstrap only (`0d6ac19`, `79065b6`) |
| Coordinate full suite | `1864 passed, 9 failed, 449 subtests passed` | failures are the documented CLI rewind / AST fixture failures; matches plan baseline exactly |
| MultiNexus full suite | `389 passed, 2 skipped, 26 subtests passed` | matches plan baseline exactly |
| Plan SHA | `c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e` | verified with `shasum -a 256` |

## Scope and adversarial findings

### Cross-repo contract package
The plan keeps the contract as a versioned v1 JSON object plus byte-identical golden fixtures in each repo, rather than introducing a third shared package. This is consistent with prior P9-0A packages and is acceptable because the fixture SHA and rollout matrix provide auditability and staged rollout.

### Snapshot / immutability / backfill rules
The plan correctly orders authority: Coordinate computes the context at `submit_request`, persists it in `jobs.payload_json`, returns the identical snapshot on recovery, backfills pre-upgrade pending jobs once at first claim, and refuses claim on host mismatch without mutating status/attempt. The idempotency key is based on the request event; the plan additionally requires rejecting payload/context conflicts on replay, which prevents a request event without a matching job or a silently mutated scope.

### Scope authority
Task scope is Coordinate-canonicalized to `task:{workspace_id}:{task_id}`. Non-task scope is bounded to channel/thread/request. Legacy scope ids are bounded, unique, and secondary. This prevents private task sessions from being reused across workspaces or tasks.

### Host profile / path mapping
The plan requires host-aware foreign-path joining and explicit tests for POSIX/Windows/relative/space/backslash. Current `handoff._path_for_execution_host` uses local `Path.resolve()`, which is unsafe for mapping to a foreign host root; the implementation must replace that with pure string/segment joining in `execution_context.py`.

### `worktree_path = workspace_path` fallback
The fallback is honest and fail-closed: the plan explicitly states worktree provisioning and branch switching are out of scope, and the resolver must fall back to the host workspace path when no explicit job worktree exists.

### Context digest and log handle
The digest binds the canonical v1 scalar fields excluding `context_id` itself, with `attempt_token` kept outside. The `log_handle` keeps `logs_path` nullable and defers provider JSONL/liveness semantics to P9-4.

### Job repository extraction
The extraction boundary is feasible: `job_repository.py` can depend only on `db_support.py` and narrow SQL, while `coordinate.db` statically re-exports the six symbols. No cycle is introduced as long as `job_repository.py` does not import `coordinate.db`.

### Failure modes
Missing profile/context fails before job creation or before adapter invocation. CLI errors must surface as bounded log + backoff rather than silent empty poll. Host mismatch fails closed. These rules prevent poison jobs, hot spin, and daemon death.

### MultiNexus direct Coordinate SQLite reads
The plan explicitly removes `resolve_workspace_path` and direct `sqlite3.connect(coordinator_db_path)` from managed (`agentd_mode`) worker and reviewer handoff paths. Legacy non-agentd mode may retain the fallback. This satisfies the P9-1 boundary; the static gate in the validation section must prove it.

### Handoff machine message additions
Adding host-native `workspace_path`, `harness_root`, and `branch` to the `[handoff]` machine text does not expand path-traversal surface if MultiNexus uses them only as parsed metadata and derives the actual adapter cwd/session from the Coordinate claim context. The plan already requires that. A non-blocking note below asks the worker to make this invariant explicit in tests and comments.

### Rollout and rollback
The compatibility matrix and order (Coordinate first, MultiNexus second) are correct. Pre-upgrade pending jobs are backfilled. MultiNexus rollback is safe while Coordinate remains additive; Coordinate rollback after MultiNexus upgrade is forbidden because new MultiNexus fails closed without context.

### Scope containment
The non-goals explicitly exclude P9-2 routing, P9-3 leases, P9-4 observation, P9-5 matrix, schema migration, and lifecycle authority changes. The code-ownership list is bounded and deterministic.

## Non-blocking notes

1. **Explicitly forbid local `pathlib.resolve()` for foreign host paths.**
   - Plan section: Stage B / `execution_context.py` resolver.
   - Evidence: current `handoff._path_for_execution_host` calls `Path(...).resolve()` against the control host, which cannot correctly normalize a Windows path on POSIX or vice versa.
   - Request: add an implementation note (and a static check or test assertion) that the v1 resolver joins segments using the host profile's native separator without calling `Path.resolve()` on a foreign root.

2. **Make the handoff machine-field trust boundary explicit.**
   - Plan section: Stage B handoff contract / Stage C handoff parsing.
   - Evidence: the new `[handoff]` lines carry host-native paths that a spoofed Discord message could manipulate.
   - Request: in `multinexus/agentd/execution_context.py` and handoff parsing, document that these parsed fields are advisory/metadata only; adapter cwd, session scope, and filesystem access must come from the Coordinate `runtime job claim` response.

3. **Strengthen idempotency conflict detection in `submit_request`.**
   - Plan section: Stage B point 3.
   - Evidence: the idempotency key (`_request_key`) covers platform/destination/message_id/target_agent but not every semantic field in `origin` (e.g. `session_scope_id`).
   - Request: on replay, compare the stored snapshot's origin/scope fields with the replay input and raise a bounded error on conflict, rather than relying solely on the idempotency key.

## Must-fix

None. The plan is bounded, internally consistent, and safe to implement subject to the non-blocking notes above.

## Implementation gate

Approved plan revision for worker bootstrap:

```text
c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e
```

---

[agent-report]
action=review.plan
verdict=APPROVE_WITH_NON_BLOCKING_NOTES
plan_sha256=c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e
session=019f598b-6caf-7000-9bf3-c412a01f6405
must_fix=0
non_blocking_notes=3
