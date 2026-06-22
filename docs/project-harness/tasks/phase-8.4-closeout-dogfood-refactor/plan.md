# Phase 8.4 Closeout, Dogfood, and Boundary Refactor

## Ownership

- Operator / implementer: `codex`
- Independent reviewer: persistent Codex subagent assigned by the operator
- Source baseline:
  - coordinate `011df4a4c9c30ad69dff191471bd76f3fc054c23`
  - multinexus `b0358f1e06cbe51f2d5a2f6cc246a98bea302804`
- Human gates: merge, deletion, force-push, branch-protection changes

## Goal

Finish Phase 8.4 correctness, prove the host/server publish path with a real
non-merged dogfood PR, and then reduce the change risk of the largest Phase 8
modules through behavior-preserving extraction.

## Non-goals

- No automatic merge.
- No branch-protection or CI policy redesign.
- No new agent framework, repository layer, dependency-injection container, or
  class hierarchy solely for the refactor.
- No unrelated cleanup of stable modules.

## Stage A: Correctness closeout

1. Gate schema v9 migration by the pre-migration `PRAGMA user_version`.
2. Perform task-index replacement atomically under a write transaction; a
   failed rebuild leaves the prior indexes intact.
3. Make `publish_pr_existing` accept an empty/fresh host mirror when remote
   preflight supplied `expected_pr_url`; use GitHub discovery to verify URL,
   head SHA, and base before repairing the local mirror.
4. Read mirror identity through one compatibility helper supporting:
   - historical `payload.repo` / `payload.commit`;
   - current `payload.publish_metadata.repo` /
     `payload.publish_metadata.reported_commit`.
5. Validate malformed/version-skewed preflight envelopes before indexing
   `expected_pr_url`.
6. Add regression tests for real cross-DB rows and a concurrent migration
   writer.

### Stage A acceptance

- Opening a schema-v9 DB performs no task-index DROP/CREATE statements.
- A forced migration failure rolls back without losing the prior indexes.
- A fresh host DB can perform the second identical publish as `linked`, with
  one `gh pr list`, zero `gh pr create`, and successful remote replay.
- Sink-produced repo/commit mismatches fail preflight.
- Full tests, harness validation/doctor, and diff checks pass.

## Stage B: Independent review loop

The same reviewer subagent reviews every Stage A revision. It receives the full
plan, both repository diffs, historical Round 1-7 findings, tests, and remote
lifecycle constraints. The operator fixes all actionable findings and resubmits
until the reviewer explicitly reports no P1/P2 findings. Reviewer approval is
not merge authorization.

## Stage C: Real dogfood

1. Materialize this task in the source checkout and record it in the remote
   coordinator DB through the host-aware path.
2. Deploy the reviewed coordinate commit to Tencent Cloud and verify the
   running version plus schema migration.
3. Use a clean host DB and a pushed Codex branch to run:
   remote preflight -> GitHub remote verification -> PR create/link -> remote
   record-only sink.
4. Repeat from a second clean host DB and require a linked result with zero
   second create.
5. Inspect coordinator events, remote task mirror, delivery/policy output,
   GitHub PR, and existing CI/review/merge read-only gates.
6. Record friction in `progress.md` and `dogfood-feedback.md`. Fix bounded
   correctness/operability issues when safe; defer scope expansions as explicit
   checklist items.
7. Leave the PR open for the human gate.

## Stage D: Boundary refactor

Use separate branches based on the reviewed Stage A commit.

Stage C completed on 2026-06-22. Real PR #1 remains open and unmerged. The
final fresh-host replay at coordinate `6b0f0fa` produced no duplicate event or
mirror update; CI/review/merge gates remained closed. The runtime-only server
`gh` gap is explicitly deferred to the later host-side driver/record-sink
slice.

### Coordinate

- Extract schema/migration code from `db.py` while preserving `db.migrate` and
  `db.initialize` compatibility.
- Extract host publish orchestration and remote record/preflight operations
  from `prs.py`; keep `coordinate.prs` as the compatibility facade.
- Extract PR CLI parser registration, handlers, and forwarding helpers from
  `cli.py`; keep the root parser and command behavior stable.
- Split oversized PR/CLI tests by the same feature boundaries.

### Multinexus

- Extract coordinator/handoff request orchestration from
  `multinexus/client.py` behind the existing client facade.
- Extract the large agent request workflow from `cogs/agents.py` into a small
  orchestration module while preserving Discord-visible behavior.
- Split associated tests by behavior boundary.

### Refactor invariants

- No public CLI, event, JSON, database, task-state, or adapter contract change.
- No new abstraction without two real callers or two concrete variants.
- Every extraction is independently testable and committed separately.
- Record before/after file and largest-function line counts.

### Stage D implementation result

- coordinate compatibility facades now route to `schema.py`,
  `pr_publishing.py`, `pr_recording.py`, and `pr_cli.py`. `db.py` fell from
  1320 to 1090 lines, `prs.py` from 2353 to 234, and `cli.py` from 2417 to
  1871. Phase 8.4 PR tests moved from the generic 4911/3171-line test files to
  feature-specific `test_pr_cli.py` and `test_pr_publish.py`.
- multinexus moved coordinator handoff/lifecycle orchestration from
  `client.py` (1229 to 910 lines) to `coordinator_handoff.py`; the shared
  response chunker is independent. The agent request workflow moved from
  `cogs/agents.py` (1415 to 761 lines) to `cogs/agent_request.py`, preserving
  the Cog method through a mixin and explicit boundary tests.
- Public command names, handler signatures, facade imports, monkeypatch hooks,
  event JSON, DB schema, and Discord behavior remain covered. Full suites after
  extraction: coordinate 1084 OK; multinexus 314 OK (2 skipped), before adding
  the three boundary-contract tests.
- Reviewer round 1 rejected incomplete legacy import/patch surfaces. The final
  compatibility pass explicitly re-exports moved helpers and makes remote
  recording, coordinator lifecycle, and agent-request injection resolve via
  the old facades. Dedicated patch-effect tests verify the indirection rather
  than only checking attribute presence.

## Stage E: Final review and closeout

The same reviewer subagent reviews both refactor branches. The operator repeats
fix/review until clean, then pushes final commits, updates harness artifacts,
and reports the exact PR/branch/commit/lifecycle state. No merge is performed.

Completed 2026-06-22. Two refactor review rounds restored all legacy import and
patch surfaces; the persistent reviewer returned `APPROVED` with no actionable
P1/P2. Final suites: coordinate 1087 OK; multinexus 319 OK (2 skipped). Both
refactor branches are pushed and remain unmerged/undeployed.

## Verification commands

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

Dogfood verification additionally requires remote schema/version inspection,
coordinator event/mirror inspection, GitHub ref/PR inspection, and an explicit
assertion that the replay issued no `gh pr create`.
