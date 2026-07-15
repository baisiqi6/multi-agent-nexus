# P9-3C0 Package 3 crash-stop 偏差计划

状态：`APPROVED_FOR_IMPLEMENTATION`

## 1. 触发证据

真实 sidecar run `p9-3c0-pkg3-20260715h` 已通过 base concurrency、distinct
worktree/resource lease、hold `claude_child_boundary` 与精确 cgroup/process tree
证明。随后 timed stop 使用普通 `systemctl stop`，agentd 在 SIGTERM 后优雅完成
hold adapter call 并提交 `job.completed status=done`；attempt N lease 以
`release_reason=job_done` 释放，无法进入计划要求的 expiry/reap/recovery。

因此当前 stop 实现与已审核的“fixture 在 crash 前不产生 provider session，N 由
lease expiry/reap 进入 `timed_out`，随后 recovery 产生 N+1”语义不一致。

## 2. 审核结论

独立 Kimi plan reviewer 结论为 `APPROVE`：增加显式、opt-in 的 exact-unit
`--crash` stop 是最小正确修复。服务器 systemd 255 的实际参数 authority 为：

```text
systemctl kill --kill-whom=all --signal=SIGKILL <exact-unit>
```

不得使用 reviewer 草案中的旧拼写 `--kill-who`。

## 3. 实现边界

1. `p9-3c0-unit.sh stop` 接受无值 flag `--crash`，默认仍为 graceful。
2. crash 顺序固定为 exact `systemctl kill`、exact `systemctl stop`、bounded
   inactive/failed wait、recorded-cgroup-empty proof；timing 失败仍先完成此顺序。
3. active unit 的 kill 失败必须在完成安全 cleanup 后 fail closed；只有 kill 前已
   inactive/failed 才可将 nonzero 记为 `not-needed`。
4. ledger stop record 固定增加 `termination=graceful|crash`、
   `kill_signal=none|SIGKILL`、`kill_result=not-requested|ok|not-needed|failed`。
5. hold N timed stop 与 recovery N+1 stop 必须传 `--crash`。
6. E2 stop、failure trap、independent cleanup 与普通 operator stop 绝不能传
   `--crash`。

## 3.1 systemd 255 effective-nonzero 修订

真实 sidecar run `p9-3c0-pkg3-20260715i` 证明：`systemctl kill` 已向 exact unit
的 main、fixture child 与 descendant 发送 `SIGKILL`，unit 随后以
`status=9/KILL`、`Result=signal` 进入 `failed`，attempt N 仍保持
`running + active lease`；但 systemd 在清理 auxiliary process 时发生 race，命令
最终返回 nonzero。仅按 rc 判定会把已经成功形成的 crash 错报为失败。

本修订只增加一个窄分类 `effective-nonzero`：

1. kill 前使用 start ledger 中唯一 exact-unit record 的 `cgroup=` 路径；不得从
   kill 后状态重建、猜测或替换该 authority。
2. rc=0 仍记为 `ok`；kill 前已为 `inactive|failed` 且 rc nonzero 记为
   `not-needed`。
3. kill 前为 active 且 rc nonzero 时，必须在调用 graceful `systemctl stop`
   **之前**做最多 1 秒 bounded proof；同一次 poll 内同时满足 exact unit 为
   `inactive|failed`，且 ledger-recorded cgroup 已不存在或其 `cgroup.procs` 是
   readable regular file 且内容为空，才记为 `effective-nonzero`。
4. `effective-nonzero` 与 `ok` 都是成功结果：最终 cleanup proof 通过后 helper
   返回 0，不触发 fail-closed。
5. 如果 pre-stop proof 超时、unit 仍 active、cgroup nonempty、unreadable、读取
   失败或 authority 无效，必须记为 `failed`；完成 exact graceful cleanup 后返回
   nonzero。
6. 无论 kill 分类如何，最终仍调用 exact `systemctl stop`，bounded wait 接受
   `inactive|failed` 任一 terminal state；当前固定上限为 60 次、每次 0.5 秒，
   即最多 30 秒。随后再次证明 ledger-recorded cgroup absent/empty。不得要求
   `failed` 自动变回 `inactive`，也不新增 `reset-failed`。
7. 禁止以 journal 文本、PID/name pattern、kill rc 单独作为
   `effective-nonzero` authority。

ledger 枚举相应扩展为
`kill_result=not-requested|ok|not-needed|effective-nonzero|failed`。
`not-needed` 与 `ok`、`effective-nonzero` 一样，在最终 cleanup proof 通过后返回
0。

## 4. 禁止扩展

- 不改 Coordinate、agentd shutdown 语义、TTL 120 或 renewal interval 30；
- 不使用 wildcard unit、PID 猜测、`pkill`、`pgrep` 或 direct SQLite mutation；
- 不接触 canonical service、production DB 或 P9-3C1 activation。

## 5. 验证门

- helper mock tests 证明 flag parsing、kill-before-stop、graceful 不 kill、active
  kill failure 的 cleanup-then-fail、inactive nonzero 的 `not-needed`、active
  nonzero + pre-stop terminal/empty proof 的 `effective-nonzero`、terminal 但
  nonempty/unreadable 仍 fail closed，以及 ledger 字段；
- controller tests 证明仅 hold N 与 recovery N+1 传 `--crash`；
- shell parse、focused/adjacent/full pytest 与 merged-main validation 全通过；
- inert deploy 后使用全新 run id；N stop 后必须仍为 `running + active lease`，过
  `expires_at` 后 reap 为 `timed_out + expired`；N+1 重复 crash/expiry/reap；
- stale N report 必须被拒且 N+1 snapshot 不变；production baseline 完全不变；
- cleanup 完成且保留 sidecar evidence。P9-3C1 仍 blocked。
