# P9-3C0 Package 3 Deployment and Dogfood

状态：`PASS_PENDING_INDEPENDENT_CLOSEOUT_REVIEW`

日期：2026-07-15

## 1. 最终部署边界

- Coordinate source/deployed：
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- MultiNexus source/main/deployed：
  `805901e635531e5cfe53bacce89536137727bfad`。
- 部署命令：
  `scripts/deploy-server.sh multinexus --host kook-hermes-admin --no-restart`。
- `scripts/p9-3c0-local-verify.sh` source/deployed SHA-256：
  `bf1d86d183462fa6c903a2f351ff28d589ad837d3f1d7ff3c7ebbee335f13061`。
- 最终部署前后 canonical PID 保持：Coordinate `836234`、Discord bridge
  `1276892`、KOOK Hermes `4551`；三者 `NRestarts=0`，均为
  `active/running`；server smoke PASS。

必须保留一项操作偏差：在较早的 `f2f309f` 部署轮次，Operator 曾遗漏
`--no-restart`，导致 Discord bridge 被部署脚本重启。该次立即验证并恢复了 canonical
agent/service 健康，但它违反 Package 3 inert-deploy 意图。此后的 snapshot、recovery、
nested-lock 修复部署全部显式使用 `--no-restart`；最终部署 PID/NRestarts 未变化。该偏差
不能从历史中删除，也不能被最终绿灯描述成“从未重启”。

## 2. 本地与独立审核门

- nested-lock targeted：`12 passed`；
- Package 3 script suite：`128 passed`；
- focused：`253 passed, 26 subtests passed`；
- adjacent authority/runtime：`207 passed, 39 subtests passed`；
- full：`878 passed, 2 skipped, 81 subtests passed`；
- `bash -n`、`compileall`、`git diff --check`：PASS。
- fresh Claude Code `--model sonnet` result reviewer 的 JSONL 实际 provider model
  为 `kimi-for-coding`。Round 1 只因审核文档 trailing whitespace 返回
  `REQUEST_CHANGES`；Round 2 对 exact head `719cec5` 返回 `APPROVE`。

## 3. Fresh-run 偏差账本

每次运行都使用新的 immutable run id；没有删除、覆盖或复用失败 namespace。服务器保留
runs `a-m`，以及实际到达 recovery 的 `k-r2`、`l-r2`、`m-r2`。

| Run | 首个 fail-closed 边界或结论 | 后续处理 |
|---|---|---|
| `a` | root controller 的 `runuser` 依赖 PATH，clean env 下入口不可达 | 改为绝对 `/usr/sbin/runuser` |
| `b` | `PrivateTmp` 使 unit 看不到未 bind 的 isolated state | 显式绑定批准的 state root |
| `c` | E1/E2 共享 worktree resource key，capacity lease 正确拒绝并发 | 为两个 fixture executor 使用 distinct worktrees |
| `d` | server installed Coordinate CLI 仍是旧 runtime surface | 完整安装 reviewed Coordinate revision 后重跑 |
| `e` | systemd journal 行带 Python logging prefix，严格 boundary parser 未归一化 | 只允许并归一化精确日志 prefix |
| `f` | shebang fixture 实际 process argv 与脚本路径证明不一致 | 证明 interpreter + script 的真实 argv 形态 |
| `g` | Python locale coercion 注入了受控环境字段 | 将可证明的 locale coercion 纳入 exact env contract |
| `h` | graceful stop 允许 hold job 自然完成，未形成 crash evidence | 引入精确 crash-stop 语义 |
| `i` | `systemctl kill` 在 SIGKILL 已生效后仍可能返回非零 | 只接受独立 cgroup-empty 证明的 `effective-nonzero` |
| `j` | production snapshot capture 使用 tuple、JSON reload 使用 list，未变数据被误报 drift | 统一 capture row 为 JSON-compatible list |
| `k` | recovery proof 用 `-r2` namespace 推导 PWD，但 shared job/lease worktree 仍属于 primary | 显式把 primary worktree 传入 recovery proof |
| `l` | 所有业务/数据门 PASS，但 nested `_p9c0_with_run_lock` 重用 FD 9，inner close 提前释放 outer primary lock，并出现 `flock: 9: Bad file descriptor` | depth `0/1` 显式映射 FD `9/8`，第三层 fail closed；run `l` 不计 lock-gate PASS |
| `m` | exit 0；完整 base/crash/reap/recovery/stale/cleanup PASS；无任何 flock warning | 接受为 Package 3 最终 production-host isolated sidecar 证据 |

这些轮次证明 fail-closed 校验不是噪声：每一轮都暴露一个可复现的 harness、process、
snapshot 或 lock authority 偏差；修复经过独立 plan/result review 后才允许新 run id。

## 4. Run `m` 精确执行与证据

准备与验证只针对新 namespace：

```text
sudo /opt/multinexus/scripts/p9-3c0-local-verify.sh prepare \
  --run-id p9-3c0-pkg3-20260715m \
  --unit-user coord --unit-group coord --agent p9-3c-fixture-e1

sudo /opt/multinexus/scripts/p9-3c0-local-verify.sh verify \
  --run-id p9-3c0-pkg3-20260715m \
  --unit-user coord --unit-group coord
```

Preflight：namespace absent；production DB `integrity=ok`、schema `13`、
pending/running jobs `0`、active leases `0`、fixture agents/runners `0`；fixture units
为空。

核心 evidence：

- E1/E2 base jobs 都为 `done`，各自证明 `renewals=2`；
- hold process tree 记录 agentd MainPID、fixture PID `1821326`、sleep PID `1821327`
  与 exact cgroup；
- crash stop：`elapsed=80040` ms、`kill_signal=SIGKILL`、`kill_result=ok`、
  `verdict=ok`；E2 为 deliberate graceful stop；
- hold lease `8e812872-d1ad-49b8-9d4f-898075a8d973` 到期后 first reap；
- recovery run `p9-3c0-pkg3-20260715m-r2` 使用 shared isolated DB，attempt `2`、
  lease `6473dfea-dee4-4074-b3b7-a65a7d6df330`；
- stale attempt N 被拒绝，job/N+1 lease/event/delivery snapshot 未变；
- recovery stop、expiry 与 second reap 完成；
- cleanup 固定经过 `freeze -> units-quiescent -> executor-v3-disabled ->
  capacity-v2-empty -> executor-v4-empty -> units-cleaned -> snapshot-retained -> done`；
- nested recovery lock 实际执行后没有 `flock` warning，outer primary lock 没有被
  inner recovery lock 覆盖或提前关闭。

## 5. 最终数据与 residue

Run `m` control/evidence：

- `phase=done`；
- `cleanup-phase=done`；
- `intake=frozen`；
- `evidence=verified-and-cleaned`。

Isolated DB：

- `integrity=ok`、schema `13`；
- jobs：`done=2`、`timed_out=1`；
- leases：`expired=2`、`released=2`；
- pending/running `0`、active leases `0`；
- definitions/bindings/capacity policies 均 `0`；
- retained empty source metadata：executor v4、capacity v2；
- dormant fixture agents/runners 仅保留在 isolated DB，符合计划。

Cleanup final snapshot：isolated SHA-256
`cadf2c731a201377093c60697c157a750b3c2ecf9655798ea595c09ecaebb173`，
production SHA-256
`260abe6c4d5d5d73dfc5e7c9206d5917060c84ac263fb311a52712f14fc1ae99`。

Production：

- DB `integrity=ok`、schema `13`；
- pending/running `0`、active leases `0`、fixture agents `0`、fixture runners `0`；
- fixture systemd units `0`；fixture Python/sleep processes `0`；
- canonical PID/NRestarts 与部署前完全一致；
- run roots 与 mode-restricted evidence 被保留，未直接删除或修写 SQLite。

## 6. 边界

本证据只关闭 P9-3C0 Package 3：它证明 production host 上的 isolated sidecar 与
canonical production read-only comparison。它没有把 fixture executor/capacity source
注册到 production DB，没有执行付费 provider request，也没有授权 P9-3C1 production
catalog activation、真实 production jobs/leases/reap 或 canonical service restart。
