# P9-0A1 Result Review — Round 1

- Reviewer: Codex
- Mode: correctness/tests/structure review
- Worker: Kimi Code Highspeed through Oh-My-Pi (`mac-omp`)
- Worker session: `019f559d-7e43-7000-87ed-84a38ee960aa`
- Start SHA: `e0cc1561cd20b0f22389234aefe92d01273860e4`
- Reviewed worker commit: `dfdd03681b0c53675e52b75fdcd50c5e6bc419bf`
- Approved plan SHA-256:
  `00a52ea12a85f8e18aa6b9e56224ea5478b0ca7e21d3d2fc7e1ead0f540a3796`
- Verdict: `changes_requested`

## Scope and positive evidence

The worker changed only the four approved paths:

- `src/coordinate/cli.py`
- `src/coordinate/cli_support.py`
- `tests/test_cli_contract.py`
- `tests/fixtures/cli_contract.json`

The support extraction is small and acyclic, root aliases remain present, the worker
reported 21 top-level commands / 75 leaves / 99 parser nodes, and the clean-environment
contract/focused/full suites passed. Codex independently confirmed the clean contract
suite passes and the fixture hash is
`d9701e13c0ce5913d2c35bc54100f719c837f4668cf8b8d0aba3498a47e51090`.

These positives do not close the acceptance gaps below.

## Must-fix findings

### 1. Contract tests are not isolated from the parent DB override

`tests/test_cli_contract.py:192-198` calls `build_parser()` in the parent test process
without removing `MULTI_AGENT_COORDINATOR_DB`. Codex ran:

```bash
MULTI_AGENT_COORDINATOR_DB=/tmp/p9-review-poison.sqlite3 \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python3 -m unittest tests.test_cli_contract -v
```

The suite failed because the parser default became the injected path. The two fixture
subprocesses are sanitized, but the contract test module as a whole is not deterministic
under a legitimate caller environment. Isolate every direct parser build used for the
baseline/semantic assertions while preserving the public runtime override behavior.

### 2. The committed fixture contains host-specific personal paths

`tests/fixtures/cli_contract.json:3419`, `:3447`, `:8745`, and `:8788` contain
`/Users/yinxin/.local/bin/coord-ssh`. The approved plan forbids arbitrary local paths in
the fixture and the scope/privacy acceptance case requires no local paths. Existing help
semantics should remain locked, but host identity must be normalized deterministically,
for example `<HOME>/.local/bin/coord-ssh`, in both action help and rendered parser help.
Add a broad assertion that fixture bytes contain no `/Users/` path, not only that the
exact `DEFAULT_DB_PATH` is absent.

### 3. The callable-handler invariant is not actually tested

`tests/test_cli_contract.py:175-190` inspects the normalized contract where callable
handlers have already become strings, then asserts only `isinstance(..., str)`. Codex
patched `_build_contract()` in memory with a leaf whose handler was the non-callable
string `"not.callable"`; the test passed. Inspect the raw parser leaf defaults and assert
that there is exactly one `handler` value and that it is callable. Keep the qualified
name in the fixture as separate serialization evidence.

### 4. The default-path relationship assertion is too weak

`tests/test_cli_contract.py:195-197` only checks that the string ends with
`/data/coordinator.sqlite3`; any unrelated absolute prefix would pass. Replace it with a
semantic exact relationship that preserves the current canonical Coordinate DB default
without embedding checkout-specific bytes in the fixture, such as comparison against
`Path.home() / "projects/coordinate/data/coordinator.sqlite3"` if that is the actual
preserved authority. Do not change runtime default behavior in this fix.

## Optional hardening

`_build_contract()` stops at the first `_SubParsersAction` per parser. Current Coordinate
has one at most, so this is not a current regression. An explicit assertion of that
structural invariant would prevent a future second subparser action from being only
partially represented.

Temporary directories in import-order tests should preferably use
`TemporaryDirectory()` contexts instead of unmanaged `mkdtemp()`, but this is not an
acceptance blocker.

## Required next evidence

- a new worker commit on top of `dfdd036` (do not amend);
- clean and poisoned-environment contract suites both pass;
- no `/Users/` or checkout-specific path remains in the fixture;
- a negative test proves a non-callable leaf handler is rejected;
- exact default-path semantic assertion passes;
- focused CLI/PR and full discovery suites pass with no regression;
- changed paths remain within the approved four paths.

No integration, push, deploy, or lifecycle closeout is approved by this review.
