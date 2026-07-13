# Project Harness Progress

Harness root: `docs/project-harness/`

## 2026-07-13 — P9-2A executor identity deployment, repair, and closeout review

- Coordinate `eec9b23` is pushed, fully installed, and deployed; source/deployed/
  installed onboarding module hashes match. MultiNexus repair/evidence heads through
  `6e980be` are pushed.
- Real typed job `request:64f42ca6-3b8b-4f78-a56c-c417c6ddeebd` remains `done` with
  immutable binding `sha256:04122c...15e27`, context `sha256:0fad70...869f`, exact
  sentinel, and sent Discord delivery `0e792036...`.
- Exact production-copy rehearsal caught and gated a second erased immutable field
  (`phase`) before production mutation. Amended script SHA `75423566...07e1` passed a
  fresh-copy first run/retry/doctor, then produced the identical accepted production
  repair event `594892d1...`; production doctor is now `projection_ok=true`, errors 0.
- Fresh backup `coord.sqlite3.p9-2a-mirror-fix.20260713T093705Z` is mode 600,
  integrity `ok`, schema v12, SHA `5807973f...2580`. Production integrity is `ok` and
  both services remained active with zero restarts; server smoke passed.
- Closeout request `e3c17b26...` and final review approval `ca0bfd31...` are durable.
  Source lifecycle projection is aligned and ready for the normal host-aware terminal
  receipt. Exact evidence: `tasks/p9-2a-executor-identity-registry/closeout.md`.
- After receipt consumption, P9-2B is the next detailed-plan gate. Ordinary
  `Kimi for Coding` (no `highspeed`) is the preferred coding worker.

## 2026-07-13 — P9-1 deployment and production dogfood

- Coordinate `b732159` and MultiNexus `066ca74` integrated to `main`, pushed, and
  deployed in producer-before-consumer order.
- Backed up the production Coordinate DB before rollout; verified both installed
  runtime import paths and contract v1 after full installs.
- Restarted the server services and four local managed agentd services; bounded-window
  server smoke passed.
- Real `mac-omp` job `request:ced328ec-4a97-4052-817e-bb4ab5adb4fc` claimed and
  completed with a single immutable context id, correct local cwd/worktree, correct
  request scope, exact `P9-1_EXECUTION_CONTEXT_OK` response, and a sent Discord reply.
- Result review, closeout request, and final closeout approval are durable. Receipt
  `e7feda4e-e0d7-4115-9cd0-fe713f87b5d8` completed authorized -> claimed -> applied ->
  task.done -> consumed; P9-1 is closed and P9-2 is the next detailed-plan gate.
- Detailed evidence:
  `tasks/p9-1-job-scoped-execution-context/deployment-dogfood.md`.

## 2026-07-13 — P9-1 Round 4 corrections

- MultiNexus `multinexus/handoff_handler.py`: `parse_coordinator_handoff` keeps
  strict default behavior (returns `None` for missing/relative/unsupported v1
  authority) and adds a keyword-only `diagnostic` flag. Diagnostic mode returns
  a candidate handoff with `context_version=None` for messages that identify
  this agent with a supported action but carry a malformed v1 block; partial
  path/branch fields are cleared so malformed context can never become authority.
- MultiNexus `multinexus/coordinator_handoff.py`: `_try_coordinator_handoff` now
  falls back to the diagnostic parser in `agentd_mode` when the strict parser
  returns `None`. The existing `_has_v1_handoff_authority` gate then emits exactly
  one visible blocker for partial/legacy managed handoffs and returns `True`
  (handled). Legacy non-agentd behavior is unchanged.
- Updated MultiNexus worker integration test: a partial v1 handoff is now
  asserted to return `handled=True`, emit exactly one blocker, and call none of
  assignment accept, bootstrap read, SQLite fallback, agentd submit, or provider
  invocation.
- Added MultiNexus reviewer integration test with the same visible fail-closed
  assertions for a partial v1 review handoff.
- Added diagnostic parser unit tests proving candidate creation for partial v1
  and legacy handoffs, and proving wrong-target messages still return `None`.
- Status: Round 4 corrections applied; stopped for Codex Round 5 review. No
  commit, push, deploy, lifecycle closeout, receipt, or production mutation.

## 2026-07-13 — P9-1 Round 3 corrections

- Coordinate `src/coordinate/handoff.py`: `prepare_handoff` now stores the complete
  `WorkspaceHostProfile.to_dict()` value for targeted handoffs, materializing the
  canonical `workspace_path`/`harness_root` into that copy, and stores
  `execution_profile=null` for untargeted handoffs, restoring the pre-P9-1
  compatibility contract.
- Added Coordinate regression tests for preserved host/CLI/DB/shell/metadata fields
  and the untargeted `null` case; retained the harness-root fallback test.
- MultiNexus `multinexus/handoff_handler.py`: `parse_coordinator_handoff` now rejects
  any v1 block that lacks a non-empty, host-absolute `workspace_path` or
  `harness_root`.
- MultiNexus `multinexus/coordinator_handoff.py`: `_has_v1_handoff_authority` now
  requires both fields; `_try_coordinator_handoff` and `_handle_review_handoff`
  enforce the complete v1 authority check before assignment accept, bootstrap read,
  SQLite fallback, agentd submission, or provider invocation in `agentd_mode`.
- Added MultiNexus parser tests for missing workspace, missing harness, relative
  workspace, relative harness, and valid quoted Windows/POSIX blocks.
- Added MultiNexus worker/reviewer integration tests proving no assignment accept,
  SQLite fallback/bootstrap read, agentd submission, or adapter invocation occurs
  for legacy/partial managed handoffs.
- Verification (Round 3):
  - Coordinate focused suites (`test_execution_context.py`, `test_handoff.py`,
    `test_policy.py`, `test_runtime.py`, `test_job_repository.py`, `test_cli.py`,
    `test_workflow_cli.py`): `525 passed, 88 subtests passed`.
  - Coordinate full suite: `1944 passed, 449 subtests passed`, plus exactly the
    nine known historical CLI-contract/AST failures (unchanged baseline).
  - MultiNexus focused suites (`test_agentd_execution_context.py`,
    `test_coordinator_handoff_runtime.py`, `test_handoff_handler.py`,
    `test_n_plus_m_invariant.py`, `test_handle_via_agentd.py`): `174 passed,
    2 skipped`.
  - MultiNexus full suite: `457 passed, 2 skipped, 26 subtests passed`.
  - `compileall` clean in both repos; `git diff --check` clean in both repos.
  - Cross-repo fixture byte-identical: SHA-256
    `975be64ca2cba84530cf969038cce4c5fb74df0b5f33aed86df9352ec9d12786`.
  - Managed agentd path rejects legacy/partial handoffs before assignment accept,
    bootstrap read, SQLite fallback, or provider/agentd invocation.
- Status: Round 3 corrections applied; stopped for Codex Round 4 review. No
  commit, push, deploy, lifecycle closeout, receipt, or production mutation.

## 2026-07-13 — P9-1 job-scoped execution context implementation

- Implemented in isolated worktrees:
  - Coordinate `~/Documents/Codex/2026-07-10/ni/work/coordinate-p9-1-kimi`, branch
    `agents/mac-omp/p9-1-job-scoped-execution-context`.
  - MultiNexus `~/Documents/Codex/2026-07-10/ni/work/multinexus-p9-1-kimi`, branch
    `agents/mac-omp/p9-1-job-scoped-execution-context`.
- Approved plan SHA-256 verified:
  `c06e7d25a2c308a2600a403e3bff19cd8309b84d6153c21781e2cf7cbcc2ff5e`.
- Coordinate changes:
  - Added `src/coordinate/db_support.py` with canonical JSON, UTC, and host-native
    path helpers.
  - Added `src/coordinate/job_repository.py` for cycle-free, public-import-compatible
    job/event repository access; `src/coordinate/db.py` keeps identical public symbol
    identity.
  - Added `src/coordinate/execution_context.py` v1 value object, deterministic
    SHA-256 digest, canonical snapshot, scope parsing, and host-path resolver.
  - Hardened `src/coordinate/runtime.py` `submit_request`/`claim_job` to bind every
    managed job to a validated v1 context, persist the snapshot, detect semantic
    replay conflicts, and fail closed on missing host profiles or session scope.
  - Updated `src/coordinate/handoff.py` to read execution profiles and emit v1
    handoff fields (`workspace_path`, `harness_root`, `branch`) as advisory
    bootstrap metadata in the human-readable handoff text.
  - Updated `src/coordinate/policy.py` so the real `[handoff]` machine message
    preserves the exact legacy prefix ending with `action=...`, then appends
    safely quoted v1 fields (`context_version=1`, `workspace_path`, `harness_root`,
    `branch`) derived from the prepared handoff event.
  - Materialized a complete canonical handoff execution profile in
    `src/coordinate/handoff.py` `prepare_handoff`, including `harness_root`
    fallback when the host profile omits it, so the rendered handoff context
    is never partial.
  - Added `tests/test_execution_context.py`, `tests/test_job_repository.py`, and the
    byte-identical fixture `tests/fixtures/execution_context_v1.json`.
  - Updated `tests/test_cli.py` runtime flow tests to supply host profiles and
    session scope.
  - Removed the unplanned `tests/__init__.py` package marker.
- MultiNexus changes:
  - Added `multinexus/agentd/execution_context.py` strict parser/value object that
    consumes Coordinate v1 context, validates digest/contract/scope, and rejects
    mutations and missing authority.
  - Updated `multinexus/agentd/coordinate_client.py` to preserve the full claim
    envelope and normalize non-zero exit, timeout, non-JSON output, OS errors,
    and malformed envelopes into bounded `CoordinateRuntimeError` exceptions so
    the agentd loop backs off instead of spinning or invoking an adapter.
  - Updated `multinexus/agentd/worker.py` to use `context.cwd` and
    `context.session_scope_id` for managed sessions; fail closed when context is
    missing or invalid.
  - Updated `multinexus/handoff_handler.py` and `multinexus/coordinator_handoff.py`
    to parse and validate v1 handoff fields (`context_version`, host-absolute
    `workspace_path`/`harness_root`) and avoid direct Coordinate SQLite access in
    `agentd_mode`.
  - Updated managed worker/reviewer handoff paths to fail closed with one bounded
    blocker when bootstrap content is missing after assignment-accept output/file
    resolution, even if valid v1 handoff metadata is present.
  - Added `tests/test_agentd_execution_context.py` and the byte-identical fixture
    `tests/fixtures/execution_context_v1.json`; updated `tests/test_n_plus_m_invariant.py`
    for the new claim-envelope shape.
  - Fixed `multinexus/agentd/coordinate_client.py` missing `typing.Any` import.
  - Strictened both Coordinate and MultiNexus v1 parsers: required scalar fields
    are explicitly non-null, `legacy_scope_ids` must be a unique JSON list (no
    tuples, no duplicates, no duplicate-of-primary-scope).
- Verification (Round 2 corrections):
  - Coordinate focused P9-1 suites: `318 passed`.
  - Coordinate full suite: `1942 passed, 449 subtests passed`, exactly 9 known
    historical CLI-contract/AST failures (unchanged from baseline).
  - MultiNexus full suite: `448 passed, 2 skipped, 26 subtests passed` (baseline
    `389 passed, 2 skipped, 26 subtests passed`).
  - `compileall` clean in both repos; `git diff --check` clean in both repos.
  - Cross-repo fixture byte-identical: SHA-256
    `975be64ca2cba84530cf969038cce4c5fb74df0b5f33aed86df9352ec9d12786`.
  - Static gates pass: managed agentd path uses only Coordinate claim context for
    cwd/session; managed handoff does not open Coordinate SQLite; no config.work_dir
    fallback in the managed worker path.
- Status: Round 2 corrections applied; stopped for Codex Round 3 review. No
  commit, push, deploy, lifecycle closeout, receipt, or production mutation.

## 2026-07-13 — P9-1 Round 1 corrections

- Corrected Coordinate `submit_request` to resolve and validate all authority
  inputs (workspace, agent host/profile, task mirror, session scope, paths)
  before the first durable event/job write.
- Rejected requests for a `task_id` with no task mirror; fixed job/task identity
  binding in `claim_job` validation.
- Hardened semantic replay conflict detection to compare workspace, target agent,
  task, prompt, origin, reply, and the full execution context snapshot.
- Strictened both Coordinate and MultiNexus v1 parsers: exact key sets, no type
  coercion, exact `log_handle` schema, host-absolute paths, rejection of
  traversal/relative/NUL/newline paths, and 64-hex `context_id`.
- Made `ExecutionContextV1.log_handle` immutable with `MappingProxyType` after
  digest binding in both repos.
- Fixed `src/coordinate/policy.py` machine handoff to append real v1 fields
  (`context_version`, `workspace_path`, `harness_root`, `branch`) safely quoted;
  legacy fields preserved byte-for-byte.
- Fixed MultiNexus managed handoff to fail closed when v1 context/bootstrap
  authority is missing; removed `coordinator_workspace_path` fallback in
  `agentd_mode`.
- Normalized all Coordinate CLI failure modes in `coordinate_client.py` into
  `CoordinateRuntimeError` with bounded backoff in `AgentdWorker.run()`.
- Expanded adversarial test coverage for pre-write failures, missing task mirror,
  unsafe path/scope matrix, full replay semantics, claim identity mismatches,
  real policy handoff rendering, and managed no-fallback flows.
- Residual risks: legacy non-agentd handoff still uses Coordinate SQLite; adapter
  base interface still receives `work_dir` through existing contract; Windows/foreign
  root path mapping is string-segment only and not locally resolved.
- Work stopped for Codex result review; no commit, push, deploy, or production
  mutation was performed.

## 2026-07-13 — P9-0A6 post-closeout module review durable closeout

- Coordinate `15020c2204e8e05c6304f6ed83a5fed83ad12eae` was independently
  remeasured; `HEAD == origin/main` and dirty state remained only `.qoder/`.
- Approved plan SHA-256 `825d1aec89877b7cfff1b05938dabde4968d88fd3f29b2baa22359d02d6ee792`
  verified unchanged.
- Physical/AST metrics reproduced: `completion.py` 1,038 lines / 26 funcs / 8 classes;
  `db.py` 1,798 lines / 54 funcs / 6 classes; `transitions.py` 1,391 lines / 28 funcs /
  9 classes.
- Slice-4 churn reproduced: `completion.py` and `transitions.py` unchanged;
  `db.py` `+703/-75` across four commits (agent registry and split-operation work).
- Import direction remains acyclic: `db -> schema`; `completion -> db + harness`;
  `transitions -> completion + db + harness + reconcile`.
- Transaction/authority boundaries preserved: atomic `consume_completion_receipt`
  SAVEPOINT, `sync_workspace_agents` SAVEPOINT, operation-specific harness mutations.
- No extraction candidate satisfies all seven rubric conditions; the accepted decision
  is **no production-code extraction**.
- Routing: job/delivery/event repository candidates to P9-1 job-scoped context;
  agent registry candidates to P9-2 executor routing; split-operation ledger remains
  a Slice-4 primitive; `completion.py` and `transitions.py` retained as cohesive
  authority modules.
- Target-focused tests: `359 passed, 43 subtests passed`.
- `git diff --check` clean; `harnessctl validate` and `harnessctl doctor` passed with
  only known historical warnings/misses.
- Accepted worker documentation was integrated as `8cc3dd1`; terminal checklist files
  were deployed at `5e91632`.
- Documentation-only edits limited to the approved paths:
  - `tasks/p9-0a6-post-closeout-module-review/measurement.md`
  - `tasks/phase-9-execution-isolation/plan.md`
  - `roadmap.md`
  - `progress.md`
  - `dogfood-feedback.md`
- Receipt `15e7d03f-43af-42ab-92cb-dfc5fc06c00b` completed
  authorized/claimed/applied/task.done/consumed with fingerprint
  `9189fc08... -> 9e35da56...`.
- Final production doctor returned `projection_ok=true`, `errors=0`, and two known
  superseded-unused-receipt warnings; server smoke remained OK.
- Durable evidence:
  `tasks/p9-0a6-post-closeout-module-review/closeout.md`.
- Next detailed-plan gate: P9-1 job-scoped execution context.

## 2026-07-13 — Slice 4D projection doctor closeout

- Coordinate `15020c2204e8e05c6304f6ed83a5fed83ad12eae` passed five post-deploy
  adversarial review rounds, was pushed, installed, and deployed with schema v11.
- Independent final verification: `241 passed, 43 subtests passed`; full suite
  `1864 passed, 449 subtests passed` with exactly nine known historical failures;
  ruff/compileall/diff/CLI-byte gates passed.
- Production DB backup
  `/var/backups/coordinate/coord-20260713T020019Z.sqlite3` and source DB both have
  integrity `ok`.
- Full production doctor before and after closeout returned `rc=0`, projection errors
  `0`, and the expected approved S4-D `operation_plan_superseded` info. The original
  S4-C2 lifecycle false positive is absent.
- Receipt `ee38b348-b2fb-4ad1-b9af-dc01f4d6c144` completed
  authorized/claimed/applied/task.done/consumed with fingerprint
  `8447cf7a... -> 86bdeac6...`.
- S4-D and the Slice 4 stage are closed. Next ordered package: P9-0A6 boundary
  remeasurement.
- Slice 4 stage receipt `046f5bf9-62ad-40ea-a828-c2b984531212` was consumed as
  `7e782f24-c38b-49dd-9621-8baecf13f66d`; stage fingerprint
  `bddac5cb... -> 48f93d8a...`. Final production doctor remained `errors=0`.
- Durable evidence:
  `tasks/slice-4d-projection-doctor-evidence/closeout.md` and
  `tasks/slice-4-projection-hardening/closeout.md`.

## 2026-07-13 — Slice 4C2 issue.materialize operation adoption closeout

- Coordinate `a21d946e4d6be78f3f481d38eb2571229a4d3a9f` was approved after three
  request-changes rounds, pushed, installed into the production venv, and deployed.
- Worker and Codex full validation reproduced `1733 passed, 435 subtests passed` with
  exactly nine known historical argparse/AST failures; focused clean gate was
  `417 passed, 1 deselected, 49 subtests passed`; ruff/compileall/diff checks passed.
- Local and deployed-wheel isolated dogfood passed files-only, before-deploy refusal,
  atomic record, sent-delivery exact retry, injected rollback, source conflict,
  integrity, and cleanup checks without production issue/task rows.
- Production backup `coord.sqlite3.before-s4c2-20260712T221137Z.bak` is v11 / `ok`,
  SHA-256 `c0fae9d...04d0`; production remained v11 / `ok` with zero
  `issue.materialize` ledger rows.
- First receipt `924714d9...` failed closed before claim on source/deployed fingerprint
  mismatch. Canonical lifecycle was replayed and deployed; receipt `06a7fa5c...` then
  completed `task.done=050f8c0c...` and `completion.consumed=680e3ec4...`, fingerprint
  `6b25c0b3... -> 05d51ed8...`.
- MultiNexus completion projection `6d913b64a410c7bc3950aff575a7904586e84135`
  deployed; Coordinate PID `653825` and bridge PID `341847` stayed stable with zero
  restarts and repeated `server smoke OK`.
- Durable evidence:
  `tasks/slice-4c2-issue-materialize-operation-adoption/closeout.md`.


## 2026-07-13

### Slice 4B2 Deployed Agent Registry Authority — closeout

- Codex reviewed Kimi commit `1441ad9`, requested three corrections and integrated
  accepted commit `ac12396` to main/origin.
- Local final evidence: 39 focused, 391 full MultiNexus (2 skipped), 83 Coordinate B1;
  strict parity/hash/syntax/compile/diff checks pass.
- Backed up production DB to
  `coord.sqlite3.before-s4b2-20260712T194617Z.bak` with integrity `ok`.
- Deployed source `multinexus.discord` v1: revision 1, ten authoritative, zero legacy,
  projection ten; Coordinate PID/start time unchanged and stable-window smoke passes.
- Empty isolated server sidecar proved same-process v1-to-v2 removal plus conflict and
  rollback rejection, then removed all sidecar artifacts.
- S4-B is closed. Next package: S4-C bound split operations.
- Completion receipt `1cead9e6-ecf3-4914-8813-a13684b5215a` was authorized,
  claimed, applied and consumed; checklist is terminal done/closed.


## 2026-07-13

### Slice 4B2 Deployed Agent Registry Authority — implementation

- Verified cwd/branch/plan SHA (`b9cd5c80b8d84c3e011863a7f2b526ab72c2ec083d664c46b76ad00345299811`).
- Added canonical secret-free authority `config/agent-registry.toml` (source id
  `multinexus.discord`, version 1, ten entries including `pad-jarvis`).
- Added `multinexus/registry_authority.py`: strict authority allow-list, runtime
  projection, canonical SHA-256 matching Coordinate v10, parity verifier CLI.
- Added `scripts/agent_registry_deploy_verify.py`: read-after-write Coordinate DB
  verification using the deployed Coordinate venv.
- Hardened `scripts/deploy-server.sh` with local parity → copy → remote parity →
  authoritative sync → committed-state proof → version marker → restart ordering;
  `--no-restart`/`--skip-install`/`status` semantics preserved.
- Extended `scripts/server-smoke.sh` with read-only v10 registry authority checks
  and active-override failure.
- Updated `agents.toml.example`, `docs/deploy-runbook.md`,
  `docs/project-harness/runbook.md`, `docs/project-harness/dogfood-feedback.md`.
- Tests: 27 parity tests, 6 deploy contract tests, 3 smoke contract tests,
  full MultiNexus 388 tests OK (2 skipped), focused Coordinate B1 registry/daemon
  83 tests OK, `git diff --check` clean.
- Production deploy, PID evidence, and isolated server sidecar closeout remain
  pending Codex operator action; no production DB/SSH/deploy was performed from
  this worker session.

## 2026-07-13

### P9-0A4b Workflow and Assignment CLI Extraction

- Implemented in coordinate worktree (`~/projects/coordinate-p9-0a4b-work`, branch
  `agents/mac-omp/p9-0a4b-workflow-cli`) from reviewed start `4526d09`.
- Extracted 12 handlers (branch allocate; ci/review/merge; assignment
  request/accept/handoff/blocker/unblock/closeout/review-result/mark-done) and 3
  registrars from `coordinate.cli` to new `coordinate.workflow_cli`.
- Dependency direction: `cli -> workflow_cli -> completion_cli`; root keeps
  object-identical aliases for all 12 handlers and 3 registrars.
- Three static registrar calls placed at exact parser seams (branch before PR,
  forge between PR and issue, assignment between runtime and operator).
- Contract fixture regenerated (SHA `43e181...`); A4b rewind proves exclusive
  12-handler ownership and matches P9-0A4a SHA `a7c6e955...`. All 7 cumulative
  layer rewinds and 7 drift tests pass.
- Boundary tests: `tests/test_workflow_cli.py` (37 tests) proving ownership,
  import direction, registration seam order, canonical AST body hashes, and
  mocked service forwarding for all 12 handlers.
- Updated `tests/test_completion_cli.py` ownership assertion: root exposes
  workflow handlers as workflow_cli aliases, receipt handlers as completion_cli.
- 21 top-level commands / 75 leaves / 99 nodes unchanged. Focused 473, full 1562.
- One worker commit `65e80c5`; no deploy (pure CLI refactoring; plan explicitly
  waives runtime deploy).

## 2026-07-12

### S3-C1 durable audit package closed locally

- Human-authorized fast-forward moved local MultiNexus `main` from `d2e7dee` to
  `44e708f` (`docs: record Slice 3 local acceptance`); nothing was pushed.
- Oh-My-Pi session `019f53b1-540b-7000-b0c0-678aabfd52f8` produced the three
  approved artifacts: the source-of-truth audit update, durable local-code-review
  summary, and proposed S3-C2 integration decision.
- Codex approved the result after two factual-correction rounds. Local acceptance
  remains distinct from Coordinate Slice 3 integration, deployment, real multi-host
  smoke, and the Slice 3 umbrella closeout.
- Coordinate lifecycle reconciliation recorded `assignment.requested`,
  `assignment.accepted`, `closeout.requested`, `review.completed`, and `task.done`;
  S3-C1 is `done/closed` with reviewer `codex` and owner lease released.
- Validation: exact reviewed three-file result scope, `git diff --check`, checklist
  validation with the same four historical warnings, and doctor with no new invalid
  artifact. Existing missing `round-2-hardening/plan.md`, `current/task_plan.md`, and
  optional `init.sh` remain unrelated.
- Operator note: the assignment request implicitly created pending live delivery
  `88e08514-f21b-47ed-8316-cebd84d28afd` from workspace defaults even without an
  explicit platform. No sender/pump was active or invoked; the missing local-only and
  cancel/suppress controls are recorded in Coordinate's operator backlog.

## 2026-07-11

### Post-Slice-3 roadmap and plan-gate protocol

- Added `roadmap.md` as the canonical cross-stage sequence for Slice 3 closeout,
  Slice 4 hardening, and Phase 9 multi-project execution isolation.
- Added roadmap-level overview plans for all three stages. These plans intentionally
  constrain goals, dependencies, work packages, non-goals, and acceptance gates; they
  are not executable worker plans.
- Added `templates/detailed-execution-plan.md` for package-level implementation plans.
- Made independent plan review mandatory before bootstrap generation and worker
  assignment. Approval is bound to a stable plan revision; material edits invalidate
  both approval and bootstrap.
- Recorded the 2026-07-11 planning snapshot: MultiNexus `4e2fa46`, Coordinate `main`
  `46a75da`, and Coordinate Slice 3 worker checkpoint `1b86212`.
- No runtime code, service, deployment, production DB, worker assignment, or lifecycle
  state was changed while establishing this roadmap.

### S3-C1 detailed plan review

- Added the package-level detailed plan at
  `tasks/slice-3-c1-audit-integration-plan/plan.md` for a documentation-only durable
  audit, local review-evidence, and S3-C2 integration-decision package.
- Registered local Coordinate `plan.ready`
  `b403c8ce-4a91-4e12-9e52-263d5c699e8b` with content hash
  `b8e342648a434b85`, then requested read-only plan review.
- Generated a reviewer bootstrap without a target agent or real Discord delivery. The
  generated artifact exposed a known path/context bug, so a task-scoped supplement
  identifies the canonical plan and acceptance criteria; the generator gap is recorded
  in Coordinate's operator backlog.
- Claude Sonnet session `49f43a6e-5667-4a4f-8c23-284549049157` independently verified
  the current SHAs, merge base, stable patch ID, changed-path sets, and local reviewer
  evidence. Verdict: approved with no must-fix findings.
- Coordinate recorded `plan.approved`
  `e1b0e261-f852-4d30-b5e1-aba984e77f33`, scope `implementation plan`, bound to the
  exact `plan.ready` revision.
- No coding-worker bootstrap, worker assignment, branch integration, runtime code,
  deployment, service control, production DB access, real `coord-ssh`, or mark-done
  action was performed.

## 2026-06-24

### Phase 8.7 Worker Self-Test Before Closeout

- Implemented in `coordinate` worktree (`~/projects/coordinate`, branch `agents/mac-omp/phase-8.7-worker-self-test`).
- Worker bootstrap (`src/coordinate/handoff.py:_build_worker_bootstrap`) now includes a "Self-Test Before Closeout" section with deploy/e2e rules, `--self-test-evidence` usage, and cross-repo coordinate branch reminder.
- Reviewer bootstrap (`_build_reviewer_bootstrap`) now includes "Verify Worker Self-Test Evidence" with reject criteria.
- `assignment closeout` CLI gained `--self-test-evidence`; `closeout_task` forwards it to `harnessctl` and stores it in the event payload.
- `scripts/harness/prepare_closeout_packet.py` renders `self_test_evidence` in the closeout packet (warning placeholder if empty).
- Added targeted tests: bootstrap content, CLI payload/command, transition args/payload. Full coordinate suite: **1166 tests OK**.
- Updated `docs/project-harness/tasks/phase-8.7-worker-self-test/plan.md` with reviewer round-1 implementation notes (`raw_e2e_output`, self-test failure handling).
- Pushed both coordinate and multinexus branches.
- Self-test evidence: coordinate 1166 tests OK; bootstrap text verified by targeted tests; no server deploy required because this task only changes coordinate/harness protocol code.

## 2026-06-22

### Phase 8.4.3 long-running job recovery implementation

- Coordinate runtime jobs now have explicit recoverable timeout state:
  `timed_out`, `recoverable`, `last_activity_at`, `progress`, and
  `terminal_session_id` are recorded outside the error string. Agentd can
  checkpoint bounded progress/session id through `runtime job progress`.
- Runtime result handling now has deterministic recovery rules: ordinary
  terminal `done`/`failed` rows remain immutable, replay events retain the
  submitted payload and reason, recoverable `timed_out` rows can be reclaimed,
  and late `done`/`failed` results can be accepted once with their response
  delivery.
- Runtime reply delivery normalizes Discord responses to `discord_webhook`,
  matching the currently pumped transport instead of leaving `platform=discord`
  responses pending.
- Multinexus agentd no longer wraps adapter execution in a competing
  equal-budget `wait_for`. The Claude adapter owns first-byte/activity/total
  timeout semantics, emits safe bounded progress and session checkpoints, and
  kills/reaps the subprocess on timeout, cancellation, or unexpected exception.
- Recoverable retries resume the recorded session id from coordinate when no
  local session exists. If that resume fails, worker reports an operator-visible
  failure and does not silently start duplicate fresh work.
- Verification: coordinate full suite passed `1091 tests OK`; multinexus full
  suite passed `325 tests OK (2 skipped)` under a temporary Python 3.12 venv;
  `git diff --check` passed in both repos. No merge, deploy, mark-done, force
  push, harnessctl mutation, or Phase 8.4.2 checkout cleanup was performed.

### Phase 8.4 closeout dogfood — final publish replay and gate probe

- Deployed reviewer-approved coordinate `aaea94d` and multinexus `b655b9c` to
  Tencent Cloud; both services remained active and the remote schema stayed at
  v9.
- A fourth fresh host DB linked real PR
  `https://github.com/baisiqi6/multi-agent-coordinator/pull/1` at commit
  `aaea94df86cf966cf6a835ef22bb2646f2588e94`. Immediate replay returned
  `event_created=false` and `mirror_updated=false`; no second PR was created.
- Remote event `bd9d8103-0236-4fbe-b77f-7780916ff8ca` produced sent Discord
  delivery `47a192f3-41c8-4436-a0d2-ed0b4c29c8e4` with platform message
  `discord_bot:1518407243366793217`. The PR remains open and unmerged.
- Real `gh pr checks` exposed the no-checks exit-code shape. Coordinate now
  records that exact response as `ci.pending`; host-side review remained
  `pr_review.required`, and merge gate correctly remained closed with
  `human_gate_required=true`.
- Direct remote CI/review/head refresh remains unavailable because the runtime
  server intentionally has no `gh` or GitHub token. This is recorded as a
  deferred host-side driver/record-sink requirement rather than weakening the
  runtime credential boundary.
- The persistent reviewer rejected the first no-checks parser because a
  substring match could hide auth/network errors. The approved implementation
  accepts only rc=1, empty stdout, and a full match of GitHub's two no-checks
  messages; auth/network/403 lookalikes and rc=8 fail with zero CI events.
- Final deployed heads are coordinate `6b0f0fa` and multinexus `f5e0350`.
  Fresh host 5 linked PR #1 at the final coordinate SHA, then immediately
  replayed with `event_created=false` and `mirror_updated=false`. A final local
  gate probe recorded `ci.pending` and `pr_review.required`; merge readiness is
  false and `human_gate_required=true`.

### Phase 8.4.1 boundary refactor

- Created separate `agents/codex/phase-8.4.1-boundary-refactor` branches from
  the reviewed/dogfooded heads; PR #1 remains attached to the closeout branch
  and was not updated or merged by the refactor.
- coordinate extracted schema migration, host publish, remote recording, and
  PR CLI boundaries while retaining `coordinate.db`, `coordinate.prs`, and
  `coordinate.cli` facades. PR tests were split into feature-specific files.
- multinexus extracted coordinator handoff/lifecycle and the central agent
  request workflow behind the existing `DiscordClient`/`Agents` types. Added
  explicit inheritance and chunking contract tests.
- Before reviewer submission, coordinate full suite passed 1084 tests and
  multinexus passed 314 tests (2 skipped); both harness validate/doctor and
  diff checks passed.
- Refactor review round 1 found incomplete compatibility surfaces in both
  repositories. Old `coordinate.db` schema helpers, `coordinate.prs` publish
  helpers, `multinexus.client` handoff helpers, and `cogs.agents` exception/UI/
  correlation hooks are re-exported again. Critical record, lifecycle, and
  request workflows now resolve injected helpers through those historical
  facades at runtime. New import-surface and patch-effect tests bring the final
  suites to coordinate 1087 and multinexus 319 (2 skipped).
- Refactor review round 2 found the last three compatibility omissions:
  record action constants, Discord message-length constant, and the historical
  handoff chunk monkeypatch hook. All were restored with patch-effect coverage.
  The persistent reviewer then returned `APPROVED` with no actionable P1/P2.
- Final verification: coordinate 1087 OK; multinexus 319 OK (2 skipped);
  both harness validate/doctor and diff checks pass. Refactor branches are
  pushed but not deployed or merged. Real PR #1 remains open on the separate
  Phase 8.4 closeout branch.
- Remote lifecycle closeout produced durable events: `closeout.requested`
  `7feeec89-17b9-4042-aeef-37a3e136fba6`, approved `review.completed`
  `46033db5-401a-4dd6-950b-afbec4288576`, and `task.done`
  `09e6a173-e998-4908-a8df-0777d09e8ece`.
- Post-closeout inspection caught reconcile erasing the PR binding. The same
  reviewer rejected the first preservation patch until branch/PR/metadata
  rebinds also failed closed, then APPROVED. The fix is present on refactor
  coordinate `63cdafb` and backported/deployed as closeout `cf4f1e9`.
- Fresh host 6 linked PR #1 at `cf4f1e9`; remote reconcile then reported the
  closed task unchanged with PR/publish metadata intact, and immediate replay
  returned event/mirror false/false. The PR remains open and unmerged.

### Phase 8.4 operator closeout — correctness pass

The operator resumed Phase 8.4 from Round 7 on dedicated
`agents/codex/phase-8.4-closeout` branches. This pass reproduced and fixed four
cross-host/schema defects before starting the independent review loop:

- Schema v9 task-index replacement is now version-gated. Opening an existing
  v9 DB performs no task-index `DROP`/`CREATE` statements.
- The v8-to-v9 destructive index replacement runs under `BEGIN IMMEDIATE`; a
  failed rebuild restores both prior indexes, and a concurrent duplicate
  branch writer blocks until the rebuilt unique index rejects it.
- A fresh host DB can follow a remote `link_existing` preflight. The remote
  expected PR URL is validated against the repository, GitHub discovery still
  verifies URL/head SHA/base, and the successful link repairs the local mirror.
- Mirror repo/commit identity is read through one compatibility helper that
  supports legacy top-level payloads and current `publish_metadata` rows.
  Sink-produced repo/commit mismatches now fail remote preflight.
- Malformed successful preflight envelopes fail closed: unknown modes and
  `link_existing` without `expected_pr_url` return code 1 before any `gh` call.

Validation before review:

- coordinate full suite: `1064 tests OK`.
- multinexus full suite: `314 tests OK (2 skipped)` using the project venv.
- Both `harnessctl validate` commands pass.
- Both `harnessctl doctor` commands exit 0 with pre-existing optional/current
  pointer misses only.
- Both `git diff --check` commands are clean.
- No GitHub write, deploy, merge, lifecycle closeout, or remote DB mutation was
  performed in this correctness pass.

### Phase 8.4 operator closeout — independent review round 1

The persistent reviewer rejected coordinate `8e39578` with two P1 findings
and one P2 test gap. The operator reproduced each issue before fixing it:

- On Python sqlite versions without `Connection.autocommit`, the prior
  `isolation_level=None` fallback let `append_event()` commit before mirror
  upsert. A simulated mirror failure left a permanent `pr.created` event.
  `append_event` and `upsert_task_mirror` now expose compatibility-preserving
  `commit=False`; the record sink owns both writes through one SAVEPOINT on
  every supported Python version.
- A hostile/stale success envelope could previously record an invalid repo,
  branch, SHA, head/base, or non-GitHub PR URL. The server now accepts a
  created/linked result only when workspace identity matches, all GitHub facts
  are canonical, `head_ref == repo_owner:branch`, the PR URL belongs to the
  repository, and `remote_sha == reported_commit`. Blocked results may still
  preserve invalid worker input for audit but never update the mirror.
- The fresh-host test now sends the linked result back to the independent
  remote DB twice, verifies the first linked event/mirror update, and verifies
  the second replay reuses the event without mirror drift.

Review-fix validation in progress: targeted tests pass on the normal test
runtime and the system Python sqlite semantics without `autocommit`; coordinate
full suite passes `1065 tests OK`. No GitHub write or deployment occurred.

Round 2 found one remaining P2 in committed head `b8c4081`: workspace identity
was enforced for created/linked but not blocked/push-required audit events. The
check now applies before action branching, so the envelope workspace must equal
the record target for every action. A mismatched blocked envelope writes zero
events. Coordinate full suite after this final fix passes `1066 tests OK`.

The persistent reviewer approved coordinate `8013f2f` / multinexus `b050f5b`.
Real dogfood then deployed both commits, migrated the Tencent DB from schema 7
to 9 with the expected partial branch/global PR indexes, registered this task,
and created `https://github.com/baisiqi6/multi-agent-coordinator/pull/1` through
remote preflight -> host GitHub create -> remote record sink. A second fresh
host exposed a real CLI mismatch: same-repo `gh pr list --head` needs a bare
branch, not `owner:branch`, so replay safely blocked without duplicate create.
The bounded fix and commit-advance replay support are under review before the
dogfood retry. Deployment also surfaced and fixed a missing `.coordinator`
server-local exclusion in `deploy-server.sh`.

Dogfood-fix review round 1 rejected the initial bare-branch normalization:
same-name fork PRs could appear in the candidate list. The follow-up requests
head repository/owner/cross-repository metadata, scans up to 100 candidates,
and selects only an exact same-repo candidate matching expected SHA and base.
Fork-only candidates now fail closed. Real read-only discovery still resolves
PR #1 with the new metadata checks.

Dogfood-fix review round 2 found two adjacent gaps: candidate PR URLs were not
canonicalized, and GitHub may preserve mixed-case owner/repository names. The
shared validator now enforces a query-free HTTPS GitHub pull URL scoped to the
target repo, while repository identity comparisons use case-insensitive GitHub
semantics. A full first-publish regression proves malformed URLs never bind a
task mirror. Real PR #1 still passes the stricter read-only discovery.

Dogfood-fix review round 3 fuzzed the canonical URL boundary and found Unicode
digits plus empty `?`/`#` delimiters still passed. PR numbers now use ASCII
digits only, the raw URL rejects all query/fragment delimiters, and parser
errors are normalized to `invalid_pr_url`. Remote sink regressions assert zero
event/mirror writes for every edge case.

Dogfood-fix review round 4 found that Python URL parsing normalizes raw control
characters before validation. The validator now rejects non-ASCII input and
all whitespace/C0/DEL characters before parsing, and requires a positive PR
number without leading zeros. Remote sink fuzz regressions again require zero
event/mirror writes.

Dogfood-fix review round 5 found one final generic-parser normalization case:
an empty path-params delimiter. Because GitHub PR URLs have a deliberately
narrow grammar, validation now uses an exact full-string ASCII pattern instead
of `urlparse`, followed by case-insensitive repo binding. This removes the
entire delimiter-normalization class rather than adding another parser patch.

Dogfood-fix review round 6 found repo dot-segments were still valid according
to the upstream repo regex. Repo validation now rejects `.`/`..` components;
branch validation was hardened at the same boundary against path traversal,
empty components, hidden/`.lock` components, double dots, and invalid endings.
Remote sink tests cover matching malicious repo+URL pairs with zero writes.

Dogfood-fix review round 10 approved coordinate `6bec11e` / multinexus
`06033bb`. Both were deployed; the new deploy exclusion removed the prior
`.coordinator` deletion warning. A third fresh host successfully followed
`link_existing` for PR #1 at commit `6bec11e`; the remote `pr.linked` event and
publish metadata match the live PR head. This live replay exposed one response
accuracy issue: `mirror_updated` was false despite a metadata update. The sink
now derives that flag from the DB upsert status and prefers current nested
publish metadata over legacy top-level identity.

Post-replay review round 1 found an idempotent publish replay could regress
`tasks.last_event_id` after a newer lifecycle event. Replay now compares event
row order and preserves the newer pointer while retaining its repair behavior
for missing PR/metadata. The no-side-effect replay contract has an explicit
publish/lifecycle/replay regression.


### Phase 8.4.4 Host-Aware Mark-Done (Reconcile Drift)

- Implemented host-aware `mark-done-files` and `mark-done-record` in coordinate
  (branch `agents/mac-omp/phase-8.4.4-host-aware-mark-done`, commit
  `8c31416`).
- **mark-done-files**: writes local `mvp-checklist.json` (status=done,
  workflow=closed), no DB connection, /opt guard without `--allow-runtime-copy`.
  Privileged operator tool that bypasses the review gate (explicitly documented).
- **mark-done-record**: inline `append_event('task.done')` via cloud DB,
  never calls `adapter.run_mutation` (zero file touches). Wide-match
  idempotency scans all prior `task.done` by workspace+task (ignoring actor).
  Gate diagnostic from /opt checklist is present but non-blocking.
- Runbook updated with reconcile drift standard flow and legacy race warning
  (do not run legacy `assignment mark-done` between files/record).
- Coordinate full suite: 1141 tests OK (17 new + pre-existing baseline 1087).
- Multinexus full suite: 333 tests, 8 pre-existing asyncio errors, 2 skipped.
- `harnessctl validate` passed; `harnessctl doctor` exited 0 with pre-existing
  optional misses; `git diff --check` clean.
- End-to-end dogfood confirmed: mark-done-files (checklist update + idempotent
  no-op) → mark-done-record (event created + wide-match idempotent with
  different actor+hint).
## 2026-06-18

### Phase 8.4 — review-fix round (2026-06-19, address codex findings)

Codex reviewed the Phase 8.4 commit `73a439a` and surfaced three P1
findings. The fix commit `54788ae` (coordinate) addresses all three:

- **P1-A (host/server split inverted)**: `--event-cli-path` was forwarding
  the entire `pr publish` argv to a remote coord CLI, which on Tencent
  Cloud has no `gh` and would surface GH_MISSING. Replaced the
  `_publish_via_event_cli` wrapper with `_forward_publish_event`, which
  forwards a single `event append <type> ...` argv per emitted event.
  The remote coord CLI is now strictly a durable event sink. `gh` lives
  on the coding host only.
- **P1-B (blocked paths wipe mirror payload)**: `_emit_publish_event`
  no longer calls `mirror_branch_update`. Blocked / push.required paths
  record the event only; the trusted branch / payload in the mirror is
  left untouched. All `existing[...] ['payload_json']` reads switched
  to `existing.get('payload')` (the post-`row_to_dict` name). Mirror
  conflict is recorded as `publish.blocked` without altering the
  existing mirror row.
- **P1-C (discover PR without SHA / base check)**: `discover_open_pr_for_head`
  now takes `expected_head_sha` and `expected_base` and rejects
  mismatches with `GitHubCommandError(reason="discovery_mismatch")`,
  which `publish_pr` records as `publish.blocked`. The blocked payload
  carries the requested `head_ref` and `base` so the operator sees what
  was requested vs. what GitHub returned. Policy text + Discord embed
  now surface `Head` / `Base` for `publish.blocked`.

Validation:

- coordinate `1002 tests OK` (993 + 9 review-fix regressions).
- multinexus `314 tests OK (2 skipped)`.
- `git diff --check` clean on both repos.
- `harnessctl validate` passes on both repos.
- No real GitHub write. No deploy. No merge.

Plan and bootstrap updated:

- `docs/project-harness/tasks/phase-8.4-worker-push-pr-creation/plan.md`
  Boundary Review Q1 + Q2 rewritten to match the corrected semantics.

Reviewer still has not written `review.completed`; this round is again
requesting review (no `task.done` written).

### Phase 8.4 — review-fix round 4 (2026-06-21, address codex P1/P2)

Codex reviewed the Phase 8.4 review-fix commit `54788ae` and surfaced
three P1 + one P2 findings. Fix commits `0bb3816` (coordinate) and
`9cc5e33` (multinexus) address all four:

- **P1 (preflight bypassable)**: `--preflight-event-cli-path` was optional
  and `--event-cli-path` alone allowed direct PR creation without a
  remote mirror preflight. Fixed by defaulting the preflight path to the
  event-cli path, and by strictly checking `ok is True` instead of
  truthiness (the string `"false"` is truthy). The help text now documents
  the mandatory coupling.
- **P1 (SAVEPOINT lock leak)**: The exception path rolled back to the
  savepoint but never released it, leaving the transaction lock held on
  Python <3.12 or autocommit-capable connections. Fixed by releasing the
  savepoint after rollback. Also added Python 3.10/3.11 compatibility by
  falling back to `isolation_level=None` when `autocommit` is unavailable.
- **P1 (cross-task uniqueness bypass)**: `record_publish_result` and
  `record_publish_preflight` only checked the current task mirror, so a
  record-only sink could attach the same branch or PR URL to multiple
  tasks in the same workspace. Added `_cross_task_conflict_check` mirroring
  the protections in `link_pr` and enforced it in both preflight and result
  sinks.
- **P2 (audit fields dropped)**: `PublishResult.to_dict()` omitted
  `remote`, `validation`, `message`, `detail`, so the server-side payload
  recompute lost worker audit context. Extended the dataclass and added
  round-trip serialization; `_record_event_payload` now copies
  `blocked_detail` into `publish.blocked` payloads.

Validation:

- coordinate full suite `1033 tests OK`.
- multinexus full suite `314 tests OK (2 skipped)`.
- `harnessctl validate` passes on both repos.
- `git diff --check` clean on both repos.
- No real GitHub write. No deploy. No merge.

Plan and documentation updated:

- `docs/project-harness/tasks/phase-8.4-worker-push-pr-creation/plan.md`
  removes stale `publish_pr_via_gh` reference and lists the host
  orchestrator, remote sink, and remote preflight in the correct order.
- `docs/project-harness/tasks/phase-8.4-worker-push-pr-creation/worker-bootstrap.md`
  documents `publish-preflight` and the automatic preflight triggered by
  `--event-cli-path`.
- `coordinate/docs/runbook.md`,
  `coordinate/skills/coordinate-operator/references/command-reference.md`,
  and
  `coordinate/skills/coordinate-operator/references/github-integration.md`
  now describe the preflight guarantee, the `--preflight-event-cli-path`
  override, and the server-side `publish-record` / `publish-preflight`
  subcommands.

Reviewer still has not written `review.completed`; this round is again
requesting review (no `task.done` written).

### Phase 8.4 — review-fix round 5 (2026-06-21, address codex P1/P2)

Codex reviewed the Phase 8.4 review-fix commit `0bb3816` and surfaced
two P1 + one P2 findings. Fix commit `f3110b3` (coordinate) addresses
all three:

- **P1 (cross-task uniqueness TOCTOU)**: `_cross_task_conflict_check` ran
  outside the record-only sink transaction, so two concurrent
  `record_publish_result` calls could both observe no conflict and then
  both bind the same branch or PR to different tasks. Fixed by adding
  unique indexes `idx_tasks_workspace_branch` and `idx_tasks_workspace_pr`
  on the `tasks` table (schema version 8) and moving the mirror conflict,
  cross-task, and same-task rebind checks inside the SAVEPOINT. The
  resulting `sqlite3.IntegrityError` is caught and surfaced as
  `RecordPublishError(reason="cross_task_conflict")`, with no half-state
  left on disk.
- **P1 (same-task PR silent rebind)**: `publish_pr` created/linked paths
  would overwrite a task mirror's existing PR with a new one, violating
  the same invariant enforced by `link_pr`. Added
  `_check_existing_pr_rebind` and applied it in `publish_pr` (before
  writing `pr.created`/`pr.linked`) and in `record_publish_result` (inside
  the SAVEPOINT). A task with `/pull/1` now returns
  `publish.blocked (pr_already_linked)` instead of silently becoming
  `/pull/2`.
- **P2 (created/linked audit fields dropped)**: `PublishResult.to_dict()`
  and the success-path payloads omitted `remote` and `validation`, so the
  remote sink lost worker audit context for created/linked events.
  `_finalize_link` and `_finalize_created` now return `remote` and
  `validation` in `PublishResult`, and `_record_event_payload` copies them
  into `pr.created`/`pr.linked` payloads.

Validation:

- coordinate full suite `1043 tests OK` (1033 + 10 Round 5 regressions).
- multinexus full suite `314 tests OK (2 skipped)`.
- `harnessctl validate` passes on both repos.
- `git diff --check` clean on both repos.
- No real GitHub write. No deploy. No merge.

Reviewer still has not written `review.completed`; this round is again
requesting review (no `task.done` written).

### Phase 8.4 — review-fix round 6 (2026-06-22, address codex P1/P2)

Codex reviewed the Phase 8.4 review-fix commit `f3110b3` and surfaced
two P1 + one P2 findings. Fix commit `f2ec9f8` (coordinate) addresses
all three:

- **P1 (schema v8 migration fails on production DB)**: The schema version 8
  unique indexes on `(workspace_id, branch)` and `(workspace_id, pr)` were
  global, so migrating a v7 database with duplicate closed-task branches
  (e.g. `discord-nexus / feature/multi-bot` shared by two closed tasks)
  raised `IntegrityError`. Replaced the global unique indexes with partial
  unique indexes `WHERE phase IS NOT 'closed'`, both in the initial
  `CREATE TABLE` block and in the v7→v8 migration path. Active tasks still
  enforce cross-task uniqueness; closed-task historical reuse is allowed.
- **P1 (preflight allowed host to create duplicate PR)**: `record_publish_preflight`
  only checked mirror conflict and cross-task branch conflict. If a task's
  remote mirror already had `/pull/1`, the host would still run `gh pr create`
  and only be rejected later by the record sink. Added a same-task PR probe
  to `record_publish_preflight`: when the mirror already has a PR, preflight
  returns `ok=false, reason=pr_already_linked, pr_url=<existing>` *before*
  any GitHub write. The host CLI already treats any `ok=false` preflight as
  a hard failure and skips all `gh` calls.
- **P2 (IntegrityError not converted to cross_task_conflict)**: SQLite reports
  unique-constraint failures as `UNIQUE constraint failed: tasks.workspace_id,
  tasks.branch` — the message does not contain the index name. The previous
  code matched on `idx_tasks_workspace_*`, so the raw `IntegrityError` leaked
  out instead of becoming `RecordPublishError(reason="cross_task_conflict")`.
  Changed the exception translator to match the canonical column combinations
  (`tasks.workspace_id, tasks.branch` and `tasks.workspace_id, tasks.pr`),
  and added regression tests that bypass the application-level check to
  guarantee the DB-level guard is exercised.

Validation:

- coordinate full suite `1049 tests OK` (1043 + 6 Round 6 regressions).
- multinexus full suite `314 tests OK (2 skipped)`.
- `harnessctl validate` passes on both repos.
- `git diff --check` clean on both repos.
- No real GitHub write. No deploy. No merge.

Reviewer still has not written `review.completed`; this round is again
requesting review (no `task.done` written).

### Phase 8.4 — review-fix round 7 (2026-06-22, address codex P1/P2)

Codex reviewed the Phase 8.4 review-fix commit `f2ec9f8` and surfaced
one P1 + three P2 findings. Fix commit `011df4a` (coordinate) addresses
all four:

- **P1 (second run with existing PR was not idempotent)**: `record_publish_preflight`
  returned `ok=false, reason=pr_already_linked` for any task whose mirror
  already had a PR, so the host CLI exited 1 on the second execution.
  Phase 8.4 requires the second run to discover and link the existing PR
  read-only, succeeding without another `gh pr create`. Changed preflight
  so that, when the worker's repo/branch/commit are consistent with the
  mirror, it returns `ok=true, mode=link_existing, expected_pr_url=<url>`.
  Added `publish_pr_existing()` which performs only read-only `gh pr list`,
  verifies URL/SHA/base match, and writes `pr.linked` + updates the mirror.
  The CLI routes preflight `link_existing` to this path and still forwards
  the linked result to the remote record-only sink. URL/SHA/base mismatch
  returns `publish.blocked` with exit 1.
- **P2 (schema v8 was not upgraded to partial index)**: Round 5/6 shared
  schema version 8, so environments that already ran Round 5 kept the
  global `(workspace_id, branch)` index even though Round 6 code created
  partial indexes with `IF NOT EXISTS`. Bumped `SCHEMA_VERSION` to 9 and
  added an explicit `DROP INDEX IF EXISTS` + recreate for both indexes in
  the migration path, guaranteeing partial branch + global PR shapes.
- **P2 (active-only rule not applied in application layer)**: Database
  allowed active tasks to reuse a closed task's branch, but
  `_cross_task_conflict_check` and `allocate_branch` still treated closed
  tasks as branch conflicts. Updated both queries to include
  `AND phase IS NOT 'closed'`, matching the partial index semantics.
- **P2 (PR URL should not be widened with branch)**: Production data only
  had duplicate closed branches, not duplicate PRs. PR URLs are immutable
  historical associations, and `link_pr` already forbids cross-task reuse.
  Reverted the PR unique index to global `(workspace_id, pr)`; only the
  branch index is partial.

Validation:

- coordinate full suite `1057 tests OK` (1049 + 8 Round 7 regressions).
- multinexus full suite `314 tests OK (2 skipped)`.
- `harnessctl validate` passes on both repos.
- `git diff --check` clean on both repos.
- No real GitHub write. No deploy. No merge.

Reviewer still has not written `review.completed`; this round is again
requesting review (no `task.done` written).

### Phase 8.4 — Worker Push And PR Creation (vertical slice, source-of-truth only)

- **Scope**: close the GitHub automation loop from a worker host's
  `[agent-report] action=done` to a real PR, without requiring the Tencent
  Cloud coordinate server to own a local checkout of the worker branch.
- **Branch**: `agents/mac-claude/phase-8.4-worker-push-pr-creation` (both
  repos; base = `origin/agents/mac-claude/phase-8-preflight-dogfood-cleanup`).
- **Plan + bootstrap**:
  `docs/project-harness/tasks/phase-8.4-worker-push-pr-creation/plan.md`,
  `.../worker-bootstrap.md`.
- **Coordinate changes**:
  - `src/coordinate/github.py`: new `fetch_remote_ref`,
    `discover_open_pr_for_head`, `create_pr`, and strict
    `validate_repo/branch/commit/pushed`. All `gh` calls go through an
    injected runner.
  - `src/coordinate/prs.py`: new `publish_pr()` orchestrator emitting
    `pr.created` / `pr.linked` / `push.required` / `publish.blocked`.
    Decision tree: validate → mirror conflict → `pushed=false` → remote
    ref lookup → SHA mismatch → discover existing PR → create-or-link.
    Idempotency keys embed `(workspace, task, repo, branch, commit,
    action)`, so reruns never duplicate events and never call
    `gh pr create` twice.
  - `src/coordinate/daemon.py`: `AgentReport` and `agent.reported`
    payload gain optional `repo/branch/commit/remote/pushed/validation`.
    Old reports (summary/reason only) keep working.
  - `src/coordinate/policy.py` +
    `src/coordinate/discord_rendering.py`: 3 new visible events added
    to `SUPPORTED_EVENT_TYPES` with stable text renderers and Discord
    embed colour mappings.
  - `src/coordinate/cli.py`: `pr publish <workspace> --task-id ...
    --repo ... --branch ... --head-owner ... --base ... --title ... --body
    ... --commit ... --pushed true|false [--event-cli-path PATH]`.
- **Host/server split**: server path is record-only and never calls
  `gh`. Host wrapper (`coord-ssh` on Mac, `coord-ssh-win.py` on Windows)
  is the only thing that invokes `gh api` / `gh pr list` /
  `gh pr create`. `--event-cli-path` mirrors the Phase 8.1 issue-scan
  pattern.
- **Validation**:
  - coordinate `993 tests OK` (805 pre-existing + 188 new for Phase 8.4).
    Targeted modules (`test_prs`, `test_github`, `test_cli`, `test_daemon`,
    `test_policy`, `test_discord_rendering`, `test_ci`, `test_reviews`)
    all green; `merge gate` / `ci check` / `review check` tests
    unchanged green.
  - multinexus `314 tests OK (2 skipped)` (no runtime change).
  - `git diff --check` clean on both repos.
  - `scripts/harness/harnessctl validate` passes on both repos.
- **No real GitHub write operation was performed** (no `gh pr create`,
  no `gh api POST`). Only read-only smoke is allowed for Phase 8.6
  end-to-end, after operator explicit authorization.
- **No deploy**, **no merge** of the long-lived Phase 8 branch.

### Harness state preflight repair (this task)

- `docs/project-harness/mvp-checklist.json`: changed
  `phase-8.3.2-a0-materialization-dogfood.priority` from the invalid
  value `high` to `p1` so the local `harnessctl validate` no longer
  fails. This is a minimal, evidence-driven operator repair — see
  implementation handoff §7.
- Added the canonical checklist item for `phase-8.4-worker-push-pr-creation`
  with explicit `priority=p1`, `owner=mac-claude`, blocked_by
  `phase-8.3.2-a0-materialization-dogfood`. This task does **not**
  forge `issue.spotted` / `issue.triaged` events; remote registration
  remains an operator step.
- The local checklist still shows 8.3.1 / 8.3.2 / host-profile smoke
  as `todo` even though the remote DB has `task.done` for all three
  (`2544db0f`, `b905a4be`, `1682cf34`). That drift is intentional and
  not silently repaired here — reconciliation is the operator's job.

### Phase 8.3.1 — harness source-of-truth boundary + sidecar workspace rules

- Task `phase-8.3.1-harness-source-boundary` (branch `agents/mac-claude/phase-8-preflight-dogfood-cleanup`). Turns the Phase 8.3 host-aware materialize decision into documented, tested, worker-facing rules. Coordinate-side work (test + docs) lands in the `coordinate` repo; this entry records the multinexus-facing documentation.
- **Rule** (added to `scope.md` Boundaries, mirrored in coordinate `docs/runbook.md`): multinexus is an internal repo → harness lives in-repo and is committed (`workspace.path` parent of `workspace.harness_root`). External/upstream repos use a **sidecar `harness_root` outside the checkout** so upstream PRs stay free of our harness files. `workspace.path` and `workspace.harness_root` are intentionally separate. Server `/opt/multinexus` is a deploy artifact (tar+ssh, no git history), not source — never edit harness state there directly.
- **No multinexus code/runtime change**: the worker bootstrap already exposes both `execution_workspace_path` (cd/git) and `execution_harness` (harness root) as separate values via the coordinator host profile, so a coding-host worker is never pointed at `/opt/multinexus`. This was the A0 fix recorded in dogfood-feedback #11/#14/#15; 8.3.1 only codifies it.
- Verification: no multinexus source changed, so no multinexus test run needed. Coordinate suite 805 OK (incl. new sidecar materialize-files test). `git diff --check` clean on both repos.
- Open risk: none. Documentation + cross-repo test only; no deploy, no service change.

### Phase 8.3.2 — A0 issue materialization dogfood closeout

- **目标**: 从一条 GitHub issue 走完 host-aware 全链路 — issue scan → triage accept → `materialize-files`（Mac 写 checklist）→ deploy → `materialize-record`（coord-ssh 写 DB，不碰 `/opt` 文件）→ plan approval → Discord handoff → worker 实现 → review → closeout。本条是上一轮 worker job 遇 Claude API `529 Overloaded` 后的重试收口（accept 已在首轮回退前记录，本次不再重复 accept）。
- **Source**: GitHub issue `baisiqi6/multi-agent-nexus#5`（临时 operator-owned dogfood issue）。issue body 一律标 `content_trust=untrusted`，不作 worker / system prompt；实现指令以本仓 `tasks/phase-8.3.2-a0-materialization-dogfood/plan.md` 为唯一来源。
- **Materialization 链路证据**（远端 coordinate DB，workspace `discord-nexus`，actor `codex`，2026-06-18 UTC）：
  - `04:59:55Z` `issue.spotted` `ae7c7493-54b8-4985-b54e-12dcce1bce8b` — Mac 本地 `gh` + `/Users/yinxin/.local/bin/coord-ssh` 写入，`content_trust=untrusted`。
  - `05:00:17Z` `issue.triaged` `a28062a2-e576-4744-b2ec-6478975a95cd`（decision `accept`）→ task mirror `phase-8.3.2-a0-materialization-dogfood`。
  - `05:00:51Z` Mac checkout `mvp-checklist.json` 写入对应 checklist item — 由 `materialize-files` 生成，非手工编辑。
  - `05:01:32Z` `plan.ready` `f0f32d89-b543-49b2-a9e1-796f62cb2b87` + `issue.materialized` `60c612ff-2a83-45f4-88b9-92d175af3edc`，`materialize_mode=record-only`，未改动服务器 harness 文件系统。
  - `05:01:43Z` `plan.approved` `85210fc3-e1a3-4cfd-a2c8-b4715786a075`（scope "implementation plan"）。
  - `05:02:05Z` `worker.handoff.prepared` `168cb51e-422b-47f6-8e3a-02ca77c98606` — bootstrap 按目标 host profile 渲染。
  - `05:02:11Z` `assignment.accepted` `e5800e0c-9d8f-44e4-a7f0-8ca8f14ed755`，owner `mac-claude`，session `auto-mac-claude-1781758930`（首轮已记录，重试复用，未再次 accept）。
- **Host-aware profile 验证**（plan acceptance #3）: `worker.handoff.prepared` 的 `execution_profile` = host `macbook-local`，`workspace_path=/Users/yinxin/projects/multinexus`，`harness_root=/Users/yinxin/projects/multinexus/docs/project-harness`，`coordinator_cli_path=/Users/yinxin/.local/bin/coord-ssh`，`coordinator_db_path=/var/lib/coordinate/coord.sqlite3`，`harnessctl_path=/Users/yinxin/projects/multinexus/scripts/harness/harnessctl`。worker 执行目录指向 Mac source checkout；`/opt/multinexus` 仅作为服务器控制面 `control_workspace_path`，未被当作 worker 执行目录 —— 即 #11/#14/#15/#20 的 A0 修复，8.3.2 用真实 handoff 再次验证。
- **Worker 改动**: 仅 `progress.md` + `dogfood-feedback.md`（记录 A0 dogfood 证据 + 重试观察）；无 runtime / coordinate / harness 代码改动。
- **验证**: `git diff --check` 干净；multinexus 全量 `python -m unittest discover -s tests` 通过；`coord-ssh event list --workspace-id discord-nexus` 链路证据如上；GitHub issue #5 保持 OPEN（plan 非目标：不在本次自动关 issue，待 closeout approved 后由 operator 关闭）。
- **Closeout**: worker commit `d68c8b0` push 后通过 `coord-ssh assignment closeout discord-nexus --task-id phase-8.3.2-a0-materialization-dogfood --reviewer codex --actor mac-claude` 请求审核（event `83ae267e-7bb0-4f83-972e-a68d0c908b46`）。Codex review approved（event `1d4b0625-b8aa-4cec-b278-ef641601fa4d`），修正文档中对 529 可见性的错误描述（operator commit `1bff2be`），随后 `task.done`（event `b905a4be-3135-49f8-ac19-7e9e1d1f15d7`）。临时 GitHub issue #5 已由 operator 关闭。

## 2026-06-17

### Phase 8 dogfood cleanup — win-opencode degraded service

- **目标**: 收口 Windows `win-opencode` 接入，避免 Discord job 出现假成功、永久 thinking 或 SSH wrapper 卡死。
- **代码修复**:
  - `2b8a3a3`: Windows adapter 子进程环境不再注入 `PWD`。
  - `d1cdb93` / `8066e0c`: OpenCode 空 text 做有限重试；重试后仍为空时返回错误，并由 agentd 标记 job `failed`，不再生成 `"(no response)"` 假成功。
  - `6c926a4`: Windows `coord-ssh-win.py` 支持显式 `COORD_SSH_TARGET`、identity file、timeout。
  - `c662313`: SSH wrapper 加 `BatchMode=yes`、`StrictHostKeyChecking=accept-new`、可选 known_hosts，避免服务态交互等待。
  - `3fa17c2`: Windows wrapper 避免 OpenSSH stdin pipe；改为传单个 POSIX-quoted remote command arg，解决 `ssh -T ... sh` 在 Windows 下卡 EOF 的问题。
- **运维修复**:
  - Windows NSSM `win-claude` / `win-opencode` 服务增加 `COORD_SSH_TARGET=ubuntu@124.221.111.209`、`COORD_SSH_IDENTITY_FILE`、`COORD_SSH_KNOWN_HOSTS_FILE`。
  - 纠正服务私钥：服务器授权的是 `id_ed25519_coord_win_v2`，不是旧 `id_ed25519_coord_win`。
  - 为 LocalSystem 服务复制专用私钥到 `C:\ProgramData\ssh\coord\id_ed25519_coord_win_v2`，ACL 限制为 `SYSTEM` / `Administrators`，解决 OpenSSH `UNPROTECTED PRIVATE KEY FILE`。
- **验证结果**:
  - Windows wrapper `--version` 通过显式 v2 key 返回 `coordinate 0.1.0`。
  - `win-opencode` NSSM 服务恢复 claim/report，不再因为 SSH alias、stdin pipe 或私钥 ACL 卡住。
  - 5 个 pending smoke job 被消费：2 done (`WIN-OPENCODE-ENV-2`, `WIN-OPENCODE-ENV-4`)，3 failed (`OpenCode returned no text (events=step_start)`)。
- **结论**: `win-opencode` 链路已从“假 done / pending / SSH 卡死”降级为“明确 failed”，但 NSSM LocalSystem 下 OpenCode 仍不稳定；暂不作为默认 worker。后续需要 per-user runner 或 NSSM ObjectName=ADMIN 后再验收。

### Phase 8 preflight — manual server deploy/sync

- **目标**: 在进入 GitHub PR / review automation 前，先解决腾讯云 `/opt/coordinate` / `/opt/multinexus` 运行副本与本地开发 checkout 漂移的问题。
- **落地内容**:
  - `scripts/deploy-server.sh`: 手动部署入口，支持 `status` / `coordinate` / `multinexus` / `all`。
  - `scripts/server-smoke.sh`: 服务器健康检查，验证 systemd、`VERSION_DEPLOYED`、`coord-local`、mihomo proxy、agent registry、近期 breaker log。
  - `docs/deploy-runbook.md`: 记录 source-of-truth 边界；`/opt/*` 是部署副本，不是开发源。
- **验证**:
  - `scripts/deploy-server.sh status` 通过，coordinate / bridge 均 active，Discord proxy 可达。
  - `scripts/deploy-server.sh multinexus --skip-install` 已将腾讯云 `/opt/multinexus` 同步到 `f465a1f91ead938b355d2ca935fb48e4323dc3a8` 并重启 bridge；smoke 通过。
  - `/opt/coordinate/VERSION_DEPLOYED` 已是本地 coordinate tip `244f95f6026857fef8cd74362792435955f2c72d`，本轮无需重复部署。
- **边界**: 这是最小手动 deploy/sync，不是 GitHub Actions 自动生产发布。后续 CI/CD 应复用该脚本作为唯一部署路径。

### Phase 8.1 — GitHub issue intake MVP

- **目标**: 实现 Phase 8 的第一段闭环：own-repo GitHub issue scan → coordinate `issue.spotted` event → Discord-visible `[ISSUE]` rendering。该阶段不做自动 triage、assignment、PR 或 merge。
- **Coordinate 实现**:
  - `coordinate` commit `38f773a`: 新增 `src/coordinate/issues.py`、`coordinate issue scan` CLI、`issue.spotted` policy/rendering、测试。
  - issue idempotency key 使用 `<workspace_id>:github_issue:<repo>:<number>:<updated_at>`，同一 updated_at 不重复刷事件，issue 更新后可再次 surfaced。
  - issue body 只保存短 excerpt，并带 `content_trust=untrusted`；渲染文案明确提醒 operator/worker 不得把 issue 正文当系统指令。
- **验证**:
  - coordinate full suite 759 tests OK。
  - 本机 `coordinate issue scan demo --repo baisiqi6/multi-agent-nexus --limit 3` 返回合法空结果（当前 repo 无 open issue）。
  - `multi-agent-nexus` / `multi-agent-coordinator` 当前均无 open issue，因此尚未产生真实 `issue.spotted` 事件。
- **部署**:
  - 已用 `scripts/deploy-server.sh coordinate --skip-install` 部署到腾讯云。
  - `/opt/coordinate/VERSION_DEPLOYED` 已更新为 `38f773a8d4cc9aa95c9a4a62bf3631dd7f1ebe94`，server smoke OK。
- **原始待验证项**:
  - 首版实现只能在本地 DB 或 server-side `gh` 形态下运行；A0 runtime-only 形态需要后续 dogfood 验证。
  - 当时 owned repos 没有 open issue，需要创建或标记一个低风险测试 issue 才能做真实 Discord `[ISSUE]` dogfood。

### Phase 8.1 — GitHub issue intake dogfood closeout

- **架构修正**: 腾讯云继续保持 runtime-only，不安装 `git` / `gh` / GitHub token；GitHub issue scan 应在 Mac / Windows coding worker 宿主机上运行，再通过 `coord-ssh` / `coord-ssh-win.py` 把 `issue.spotted` event 写入远端 coordinate DB。
- **Coordinate 修复**:
  - `966b8c5`: `coordinate issue scan` 新增 `--event-cli-path`，支持本地 `gh issue list` + 远端 `event append` 的组合模式。
  - 这避免把服务器变成开发机，也保留原来的本地 SQLite scan 模式。
- **真实 dogfood**:
  - 创建临时 issue `baisiqi6/multi-agent-nexus#2`：`[dogfood] Phase 8 issue intake smoke`。
  - 在 Mac 上运行 `PYTHONPATH=src python3 -m coordinate issue scan discord-nexus --repo baisiqi6/multi-agent-nexus --limit 5 --event-cli-path /Users/yinxin/.local/bin/coord-ssh`。
  - 远端 event `335d09e2-189c-41bd-b874-8fbe32f1bca2` 创建成功，payload 带 `content_trust=untrusted`。
  - 远端 coordinate daemon 将 delivery `6d5c5601-1f36-45e7-9317-305912893aba` 发送到 Discord，`platform_message_id=discord_bot:1516860802613641457`。
  - 重复 scan 返回 `created=0 existing=1`，幂等正常。
  - 临时 GitHub issue 已关闭。
- **Dogfood 发现**:
  - 之前 `scripts/deploy-server.sh coordinate --skip-install` 只同步了 `/opt/coordinate/src`，但 `/opt/coordinate/.venv/site-packages` 仍是旧 wheel，导致 `coord-local policy create-deliveries` 报 `unsupported event type: issue.spotted`。
  - 结论：Python package 代码变更不能用 `--skip-install` 部署；`--skip-install` 只适合文档、非导入脚本或确认 venv 不需要更新的紧急同步。
  - Mac tar 会带 Apple extended attributes / file flags，服务器 tar 会输出 `LIBARCHIVE.xattr.*` / `SCHILY.fflags` warning；`deploy-server.sh` 已设置 `COPYFILE_DISABLE=1`，并自动探测 `--no-xattrs` / `--no-fflags` 降噪。

### Phase 8.2 — GitHub issue triage dogfood closeout

- **目标**: 验证 `issue.spotted` 能被 operator triage 成 accept/reject/defer 决策，并通过远端 coordinate DB 产生 `[ISSUE_TRIAGE]` 可见消息。
- **Coordinate 实现/部署**:
  - `995bc5c`: `coordinate issue triage`、`issue.triaged` event、task mirror、policy delivery、幂等/冲突保护。
  - `5092bc4`: review follow-up，triage 层强制 `content_trust="untrusted"`，忽略 spotted payload 的自声明 trust；文档明确 8.2 accept 只创建 DB task mirror，不写 harness checklist。
  - 已用 `scripts/deploy-server.sh coordinate` 部署到腾讯云，未用 `--skip-install`；`/opt/coordinate/VERSION_DEPLOYED` 记录 `5092bc416caae836a8a01b9cc59dffdfd4ae3281`。
- **真实 dogfood**:
  - 创建临时 issues `baisiqi6/multi-agent-nexus#3`（accept）和 `#4`（reject），Mac 本地跑 `gh`，通过 `/Users/yinxin/.local/bin/coord-ssh` 写远端 coordinate DB。
  - Scan events: `45279001-d431-45f7-8286-30c0a1e08af3`（#3）和 `b59be207-33c6-4434-9357-e65c96f68f1d`（#4）。
  - Accept triage: event `b1d35a1c-970a-4f75-914c-e94cb5ca5ffa`，delivery `240e9eb1-01c0-4bdd-94e2-bddc5bdb0f4b`，task mirror `phase-8-2-triage-accept-smoke`，Discord message `discord_bot:1516871824963539165`。
  - Reject triage: event `f7f8bcc5-9086-4e95-b250-31fa12f37e6f`，delivery `076e71b3-4daa-4217-89c1-96d7c172dad0`，Discord message `discord_bot:1516871826884661398`。
  - Repeated accept reused the existing triage event/delivery; conflicting reject on the accepted issue returned `IssueTriageError`. Temporary issues #3/#4 were closed.
- **Boundary**: 8.2 is complete but intentionally stops at DB task mirror. Phase 8.3 must materialize accepted issue mirrors into harness checklist/task state before `task handoff` can use them.

### Phase 8 host-profile handoff smoke — dogfood closeout

- **目标**: 验证 A0 形态下 `coordinate` / Discord bridge 跑在腾讯云、worker agentd 跑在各宿主机时，handoff bootstrap 使用目标宿主机自己的 repo path，而不是服务器部署副本 `/opt/multinexus`。
- **代码/部署前提**:
  - `coordinate` branch `agents/mac-claude/phase-8-preflight-dogfood-cleanup`
    - `a9ba1c7` host-aware bootstrap / `workspace_host_profiles`
    - `fb25b78` daemon internal pump guard
    - `244f95f` relaxed handoff state preflight for summary state
  - `multinexus` branch `agents/mac-claude/phase-8-preflight-dogfood-cleanup`
    - `d315eea` bridge uses `assignment accept` returned `bootstrap_text`
    - `7ef76aa` host-profile smoke task
    - `8ca4e6e` smoke task lease release
- **Host profiles verified**:
  - `macbook-local`: `/Users/yinxin/projects/multinexus`, coordinator wrapper `/Users/yinxin/.local/bin/coord-ssh`
  - `win-admin`: `C:\Users\ADMIN\projects\multinexus`, coordinator wrapper `python C:\Users\ADMIN\projects\multinexus\scripts\coord-ssh-win.py`
- **Mac handoff result**:
  - Handoff bootstrap correctly used `/Users/yinxin/projects/multinexus` and did not leak `/opt/multinexus` as worker execution path.
  - Execution blocked in environment: Mac Claude CLI could not reach local API proxy (`ConnectionRefused` / local `claude -p` timed out). This is recorded as dogfood feedback item 12.
- **Windows handoff result**:
  - Windows checkout was first synced from `agents/mac-claude/phase-7.2-multi-host-agent-runtime` to `agents/mac-claude/phase-8-preflight-dogfood-cleanup`.
  - Handoff event `6bf3aad2-ea9d-4da3-8381-16cffa085214` generated bootstrap for `C:\Users\ADMIN\projects\multinexus`.
  - Job `request:651a60b4-327b-4aa7-95c6-b53e8bba7856` was claimed by `win-claude` and completed `done` in ~97.5s.
  - Worker result verified: Windows path present, `/opt/multinexus` not used as execution directory, branch matched, no source files/services/tokens touched.
- **Lifecycle closeout**:
  - Worker response included `[agent-report] action=done`, but coordinate did not ingest it as `agent.reported done`; bridge emitted fallback `progress.reported` instead. This is recorded as dogfood feedback item 13.
  - Operator reviewed the visible result, recorded `assignment review-result ... approved`, then `assignment mark-done`; task `phase-8-host-profile-handoff-smoke` is closed on the remote harness.

## 2026-06-10

### Phase 7.1.1 后续维护 + 回归 (mac-* agentd)

> **上下文**: phase-7.1.1 closeout 后, operator 在本机做 Discord reply path + 跨 agent handoff 回归, 发现 4 项遗留需要修. 该 commit 落在 phase-7.1.1 的 worker 分支 `agents/mac-claude/phase-7.1.1-single-platform-bridge-process` 上.

#### 修改

1. **mac-opencode context 窗口对齐** (`agents.toml`, runtime config 不入仓)
   - `context_recent_messages: 10 → 40`
   - `context_budget_chars: 4000 → 12000`
   - 理由: mac-opencode 原来只有其他 agent 的 1/3 context, 跨 agent handoff 时 `[handoff]` 头部可能被截断

2. **`{available_peers}` 占位符 + loader 注入** (`multinexus/config.py`)
   - 新增 `_render_system_prompt_placeholders()` helper, 支持 `{available_peers}` 和 `{self_id}` 占位符
   - 4 个 mac agent 的 `system_prompt` 里硬编码的 "可用 agent: xxx" 全部替换为 `{available_peers}`
   - 行为: 从 `agents.toml` 其他 `[[agents]]` 自动生成 peer 列表 (不含自己, 含所有其它 agent 包括 win-*)
   - 决策记录: 保留 win-* 在 peer 列表内 (F 阶段腾讯云部署后自动生效, 不用改 toml)

3. **`agents.toml` mac.sh 路径漂移修复** (4 处 `system_prompt` block, runtime config 不入仓)
   - `multi-agent-coordinator` → `coordinate` (项目实际目录名)
   - 全仓 grep 验证 `.py / .toml / .yaml / .sh / .json` 中残留 = 0 处
   - 历史背景: 昨天 `discord.bridge.err.log` 里 `invalid choice: 'runtime'` 错误的根因是 mac.sh 旧版本 + agents.toml 路径漂移双重叠加. agent 按旧 prompt 去 `multi-agent-coordinator/skills/coordinate-operator/scripts/mac.sh runtime ...`, 旧 binary 不认识 `runtime` 子命令. 12 小时前已自动停止.

4. **4 个 mac agentd 重启加载新 prompt** (运维动作, 不入仓)
   - `launchctl kickstart -k` 重启, **注意 launchd label 是带 `.agentd` 后缀的** (plist Label 是 `com.multinexus.mac-claude`, launchd 注册的是 `com.multinexus.mac-claude.agentd`)
   - 新 PID: 48703 / 48706 / 48709 / 48712 (启动 14:35:28)
   - 启动日志全部 `Agentd worker started`, 5 秒实时扫描 0 新错误

#### 验证

- **C — Discord reply path 终验**: PASS
  - 测试消息: `@Mclaucode 报一下时间`, message_id `1514143348888174593`
  - 链路 22 秒: `request.received (05:45:06) → job.claimed (05:45:08) → job.completed (05:45:28)`
  - jobs 表 `request:48fd85f1-10bd-4dc0-af81-179ce60c42c3` status=done
  - 0 处 "Job done" / "✅ Job 完成" 卡片
- **E — 跨 agent handoff 测试**: PASS
  - 测试文案: `@Mac Codex 请用 [handoff] @Mac Claude 让它只回复 "E-HANDOFF-OK"`
  - 5 个 job 时序: codex 收到指令 → 生成 handoff → bridge 路由 → claude 回复
  - handoff 链路总耗时 54 秒 (含两次手动触发间隔)
  - 无 mention cascade, 无 "Job done" 残留
- 配置加载相关轻量回归: 27 tests OK

#### 已知非阻塞观察

- `events` 表**没有专门的 `handoff.detected` 事件类型** — handoff 路由链路靠 jobs 表时间序列拼接追溯, 不是显式事件
- `deliveries` 表 22 个 pending 是历史积累孤儿, agent reply 不走 deliveries 表 (走 Discord API 直发)

#### 文档边界澄清

- `~/.openclaw/plans/findings.md` 是 **OpenClaw 本地工作目录生成的笔记**, 不是 multinexus 项目文档, **不应 commit 到本仓**. 它的内容是关于 multinexus 的盘点, 但权威来源应该是本目录的 `progress.md` / `dogfood-feedback.md` / `mvp-checklist.json`
- 类似地, `~/.openclaw/` 目录本身的命名属于历史遗留, 等 F 阶段腾讯云部署时统一重命名 (涉及 launchd plist / log 路径 / sqlite db 路径 / env var)

#### 遗留 (deferred, 留作后续 phase 钩子)

- KOOK bridge plist + `multinexus/kook/__main__.py` (与 phase-7.1.1 同样的 deferred, 参见原 review)
- 跨 agent mention router 在 1 进程多 client 下的实际解析路径 (phase-7.1.1 closeout 已有, 但仅覆盖 mention map 同步机制)
- `~/.openclaw/` 目录重命名
- `:memory:*` / `docs/project-harness/current/` 等 runtime 产物补进 `.gitignore` (跟今天的 commit 无关, 单独处理)

#### Harness state 回填

- `docs/project-harness/events.jsonl`: 回填 phase-5.5 / phase-7.1 / phase-7.1.1 的 closeout 事件 (22 条), 这些是 harness 之前写过但未 commit 的
- `docs/project-harness/harness-state.json`: `current_item` 从 phase-6.1-omp-smoke 更新到 phase-7.1.1, status `todo` (等待 human gate 后转 `done`)
- **入仓原因**: harness state 是项目状态权威来源的一部分, 跟 working tree 同步后才能反映当前 phase

## 2026-06-09

### Phase 7.1.1: Single Platform Single Bridge Process — implementation + closeout

- **Codex 不可用**，operator 代行 worker + reviewer 全流程
- **实施概要**：
  - `multinexus/config.py`: token 值校验抽出为 `require_token` flag；新增 `load_all_configs_for_platform()` 读所有 `[[agents]]`
  - `multinexus/agentd/__main__.py`: 调 `load_config(..., require_token=False)`
  - `multinexus/client.py`: 加 `DiscordBridge` 类（持 N 个 `DiscordClient` 共享 asyncio loop，`_on_client_ready` 跨 client 同步 `register_peer_bot`）
  - `multinexus.py`: 加 `--platform {discord,kook}` 参数；`--platform discord` 走 `DiscordBridge` 启动 N client
  - `tests/test_discord_bridge_multi_agent.py`: 11 个新测试
  - launchd: 新 `com.multinexus.discord.bridge.plist`（1 bridge）；旧 4 个 `com.multinexus.mac-X.bridge.plist` 移到 `launchd/legacy/`
- **测试**: multinexus 269/269 pass (258 legacy + 11 new), coord 731/731 pass
- **现场拓扑**（6 进程）:
  - PID 13842 coord serve
  - PID 13844 multinexus.py --platform discord（bridge, 承载 6 个 DiscordClient: mac-claude / mac-codex / mac-omp / mac-opencode / win-claude / win-openclaw）
  - PID 13846/13848/13850/13852 multinexus.agentd --agent <4 Mac agents>
- **端到端 smoke**: coord CLI `runtime request submit --target-agent mac-claude` → job `713c3ae2-...` → agentd claim → claude CLI → report done 11.6s
- **遗留 / deferred** (见 `tasks/phase-7.1.1-single-platform-bridge-process/review-feedback-2026-06-09-operator-closeout.md`):
  - KOOK bridge plist + `multinexus/kook/__main__.py` 未实现（plan 标 optional，closeout 显式 deferred）
  - 跨 agent mention 路由测试只覆盖了 mention map 同步机制（`register_peer_bot`），没测 `MentionRouter` 在 1 进程多 client 实际解析路径
  - Discord 真消息触发 reply 回原频道的 webhook 路径没测（用 coord CLI 模拟提交）
  - 流程上 omp plan review 是 operator 代写（codex 不可用），已在 `operator-needs-backlog.md` 落档
- **Coord events timeline**:
  - 17:15:04 `assignment.requested` operator
  - 17:30:19 `plan.review_requested` operator (round 1)
  - 17:30:38 `plan.approved` operator (round 1)
  - 17:36:00 `plan.rejected` omp (3 must-fix items)
  - 17:36:58 `plan.review_requested` operator (round 2)
  - 17:37:08 `plan.approved` operator (round 2, after omp feedback)
  - 18:07:06 `closeout.requested` coordinator
  - 18:08:27 `review.completed` operator (approved with caveats)
  - 18:09:10 `task.done` operator (via `harnessctl mark-done`)
- **mvp-checklist.json**: phase-7.1.1 status `done`, workflow `closed`, owner `operator` (harnessctl 自动更新)

### Phase 7.1 review (operator-side retrospective)

- 7.1 task 在 2026-06-08 15:51 由 `codex-operator` 走完 closeout → mark-done 路径
- 2026-06-09 复盘发现 plan 验收标准（`docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/plan.md` 第 38-39 行 ASCII 图）要求 "1 Discord bridge 进程 + 1 KOOK bridge 进程 + 1 coord + 1 agentd/agent" 的 N+M 拓扑，**但当前 `multinexus.py` 是 1 process 1 agent**，bridge 没合并
- 7.1 报告 closeout 时此问题未被记录，也未在 review feedback 中提出
- 处置：开 `phase-7.1.1-single-platform-bridge-process` 任务（本段之上记录的实施段）
- 现场：原 4 legacy multinexus.py 已 bootout，6 进程 N+M 拓扑（1 coord + 1 bridge + 4 agentd）已上线

## 2026-06-08

### Dogfood feedback: agent-report fallback after accept

- Observed Phase 7.1 Round 3 feedback in Discord, but coordinate did not ingest a done/closeout event; state only showed the runtime auto `action=accept`.
- Root cause in MultiNexus runtime: `_send_missing_report_fallback()` treated any `[agent-report]` in adapter output as sufficient. If the output contained an `action=accept` line plus natural-language completion, fallback did not emit progress.
- Added `contains_execution_agent_report()` so only `done`, `blocker`, or `progress` suppress the fallback; `accept` no longer counts as execution completion.
- Added regression coverage for accept-only report plus natural-language completion.

### Phase 7.1: 单机 N+M 运行架构 — round 3 rework (job polling + session resume)

- Fixed coordinate job polling: `_get_job()` was parsing `result.result.jobs` but coordinate outputs top-level `{"jobs":[...]}`. Removed `--status all` (not a valid coordinate filter), added `--workspace-id` filter.
- Preserved session resume in agentd worker mode: bridges now include `session_scope_id` and `legacy_scope_ids` in origin_json. `AgentdWorker._call_or_resume()` checks session store, calls `adapter.resume()` for existing sessions, falls back on error.
- 9 new regression tests: job polling format parsing, status filter omission, wait_for_job_result finding done jobs, worker resume flow, fresh call, resume error fallback, bridge origin scope fields.
- 256/256 pass (2 skipped: khl). harnessctl validate passes.

### Phase 7.1: 单机 N+M 运行架构 — round 3 rework (shutdown + test coverage)

- Fixed agentd worker shutdown: replaced `asyncio.sleep` with `asyncio.Event` for immediate wake on stop().
- Simplified `__main__.py` _shutdown callback: only calls `worker.stop()` (no `loop.stop()`), lets `run_until_complete` exit cleanly.
- Added `RuntimeError` catch alongside `KeyboardInterrupt` in main loop.
- Updated tests: shutdown test now verifies `_wake` event is set, worker stops immediately.
- Full suite 247/247 pass, 2 skipped (khl not installed). Harness validate passes.

### Phase 7.1: 单机 N+M 运行架构 — round 2 rework

- Addressed codex round 2 review: implemented bridge -> coordinate -> standalone agentd flow.
- Created `multinexus/agentd/worker.py`: `AgentdWorker` claims jobs from coordinate runtime via CLI, executes adapter, reports results.
- Rewrote `multinexus/agentd/__main__.py`: replaced HTTP-based `AgentDaemon` with coordinate-based `AgentdWorker`. Uses `run_until_complete` instead of `run_forever`, signal handler calls `worker.stop()` + `loop.stop()`.
- Both Discord and KOOK bridges submit via `CoordinateRuntimeClient` (committed in prior commit).
- Added 6 new tests: worker job processing (success + error + invalid payload), graceful stop, shutdown testability, shutdown callback verification.
- `khl>=0.4.0` was already committed in an earlier commit.
- Full suite 247/247 pass (2 skipped: khl not installed). harnessctl validate passed.

### Phase 7.1: 单机 N+M 运行架构 — blocker fix

- Fixed reviewer blocker: removed embedded `AgentDaemon` from both `DiscordClient` and `KookBridge`.
- Both bridges now connect to a standalone agentd via `AgentdClient` (HTTP client only).
- Created `multinexus/agentd/__main__.py`: standalone agentd launcher (`python -m multinexus.agentd --agent <id> --port <port>`).
- One agentd process per agent identity, shared by all bridges. Prevents duplicate adapter instances.
- `agentd_mode=true` now requires `agentd_port` to be set in config — fails fast if missing.
- `khl>=0.4.0` already in requirements.txt (reviewer finding was stale).
- Full suite 224/224 pass. 1 new commit.

### Phase 7.1: 单机 N+M 运行架构 — review blocker

- Reviewed `agents/mac-claude/phase-7.1-single-host-n-plus-m-runtime` after Claude's Discord completion report.
- Validation observed: `.venv/bin/python -m unittest discover tests/` passed 224 tests; `scripts/harness/harnessctl validate` passed after checklist repair; `git diff --check` passed.
- Blocker recorded through coordinate as `blocker.raised` event `3c28dada-bfa2-4d60-a04c-438673caae04`.
- Blocking findings:
  - The implementation starts an embedded `AgentDaemon` inside each bridge process. If Discord and KOOK bridges both run for the same agent, they can still create two adapter/agentd instances, so the acceptance goal "only one agentd per agent identity shared by all IM bridges" is not met.
  - The actual chain is `bridge -> local HTTP agentd -> adapter`; it bypasses the planned `bridge -> coordinate -> agentd` control-plane boundary for Phase 7.1 dogfood.
  - `multinexus.kook.bot` cannot import in the current environment because `khl` is not in `requirements.txt`; current tests cover KOOK mention parsing but not KOOK bridge startup/import.
- Also repaired missing Phase 7 checklist metadata: added `phase-7-n-plus-m-runtime`, `phase-7.1-single-host-n-plus-m-runtime`, and `phase-7.2-multi-host-agent-runtime` to `mvp-checklist.json` so future assignment/review/blocker transitions can be tracked.

### Phase 7.1: 单机 N+M 运行架构 — rework handoff

- Added reviewer feedback at `docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/review-feedback-2026-06-08-codex.md`.
- Unblocked the task through coordinate and re-handed it to `mac-claude` with `task handoff --target-agent mac-claude`.
- Confirmed agent-specific Discord handoff was sent with `<@1507329791982833775>` and bootstrap path `docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/worker-bootstrap.md`.
- `mac-claude` auto-accepted; checklist is now `status=doing`, `workflow.status=running`, owner `mac-claude`.
- Dogfood issue found during handoff: public `[HANDOFF]` status text triggered duplicate accept before the agent-specific `[handoff]` message. Fixed in coordinate by changing public handoff status rendering to `[HANDOFF_STATUS]` while keeping agent-specific protocol messages unchanged.

### Phase 7.1: 单机 N+M 运行架构 — implementation

- Created `multinexus/protocol.py`: platform-agnostic `AgentRequest`/`AgentResponse` envelope with `Platform` enum, `PlatformOrigin`/`PlatformDestination` for cross-platform routing. JSON serialization round-trip tested.
- Created `multinexus/agentd/server.py`: `AgentDaemon` HTTP server (aiohttp) that accepts `AgentRequest` via POST, processes through existing adapters, manages session lifecycle, returns `AgentResponse`. One agentd per agent identity. Includes health check endpoint.
- Created `multinexus/agentd/client.py`: `AgentdClient` HTTP client for bridges to submit requests to agentd.
- Modified `multinexus/client.py`: added bridge mode (`agentd_mode=true`). When enabled, `DiscordClient` no longer calls `make_adapter()` directly — it submits `AgentRequest` to local agentd. Legacy mode preserves existing behavior.
- Created `multinexus/kook/`: KOOK bridge module ported from kook-nexus.
  - `kook/bot.py`: `KookBridge` — WebSocket + HTTP polling, message dedup, transient filtering, handoff dedup. Submits to agentd in bridge mode.
  - `kook/mentions.py`: `KookMentionRouter` — KMarkdown `(met)ID(met)` / `(rol)ID(rol)` parsing, agent addressing, outbound mention conversion.
- Updated `multinexus/models.py`: added `agentd_mode`, `agentd_port`, `agentd_host`, `kook_poll_*` fields.
- Updated `multinexus/config.py`: parse new fields from TOML.
- Updated `docs/project-harness/architecture.md`, `domain-model.md`, `scope.md` for N+M architecture.
- 41 new tests: 10 protocol, 9 agentd HTTP, 21 KOOK mentions + 1 lazy import. Full suite 224/224 pass.
- 5 commits on `agents/mac-claude/phase-7.1-single-host-n-plus-m-runtime`.

## 2026-06-03

### Phase 6.1: omp Adapter 基础接入 — implementation

- Created `multinexus/adapters/omp.py`: `OmpAdapter(AgentAdapter)` with `call()`, `resume()`, `health_check()`.
  - Uses `omp -p --auto-approve` for non-interactive mode.
  - `resume()` passes `--resume <session_id>`.
  - Optional `--model` and `--thinking` flags via `omp_model` / `omp_thinking` config.
  - Simple subprocess communicate (no streaming), with timeout via `asyncio.wait_for`.
- Extended `multinexus/models.py`: added `omp_bin`, `omp_model`, `omp_thinking`, `omp_auto_approve` fields to `AgentConfig`.
- Updated `multinexus/config.py`: parse omp fields from TOML with `_first_existing_command` for `omp_bin`.
- Registered in `multinexus/adapters/factory.py`: `adapter == "omp"` → `OmpAdapter(config)`.
- Added mac-omp config block to `agents.toml` (local, gitignored) with `omp_model = "opus"`, `omp_thinking = "high"`.
- 16 new tests in `tests/test_omp_adapter.py`: CLI arg construction (auto-approve, model, thinking, resume), call/resume/failure/timeout/missing CLI/health check/factory.
- Full test suite: 183/183 pass (167 existing + 16 new).

### Phase 6.1: mac-omp Smoke Test — verification

- **omp CLI**: `omp/15.7.6` available at `/Users/yinxin/.bun/bin/omp`
- **Health check**: `{"adapter": "omp", "bin": "omp", "available": true, "path": "/Users/yinxin/.bun/bin/omp"}` — PASS
- **Real call**: `omp -p --auto-approve "Reply with exactly: OK smoke-test-passed"` returned "OK smoke-test-passed" — PASS
- **Unit tests**: 16/16 omp adapter tests pass; full suite 183/183 pass
- **plist**: `com.multinexus.mac-omp.plist` validated with `plutil -lint` — OK
- **Shell scripts**: `bash -n` all pass; `launchd.sh` AGENTS includes `mac-omp`
- **Known gap**: `session_id` is not captured from `omp -p` output (omp print mode does not output session IDs); resume support is limited without interactive mode
- All Phase 6.1 acceptance criteria met:
  1. OmpAdapter constructable via `make_adapter()` ✅
  2. `--auto-approve` in call/resume CLI args ✅
  3. `--resume <session_id>` passed correctly ✅
  4. Health check format correct ✅
  5. All omp adapter tests pass ✅
  6. No existing test regression (183/183) ✅

## 2026-06-01

### Phase 5.4: Workspace Doctor And Full Harness Init — implementation

- Created `src/multi_agent_coordinator/doctor.py`: workspace harness diagnostics module with `diagnose_workspace()` function. Produces a `DoctorReport` that checks workspace path, harness root, harnessctl availability/executability, required and optional file presence, checklist validity, harnessctl validate/doctor health, and distinguishes between `none`, `minimal_file_backed`, and `full_harness_runtime` modes.
- Added `workspace doctor <workspace_id>` CLI subcommand. Returns exit 0 for full_harness_runtime, 1 otherwise.
- Enhanced `init_file_harness()` in `onboarding.py` with `init_full_harness()`: copies `scripts/harness/` runtime from a `--source` directory, creates protocol file stubs (scope.md, architecture.md, domain-model.md, runbook.md), ensures minimal harness files exist. Supports `--dry-run`, never overwrites existing files, validates harness_root is within workspace path (security boundary), updates workspace `harnessctl_path` when harnessctl is created.
- Updated `workspace init-harness` CLI to accept `--mode full|minimal`, `--source`, and `--dry-run` flags. Full mode requires `--source`, minimal mode requires `--root`/`--task-id`/`--plan-doc`.
- 22 new tests in `tests/test_doctor.py`: doctor (missing path, missing root, missing harnessctl, not executable, healthy full, invalid checklist, bus note, to_dict), full init (dry-run, creates files, no overwrite, updates harnessctl_path, missing source, root outside workspace, unknown workspace, empty source, to_dict), CLI integration (doctor unknown/minimal, init full requires source, init minimal requires root).
- Coordinator test suite: 664/664 pass (642 existing + 22 new).
- Updated `docs/project-harness/runbook.md` with new workspace onboarding order (register → doctor → init-harness full → doctor verify → task create → audit).

### Phase 5.3: Agent Registry Auto-Sync — implementation

- Created `src/multi_agent_coordinator/agent_registry.py`: TOML parser for `[[agents]]` and `[[external_agents]]` that extracts `id`, `display_name`, `discord_user_id`, and `agent_type`. Skips entries missing `discord_user_id`, fails closed on duplicate IDs or Discord user IDs.
- Added `sync_workspace_agents` batch helper to `db.py` with merge (default, preserves manual overrides) and `--replace` (replaces entire registry) semantics.
- Added `workspace agent sync` CLI subcommand with `--source` and `--replace` flags. Outputs JSON summary: `added`, `updated`, `unchanged`, `skipped`, `removed` (replace only).
- 16 new tests: 6 TOML parsing, 6 DB sync, 4 CLI integration (including token leak prevention).
- Coordinator test suite: 640/640 pass. multinexus test suite: 165/165 pass.
- End-to-end verified: synced 8 agents from real `agents.toml` to coordinator DB.
- Updated `agents.toml.example` to mark `discord_user_id` as required for registry sync.
- Updated runbook with `workspace agent sync` commands.

### Phase 5.2: Task-Scoped Session Lifecycle — implementation

- Added canonical session scope helpers for `channel:<channel_id>`, `thread:<thread_id>`, and `task:<workspace_id>:<task_id>`, with legacy numeric scope fallback for existing sessions.
- Extended `SessionStore` with active lookup fallback, scope-prefix/task queries, and task stale/archive lifecycle operations.
- Updated coordinator handoff runtime so accepted task handoffs use task scope, resume the same task session, isolate different tasks, and archive local task sessions on coordinator closeout/done lifecycle notices without executing coordinator mutations from Discord text.
- Updated text and slash session status/reset output to show scope type.
- Updated session persistence design and runbook with task scope priority, archive semantics, and contamination troubleshooting.
- Validation: targeted session/command/handoff tests passed; full suite `.venv/bin/python -m unittest discover tests/` passed with 161 tests.

### Phase 5.1: Handoff Runtime Hardening — runtime tests and protocol docs

- Added 12 runtime tests in `tests/test_coordinator_handoff_runtime.py` covering:
  - Accept failure: sends `[agent-report] action=blocker`, adapter NOT called.
  - Accept success: sends accept report, reads bootstrap, calls adapter with bootstrap prompt.
  - Bootstrap missing: adapter still called, prompt notes bootstrap missing.
  - All report sends use `AllowedMentions.none()`.
  - Action scope: only `assignment.accept` auto-executed; `mark-done`, `closeout`, `merge`, `deploy`, `pr` all rejected.
- Created `docs/agent-report-protocol.md`: documents report format, supported actions, auto-accept behavior, and when to use Discord report vs coordinator CLI.
- Full test suite: 134 pass (122 existing + 12 new).

## 2026-05-29

### Round 1 — Initial implementation

- Worker implemented all Phase 3.3 launchd artifacts:
  - 3 plist templates (`launchd/com.multinexus.mac-{claude,codex,opencode}.plist`)
  - Shared lib (`scripts/lib/launchd.sh`)
  - 4 management scripts (`scripts/{start,stop,status,uninstall}.sh`)
- Fixed `start.sh` plist update semantics: `bootout` + `bootstrap` cycle replaces `kickstart -k` so launchd reloads changed plists.
- Added launchd documentation section to `docs/platform-setup.md`.
- Static validation passed: `plutil` 3/3, `bash -n` all pass, 106 tests OK.
- Submitted for review.

### Round 2 — Review findings addressed

- **Finding 1**: `check_manual_process` in `scripts/lib/launchd.sh` used a narrow `pgrep -f "multinexus.py --agent $agent"` pattern that missed invocations with intervening flags (e.g. `python multinexus.py --config agents.toml --agent mac-claude`). Fixed to `nexus\.py.*--agent[= ]${agent}\>` which matches `--agent X` and `--agent=X` regardless of flag order.
- **Finding 2**: Closeout file list was incomplete (omitted 5 of 9 artifacts). Corrected.
- Re-validated: `bash -n` all pass. (plutil and tests unchanged from round 1.)

### Manual validation

Human performed terminal and Discord validation:

- `scripts/start.sh mac-claude` → loaded, Gateway connected.
- `scripts/status.sh mac-claude` → pid visible.
- `scripts/stop.sh mac-claude` → stopped.
- `scripts/uninstall.sh mac-claude` → plist removed.
- `scripts/start.sh` (all 3) → mac-claude, mac-codex, mac-opencode all loaded.
- Discord health check → mac-codex responded with adapter/bin/available fields.

### Current status

- Task status: **done** — all static, terminal, and Discord validation passed.
- Human gate: **passed**.
- Ready for commit and merge at human's discretion.

## 2026-05-31

### Dogfood doc sync — coordinator integration docs

- Read harness state, progress, scope, architecture, domain model, and `dogfood-doc-sync` plan before editing.
- Confirmed the task already had an active coordinator lease for `mac-codex` / `auto-mac-codex-1780240587`; a duplicate `assignment accept` attempt through coordinator CLI failed because of that active lease.
- Updated current-state docs for Phase 4 coordinator integration:
  - `docs/discord-multibot-plan/multi-bot-refactor-plan.md`
  - `docs/multi-agent-harness-overview.md`
  - `docs/project-harness/runbook.md`
  - `docs/project-harness/scope.md`
- Synced wording around coordinator Discord daemon, targeted agent handoff delivery, multinexus coordinator handoff auto-accept, and the rule that task lifecycle state changes go through coordinator CLI rather than direct harness JSON edits.
- Sanity-checked documented coordinator commands against current `mac.sh --help` output.
- Validation: `git diff --check` passed; `scripts/harness/harnessctl validate` passed; `scripts/harness/harnessctl doctor` exited 0 with existing optional/current file misses (`current/task_plan.md`, `init.sh`).

## 2026-07-12 — P9-0A1 plan review

- Added the detailed `p9-0a1-cli-boundary-extraction` plan under the Phase 9
  architecture-hardening prelude and registered its SHA256 with Coordinate.
- Independent read-only review approved the exact registered revision with no must-fix
  findings; review evidence is preserved in
  `docs/project-harness/tasks/p9-0a1-cli-boundary-extraction/plan-review-round-1.md`.
- The review ran through Claude Code CLI, while provider JSONL identified the effective
  assistant response model as `glm-5.2`; the evidence records both facts explicitly.
- Package execution remains fail-closed: no coding-worker bootstrap or implementation
  is authorized until `slice-4-projection-hardening` is accepted and a fresh drift,
  command-contract, focused-test, full-suite, and import-boundary preflight passes.
- Harness validation passed with six warnings: four historical completed-item review
  warnings plus two P9-0A1 blocked-task shape warnings (`blocked_by` and `handoff`) that
  the current Coordinate blocker transition does not populate. No checklist JSON was
  edited directly to conceal that lifecycle/tooling gap.

## 2026-07-12 — S3-C2 local-integration plan approval

- Added the detailed `slice-3-c2-local-integration` execution plan, bound to
  Coordinate `main` `8fadd687d68032cf656291e6bf537ec481fb3e25` and the reviewed
  Slice 3 checkpoint `1b862129897be001e5a9078b7b4fad48d90d89c2`.
- Registered plan-ready event `01f7dd53-2336-46a2-9d4e-f76908ecf038` with full
  SHA256 `aea8b2dd7a8348904fd1ffadc3a649c79355c76eba9c2d806d8adbff78e898ee`.
- Independent read-only review approved that exact plan revision with no must-fix
  findings. Review evidence and the corrective reviewer supplement are preserved in
  `docs/project-harness/tasks/slice-3-c2-local-integration/`.
- Recorded Coordinate `plan.approved` event
  `c13bf777-85e3-4228-8996-6fe182ce3994` for reviewer
  `claude-code/glm-5.2`; the reviewer limitations are stated in the review artifact.
- The approved package authorizes only an isolated single-cherry-pick integration and
  validation worker. Coordinate `main` advancement, push, deploy, real runtime and
  multi-host smoke remain behind separate gates.

## 2026-07-12 — S3-C2 isolated integration candidate review

- Oh-My-Pi session `019f5490-4f9e-7000-a55c-7e68fc017b93` used provider/model
  `zhipu-coding-plan/glm-5.2` and performed the single authorized cherry-pick in the
  isolated Coordinate worktree.
- Candidate `e0cc1561cd20b0f22389234aefe92d01273860e4` has parent `8fadd687...`;
  its stable patch ID and raw diff SHA256 exactly match reviewed source `1b862129...`.
- Independent Codex review passed the exact eight-path and schema boundaries, focused
  342 tests, full 1,347 tests, checklist validation with 0 warnings, and clean-worktree
  check. Evidence is in `result-review-round-1.md`.
- The Operator independently located the OMP provider-native JSONL and corrected the
  worker's mistaken N/A claim in the review artifact.
- Result approval applies only to the isolated candidate. Coordinate `main` still points
  to `8fadd687...` and requires an explicit human gate before a final no-drift
  fast-forward. No push, deploy, runtime/DB/delivery mutation, SSH, or multi-host smoke
  occurred.

## 2026-07-12 — S3-C2 human-gated local main integration

- The user explicitly authorized advancing local Coordinate `main` to the independently
  reviewed S3-C2 candidate.
- Final no-drift checks confirmed main `8fadd687...`, candidate `e0cc1561...`,
  candidate parent equal to main, unchanged patch identity, exact eight paths, and clean
  candidate state.
- `git merge --ff-only e0cc1561cd20b0f22389234aefe92d01273860e4` advanced local
  Coordinate `main` without creating a new merge commit.
- Main-side validation passed: focused 342, full 1,347, checklist validation with 0
  warnings, and `git diff --check`. Coordinate `main` and the candidate branch now point
  to the same commit; `.qoder/` remains the only unrelated untracked path.
- Updated the durable audit, code-review summary, integration decision, result review,
  and stage overview to distinguish local-integration PASS from S3-C3 deployment and
  real multi-host PASS.
- No push, deploy, service/process control, real DB/delivery, SSH, or multi-host smoke
  occurred.
- Operator lifecycle closeout completed through the newly integrated completion receipt
  protocol: closeout `bf8122dc...`, review approval `48ac7ede...`, receipt
  `2b3e7a71-e045-4da2-8458-37d97fc0fd0a`, claim `214ed7e0...`, apply
  `81c4cd57...`, atomic `task.done` `d91f8b80...`, and consume `1bd5de48...`.
- Receipt before/after fingerprints were `0fd37fc8...` and `8e7afb53...`; deployed
  verification re-read the local canonical harness as `done/closed` with the same final
  fingerprint. Reconciliation updated the Coordinate task mirror to `closed`, and
  `operator pending` returned no S3-C2 action.

## 2026-07-12 — S3-C3 attempt 2 deployment and receipt smoke

- Worker verified all resume conditions: Mihomo alive upstream, Discord/PyPI probes
  200, both services active with NRestarts=0.
- Deployed exact approved SHAs (Coordinate `e0cc1561`, MultiNexus `82c5613`) via
  full-install/full-restart/full-smoke path using clean detached release worktrees.
  No `--skip-install`/`--no-restart`/`--no-smoke`/`--allow-dirty`.
- Initial deploy exit 1 was a false positive: pre-proxy-recovery breaker traces at
  14:09 CST fell within the smoke script's 10-minute journal window. Fresh-window
  re-run passed `server smoke OK`.
- Provisioned isolated sidecar workspace `s3c3-smoke-20260712T062036Z-e0cc1561`
  with full harness copy, 6 namespaced tasks (4 original + 2 fingerprint-drift retries).
- Receipt matrix all PASS: happy path (authorized→claimed→applied→task.done+consumed),
  replay (idempotent, no duplicate terminal), expiry (2s TTL rejected before mutation),
  fingerprint drift (before_fingerprint_mismatch), interrupted recovery (stale reject,
  sync, retry succeeds).
- Canonical `discord-nexus` zero drift: 29 tasks, 851 events unchanged.
- DB integrity ok, backup at `coord-backup-20260712T061733Z.db` (mode 0600).
- Evidence in `execution-report-attempt-2.md`. No package closeout or mark-done
  (Codex performs independent result review).

## 2026-07-12 — S3-C4 durable closeout documentation

Non-Codex documentation worker (Oh-My-Pi, session
`019f5529-c817-7000-97dc-46a68600a251`) prepared the bounded Slice 3 durable closeout
evidence package. The same session spans two provider/model intervals:
- initial document work and partial round-1 correction: `zhipu-coding-plan/glm-5.2`;
- correction continuation after explicit user-requested model switch on provider 429:
  `kimi-code/kimi-for-coding-highspeed` (high thinking), which completed validation and
  commit `19b0bc8825d65f4bf7859c7c66dab3e7cd344ec8`.

- Verified workspace gates: worktree
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-s3-c4-closeout`, branch
  `agents/mac-omp/slice-3-c4-durable-closeout`, recomputed plan SHA-256
  `6190b93f1ce28ed31d891019d758fddb01d1c7e01dda01b39fa2fb9b38cbe32b`, plan-review verdict
  approved (no P0/P1), and plan-ready/plan-approved events bound in the supplement and
  review artifact.
- Authored/updated exactly six documentation paths:
  - `tasks/slice-3-completion-closeout/closeout.md` (new roll-up index binding S3-C1
    through S3-C4 identities, separate verdicts, retained sidecar, residual-risk routing).
  - `source-of-truth-audit.md` (Slice 3 boundary: locally accepted → deployed and
    real-boundary verified; residual gaps preserved as open).
  - `tasks/slice-3-completion-closeout/plan.md` (appended S3-C3/S3-C4 executed status and
    closeout evidence pointer).
  - `roadmap.md` (current status note; preserved 2026-07-11 snapshot as historical).
  - `progress.md` (this entry).
  - `dogfood-feedback.md` (S3-C3/S3-C4 closeout-level dogfood grading and backlog routing).
- Bound exact deployed identities: Coordinate
  `e0cc1561cd20b0f22389234aefe92d01273860e4`, MultiNexus
  `82c5613f9d8fcb25c5ca936a24c61536e567df50`; services active NRestarts=0, proxy HTTP 200,
  DB integrity ok, server smoke OK; canonical `discord-nexus` 29 tasks / 851 events.
- Validation: `git diff --check` clean; `jq empty mvp-checklist.json` passed;
  `harnessctl validate` passed with the same six recorded warnings (no new warning);
  `harnessctl doctor` introduced no new MISS/invalid finding; `git diff --name-only`
  limited to the six allowed paths.
- Residual risks kept open and routed: stale interrupted-recovery projection
  (Slice 4), deploy non-atomicity and smoke-window false positive (deployment hardening),
  CLI ergonomics and missing workspace delete (`p9-0a1-cli-boundary-extraction`), missing
  full-dogfood host profile (multi-host agent runtime). Retained sidecar
  `s3c3-smoke-20260712T062036Z-e0cc1561` cleanup deferred and separately reviewed.
- Boundaries: no checklist/event/state JSON edit, no Coordinate lifecycle command, no
  SSH/deploy/restart/DB mutation, no push/merge, no Phase 9/Slice 4 implementation, no
  sidecar cleanup. The S3-C3/S3-C4/umbrella lifecycle remains Operator-only; this worker
  does not claim closure and does not mark itself done.
- R2 correction (this commit): `closeout.md` now keeps four Git authorities distinct
  (canonical `main` pre-integration `04048e1`, upstream `origin/main` `82c5613`, deployed
  MultiNexus `VERSION_DEPLOYED` `82c5613`, and isolated worker branch HEAD), and all
  three worker-owned documents record the GLM-to-Kimi provider/model transition within
  the same OMP session.

## 2026-07-12 — Slice 3 final Operator lifecycle closeout

- Codex result-review round 4 approved accepted S3-C4 worker tip `76137f2`; review
  artifacts are committed on canonical MultiNexus `main` through `31b5e5c`.
- Refreshed runtime evidence immediately before approval: deployed Coordinate
  `e0cc1561`, deployed MultiNexus `82c5613`, both services active with stable PID/start
  identity and `NRestarts=0` across two observations, Discord/PyPI HTTP 200, production
  DB integrity `ok`, canonical 29 tasks / 851 events, retained sidecar 6 / 89, and fresh
  `server smoke OK`.
- Closed S3-C3, S3-C4, and umbrella in dependency order through public Coordinate
  `closeout` → `review-result approved` → receipt-aware `mark-done-prepare/files/record`.
  Receipts: S3-C3 `ba8643c3-fdff-4d15-a8c0-a4d3c8012dcd`; S3-C4
  `2539f998-a9f9-47b1-b727-102f270465cb`; umbrella
  `aacafb58-f74e-4973-81f7-f8e70e96fbed`.
- Each package has exactly one authorized/claimed/applied/task.done/consumed terminal
  chain. No legacy mark-done, repair-only path, direct JSON edit, or direct SQLite edit
  was used.
- Supported reconciliation converged all three local Coordinate task mirrors to
  `closed`. Refreshed harness state reports Slice 3 `done/closed`; `operator pending`
  contains no Slice 3 action. Validation remains at the six pre-existing warnings and
  doctor reports no new finding.
- Retained S3-C3 sidecar evidence was not deleted. Accepted residual risks remain routed
  to P9-0A, Slice 4, deployment hardening, and later multi-host runtime work.

## 2026-07-12 — P9-0A1 CLI contract and support seam durable closeout

- Refreshed and independently reviewed the P9-0A1 plan through four Kimi rounds; exact
  approved SHA-256 is `00a52ea12a85f8e18aa6b9e56224ea5478b0ca7e21d3d2fc7e1ead0f540a3796`.
- Kimi worker session `019f559d-7e43-7000-87ed-84a38ee960aa` implemented three
  attributable commits (`dfdd036`, `c47e899`, `117ff5d`) in an isolated Coordinate
  worktree. Codex requested two correction rounds and approved Round 3.
- Integrated and pushed Coordinate `main`/`origin/main` at `117ff5d`. Exact scope is
  `cli.py`, new `cli_support.py`, contract test, and fixture; no domain handler moved.
- Canonical validation: four contract environment cases 19 passed each, alternate-HOME
  dump byte-identical, focused 350 passed, full 1,366 passed, fixture hash `83c4c181...`,
  no private path/import backedge/runtime-default regression.
- Closed through receipt `f1f8da57-57c9-4bc4-8f40-76e0c8158f4c`; event chain contains
  one authorized/claimed/applied/task.done/consumed sequence and reconcile converged to
  `closed`. Harness validate remains at the four historical review warnings.
- Dogfood remained semi-full: target-agent handoff failed on missing `macbook-local`
  execution profile, so the Operator used local OMP plus generated bootstrap/supplement.
  Also recorded stale pending delivery, cross-repo bootstrap, relative harness-root UX,
  and post-consumed preflight-status gaps.
- Exact evidence index: `tasks/p9-0a1-cli-boundary-extraction/closeout.md`.
- Next package: P9-0A2 workspace/planning/issue CLI extraction; it requires a fresh
  detailed plan and independent plan review before bootstrap.

## 2026-07-12 — P9-0A2 measured refinement and P9-0A2a plan checkpoint

- Refreshed the post-P9-0A1 Coordinate source at canonical `947368a`; `cli.py` is 2,688
  lines and the deterministic CLI contract remains 21 top-level commands, 75 leaves,
  and 99 parser nodes.
- Refined the former combined P9-0A2 package after measuring three separate service
  authorities: P9-0A2a workspace/state/reconcile, P9-0A2b event/task/plan/operator, and
  P9-0A2c issue. The split changes package boundaries, not the parent scope.
- P9-0A2a owns exactly 11 leaves and approximately 178 handler plus 91 registration
  lines. Its detailed plan preserves root handler aliases, ordered registration, and an
  exact contract delta limited to those 11 handler qualified names.
- Refreshed baselines are 231 focused tests and 1,366 full tests. No implementation,
  bootstrap, lifecycle mutation, deployment, or live-state operation is authorized by
  this checkpoint.
- Next gate: commit the exact plan revision, record its full SHA-256 in Coordinate, and
  obtain approval from an independent non-Codex reviewer before creating a worker
  bootstrap. P9-0A2b/c and later packages remain unauthorized.

## 2026-07-12 — P9-0A2a workspace/state/reconcile CLI durable closeout

- Independent Kimi plan review approved exact plan SHA-256 `24197103...f3598`; reviewer
  reproduced 231 focused and 1,366 full tests before implementation.
- Kimi worker session `019f55ce-6283-7000-be7b-0204c5d16138` produced implementation
  `e4c98ea` and review correction `10862d9`. Codex Round 1 rejected an ownership-only
  contract test; Round 2 approved after the full baseline-rewind verifier was added.
- Integrated and pushed Coordinate `main`/`origin/main` at `10862d9`. Exact scope is five
  approved paths, including new `workspace_cli.py` and `test_workspace_cli.py`.
- Canonical evidence: 21/75/99 unchanged; old/new fixture hashes `83c4c181...` /
  `652a77d5...`; 11/11 handler AST bodies identical; four environment hashes identical;
  37 contract/boundary and 1,384 full tests passed.
- Closed through receipt `b2fedbf8-d54c-4586-b3f9-04d3b2e683b9`; one
  authorized/claimed/applied/task.done/consumed chain exists and reconcile converged the
  task mirror to `closed`.
- Dogfood remained semi-full. Generated bootstraps needed exact supplements, and
  assignment request left pending delivery `30aeb26b-0346-41d5-8706-40eb3e480ff2`.
  Kimi completed without quota failure; GLM is the authorized fallback for future Kimi
  quota exhaustion, with model transitions recorded in JSONL and artifacts.
- Exact evidence index:
  `tasks/p9-0a2a-workspace-state-reconcile-cli/closeout.md`.
- Next package: P9-0A2b event/task/plan/operator CLI extraction; it requires its own
  detailed plan and independent review before bootstrap.

## 2026-07-12 — P9-0A2b detailed-plan checkpoint

- Refreshed Coordinate at canonical `10862d9`: `cli.py` is 2,422 lines and the accepted
  contract is 21 top-level / 75 leaves / 99 nodes with fixture SHA `652a77d5...`.
- Measured P9-0A2b as 10 event/task/plan/operator leaves and 178 handler lines. Two
  registrars are required because operator remains after assignment while event/task/
  plan are contiguous before runner.
- Detailed plan locks both the immediate P9-0A2a baseline (`652a77d5...`) and cumulative
  P9-0A1 baseline (`83c4c181...`) so later fixture regeneration cannot erase earlier
  contract proof.
- Refreshed baselines are 289 focused and 1,384 full tests. No implementation,
  bootstrap, lifecycle mutation, deployment, or live-state operation is authorized by
  this checkpoint.
- Next gate: commit the exact plan, bind its full SHA-256 in Coordinate, and obtain
  independent non-Codex approval. Kimi Highspeed is preferred; GLM is the explicit
  fallback if Kimi quota/auth/provider availability fails.

## 2026-07-12 — P9-0A2b implementation and durable closeout

- Kimi worker session `019f55ea-75fa-7000-949c-7d4216f9c4bc` implemented the exact
  five-path extraction. Codex review required one test-isolation correction (`d250e47`)
  before approving the integrated Coordinate tip `38da30f`.
- Contract remains 21/75/99. Layered rewinds reproduce P9-0A2a SHA `652a77d5...` and
  P9-0A1 SHA `83c4c181...`; 10 handler AST bodies are identical. Canonical 48 focused
  and 1,411 full tests pass.
- Receipt `4c85dd46-97b7-415f-85a1-450107e30112` completed authorized/claimed/applied/
  task.done/consumed with fingerprints `4fffae00...` → `52198c05...`.
- Lifecycle initially failed closed because deployed harness lacked the new task, then
  receipt claim failed closed because local/deployed lifecycle projections differed.
  Canonical deploy plus local replay through harnessctl aligned them; no direct JSON or
  DB edit was used.
- Global reconcile remains blocked by an unrelated historical Phase 8.7 branch conflict;
  P9-0A2b itself is canonical `done/closed` with a terminal receipt chain. Exact evidence:
  `tasks/p9-0a2b-event-task-plan-operator-cli/closeout.md`.
- Next package is P9-0A2c issue CLI extraction. It requires a fresh measured detailed
  plan, independent review, and new bootstrap.

## 2026-07-12 — P9-0A2c implementation and durable closeout

- Independent Kimi review approved exact plan SHA `d5ff4620...`; reviewer JSONL caught
  and discarded one full-suite run launched from the wrong MultiNexus cwd, then accepted
  1,411 Coordinate tests.
- Kimi worker session `019f5606-3bc7-7000-9bee-ebe1c0edfe31` produced implementation
  `3ae4f9f` and Codex-directed proof correction `d978d75`. Integrated Coordinate tip is
  `10135bc`.
- Exact five-path scope, `issues.py` unchanged, 21/75/99, fixture `dde4c0d7...`, three
  rewind hashes, five stable AST hashes, 288 focused and 1,434 full canonical tests pass.
- Receipt `2ce2cedc-33ca-4f4f-b66f-c9d6034c262a` completed one authorized/claimed/
  applied/task.done/consumed chain with `81f817dc...` → `47e96755...`.
- Local lifecycle replay was performed before receipt claim, avoiding the known
  source/deploy fingerprint mismatch. Global reconcile remains blocked by the old
  Phase 8.7 branch conflict, so the P9 task mirror remains stale while canonical files
  and terminal receipt events are authoritative.
- Exact evidence: `tasks/p9-0a2c-issue-cli/closeout.md`. Next package: P9-0A3; it needs
  fresh measurement, detailed plan, independent review, and worker bootstrap.

## 2026-07-12 — P9-0A3a runner/job/runtime CLI durable closeout

- Independent Kimi plan review approved exact corrected plan SHA
  `66784772...b9b`; Round 1 measurements were corrected from 166/107 to the exact
  P9-0A3a 159 and P9-0A3b 114 split before approval.
- Kimi worker session `019f56c5-b9bf-7000-8d0e-8a2876dbe6ff` produced implementation
  `d9faf1a`. Codex rejected whole-FunctionDef `ast.dump` hashes and the first
  `ast.unparse` correction; final correction `533ffcb` uses a canonical AST projection.
- Integrated and pushed Coordinate `main`/`origin/main` at `533ffcb`. Exact five-path
  scope, 21/75/99, fixture `fbdb5064...`, four layered rewinds, 58 structural, 243
  focused, and 1,467 full tests pass. Execution proof passes on Python 3.12.13/3.14.
- Receipt `19d917fb-fb66-49f8-91ad-92d95b8cc93f` completed one authorized/claimed/
  applied/task.done/consumed chain with `25f959d8...` -> `49c70c6d...`; deployed
  MultiNexus `247357d` was verified done/closed before the terminal record.
- Dogfood exposed an invalid `approve` enum attempt and a source/deployed lifecycle
  projection mismatch. Both failed closed; source was synchronized to the reviewed
  projection before the receipt was claimed. No repair path or direct DB edit was used.
- Exact evidence: `tasks/p9-0a3a-runner-job-runtime-cli/closeout.md`. Next package:
  P9-0A3b delivery/policy/worker CLI extraction; it requires a fresh detailed plan,
  independent review, and worker bootstrap.

## 2026-07-12 — P9-0A3b measured detailed-plan checkpoint

- Refreshed Coordinate at canonical `533ffcb`: root `cli.py` is 1,590 lines and the
  accepted contract remains 21/75/99 with fixture SHA `fbdb5064...`.
- Measured P9-0A3b as exactly ten delivery/policy/worker leaves and 114 handler lines
  (56 + 44 + 14) in one contiguous parser range after job and before runtime.
- Detailed plan keeps `BusError`/`PolicyError` in root, preserves direct aliases and
  output-stream/worker-loop behavior, and extends contract rewind through all five
  accepted fixture layers.
- Refreshed baseline is 382 focused and 1,467 full tests. The recent concurrent-pump
  `sending` race is recorded as Slice 4/P9 evidence and explicitly excluded from this
  behavior-preserving package.
- No implementation or bootstrap is authorized. Next gate: bind the exact plan SHA in
  Coordinate and obtain independent Kimi review, using GLM only on documented Kimi
  quota/auth/provider failure.

## 2026-07-12 — P9-0A3b delivery/policy/worker CLI durable closeout

- Independent Kimi plan review approved exact plan SHA `5a9438c...a2f`; worker session
  `019f56f4-79c4-7000-888a-05cc20a49cb5` produced `f1ccf37`, and Codex required
  correction `cfcb56f` to restore the out-of-scope removed `get_workspace` import.
- Integrated and pushed Coordinate `main`/`origin/main` at `cfcb56f`. Exact five-path
  scope, 21/75/99, fixture `0bb76d48...`, five layered rewinds, ten canonical AST
  body equalities, 53 boundary/contract, 384 focused, and 1,493 full tests pass.
- Receipt `63c3543b-bf56-45f2-bb40-8c2a805ed883` completed one authorized/claimed/
  applied/task.done/consumed chain with `955b7c5a...` -> `fca58d44...`; deployed
  MultiNexus `0eb1f06` was verified done/closed before the terminal record.
- The first record attempt used local `mac.sh` and failed closed with `unknown_receipt`;
  the required production `coord-ssh` replay succeeded idempotently. No repair, legacy
  mark-done, direct DB edit, duplicate terminal event, or provider fallback was used.
- Exact evidence: `tasks/p9-0a3b-delivery-policy-worker-cli/closeout.md`. Next package:
  P9-0A4 workflow/completion CLI extraction; it requires fresh measurement, detailed
  plan, independent non-Codex review, and a new worker bootstrap.

## 2026-07-12 — P9-0A4 refinement and P9-0A4a detailed-plan checkpoint

- Refreshed Coordinate at reviewed `origin/main@cfcb56f`: root `cli.py` is 1,369 lines;
  contract remains 21/75/99 with fixture SHA `0bb76d48...`; focused 371 and full 1,493
  tests pass.
- Measurement split the former P9-0A4: receipt completion is six leaves, 14 functions,
  510 span / 491 nonblank lines; the remaining workflow/assignment seam is 12 handlers
  and 254 handler lines. Combining them would exceed the bounded structural review
  surface.
- P9-0A4a introduces `completion_cli` first while root continues to own assignment;
  P9-0A4b later moves that parser into `workflow_cli` and calls the same completion
  registrar. This preserves the approved final architecture without a temporary cycle.
- No implementation or bootstrap is authorized. Next gate: bind the exact P9-0A4a plan
  SHA in Coordinate and obtain independent Kimi review, using GLM only on documented
  Kimi quota/auth/provider failure.

## 2026-07-13 — P9-0A4a receipt completion CLI durable closeout

- Independent Kimi review approved exact plan SHA `3f060777...6b28`; worker session
  `019f5714-06fb-7000-b60c-744542c54755` produced `41b6a9c`. Codex required
  correction `4526d09` so the safety-order test proves preflight -> claim -> write ->
  apply rather than omitting the write from its sequence.
- Integrated and pushed Coordinate `main`/`origin/main` at `4526d09`. Exact five-path
  scope, 21/75/99, fixture `a7c6e955...`, six rewinds, 14 AST body equalities, 59
  boundary/contract, 401 total focused, and 1,523 full tests pass.
- Receipt `23b7563a-89c7-4642-992f-5d50ebdefca0` completed one authorized/claimed/
  applied/task.done/consumed chain with `341aebe4...` -> `123063c7...`; deployed
  MultiNexus `92afd51` was verified done/closed before the terminal record.
- Dogfood recovered one legacy server-only task materialization through source
  `task create-files` + deploy + idempotent `task create-record`. Concurrent canonical
  edits were preserved in a named stash. No direct DB/JSON repair or provider fallback
  was used.
- Three more pump races ended with sent deliveries and no last error, strengthening the
  existing Slice 4/P9 runtime-hardening evidence without changing A4a behavior.
- Exact evidence: `tasks/p9-0a4a-receipt-completion-cli/closeout.md`. Next package:
  P9-0A4b workflow/assignment CLI extraction; it requires fresh measurement, detailed
  plan, independent non-Codex review, and a new worker bootstrap.

## 2026-07-13 — P9-0A4b measured detailed-plan checkpoint

- Refreshed Coordinate at canonical `4526d09`: root `cli.py` is 730 lines; contract is
  21/75/99 with fixture SHA `a7c6e955...`; focused 472 and full 1,523 tests pass.
- Measured exactly 12 workflow handlers / 254 lines and three parser seams totaling
  117 span / 102 nonblank lines. A single registrar would reorder the existing PR and
  middle domain families, so the plan uses three explicit static calls.
- Final dependency direction is `cli -> workflow_cli -> completion_cli`; assignment
  moves as a unit while the six receipt leaves remain owned and registered by
  `completion_cli`.
- No implementation or bootstrap is authorized. Next gate: bind the exact plan SHA and
  obtain independent Kimi review, with GLM only on documented Kimi quota/auth/provider
  failure.

## 2026-07-13 — P9-0A4b plan review Round 1 rejected

- Kimi session `019f572b-5869-7000-9063-ff9af65eea79` confirmed every measured source,
  contract, seam, test-baseline, ordering, and dependency claim.
- It rejected SHA `f331e84d...` because the existing P9-0A4a completion boundary test
  still requires three workflow handlers to be literal root definitions, while A4b
  moves them and preserves aliases. The allowed paths omitted that necessary test.
- Plan revision now authorizes only that boundary assertion to change from root
  `FunctionDef` checks to root alias/owner checks; `completion_cli.py`, receipt behavior,
  and other completion tests remain forbidden.
- No implementation/bootstrap is authorized until a new exact SHA receives independent
  approval.

## 2026-07-13 — P9-0A4b workflow/assignment CLI durable closeout

- Kimi Round 2 approved exact revised plan SHA `62a7f267...2f7c`; worker session
  `019f5735-f0ab-7000-9588-8e694e5c662a` produced `009533f`. Codex required
  correction `882c2a1` because the green suite did not yet prove fresh import orders
  across completion/workflow/root or lock the global dispatch tuple at the new boundary.
- Integrated and pushed Coordinate `main`/`origin/main` at `882c2a1`. Exact six-path
  scope, 21/75/99, fixture `43e18104...`, seven rewinds, 12 AST body equalities, 91
  boundary/contract, 440 service-focused, and 1,555 full tests pass.
- Receipt `1c9269e9-e7b5-442c-b856-d0216d62bdab` completed one authorized/claimed/
  applied/task.done/consumed chain with `dfceae7e...` -> `74282c7c...`; deployed
  MultiNexus `9ebf442` was verified done/closed before the terminal record.
- Dogfood required explicit source/deploy lifecycle replay after a documentation deploy
  correctly restored the still-`todo` canonical source projection. It also exposed that
  host-side completion reports harness project id `local` while the control workspace
  is `discord-nexus`; Slice 4 should represent both identities explicitly.
- Three observed concurrent-pump races ended `sent` with no last error. No direct
  JSON/DB repair, legacy mark-done, duplicate terminal event, or provider fallback was
  used.
- Exact evidence: `tasks/p9-0a4b-workflow-assignment-cli/closeout.md`. Next package:
  P9-0A5 event presentation; it requires refreshed measurement, a detailed plan,
  independent non-Codex review, and a fresh worker bootstrap.

## 2026-07-13 — P9-0A5 event presentation durable closeout

- Kimi Round 2 approved exact plan SHA `f8507735...3c1c2`; worker session
  `019f5760-6411-7000-8b40-45d5cd2e7ec7` produced `fa79fa6`. Codex removed two
  untracked shell artifacts and added correction `084419c` to close the boundary
  test's SQLite connection.
- Integrated and pushed Coordinate `main`/`origin/main` at `084419c`. Exact three-path
  scope, 44 + 1 portable witnesses, 34/34/31/3 partition, three cold import orders,
  264 focused, and 1,572 full tests pass under the known-good Python 3.14 baseline.
- Receipt `8529a3be-3226-4723-a7e5-584eea24d6ea` completed the authorized/claimed/
  applied/task.done/consumed chain with `214282df...` -> `9ec79aec...`; deployed
  MultiNexus `b562533` was verified done/closed before terminal record.
- One pre-replay receipt was rejected before claim on a source/deployed fingerprint
  mismatch. Source lifecycle replay, commit and deploy restored equality without direct
  JSON or DB repair.
- Generic handoff identity, control-vs-harness workspace identity, split-operation UX,
  pending direct assignment delivery, and recovered pump-race breaker behavior are
  routed to Slice 4/runtime hardening.
- Exact evidence: `tasks/p9-0a5-event-presentation-registry/closeout.md`. Next stage:
  refresh and independently review the Slice 4 detailed plan before any worker runs.

## 2026-07-13 — Slice 4A deterministic latest-event reads durable closeout

- Round 1 Kimi rejected a `tests.*` package-style validation command; revised plan SHA
  `dd4f8e5f...1360` uses explicit Python 3.14 discovery and received Round 2 approval.
- Worker Kimi session `019f577f-6121-7000-a0d3-d949c25202a9` produced `5986cc3`.
  Codex approved without correction after 39 daemon, 152 policy, 191 focused and 1,574
  full tests passed.
- Receipt `f779f41b-a487-42d4-8f07-981058ec2404` completed with `01e9b0e3...` ->
  `c151bdea...`; deployed `0b37b06` was verified done/closed.
- Codex rejected one corrected `plan.ready` whose declared new SHA disagreed with the
  server's old deployed content hash; docs deploy plus `fa38a7db...` restored identity.
- Exact evidence: `tasks/slice-4a-deterministic-latest-event-reads/closeout.md`. Next:
  detailed S4-B versioned replace-sync registry audit and plan review.

## 2026-07-13 — Slice 4B1 Coordinate agent registry model durable closeout

- Kimi worker session `019f579b-9317-7000-879a-acfa73577120` produced `6c340d4`.
  Codex rejected a silent no-audit compatibility shim, incorrect durable shadowed
  evidence and missing audit-failure rollback, then integrated correction `2bf835f` as
  Coordinate `ff6b8bf`.
- Final evidence is 40 agent-registry, 21 DB, 19 workspace CLI, 43 daemon, 33 contract,
  169 root CLI and 1,608 full tests; fixture `0c54732c...` rewinds to reviewed
  `43e18104...`.
- Production migrated v9 -> v10 after backup, preserving nine legacy/projected
  identities with zero authoritative sources before S4-B2. Both services are active
  and the daemon loaded the same nine effective identities.
- Receipt `dca68d10-f805-4cbf-af35-1ac73a8f86d4` completed authorized/claimed/applied/
  task.done/consumed with `3d5112f4...` -> `95f1e399...`.
- Dogfood recorded exact-plan gate recovery, relative harness-root fail-closed,
  `approve` vs `approved` vocabulary, `local` vs `discord-nexus` host identity and
  local-vs-server review evidence split. No direct DB/JSON repair or provider fallback
  was used.
- Exact evidence: `tasks/slice-4b1-coordinate-agent-registry-model/closeout.md`. Next:
  S4-B2 detailed plan and independent review for deployed roster authority integration.

## 2026-07-13 — Slice 4C1 task-create split operation contract

- Kimi session `019f5800-43f6-7000-a437-59b6aaf8d701` produced `f0fff49`; three
  Codex request-changes rounds closed exact-retry, envelope, target-ledger,
  persisted-intent, mirror-linkage and event-collision gaps. Final Coordinate head is
  `1cbb547`.
- Schema v11 and the neutral `split_operations` ledger are deployed after backup
  `coord.sqlite3.before-s4c1-20260712T205625Z.bak` (`b031c2fc...b0cb`), integrity
  `ok`. Both services and server smoke pass.
- Local and server isolated dogfood prove files-only detection, deploy then record,
  idempotent record retry, drift refusal and cleanup with no production task row.
- Receipt `c968e093-c5b0-4773-800c-0f17b1abd2dd` completed authorized/claimed/applied/
  task.done/consumed with fingerprint `5204d330...` -> `cfd6fc9e...`;
  `task.done=948ff132...` and `completion.consumed=61ec9d97...`.
- Dogfood exposed two durable operator gaps: remote lifecycle state does not flow back
  into Git source automatically, and code-sync/`VERSION_DEPLOYED` does not prove the
  venv package or DB schema was upgraded. Exact evidence is in
  `tasks/slice-4c1-task-create-operation-contract/closeout.md`.
