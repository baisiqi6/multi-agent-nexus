# Phase 7: N+M 运行架构总览

## 目标

把 MultiNexus 从当前的“每个平台各自启动一套 agent adapter 进程”改成：

```text
IM bridge 数量 + agent runner 数量
```

也就是从：

```text
n 个 agent * m 个 IM 平台
```

变成：

```text
n 个 agentd + m 个 IM bridge
```

例如 `mac-codex` 只应该有一个 Codex adapter/runner 进程，即使 Discord 和 KOOK 都可以触发它。

## 当前问题

现在 `multinexus` 和 `kook-nexus` 都把两件事绑在同一个常驻进程里：

- 平台连接：Discord Gateway、KOOK polling/token/rate limit
- agent 执行：Claude/Codex/Hermes/OpenCode adapter

这会导致重复进程：

```text
Discord mac-codex 进程 -> Codex adapter
KOOK mac-codex 进程    -> Codex adapter
```

如果以后继续接 Slack、Telegram 或其他 IM 平台，重复会继续扩大。

## 架构决策

拆成三个边界：

```text
Discord bridge ┐
KOOK bridge    ├── coordinate / request bus ── mac-codex agentd
future bridge  │                         ├── mac-claude agentd
               │                         └── server-hermes agentd
```

### IM Bridge

职责：

- 维护平台连接、token、Gateway/polling、rate limit。
- 解析平台消息和 mention。
- 把消息转换成标准 `AgentRequest`。
- 把请求交给 `coordinate`。
- 把结果发回原始 Discord/KOOK 频道。
- 不直接调用 Claude/Codex/Hermes/OpenCode adapter。

### Agent Runner / Agentd

职责：

- 每个 agent identity 只有一个 runner，例如 `mac-codex`。
- 持有具体 adapter 和 CLI session/resume 状态。
- 执行 timeout、并发、取消、健康检查策略。
- 从 `coordinate` 领取任务。
- 把结构化结果回传给 `coordinate`。

### Coordinate

从 MultiNexus 角度看，coordinate 负责：

- 接收 bridge 标准请求。
- 路由任务到目标 agentd。
- 保存 canonical runtime state：jobs、events、deliveries、agent 在线状态。
- 把 agent 结果投递回正确的 IM 平台目标。

coordinate 不应该拥有 Claude/Codex adapter 逻辑；MultiNexus bridge 也不应该拥有 durable workflow 状态。

## 阶段拆分

### Phase 7.1: 单机 N+M 运行架构

先全部跑在 Mac 上，但使用未来跨主机也一样的边界：

```text
Mac:
  coordinate
  discord-bridge
  kook-bridge
  mac-codex agentd
  mac-claude agentd
```

详细计划：

```text
docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/plan.md
```

核心验收：

- Discord 和 KOOK 都能触发同一个 agent identity。
- 同一个 agent 只有一个 adapter/agentd 进程。
- bridge 不直接调用 adapter。
- 请求路径统一为 `bridge -> coordinate -> agentd`。

### Phase 7.2: 多主机 agent runtime

保持 bridge/coordinator 放置位置和 agent 放置位置解耦：

```text
Mac:
  coordinate
  discord-bridge
  kook-bridge
  mac-codex agentd
  mac-claude agentd

Windows:
  win-claude agentd
  win-opencode agentd

Linux:
  server-hermes agentd
```

后续也可以把 coordinate 和 bridges 迁到服务器：

```text
Server:
  coordinate
  discord-bridge
  kook-bridge

Mac / Windows / Linux:
  agentd processes
```

详细计划：

```text
docs/project-harness/tasks/phase-7.2-multi-host-agent-runtime/plan.md
```

核心验收：

- 远程 agentd 能通过 `COORDINATE_URL` 领取并完成任务。
- Discord/KOOK 请求都可以路由到非本机 agentd。
- 迁移 coordinate 到服务器时，客户端只改配置，不改业务逻辑。

## 非目标

- 不把所有 IM bridge 强行合成一个大进程。
- 不运行多个独立 coordinate 数据库。
- 不把 Claude/Codex/Hermes/OpenCode adapter 迁入 coordinate。
- Phase 7.1 不要求 PostgreSQL。
- 单 active bridge 和单 active coordinate 未稳定前，不做高可用。

## Coordinate 依赖

Phase 7 需要 coordinate 提供：

- request ingest
- agent register / heartbeat
- job claim
- result report
- delivery routing
- 简单认证

对应计划在 coordinate 项目：

```text
docs/tasks/phase-7-service-control-plane/plan.md
```

## Dogfood 路径

继续用 Discord 做可见协作入口：

```text
Discord 讨论 -> coordinate task -> agent 实现分支 -> PR/review -> coordinate closeout
```

早期可以继续借用现有 Discord bot 执行任务，但每个完成切片都应该让系统更接近：

```text
bridge -> coordinate -> agentd
```
