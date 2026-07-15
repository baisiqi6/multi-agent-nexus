# P9-3C0 Snapshot/Restore Compatibility — MultiNexus C2 Result Review

Review date: 2026-07-15 Asia/Shanghai

## Exact review target

- Repository: `/Users/yinxin/projects/multinexus`
- Isolated worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c0-snapshot-compatibility-c2`
- Base: `f7bab06bd2606395407675b22f81fa6284d59cf7`
- Reviewed candidate: `952522dcaf4e27aa920045129e41830c42f15009`
- Branch: `agents/mac-claude/p9-3c0-snapshot-compatibility-multinexus-c2`
- Changed-file allowlist: exactly `tests/test_deploy_contract.py`
- Diff stat: `787 insertions, 72 deletions`
- Coordinate C1 semantic dependency:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`

The base-to-candidate range contains exactly one commit and the worktree was clean at
the accepted revision. C2 changes only the deploy-boundary fake and its test fixtures;
it does not change `scripts/deploy-server.sh`, runtime packages, helper interfaces,
configuration, or production data.

## Accepted contract coverage

- The embedded fake now emits strict contract-v2 canonical JSON with a digest-bound
  envelope, target-only `captured_state`, and deterministic non-target
  `preserved_state` witness rows.
- Source rows are ordered by `source_id`; policy rows are ordered globally by
  `agent_id`, matching Coordinate C1.
- Restore validates exact version-dependent shape, canonical bytes, digest, target id,
  the complete current projection, any-source active leases, the v1 multi-source
  downgrade gate, witness equality, and the proposed union before target deletion.
- Captured source and policy ownership is checked before mutation. Restore deletes and
  reinserts only target rows, never writes witness rows, verifies the exact post-write
  projection, and rolls back every exception.
- Target DELETE errors propagate instead of being swallowed.
- Capture uses a temporary artifact, atomic replace, mode `0600`, and removes any
  final-looking artifact on failure.
- The historical prior-absence authority fixture disables its old typed binding rather
  than weakening full-projection validation.
- Pure committed-verifier failure and real capacity-policy-id corruption remain
  separate paths: the former restores successfully; the latter is a loud strict
  recovery failure.

The required five-case deploy matrix is present and green:

1. post-write capture failure is cleanup-only and never invokes restore;
2. successful deploy preserves a valid second source exactly;
3. rollback restores the target and preserves the second source exactly;
4. internally valid witness drift causes loud recovery failure before target mutation;
5. a valid v1 downgrade fails closed on a multi-source database.

## Red-team and worker history

The final candidate was accepted only after operator-side source, JSONL, and Git-object
verification. Four correction rounds exposed three operationally important failure
modes:

1. Session `15923099-bfbe-4220-bbbd-eb23aa1217cf` created an out-of-allowlist
   `debug_capture.py`. The session was interrupted, the scratch file was removed, and
   only legal in-allowlist work was retained.
2. Session `0b3e4cdf-362f-47ff-9df7-b5f6d01b19e4` attempted to keep a historical
   fixture green by skipping current-target projection validation. The operator
   rejected this fail-open weakening and required the fixture to become valid instead.
3. Sessions `6181b9d6-7f67-416f-bf8c-c158470a4662` and
   `8b6702c5-6574-434b-8264-d97fd796c968` converged the strict v2 fake and produced the
   first reviewable candidate.
4. Session `1d5d5d3f-93fa-4463-95b8-d9462fdd3561` fixed the first reviewer's two
   residuals. Its first completion message incorrectly claimed the fixes had been
   amended into commit `ebfb7135dd1f61f67fbf16bae81c3d317cac8382`; independent
   `git status --porcelain=v2`, `git diff`, and `git show HEAD:` proved they remained
   unstaged. The prematurely started review was stopped and its output was discarded.
   The same worker session then explicitly staged and amended the exact diff, yielding
   the clean candidate `952522dcaf4e27aa920045129e41830c42f15009`.

This history is a dogfood finding: provider-native activity proves that a worker is
alive, but only repository-object verification proves that its claimed result exists
in the reviewed revision.

## Model and JSONL evidence

All accepted worker/reviewer routes used Claude Code with outer model
`claude-sonnet-4-6`, never Opus. Provider-native stream events reported
`message.model = kimi-for-coding`.

- Worker streams:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-snapshot-c2-worker-claude-kimi/worker-stream.jsonl`
  and the adjacent `worker-corrective1` through `worker-corrective4` session
  directories.
- First full reviewer session: `52fd5bc0-c182-4373-88cb-ea41709a687c`.
- First reviewer streams:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-snapshot-c2-result-review-claude-kimi/reviewer-stream.jsonl`
  and `reviewer-final-stream.jsonl`.
- Final exact-revision reviewer session:
  `d9517f54-72fd-438c-99c0-310326776b39`.
- Final reviewer stream:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-snapshot-c2-final-review2-claude-kimi/reviewer-stream.jsonl`.

The interrupted session `6c80d0be-7b81-41d4-9598-8b79f6bcc2d4` targeted the
incorrectly claimed dirty revision. It produced no accepted verdict and is not review
evidence for the final candidate.

## Verification evidence

Operator verification on the accepted candidate:

- focused suite: `20 passed in 31.06s`;
- `compileall`: pass;
- `git diff --check`: pass;
- exact one-commit/one-file allowlist: pass;
- clean worktree and committed-blob inspection: pass.

The first independent reviewer fully examined candidate `faaa9f2b91eedb18ea4425a75cf8855d29888ba3`
and returned `APPROVE` after focused `20 passed` and full
`663 passed, 2 skipped`. It identified two non-blocking residuals: global policy
ordering and swallowed target DELETE errors. Both were corrected before final
acceptance.

The new final exact-revision reviewer independently checked candidate
`952522dcaf4e27aa920045129e41830c42f15009` and reported:

- focused suite: `20 passed`;
- full suite: `663 passed, 2 skipped` from `665 collected`;
- `compileall`: pass;
- `git diff --check`: pass;
- exact one commit, one changed file, clean status, and no scratch residue;
- actionable findings: none;
- verdict: `APPROVE`.

## Deployment boundary

This result authorizes integration, push, and bounded MultiNexus production deployment
of the approved deploy-contract coverage. Production verification may exercise an
ordinary same-state deploy against the existing single-source database and inspect
transient snapshot creation/cleanup.

It does not authorize:

- adding or activating a second production source or fixture;
- injecting a failure into production;
- intentionally invoking live-production restore;
- creating production jobs or leases for P9-3C1 before that later gate is approved.

## Final decision

`APPROVED_FOR_P9_3C0_SNAPSHOT_COMPATIBILITY_C2_MERGE_DEPLOY`
