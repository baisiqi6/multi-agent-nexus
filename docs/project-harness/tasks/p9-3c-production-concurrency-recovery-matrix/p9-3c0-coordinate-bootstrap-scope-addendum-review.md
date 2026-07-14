# P9-3C0 Coordinate Package 1 — Scope Addendum Independent Review

Reviewer: Claude (plan/scope reviewer, read-only)
Date: 2026-07-15

## Reviewed hashes

| Artifact | Expected SHA-256 | Verified |
|---|---|---|
| Addendum | `ffe9f4fbb7f20836536bcbd16771b2ea8132a7e1fb0c7d9cb83a68e6049c97a4` | ✅ matches |
| Parent bootstrap | `3c6cbfeb6d96bbba8b4a6fbe87eab1d8b99bcbeb6e49750e63df69582c7cbdbb` | ✅ matches |
| Coordinate base SHA | `3eaa7bfdeb0f660da46bd7fe6003231822c9658c` | ✅ referenced consistently |

## Findings

### P0 (blockers)

None.

### P1 (significant concerns)

None.

### P2 (minor suggestions / clarity nits)

1. **Baseline reporting burden:** The addendum requires the worker to "report the full-suite baseline comparison explicitly." Consider having the worker attach the before/after failure lists verbatim in the completion report so Codex can diff them mechanically. This is already implied by the acceptance criteria and does not block approval.

## Six-point focused assessment

### 1. Single-test scope

**Verdict: PASS.**

The addendum authorizes only `tests/test_execution_leases.py` and, within it, only `LeaseReserveTests.test_conflicting_replay_fails` plus imports strictly required by that test. It does not authorize changes to `src/coordinate/executor_capacity.py`, `src/coordinate/execution_cli.py`, schema, snapshots, or any other lease/runtime module. The current worktree diff confirms `test_execution_leases.py` is untouched, which is the expected starting state.

### 2. New assertions match the approved fail-closed contract

**Verdict: PASS.**

The addendum mandates:

- reserve an active lease;
- snapshot source/policy rows field-for-field;
- attempt a version/hash bump that produces a replacement `capacity_policy_id`;
- assert `CapacityError` with a concise active-lease replacement error;
- assert source/policy rows are unchanged;
- assert the original lease stays active and exact replay remains idempotent.

This directly verifies the parent bootstrap's active-lease replacement/removal guard: sync fails at the sync stage, leaves zero mutation, preserves the active lease, and keeps idempotent replay possible against the unchanged policy.

### 3. No weakening of guards or lease termination

**Verdict: PASS.**

The addendum explicitly forbids:

- weakening `sync_capacity_catalog`;
- bypassing the exact policy-id comparison;
- ending or mutating the active lease merely to preserve the old test expectation;
- changing any other lease/runtime behavior.

The prescribed failure boundary stays inside `sync_capacity_catalog`, consistent with the parent bootstrap.

### 4. Full-suite baseline gate

**Verdict: PASS.**

The addendum names the nine known Coordinate base failures (eight in `tests/test_cli_contract.py`, one in `tests/test_issue_cli.py`) and states they reproduce on the unmodified base. Acceptance requires the focused Package 1 suites to be green, `tests/test_execution_leases.py` to be green, and the full suite to have exactly those nine known failures with no new failure. The worker must report the baseline comparison explicitly. This is a clear, verifiable gate.

### 5. Parent bootstrap boundaries preserved

**Verdict: PASS.**

The addendum repeats the parent bootstrap's prohibitions: no push, merge, deploy, service restart, production DB work, fixture/job/lease creation, Package 2, Package 3, schema changes, snapshot/restore changes, or any additional file. It does not relax any of the parent bootstrap's fail-closed stop conditions.

### 6. P0/P1 safety / executability gaps

**Verdict: PASS.**

No P0 or P1 gaps were identified. The required test change is small, mechanical, and executable with the existing in-memory test helpers. The only new import needed (`CapacityError`) falls under "imports strictly required by that test."

## Authorization boundary

This addendum, if approved, authorizes the worker to modify **only**:

- `tests/test_execution_leases.py`
- specifically `LeaseReserveTests.test_conflicting_replay_fails`
- and imports strictly required by that test (e.g., `CapacityError` from `coordinate.executor_capacity`)

It does **not** authorize changes to:

- `src/coordinate/executor_capacity.py`
- `src/coordinate/execution_cli.py`
- any other source, test, schema, migration, snapshot, or deploy artifact
- push, merge, deploy, service restart, production DB operations, fixture/job/lease creation, Package 2, or Package 3

## Verdict

`APPROVED_FOR_P9_3C0_COORDINATE_SCOPE_EXPANSION`
