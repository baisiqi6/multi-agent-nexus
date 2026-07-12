# Source-of-Truth Write-Path Audit

> **Status: audit plus Slice 1-2 implementation and Slice 3 local-integration snapshot, 2026-07-12.**
>
> This document is diagnostic evidence and a remediation record. It does not replace
> [product-definition.md](product-definition.md), the project checklist, Coordinate DB,
> Git, GitHub, or runtime configuration as an authority.

## Scope

This audit traces current mutable facts across:

- `/Users/yinxin/projects/coordinate`
- `/Users/yinxin/projects/multinexus`

It distinguishes:

- **authority** — the only place allowed to decide or mutate a fact;
- **projection** — a rebuildable or reconcilable view of an authority;
- **runtime scratch** — replaceable state owned by one execution attempt or session;
- **transcript** — human-visible communication that must not be re-ingested as fact
  unless it is explicitly acting as an authenticated command transport.

## Verdict

**Slice 1 and Slice 2 are implemented; Slice 3 is reviewer-accepted and integrated on
local Coordinate `main`, but is not pushed, deployed, or proven through real multi-host
execution.** The
overall authority split is viable and does not require a rewrite. Three originally
identified violations are resolved; the host-aware completion receipt gap is now closed at
code-review, local-test, and local-integration level and remains open for deployment:

1. Host-aware completion can advance harness and DB completion independently without a
   shared authorization receipt — the receipt protocol is now implemented and
   reviewer-accepted and integrated on local `main` (see the finding below); deployment
   and multi-host smoke remain separate gates.

Slice 1 and Slice 2 were implemented on 2026-07-10 without a schema migration. They scope
Discord authorization by workspace, remove the agentd-to-Discord report command loop, keep
task phase harness-owned, and derive Operator attention from deterministic events. Slice 3
added a one-time completion authorization receipt at the local checkpoint on 2026-07-11.

## Authority inventory

| Fact category | Intended authority | Current writers | Projections / scratch | Audit result |
|---|---|---|---|---|
| Shared product mission and roles | `product-definition.md` | Human-reviewed docs | README summaries | Clean after documentation repair |
| Project scope, plan, acceptance, task workflow, assignment owner/lease | Canonical harness files | `harnessctl`; Coordinate `HarnessAdapter`; host-side `*-files` commands | `harness-state.json`; Coordinate task rows | Phase projection repaired; completion receipt integrated on local Coordinate `main`, not yet deployed (see Slice 3 finding) |
| Runtime job, claim, attempt, liveness, result, delivery | Coordinate DB | `coordinate.runtime`, `coordinate.jobs`, `coordinate.bus` | CLI/UI/platform views | Clean core ownership; CAS protections are present |
| Runtime agent result and review evidence | Coordinate DB event ledger | Agentd result ingestion; Discord daemon ingestion in legacy direct mode | Visible report lines/cards | Resolved: managed agentd results are not re-posted as Discord commands |
| Static runtime agent configuration | Deployed MultiNexus `agents.toml` | Runtime operator/config deployment | Parsed `AgentConfig` and peer roster | Clear for invocation configuration |
| Workspace-to-agent Discord authorization | Coordinate workspace registry, derived from approved runtime config | Manual `workspace agent add`; manual `workspace agent sync` | Workspace-aware daemon in-memory map | Membership enforcement resolved; registry provenance/reload remains P2 |
| Runtime agent presence and liveness | Coordinate `agents` table | Agentd/bridge register + heartbeat | Health views | Separate fact; not a duplicate of static config |
| Agent native session and resume identifier | MultiNexus/runtime session store | Bridge/agentd | Coordinate job summaries | Clean runtime scratch ownership |
| Visible conversation context | MultiNexus context store | Discord/KOOK bridges | Prompt context | Clean, explicitly non-authoritative |
| Code, commit, branch | Git | Git clients/workers | Coordinate task/event references | Correct authority; Coordinate must continue verifying current refs |
| PR, CI, review, merge state | GitHub/configured forge | Forge | Coordinate last-known events and gate evidence | Correct projection model; refresh required before gates |
| Harness machine-readable summary | Canonical harness files | `build_harness_state.py` only | `harness-state.json` | Clean derived projection |
| Local harness event log | Harness runtime | `harnessctl` scripts | `harness-state.json.recent_events` | Optional local audit trail, not Coordinate runtime authority |
| Legacy MultiNexus `persistence.db.jobs` | None in current managed runtime | No active current caller found | Legacy schema/methods | Dead compatibility storage, not an active competing authority |

## Findings

### [P1][Resolved 2026-07-10] Scope Discord agent authorization to the target workspace

Resolution evidence:

- `coordinate/src/coordinate/daemon.py:89,111-126` stores a fresh
  `discord_user_id -> {workspace_id: agent_name}` map on each successful registry load.
- `coordinate/src/coordinate/daemon.py:160-176` parses the report and rejects it before
  `_do_ingest` unless the author is registered in the reported workspace.
- `coordinate/tests/test_daemon.py` covers same-workspace acceptance, cross-workspace
  rejection, duplicate Discord IDs across workspaces, and stale-entry replacement.

Prevented abuse sequence:

1. Agent A is registered only in workspace A.
2. Agent A posts a valid `[agent-report]` with `workspace_id=B`.
3. The daemon finds no `(A, workspace B)` membership, logs a warning, and returns.
4. No event or mark-done transition is attempted for workspace B.

Implemented behavior:

- Store daemon authorization as `(workspace_id, discord_user_id) -> agent_name`, or
  `discord_user_id -> {workspace_id: agent_name}`.
- Parse the report, then verify the author is registered for exactly that workspace
  before calling `_do_ingest`.
- Reject cross-workspace reports visibly and without writing an event.
- Regression tests prove allowed same-workspace and rejected cross-workspace reports.

### [P1][Resolved 2026-07-10] Do not re-ingest agentd report projections through Discord

Resolution evidence:

- `coordinate/src/coordinate/runtime.py:388-408` records a terminal job, parses the
  response, and appends runtime report/review events without mutating harness phase.
- `coordinate/src/coordinate/runtime.py:584-650` gives these events runtime-specific
  idempotency keys and `source=runtime`.
- `multinexus/coordinator_handoff.py:125-180,263-317` renders human-visible worker and
  reviewer text but sends extracted report blocks only in direct-adapter mode.
- `multinexus/coordinator_handoff.py:378-380` uses `reply.platform=none` for handoff
  runtime requests, matching the normal agentd bridge path.
- `multinexus/coordinator_handoff.py:416-428` disables Discord fallback reports in
  `agentd_mode`; Coordinate already owns the runtime result.
- `multinexus/handoff_handler.py` extracts both action reports and review-decision blocks,
  including multiline review output, before visible rendering.
- `multinexus/tests/test_coordinator_handoff_runtime.py` covers no worker/reviewer report
  echo in agentd mode, human-visible summaries, no fallback echo, and preserved direct
  delivery.

Divergence sequence:

1. Agentd reports `done` to Coordinate.
2. Coordinate writes `job.completed` and runtime `agent.reported`; Operator attention is
   derived from those events rather than persisted into task phase.
3. MultiNexus removes the report block from visible text and does not post it as a new
   Discord message.
4. The canonical runtime event chain remains the only managed-mode result path.

Implemented behavior:

- In `agentd_mode`, never post machine-ingestable report lines after Coordinate has
  already recorded the result.
- Render a human summary or a non-command marker such as `[runtime-report-recorded]`.
- Keep raw report posting only for the legacy direct-adapter path where Discord is the
  actual command transport.
- Use `reply.platform=none` consistently for handoff runtime requests, matching the
  normal agentd bridge path.
- Tests now assert no raw worker or reviewer report line and do assert the human-visible
  summary.

### [P1][Locally integrated 2026-07-12; deployment remains open]

The host-aware completion gap documented below is now closed at code-review, local-test,
and local-integration level. The reviewed patch is on local Coordinate `main`; it is not
pushed, deployed, or verified through real multi-host execution.

Pre-Slice-3 divergence evidence (context retained):

- `coordinate/src/coordinate/transitions.py` documented that `mark_done_files` bypassed
  `_check_mark_done_gate`.
- `mark_done_files` directly wrote canonical `status=done` and `workflow.status=closed`.
- `mark_done_record` did not read harness state or validate a gate.
- `mark_done_record` independently appended `task.done`; `verification` was optional.
- Running only `mark-done-files` made the canonical harness done while Coordinate lacked
  the completion event; running only `mark-done-record` did the reverse; neither proved
  that the same review/gate evidence authorized both writes.

Accepted local receipt protocol (reviewer-approved at the checkpoint):

```text
completion.authorized
  -> completion.claimed        # remote reserve before canonical write
  -> completion.applied        # remote acknowledgement after verified write
  -> task.done + completion.consumed   # atomic server terminal
```

The receipt binds workspace, task, authorized actor, expiry, gate/forge evidence, and
lifecycle fingerprints. The coding host must use the online remote CLI path; no-receipt
split commands are repair-only and require a non-empty reason.

Checkpoint and integration identity (re-verified during S3-C2, 2026-07-12):

- Worker checkpoint commit `1b862129897be001e5a9078b7b4fad48d90d89c2` on branch
  `agents/mac-claude/slice-3-completion-receipt`, parent and merge-base against Coordinate
  `main` `a2ad92d2bf13ec894979c082897a713f3870d130`, stable patch ID
  `eb204296bd6a09e4caccabfe4bb05802e7ef7b37`.
- Reviewer verdict (Codex, independent code/result reviewer): approve for a local
  checkpoint only.
- Accepted prior-review evidence rechecked against the review report by this audit
  worker (the suites were not rerun here): full suite `1347 passed, 58 subtests passed`;
  focus counts transitions 131, CLI 169, completion 42; `git diff --check` and harness
  checklist validation passed; the final adversarial retry returned
  `before_fingerprint_mismatch` and left the canonical item `doing/blocked`.
- Reviewed file set, accepted protocol, adversarial rounds, and the provider session
  handle are recorded durably in
  [tasks/slice-3-completion-closeout/local-code-review.md](tasks/slice-3-completion-closeout/local-code-review.md).
- S3-C2 cherry-picked the reviewed patch onto base
  `8fadd687d68032cf656291e6bf537ec481fb3e25`, producing
  `e0cc1561cd20b0f22389234aefe92d01273860e4`. Source and integrated stable patch IDs
  both equal `eb204296bd6a09e4caccabfe4bb05802e7ef7b37`; raw diff SHA256 is identical.
- After explicit human authorization, local Coordinate `main` fast-forwarded to
  `e0cc1561`. Main-side verification passed: focused 342, full 1,347, checklist 0
  warnings, exact eight paths, and no DDL/schema-version change.

Boundary this audit must not overstate:

- The receipt is accepted as local code and local integration, not as pushed, deployed,
  or multi-host PASS.
- The executed S3-C2 method and evidence are recorded in
  [tasks/slice-3-completion-closeout/integration-decision.md](tasks/slice-3-completion-closeout/integration-decision.md).
- Real `coord-ssh`, SSH, and remote-DB behavior is covered only through mocked subprocess
  boundaries in the local suite.

Non-blocking maintainability notes retained for follow-up (not S3-C1 scope):

- `src/coordinate/completion.py` is large; state authority is centralized, not
  duplicated, so this is a simplification opportunity rather than a correctness blocker.
- `latest_event()` materializes all matching rows; a later slice can use
  `ORDER BY rowid DESC LIMIT 1`.

### [P1][Resolved 2026-07-10] Separate harness phase from Operator-attention state

Resolution evidence:

- `coordinate/src/coordinate/runtime.py:388-408` records job/report/review events without
  writing `awaiting_operator` into the task mirror.
- `coordinate/src/coordinate/plan_gate.py:145-157,203-215` records plan decisions while
  preserving the existing harness-derived phase.
- `coordinate/src/coordinate/reconcile.py:101-112` always applies the current harness
  phase; legacy `awaiting_operator` overlays are no longer preserved.
- `coordinate/src/coordinate/operator.py:35-120` derives Operator actions from harness
  phase plus current event evidence and suppresses any task with terminal phase or a
  `task.done` event.
- `coordinate/src/coordinate/operator.py:142-217` uses deterministic event ordering and
  exposes the DB snapshot version and staleness contract.
- `coordinate/src/coordinate/cli.py:2063-2070` returns that snapshot metadata alongside
  pending actions.

Observed behavior after the fix:

After a task has a `task.done` event, `operator pending` returns no action even if a late
agent report arrives afterward. Legacy `awaiting_operator` rows remain readable but are
replaced by the harness phase on the next reconcile.

Implemented behavior:

- Keep the task mirror's harness lifecycle field a pure projection.
- Represent plan decisions and runtime attention in the event ledger rather than phase.
- Derive Operator action from report/review/plan events at query time.
- Suppress pending actions after terminal phase or any `task.done` event.
- `operator pending` does not refresh harness; it reports `harness_refreshed=false`,
  `may_be_stale=true`, the task-mirror update time, and latest event rowid/id/time.

### [P2][Operator path resolved 2026-07-10] Make latest-event ordering deterministic

Evidence:

- `coordinate/src/coordinate/db.py:50-51` stores timestamps with one-second precision.
- `coordinate/src/coordinate/operator.py:170-187` now orders decision-relevant events by
  `created_at DESC, rowid DESC`.
- CI, PR review, and handoff queries already use `created_at DESC, rowid DESC`.

The Operator decision path is deterministic and has same-second regression coverage.
Two lower-priority read paths still use timestamp-only ordering: daemon task-status display
and policy owner fallback. Add `rowid DESC` there during Slice 4 hardening.

### [P2] Bind split file/record operations with an operation ID and fingerprints

Evidence:

- `coordinate/src/coordinate/onboarding.py:198-218` writes DB mirror/event before the
  legacy command updates `mvp-checklist.json`.
- `coordinate/src/coordinate/onboarding.py:232-310` performs mirror/event/mirror updates
  in separate commits.
- `coordinate/src/coordinate/issues.py:983-1048` performs DB-only issue materialization
  in multiple independently committed steps.

These paths are retryable and mostly fail closed later, but crashes can leave partial
state that is indistinguishable from an intentionally completed half of a host-aware
operation. Use one stable operation ID plus input/output fingerprints across `*-files`
and `*-record`; group purely DB-side writes in one SQLite transaction.

### [P2] Treat `agents_json` as a replaceable authorization projection

Evidence:

- `coordinate/src/coordinate/db.py:397-466` merges registry entries by default and keeps
  absent/removed entries unless `replace=True`.
- `coordinate/src/coordinate/cli.py:256-268` makes `--replace` optional.
- `coordinate/src/coordinate/daemon.py:105-125` loads the registry only at startup.
- No automatic MultiNexus deployment/start path currently synchronizes the registry.

Consequences:

- A removed Discord agent ID may remain authorized.
- A newly configured ID may not be recognized until manual sync and daemon restart.
- Manual `workspace agent add` can diverge from deployed `agents.toml` indefinitely.

Required fix:

- Declare the approved deployed agent roster as the source for static identity.
- Store a source path/version/hash with each workspace registry projection.
- Make authoritative sync replace removed entries, report the diff, and reload the daemon.
- Keep manual additions as explicit, auditable overrides with expiry or reason.

## Safe existing boundaries

The audit found several areas that should not be rewritten merely because data appears in
more than one place:

- Coordinate job/claim/result state is authoritative and MultiNexus agentd acts as a
  client. Attempt tokens and SQL CAS protect stale results.
- MultiNexus session IDs and context messages are legitimate runtime scratch state.
- `harness-state.json` is generated from canonical harness files and is correctly treated
  as a projection.
- Coordinate delivery rows and platform message IDs are an outbox plus delivery evidence;
  the visible platform message is not another lifecycle authority.
- Git/GitHub remain authoritative for code and forge facts. Coordinate's records are
  last-known evidence and current gate paths refresh head/review/CI state.
- Legacy MultiNexus `persistence.db.jobs` is not used by the current agentd path and does
  not currently compete with Coordinate jobs.

## Remediation order

### Slice 1 — Stop unauthorized and recursive ingestion — complete 2026-07-10

1. Scope daemon agent authorization by workspace.
2. Stop posting raw report commands in `agentd_mode`.
3. Add regression tests covering cross-workspace rejection and no runtime-report echo.

Implemented without a schema migration. It prevents cross-workspace transcript input and
managed-runtime report projections from advancing the wrong lifecycle.

### Slice 2 — Correct Operator pending semantics — complete 2026-07-10

1. Add deterministic event ordering.
2. Suppress pending actions after `task.done`.
3. Separate `awaiting_operator` from harness phase, either as a new field or an event-derived
   query result.
4. Add version/staleness information to pending-action output.

Implemented as an event-derived query without a schema migration. Runtime and plan-gate
decisions no longer overwrite harness phase; terminal tasks cannot be reopened by late
reports; CLI output states that it did not refresh the harness and exposes its DB version.

### Slice 3 — Authorize completion once — local integration accepted 2026-07-12

1. Introduce a completion authorization receipt. — done at checkpoint.
2. Bind host-side and server-side mark-done operations to that receipt. — done at
   checkpoint.
3. Demote current split commands to explicit repair-only compatibility paths. — done at
   checkpoint.

Local code acceptance is recorded in
[tasks/slice-3-completion-closeout/local-code-review.md](tasks/slice-3-completion-closeout/local-code-review.md).
The executed local integration method and evidence for S3-C2 are recorded in
[tasks/slice-3-completion-closeout/integration-decision.md](tasks/slice-3-completion-closeout/integration-decision.md).
Deployment, real multi-host smoke, and umbrella closeout remain separate, explicitly
authorized gates (S3-C3, S3-C4).

### Slice 4 — Harden projections and split operations

1. Version and replace-sync the workspace agent registry.
2. Add operation IDs/fingerprints to host-aware file/record pairs.
3. Make related DB event/mirror writes transactional.
4. Add doctor checks for stale registry, partial operations, and task-mirror drift.

## Acceptance criteria for the first implementation slice

- An agent registered only in workspace A cannot write any report event for workspace B.
- An agentd result produces one canonical report/review event chain, not a second chain
  through Discord.
- Agentd-mode completed-response output contains no raw machine-ingestable result or
  review command.
- Legacy direct mode continues to deliver structured reports through Discord.
- Existing runtime job CAS, session resume, and visible human summaries continue working.
- Tests fail before each fix and pass after it.

All criteria passed on 2026-07-10. Validation evidence:

- Coordinate focused suites: 83 tests passed.
- MultiNexus focused suites: 76 tests passed.
- Coordinate full suite: 1,256 tests passed.
- MultiNexus full suite: 350 tests passed, 2 skipped.
- Coordinate harness validation passed with 0 warnings.
- MultiNexus harness validation passed with the same 4 pre-existing review warnings.
- `git diff --check` passed in both repositories.

## Acceptance criteria for the second implementation slice

- Runtime completion and plan decisions do not overwrite the harness-derived task phase.
- Reconcile replaces legacy `awaiting_operator` values with the current harness phase.
- `task.done` suppresses all pending actions, including after a late agent report.
- Same-second plan/report decisions use insertion order as a deterministic tie-breaker.
- Approved review evidence yields `mark_done`; rejected review evidence never does.
- `operator pending` identifies its sources, version, lack of harness refresh, and possible
  staleness.
- Existing public commands and DB schema remain compatible.

All criteria passed on 2026-07-10. Validation evidence:

- Slice 2 focused suites: 213 tests passed across operator, runtime, reconcile, plan gate,
  and CLI.
- Coordinate full suite: 1,263 tests passed.

## Acceptance criteria for the third implementation slice (local integration)

- A completion authorization receipt is issued once and binds workspace, task, authorized
  actor, expiry, and lifecycle fingerprints.
- Host-side files and server-side record operations are bound to the same receipt; the
  no-receipt split commands are repair-only and require a non-empty reason.
- Forge, actor binding, fingerprint drift, expiry, replay, fail-after-write, and
  idempotent retry drift are covered by adversarial probes.
- The receipt lifecycle is `completion.authorized -> completion.claimed ->
  completion.applied -> task.done + completion.consumed`.
Criteria met at the local checkpoint on 2026-07-11 and on local Coordinate `main` on
2026-07-12. Final main-side reviewer evidence:

- Full local suite: 1,347 passed.
- Focus counts: transitions 131, CLI 169, completion 42.
- `git diff --check`: passed. Harness checklist validation for the Slice 3 change set:
  passed with 0 warnings.
- Final adversarial retry probe returned `before_fingerprint_mismatch` and left the
  canonical item `doing/blocked`.

This is a local code-review, local-test, and local-integration PASS. It is not push,
deployment, or real multi-host PASS; those remain S3-C3/S3-C4 gates.
