# P9-3C0 effective-nonzero result review

Reviewed commit：`8efcd35`

Verdict：`APPROVE`

独立 reviewer 通过 Claude Code `--model sonnet` 执行；JSONL 中
provider-native model 为 `kimi-for-coding`，未使用 Opus。审查工具限制为只读
`Read,Bash`，并独立复测 helper 与 P9-3C0 focused suites。

Reviewer 未发现 blocking finding，并确认：

- nonzero kill 后的 proof 严格发生在 graceful `systemctl stop` 之前；
- authority 仅来自 start ledger 的 exact-unit recorded cgroup，并沿用既有 path
  validation；
- exact unit terminal state 与 recorded-cgroup absent/readable-empty 必须在同 poll
  同时成立；
- `effective-nonzero` 不设置 `kill_failed`，最终 cleanup proof 通过后返回 0；
- still-active、terminal+nonempty、terminal+unreadable 均 cleanup-then-fail；
- pre-stop 最多 20 × 0.05 秒，final wait 最多 60 × 0.5 秒且接受
  `inactive|failed`；
- graceful default、P9-3C1 authorization boundary 与其他 controller caller 均未
  改变。

Operator 验证：

- targeted：`6 passed, 73 deselected`；
- helper：`79 passed, 26 subtests passed`；
- Package 3 focused：`237 passed, 26 subtests passed`；
- adjacent authority/runtime：`207 passed, 39 subtests passed`；
- full：`862 passed, 2 skipped, 81 subtests passed`；
- `bash -n`、`compileall`、`git diff --check` PASS；ShellCheck 仅有提交前已存在
  warnings。

Reviewer 独立复测：helper `79 passed, 26 subtests passed`，P9-3C0 focused
`191 passed, 26 subtests passed`。

Residual risk 只剩真实 systemd 255 race 需要用全新 isolated sidecar run 验证；这
正是下一 gate，不能由 mock 测试替代。P9-3C1 仍未授权。
