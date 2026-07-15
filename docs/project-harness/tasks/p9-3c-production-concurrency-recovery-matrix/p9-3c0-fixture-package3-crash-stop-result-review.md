# P9-3C0 Package 3 crash-stop result review

Reviewed commit：`36f4fc7`

Verdict：`APPROVE`

独立 reviewer 通过 Claude CLI `--model sonnet` 执行；JSONL provider-native
model 为 `kimi-for-coding`，工具面限制为只读 `Read,Bash`。Reviewer 未发现
blocking finding，并逐项确认：

- `--crash` 是 opt-in，graceful default 未改变；
- exact `systemctl kill --kill-whom=all --signal=SIGKILL` 严格早于 exact
  `systemctl stop`；
- active kill failure 为 cleanup-then-fail，inactive/failed nonzero 为
  `not-needed`；
- timing invalid 仍先完成 termination/cgroup proof；
- ledger termination/signal/result 字段无歧义；
- 只有 hold N 与 recovery N+1 crash，E2/failure trap/cleanup 均 graceful；
- helper/controller tests 覆盖成功、失败与调用边界；
- docs 使用目标 systemd 255 实测的 `--kill-whom` 拼写。

验证基线：focused `188 passed, 26 subtests`；full `859 passed, 2 skipped,
81 subtests`；`bash -n` PASS。ShellCheck 仅报告该提交之前已有的 warning。

唯一 non-blocking minor：一个 `assertNotEqual` 未附 `result.stderr` 作为失败信息；
不影响测试断言或批准结论。
