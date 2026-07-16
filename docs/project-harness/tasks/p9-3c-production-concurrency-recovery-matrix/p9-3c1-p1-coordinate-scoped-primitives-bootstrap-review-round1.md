# P9-3C1 P1 Coordinate Scoped Primitives — Bootstrap Review Round 1

日期：2026-07-16 Asia/Shanghai

## Verdict

```text
APPROVE
```

本 verdict 绑定 worker bootstrap SHA-256：

```text
002d99eacbd11b3090f0265d3432578c58ffb9df216e3a06512631396381c539
```

只授权 operator 创建 bootstrap 指定的 isolated Coordinate worktree/branch，并派发一次本地
non-Codex coding worker。仍不授权 push、merge、deploy、SSH、production DB mutation、lease
reap、agent deactivate、service restart、fixture/controller、P2/P3 或 live matrix。

## Reviewer routing evidence

Primary route 按 worker bootstrap 与 operator routing rule 使用 Claude Code `--model sonnet`；
没有使用 Opus。该 route 在任何 tool/repo write 前返回 Kimi billing-cycle `403`：

- session：`d31ca49b-0156-4447-ad67-78f8069504e4`；
- stream：
  `sessions/p9-3c1-p1-coordinate-scoped-primitives-bootstrap-review-round1-claude-kimi/reviewer-stream.jsonl`；
- stream SHA-256：
  `6e81dd0a80ec7fc0327a9f52ac16e39a3ad8de069685022b6c8e94cd1ab7dcb0`。

随后 fresh fallback 使用 DeepSeek V4 Pro；native JSONL 证明实际 route 为
`provider=deepseek`、`model=deepseek-v4-pro`：

- session：`019f681b-482a-7000-bc3f-fa3d1bce67bf`；
- stream：
  `sessions/p9-3c1-p1-coordinate-scoped-primitives-bootstrap-review-round1-deepseek-v4-pro/reviewer-stream.jsonl`；
- stream SHA-256：
  `056445d5f3676d2fd164c0e19263e57e863aa04060aeb178b780db85718a416c`。

没有 silent model switch；两个 attempt 的 JSONL 都保留。

## Exact inputs verified by reviewer

| Input | SHA-256 / revision | Result |
| --- | --- | --- |
| measurement | `4b7e59ce4b249c65059f08ec43ef1577b028876d1ab3e2fd4c22740c2da397b7` | match |
| detailed plan | `30a9764fe15391c47320d7c1636cebcee695665bfca8ac6876f03eb64d188a9c` | match |
| plan review | `c7e67f63a1d4af6c2b68165d6449b9936b4f431df8144075985c8601d60ac96a` | match |
| worker bootstrap | `002d99eacbd11b3090f0265d3432578c58ffb9df216e3a06512631396381c539` | match |
| Coordinate HEAD/origin | `9804bbd74c4b826d0620c5939b00e01be9c1120d` | match |
| MultiNexus HEAD/origin | `1b1d1fd1c5c160e3ede16ee2f07fb2989990e3c2` | match |

Coordinate main checkout only had user-owned untracked `.qoder/`；reviewer did not read or modify it。
MultiNexus tracked files remained clean；P1 docs/sessions were expected untracked harness artifacts。
`git diff --check` passed。

## Independent verification

Reviewer independently inspected current `runtime.py`、`runtime_lease.py`、`execution_cli.py`、event
schema/append path and exact executor binding path。It reproduced：

```text
focused: 214 passed, 37 subtests passed, 8 known failures
full: 2461 passed, 517 subtests passed, 9 known failures
fixture SHA-256: 13cb4f3b748fdf7dc1d91dfbb27d9a214d23dfff1112d253d0e01aa0c701ad3d
```

No new failure name appeared。The exact eight-file allowlist、one-commit boundary、exact reap isolation、
typed claim transaction fence、deactivation blocker/event generation chain、two-connection barriers、
CLI P1-only rewind、worker JSONL route proof and post-worker/deploy gates all received `PASS`。

## Codex acceptance note

Independent reviewer noted that the legacy untyped claim path remains outside `BEGIN IMMEDIATE`。Codex
rechecked current source plus approved measurement/plan：P1 intentionally closes the measured **typed**
claim/deactivate race and explicitly preserves untyped claim semantics；P3 owns intake freeze/routing
closure。This is therefore not silently treated as a general claim-safety proof。P1 acceptance remains
limited to the approved typed-managed-agent boundary，and P2/P3 remain blocked by their own gates。

Worker bootstrap exact SHA may now be used once。Any bootstrap edit invalidates this review。
