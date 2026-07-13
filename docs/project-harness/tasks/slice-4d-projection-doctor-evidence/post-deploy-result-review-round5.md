# Slice 4D Post-Deploy Correction Result Review — Round 5

## Decision

**APPROVED** for the complete post-deploy correction through
`15020c2204e8e05c6304f6ed83a5fed83ad12eae`, based on production baseline
`0563cc01f9b12d5c196f59aaece8d81d1d5e5bc5`.

All must-fix findings from post-deploy result review Rounds 1–4 are closed. The
Coordinate branch is authorized for fast-forward integration, push, DB backup,
deployment, and production read-only doctor. This approval does not itself close
S4-D: production doctor must return zero errors before receipt-based closeout.

## Closed findings

- **PD-R1-1:** split task-create and issue-materialize exact retries independently
  derive historical supersedes provenance at the bound ready-event rowid.
- **PD-R2-1:** arbitrary unknown checklist top-level fields fail closed through an
  explicit recognized-field set.
- **PD-R2-2:** both `plan_path` and `artifacts.plan` must match the recorded canonical
  `plan_doc`.
- **PD-R3-1:** supported lifecycle `lease` is explicitly evidenced and allowed.
- **PD-R4-1:** default non-split ready requires a regular readable plan before any DB
  write, computes one full SHA, derives the short hash from it, and cannot emit null
  SHA or a `nohash` key.

## Independent Codex verification

- Branch ancestry: `0563cc0` is an ancestor of `15020c2`.
- Changed files are limited to:
  - `src/coordinate/onboarding.py`;
  - `src/coordinate/projection_doctor.py`;
  - `src/coordinate/split_operations.py`;
  - `tests/test_onboarding.py`;
  - `tests/test_projection_doctor.py`;
  - `tests/test_split_operations.py`.
- Current canonical checklist keys minus recognized keys: empty set.
- Independent lifecycle lease reproduction: clean.
- Independent arbitrary unknown field reproduction: `operation_envelope_drift`.
- Independent `artifacts.plan` tamper reproduction: `operation_envelope_drift`.
- Independent missing-plan reproduction: stable `ValueError`, zero task mirrors, zero
  events.
- Focused onboarding/projection/split verification:
  `241 passed, 43 subtests passed`.
- Full suite: `1864 passed, 449 subtests passed, 9 failed`; all nine are the known
  historical eight CLI-contract fixture hashes plus one issue-CLI AST hash.
- Changed-path ruff and compileall passed.
- `git diff --check` passed.
- `src/coordinate/cli.py` is byte-identical to `0563cc0`.
- No repository `events.jsonl` diff exists.
- Kimi JSONL session:
  `019f5924-d9fd-7000-9537-0cf3a099e558` records the Round 2–4 correction work and
  verification. Provider/model remained
  `kimi-code/kimi-for-coding-highspeed`; no fallback was needed.

## Deployment gate

1. Fast-forward Coordinate main from `0563cc0` to `15020c2` and push.
2. Back up `/var/lib/coordinate/coord.sqlite3` and verify source/backup integrity.
3. Deploy and install Coordinate from the approved revision; verify deployed source
   SHA, runtime import path/version, schema version, DB user version, service state,
   and server smoke.
4. Run `coord-local workspace doctor discord-nexus` without
   `--no-projections` and retain JSON evidence.
5. Require zero error findings. Expected non-errors include an
   `operation_plan_superseded` info for the approved S4-D plan revision and legitimate
   receipt warnings/info. Any error returns to review; do not whitelist, repair JSON,
   or edit the production DB directly.

## Residual note

`onboarding._plan_content_hash` is now unused after the single-read SHA correction.
It is harmless and outside the correctness gate; remove it in a later surgical cleanup
rather than changing the approved branch after review.
