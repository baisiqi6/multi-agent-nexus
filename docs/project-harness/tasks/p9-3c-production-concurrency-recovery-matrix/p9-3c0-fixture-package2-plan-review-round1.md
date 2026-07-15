# P9-3C0 Package 2 — Plan Review Round 1

## Review identity

- Verdict: `REQUEST_CHANGES`.
- Exact revision reviewed:
  `5d44cc7ed2585332a74c365abc7b84d34470e4b0`.
- Planning base:
  `ba6bb122eef17910a463be259142c6c0b82020e4`.
- Reviewed plan SHA-256:
  `89cf8b3583b2936241f359fa0c1bab147165591bfdcbfdb3303babfc63c07900`.
- Reviewer session:
  `d8909728-002a-40bd-a64b-58627540ac27`.
- Claude outer model: `claude-sonnet-4-6`; Opus was not used.
- Provider-native model: `kimi-for-coding`.
- Provider-native JSONL:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-package2-plan-review-claude-kimi/reviewer-stream.jsonl`.
- Final-response JSONL:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-package2-plan-review-claude-kimi/reviewer-final-stream.jsonl`.
- The reviewed worktree was clean and the revision contained only the original
  Package 2 plan relative to its stated planning base.

This verdict does not authorize bootstrap authoring or implementation.

## Blocking findings

### P0 — Fixture executor authority was unimplementable as specified

The plan required every fixture executor authority to parse through
`load_authority` while also forbidding any `discord_user_id`. The current shared
parser requires every managed `[[agents]]` entry to contain a quoted positive
decimal `discord_user_id`; external entries cannot carry executor bindings. A worker
therefore could not satisfy both requirements without changing a forbidden runtime
file.

Required correction:

- give E1 and E2 fixed, unique, non-production synthetic parser placeholders;
- state that they are not real Discord identities and must never enter roster sync;
- prove that the synthetic values and fixture ids do not collide with or appear in
  the canonical authority;
- keep the runtime parser unchanged.

### P1 — Silent hold had no stop window before first-byte timeout

The fixture emits no bytes in `hold` mode. `ClaudeAdapter` applies
`first_byte_timeout=90` until the first output byte, so an unspecified stop after the
75-second boundary can be killed and classified `timed_out` at about 90 seconds.

Required correction:

- define a bounded exact-unit stop window after the 75-second quiet proof and before
  the 90-second adapter timeout;
- enforce and record that window in the Package 3 controller/helper contract and
  runbook;
- preserve cleanup even when timing evidence is late, then fail that evidence row;
- do not treat `RuntimeMaxSec=300` as a valid hold duration.

## Non-blocking guidance incorporated into the revision

- Synthetic parser placeholders must be exact, unique, and checked against current
  canonical ids rather than described as an official Discord-reserved range.
- Explain `RuntimeMaxSec=300` as `timeout=240` plus a bounded 60-second shutdown and
  cleanup ceiling.
- A mandatory sandbox-property failure must append bounded failure evidence before
  the helper refuses start.

## Boundaries accepted in Round 1

The reviewer accepted the source/deployment path, render-before-use config gate,
isolated-only production DB/wrapper rejection, mandatory systemd sandbox, Package
2/Package 3/P9-3C1 separation, sourced-function test seam, and separate E1/E2 context
databases.

## Gate state

`APPROVED_FOR_P9_3C0_FIXTURE_PACKAGE2_BOOTSTRAP_AUTHORING` was not issued. A revised
exact plan revision requires a fresh independent Round 2 review.
