> **Historical overview.** This document describes an earlier three-layer model in
> which Coordinate was presented as the coordinator and MultiNexus as only a message
> layer. Current authority: [`project-harness/product-definition.md`](project-harness/product-definition.md),
> [`project-harness/scope.md`](project-harness/scope.md), and
> [`project-harness/architecture.md`](project-harness/architecture.md).

# Multi-Agent Harness 工程体系（历史）

## 一句话概括

三层架构：**Harness（工程状态）→ Coordinator（编排控制面）→ MultiNexus（消息投递层）**，让多个 AI coding agent 在真实的软件工程项目中协作完成开发任务。

## 三层架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                     MultiNexus（消息投递层）                      │
│  Discord / KOOK 频道内的多 agent 通信、handoff、上下文管理           │
│  每个 agent = 一个独立进程 + 一个 bot 身份                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Discord / KOOK 消息
                            │ [handoff] @AgentName 任务描述
┌───────────────────────────▼─────────────────────────────────────┐
│                   Coordinator（编排控制面）                       │
│  SQLite 本地控制面：任务分配、状态流转、策略路由、delivery 投递         │
│  不嵌入任何 agent SDK——agent 以 subprocess 适配器接入               │
│   把多 agent 工程协作的状态机、事件日志、任务分配、delivery、          │
│   PR/CI/review gate 包成一个可恢复、可审计的控制面                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ harnessctl 调用
┌───────────────────────────▼─────────────────────────────────────┐
│              Harness协议 + HarnessCLI（工程状态层）                │
│  文件持久化的工程状态：checklist、event log、分支、PR、CI             │
│  harnessctl 是唯一合法的状态变更入口                                │
└─────────────────────────────────────────────────────────────────┘
```
/
## 各层职责

### 1. Harness + HarnessCLI — 工程状态层

**是什么：** 文件系统上的一组 JSON 文件，记录一个长期工程项目的完整状态。

**核心文件：**
- `mvp-checklist.json` — 任务清单（任务 ID、描述、负责人、状态）
- `events.jsonl` — 不可变事件日志（每次状态变更追加一行）
- `harness-state.json` — 当前快照

**HarnessCLI（harnessctl）：**
- 唯一合法的状态变更工具
- 提供 `assign`、`accept`、`handoff`、`blocker`、`unblock`、`closeout`、`mark-done` 等操作
- 每次调用都追加事件到 `events.jsonl`
- Coordinator 层通过 `HarnessAdapter` 封装调用，永远不直接写 harness 文件

**设计原则：** 状态是文件，可以用 git 追踪，可以人肉审查，可以在断电后恢复。

### 2. Coordinator — 编排控制面

**是什么：** SQLite 驱动的本地控制面，管理任务从分配到完成的完整生命周期。

**核心数据流：**

```
CLI / API 调用
    │
    ▼
Service 层（assignments.py, transitions.py）
    │  调用 harnessctl 执行状态变更
    │  写入事件到 SQLite
    ▼
Policy 层（policy.py）
    │  判断哪些事件需要对外可见
    │  渲染为带标签的消息（[ASSIGN]、[BLOCKER]、[DONE] 等）
    ▼
Delivery 层（bus.py）
    │  写入 outbox 表
    ▼
Bus 适配器
    ├── StdoutBus   → 本地测试（打印 JSON）
    ├── DiscordBus  → Discord 频道消息
    └── KookBus     → KOOK 房间消息
```

**任务生命周期：**

```
request → accept → (handoff → accept)* → [blocker → unblock]* → closeout → mark-done
```

**关键设计：**
- **事件是不可变事实**：每次操作产生事件，事件不修改、不删除
- **策略决定可见性**：只有白名单内的 20 种事件类型会生成对外消息
- **Delivery 是 outbox 模式**：发送失败不影响事件本身，delivery 可以重试
- **Bus 是无状态发送器**：只负责把消息投递到平台，不存储状态

**支持的 bus 平台：**
| 平台 | 适配器 | 用途 |
|------|--------|------|
| stdout | StdoutBus | 本地 dry-run 和测试 |
| discord | DiscordBus | 投递到 Discord 频道 |
| kook | KookBus | 投递到 KOOK 房间 |

### 3. MultiNexus — 消息投递层

**是什么：** 多 agent 的 Discord/KOOK 通信层，每个 coding agent 一个独立 bot 进程。

**架构：**

```
每台机器：
  进程1 (multinexus.py --agent mac-claude)     → Discord bot "Mac Claude"
  进程2 (multinexus.py --agent mac-codex)      → Discord bot "Mac Codex"
  进程3 (multinexus.py --agent mac-opencode)   → Discord bot "Mac OpenCode"
  ...

外部 agent（原生 Gateway，不受 MultiNexus 管理）：
  小龙虾/OpenClaw  → 自己的 Discord bot 连接
  Hermes          → 自己的 Discord bot 连接
```

**两种 agent 类型：**

| 类型 | 代表 | Discord 连接 | MultiNexus 管理 |
|------|------|-------------|----------------|
| Managed Coding Agent | Claude、Codex、OpenCode | MultiNexus 启动 adapter 进程 | 启动、上下文、handoff |
| External Gateway Agent | 小龙虾、Hermes | 自带原生 Gateway | 只做 handoff 路由 |

**Adapter 模式：**
每个 managed agent 有一个 adapter，包装对应的 CLI 工具为子进程：

| Adapter | CLI 命令 | 输入方式 |
|---------|---------|---------|
| ClaudeAdapter | `claude -p --output-format stream-json` | stdin |
| CodexAdapter | `codex exec --json -` | stdin |
| OpenCodeAdapter | `opencode run --format json` | stdin |

**Handoff 协议：**
- Agent 输出 `[handoff] @AgentName 任务描述`
- 系统自动解析 `@AgentName` 为 Discord mention
- 目标 agent 收到 Discord 消息后开始处理
- 所有跨 agent 交接通过 Discord 频道可见、可追溯

**上下文管理：**
- SQLite WAL 模式存储频道历史
- 每次请求注入最近 N 条消息（可配置）
- Adapter 错误不入上下文，避免污染历史

## 三层如何协作：一个完整任务流程

以"让 Codex 实现 feature-X，然后 Claude review"为例：

```
1. 用户在 Discord 频道说：
   @Mac Codex 请实现 feature-X

2. MultiNexus (Codex bot) 收到消息：
   - 构建 prompt（系统提示词 + 频道上下文 + 当前消息）
   - 启动 codex exec 子进程
   - Codex 完成实现

3. Coordinator 层（可选）：
   - 用户通过 coordinator CLI 分配任务
   - coordinator 调用 harnessctl assign 记录状态
   - coordinator 通过 DiscordBus 投递分配消息到频道
   - MultiNexus 将消息路由到对应 agent

4. Codex 输出 handoff：
   [handoff] @Claude 请 review feature-X 的实现

5. MultiNexus 解析 handoff：
   - @Claude → <@Claude的UID>
   - Claude bot 收到 Discord 消息
   - Claude 开始 review

6. Claude 完成后，coordinator 可记录 closeout：
   - harnessctl closeout task-id
   - 事件追加到 events.jsonl
   - 可见的 [DONE] 消息投递到频道
```

## 部署矩阵（当前）

| 机器 | Agent | 类型 | 状态 |
|------|-------|------|------|
| Mac | Claude | Managed (MultiNexus) | ✅ 运行中 |
| Mac | Codex | Managed (MultiNexus) | ✅ 运行中 |
| Mac | OpenCode | Managed (MultiNexus) | ✅ 运行中 |
| Mac | 小龙虾/OpenClaw | External Gateway | ✅ 运行中 |
| 云服务器 | Hermes | External Gateway | ✅ 运行中 |
| Windows | Claude | Managed (计划中) | Phase 4 |
| Windows | OpenCode | Managed (计划中) | Phase 4 |
| Windows | OpenClaw | Managed (计划中) | Phase 4 |

## 关键设计决策

1. **文件优先**：Harness 状态是 JSON 文件，可 git 追踪、可审查、可恢复
2. **SQLite 控制面**：Coordinator 用 SQLite 而非远程服务，零运维成本
3. **Outbox 模式**：Delivery 失败可重试，不影响事件源
4. **频道即总线**：所有 agent 间通信走 Discord/KOOK 频道，天然可追溯
5. **Adapter 解耦**：Agent 只需要是一个 CLI 工具，不需要 SDK 集成
6. **混合架构**：coding agent 由 MultiNexus 管理，personal assistant 保留原生 Gateway
