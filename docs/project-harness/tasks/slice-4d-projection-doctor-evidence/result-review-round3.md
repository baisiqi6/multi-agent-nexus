# Slice 4D Result Review — Round 3

## Decision

**CHANGES_REQUESTED** for correction commit `313e366` on top of `03c4d2b`.

Round 2 closes the missing checks it explicitly implements and removes the global
`Finding.evidence_dict` monkey-patch. The independent review still reproduces four
P1 contract/proof gaps. This package remains unauthorized for merge, push, deploy,
production dogfood, mark-done, or closeout.

## Independent verification

- `src/coordinate/cli.py` remains byte-identical to `a21d946` (`git diff --quiet`
  returned 0).
- The worker's focused suite reports `99 passed, 77 subtests`.
- The worker's full suite reports `1808 passed, 9 failed`, matching the known
  historical failure count after it added `tests/__init__.py`.
- Reviewer executable reproductions show the following invalid chains are still
  accepted as healthy terminal receipts by both preflight and doctor:

```text
missing applied.before:
  preflight => status=consumed, broken=None
  doctor    => ok=True, receipt_terminal/info

mismatched applied.before:
  preflight => status=consumed, broken=None
  doctor    => ok=True, receipt_terminal/info

malformed linked fingerprints ("not-a-sha" / "also-not-a-sha"):
  preflight => status=consumed, broken=None
  doctor    => ok=True, receipt_terminal/info

nested evidence mutation:
  finding.evidence[0]["nested"]["items"].append("mutated") succeeds
```

## Remaining must-fix findings

### R3-1 — `completion.applied.before_fingerprint` is not validated (P1)

`completion_cli.py` and `projection_doctor.py` read only
`completion.applied.after_fingerprint`. They neither require
`completion.applied.before_fingerprint` nor compare it back to the authorized/claimed
before fingerprint. The new fixtures omit this field by default, so the green tests
encode the incomplete contract.

Require the field in both preflight and doctor. Missing is
`receipt_chain_incomplete`; mismatch is `receipt_chain_conflict`. Add independent
missing and mismatch tests for both paths, and make every valid fixture include the
field.

### R3-2 — Fingerprint format is never validated (P1)

The implementation checks only truthiness and equality. Arbitrary non-empty strings
are accepted when linked strings match. Every fingerprint in this receipt chain must
be a canonical SHA-256 value: exactly 64 lowercase hexadecimal characters. Validate
`authorized.harness_fingerprint`, claimed before/expected-after, applied
before/after, and `task.done.applied_fingerprint` in both paths. Malformed values must
fail closed even if mutually equal. Add per-transition malformed tests plus at least
one complete mutually-equal malformed-chain regression.

### R3-3 — Evidence remains shallowly mutable (P1)

`MappingProxyType(dict(item))` freezes only the outer mapping. Existing evidence
contains nested lists and dicts (for example conflicts, chain statuses, and effective
state), and callers can still mutate those values in place. Implement recursive
freeze/thaw semantics: mappings, lists/tuples, and sets must become immutable at every
depth; `to_dict()` must return a fresh JSON-serializable mutable copy. Add nested
dict/list mutation-refusal tests and copy-isolation tests.

### R3-4 — The AST rewind is still a literal historical-body replacement (P1)

`_S4D_REWIND_SOURCE` embeds the complete historical source of both changed functions,
and `_rewind_s4d_delta` replaces their entire body/decorators/return annotation. This
can recover the expected hashes regardless of whether the current S4-D implementation
contains the reviewed delta, so it is not evidence that removing only that delta from
the current AST yields P9.

Replace this with a shape-guarded transformation of the current AST. It must first
recognize the exact reviewed S4-D structure and fail if unrelated statements are
present, then remove/rewrite only the S4-D nodes needed to recover the historical
projection. Do not embed or assign a complete historical function body. Add a
negative test showing that an unrelated injected statement makes the rewind fail
rather than being silently overwritten.

## Test-environment hygiene

`tests/__init__.py` was added only to work around an unrelated editable package that
polluted the worker's global Python environment. Remove it from this correction. Run
the suite in the repository venv or another isolated environment instead of changing
package structure to compensate for external `sys.path` contamination.

## Correction boundary

Continue on the same approved branch. Touch only `completion_cli.py`,
`projection_doctor.py`, their focused tests, and removal of the accidental
`tests/__init__.py`. Keep `src/coordinate/cli.py` exact to `a21d946`. Do not edit
MultiNexus plan bytes, push, deploy, access production, or perform lifecycle closeout.
A fourth Codex result review is required.
