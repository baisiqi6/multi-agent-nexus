# P9-3C0 Coordinate Package 1 — Scope Addendum

Status: **draft; requires independent review before worker may use this scope**

Parent bootstrap SHA-256:
`3c6cbfeb6d96bbba8b4a6fbe87eab1d8b99bcbeb6e49750e63df69582c7cbdbb`

Coordinate base SHA:
`3eaa7bfdeb0f660da46bd7fe6003231822c9658c`

## Why this addendum exists

The first Package 1 implementation run exposed one test-contract conflict that
cannot be resolved inside the original allowed-file list without weakening the
approved fail-closed behavior.

`tests/test_execution_leases.py::LeaseReserveTests::test_conflicting_replay_fails`
currently creates an active lease, syncs a capacity catalog version bump that
replaces the lease's exact `capacity_policy_id`, and expects that sync to succeed.
It then expects a later replay to fail.

The approved bootstrap intentionally moves the failure boundary earlier:
`sync_capacity_catalog` must reject every removal or replacement of an exact old
policy id referenced by an active lease, with zero mutation. Version, catalog hash,
or capacity changes all produce a replacement policy id and therefore must be
blocked while the lease is active.

The base test passes at `3eaa7bf`, while the approved implementation correctly
makes it fail at the sync call. Preserving the old test would contradict the new
active-lease authority contract.

## Minimal scope expansion

Authorize one additional test file only:

- `tests/test_execution_leases.py`

Within that file, the worker may modify only
`LeaseReserveTests.test_conflicting_replay_fails` (and imports strictly required by
that test) so it asserts the new failure boundary:

1. reserve the active lease;
2. snapshot relevant capacity source and policy rows field-for-field;
3. attempt the version/hash policy-id replacement;
4. assert `CapacityError` with a concise active-lease replacement error;
5. assert source/policy rows are byte-for-byte/field-for-field unchanged;
6. assert the original active lease remains active and exact replay remains
   idempotent against the unchanged policy.

Do not weaken `sync_capacity_catalog`, bypass the exact policy-id comparison, end
or mutate the active lease merely to keep the old expectation, or change any other
lease/runtime behavior.

## Verification baseline

The Coordinate base currently has nine unrelated full-suite failures:

- eight historical CLI contract fixture/hash rewind failures in
  `tests/test_cli_contract.py`;
- one historical handler AST hash failure in `tests/test_issue_cli.py`.

These reproduce on the unmodified `3eaa7bf` main checkout and are outside Package 1.
Package 1 acceptance therefore requires:

- the focused Package 1 suites are green;
- `tests/test_execution_leases.py` is green;
- a full suite has exactly the same nine known baseline failures and no new failure;
- `git diff --check` passes;
- the final diff contains only the parent bootstrap files plus the single lease-test
  scope above.

Exact commands:

```bash
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest -q \
  tests/test_executor_capacity.py tests/test_execution_cli.py tests/test_execution_leases.py
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest -q
git diff --check
git status --short
```

The worker must report the full-suite baseline comparison explicitly. This addendum
does not authorize push, merge, deploy, service restart, production DB work,
fixture/job/lease creation, Package 2, Package 3, schema changes, snapshot/restore
changes, or any additional file.
