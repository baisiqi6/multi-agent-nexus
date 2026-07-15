# P9-3C0 effective-nonzero plan review

状态：`ROUND_2_APPROVE`

## 审核身份

- 调用入口：Claude Code `--model sonnet`，未使用 Opus；
- JSONL provider-native model：`kimi-for-coding`；
- 审核范围：只读审查 systemd 255 nonzero-but-effective crash 分类计划；
- Round 1 结论：`REQUEST_CHANGES`。

## Round 1 必改项

1. 计划必须明确 `effective-nonzero` 是成功分类，最终 cleanup proof 通过后返回
   0，不能继续触发现有 `kill_result=failed` fail-closed。
2. 最终 `systemctl stop` 后的 bounded wait 必须明确接受
   `inactive|failed`，不能只等待 `inactive`；SIGKILL 后 unit 保持 `failed` 是正常
   terminal state，本修订不引入 `reset-failed`。

## 已修订

两项均已写入
`p9-3c0-fixture-package3-crash-stop-deviation-plan.md` 的 §3.1：

- `effective-nonzero` 与 `ok` 同为成功语义；
- 最终 wait 接受 `inactive|failed`；
- 同时补充 pre-kill ledger-recorded cgroup authority、pre-graceful-stop 同 poll
  双证据、1 秒上限，以及 nonempty/unreadable/read-failed 必须 fail closed。

## Round 2 结论

同一模型路径重新审核修订后的完整 contract，结论为 `APPROVE`。JSONL 再次确认
provider-native model 为 `kimi-for-coding`，Claude Code 入口为 `sonnet`，未使用
Opus。Reviewer 明确确认 Round 1 两项 blocking finding 已完全闭合，并判断该
修订安全、最小且 fail-closed。

两项非阻塞建议也已由现有 contract 明确：

- `not-needed` 在最终 cleanup proof 通过后返回 0；
- 最终 terminal-state wait 固定为最多 60 次、每次 0.5 秒，即 30 秒。

因此该窄修订现为 `APPROVED_FOR_IMPLEMENTATION`。P9-3C1 仍未授权。
