# P9-3C0 Snapshot/Restore Compatibility — MultiNexus C2 Bootstrap Review

Review date: 2026-07-15 Asia/Shanghai

## Exact review target

- MultiNexus reviewed revision:
  `7ede15604d294d1cd911d3402552b6a7b7019a37`.
- MultiNexus implementation base:
  `f7bab06bd2606395407675b22f81fa6284d59cf7`.
- Coordinate C1 dependency:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.
- Reviewed artifact:
  `p9-3c0-snapshot-compatibility-multinexus-c2-bootstrap.md`.
- Worktree at review time: clean.

The reviewer also verified that Coordinate C1's production source hash
`ce8ad4dd4546265f3dbc7a4854b9bb9fd3d3e3537942a20f5ac11d443ac862fe`
matches the recorded deployment evidence.

## Independent reviewer routing

- Claude Code session: `117ee9d3-5fc6-4a8c-9f92-82a27224e77d`.
- Outer model from result metadata: `claude-sonnet-4-6`.
- Provider-native JSONL `message.model`: `kimi-for-coding`.
- Stream:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-snapshot-c2-bootstrap-review-claude-kimi/reviewer-stream.jsonl`.

The provider claim is based on the structured stream itself, not a UI label or prompt
assertion.

## Independent evidence

- Focused baseline: `15 passed`.
- Full baseline: `658 passed, 2 skipped`.
- Full collection: `660 tests`.
- `compileall`: pass.
- `git diff --check`: pass.
- The only file changed between implementation base and reviewed revision was the C2
  bootstrap document.

The reviewer read the C2 bootstrap, approved parent plan, C1 result/deployment
evidence, real deploy/helper/verifier code, embedded fake deploy contract, registry and
capacity authority parsers, and Coordinate C1 implementation at the exact dependency
revision.

## Findings

No blocking findings.

The reviewer confirmed:

- C2 requires no production interface change; only `tests/test_deploy_contract.py`
  needs implementation changes.
- Snapshot contract version `2` remains distinct from capacity policy-id contract
  version `1`.
- The fake v2 requirements cover canonical bytes, digest, v1/v2 shape, full
  projection, any-source leases, witness-only semantics, target-only restore,
  pre-delete failure, and rollback.
- The five deploy matrix cases completely map to the approved parent plan.
- The prior-absence fixture must use `enabled = false` in its old authority; the real
  rollback sequence restores executor bindings before capacity restore, so this is
  consistent with C1 union coverage.
- Witness drift must remain internally valid and be detected by witness comparison,
  not by earlier projection corruption.
- v1 downgrade is a stale-artifact injection only; the default fake writer remains v2.
- All execution remains under the test temp fake root and cannot use real SSH or
  production paths.

## Non-blocking worker guidance

- Strengthen the existing capture-failure test to prove the SSH log contains no
  `restore-capacity-snapshot` invocation.
- Explicitly put `enabled = false` on the old mac-claude authority entry in the
  historical prior-absence fixture.
- Give fake restore its own `BEGIN IMMEDIATE` transaction and rollback-on-failure
  semantics.

## Authorization boundary

This review authorizes one isolated C2 coding worker from base
`f7bab06bd2606395407675b22f81fa6284d59cf7`, changing only
`tests/test_deploy_contract.py` and producing one local commit.

It does not authorize push, merge, deploy, SSH, production DB access, live restore,
fixture activation, runtime/helper/config changes, or P9-3C1.

`APPROVED_FOR_P9_3C0_SNAPSHOT_COMPATIBILITY_C2_WORKER_LAUNCH`
