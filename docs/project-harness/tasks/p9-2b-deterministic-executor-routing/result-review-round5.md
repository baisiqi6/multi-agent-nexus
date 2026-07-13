# P9-2B Result Review — Round 5

Status: `changes_requested`

## Reviewed authority

- Approved plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate Round 4 HEAD: `5d9b458bd70afb649e25f4a20d9db69e484f9d46`
- MultiNexus Round 4 report HEAD: `eea988f550f088a703b39e565c20691991c79b7f`
- Worker model: ordinary `kimi-code/kimi-for-coding` (no highspeed)
- Review time: `2026-07-13 23:14:08 +0800`

## What passes

- Independent focused Coordinate gate: `181 passed in 0.96s`.
- Independent Coordinate full suite: `2148 passed` plus exactly the accepted nine
  historical CLI-contract/AST failures; there is no P9-2B regression.
- Independent MultiNexus full suite: `503 passed, 2 skipped, 1 warning`.
- Both repositories pass `compileall`.
- Coordinate committed-range `git diff --check` is empty.
- Inline AST inspection reports no duplicate P9-2B test methods.
- Independent forged selected-capabilities replay probe rejects before mutation, with
  event count/payload and job payload/status/attempt count all unchanged.
- Independent cardinality probes accept 32 capabilities and reject 33 and 5000.

## R5-1 — strict stored capability labels do not enforce the shared length bound

`_normalize_capabilities()` bounds caller labels through `_validate_safe_label(...,
max_len=64)`, but `_validate_canonical_capabilities()` only checks string type,
character grammar, uniqueness, cardinality, and ordering. It does not enforce the
P9-2A authority `MAX_CAPABILITY_LEN = 64`.

Because strict stored request and candidate parsing share this helper, a caller can
replace a capability with an arbitrarily long safe-character string, recompute the
public digest, and pass strict parsing. The independent reviewer probe returned:

```text
PROBE_OVERLONG_STORED_CAPABILITY_ACCEPTED 65
```

This violates the approved plan's bounded-label contract and makes caller and stored
validation disagree.

### Required correction

- Import and reuse `coordinate.executor_identity.MAX_CAPABILITY_LEN`; do not introduce
  another magic number or a second authority.
- Enforce the same per-item length bound in `_validate_canonical_capabilities()` while
  preserving existing type/unsafe/duplicate/cardinality/order error behavior.
- Add exact 64-accepted/65-rejected boundary tests for caller construction, strict
  stored `routing_request` with a recomputed valid digest, and stored candidate
  evidence with a recomputed valid decision digest.
- Add routed replay and claim fail-closed coverage for the forged overlong candidate
  envelope. Prove rejection occurs before any event/job/CAS mutation.
- Run the focused/full/static/range gates and update the implementation report.

## Documentation range cleanup

The MultiNexus committed-range `git diff --check` found Markdown hard-break whitespace
and extra EOF blank lines in earlier Codex-authored review/bootstrap documents. These
are reviewer-owned documentation defects, not worker implementation defects. Round 5
normalizes them before the correction worker starts; the final MultiNexus range gate
must be empty.

## Scope and gate

This correction is limited to the shared per-capability length bound, permanent tests,
and report evidence. No schema, routing policy, CLI shape, MultiNexus source, deploy,
restart, push, production DB access, or lifecycle closeout is authorized. Do not amend
or rewrite existing commits. P9-2B remains unapproved pending Codex Round 6 review.
