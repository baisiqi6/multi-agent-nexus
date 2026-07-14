# P9-3C0 Fixture Plan Review — Round 3

Reviewer: Claude independent exact-revision reviewer (sonnet)  
Verdict: **APPROVED_FOR_P9_3C0_COORDINATE_BOOTSTRAP_ONLY**

Reviewed measurement SHA-256:
`bd52cf986283d190cb5bc80434102172b46d09eb14324c492ddfb8cc01b6d4ab`

Reviewed plan SHA-256:
`f57f01e739f742df75c553a9507fbbda722fd618e1a114956bfc072a91eb8829`

## Scope

仅读取以下五个文件：

- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-assessment-bootstrap.md`
- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-measurement.md`
- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-plan.md`
- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-plan-review-round1.md`
- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-plan-review-round2.md`

仅创建本 review 文件。未执行 Bash/ls/rg、subagent、TaskCreate、测试、provider、git、deploy、SSH、DB、service、job 或 lease 操作。

## Round 2 P1 复核

| Round 2 P1 要求 | 当前 plan 状态 | 位置 |
|---|---|---|
| `first_byte_timeout=90` | 已显式固定 | `agents.fixture.toml` 条目（包 2 Secret-free agent config） |
| `activity_timeout=90` | 已显式固定 | 同上 |
| `timeout=240` | 已显式固定 | 同上；未使用不存在的 `total_timeout` |
| `quiet_seconds=75` 必填且无默认 | 已要求；缺失/非整数/越界 fail closed | 包 2 Fixture executable |
| `RuntimeMaxSec=300` | 已固定为 300 秒 | 包 2 Transient unit operator helper |
| mandatory network sandbox 不支持即 fail closed | 已要求；不能以审计记录替代 | 同上 |

结论：Round 2 的唯一 P1 已修正。

## 整体 Round 1 要求复核

| Round 1 主题 | 复核结果 |
|---|---|
| 真实文件/符号/schema/CLI 语义 | 使用 `src/coordinate/executor_capacity.py`、`execution_cli.py` 及现有测试文件；不新增 `owner_source_id` |
| Union coverage / ownership / unknown-id / active-lease | 包 1 完整定义；保留 `source_id` ownership、unknown id 拒绝、active lease 删除保护 |
| Disabled-binding staging | forward v1→v2 与 reverse v3→v4 顺序正确；cleanup 先 disable binding 再空 capacity |
| 75 秒 zero-output/zero-progress quiet row | fixture executable 静默期内零 stdout/stderr/JSONL；仅输出 `{"type":"result","result":"fixture complete"}` |
| Claude 真实 CLI 参数 + stdin envelope | 不接受自定义 `--mode`；从 stdin 读取 `contract_version`/`mode`/`quiet_seconds` |
| Exact systemd unit / cgroup handle | `p9-3c-fixture-e1/e2-<run>.service`；`systemctl show`/`stop`/`is-active`；验证 cgroup 为空；不用 `pkill` |
| Scoped queue isolation / intake freeze | fixture `agent_id` 不在 canonical roster；helper 使用 exclusive run lock/ledger 并拒绝 unknown ids |
| 三个 sequential bootstraps | 包 1（Coordinate）→ 包 2（MultiNexus fixture）→ 包 3（local/sidecar 验证） |
| Inert deployment | 默认无 fixture unit/source/job；模板不污染 canonical `agents.toml`/registry |
| P9-3C1 production 边界 | P9-3C0 仅授权本地/isolated sidecar；生产激活为独立 P9-3C1 exact-revision gate |
| Dormant residue 边界 | 明确接受 uniquely namespaced dormant runtime agent/runner rows 作为 audit residue；禁止声称“无 fixture runtime agent registered” |

未发现 P0/P1。

## Findings

- P0：无。
- P1：无。
- P2（后续 bootstrap preflight，未执行、不阻塞）：
  - 包 3 验证脚本应增加对 `agents.fixture.toml` 中 `first_byte_timeout`/`activity_timeout`/`timeout` 的只读校验，确保与 `quiet_seconds=75` 一致。
  - runbook 应记录 `RuntimeMaxSec=300` 与 `timeout=240`/`lease_ttl=120` 的推导关系，方便 operator 复查。
  - 网络 sandbox preflight 失败路径应写入 evidence ledger，便于 closeout 审计。

## Authorization boundary

本 verdict 仅授权生成并评审**第一个 Coordinate implementation bootstrap**（包 1：capacity-source decoupling）。

不授权：

- 任何编码、测试、配置变更；
- 部署、服务重启、job/lease 创建；
- provider 调用或生产 fixture 激活；
- 包 2/3 的启动或并行修改；
- P9-3C1 生产 catalog 激活。

包 1 完成后须通过独立的 exact-revision review，方可进入包 2。
