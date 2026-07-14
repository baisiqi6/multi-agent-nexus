# P9-3C0 Fixture Implementation Plan

**本文件仅为待审核计划，不授权任何实现或生产操作。** 在独立 exact-revision 评审通过前，不得进行编码、配置变更、测试、部署、服务重启、job/lease 创建或 provider 调用。

## 背景

`p9-3c0-fixture-measurement.md` 已确认 Coordinate/MultiNexus 当前未暴露安全的 zero-paid-provider fixture：

- `multinexus/adapters/factory.py` 没有 no-op/fixture adapter。
- `src/coordinate/executor_capacity.py::sync_capacity_catalog` 对每个 source 要求 global-complete-coverage，使独立 fixture capacity source 无法创建。
- 普通 `coordinate job create` 缺少 typed managed claim 所需的 executor binding snapshot；strict typed managed claim 会拒绝。
- Operator 精确 stop/status handle 需要 systemd transient unit helper/runbook。
- fixture executable 必须实现零输出 quiet window、接受真实 Claude CLI 参数、从 stdin 读取 contract envelope。

## 拆分实现包

本计划拆为 **3 个按仓库顺序、独立 bootstrap** 的实现包。每个包拥有自己的 worker branch、Codex result review、测试与 deploy gate；**不得给一个 worker 同时授权对 Coordinate 与 MultiNexus 的变更。**

### 包 1：Coordinate capacity-source decoupling

目标：让 fixture capacity source 与 canonical production capacity source disjoint，并通过 union coverage 共同覆盖所有 enabled typed executor binding；容量 policy 激活/清理遵循 disabled-binding staging。

#### 候选文件与 symbol 范围

| 文件 | 关注区域 |
|------|----------|
| `src/coordinate/executor_capacity.py` | `sync_capacity_catalog`、`CapacityCatalog`、`CapacityPolicy` 的 ownership/coverage 逻辑 |
| `src/coordinate/execution_cli.py` | 仅在需要保持 `capacity sync` 错误传播/输出兼容时做最小调整；现有 `capacity list/show` 已暴露 `source_id` |
| `tests/test_executor_capacity.py` | 新增 union coverage、ownership takeover、active-lease guard 用例 |
| `tests/test_execution_cli.py` | 多 source sync、空 source cleanup 用例 |

#### 变更点

1. **Union coverage**
   - `sync_capacity_catalog` 不再要求单个 source 单独覆盖所有 enabled typed bindings。
   - 计算 post-sync 所有 source 的 policy union，并检查 union 是否覆盖所有 enabled typed executor bindings。
   - 单个 source 可以包含仅部分 policy，也可以因 staging 而暂时包含 disabled bindings 的 policy。

2. **Ownership guard**
   - 使用现有 `executor_capacity_policies.source_id` 表达 ownership。
   - 后续 source 若声明已存在的 `agent_id`，sync 必须失败且零变更，报错明确指出已有 owner source。
   - source 同步自身既有 `agent_id` 不受影响。
   - **禁止新增 `owner_source_id` 列。**

3. **Unknown-id guard**
   - capacity policy 只接受已有 typed executor binding 的 `agent_id`。
   - 对 arbitrary unknown id 的 policy 拒绝并零变更。

4. **Post-sync validation**
   - 在事务内、任何写入前，用当前其他 source 的 policy 加本 source 的 proposed catalog 构造 post-sync union。
   - 如果 union 缺失 enabled typed binding，零写入并回滚，输出缺失 binding 列表。

5. **Active-lease guard**
   - 删除某个 `agent_id` 的 policy 时，检查是否存在 status=`active` 的 typed lease 引用该 policy。
   - 若存在，拒绝删除并返回零变更。

6. **Disabled-binding staging for fixture activation/cleanup**
   - **激活顺序（forward-only）**：
     1. register fixture runtime agents / runner profiles；
     2. sync fixture executor source v1，E1/E2 bindings `enabled=false`；
     3. sync fixture capacity source v1，E1/E2 policies；
     4. verify ownership + union coverage；
     5. sync fixture executor source v2，E1/E2 `enabled=true`。
   - **清理顺序（reverse）**：
     1. executor source v3 disables E1/E2；
     2. capacity source v2 is empty；
     3. executor source v4 is empty。
   - 每个版本/hash mutation 必须 forward-only、transactionally fail-closed、并受 in-flight typed jobs/active leases guard。

7. **Empty-source cleanup semantics**
   - fixture 用完后，允许 sync 一个更高版本但空的 fixture capacity catalog。
   - 成功条件：fixture executor bindings 已 disabled，且 fixture capacity policy 无 status=`active` 的 lease 引用；随后才把 executor source sync 为空。
   - 空 source 成功同步后保留 source 元数据行，但 policy 行清空。

8. **Migration compatibility**
   - 现有单 canonical source 的 CLI 行为、返回码、错误信息保持不变。
   - 对未启用 fixture source 的现有部署，零行为变化。

#### 测试

- 现有 canonical single source 保持兼容（golden test）。
- 两个 disjoint capacity source 共同覆盖所有 enabled typed executors。
- 在没有其他 source 补足 coverage 时，单个 partial source sync 因 post-sync union 缺失 enabled binding 而失败；canonical source 已覆盖 real executors 时，fixture partial source 可补充 disabled fixture policies。
- 跨 source takeover 已有 `agent_id` 失败，零变更。
- 删除被 active lease 引用的 policy 失败，零变更。
- unknown `agent_id` policy 被拒绝，零变更。
- 空高版本 fixture capacity source 在 fixture bindings 已 disabled 且无 active lease 时成功；之后 executor source 可安全清空。

### 包 2：MultiNexus zero-provider fixture

目标：在不修改 canonical Discord roster 的前提下，提供 secret-free、zero-network、zero-provider 的本地 fixture。

**本包必须在包 1 评审通过并合并后才开始；不得与包 1 并行修改。**

#### 候选文件与 symbol 范围

| 文件 | 关注区域 |
|------|----------|
| 新增 `multinexus/fixture/bin/p9-3c0-fixture.py` | fixture executable 本体 |
| 新增 `multinexus/fixture/config/agents.fixture.toml` | secret-free `[[agents]]` 模板 |
| 新增 `multinexus/fixture/config/executor.fixture.toml` | fixture executor definitions + bindings 模板 |
| 新增 `multinexus/fixture/config/capacity.fixture.toml` | fixture capacity policies 模板 |
| 新增 `multinexus/fixture/bin/p9-3c0-unit.sh` | 本地 transient unit launch helper |
| 新增 `multinexus/fixture/docs/runbook.md` | operator runbook |
| `multinexus/adapters/claude.py` | `ClaudeAdapter._build_cmd` / `_run`（不修改，仅作为契约依赖） |
| `multinexus/agentd/__main__.py` | `load_config(..., require_token=False)` 路径（不修改） |

#### 变更点

1. **Fixture executable**
   - 接受并验证真实 Claude CLI 参数（`-p --verbose --output-format stream-json --include-partial-messages` 等由 `ClaudeAdapter._build_cmd` 传递）。
   - 从 stdin 读取严格、有界的 fixture control envelope，例如 `contract_version`、`mode`、`quiet_seconds`；不支持命令行 `--mode` 标志。
   - `quiet_seconds` 必须显式提供且 P9-3C0/P9-3C1 证据值固定为 75；缺失、非整数或超出审核边界时 fail closed，不使用隐式默认值。
   - **quiet evidence window 内零 stdout/stderr、零 progress event。**
   - `quiet_seconds` 后只输出一行 `{"type":"result","result":"fixture complete"}`，退出码 0。
   - 支持 `mode` 取值：
     - `complete`：quiet 窗口结束后输出 result 并退出 0（默认验证路径）。
     - `hold`：quiet 窗口结束后继续 hold，用于 lease recovery / stale-attempt 测试，直到被外部停止。
   - 可选 bounded `spawn_descendant=true` 只用于 cgroup cleanup 证明；它不是第三种 crash mode。
   - **external crash row 必须通过停止 exact agentd transient unit 实现**，而不是让 adapter child 调用 `os._exit(1)`；后者会留下 agentd 存活并产生 failed report，无法证明 unreported lease expiry/recovery。
   - 不读取 `ANTHROPIC_API_KEY`、Discord token、任何云凭证；不建立网络连接。

2. **Secret-free agent config**
   - `agents.fixture.toml` 包含两个 `[[agents]]` 条目：
     - `id = "p9-3c-fixture-e1"`、`id = "p9-3c-fixture-e2"`。
     - `adapter = "claude"`；helper 必须把模板渲染成当前环境的绝对 `claude_bin`（本地 checkout 路径或 `/opt/multinexus/multinexus/fixture/bin/p9-3c0-fixture.py`），不得把占位符字面量交给 agentd。
     - 显式固定 `first_byte_timeout = 90`、`activity_timeout = 90`、`timeout = 240`。这些是 `AgentConfig` 的真实字段；不得使用不存在的 `total_timeout` 或依赖当前默认值。
     - `token` 字段省略或置空；`agentd` 用 `require_token=False` 启动。
   - 不加入 canonical `agents.toml`，避免影响 bridge 启动或 Discord roster。

3. **Executor authority template**
   - `executor.fixture.toml` 使用实际 parser 字段：
     - `[registry] id/version`；
     - `[[executor_definitions]] id/provider/adapter/capabilities`；
     - `[[agents]] id/executor_definition_id/runner_profile_id/enabled`。
   - 一个 definition 如 `p9-3c-local-fixture`，`provider="local-fixture"`，`adapter="claude"`，sorted capabilities，可绑定 E1/E2 两者。
   - fixture executor source `id` 独立，例如 `p9-3c0-fixture-executors`。
   - 忽略 Discord identity 字段，不需要 `discord_user_id`。

4. **Capacity authority template**
   - `capacity.fixture.toml` 使用实际 parser 字段：
     - `[capacity_registry] id/version`；
     - `[[executor_capacities]] agent_id/max_concurrent_jobs`。
   - fixture capacity source `id` 独立，例如 `p9-3c0-fixture-capacity`。
   - `max_concurrent_jobs` = 1。

5. **Transient unit operator helper**
   - `p9-3c0-unit.sh` 提供：
     - namespace 校验：unit 名前缀 `p9-3c-fixture-`。
     - exact unit identity：生成 `p9-3c-fixture-e1-<run>.service` / `p9-3c-fixture-e2-<run>.service`。
     - exclusive run lock/ledger，拒绝 unknown fixture ids。
     - global quiescence 检查：确认无真实 executor/service 受影响。
     - queue isolation 检查：确认 fixture runtime agents / queues 未与 canonical 队列重叠。
     - job/process budgets：单个 run 内最多 2 个 fixture unit、最多 N 个并发 job。
     - 启动前只读校验 `quiet_seconds=75`、`first_byte_timeout>=90`、`timeout>first_byte_timeout`，并把 `RuntimeMaxSec` 固定为 300 秒；任何值不一致即拒绝启动。
     - systemd network sandbox 是 mandatory gate；若 `IPAddressDeny=any` 与审核后的 restricted address families 不能被只读 preflight 证明支持，helper 必须拒绝启动，不降级成仅记录审计。
     - cleanup order fail-closed：先 freeze intake，再 drain jobs，再 stop unit，再验证 cgroup。

6. **Runbook**
   - 详细列出注册 runtime agent、sync executor catalog、sync capacity catalog、提交 exact request、停止 unit、cleanup 每一步的命令与预期输出。

#### 测试

- fixture executable 参数/stdin/JSONL 契约测试（pytest，无需网络）。
- 75 秒静默后仍能被 agentd renew 至少两次（approximately 30 秒与 60 秒）。
- 配置/verify 测试证明 `first_byte_timeout=90`、`activity_timeout=90`、`timeout=240`、`RuntimeMaxSec=300`，且缺失/错误 timeout 或不支持 mandatory network sandbox 时 fail closed。
- clean result、hold、cgroup cleanup、no network/provider credential access 的静态/沙箱测试。
- agent config secret-free，且不包含在 bridge 启动读取的 `agents.toml` 中。

### 包 3：local/isolated verification + closeout

目标：在本地或 sidecar 环境验证 fixture 走完整 managed execution-lease 路径，并产出 closeout 证据。

**本包必须在包 2 评审通过并合并后才开始；不得与包 2 并行修改。**

#### 场景

1. **基础 quiet renew**：
   - 启动两个 capacity-1 fixture executors。
   - 对每个 executor 提交一个 typed exact request。
   - 请求在 75 秒静默期间，agentd 至少完成两次 automatic lease renewal（approximately 30 秒与 60 秒）。
   - job 最终成功，输出 `fixture complete`。
   - 启动前 evidence ledger 记录只读 config check：`quiet_seconds=75`、`first_byte_timeout=90`、`activity_timeout=90`、`timeout=240`、`RuntimeMaxSec=300`。

2. **Queue isolation / intake freeze**：
   - 确认 fixture queue 与 canonical queue 不共享 `agent_id`。
   - 冻结 fixture intake 后，向真实 executor 的新提交不受影响。
   - fixture executor 上已排队的 job 仍按 lease 执行。

3. **Exact stop / status / cgroup cleanup**：
   - 使用 `systemctl show` 获取精确 unit status。
   - 使用 `systemctl stop` 停止其中一个 exact unit。
   - 等待 `systemctl is-active` 返回 inactive，并验证对应 cgroup 为空。
   - 确认另一个 fixture unit 与真实服务继续运行。

4. **Expiry / reap / recovery / stale-attempt**：
   - 使用 accepted lease contract 的固定 TTL 120 秒与 renew interval 30 秒；**不得“调低 lease timeout”作为证据**。
   - 停止 exact agentd transient unit、await cgroup cleanup、wait past recorded `expires_at`、在 global quiescence 下 invoke explicit global reap，然后启动一个 exact recovery unit，并带有 `--recoverable --recovery-reason ... --prior-process-stopped`。
   - stale attempt N 的检查只在 N+1 建立后使用旧的 lease/token。

5. **Zero paid-provider / network evidence**：
   - 使用最小化环境变量、显式 credential unsets、以及预检支持的 systemd network sandbox（例如 `IPAddressDeny=any` / 受限 address families）。
   - mandatory network sandbox 任一属性不受支持或未生效时，本行与整个 fixture run fail closed，不允许以 packet capture 替代。
   - packet capture 仅作为辅助证据；primary gate 是环境变量审计与 systemd network sandbox 配置。

#### 所需工具/脚本

- `scripts/p9-3c0-local-verify.sh`：一键 local/sidecar 验证。
- `scripts/p9-3c0-cleanup.sh`：验证后清理。

#### 成功标准

- 两个 fixture job 全部完成且结果为 `fixture complete`。
- agentd 日志显示至少两次 successful lease renewal。
- `systemctl show`/`is-active` 与 cgroup 检查全部通过。
- 真实 executor 流量在 fixture intake freeze 期间无中断。
- 无 provider/network 凭证访问证据。

## 部署边界与门控

### Inert deployment gate

- Coordinate 变更（包 1）按现有 `scripts/deploy-server.sh coordinate` 流程部署。
- MultiNexus fixture 资源（包 2）按 `scripts/deploy-server.sh multinexus` 部署到 `/opt/multinexus/fixture/`。
- fixture config 模板默认**不**被 `agents.toml`、executor registry、capacity registry 引用。
- fixture systemd helper 脚本默认**不**创建 transient unit。
- 部署完成后默认状态：
  - 无 `p9-3c-fixture-*` service 运行；
  - 无 fixture executor/capacity source synced；
  - 无 fixture job pending/running。
- **runtime agent / runner profile residue**：Coordinate CLI 当前没有 unregister runtime agent / runner profile 命令。在本 scope 内， uniquely namespaced dormant fixture agent/runner rows 作为 audit/config residue 保留；必须验证它们无法 claim typed work。未来 unregister 功能是独立 roadmap 项；禁止直接 SQLite 删除。因此，在已完成激活/清理的 cycle 后，**不得声称“无 fixture runtime agent registered”**；应声称 residue 处于 dormant、non-active 状态。

### P9-3C1 production activation gate

- P9-3C0 仅授权本地/isolated sidecar jobs 与 leases 以关闭 fixture 本身。
- 生产 catalog activation 与生产 concurrency/recovery matrix 属于 P9-3C1，需要独立的 exact-revision gate。
- P9-3C0 closeout 评审通过后，**不自动激活生产 fixture sources**；进入 P9-3C1 仍需单独审批，并至少执行：
  1. operator 获取 exclusive run lock，证明 global quiescence 与 scoped fixture intake freeze；
  2. 注册 fixture runtime agents / runner profiles；
  3. sync fixture executor source v1，E1/E2 `enabled=false`；
  4. sync fixture capacity source v1，E1/E2 `max_concurrent_jobs=1`；
  5. 验证 ownership/union coverage 后 sync fixture executor source v2，E1/E2 `enabled=true`；
  6. 启动 exact transient units，再通过 helper 提交 exact `--target-agent` requests；
  7. 每一步完成后运行对应只读 verifier；任一步不满足即停止，不进入下一步。
- 包 1 Coordinate 变更部署后如需 `systemctl restart coordinate`，必须确认 P9-3C1 未授权且 fixture 未激活。

## Fail-closed stop conditions

- 任一步骤若发现 canonical production executor/agent 受影响，立即停止并回滚。
- `sync_capacity_catalog` 在 union coverage 失败时必须事务回滚，禁止 partial apply。
- ownership takeover 检测失败时，禁止任何 source 变更。
- active-lease guard 触发时，禁止 policy/executor binding 删除。
- fixture unit 停止后 cgroup 非空，禁止进入下一步清理。
- 发现 fixture executable 读取 provider 凭证或建立网络连接，立即失败并移除 fixture。
- 激活/清理顺序若违反 disabled-binding staging，立即失败并回滚。

## Review gates

1. **包 1 review**：capacity-source decoupling 的设计、事务边界、ownership guard、active-lease guard、unknown-id guard、disabled-binding staging、兼容性测试通过。
2. **包 2 review**：fixture executable、config 模板、helper/runbook 完整，无 canonical roster 污染，真实 CLI 参数/stdin contract 正确。
3. **包 3 review**：local/sidecar 验证报告通过，success criteria 全部满足，fail-closed stop conditions 未被触发或已解释。
4. **整体 P9-3C0 closeout review**：所有包合并后进入独立 exact-revision 评审，评审通过后才进入 P9-3C1 production authorization。

## 不授权事项

- 本计划不授权修改 canonical `agents.toml`、Discord roster、production capacity policy、real executor binding。
- 本计划不授权在生产环境运行 fixture job/lease 或服务重启；生产激活属于 P9-3C1 的独立审批。
- 本计划不授权直接 SQLite 删除、无审计的 catalog mutation、`--allow-dirty` 部署例外。
- 本计划不授权使用 `pkill`、名称模式、猜测 PID 进行 fixture process 管理。
- 本计划不授权让单个 worker 同时修改 Coordinate 与 MultiNexus。

## 产出物 checklist（待实现）

- [ ] 包 1：Coordinate capacity-source decoupling 代码 + 单元/CLI 回归测试
- [ ] 包 1 deploy gate：inert by default，canonical 行为兼容
- [ ] 包 2：MultiNexus fixture executable + config 模板 + helper + runbook
- [ ] 包 2 deploy gate：fixture 资源 inert by default
- [ ] 包 3：local/sidecar 验证脚本与报告
- [ ] 独立 exact-revision review 通过
- [ ] P9-3C1 production 授权门控明确
