# P9-3C0 Package 3 crash-stop plan review

结论：`APPROVE`

Reviewer 通过 Claude CLI `--model sonnet` 执行；JSONL 中 provider-native model
为 `kimi-for-coding`，未使用 Opus。审查为只读，覆盖 helper stop/cleanup、local
verifier、tests、Package 2/3 plan、measurement 与 runbook。

批准条件已归入
`p9-3c0-fixture-package3-crash-stop-deviation-plan.md`：显式 opt-in、exact-unit
`SIGKILL` 后再 stop、cgroup-empty proof 不得省略、只有 N/N+1 crash、其他 stop
保持 graceful、失败后 cleanup-then-fail，以及完整 ledger/test/doc/sidecar gate。

Reviewer 草案使用 `--kill-who=all`；operator 已在目标 systemd 255 上核对真实
CLI authority 并修正为 `--kill-whom=all`。这是审核后的必要兼容性修订，不改变
批准的终止语义。
