# P9-3C0 Package 3 recovery worktree proof 偏差计划

状态：`RESULT_REVIEW_APPROVED_PENDING_DEPLOY`

## 1. 触发证据

isolated sidecar run `p9-3c0-pkg3-20260715k` 已通过：

- base concurrency：E1/E2 job 均 done、attempt 1、renewal 2；
- hold process tree 与 crash-stop：`kill_result=effective-nonzero`、约 80 秒、
  `verdict=ok`；
- crash 后 attempt N 仍 running、lease active；
- expiry 与 first reap；
- recovery unit 启动并 claim attempt N+1。

随后 `_p9c0_process_tree_proof` 以 exit 101 fail closed：

```text
fixture environment mismatch:
['PATH=/usr/local/bin:/usr/bin:/bin', 'LC_CTYPE=C.UTF-8',
 'PWD=/var/tmp/multinexus-p9-3c0/p9-3c0-pkg3-20260715k/work/p9-3c-fixture-e1']
```

真实 authority 同时证明：

- recovery namespace 为 `.../p9-3c0-pkg3-20260715k-r2`，使用 primary shared DB；
- recovered job、attempt 2 lease 的 `worktree_path/normalized_path` 均保持 primary
  `.../p9-3c0-pkg3-20260715k/work/p9-3c-fixture-e1`；
- `_p9c0_process_tree_proof` 却按当前 `P9C0_RUN_ID=-r2` 推导 expected PWD 为
  recovery namespace worktree。

因此 actual environment 的三项值本身正确；误报来自 proof 使用了错误 namespace
推导 expected worktree。

## 2. 最小修复

1. `_p9c0_real_process_tree_proof` 接受可选的第三个
   `expected_worktree`；未提供时仍使用当前 run 的既有推导，保持 base 路径不变。
2. recovery proof 调用显式传入 primary run 的 allowlisted E1 worktree：
   `STATE_PREFIX/$primary/work/p9-3c-fixture-e1`。
3. 不放宽 environment equality：仍要求恰好 `PATH`、`LC_CTYPE`、正确 `PWD` 三项；
   额外变量、错误 primary path 或 recovery namespace path 仍失败。
4. 不改变 recovery namespace、shared DB、job/lease worktree authority、process tree、
   systemd unit、TTL/reap/stale rejection、production snapshot 或 cleanup。

## 3. 回归门

- behavioral test 证明 base proof 未提供 override 时仍使用 current-run worktree；
- behavioral recovery test 捕获 proof argv，必须是 recovery unit/fixture PID 加 primary
  E1 worktree，同时 ledger 仍来自 recovery namespace；
- wrong/extra fixture environment 现有严格比较保持不变；
- Package 3 focused、adjacent、full pytest、`bash -n`、`compileall`、
  `git diff --check` 全通过；
- 独立 result review `APPROVE`。

## 4. 部署与重跑

- merge/push 后只用 `scripts/deploy-server.sh multinexus --no-restart`；
- 三个 canonical service PID/NRestarts 必须不变；
- 保留 runs `a` 至 `k`，使用 fresh run
  `p9-3c0-pkg3-20260715l` 完整重跑；
- production snapshot、cleanup、dogfood/closeout 完成前 P9-3C0 不收口；
- P9-3C1 仍未授权。

## 5. 独立计划审核

- verdict：`APPROVE`
- reviewer：Claude Code `--model sonnet`；JSONL assistant 事件实际
  `model=kimi-for-coding`，permission denial 0；
- reviewer caveat：primary E1 worktree 必须在把 `P9C0_RUN_ID` 切换到 recovery
  namespace 之前计算并保存；实现与测试必须锁定该顺序。

## 6. 独立结果审核

- verdict：`APPROVE`
- reviewer：Claude Code `--model sonnet`；JSONL assistant 事件实际
  `model=kimi-for-coding`，permission denial 0；
- reviewer 独立验证：targeted `2 passed`，focused process-tree/recovery
  `27 passed`，完整 Package 3 scripts `116 passed`，静态门全通过；
- residual gate：fresh production sidecar run `l` 尚未执行，不能据此收口。
