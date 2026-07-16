# P9-3C1 P1 Coordinate Scoped Primitives — Independent Plan Review Round 1

状态：`APPROVED_BOOTSTRAP_DRAFT_ONLY`

日期：2026-07-16 Asia/Shanghai

## Exact reviewed inputs

- Measurement SHA-256：
  `4b7e59ce4b249c65059f08ec43ef1577b028876d1ab3e2fd4c22740c2da397b7`。
- Plan SHA-256：
  `30a9764fe15391c47320d7c1636cebcee695665bfca8ac6876f03eb64d188a9c`。
- Coordinate base/source/origin/deployed：
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- MultiNexus source/origin/deployed docs projection：
  `1b1d1fd1c5c160e3ede16ee2f07fb2989990e3c2`。

Primary Claude Code `--model sonnet` attempt returned Kimi billing-cycle `403` before any tool call or
repo write。Failure stream/session were preserved：

- session `6bb67fc1-4d89-4c81-9417-b78319150b24`；
- `sessions/p9-3c1-p1-coordinate-scoped-primitives-plan-review-round1-claude-kimi/reviewer-stream.jsonl`。

Fresh quota fallback used OMP native
`provider=deepseek`、`model=deepseek-v4-pro`，session
`019f6811-0b13-7000-a712-10052746bf99`。Full stream：

`sessions/p9-3c1-p1-coordinate-scoped-primitives-plan-review-round1-deepseek-v4-pro/reviewer-stream.jsonl`

## Verdict and evidence

```text
VERDICT: APPROVE
P0: None
P1: None
```

Reviewer independently：

- matched both file SHA-256 values；
- verified Coordinate/MultiNexus HEAD and origin identities；
- inspected current global reap、implicit claim reap、pretransaction online check、missing deactivate、
  missing claim policy evidence and CLI parser/handler paths；
- reran focused baseline：`214 passed, 37 subtests, 8 known failures`；
- reran full baseline：`2461 passed, 517 subtests, 9 known failures`；
- matched base CLI fixture SHA-256
  `13cb4f3b748fdf7dc1d91dfbb27d9a214d23dfff1112d253d0e01aa0c701ad3d`；
- accepted exact reap、claim policy、transactional deactivate fence、CLI delta proof、test and inert
  deploy contracts。

Non-blocking bootstrap considerations：

1. shared `_reap_one_lease` refactor must preserve global behavior；
2. direct `claim_leased_job()` must defensively enforce typed/none authority；
3. offline retry must query exact prior `agent.deactivated` audit evidence；
4. handler must map absent exact ids + `batch_size=None` back to legacy global `100`。

Codex further tightens item 3 in the bootstrap：do not rely only on second-resolution
`last_seen_at`；derive deactivation generation from a transaction-local deterministic prior-event
chain/ordinal so heartbeat/deactivate cycles in the same second cannot reuse an idempotency key。

## Authorization boundary

This approval authorizes only drafting the exact P1 worker bootstrap。It does not authorize worktree
creation、coding worker、file changes、commit、push、deploy、production mutation、new CLI invocation、
service restart、P2/P3 or live matrix。The bootstrap exact SHA requires a fresh independent review。

P9_3C1_P1_PLAN_ROUND1_APPROVED_BOOTSTRAP_DRAFT_ONLY
