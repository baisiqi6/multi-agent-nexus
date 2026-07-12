# P9-0A2a Result Review — Round 1

## Verdict

**Changes requested.** Do not integrate, push, close out, or mark done.

- Worker OMP session: `019f55ce-6283-7000-be7b-0204c5d16138`
- Worker JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-p9-0a2a-kimi/2026-07-12T10-10-16-835Z_019f55ce-6283-7000-be7b-0204c5d16138.jsonl`
- Reviewed start: `947368a4c278aa847b40eea20a7088c5cb28446f`
- Reviewed worker tip: `e4c98ea44f609ee7468d283a82840b16e41a9fec`
- Scope observed: the five approved paths only.
- Worker validation observed: 36 new/contract, 212 compatibility-focused, and 1,383
  full tests passed; 21/75/99 counts preserved; fixture diff visually contains the 11
  intended handler identities.

## Must-fix finding

### P1 — The structural delta verifier does not compare against the P9-0A1 baseline

`tests/test_cli_contract.py:test_migrated_handler_modules_are_exactly_the_11_workspace_state_reconcile_leaves`
verifies that the 11 named leaves currently point to `coordinate.workspace_cli` and no
other leaf does. It does **not** verify that actions, order, flags, choices, defaults,
help text, leaf paths, node metadata, or non-migrated handler identities remain equal to
the P9-0A1 fixture. Because `test_fixture_matches_generated_contract` compares only
against the newly regenerated fixture, an unrelated parser change plus fixture update
would still pass both tests.

This violates the approved requirement that the complete normalized contract differ
from the P9-0A1 baseline only at the exact 11 path-to-handler mappings.

## Required correction

Within `tests/test_cli_contract.py` only:

1. keep the current fixture-vs-generated assertion;
2. build the current normalized contract;
3. find exactly the 11 approved leaf paths and require each current handler to equal its
   exact `coordinate.workspace_cli.handle_*` value;
4. replace only those 11 values in an isolated copy with the corresponding historical
   `coordinate.cli.handle_*` values;
5. serialize using the canonical JSON byte function/format; and
6. assert the resulting bytes have the exact P9-0A1 baseline SHA-256
   `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.

The test must also fail if any approved path is missing/duplicated or another
`coordinate.workspace_cli` handler appears. Add a focused negative test only if needed
to prove the helper rejects non-handler drift; do not duplicate the full fixture.

Do not modify production code, the fixture, another path, the existing commit, or
lifecycle state. Add one correction commit, rerun 36/212/full tests plus `diff --check`,
and report the new tip.

## Other review observations

- Handler bodies and parser registration appear mechanically moved.
- Root direct aliases, import direction, top-level registration positions, and approved
  path scope appear correct.
- No additional must-fix finding was identified in this round, but final approval waits
  for the corrected verifier and refreshed independent validation.
