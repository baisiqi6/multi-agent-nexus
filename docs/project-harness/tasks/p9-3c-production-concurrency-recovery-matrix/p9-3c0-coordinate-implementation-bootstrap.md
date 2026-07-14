# P9-3C0 Coordinate Capacity-Source Decoupling — Implementation Bootstrap

Status: **draft; requires independent bootstrap review before worker launch**  
Worker role: coding worker for the Coordinate repository only  
Reviewer/operator: Codex  
Implementation package: P9-3C0 Package 1 only

## Authorization chain

- P9-3C0 measurement SHA-256:
  `bd52cf986283d190cb5bc80434102172b46d09eb14324c492ddfb8cc01b6d4ab`
- P9-3C0 implementation plan SHA-256:
  `f57f01e739f742df75c553a9507fbbda722fd618e1a114956bfc072a91eb8829`
- Independent plan verdict:
  `APPROVED_FOR_P9_3C0_COORDINATE_BOOTSTRAP_ONLY`
- Plan review:
  `p9-3c0-fixture-plan-review-round3.md`

This bootstrap does not authorize itself. The worker may start only after an independent
review approves the exact bootstrap hash.

## Fixed repository and branch

- Repository: `/Users/yinxin/projects/coordinate`
- Base branch: `main`
- Base SHA: `3eaa7bfdeb0f660da46bd7fe6003231822c9658c`
- Required worker branch:
  `agents/mac-claude/p9-3c0-capacity-source-decoupling-coordinate`
- Required isolated worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3c0-capacity-source-decoupling`

The operator creates the branch/worktree from the exact base before worker launch. The
worker must stop if `HEAD`, branch, or worktree path differs. The untracked `.qoder/` in
the main checkout is user-owned and out of scope; do not read, copy, delete, stage, or
commit it.

## Goal

Decouple capacity authority sources without weakening the global runtime invariant:

- each source may own a disjoint partial set of capacity policies;
- the proposed union across all sources must cover every enabled typed executor;
- a policy may target an existing enabled or disabled typed binding, but never an
  unknown/untyped id;
- another source may not take over an existing `agent_id` policy;
- any mutation that would replace/remove a policy id referenced by an active lease must
  fail with zero mutation;
- existing canonical single-source behavior and CLI contracts remain compatible.

This enables later fixture staging:

1. executor source v1 creates E1/E2 disabled bindings;
2. capacity source v1 adds E1/E2 policies;
3. executor source v2 enables E1/E2;
4. after terminal cleanup, executor v3 disables them;
5. capacity v2 becomes empty;
6. executor v4 becomes empty.

The worker implements only Coordinate's capacity-source behavior. It must not create
fixture agents, catalogs, processes, services, jobs, or leases.

## Allowed files

Primary implementation:

- `src/coordinate/executor_capacity.py`

Tests:

- `tests/test_executor_capacity.py`
- `tests/test_execution_cli.py` only for CLI error propagation/output regression tests

`src/coordinate/execution_cli.py` may be modified only if a failing focused test proves
that a minimal compatibility change is required. Any other file requires reviewer
approval and a new bootstrap revision. Do not modify schema, migrations, executor
identity/routing/runtime modules, doctor/projection code, docs, packaging, deploy
scripts, or snapshots.

## Required implementation semantics

Work inside the existing `sync_capacity_catalog` transaction. Preserve current version
and hash error precedence, deterministic result fields, and idempotent retry behavior.

### 1. Source version/hash gate

- version downgrade: fail, zero mutation;
- same version/different hash: fail, zero mutation;
- same version/same hash: may return `changed=false` only after the current global
  ownership/known-binding/union invariants are revalidated.

### 2. Existing `source_id` is ownership

- Do not add a column or schema migration.
- For every proposed catalog `agent_id`, query the existing policy owner.
- If an existing row is owned by another source, fail with a deterministic ownership
  error before any write.

### 3. Known-binding guard

- Read all `executor_instance_bindings.agent_id`, including disabled bindings.
- Every policy in the proposed catalog must target one of those typed bindings.
- Unknown/untyped ids fail with zero mutation.

### 4. Proposed post-sync union

Before any write, construct the policy-agent union as:

- all current policy agents owned by other sources;
- plus all agents in the proposed catalog for this source.

Require every `enabled=1` executor binding to appear in that proposed union. Policies
for existing disabled typed bindings are allowed for safe staging. Do not require one
source to cover the whole enabled set.

### 5. Active-lease replacement/removal guard

Compute the exact old capacity policy ids owned by this source and the exact new policy
ids produced by the proposed catalog. If any old id absent from the new-id set is
referenced by `execution_attempt_leases.status='active'`, fail with zero mutation.

This guard covers both removal and replacement/update: changing source version,
catalog hash, or `max_concurrent_jobs` changes `capacity_policy_id` and must not orphan
an active lease. Reuse existing digest helpers; do not weaken lease identity.

### 6. Atomic replacement and empty source

Only after all guards pass, replace this source's policies atomically using the existing
tables. A higher-version empty fixture capacity source is allowed only when the proposed
union still covers every enabled typed binding and no active lease references an old
policy id. Preserve the source metadata row and return deterministic added/updated/
removed/unchanged agent-id lists.

## Required tests

Add focused tests that prove, at minimum:

1. the existing single canonical source remains compatible;
2. two disjoint sources can jointly cover enabled typed executors;
3. a partial source fails when the proposed global union misses an enabled binding;
4. a policy for an existing disabled typed binding is accepted;
5. an unknown/untyped policy id fails with zero mutation;
6. cross-source takeover of an existing `agent_id` fails with zero mutation;
7. removing an old policy id referenced by an active lease fails with zero mutation;
8. replacing an active policy id by version/hash/capacity change also fails with zero
   mutation;
9. after fixture bindings are disabled and leases are inactive, a higher-version empty
   fixture source succeeds and removes only that source's policies;
10. emptying the fixture source while its binding is still enabled fails union coverage;
11. version downgrade, same-version/different-hash, and exact idempotent retry retain
    their contract; idempotent retry still revalidates global invariants;
12. CLI returns nonzero with a concise `error:` for each new rejection and preserves
    existing JSON output for success/list/show.

Each zero-mutation test must snapshot the relevant source/policy rows before the call
and compare them after the rejected call. Do not rely only on exception text.

## Verification commands

Run from the isolated Coordinate worktree:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_executor_capacity.py tests/test_execution_cli.py
PYTHONPATH=src .venv/bin/python -m pytest -q
git diff --check
git status --short
```

If the repository venv is absent in the new worktree, use the read-only interpreter
from `/Users/yinxin/projects/coordinate/.venv/bin/python` with `PYTHONPATH=src`; do not
install or upgrade dependencies.

## Worker completion contract

The worker may make one local commit on the required branch after all focused tests
pass. It must not push, merge, deploy, restart services, touch production DB, or run
fixture jobs/leases.

Return:

- commit SHA and exact changed-file list;
- focused and full test command/result/count/duration;
- concise explanation of the proposed-union algorithm and active-policy replacement
  guard;
- any residual risk or scope deviation;
- provider-native JSONL session path supplied by the operator.

Codex will independently inspect the diff, rerun tests, and decide acceptance. A worker
commit or green tests do not authorize merge/deploy or Package 2.

## Fail-closed stop conditions

Stop without committing if:

- base/branch/worktree does not match;
- any file outside the allowed set appears modified;
- a schema change seems necessary;
- ownership would be inferred without using the existing `source_id`;
- a rejected sync leaves any source/policy mutation;
- an active policy id can be replaced or removed;
- full tests reveal an unrelated regression that cannot be explained without expanding
  scope.

