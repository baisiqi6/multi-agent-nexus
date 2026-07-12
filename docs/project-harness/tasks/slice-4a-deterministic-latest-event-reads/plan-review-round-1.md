# Slice 4A Plan Review — Round 1

## Verdict

`CHANGES_REQUESTED`

- Reviewed plan SHA-256:
  `4d2bbc60464b5333d6d6c627a8cbe4809d71fdde26c3bd246db4f81bdf9720ab`.
- Coordinate start:
  `084419c5b36b32a81a39634c7ebbbf8b8b71d04c`.
- Provider/model: `kimi-code/kimi-for-coding-highspeed` through Oh-My-Pi.
- Provider session: `019f5776-8b26-7000-9dc1-42e888c72f5f`.
- Provider JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-s4a-plan-review/2026-07-12T17-53-34-503Z_019f5776-8b26-7000-9dc1-42e888c72f5f.jsonl`.

## Independently accepted evidence

- Production has exactly two timestamp-only event-ledger newest reads:
  `_do_task_show` and `_task_owner_for_event`.
- The daemon `tasks ORDER BY updated_at DESC` query is display-only and not an
  event-ledger decision authority, so excluding it is correct.
- `created_at DESC, rowid DESC` matches established ledger insertion authority.
- Same-second behavioral proofs, mirror-first precedence, malformed payload behavior,
  four-path scope and the Slice 4A/B/C/D boundary are sound.
- Python 3.14 reproduced 189 focused and 1,572 full passing tests.

## Must-fix

The plan's focused command imported `tests.test_daemon` and `tests.test_policy` as a
package. `tests/` has no `__init__.py`, and an installed third-party `tests` namespace
can intercept those imports under the worker's Python 3.12 environment. Replace it
with explicit `unittest discover -s tests -p ...` commands and name the known-good
Python 3.14 binary so the worker can follow validation verbatim.

After revision, bind a new exact SHA and obtain a fresh Round 2 verdict.
