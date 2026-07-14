# P9-3A Code Result Review — Round 3

**Verdict:** `changes_requested`

**Durable review event:** `5a483e9c-b5ef-4543-aac1-16d86b9b40dc`

**Reviewed implementation:**

- Coordinate: `375669b7e7b80db715cfbd59b1d48bfff6960cb0`
- MultiNexus code: `4a4af5cf09620b57a49a5ba3f280657856aee042`
- MultiNexus report: `80afa37fdb2868c1083e527a249f451cc9e2df5b`
- Worker: `deepseek/deepseek-v4-pro`
- Provider session: `019f5e3b-f14f-7000-b378-852af19e41fa`
- Approved plan SHA-256:
  `d75486b42e8d3315bda488db1129e02c03c0a2c152c04a60cccce917a385d99e`

No push, merge, deployment, SSH, service action, or production DB mutation is
authorized by this review.

## Independent verification

Coordinate focused:

```text
PYTHONPATH=src python -m pytest \
  tests/test_executor_capacity.py \
  tests/test_execution_resources.py \
  tests/test_execution_leases.py \
  tests/test_db.py \
  tests/test_execution_cli.py \
  --import-mode=importlib -q
206 passed, 5 subtests passed
```

Coordinate full:

```text
PYTHONPATH=src python -m pytest tests/ --import-mode=importlib -q
9 failed, 2294 passed, 493 subtests passed
```

The nine failures are the unchanged historical baseline: eight
`tests/test_cli_contract.py` rewind/hash failures and
`tests/test_issue_cli.py::IssueCLIOwnershipTests::test_all_five_handler_ast_bodies_match_start_revision`.

MultiNexus focused:

```text
PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest \
  tests/test_executor_capacity_authority.py \
  tests/test_deploy_contract.py \
  tests/test_smoke_contract.py -q
34 passed
```

MultiNexus full, run alone because deploy contract fixtures use a shared remote
staging name:

```text
PYTHONPATH=. /Users/yinxin/projects/multinexus/.venv/bin/python -m pytest tests -q
526 passed, 2 skipped, 1 warning, 36 subtests passed
```

Green suites do not close the must-fix findings below.

## Must-fix findings

### R3.1 — Restore accepts internally consistent snapshot coverage drift

`restore_capacity_snapshot()` calls `_strict_validate_captured_state()` but never
compares an existing snapshot's policy agents with the current enabled typed executor
bindings. Removing one otherwise-valid policy, recomputing the canonical digest, and
restoring is accepted. The resulting capacity projection no longer covers the executor
projection.

Required correction:

- inside the restore transaction and before any DELETE, require snapshot policy agent ids
  to equal `_enabled_typed_agent_ids(conn)` when `captured_state` is non-null;
- add a recomputed-digest adversarial test proving zero writes on missing and extra policy
  coverage;
- prior absence remains exempt from snapshot coverage.

### R3.2 — Snapshot timestamp validation checks only shape

`_validate_snapshot_timestamp()` accepts impossible timestamps such as
`2026-99-99T99:99:99Z`. A strict timestamp contract requires both exact canonical shape
and real calendar/time validation.

Required correction:

- parse with strict UTC `datetime.strptime(..., "%Y-%m-%dT%H:%M:%SZ")` or equivalent;
- retain exact `Z` shape and reject non-canonical offsets/fractions;
- add source and policy adversarial cases with recomputed digest.

### R3.3 — Current DB corruption is deleted before complete validation

Before DELETE, restore validates only a subset of the current projection. Two direct
probes are accepted:

- target-source policy exists while the target source row is absent;
- current policy has a shaped but recomputation-invalid `capacity_policy_id`.

Current source path/timestamp, policy label/capacity/timestamps/policy id, duplicate or
coverage state must be validated with the same strict contract used for captured state.

Required correction:

- construct and strict-validate the complete current target state before DELETE;
- reject a target policy when the target source is absent;
- reject all current shape, policy-id, source linkage, and enabled-binding coverage drift;
- preserve exact corrupt bytes/rows on failure.

### R3.4 — Atomic write failure can leave a valid-looking output

If `os.replace()` succeeds and the following `os.chmod()` raises, `_atomic_write_snapshot()`
removes only the temporary path. `capture_capacity_snapshot()` still has
`file_written=False`, so the final snapshot remains even though capture failed.

Required correction:

- track final replacement and remove the final path on every post-replace failure;
- add a deterministic `chmod` failure test asserting exception, rollback, and no output;
- keep successful final mode exactly `0600`.

### R3.5 — Deploy cleanup and double-failure lifecycle remain incomplete

The guarded source-mutation path still executes
`restore_previous_accepted_state ... || true`. Capture failure returns before a cleanup
trap exists, and the constant backup path is neither unique nor cleaned on success or
failure. Tests do not prove snapshot, staging, and backup residue is absent.

Required correction:

- handle restore failure explicitly and emit a distinct loud recovery-failure stage; do
  not use `|| true` on restore;
- clean a potentially created snapshot when capture fails;
- make the backup path per-deploy or remove stale backup before use, and clean it in both
  accepted and rollback paths;
- retain only best-effort cleanup inside the EXIT trap; explicit success cleanup must be
  checked;
- add success, rollback, capture-failure, source-mutation double-failure, and restore-hard-
  failure assertions for cleanup commands and remote residue.

### R3.6 — Fault tests do not perform the claimed exact comparison

`_snapshot_full_db_state()` selects only subsets of columns; timestamps, source paths,
and other row fields are omitted. `_assert_db_state_matches()` is unused. Each test takes
its snapshot after rollback and compares it with hand-written selected tuples rather than
recording the complete accepted pre-state and comparing the complete post-state.

Required correction:

- seed the complete previous accepted roster, executor, and capacity projections;
- capture complete ordered rows before mutation, including all table columns;
- compare complete post-rollback rows to that pre-state via one used helper;
- compare exact authority bytes independently;
- for prior absence, record complete roster/executor pre-state and exact empty capacity;
- for restore hard failure, assert only the components actually restored and explicitly
  prove capacity was not falsely reported restored.

### R3.7 — Implementation report overstates evidence

The report labels R3-1 correct, claims all five fault tests use exact tuple comparison,
and substitutes a 52-test file run for the Coordinate full suite. Those claims conflict
with the probes and exact full run above.

Required correction:

- append a Round-5 correction section; do not rewrite the historical worker claim;
- record the exact independent full-suite counts and this review event;
- state only evidence actually established by the corrected tests and final reviewer gate.

## Reproduced probe outcome

The reviewer constructed canonical, recomputed-digest inputs and observed:

```json
{
  "snapshot_coverage_drift": "ACCEPTED",
  "invalid_timestamp": "ACCEPTED",
  "current_bad_policy_id": "ACCEPTED",
  "current_target_orphan": "ACCEPTED",
  "chmod_failure_output_exists": true
}
```

These are implementation correctness failures inside the already approved rollback
amendment. No plan revision is required. A bounded Round-5 coding correction may proceed.
