# P9-3C1 Production Concurrency/Recovery Matrix — Detailed Plan

状态：`DRAFT_FOR_INDEPENDENT_PLAN_REVIEW_PRODUCTION_BLOCKED`

日期：2026-07-15 Asia/Shanghai

Measurement：`p9-3c1-production-measurement.md`

本计划替代旧 `plan.md` 中 P9-3C1 的可执行细节；旧文件继续作为历史 umbrella plan，
不得被当作 bootstrap。任何 production activation 都要等本文件 exact revision 获得独立
plan approval，并完成下面各 package 的 bootstrap/result/deploy gate。

## 1. 目标

在不调用 paid coding provider、不影响真实 executor/job、不重启 canonical services 的
前提下，把 reviewed P9-3C0 fixture 作为第二组临时 production catalog authority 激活到
真实 Coordinate DB，验证：

- capacity-1 saturation/release；
- different-worktree cross-executor concurrency；
- same-worktree cross-executor exclusion；
- quiet automatic renewal；
- exact crash-stop、expiry、scoped reap、N+1 recovery、stale-N fencing；
- multi-source activation/cleanup 与 canonical projection exact preservation；
- concurrent deploy/matrix mutation fail-closed；
- cleanup 后只有 offline/dormant/terminal audit residue，无可执行 fixture state。

## 2. 非目标

- 不验证 provider-native JSONL/session handle；属于 P9-4。
- 不执行多项目/多 provider/full Discord matrix；属于 P9-5。
- 不重启 `coordinate.service`、Discord bridge 或 KOOK Hermes。
- 不使用 global lease reap 作为 P9-3C1 evidence。
- 不直接 SQLite INSERT/UPDATE/DELETE，不删除 terminal jobs/leases/events/deliveries。
- 不把 fixture capability 暴露为 `coding`/`review`，不允许 routed submission。
- 不把 whole-DB restore 当普通 cleanup；仅作为另行批准的 incident recovery last resort。

## 3. 固定 authority 与命名

- Production DB：`/var/lib/coordinate/coord.sqlite3`。
- Installed CLI：`/usr/local/bin/coord-local`。
- Host：`VM-0-15-ubuntu`。
- State root：`/var/tmp/multinexus-p9-3c1/<run-id>`。
- Global mutation lock：`/run/lock/coordinate-production-mutation.lock/`。
- Workspace：`p9-3c1-production`。
- Agents：复用 reviewed unit helper allowlist 的 `p9-3c-fixture-e1`、
  `p9-3c-fixture-e2`；workspace/source/run id 仍使用 `p9-3c1-*` namespace。
- Executor source：`p9-3c1-fixture-executors` versions 1 disabled、2 enabled、
  3 disabled、4 empty。
- Capacity source：`p9-3c1-fixture-capacity` versions 1 active、2 empty。
- Capability：仅 `p9-3c1-fixture`。
- Run id：`p9-3c1-prod-<UTC timestamp>-<short nonce>`，只能 fresh 创建一次。
- Job budget：exactly 5 submitted jobs；unit concurrency最多 2；paid provider calls 0。

所有可控 task/idempotency/actor/session/temp/unit 名都含 run id。Coordinate-generated
job/lease/delivery ids 写入 mode `0600` append-only ledger，不假设含 namespace。

## 4. Package 顺序与 hard gates

### Package P0 — Shared production mutation lock

目标：阻止另一条 deploy/task line 在 P9-3C1 activation window 替换生产文件、catalog 或
service，同时阻止 P9-3C1 在 deploy 中途进入。

实现范围：

- 新增小型 lock helper，提供 `acquire/status/release/recover`；
- `acquire` 通过 root-owned atomic `mkdir` 获得唯一 owner token，metadata 使用
  `O_EXCL`/mode `0600`，lock directory 为 root-owned mode `0700`，metadata 包含 bounded
  owner/action/host/start time/token；非 root mutation caller fail closed；
- `release` 必须 exact token match；unknown/mismatch 不得删除；
- `recover` 需要 exact stale token、operator reason，并证明无 P9-3C1 transient unit，
  不允许基于 age 自动 steal；
- `scripts/deploy-server.sh coordinate|multinexus` 在第一个 rsync/copy/snapshot/sync/
  restart 前 acquire，在成功 smoke 或失败 rollback/cleanup 完成后 release；`--no-restart`、
  skip-smoke/inert deploy 也必须持锁，只有纯 read-only `status` 不获取 mutation lock；
- P9-3C1 controller 使用同一 helper/lock directory，整个 live run 持有一次 token；
- 首次 helper bootstrap 由 deploy script 先用同一 lock directory/token/metadata contract 的
  bounded inline acquire 获锁，再 atomic install helper；新 helper 必须 adopt/validate 同一
  token，随后承担 status/release。bootstrap 只允许 helper 缺失且 lock free、无 P9-3C1
  unit/process 时执行，不形成未受保护的 first-deploy copy window；
- shell exit、signal 与 remote failure tests 证明不 silent unlock；stale lock 是 loud blocked
  state；`status` 只读返回 owner/action/start/phase，不创建、更新或释放锁。

建议文件边界：

- `scripts/production-mutation-lock.py`；
- `scripts/deploy-server.sh`；
- `tests/test_production_mutation_lock.py`；
- `tests/test_deploy_contract.py`。

P0 plan approval 后才生成 P0 worker bootstrap。P0 必须独立 result approval、merge、push、
inert deploy 与 lock status smoke 完成，才能进入 P1 deploy。首次 inert deploy 不允许 restart。

### Package P1 — Coordinate scoped production primitives

目标：移除 P9-3C1 对 global reap 和 permanently-online fixture agent 的依赖。

#### P1.1 Exact scoped reap

CLI contract：

```text
coordinate runtime job lease reap \
  --lease-id <lease-id> --job-id <job-id> --actor <actor>
```

- parser 将 `--batch-size` 改为 optional/default `None`：无 exact ids 且未显式传值时 dispatch
  legacy global batch `100`；`--lease-id` 与 `--job-id` 必须同时出现，且与显式
  `--batch-size` mutually exclusive；
- exact mode 单 transaction 读取一个 lease，验证 exact job id、status active、due、stored
  snapshot 与 matching running attempt；
- 成功只 expire 这一 lease/CAS 这一 job/append 对应 events；
- not found、job mismatch、not active、not due、CAS/stored snapshot mismatch 均 fail closed，
  返回 bounded machine-readable result 或 nonzero contract error；不得 global fallback；
- existing no-filter global mode behavior/CLI contract 保持兼容；
- tests 必须同时放置另一个 due real-like lease，证明 exact reap 后它完全未变。

建议实现：在 `runtime_lease.py` 增加独立 `reap_exact_lease()`，不要把更多分支堆进
`reap_due_leases()`；`execution_cli.py` 只负责参数/dispatch。

#### P1.2 Claim-time reap policy

当前 `claim_leased_job()` 无条件调用 transaction-local global due reap。新增显式 contract：

```text
coordinate runtime job claim \
  --agent-id <id> --reap-mode none --reap-reason <bounded-reason>
```

- `reap_mode` 只允许 `global|none`，API/CLI default `global`，保证所有既有 caller 行为不变；
- `none` 必须有 nonblank/bounded/control-char-free `reap_reason`；`global` 携带 reason、unknown
  mode 或部分参数均 fail closed before transaction；
- `none` 跳过 `_reap_due_leases_in_transaction()`，只执行 claim 本身；返回值与 audited
  `job.claimed` payload 记录 reap mode/reason，未 claim 时也在 controller ledger 记录 exact
  argv/result；
- MultiNexus `CoordinateRuntimeClient.claim_job()`、agentd CLI/worker 增加对应显式参数，normal
  与 recovery fixture unit 均固定传 `none` 和 sealed P9-3C1 reason；非 fixture default 不变；
- tests 放置 nonfixture due sentinel，证明 `none` normal/recovery claim 不改变其 lease/job/
  events；另测 default `global` regression contract 与 invalid combinations zero mutation。

建议 Coordinate 文件边界为 `runtime_lease.py`、`runtime.py`、`execution_cli.py` 及 focused
tests；MultiNexus propagation 归 P2 实现，避免 P1 跨 repo 半部署。P1 deploy 后 P2 未部署前，
现有 agentd 仍走 default `global`。

#### P1.3 Runtime agent deactivate

CLI contract：

```text
coordinate runtime agent deactivate \
  --agent-id <id> --host-id <host> --reason <bounded-reason> --actor <actor> [--dry-run]
```

- unknown agent、host mismatch、non-agentd、blank/oversized/control-char reason fail closed；
- exact query 同时检查 active lease 与该 agent 的 `pending`、`running`、
  `timed_out AND recoverable=1` jobs；任一存在时 zero mutation；
- 成功只把 exact agent `online_state=offline`，不删除 agent/runner/history；
- append idempotent audited `agent.deactivated` event；exact retry 返回 stable offline state；
- `--dry-run` 执行全部 identity/blocker checks 并返回 machine-readable projected result，绝不
  update/append event；
- heartbeat 可按现有 contract 再激活同 host agent；不同 host/client identity 仍 fail closed；
  cleanup 后出现同-host heartbeat/reactivation 属 incident，不能被当作 successful cleanup。

建议文件边界：

- `src/coordinate/runtime.py`；
- `src/coordinate/execution_cli.py`；
- focused runtime/CLI tests 与 CLI golden fixture。

P1 必须经过独立 result approval，再用 P0 lock deploy Coordinate。Deploy 后只做 read-only
help/version/integrity smoke，不创建 fixture row、不执行 reap/deactivate mutation。

### Package P2 — Inert production controller and assets

目标：把 P9-3C0 的 reviewed fixture/unit contract 包装成显式 production-aware、可恢复、
不可误指 isolated/prod DB 的 controller。

建议文件边界：

- `scripts/p9-3c1-production-verify.sh`：thin root/run-id entrypoint；
- `scripts/p9_3c1_controller.py`：state machine、CLI arrays、read-only DB evidence、ledger；
- `multinexus/fixture/config/p9-3c1/`：独立 v1-v4 executor/v1-v2 capacity/
  rendered agent config templates；
- 复用 `multinexus/fixture/bin/p9-3c0-fixture.py` 与 `p9-3c0-unit.sh`，不复制 process
  stop/cgroup logic；固定复用其 `p9-3c-fixture-e1/e2` allowlist，不为 P9-3C1 改 agent id；
  preflight 必须解析/cross-check helper allowlist 与 sealed agent ids exact match；如复用边界
  不够，先写 deviation plan，不得 silent fork；
- `multinexus/agentd/coordinate_client.py`、agentd CLI/worker 支持并校验 P1.2 claim reap
  policy；P9-3C1 unit normal/recovery 两条路径都固定 `none` + sealed reason；
- `tests/test_p9_3c1_production_controller.py` 与 adjacent deploy/fixture tests；
- `multinexus/fixture/docs/runbook.md` 增加 P9-3C1 production section。

Controller 子命令：

- `prepare --run-id ... --unit-user coord --unit-group coord`：只创建 immutable sealed
  state/expected hashes；拒绝已存在 run id；不得打开 production DB writable；
- `preflight --run-id ...`：read-only，验证 exact revision、installed hashes、lock status、
  schema/integrity/FK、fixture absence、canonical projection 与 service identities；
- `run --run-id ...`：获取 global lock 后执行完整 activation/matrix/cleanup；不提供跳过
  cleanup、跳过 gate、allow-dirty、force-reuse；
- `status --run-id ...`：read-only；
- `cleanup --run-id ...`：只允许从 ledgered phase 恢复，仍需 global lock；不得删除
  terminal DB history。

P2 的 local tests 使用 temp DB/fake system seams；随后在 production host 只做 inert deploy、
`prepare/preflight/status`。不得 sync source/register agent/create job/start unit，直到 P3 live
bootstrap independently approved。

### Package P3 — Exact live activation and matrix

P3 不是 coding bootstrap。它是 bind exact installed revisions/hashes/run-id/commands/
budgets/stop conditions 的 operator bootstrap。只有 P0/P1/P2 均 close 后才生成；fresh
independent reviewer 必须核验 live preflight 并批准 exact P3 bootstrap。

## 5. P2/P3 controller state machine

固定 forward phases：

```text
sealed
-> preflight-ok
-> lock-held
-> baseline-captured
-> workspace-ready
-> agents-online
-> executor-v1-disabled
-> capacity-v1-active
-> executor-v2-enabled
-> matrix-running
-> matrix-verified
-> intake-frozen
-> units-quiescent
-> executor-v3-disabled
-> capacity-v2-empty
-> executor-v4-empty
-> agents-offline
-> canonical-compared
-> done
```

每个 transition 先验证上一 phase 与 authority，再执行一次 bounded command，最后写
append-only ledger/atomic phase file。Restart/resume 只从已证明的 phase 继续；不根据目录
猜测成功。Cleanup reverse semantics 固定，不回滚 terminal history。

## 6. Live preflight gates

在任何 production mutation 前，P3 必须同时满足：

1. source/origin/deployed revision 与 bootstrap exact match；worktree 无 task-overlap dirty
   change，Coordinate `.qoder/` 明确忽略且不触碰；
2. installed controller/config/fixture/unit/Coordinate module hashes exact match；
3. global mutation lock free，随后 controller atomic acquire 并保持到 final compare；
4. production DB `integrity=ok`、schema 13、FK 0；
5. fixture source/workspace/job/lease/unit/process 全部 absent（首次 run）；reviewed shared agent
   ids 若已有 residue，必须 exact host、offline、无 executable state，否则 halt；
6. canonical executor/capacity source/binding/policy projection snapshot sealed；
7. exact fixture helper allowlist 为 `p9-3c-fixture-e1/e2` 且 unit allowlist empty，无相关
   process/cgroup；
8. five-job budget、two-unit budget、zero-provider network/credential restrictions sealed；
9. stdout delivery path supported；Discord/KOOK/Webhook destination forbidden；
10. backup/snapshot evidence fresh、mode 0600。普通 cleanup 不调用 restore；
11. read-only inventory 证明当前 due active leases 为 0；这只是 defense-in-depth，P1.2
    `reap_mode=none` 才是 claim 不触碰 nonfixture due lease 的 correctness boundary。

如果 live baseline 在 plan review 后发生任何 material drift，P3 bootstrap 失效，回到 fresh
measurement/review；不得边执行边修计划。

## 7. Catalog activation

在 lock 内按固定顺序：

1. 创建或 exact-retry dedicated workspace/host profile；default bus/destination 为空；
2. register E1/E2 为 exact host agentd；
3. sync executor v1 disabled；
4. sync capacity v1，E1/E2 各 capacity 1；
5. sync executor v2 enabled；
6. exact readback：canonical + fixture 两个 disjoint executor sources、两个 disjoint
   capacity sources共同满足 global coverage；fixture capability 仅 `p9-3c1-fixture`；
7. routed candidate negative probe只读/isolated API 证明普通 `coding` route 不会选 fixture；
8. open fixture intake，仅允许 controller 生成的 5 个 exact-target requests。

任何 sync failure 立即 freeze intake，进入固定 cleanup；不得 restore whole DB。

## 8. 五-job production matrix

### Row A/C — Capacity saturation、release 与 quiet renewal

1. 启动 E1 unit；提交 E1/W1 `J1 complete` 与 E1/W2 `J2 complete`。
2. J1 running/lease L1 后，controller 额外 exact claim E1；必须返回
   `claimed=false, reason=capacity_exhausted`，无 lease。
3. J1 在零 manual renew 下至少两次 `expires_at/renewed_at` 单调前进，journal 至少两条
   accepted renewal；随后 automatic report done/release L1。
4. E1 自动 claim J2；同样至少两次 renewal，automatic report done/release L2。
5. 对 J1/J2 returned response delivery id 分别执行 exact `delivery send`；platform 必须
   `stdout`、status 最终 `sent`；按 id readback 核验 job/request linkage、platform、payload
   hash/message id 与 captured stdout exact match，不触发 external bus。

Pass：从未同时有两个 E1 active leases；blocked reason exact；两个 job done、leases released、
renewal≥2、deliveries sent。

### Row B + D/E/F — Cross-executor resource、expiry/recovery/stale fence

1. 启动 E1 hold J3/W1；确认 active L3、attempt N、exact process/cgroup、至少两次 renewal。
2. 同时启动 E2 complete J4/W2；证明 L3/W1 与 L4/W2 active overlap，J4 自动完成并发送
   stdout delivery。
3. E2 空闲后提交 J5/W1；manual exact claim E2 必须
   `claimed=false, reason=resource_blocked`，blocking resource 与 L3 exact match。
4. 对 J3 process tree 按 reviewed monotonic/cgroup boundary exact SIGKILL；证明 cgroup empty，
   不 report、不 renew。
5. 等 L3 exact expiry；运行 P1 scoped reap，必须只处理 L3/J3。并置的 nonfixture due
   sentinel 已在 P1 exact-reap 与 claim-reap-policy tests 分别证明完全未变；live run 记录
   reap 前后所有 active lease ids，即使出现非 fixture active/due lease也不得 global reap，
   exact reap result 必须证明只触及 L3/J3，否则 halt。
6. J3 必须 `timed_out,recoverable=1`，L3 expired。启动 E1 recovery unit，使用 exact
   `hold` mode 与 `--recoverable --recovery-reason ... --prior-process-stopped`；normal/recovery
   claims 均传 P1.2 `reap_mode=none`。Controller 只读等待并证明返回同一 J3、attempt N+1、
   新 lease L3b、同一 W1 active；recovery unit 永不使用 `complete` mode。
7. L3b active 时，用 old N/L3 分别尝试 progress、report done、renew；三者必须 fail
   closed，J3/L3b/events/deliveries authoritative snapshot 不变，允许新增 bounded denial
   audit only if contract already defines it。
8. Controller 用 current N+1/L3b 与 empty result JSON exact report J3 done，使 L3b released；
   renewal supervisor 必须观察 lease loss并取消 hold adapter，最终 recovery cgroup empty，
   不创建 response delivery。不得由 recovery adapter automatic complete 抢先终结 J3。
9. E2 claim J5；必须成功、lease L5/W1；至少两次 renewal后 automatic done/release，并发送
   exact stdout delivery。

Pass：different W overlap、same W exclusion、scoped reap、same-job N+1 recovery、三类 stale
mutation rejection、current attempt terminal cleanup 与 resource release 全部成立。

## 9. Cleanup 与 final acceptance

无论 matrix pass/fail，controller 都先 freeze own intake，再按 state machine cleanup：

1. exact stop/verify allowlisted fixture units/cgroups；
2. 处理 remaining fixture active lease：优先 current exact report/cancel contract；只有 due
   lease 才使用 exact scoped reap；
3. sync executor v3 disabled；
4. sync capacity v2 empty；
5. sync executor v4 empty；
6. P1 deactivate E1/E2；
7. exact canonical projection compare；
8. DB integrity/schema/FK；
9. verify zero fixture pending/running/recoverable job、active lease、pending/failed delivery、
   binding/definition/policy、unit/process；
10. verify fixture source rows only empty v4/v2，agents offline，runner/workspace/terminal
    history exact namespaced；
11. deactivate 后持续一个 bounded heartbeat interval 证明 agents 仍 offline；任何 unexpected
    heartbeat/reactivation 立即进入 incident boundary；
12. verify canonical services PID/NRestarts unchanged；
13. release global lock only after final evidence fsync/phase done。

Final acceptance 同时要求：

- 5 jobs exactly，budget 未超；
- paid provider/network credential use 0；external messages 0；
- all matrix assertions pass；
- no unclassified deviation；
- production DB/canonical projection/service identity healthy；
- independent live result reviewer 对 exact revision、server ledger、DB filtered evidence、
  unit/journal/process evidence返回 approve；
- dogfood/deviation/closeout/progress/roadmap/Phase 9/planning docs同步；
- P9-3C1 的 checklist/materialization/receipt 只走 reviewed host-aware workflow，不手改
  canonical checklist。

## 10. Halting 与 incident boundary

立即 halt/freeze/stop exact fixture processes并保留 forensic evidence：

- lock ownership丢失、token mismatch、另一 deploy/matrix mutation出现；
- canonical source/policy/binding drift；
- same resource 出现 duplicate active lease；
- scoped reap触及非 exact lease/job；
- stale N mutation成功；
- recovery返回不同 job；
- external delivery 被创建/发送；
- real user/executor job 被 claim/reap/cancel/report；
- integrity/FK failure；
- cleanup phase无法证明。

Whole-DB restore 不是自动 rollback。只有 fresh forensic copy、证明无 intervening writes、
独立 incident plan/review 与明确 human authorization 后才可考虑。

## 11. Review、worker 与 model policy

- Codex 保持 architect/operator/final reviewer；
- coding worker 优先 Kimi，通过 Claude Code `--model sonnet`，禁止 Opus；
- 每次 session 从 provider-native JSONL assistant event 核验 actual model，预期
  `kimi-for-coding`；标签或 CLI 参数本身不算证明；
- plan reviewer 与 result reviewer 必须独立于对应 writer/worker；
- 若 Kimi/Claude route 不可用，按用户既定顺序再评估 GLM、DeepSeek V4 Pro、MiniMax M3，
  不得静默换模型；
- 每个 package 均遵循 plan approval -> reviewed bootstrap -> worker -> Codex review ->
  independent exact-revision review -> merge/push/deploy/dogfood gate。

## 12. 本 plan review 的授权边界

Independent reviewer 若批准本文件，只授权：

- 生成 P0 bootstrap；
- P0/P1/P2 按各自 hard gate 逐包实现与 inert validation。

它不自动授权 P3 production activation。P3 必须在所有 implementation/deploy close 后由
fresh exact-revision operator bootstrap + independent live preflight review单独批准。

P9_3C1_DETAILED_PLAN_READY_FOR_INDEPENDENT_REVIEW_PRODUCTION_BLOCKED
