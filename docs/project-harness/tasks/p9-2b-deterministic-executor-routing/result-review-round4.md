# P9-2B Result Review — Round 4

Status: `changes_requested`

## Reviewed authority

- Approved plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate Round 3 HEAD: `091c9e86f23dc627ea7131757de889b425eb8f3e`
- MultiNexus Round 3 report HEAD: `de6cc675945039d38c883579ea6506f3ff8e121b`
- Worker model: ordinary `kimi-code/kimi-for-coding` (no highspeed)

## What now passes

- The permanent exact replay mutation matrix now genuinely exercises both the
  typed-context and legacy/no-context branches for forged event payload
  `origin`, `reply`, and `task_id`.
- The committed absolute-path AST detector was removed.
- Coordinate focused P9-2B gate: `173 passed in 1.00s`.
- Coordinate full suite: `2140 passed` plus exactly the accepted nine historical
  CLI-contract/AST failures.
- MultiNexus full suite: `503 passed, 2 skipped`.
- The prior exact event-content reviewer probes now reject.

## R4-1 — selected candidate capabilities are not cross-bound to the binding

The selected candidate's source, version, catalog hash, ids, assignment, and host
are cross-validated against the stored P9-2A binding/P9-1 context, but its
`capabilities` evidence is not. Because the decision digest is an unkeyed public
SHA, a stored event/job pair can replace the selected candidate capabilities with
another sorted list that still contains the requested capability, recompute the
decision id, and pass both replay and claim.

Independent reviewer probes returned:

```text
FORGED_SELECTED_CAPABILITIES_ACCEPTED
FORGED_SELECTED_CAPABILITIES_REPLAY_ACCEPTED False False
```

This contradicts the plan's requirement that the persisted decision, selected
P9-2A binding, and claim evidence cross-link exactly and fail closed when stored
candidate/selected links are forged.

### Required correction

Compare the selected candidate's canonical capability list exactly with the
stored `executor_binding.capabilities` list in `_validate_routing_cross_links()`.
Add permanent tests that mutate the selected candidate capabilities to another
canonical superset, recompute the decision digest, and prove:

- `routing_claim_evidence()` rejects;
- routed replay rejects even when event and job carry the same forged decision;
- claim rejection occurs before CAS/event mutation.

Do not consult current load or reroute during replay.

## R4-2 — routed capability list cardinality is unbounded

The approved plan requires bounded required capabilities. P9-2A already defines
the catalog authority bound as `MAX_CAPABILITIES = 32`, but
`_normalize_capabilities()` and `_validate_canonical_capabilities()` enforce only
non-empty, label grammar, sorting, and uniqueness. A direct reviewer probe was
accepted:

```text
UNBOUNDED_REQUIRED_CAPABILITIES_ACCEPTED 5000
```

### Required correction

Reuse the P9-2A cardinality authority (`MAX_CAPABILITIES`, currently 32) rather
than creating another divergent magic number. Enforce it in both caller-side
normalization and strict stored-envelope validation. This must also bound each
candidate capability list because candidates use the same strict validator.
Add boundary tests for 32 accepted and 33 rejected for caller input, stored
`routing_request`, and stored candidate evidence. Preserve current sorted/unique
semantics and error ordering where already asserted.

## R4-3 — the reported diff gate did not check committed changes

The report records bare `git diff --check` on a clean worktree. That checks only
uncommitted changes, not the P9-2B commit range. The reviewer ran the correct
range gate:

```text
git diff --check eec9b233f6c797c73aec9d535fa723e037a0af65..HEAD
```

and found:

```text
tests/test_executor_routing.py:1341: new blank line at EOF.
```

Remove the extra EOF blank line. The final report must record the range-based
command and its empty output. Keep both worktrees clean.

## Scope and gate

No schema, routing policy, CLI shape, MultiNexus source, production DB, deploy,
restart, push, or lifecycle transition is authorized in this correction. Do not
rewrite or amend prior commits. P9-2B remains unapproved until a later Codex
review verifies these corrections and all final gates.
