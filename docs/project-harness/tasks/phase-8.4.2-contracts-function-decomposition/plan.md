# Phase 8.4.2 Stable Contracts And Function Decomposition

## Ownership and branches

- Operator / reviewer: `codex`
- Coding agent: `mac-claude`
- Task id: `phase-8.4.2-contracts-function-decomposition`
- coordinate branch: `agents/mac-claude/phase-8.4.2-contracts-function-decomposition`
  from `origin/agents/codex/phase-8.4.1-boundary-refactor`
  (`63cdafb5c42f84a44c210872b5c5d4ef0aa7c58c` at planning time)
- multinexus branch: `agents/mac-claude/phase-8.4.2-contracts-function-decomposition`
  from `origin/agents/codex/phase-8.4.1-boundary-refactor`
  (`0ffe32dc9dded6e6599110ee1282db4c820edb9f` at planning time)
- Human gates: merge, deployment, deletion, force-push, branch protection, and
  any real GitHub PR write performed by the implementation.

## Goal

Reduce the remaining function-level coupling left after Phase 8.4.1 without
changing public behavior. Establish one explicit PR contract/validation layer,
turn `publish_pr()` into a short orchestrator over validation/discovery/
persistence stages, and turn `handle_agent_request()` into a short orchestrator
over invocation/response processing/follow-up stages.

## Current pressure

- `pr_publishing.py::publish_pr()` is about 432 lines.
- `pr_recording.py` still consumes publish invariants through compatibility
  helpers that originated as private implementation details.
- `cogs/agent_request.py::handle_agent_request()` is about 634 lines and mixes
  request flags, history/memory, backend invocation, response tags, persistence,
  fallback, handoffs, and research dispatch.
- Existing facades and monkeypatch hooks are intentionally broad because the
  refactor had to preserve the historical import surface. This task must make
  the new direct dependencies stable while keeping those old imports working.

## Non-goals

- Do not split `db.py` into table-specific repositories.
- Do not add CI/review host drivers, GitHub Actions, branch protection, fork PR
  support, merge automation, or new user-facing commands.
- Do not change SQLite schema, event types, payload fields, idempotency keys,
  CLI arguments/exit codes/JSON, Discord text/order, adapter protocols, or
  harness lifecycle semantics.
- Do not install new dependencies or introduce a DI container/framework.
- Do not perform real `gh pr create`, deploy, merge, or mark the task done.

## Workstream A — PR contracts and validation

Create a small public module such as `src/coordinate/pr_contracts.py` that owns
only stable Phase 8.4 data/validation contracts. The final names may differ if
the code shows a clearer boundary, but the dependency direction is fixed:

```text
github primitives ──> PR contracts/validation
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      host publishing              remote recording
             └─────────────┬─────────────┘
                           ▼
                    compatibility facade
```

Requirements:

1. Define the canonical publish actions and immutable fact/result shapes in one
   place. Reuse the existing dataclasses where possible; do not create parallel
   envelopes with almost-identical fields.
2. Move pure shared invariants there: canonical action→event mapping,
   idempotency-key construction, mirror publish identity extraction/conflict
   comparison, and success fact validation that is common to host and sink.
3. `pr_recording.py` must not import private helpers from `pr_publishing.py` and
   must not route its normal production dependency through `coordinate.prs`.
4. `pr_publishing.py` and `pr_recording.py` import documented public contract
   functions/types directly. DB-owning checks may stay in their service module
   if they are not genuinely shared.
5. `coordinate.prs` keeps all currently tested legacy exports and patch hooks.
   Compatibility wrappers may delegate to contracts, but production modules
   must not depend back on the facade.
6. Add import-cycle tests and contract tests covering all four actions,
   idempotency keys, legacy/current mirror metadata, malformed success facts,
   and hostile rebind inputs.

### Workstream A acceptance

- No import from `pr_recording.py` to `pr_publishing.py` private names.
- No production call from `pr_recording.py` back through `coordinate.prs`.
- Legacy `coordinate.prs` imports and established patch-effect tests remain
  green.
- Event types, payloads, idempotency keys, and mirror writes are byte-for-byte
  equivalent for the existing behavior matrix.

## Workstream B — `publish_pr()` decomposition

Refactor the host flow into explicit stages. Prefer plain functions and one or
two small dataclasses over classes or inheritance.

Recommended responsibilities:

1. `validate_publish_request(...)`
   - strict repo/branch/base/commit/pushed/head-owner validation;
   - workspace/mirror/cross-task/rebind preconditions;
   - no GitHub write;
   - returns validated facts or the existing typed blocked outcome.
2. `discover_publish_target(...)`
   - fetch remote ref;
   - distinguish remote-ref missing, SHA mismatch, existing matching PR, and no
     matching PR;
   - preserve the exact `gh` command order and call count;
   - never writes the DB.
3. `persist_publish_outcome(...)`
   - emit the existing `push.required`, `publish.blocked`, `pr.linked`, or
     `pr.created` event;
   - update mirror only on successful canonical outcomes;
   - preserve audit fields and idempotency semantics.
4. `publish_pr(...)` becomes orchestration only. Target: roughly 150 lines or
   fewer, unless a documented reason shows that a slightly larger function is
   safer.

Do not combine GitHub creation with DB recording in a generic catch-all helper.
The irreversible GitHub write and local/remote record boundaries must remain
visibly distinct.

### Workstream B tests

- Existing create/link/push-required/blocked matrix, call counts, replay,
  same-repo/fork filtering, SHA/base mismatch, audit fields, cross-task
  uniqueness, and PR-rebind tests remain unchanged and green.
- Add focused stage tests so failures identify validation, discovery, or
  persistence rather than only exercising the 4xx-line orchestrator.
- No real GitHub write.

## Workstream C — `handle_agent_request()` decomposition

Keep `Agents.handle_agent_request` as the public async entry point through the
current mixin, but split internal responsibilities inside
`cogs/agent_request.py`. Use small internal dataclasses only where they carry a
real result across stages.

Required stages:

1. Invocation preparation and backend call
   - parse `--project`, `--long`, and Codex `-t` flags;
   - enforce depth/allowlist/agent lookup;
   - load history, ephemeral context, memory, workspace/session, mission, and
     wiki context;
   - create/start job and invoke local/research/cloud adapter with identical
     call/resume/fallback and timeout arguments;
   - return response text, metadata, job identity, placeholder/progress state,
     and any state needed by later stages.
2. Response tag processing
   - process SCRATCH, DISCOVERY, WIKI, WIKI-PRIVATE, and RESEARCH in the current
     order;
   - keep page validation, aliases, audit text, secret filtering, persistence,
     placeholder edits, private-wiki buttons, and message ordering unchanged;
   - return clean response plus handoff/research/private-page outputs.
3. Failure/fallback and follow-ups
   - keep rate-limit fallback chain and offline/timeout partial-save behavior;
   - complete job accounting/audit;
   - dispatch handoffs with the same depth/channel rules;
   - trigger researcher follow-ups in the same order.
4. `handle_agent_request()` should mainly coordinate these stages. Target:
   roughly 180 lines or fewer. Individual helpers should normally stay below
   250 lines; document any exception rather than hiding it in another giant
   function.

### Workstream C tests

- Preserve all existing Discord-visible response order and AllowedMentions.
- Add focused tests for flag parsing, invocation arguments, tag processing
  order/output, rate-limit fallback, timeout partial persistence, handoff depth,
  and research follow-up ordering.
- Existing coordinator handoff, task-session, N+M, adapter, and command suites
  remain green.

## Commit discipline

Use reviewable commits in this order:

1. `refactor: establish PR publish contracts`
2. `refactor: decompose host PR publishing stages`
3. `refactor: decompose agent request workflow`
4. `test/docs: lock function-level contracts` (only if needed separately)

Do not mix unrelated formatting or generated file churn. Do not force-push.

## Verification

Baseline at planning time:

- coordinate refactor branch: 1089 tests OK.
- multinexus refactor branch: 319 tests OK (2 skipped).

Required final verification:

```bash
# coordinate
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
scripts/harness/harnessctl validate
scripts/harness/harnessctl doctor
git diff --check

# multinexus
/Users/yinxin/projects/multinexus/.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
scripts/harness/harnessctl validate
scripts/harness/harnessctl doctor
git diff --check
```

Also report before/after line counts for `publish_pr`,
`handle_agent_request`, their containing modules, and every new stage helper.

## Closeout protocol

- Claude commits and pushes both worker branches and sends one parseable,
  unfenced `[agent-report] action=progress|done ...` block.
- Coding-agent completion is not review or merge authority.
- Reviewer `codex` independently reviews both diffs and may request fixes.
- Only after `review.completed decision=approved` may the operator mark done.
- Leave all branches/PRs unmerged and do not deploy unless a human explicitly
  authorizes it later.
