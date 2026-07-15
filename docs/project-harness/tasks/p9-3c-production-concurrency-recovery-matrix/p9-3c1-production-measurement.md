# P9-3C1 Production Matrix — Fresh Measurement

状态：`MEASURED_PLAN_REQUIRED_PRODUCTION_BLOCKED`

日期：2026-07-15 Asia/Shanghai

本文件只记录只读测量与架构判断，不授权 fixture catalog activation、production
job/lease、reap、crash、service restart、deploy 或其他生产 mutation。

## 1. 精确 revision 与 live baseline

- Coordinate source/origin/deployed：
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- MultiNexus source/origin/deployed：
  `d09e0f8fba0f6d189934173027ca5a756e5f36ce`。
- Production host：`VM-0-15-ubuntu`，SSH alias `kook-hermes-admin`。
- Installed CLI：`/usr/local/bin/coord-local`，`coordinate 0.1.0`。
- Production DB：`/var/lib/coordinate/coord.sqlite3`。

2026-07-15 fresh read-only probe：

- `integrity_check=ok`、schema `13`、FK violations `0`；
- pending/running/recoverable-timeout jobs `0`，active leases `0`；
- fixture agents/runners/executor sources/capacity sources/bindings/policies/jobs/leases
  均为 `0`；
- production executor source 仅 `multinexus.discord` v2；
- production capacity source 仅 `multinexus.discord.capacity` v1；
- terminal history 为 `done=151`、`failed=20`；
- `coordinate.service` PID `836234`，Discord bridge PID `1276892`，KOOK Hermes
  PID `4551`；三者 `NRestarts=0`、`active/running`。

Coordinate worktree 有用户拥有的未跟踪 `.qoder/`；它不属于本任务，不得删除、修改、
提交或用 destructive Git 命令处理。MultiNexus worktree 在测量时 clean。

## 2. P9-3C0 已证明什么

P9-3C0 Package 3 fresh production-host isolated run
`p9-3c0-pkg3-20260715m` 已用相同 installed Coordinate/MultiNexus runtime 证明：

- 两个 typed capacity-1 executor；
- distinct-worktree concurrency 与 lease renewal；
- exact cgroup/process-tree crash stop；
- expiry、reap、N+1 recovery、stale-N rejection；
- cleanup state machine、production fingerprint compare 与 nested controller lock。

它使用 fresh isolated DB，明确拒绝 production DB。因此 P9-3C1 的新增价值不是再证明
一次纯算法，而是证明：第二 executor/capacity source 与 canonical production source
在真实 production DB 中可以安全共存、执行、停用和留下可解释的 terminal audit residue。

## 3. 旧 umbrella plan 的漂移

原 `plan.md` 写于 P9-3C0 Package 3 之前，不能直接执行：

1. 它偏好 same-host Mac fixture；实际 reviewed fixture 位于 production Linux host 的
   transient systemd units。
2. 它使用 global `runtime job lease reap --batch-size 100`。当前 CLI 没有 exact
   `lease_id/job_id` filter；生产中这可能同时处理非 fixture due lease。
3. Row G0/G1 把 `coordinate.service` restart 当 lease 证据。实际 agentd 的
   claim/renew/report 均由独立 subprocess 调 `/usr/local/bin/coord-local` 直接访问
   SQLite；`coordinate.service` 的 `ExecStart` 是 `coordinate ... serve`，主要负责
   Discord/event pump。重启它与 attempt lease availability 没有因果关系。
4. 它没有处理 deployment 与 matrix activation 的跨任务线竞态。P9-3C1 active lease
   会让 capacity snapshot restore 正确 fail closed；同时 deploy 也可能替换 fixture 文件
   或 catalog。
5. 它把 zero residue 描述得过宽。`execution_attempt_leases` 对 `agents`/
   `runner_profiles` 有 `ON DELETE RESTRICT`，审计 job/lease 保留后，fixture agent/runner
   不应被直接 SQLite 删除。
6. 它没有规定 terminal response delivery 的收口。fixture `complete` 返回
   `response_text`，Coordinate 会创建 reply delivery；使用未支持的 `local-fixture`
   platform 会留下 pending residue。

## 4. 当前缺失的生产安全原语

### 4.1 Exact scoped reap

当前 `reap_due_leases()` 先按全局到期时间读取 bounded batch，再逐 lease transaction
处理。它本身对每个 lease fail closed，但 CLI 只能做 global batch。P9-3C1 需要新的
exact 模式，例如：

```text
coordinate runtime job lease reap --lease-id <lease-id> --job-id <job-id>
```

该模式必须同时绑定 expected `lease_id` 与 `job_id`，只允许处理这一行；not found、
identity mismatch、not due、non-active 均返回 machine-readable no-mutation result，绝不
fallback 到 global scan。现有 global `--batch-size` 保持兼容，但 P9-3C1 禁用它。

仅增加 exact reap 仍不够：`claim_leased_job()` 当前在每次 claim transaction 内先调用
`_reap_due_leases_in_transaction()`，因此 fixture claim 也可能顺带 reap 非 fixture due
lease。需要给 claim 增加显式 `reap_mode=global|none` contract：默认 `global` 保持现有行为；
`none` 必须携带 bounded audited operator reason，并由 P9-3C1 的 normal/recovery agentd
claim 全程使用。它不能依赖 live preflight 恰好没有其他 due lease。

### 4.2 Runtime agent deactivate

`runtime agent register` 会 upsert agent 为 `online` 并在缺失时创建同 id 的
`runner_type=agentd` profile。当前无 unregister/deactivate CLI。由于 audit FK，删除不是
正确 cleanup；需要受控：

```text
coordinate runtime agent deactivate --agent-id <id> --host-id <host> --reason <reason>
```

它必须验证 exact host/client、零 active lease、零 pending/running/recoverable job，再把
agent 标记 `offline` 并 append audited event。runner、terminal jobs/leases 保留。

### 4.3 Cross-workflow production mutation lock

P9-3C0 的 controller lock 只保护一个 isolated run root，不保护生产 deploy。P9-3C1
需要 server-owned atomic lock directory/token，由以下两方共同遵守：

- `scripts/deploy-server.sh coordinate|multinexus`；
- P9-3C1 production controller。

锁必须在文件 copy、catalog snapshot/sync、service action 或 fixture activation之前获取，
贯穿整个 mutation window；竞争者 fail closed。异常留下 stale lock 时不得自动偷锁，需
显式 status/recover、匹配 token 与 operator reason，并先证明无 live owner/matrix unit。
首次安装 helper 也必须先用同一 atomic directory/token 的 bootstrap protocol 获取锁，不能
把“helper 尚未安装”当作无锁 copy window。

## 5. Fixture production projection 的必要修正

现有 P9-3C0 executor definition capability 是 `coding`。即使 dedicated workspace 限制了
normal routed candidate，这个 capability 在 production activation window 仍不应与真实
coding executor 重叠。P9-3C1 使用独立 source id 与唯一 capability：

- executor source：`p9-3c1-fixture-executors`；
- capacity source：`p9-3c1-fixture-capacity`；
- definition capability：`p9-3c1-fixture`；
- agents：复用 reviewed unit helper allowlist 的 `p9-3c-fixture-e1/e2`；
- workspace：`p9-3c1-production`；
- host：`VM-0-15-ubuntu`。

Execution 只允许 exact target，不允许 route-capability。Dedicated workspace 默认 bus 为空；
job reply 使用 supported `stdout` platform。每个 exact response delivery 必须由 controller
按 returned delivery id 单独 `delivery send`，记录 stdout evidence，并最终为 `sent`；不得
留下 pending/failed fixture delivery，也不得发 Discord/KOOK/Webhook。

## 6. 合理的 terminal residue

P9-3C1 cleanup 的正确 postcondition：

- zero active fixture lease；
- zero pending/running/recoverable fixture job；
- zero fixture unit/process；
- zero enabled/disabled fixture binding、definition、capacity policy；
- fixture executor/capacity source metadata 仅保留 empty higher version；
- fixture agents 为 `offline`；runner profiles dormant；
- workspace/host profile、terminal jobs、released/expired leases、events、sent stdout
  deliveries 作为 namespaced audit/evidence residue 保留；
- canonical source/policy/binding projection exact preserved；
- production integrity/schema/FK 保持 `ok/13/0`。

这不是“零 row”，而是“零可执行状态 + 精确、不可 claim、可审核的 dormant history”。

## 7. 新计划的最小矩阵

旧 8-job A–G 可缩为 5 个 jobs，同时保留所有有因果的 production 证明：

- A/C：E1 顺序完成 J1/J2；J1 active 时 exact second claim 返回
  `capacity_exhausted`，且两个 complete job 各有至少两次 automatic renewal。
- B：E1/W1 hold 与 E2/W2 complete 并发；E2 空闲后，E2/W1 的 J5 返回
  `resource_blocked`。
- D/E/F：对 E1/W1 的 hold J3 exact crash-stop，等待 expiry，使用 exact scoped reap；
  recovery unit 仍固定为 `hold` mode；controller read-only 等待 attempt N+1/L3b active 后，
  执行 stale-N progress/report/renew rejection，再用 current N+1 lease 和 empty result
  terminal-report J3，观察 lease-lost cancellation/cgroup cleanup；recovery unit 永不使用
  `complete` mode。随后 J5 可 claim/complete。

删除 G0/G1。Canonical service restart 不是 P9-3 lease contract 的证明，也不是 P9-3C1
cleanup 手段。

## 8. 规划结论

P9-3C1 不能直接进入 bootstrap。先完成新的 detailed plan 与 independent review；plan
通过后依次交付 production mutation lock、Coordinate scoped primitives、inert production
controller，分别 result-review/deploy；最后才允许 exact-revision live bootstrap 与一次
fresh immutable production run。

P9_3C1_FRESH_MEASUREMENT_COMPLETE_PRODUCTION_STILL_BLOCKED
