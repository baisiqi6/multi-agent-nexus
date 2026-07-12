# P9-0A1 Durable Closeout

## Outcome

P9-0A1 is durably `done/closed`. It introduced the exact current Coordinate CLI contract
and a minimal acyclic `cli_support` seam without moving a domain registrar or changing
runtime, schema, lifecycle, delivery, or public CLI behavior.

## Identities

- Approved plan SHA-256:
  `00a52ea12a85f8e18aa6b9e56224ea5478b0ca7e21d3d2fc7e1ead0f540a3796`
- Plan approval event: `b293eaac-5e12-4aab-bb11-e36c07a377dd`
- Coordinate start SHA: `e0cc1561cd20b0f22389234aefe92d01273860e4`
- Accepted worker commits:
  - `dfdd03681b0c53675e52b75fdcd50c5e6bc419bf`
  - `c47e89994652720a939d857c6bfa942ad0b1e20a`
  - `117ff5d9f98272ff0d740588708b357dc955b205`
- Integrated/pushed Coordinate `main` and `origin/main`:
  `117ff5d9f98272ff0d740588708b357dc955b205`
- Worker OMP session: `019f559d-7e43-7000-87ed-84a38ee960aa`
- Worker JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-p9-0a1-kimi/2026-07-12T09-16-52-675Z_019f559d-7e43-7000-87ed-84a38ee960aa.jsonl`

## Plan and result review

- Independent plan review required four rounds. Round 2 found the real 21/75 baseline,
  checkout-path leakage, and width-dependent help; Round 3 found inherited DB override;
  Round 4 approved the exact plan hash with no must-fix.
- Kimi implemented in an isolated Coordinate worktree.
- Codex result review required three rounds:
  - Round 1 rejected parent-environment contamination, private fixture paths, a false
    callable-handler assertion, and weak default binding.
  - Round 2 rejected caller-`HOME` dependence that failed on another host identity.
  - Round 3 approved accepted tip `117ff5d` after all findings closed.
- Review artifacts: `plan-review-round-2.md` through `plan-review-round-4.md`, and
  `result-review-round-1.md` through `result-review-round-3.md`.

## Accepted implementation

Exactly four Coordinate paths changed:

- `src/coordinate/cli.py`
- `src/coordinate/cli_support.py`
- `tests/test_cli_contract.py`
- `tests/fixtures/cli_contract.json`

The committed contract records 21 ordered top-level commands, 75 ordered leaves, and 99
parser nodes. Fixture SHA-256 is
`83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.
The exact legacy default is bound by privacy-safe digest
`b91ddca4888701871807e3d0f931b54734beac92ccb73de1e37872852c416573`.

## Validation

Codex independently validated both the worker tip and canonical Coordinate `main`:

- normal, DB-poison, fake-HOME, and fake-HOME-plus-DB-poison contract suites: 19 passed
  each;
- an additional alternate-HOME dump matched the fixture bytes;
- focused `tests.test_cli tests.test_pr_cli`: 350 passed;
- full discovery: 1,366 passed;
- `git diff --check`: pass;
- import orders and `cli_support -> cli` absence: pass;
- runtime DB override preserved;
- fixture contains no private `/Users/` or caller-home path;
- canonical Coordinate `HEAD == @{u} == 117ff5d`; unrelated `.qoder/` remained untouched.

No deploy or multi-host smoke was required because this is a behavior-preserving module
and test seam with no daemon/service/schema change.

## Lifecycle

- Final closeout request: `21467920-8399-425e-bec1-839f440e4135`
- Final approved result review: `15c2ee4b-57f7-4764-9ee7-aa8972913f74`
- Completion receipt: `f1f8da57-57c9-4bc4-8f40-76e0c8158f4c`
- `completion.claimed`: `6a888797-0e97-46f1-b07c-eab832510d1f`
- `completion.applied`: `87204105-08ed-4157-9626-05787821762a`
- `task.done`: `98cdcb0a-9103-478b-b7f5-4e6d0693a085`
- `completion.consumed`: `d2f19ed1-79ab-43ae-a2b9-d706e66b2847`
- Before/after fingerprints:
  `3388bd5ea45ac9af67398db1f183fefa33aa32b1dbb9c78b0f6d8cd03bdf55e5` →
  `eba9600714481a87be16f17a903fe7a0b034a1e5824ed2e597f86de86b9b56c8`
- Supported reconcile converged the task mirror to `closed`.

No repair-only path, legacy mark-done, direct harness JSON edit, or direct SQLite edit
was used. The first file-side attempt used a relative harness root and failed before
claim or file mutation; the same authorized receipt then succeeded with the absolute
harness root.

## Dogfood boundary and routed gaps

This package is semi-dogfood. Plan/assignment/review/receipt lifecycle used Coordinate,
and worker activity used provider JSONL, but the real targeted `mac-omp` handoff was
rejected because `discord-nexus` lacks a `macbook-local` execution profile. The Operator
used a local OMP worker with generated bootstrap plus exact supplement instead.

Open operational gaps discovered here:

1. generated cross-repo bootstraps still identify MultiNexus as the implementation repo
   and require an exact supplement for the Coordinate worktree;
2. a failed targeted handoff plus assignment request left a pending live Discord delivery
   with no cancellation command; do not pump it as a stale assignment;
3. after terminal `completion.consumed`, `mark-done-preflight` still reports the original
   authorization status even though the authoritative event chain is terminal;
4. `mark-done-files` error text for relative harness roots does not show that the path was
   resolved against the caller cwd.

These gaps do not weaken P9-0A1 implementation correctness or the terminal receipt event
chain. They remain explicit dogfood/backlog inputs. P9-0A2 is next and requires its own
detailed plan and independent review.
