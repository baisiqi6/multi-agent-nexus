# Phase 7.1: 单机 N+M 运行架构

## 目标

先在 Mac 单机上跑通新的运行边界：

```text
Mac:
  coordinate
  discord-bridge
  kook-bridge
  mac-codex agentd
  mac-claude agentd
```

核心目标不是跨主机，而是先证明：

```text
多个 IM bridge 可以共享同一个 agentd
```

同一个 agent identity 不能因为 Discord 和 KOOK 同时接入而启动两份 adapter。

## 当前问题

当前形态接近：

```text
Discord mac-codex 进程 -> Codex adapter
KOOK mac-codex 进程    -> Codex adapter
```

这会导致同一个 agent 的 session、timeout、日志、进程监督和故障恢复分裂。

## 目标形态

```text
Discord bridge ┐
KOOK bridge    ├── coordinate ── mac-codex agentd
               │             └── mac-claude agentd
```

## 范围

### 1. KOOK 合入 MultiNexus

- 把 `kook-nexus` 的 KOOK runtime 迁入 `multinexus`。
- 保留 KOOK polling fallback。
- 保留 KOOK mention/role 清洗。
- 保留 transient bot message 过滤。
- 保留 `[handoff]` 触发边界和 dedupe 逻辑。

### 2. 定义平台无关请求协议

新增或整理标准结构：

```text
AgentRequest
AgentResponse
PlatformOrigin
PlatformDestination
```

至少包含：

- platform: `discord` / `kook`
- source channel/thread/message id
- requested agent id
- normalized prompt
- author id/name
- reply target
- session scope hint

### 3. Discord 改成 bridge

- Discord bridge 继续负责 Gateway、slash command、mention 解析和发消息。
- Discord bridge 不再直接调用 `make_adapter()`。
- Discord bridge 把请求交给 coordinate。

### 4. KOOK 改成 bridge

- KOOK bridge 继续负责 token、polling、quote reply、mention 渲染。
- KOOK bridge 不再直接调用 `make_adapter()`。
- KOOK bridge 把请求交给 coordinate。

### 5. 新增本地 agentd

- agentd 使用现有 `multinexus/adapters`。
- 每个 agentd 只负责一个 agent identity。
- agentd 管理 adapter call/resume、timeout、health check、progress callback。
- agentd 从 coordinate 领取任务并回传结果。

### 6. 单机 dogfood

即使所有进程都跑在 Mac 上，也必须走：

```text
bridge -> coordinate -> agentd
```

不能为了本地调试让 bridge 直接调用 adapter。

## 非目标

- 不做跨主机 agentd。
- 不迁移 coordinate 到服务器。
- 不做 PostgreSQL。
- 不做 bridge 高可用。
- 不把 Discord 和 KOOK bridge 合成一个进程。

## 验收标准

- Discord 可以触发 `mac-codex`。
- KOOK 可以触发同一个 `mac-codex`。
- 系统中只有一个 `mac-codex` adapter/agentd 进程。
- 系统中只有一个 `mac-claude` adapter/agentd 进程。
- Discord/KOOK bridge 代码不直接调用 `make_adapter()`。
- agent 回复能回到原始 Discord 或 KOOK 频道。
- 现有 task-scoped session 行为保留，或有等价的新测试覆盖。

## 建议实现顺序

1. 梳理并冻结现有 Discord/KOOK 行为测试。
2. 定义标准 request/response envelope。
3. 把 KOOK runtime 迁入 `multinexus`，先保持原行为。
4. 抽出本地 agentd，复用现有 adapter。
5. 让 Discord bridge 通过 coordinate 提交请求。
6. 让 KOOK bridge 通过 coordinate 提交请求。
7. 验证 Discord 和 KOOK 触发同一个 agentd。
8. 更新 runbook、agents 配置示例和 launchd/systemd 示例。

## 依赖

coordinate 需要先提供或并行提供：

- request ingest
- local job creation
- agentd job claim
- result report
- delivery routing

如果 coordinate API 尚未完成，本阶段可以先用等价 CLI/daemon shim，但语义必须和未来 API 一致。

## 风险

- KOOK polling 和 Discord Gateway 的消息去重语义不同。
- 原有 Discord task-scoped session 逻辑不能在拆 bridge 时丢失。
- bridge 到 coordinate 的临时 shim 如果设计太随意，后续会二次重构。
- 单机调试时容易偷懒绕过 coordinate，必须避免。
