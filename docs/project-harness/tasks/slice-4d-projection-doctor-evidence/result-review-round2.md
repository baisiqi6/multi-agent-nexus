# Slice 4D Result Review — Round 2

## Decision

**CHANGES_REQUESTED** for correction commit
`03c4d2b` on top of `210e5f4`.

Round 1's three executable reproductions are fixed: unsupported contract versions now
produce `operation_contract_unsupported`, mismatched expected/actual receipt
fingerprints produce `receipt_chain_conflict`, and consumed receipts with expired
authorizations return `status=consumed`. `src/coordinate/cli.py` is also restored to
the exact start bytes. The package still has three P1 gaps and is not authorized for
merge, deploy, dogfood, or closeout.

## Closed Round 1 findings

- R1-1 contract-version rejection: closed.
- R1-3 consumed-expiry regression: closed by independent CLI reproduction.
- R1-4 envelope drift vs orphan classification: closed.
- R1-5 event/mirror comparison breadth: materially expanded; retain in regression.
- R1-6 facade identity/start bytes: `cli.py` net diff is empty and
  `_lookup_receipt_for_preflight` is restored.
- R1-7 breadth: materially expanded with 40 focused tests.
- R1-8 output identity fields: task id remains null outside task scope; internal
  discriminator naming remains cosmetic.

## Remaining must-fix findings

### R2-1 — Missing required receipt links are still accepted (P1)

Both `completion_cli.py:680-710` and `projection_doctor.py:1413-1433` compare
fingerprints only when the predecessor value is not `None`. Neither rejects a missing
authorization `harness_fingerprint`, claim `before_fingerprint` /
`expected_after_fingerprint`, apply `before_fingerprint` / `after_fingerprint`, or
terminal `task.done.applied_fingerprint`.

Independent reproduction removed all of those fields from a complete status chain and
produced:

```text
preflight_missing_links={..., 'status': 'consumed', ...}
doctor_missing_links=[('receipt_terminal', 'info')]
```

Fail closed when any field required by that transition is absent, malformed, or
inconsistent. Compare apply `before_fingerprint` back to claim/authorization as well as
apply `after_fingerprint` to claim expected-after, and require task.done
`applied_fingerprint` to equal the applied event. Add both preflight and doctor tests
for every missing field, not only mismatch cases.

### R2-2 — The historical delta proof does not rewind anything (P1)

`test_s4d_delta_proof_against_rewound_hashes` computes current AST hashes, compares
them to historical constants, and asserts the names of the two differences. It never
constructs the historical projection from current source. `_S4D_CURRENT_HASHES` is a
new post-change baseline and can bless arbitrary edits to those two functions.

Add a deterministic, Git-independent AST projection/rewriter that removes only the
reviewed S4-D semantic delta and prove its hashes equal the unchanged P9 constants.
Keep a separate exact current hash if useful, but it is not a rewind proof by itself.

### R2-3 — Frozen dataclasses still expose mutable report state (P1)

`Finding.evidence` is a mutable list of mutable dicts, `ProjectionReport.findings` is a
mutable list, and `ProjectionReport.summary` is a mutable dict. `frozen=True` only
prevents rebinding these attributes; callers can mutate their contents and change a
supposed immutable diagnostic after collection.

Use immutable nested storage (tuples plus a frozen summary/evidence representation, or
an equivalent genuinely immutable structure) and serialize copies in `to_dict()`.
Add mutation-refusal tests.

## Test hygiene correction

Do not monkey-patch `Finding.evidence_dict` at module scope in tests. Use a local helper
function. The correction must keep `cli.py` start bytes, the same nine historical full
suite failures, and every existing/new S4-D test green.

## Correction boundary

Correction remains on the same approved plan/branch and may touch only
`completion_cli.py`, `projection_doctor.py`, focused tests, and the already-added
read-only helper if genuinely necessary. No MultiNexus edit, push, deploy, production,
or lifecycle action. A third Codex result review is required.
