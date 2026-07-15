# P9-3C0 Package 3 nested run lock 计划审核

状态：`APPROVE`

审核角色：独立 plan reviewer  
执行入口：Claude Code `--model sonnet`  
JSONL 实际 provider model：`kimi-for-coding`  
审核日期：2026-07-15

## 审核结论

1. `depth 0 -> FD 9`、`depth 1 -> FD 8`、`depth >= 2 fail closed` 是针对
   nested `exec 9>>...` 覆盖 outer FD 的最小正确修复，并兼容 macOS Bash 3.2。
2. 每层必须独立执行 open、lock、callback、unlock、close，并在 callback 非零或
   unlock 失败后恢复 previous depth；不需要改变现有 outer trap 的职责。
3. 实现必须补齐真实 behavioral tests：严格锁顺序、FD 9/8 同时存活、inner close
   不影响 outer、third-level fail closed、callback 非零后仍清理并传播结果。
4. recovery namespace、primary lock path/authority、shared DB、job/lease、systemd、
   snapshot、cleanup 与 P9-3C1 均不得扩 scope。
5. 部署只允许 `--no-restart`；fresh run `m` 必须无 `flock` warning，并完整记录
   runs `a-m` 与此前误用 deploy restart。

审核原始记录：
`sessions/p9-3c0-nested-run-lock-plan-review-claude-kimi/reviewer-stream.jsonl`
