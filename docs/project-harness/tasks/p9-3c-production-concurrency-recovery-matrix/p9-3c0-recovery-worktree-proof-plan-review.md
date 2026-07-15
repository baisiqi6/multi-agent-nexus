# P9-3C0 recovery worktree proof 计划审核

结论：`APPROVE`

## 审核身份

- Claude Code：`--model sonnet`
- JSONL assistant model：`kimi-for-coding`
- session：`p9-3c0-recovery-worktree-proof-plan-review-claude-kimi`
- permission denials：0

## 判定

1. proof 增加可选 `expected_worktree`，base/hold 保持两参默认调用，变更最小。
2. recovery 显式使用 primary E1 worktree，与 shared DB 内 job/lease authority 一致。
3. environment 仍做 exact equality，不接受多余变量、错误 PWD 或 recovery worktree。
4. behavioral tests 覆盖 base default 与 recovery explicit 两条路径。
5. `--no-restart`、fresh run `l`、保留 `a-k`、P9-3C1 blocked 的边界完整。

实现约束：必须在 `P9C0_RUN_ID` 切换到 recovery namespace 之前计算并保存 primary
worktree；否则 explicit override 仍会错误地指向 recovery namespace。
