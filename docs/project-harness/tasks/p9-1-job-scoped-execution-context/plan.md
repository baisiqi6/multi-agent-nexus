# Detailed Execution Plan: P9-1 Job-Scoped Execution Context

> This is the first Phase 9 runtime-isolation implementation package. It is a bounded
> cross-repository contract change, not a scheduler, lease system, provider-observation
> rewrite, or multi-line dogfood completion claim.

## Package identity and immutable baselines

- Package: `p9-1-job-scoped-execution-context`.
- Parent: `phase-9-execution-isolation` / P9-1.
- Coordinate start:
  `15020c2204e8e05c6304f6ed83a5fed83ad12eae` on `main == origin/main`.
- MultiNexus start:
  `0d7c716b7dc3620767069e61c3ad168ca78b78dd` on `main == origin/main`.
- Existing Coordinate exception: user-owned untracked `.qoder/` must remain untouched.
- Production at planning time:
  - Coordinate deployed/installed `15020c2`, schema code/DB `11/11`;
  - MultiNexus deployed `0d7c716`;
  - source/deployed checklist SHA
    `f1d3bd7c480fd2641df8950121d1bc97789af028d3e6afbd71ec951d83c66457`;
  - managed services active and server smoke OK;
  - production doctor `projection_ok=true`, `errors=0`, two known superseded-unused
    receipt warnings.
- Fresh test baselines:
  - Coordinate: `1864 passed, 449 subtests passed`, with exactly nine known historical
    CLI rewind/AST failures; direct global Python invocation additionally has a known
    foreign `tests` package collection collision, so the repo `.venv` is authoritative;
  - MultiNexus: `389 passed, 2 skipped, 26 subtests passed`.
- Architect/operator/result reviewer: Codex.
- Independent plan reviewer: a fresh non-Codex reviewer-only session. GLM 5.2 was
  attempted repeatedly on P9-0A6 and timed out before durable verdict; the user
  explicitly authorized Kimi when GLM is too slow. Use a fresh Kimi Highspeed plan
  reviewer unless GLM becomes responsive in a bounded preflight.
- Coding worker: a different fresh Kimi Highspeed session in isolated Coordinate and
  MultiNexus worktrees.
- Provider-native JSONL is primary activity evidence for both reviewer and worker.

## Goal

Make the managed runtime execute each Coordinate job in a versioned, durable,
host-resolved `ExecutionContext`, rather than using one agent configuration's fixed
`work_dir` and bridge-supplied session fields.

The accepted end state is:

1. Coordinate is the authority that snapshots workspace/worktree/harness/branch/
   session/log handles for each managed job.
2. `runtime job claim` returns the exact v1 context and attempt token.
3. MultiNexus `agentd` validates that context and uses it for adapter cwd and session
   storage/resume. Missing or malformed context fails closed before provider execution.
4. Managed handoff/reviewer bootstrap resolution no longer reads Coordinate SQLite
   directly from MultiNexus.
5. Existing public Coordinate imports, CLI parser/help bytes outside explicitly
   approved JSON response additions, lifecycle authority, receipt behavior, and
   MultiNexus legacy non-agentd mode remain compatible.

## Current-state evidence

### Coordinate

- `runtime.submit_request` creates a job with prompt/origin/reply only.
- `runtime.claim_job` returns the raw job and `attempt_token`; it does not resolve a
  workspace host profile or execution context.
- Jobs already carry `branch`, `worktree_path`, `terminal_session_id`, `logs_path`, and
  JSON payload/result fields, so P9-1 does not require a schema migration.
- `workspace_host_profiles` already authoritatively map
  `(workspace_id, host_id)` to host-native workspace/harness/CLI paths.
- `agents.host_id` binds a concrete agent registration to one host.
- The job CRUD region in `db.py` is stable across Slice 4, but extracting it naïvely
  creates a `db <-> job_repository` cycle through workspace/runner lookups and shared
  JSON/path/timestamp helpers.
- Handoff preparation already resolves an execution profile and stores it in
  `worker.handoff.prepared`, but the Discord machine message drops that context.

### MultiNexus

- `AgentdWorker._process_job` sets `work_dir = self.config.work_dir` and reads
  `session_scope_id`/legacy scopes from bridge-controlled origin payload.
- Progress-time session writes still use `self.config.work_dir` even when another cwd
  is passed through the call path.
- `CoordinateRuntimeClient.claim_job` discards every top-level claim field except the
  raw job.
- Managed worker and reviewer handoff paths call `resolve_workspace_path`, which opens
  Coordinate SQLite and runs `SELECT path FROM workspaces` directly.
- Internal MultiNexus session/context SQLite stores are not Coordinate authority reads
  and remain in scope as local runtime state.
- Adapters already accept an explicit `work_dir`; no provider adapter redesign is
  needed.

## Contract: `ExecutionContext` v1

Coordinate owns serialization. MultiNexus owns strict consumption. The claim response
adds a top-level `execution_context` object while preserving existing `job`, `claimed`,
and `attempt_token` fields.

Required v1 fields:

```json
{
  "contract_version": 1,
  "context_id": "sha256:<stable digest>",
  "job_id": "request:<event-id>",
  "workspace_id": "discord-nexus",
  "task_id": "task-or-null",
  "assigned_agent": "mac-omp",
  "host_id": "macbook-local",
  "workspace_path": "/host/native/workspace",
  "worktree_path": "/host/native/worktree-or-workspace",
  "harness_root": "/host/native/harness",
  "branch": "agents/...-or-base-branch",
  "session_scope_id": "task:workspace:task or channel/thread scope",
  "legacy_scope_ids": [],
  "log_handle": {
    "kind": "coordinate_job",
    "job_id": "request:<event-id>",
    "logs_path": null
  }
}
```

Rules:

- All required scalar strings are non-empty except nullable `task_id`, `branch`, and
  `log_handle.logs_path` where the current job genuinely has no value.
- For a task job, Coordinate canonicalizes session scope to
  `task:{workspace_id}:{task_id}`; bridge input may not override it.
- For a non-task job, Coordinate accepts only a bounded non-empty channel/thread/
  request scope from origin. Missing/invalid scope rejects submission before a job is
  created.
- `legacy_scope_ids` is a bounded list of unique non-empty strings; it is compatibility
  input only and never the primary scope.
- `workspace_path` comes from the target agent host's `WorkspaceHostProfile`.
- Explicit job worktree/harness/log paths are mapped from control-workspace-relative
  paths to the host profile using foreign-path-safe joining; otherwise worktree falls
  back explicitly to the host workspace path and harness to the profile harness root.
- Branch precedence: explicit job branch -> task mirror branch -> workspace base branch
  -> null. P9-1 does not provision or switch a worktree.
- `context_id` is a stable SHA-256 over canonical v1 fields excluding itself. It binds
  the snapshot and is included in `job.claimed` evidence.
- The snapshot is stored under `jobs.payload_json.execution_context` before/with first
  successful claim and is returned unchanged on recovery. If the assigned agent's
  current host differs from the snapshot host, claim fails closed; P9-2 will own
  rerouting.
- `attempt_token` remains outside the context because attempts may change while the
  job-scoped paths/scope remain immutable.
- No provider session ID or JSONL liveness semantics are added here; P9-4 owns them.

## Implementation stages

### Stage A — Coordinate job repository seam

Create `src/coordinate/db_support.py` for the minimal pure shared helpers required by
both `db.py` and the extracted job repository:

- canonical JSON serialization;
- UTC timestamp;
- absolute/control-relative path normalization.

Create `src/coordinate/job_repository.py` and move, without semantic changes:

- `create_job`;
- `get_job`;
- `list_jobs`;
- `mark_job_started`;
- `mark_job_completed`;
- `mark_job_cancelled`.

Cycle/compatibility requirements:

- `job_repository.py` may not import `coordinate.db`.
- Workspace path and runner existence checks use narrow SQL reads or a lower shared
  primitive, not callbacks or dependency-injection machinery.
- `coordinate.db` statically imports/re-exports the six historical symbols so existing
  external imports and tests remain valid.
- Runtime/jobs/execution CLI may migrate to `job_repository`, but public identity tests
  must prove `coordinate.db.<symbol> is coordinate.job_repository.<symbol>`.
- Cold-import tests cover both orders and reject a circular import.
- No broad repository framework, base class, ORM, or plugin discovery.

### Stage B — Coordinate context authority and claim contract

Create `src/coordinate/execution_context.py` containing:

- immutable `ExecutionContextV1` value object;
- canonical serialization and digest;
- strict origin scope parsing/bounds;
- host-aware foreign path mapping;
- resolver from workspace, task mirror, agent host, host profile, and job row;
- validator for persisted v1 snapshots.

Change runtime behavior:

1. `submit_request` resolves the target agent host/profile before appending a request or
   creating a job. Missing agent host/profile, invalid session scope, or unsafe path
   fails before managed job creation.
2. Newly created job payload stores the exact context snapshot.
3. Idempotent request replay returns the existing snapshot and rejects payload/context
   conflicts rather than silently changing paths.
4. `claim_job` validates the stored snapshot against job/workspace/assigned agent and
   current host, updates status/attempt with the same CAS behavior, and returns
   `execution_context` plus the existing attempt token.
5. Pre-upgrade pending jobs without a snapshot are backfilled once at claim using the
   same resolver; terminal jobs are never rewritten.
6. `job.claimed` payload records `context_id`, contract version, host, worktree, branch,
   and primary session scope without duplicating prompts or secrets.
7. Report/progress CAS and terminal authority remain unchanged.

Handoff contract:

- `worker.handoff.prepared` remains authoritative and already contains the execution
  profile.
- Discord handoff rendering adds versioned, safely quoted `context_version=1`,
  `workspace_path`, `harness_root`, and `branch` fields derived from that profile/task.
- Existing workspace/task/bootstrap/action fields remain byte-compatible except for
  the deliberate appended fields.
- Windows paths, spaces, quotes, backslashes, and absent optional branch are covered.

No SQLite schema/version change is authorized; schema remains v11.

### Stage C — MultiNexus strict consumption

Create `multinexus/agentd/execution_context.py` with a strict parser/value object for
v1. Do not import Coordinate Python code across repositories.

Change managed runtime behavior:

- `CoordinateRuntimeClient.claim_job` preserves the full claim envelope, validates that
  a claimed job has v1 context, and exposes job/context/attempt together without
  weakening error handling.
- Coordinate CLI errors are no longer converted into a silent empty poll. The agentd
  loop logs a bounded error and backs off; it must not spin or invoke an adapter.
- `AgentdWorker` uses context `worktree_path` as adapter cwd, context
  `session_scope_id`/`legacy_scope_ids` for lookup/resume, and the same context cwd for
  every progress/final session-store write.
- `config.work_dir` remains only a legacy non-agentd/default configuration value. It
  may not be a managed job fallback after rollout.
- Missing, unsupported-version, digest-mismatched, job/agent/workspace-mismatched, or
  unsafe context fails the job closed before provider invocation and reports a bounded
  error through Coordinate using the current attempt token.
- Result JSON includes `execution_context_id` and the non-secret resolved handles used,
  but not raw prompts or credentials.

Managed handoff SQLite removal:

- Extend `CoordinatorHandoff` parsing for the appended v1 path/branch fields.
- In `agentd_mode`, worker/reviewer bootstrap file resolution uses only the
  Coordinate-rendered handoff context or assignment-accept bootstrap payload.
- If the required v1 handoff context/bootstrap is missing, managed mode fails closed;
  it may not call `resolve_workspace_path` or open `coordinator_db_path`.
- Legacy non-agentd mode may retain its existing configured-path/SQLite fallback for
  backward compatibility in this package, but tests must prove the agentd path never
  calls it.
- Do not remove MultiNexus's own session/context SQLite stores.

### Stage D — Cross-repository contract and rollout

- Add byte-identical v1 golden fixture(s) in both repos and pin their SHA-256.
- Coordinate tests produce the fixture from the canonical serializer.
- MultiNexus tests parse the same bytes and reject every missing/extra/wrong-type/
  wrong-version/digest/path/identity mutation required by the contract.
- A small compatibility matrix documents old/new rollout:
  1. deploy Coordinate first: old MultiNexus ignores additive claim fields and still
     runs using its old path;
  2. deploy MultiNexus second: every new claim has v1 context;
  3. pre-upgrade pending jobs are backfilled at first claim;
  4. rolling back MultiNexus remains possible while Coordinate keeps additive output;
  5. rolling Coordinate back after new MultiNexus is forbidden until agentd is rolled
     back, because new agentd fails closed without context.

## Expected code ownership

Coordinate worker-owned paths:

- `src/coordinate/db_support.py` (new);
- `src/coordinate/job_repository.py` (new);
- `src/coordinate/execution_context.py` (new);
- `src/coordinate/db.py`;
- `src/coordinate/runtime.py`;
- `src/coordinate/policy.py`;
- narrowly necessary import sites in `jobs.py` / `execution_cli.py`;
- focused tests/fixtures for db compatibility, execution context, runtime, policy,
  cold imports, and CLI JSON contract.

MultiNexus worker-owned paths:

- `multinexus/agentd/execution_context.py` (new);
- `multinexus/agentd/coordinate_client.py`;
- `multinexus/agentd/worker.py`;
- `multinexus/handoff_handler.py`;
- `multinexus/coordinator_handoff.py`;
- narrowly necessary facade imports in `multinexus/client.py`;
- focused agentd/runtime/handoff/session tests and the v1 fixture.

MultiNexus harness documents may be updated only for this package's progress,
dogfood, closeout, plan/review/bootstrap artifacts, and Phase 9 roadmap status.

Any additional production path requires a worker stop/report and Codex approval; no
dynamic “edit whatever seems useful” permission exists.

## Explicit non-goals

- No executor selection/rerouting, capability scoring, load balancing, or Operator
  override policy (P9-2).
- No capacity counters, worktree mutual exclusion, queue fairness, or leases (P9-3).
- No provider JSONL discovery, heartbeat/liveness classifier, or overload taxonomy
  (P9-4).
- No complete Claude/OhMyPi concurrent project matrix (P9-5).
- No SQLite schema migration, new service, third control plane, ORM, DI container,
  plugin loader, or package split.
- No lifecycle/receipt authority change and no automatic merge/deploy/closeout.
- No adapter-specific context branches; adapters continue receiving `work_dir` through
  the existing base interface.
- No automatic git checkout/worktree creation. Context describes the authoritative
  handle; bootstrap/worker guards still fail closed on branch/path mismatch.
- No deletion of legacy configuration or non-agentd path in this package.

## Required permanent tests

### Coordinate

1. v1 serialize/digest deterministic under key ordering and process restart.
2. task scope canonicalization ignores conflicting bridge primary scope.
3. non-task channel/thread/request scope bounds and legacy-scope dedup/bounds.
4. POSIX and Windows host-profile path mapping, including spaces/backslashes.
5. missing agent host, host profile, workspace, task mirror, and unsafe/non-relative
   mapping fail before job creation where required.
6. explicit job path/branch precedence and honest nullable fields.
7. request replay returns identical context and rejects semantic conflict.
8. claim returns context + attempt token and records the same `context_id`.
9. pre-upgrade pending job backfill; recovery reuses snapshot; host mismatch refuses
   claim without status/attempt mutation.
10. claim CAS race remains single-winner.
11. job repository behavior parity and exact `coordinate.db` identity re-exports.
12. cold import orders are cycle-free.
13. schema remains v11 and no migration bytes change.
14. policy handoff rendering preserves old required fields and safely quotes v1 fields.
15. root argparse/CLI fixture changes only where explicitly expected; no handler
    ownership regression.

### MultiNexus

1. strict v1 fixture parse and mutation rejection matrix.
2. claim client preserves context/attempt and raises bounded errors instead of silent
   empty polling.
3. context cwd overrides deliberately wrong `AgentConfig.work_dir` for call, resume,
   progress session writes, final session writes, and recovery.
4. canonical task scope overrides conflicting origin; legacy scopes remain bounded.
5. missing/invalid/mismatched context never invokes adapter and reports one failed
   result with the current attempt token.
6. two sequential jobs for different workspace/worktree paths do not reuse the same
   stored session or cwd.
7. managed worker and reviewer handoff paths never call direct SQLite resolver.
8. legacy non-agentd behavior remains unchanged.
9. Discord and KOOK request paths preserve job creation/result presentation.
10. Windows/POSIX handoff fields round-trip through machine text parser.

### Cross-repository/static

- v1 fixtures are byte-identical and SHA-pinned.
- Neither repo imports Python modules from the other repo.
- `rg`/AST gate proves no `sqlite3.connect(coordinator_db_path)` or SQL against
  Coordinate tables is reachable from `agentd_mode` managed execution.
- `config.work_dir` has no managed-job call/session-store fallback.

## Validation gates

Worker must run and report:

- `git diff --check` in both repos;
- `python -m compileall` for changed Python modules;
- targeted Coordinate db/runtime/execution/handoff/policy/context suites;
- full Coordinate suite with exact accounting of the nine known historical failures;
- full MultiNexus suite from baseline `389 passed, 2 skipped, 26 subtests passed`;
- cross-repo fixture SHA/byte comparison;
- CLI contract/handler ownership gates;
- static managed-path SQLite/work-dir gates;
- both repos' `HEAD`, branch, upstream, dirty-state, and diff-name boundaries.

No “tests passed” summary is sufficient without command outputs and known-failure
accounting.

## Deployment and dogfood

Operator-owned after Codex result acceptance:

1. Back up production Coordinate SQLite and verify source/backup integrity even though
   schema remains v11.
2. Deploy Coordinate first; verify installed source, schema `11/11`, services, doctor,
   and an additive claim-response smoke with old MultiNexus still running.
3. Deploy MultiNexus second; restart only managed services required by changed code.
4. Run server smoke and breaker scan.
5. Run an isolated sidecar dogfood using production-installed binaries and an isolated
   SQLite/harness/config namespace, not production lifecycle rows:
   - configure the sidecar agent's legacy `work_dir` to an intentionally wrong path;
   - submit/claim a job whose v1 context resolves to workspace A; provider probe must
     report workspace A cwd;
   - submit a second job for workspace B through the same agent instance; cwd/session
     scope must change and no session from A may be reused;
   - inject missing/digest-mismatched/host-mismatched context and prove zero adapter
     invocation plus unchanged attempt/status where the contract requires;
   - exercise one pre-upgrade pending-job backfill;
   - preserve provider-native JSONL/log evidence where available.
6. Re-run full production doctor. No new error/warning is acceptable.
7. Align source/deployed harness projections before terminal receipt; do not force,
   repair, or directly edit JSON/SQLite.

P9-1 sidecar proves the context contract and cwd/session separation. It does not claim
the complete P9-5 concurrent multi-provider matrix.

## Review and stop gates

The plan reviewer must reject if:

- context is computed only in MultiNexus or falls back to config in managed mode;
- context is not persisted/versioned/digest-bound;
- task scope remains bridge-authoritative;
- first/recovery claim can silently change host/worktree/session context;
- job-repository extraction creates a cycle, breaks historical `coordinate.db`
  identity, or introduces a framework;
- missing profile/context can create a poison job, spin the poll loop, or invoke an
  adapter;
- managed handoff still directly reads Coordinate SQLite;
- Windows/foreign path handling is hand-waved through local `pathlib.resolve()`;
- schema, routing, leases, provider observation, or P9-5 scope leaks into this package;
- rollout order lacks fail-closed rollback rules;
- worker can deploy, mutate lifecycle, or broaden paths before Codex acceptance.

The worker must stop and report if current code contradicts any assumed field,
transaction, host-profile, or rollout boundary. Material plan changes require a new
plan SHA, independent review, and approval before implementation resumes.

## Acceptance

P9-1 is accepted only when:

- Coordinate-created/claimed managed jobs carry one immutable, validated v1 context;
- MultiNexus agentd uses only that context for managed cwd/session scope and fails
  closed without it;
- managed handoff has no direct Coordinate SQLite read;
- job repository extraction is cycle-free and public-import compatible;
- both full suites and cross-repo/static gates pass with exact known-failure accounting;
- Coordinate-first/MultiNexus-second deployment and isolated two-workspace sidecar
  dogfood pass;
- production doctor remains `errors=0` with no new warnings;
- Codex result review approves, source/deployed projections align, and the package is
  terminally closed through a consumed receipt.
