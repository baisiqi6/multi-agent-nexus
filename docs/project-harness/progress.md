# Project Harness Progress

Harness root: `docs/project-harness/`

## 2026-06-22

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
