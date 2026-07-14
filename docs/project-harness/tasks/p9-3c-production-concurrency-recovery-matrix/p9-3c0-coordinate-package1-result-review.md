# P9-3C0 Package 1 Coordinate Result Review

Review date: 2026-07-15

## Exact review target

- Repository: `/Users/yinxin/projects/coordinate`
- Base: `3eaa7bfdeb0f660da46bd7fe6003231822c9658c`
- Reviewed commit: `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`
- Worker branch: `agents/mac-claude/p9-3c0-capacity-source-decoupling-coordinate`
- Worker model evidence: Claude Code `sonnet` outer mode with provider-native
  `message.model=kimi-for-coding`
- Changed files:
  - `src/coordinate/executor_capacity.py`
  - `tests/test_executor_capacity.py`
  - `tests/test_execution_leases.py`

The worker worktree was clean at the reviewed revision. The changed-file set matches the
approved implementation bootstrap and scope addendum.

## Accepted behavior

- Disjoint capacity sources may own partial executor-policy sets.
- The post-sync union across every source must cover all enabled typed bindings.
- Unknown or untyped agents and cross-source takeovers fail before writes.
- Removing or replacing an exact capacity policy referenced by an active lease fails
  before writes.
- Version/hash error precedence remains stable; an exact retry still revalidates the
  global known-binding, ownership, and union-coverage invariants before returning
  `changed=false`.
- Result lists and multi-conflict errors are deterministic.
- No schema, snapshot/restore, deployment, registry, runner, or fixture change is part
  of this package.

## Independent evidence

- Focused suites: `186 passed, 5 subtests passed`.
- Full suite: `2415 passed, 493 subtests passed, 9 failed`.
- The nine full-suite failures exactly match base `3eaa7bf`: eight historical
  `tests/test_cli_contract.py` fixture/hash failures and one historical
  `tests/test_issue_cli.py` AST failure.
- `git diff --check HEAD^ HEAD`: pass.
- `python -m compileall`: pass.
- Independent Kimi result reviewer: no blocking findings.
- Reviewer verdict:
  `APPROVED_FOR_P9_3C0_PACKAGE1_MERGE_AND_INERT_DEPLOY`.

Provider-native reviewer evidence:
`/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-coordinate-result-review-kimi/stream.jsonl`.

## Deployment boundary and residual conditions

This approval authorizes merge and an inert Coordinate production deployment while the
production database still contains only the canonical
`multinexus.discord.capacity` source. It does not authorize adding a fixture capacity
source, fixture agents, fixture units, fixture jobs, or production concurrency/crash
execution.

Before any second capacity source is activated, a separate compatibility gate must
close. The current `capture_capacity_snapshot` and `restore_capacity_snapshot` contract
intentionally rejects any additional source or other-source policy. That fail-closed
behavior makes this inert deployment safe, but it cannot be treated as a multi-source
backup/restore proof.

`resolve_capacity_policy` can expose a policy belonging to a disabled typed binding.
Current claim paths subsequently validate the executor binding and fail closed, so this
is not a blocker for the reviewed package. Future scheduling call sites must preserve
that validation boundary.

## Final decision

Package 1 is accepted for fast-forward merge, push, single-source backup, inert
production deployment, and post-deploy read-only verification. A second capacity source
remains blocked on the independent snapshot/restore compatibility gate.
