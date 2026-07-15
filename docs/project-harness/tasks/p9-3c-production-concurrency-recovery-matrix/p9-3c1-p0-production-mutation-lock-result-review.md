# P9-3C1 P0 Production Mutation Lock — Result Review

状态：`APPROVED_AND_DEPLOY_GATE_OPEN`

日期：2026-07-16 Asia/Shanghai

## Exact revision and scope

- Base：`d09e0f8fba0f6d189934173027ca5a756e5f36ce`。
- Candidate：`ec748dc040b9ebf8f456c6bc0ab6db28e0dd26c6`。
- Branch：`agents/fallback/p9-3c1-production-mutation-lock`。
- Candidate 相对 base exactly one commit、clean worktree、`git diff --check` PASS。
- Diff 只包含 bootstrap allowlist 的四个文件：
  `scripts/deploy-server.sh`、`scripts/production-mutation-lock.py`、
  `tests/test_deploy_contract.py`、`tests/test_production_mutation_lock.py`。
- Authoritative bootstrap SHA-256：
  `27cb3518af97108ebaa03cf06346e8ebad8ca73b5272d756a6ccfd6336cd3418`。

## Worker and correction evidence

- Claude Code `--model sonnet` 的 Kimi route 在 repo write 前返回 billing-cycle `403`；原始
  JSONL 已保存在
  `sessions/p9-3c1-p0-production-mutation-lock-correction-claude-kimi-round4/worker-stream.jsonl`，
  session `c19a1ee0-121f-4184-a61d-d096313ac6b6`。
- MiniMax fallback 的 native stream 证明
  `provider=minimax-code-cn`、`model=MiniMax-M3`，但它在 CLI correction 中产生重复 argparse/
  missing `parse_args` 损坏。Codex 立即中止 worker，不接收报告，复核 dirty state 后接管窄修订。
- Codex 拒绝旧候选 `400146d` 的第一次独立 APPROVE，因为 reviewer 漏掉 bootstrap 7.2：
  validation 成功后的 normal release 必须调用 installed helper，streamed helper 只能用于
  validation 前 fallback。最终 candidate 实现显式 `unvalidated/validated` state、exactly-once
  release attempt、loud streamed fallback marker 和 restrictive `umask 077`，并补齐动态 contract
  tests。

## Verification

Codex 在最终 tree 上得到：

```text
bash -n: PASS
py_compile: PASS
compileall -q: PASS
git diff --check: PASS
focused: 95 passed in 73.54s
full: 953 passed, 2 skipped, 1 warning, 81 subtests passed in 146.91s
```

Fresh independent result reviewer 使用 OMP
`provider=deepseek`、`model=deepseek-v4-pro`，session
`019f67f6-8263-7000-8a3f-d53655433dac`。完整 JSONL 位于：

`sessions/p9-3c1-p0-production-mutation-lock-result-review-round3-deepseek-v4-pro/reviewer-stream.jsonl`

Reviewer 独立重跑并得到：

```text
focused: 95 passed in 75.15s
full: 953 passed, 2 skipped, 1 warning, 81 subtests passed in 150.80s
VERDICT: APPROVE
Findings: None
```

它逐项接受 root/inode authority、raw token、exact release/recover、read-only status、
installed-vs-streamed release route、atomic helper install、top-level trap、contention、SIGTERM、
status-absent 和 two-concurrent-deploy evidence。Codex 的最终 adversarial review 未发现新的
blocker。

## Authorization boundary

本 review 关闭 P0 local/result gate，并允许 merge、push、首次 `--no-restart` inert deploy、
installed helper hash/mode/status smoke 和只读 production integrity/residue verification。它不授权
fixture catalog activation、production job/lease/reap、P9-3C1 controller run、service restart 或
live lock recovery。

P9_3C1_P0_RESULT_APPROVED_FOR_INERT_DEPLOY
