# P9-3C0 Package 3 Plan Review — Round 2

## Verdict

`APPROVE`

Approval token:

`APPROVED_FOR_P9_3C0_FIXTURE_PACKAGE3_BOOTSTRAP_DRAFT`

Reviewed revision:
`af4da59dddf7570d3353e9e546c11aacf4660025`.

Reviewer session:
`1dcbf16d-26cb-4cdf-9730-15cc09e22681`.

Provider evidence from native JSONL:

- Claude Code outer model: `claude-sonnet-4-6`;
- provider-native model: `kimi-for-coding`;
- tool surface restricted to `Read`/`Bash` plus configured read-only MCP tools;
- repository remained clean and matched `origin/main` throughout.

Stream:
`/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-package3-plan-review-round2-claude-kimi/reviewer-stream.jsonl`.

## Exact evidence

- Previous plan revision:
  `2e91e6cef4f3ec58d98bb77dc7d2e7188b1612c6`.
- Reviewed plan SHA-256:
  `358c28ec0fc06d4717d1762ffe79c5bd54b2ccb20d18dd58152f02a022e08ee5`.
- Measurement SHA-256:
  `d45d9d707da8670e00c3dfb2fd66a3aea37e91686f78c072d793796bb0c6dcce`.
- Round 1 review SHA-256:
  `ba8f15496490fefdc66a32c0f5791167bb90638d6c24705c4850ab6f5f123c09`.
- Coordinate dependency:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685` (only pre-existing untracked
  `.qoder/`, preserved).

The reviewer found no P0/P1/P2 plan defect. It independently accepted the root/non-root
ownership split, wrapper manifest/self-check, systemd 255 semantic normalization,
ClaudeAdapter first-byte boundary seam, default-INFO launch regression, initial-plus-
two-renewal proof, literal quiescence sets, exact reaps, stale-attempt immutability,
interrupted cleanup, process hierarchy, exact-name environment denylist, empty-source
metadata residue, and the explicit rejection of persisted `online_state` as liveness.

## Non-blocking execution gates retained

- Implementation must actually remove `systemd-run --dry-run` and literal property
  comparison.
- It must add the default-compatible log-level parser and exact first-byte clock record.
- Hold cleanup must complete before adapter anchor + 88 seconds.
- Stale N must be tested against a genuinely running N+1 attempt with DB/event
  immutability proof.
- Credential-variable names may be logged as denylist evidence; values may never be
  logged.

## Gate status

This approval authorizes drafting the Package 3 worker bootstrap only. It does not
authorize implementation, deployment, systemd, isolated catalog/job/lease mutation,
or fixture execution. The exact bootstrap must receive a fresh independent review.
