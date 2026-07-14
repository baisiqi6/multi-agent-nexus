# P9-3C0 Fixture Assessment Measurement

评估模式：只读规划/测量；未执行任何代码、配置、测试、服务、部署或生产变更。  
结论：`implementation_plan_required`。

## 固定 revision

- Worktree: `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c0-assessment`
- Branch: `agents/mac-claude/p9-3c0-fixture-assessment`
- Base: `8f1acf9a185ff93a29769e3f1d1e5b28777cb114`
- 事实源：
  - `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-assessment-kimi-round2/facts.md`
  - `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-assessment-bootstrap.md`
  - `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/plan-approval.md`

## 逐项 gate 回答

### Gate 1：quiet long-running execution with no provider output

- **当前状态：不可直接实现，需实现本地 fixture executable 并复用 Claude adapter。**
- `multinexus/adapters/factory.py` 暴露的 adapter 只有 `claude`、`codex`、`hermes`、`jarvis`、`jarvis-local`、`omp`、`opencode`，没有 no-op/fixture adapter。
- `multinexus/adapters/claude.py::ClaudeAdapter._build_cmd` 调用可配置的 `claude_bin`，标准参数为 `-p --verbose --output-format stream-json --include-partial-messages`。
- 复用 `adapter="claude"` 但把 `claude_bin` 指向一个经审阅的本地可执行文件，即可满足“无付费 provider 输出”的要求。
- **该 fixture executable 必须接受并验证上述真实 Claude CLI 参数，从 stdin 读取严格、有界的 fixture control envelope（如 `contract_version`、`mode`、`quiet_seconds`），不通过命令行追加自定义 `--mode` 标志。**
- **quiet evidence window 内必须零 stdout/stderr 输出、零 progress event。** 在 75 秒静默期内不得发出任何 JSONL 行（包括 `system/init`）；`ClaudeAdapter` 若收到 early `system/init` 会切换为 `activity_timeout` 并产生 progress，破坏 quiet row。
- 75 秒后只输出一行 `{"type":"result","result":"fixture complete"}`，退出码 0。
- 75 秒来自当前 30 秒 renew interval，用于证明 approximately 30 秒与 60 秒两次 successful lease renewal。
- Fixture agent config 必须显式固定真实 `AgentConfig` 字段 `first_byte_timeout=90`、`activity_timeout=90`、`timeout=240`；不得依赖当前默认值。`quiet_seconds=75` 是 control envelope 必填字段且无隐式默认值，helper 必须验证 `first_byte_timeout >= quiet_seconds + 15` 且 `timeout > first_byte_timeout`。
- fixture executable 不读取 `ANTHROPIC_API_KEY`、Discord token、任何云凭证；不建立网络连接。
- 因此 gate 1 不依赖新增 adapter kind，但**必须实现并测试该本地 fixture executable**；当前不存在。

### Gate 2：strict typed context/binding/routing/worktree lease

- **正确入口：`coordinate runtime request submit --target-agent`。**
- `coordinate/runtime.py::_submit_exact_request` 会解析并存储严格的 `execution_context`、`executor_binding`、route、runner profile、resource/worktree authority。
- 普通 `coordinate job create` **不足**：它不会添加 typed managed claim 所需的 executor binding snapshot；`coordinate/runtime_lease.py::_validate_claim_authority` 会拒绝没有该 snapshot 的 typed managed claim。
- `coordinate job run` 的 generic subprocess runner 是另一条路径，**不会经过** `AgentdWorker._renewal_supervisor`、managed execution-lease envelope、adapter-owned process group cleanup、agentd recovery/cancellation。
- 因此 fixture job 必须走 `coordinate runtime request submit --target-agent` 这一严格入口。

### Gate 3：two distinct capacity-1 executor instances

- **当前 Coordinate capacity-source 设计无法干净地容纳独立的 fixture capacity source。**
- 实际文件为 `src/coordinate/executor_capacity.py::sync_capacity_catalog` 与 `src/coordinate/execution_cli.py`，测试文件为 `tests/test_executor_capacity.py` 与 `tests/test_execution_cli.py`。
- `sync_capacity_catalog` 当前把**每个** capacity catalog 单独与**全局**所有已启用 typed executor binding 做对比，要求 complete coverage 且不能有多余 policy。
- 现有 `executor_capacity_policies.source_id` 已经表达 ownership；**不要**在没有证据的情况下新增 `owner_source_id` 列。
- 一个仅包含 E1/E2 的 fixture-only capacity source 会报“capacity missing for enabled typed agents”；一个包含 real+fixture 的第二个 source 又会与现有 real policy 行冲突。
- **核心耦合缺口：capacity coverage 的 global-complete-coverage 语义把 fixture source 与 canonical production source 强制耦合在一起。**
- 修复后应支持 union coverage：post-sync 所有 source 的 policy union 覆盖所有 enabled typed executor bindings；单个 source 可以只包含部分 policy。
- **激活必须采用 forward-only staging**，通过现有 executor binding 的 `enabled` 字段：
  1. register fixture runtime agents / runner profiles；
  2. sync fixture executor source v1，E1/E2 bindings `enabled=false`；
  3. sync fixture capacity source v1，E1/E2 policies；允许为已存在的 disabled typed binding 创建 policy，但拒绝没有 typed binding 的 arbitrary unknown policy id；
  4. 验证 ownership / union coverage；
  5. sync fixture executor source v2，E1/E2 `enabled=true`。
- Cleanup 必须反向执行：
  1. executor source v3 disables E1/E2；
  2. capacity source v2 is empty；
  3. executor source v4 is empty。
- 在修复该耦合之前，无法创建两个独立的 capacity-1 fixture executor 实例而不削弱 canonical production catalog 或改动真实 executor capacity。

### Gate 4：exact child process handle/status/stop with awaited tree cleanup

- **需要 systemd transient unit 作为 Operator-visible exact handle。**
- `multinexus/adapters/utils.py::terminate_owned_process_group` 是 adapter 内部清理原语，**不是** Operator 可见的精确 status/stop handle。
- 生产探针确认 `kook-hermes-admin` 有 `/usr/bin/systemd-run` 与 systemd 255；现有服务均使用 `KillMode=control-group`。
- fixture agentd 应以唯一命名 transient unit 启动，例如 `p9-3c-fixture-e1-<run>.service` / `p9-3c-fixture-e2-<run>.service`，配置 `KillMode=control-group`、受界 `RuntimeMaxSec`、显式 user/group/workdir、fixture-only config、最小化环境变量与显式 credential unsets。
- 精确 status handle：`systemctl show <exact-unit> -p Id -p ActiveState -p SubState -p MainPID -p ControlGroup -p Result`。
- 终止验证：`systemctl stop <exact-unit>` 后等待 `systemctl is-active`/`systemctl show` 返回 inactive，并确认 cgroup 为空或不存在。不得使用 `pkill`、名称模式或猜测 PID。
- adapter 通过 `start_new_session` 创建独立 process group，但仍位于 systemd unit cgroup 内，`KillMode=control-group` 会覆盖 agentd、fixture executable 及其 descendants。

### Gate 5：scoped queue isolation and intake freeze for the fixture executors

- **fixture executor 需要独立 queue，且提交必须可被冻结。**
- `coordinate runtime job claim` 按 `agent_id` 选择，而不是按 job id。每个 fixture executor 因此需要独立的 `agent_id`。
- fixture `agent_id` 不在 canonical Discord roster / routed catalog 中，请求只通过 operator helper 的 exact `--target-agent` 路径进入 fixture queue。
- operator helper 必须使用 exclusive run lock/ledger，拒绝 unknown fixture ids，从而保证 intake freeze 只需停止向对应 fixture `agent_id` 提交新请求即可，不影响真实 executor 和用户流量。
- 两个 capacity-1 fixture executor 实例意味着两个独立的 `agent_id`、两个独立的 queue、两个独立的 runner profile。
- 该 gate 在 capacity-source decoupling 修复后才能安全实现。

## 是否必须代码变更

**是。** 最小且必须变更在 Coordinate 侧：

- `src/coordinate/executor_capacity.py::sync_capacity_catalog` 需要支持多 capacity source 的 union coverage，而非针对每个 source 的 global-complete-coverage。
- 使用现有 `executor_capacity_policies.source_id` 表达 ownership；禁止一个 source 接管另一个 source 已拥有的 `agent_id`。
- 在写入前构造 proposed post-sync union 并评估全局 coverage，保留 active-lease 删除保护；fixture binding 已 disabled 且无 active lease 后，允许空的高版本 fixture capacity source 成功同步。
- 容量 policy 只接受已有 typed binding 的 agent id，拒绝 arbitrary unknown id。
- canonical single-source 行为必须保持字节/CLI 兼容。

在 MultiNexus 侧，需要实现本地 fixture executable、secret-free 配置模板、独立 executor/capacity 权威文件、systemd transient unit 操作 helper/runbook。这些不修改 canonical Discord roster 或 production adapter。

## implementation plan 触发原因

- 当前不存在 zero-provider fixture adapter 或 fixture executable。
- 当前 Coordinate capacity-source 的全局 complete coverage 语义阻止了独立 fixture capacity source 的创建。
- 容量 policy 激活/清理顺序、unknown-id 拒绝、active-lease guard 需要在 `src/coordinate/executor_capacity.py` 中显式实现。
- 精确的 process handle 需要通过 systemd transient unit 引入新的操作 helper/runbook。
- fixture executable 必须实现零输出 quiet window、真实 Claude CLI 参数兼容、stdin contract envelope，并由 agent config 显式提供覆盖静默窗口的 `first_byte_timeout`/`activity_timeout`/`timeout`。
- 因此无法声明 `existing_fixture_verified`；必须进入实现计划评审阶段。
