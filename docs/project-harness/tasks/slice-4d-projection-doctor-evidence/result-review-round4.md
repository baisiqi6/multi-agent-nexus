# Slice 4D Result Review — Round 4

## Decision

**CHANGES_REQUESTED** for correction commit `21bfb88` on top of `313e366`.

R3-1, R3-2, and R3-4 are closed by independent executable review. The ordinary
dict/list deep-freeze path in R3-3 is also closed. One public-input form still bypasses
recursive freezing, so the report model is not yet genuinely immutable. The package
remains unauthorized for merge, push, deploy, production dogfood, mark-done, or
closeout.

## Closed Round 3 findings

- `completion.applied.before_fingerprint` is required and linked in both preflight and
  doctor. Independent missing and mismatch reproductions fail closed.
- Every receipt-chain fingerprint now requires canonical 64-character lowercase
  hexadecimal SHA-256 form. A mutually linked malformed chain fails closed.
- `_S4D_REWIND_SOURCE` is removed. The rewind uses shape-guarded node-level changes,
  and injected unrelated statements cause `AssertionError` instead of being silently
  overwritten.
- The accidental `tests/__init__.py` is removed; full collection is performed with
  `--import-mode=importlib` to avoid the unrelated external `tests` package.
- `src/coordinate/cli.py` remains byte-identical to `a21d946`.

## Independent verification

```text
focused:
  124 passed, 77 subtests passed

full (`pytest tests --import-mode=importlib -q`):
  1833 passed, 449 subtests passed, 9 failed
```

The nine failures are the same historical `test_cli_contract.py` (8) and
`test_issue_cli.py` (1) hash failures. No new full-suite failure was introduced.

## Remaining must-fix finding

### R4-1 — Pre-frozen mappings retain mutable nested values (P1)

`_freeze` recognizes only concrete `dict`; it returns `MappingProxyType` and other
`Mapping` implementations unchanged. `Finding.__post_init__` also conditionally skips
assignment when the frozen tuple compares equal to the original, and
`ProjectionReport.__post_init__` skips freezing whenever `summary` is already a
`MappingProxyType`.

These are valid inputs under the public field types and both remain mutable below the
outer proxy:

```text
Finding(evidence=(MappingProxyType({"nested": {"items": []}}), ...))
  evidence[0]["nested"]["items"].append("mutated") succeeds

ProjectionReport(summary=MappingProxyType({"errors": []}), ...)
  summary["errors"].append("mutated") succeeds
```

Freeze any `collections.abc.Mapping` by recursively copying its contents into a new
`MappingProxyType`; do not trust an existing proxy. In both dataclass post-init paths,
always replace the public attribute with the recursively frozen result rather than
using equality or outer-type shortcuts. Preserve recursive thaw/copy isolation in
`to_dict()`.

Add tests for:

1. tuple-of-`MappingProxyType` evidence with nested dict/list;
2. already-proxied summary with a nested mutable value;
3. a non-`dict` `Mapping` implementation if practical;
4. `to_dict()` returning independent mutable JSON-compatible copies for these inputs.

## Correction boundary

Continue on the same branch. This correction should touch only
`src/coordinate/projection_doctor.py` and `tests/test_projection_doctor.py`. Do not
change receipt logic, AST rewind tests, `src/coordinate/cli.py`, MultiNexus plan bytes,
or `tests/__init__.py`. No push, deploy, production, or lifecycle closeout. A fifth
Codex result review is required.
