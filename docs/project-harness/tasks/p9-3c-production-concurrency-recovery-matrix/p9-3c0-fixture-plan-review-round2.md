# P9-3C0 Fixture Plan Review — Round 2

Reviewer: Claude independent exact-revision reviewer (sonnet)  
Verdict: **CHANGES_REQUESTED**  
Reviewed measurement SHA-256:
`94ecddd14f225e0ca7911aae57de1a01ee02e7e95152d9b74b7a8d3c29eba052`  
Reviewed plan SHA-256:
`f0189ac372e8eda55f665ae44dbd93a1ca885d87d050f03f9d394c98522cb154`

## Scope

仅读取以下四个文件：

- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-assessment-bootstrap.md`
- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-measurement.md`
- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-plan.md`
- `docs/project-harness/tasks/p9-3c-production-concurrency-recovery-matrix/p9-3c0-fixture-plan-review-round1.md`

仅创建本 review 文件。未执行 Bash/ls/rg、subagent、TaskCreate、测试、provider、git、deploy、SSH、DB、service、job 或 lease 操作。

## 总体评价

`implementation_plan_required` 结论由五个 assessment gate 支撑；包 1/2/3 的仓库顺序、inert deployment、P9-3C1 边界、Coordinate multi-source capacity union、现有 `source_id` ownership guard、unknown-id guard、active-lease guard、disabled-binding staging、75 秒 zero-output/zeroprogress quiet row、Claude fixed args + stdin envelope、systemd exact unit/cgroup handle、scoped queue isolation、network sandbox 以及 dormant residue 处理，均与 measurement 和 Round 1 要求一致。

但存在一个 P1 遗漏，使计划尚不足以生成第一个 Coordinate implementation bootstrap。

## 阻断性发现（P1）

### P1-1 — 未配置 fixture agent 超时以覆盖 75 秒静默窗口

位置：`p9-3c0-fixture-plan.md` 包 2 → **Fixture executable** 段，原文：

> "quiet evidence window 内零 stdout/stderr、零 progress event。"  
> "`quiet_seconds` 后只输出一行 `{"type":"result","result":"fixture complete"}`，退出码 0。"

问题：Round 1 P1-3 明确要求 **"Set total and first-byte timeouts above the bounded quiet duration"**。本版计划仍只约束 fixture executable 在 75 秒内不输出，却未在 `agents.fixture.toml` 或对应 runner profile 中将 `first_byte_timeout` / `total_timeout` 设置为大于 `quiet_seconds`（建议至少 `quiet_seconds + 15s`，即 > 90 秒）。若沿用默认超时，75 秒静默期内 `ClaudeAdapter` 可能提前触发 `first_byte_timeout`，导致 quiet row 被错误中断，gate 1 失败。

必须修正：

1. 在 `agents.fixture.toml` 或 runner profile 中显式设置 `first_byte_timeout` 与 `total_timeout`。
2. 在 fixture executable stdin contract 与 runbook 中说明：超时值必须 ≥ `quiet_seconds` + 余量。
3. 在包 3 验证脚本中增加对 adapter timeout 配置的只读校验。

## 非阻断性记录（P2）

### P2-1 — `quiet_seconds` 默认值未明确

建议 fixture executable 默认 `quiet_seconds = 75`，与验证场景一致，避免 helper 遗漏该字段时测试过短。

### P2-2 — transient unit `RuntimeMaxSec` 建议值未给出

建议在 runbook 中给出 `RuntimeMaxSec` 计算式，例如 `quiet_seconds + max(lease_ttl, cleanup_margin)`，确保 unit 不会先于预期 cleanup 被 systemd 杀掉。

### P2-3 — network sandbox 不支持时的 fallback 未明确

若 preflight 发现 systemd 版本不支持 `IPAddressDeny=any`，helper 是拒绝启动还是仅记录审计？建议在 runbook 中说明。

## Authorization boundary

本 review 仅授权文档修正；不授权编码、测试、配置变更、部署、服务重启、job/lease 创建、provider 调用或生产 fixture 激活。修正后须再次通过独立 exact-revision review，方可进入包 1 `APPROVED_FOR_P9_3C0_COORDINATE_BOOTSTRAP_ONLY`。

## Codex reviewer clarification

The finding correctly requires explicit timeout evidence, but the real config field is
`AgentConfig.timeout`, not `total_timeout`; timeout values are not runner-profile
fields. The current defaults (`first_byte_timeout=120`, `timeout=360`) already exceed
75 seconds, so the risk is reliance on drift-prone defaults rather than an immediate
failure at the current revision. The corrected exact revision must use
`first_byte_timeout=90`, `activity_timeout=90`, `timeout=240`, require
`quiet_seconds=75`, and fail closed if the mandatory network sandbox is unsupported.
