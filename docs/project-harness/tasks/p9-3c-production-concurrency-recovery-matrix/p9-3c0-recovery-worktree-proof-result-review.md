# P9-3C0 recovery worktree proof 结果审核

结论：`APPROVE`

## 审核身份与证据

- Claude Code：`--model sonnet`
- JSONL assistant model：`kimi-for-coding`
- session：`p9-3c0-recovery-worktree-proof-result-review-claude-kimi`
- permission denials：0
- 独立测试：targeted `2 passed, 114 deselected`；focused
  process-tree/recovery `27 passed, 89 deselected`；完整 scripts test
  `116 passed`；`bash -n`、`compileall`、diff-check 均 PASS。

## 判定

1. `primary_worktree` 在 `_p9c0_prepare_recovery_namespace` 与
   `P9C0_RUN_ID=-r2` 之前保存，顺序正确。
2. base/hold 两参调用仍使用 current-run default；recovery unit/proof 仍处于
   recovery namespace，但第三参是 primary E1 worktree。
3. Python proof 的 environment exact equality 未改动，继续拒绝额外变量和错误
   PWD。
4. behavioral tests 捕获真实 shell argv/run id，不是仅做 source-string assertion。
5. shared DB、job/lease authority、TTL/reap、systemd、snapshot、cleanup 与 P9-3C1
   边界均未改变。

## Residual risk

代码顺序是该修复的一部分，未来若把 primary worktree 推导移到 namespace 切换后会
回归；当前 behavioral test 可捕获。fresh run `p9-3c0-pkg3-20260715l` 仍是最终门。
