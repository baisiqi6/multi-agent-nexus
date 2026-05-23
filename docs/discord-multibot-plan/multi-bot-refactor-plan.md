# Discord-Nexus 多 Bot 架构重构计划

## 背景

当前 discord-nexus 是**单 bot + webhook**架构：一个 Discord bot 监听所有消息，通过 webhook 模拟多个 agent 身份发言。问题：

- Agent 无法被 @mention（webhook 不是真实用户）
- Agent 间 handoff 走内部路由而非 Discord 原生消息
- 用户无法在输入 @ 后自动补全选择 agent

kook-nexus 已跑通**一进程一 agent**架构（8+ agent 跨 3 台机器），是经过验证的参考实现。

用户决定重心转移到 Discord（Discord 有原生 slash 命令、embeds、threads 等 KOOK 没有的能力）。

## 目标

建立**混合架构**的多 agent Discord 协作系统：

- **Coding agents**（Claude、Codex、OpenCode）：由 discord-nexus 托管，一进程一 bot
- **External gateway agents**（小龙虾/OpenClaw、Hermes）：保留原生 Gateway，不由 discord-nexus 管理
- Discord 作为统一协作界面和 handoff 消息总线
- @mention 原生触发（输入 @ 自动补全 bot 名字）
- agent 间 handoff 通过 Discord 消息（不是内部路由）
- 利用 Discord slash 命令（KOOK 没有此功能）
- 与 multi-agent-coordinator 集成

## 平台对比

| 能力 | Discord | KOOK |
|------|---------|------|
| @mention 自动补全 | 原生支持（bot 是真实用户） | 角色提及 + 文本匹配 |
| Slash 命令 | 平台级注册、自动补全、参数定义 | 不支持（仅文本解析） |
| 消息组件（按钮/菜单） | ActionRow + Button + SelectMenu | 卡片消息按钮（无菜单） |
| 模态框（表单） | 支持 | 不支持 |
| Bot 间消息可见 | 可见（`author.bot=True`，代码控制过滤） | 可见（`author_is_bot=True`，代码控制过滤） |
| Webhook 消息可见 | 可见（`webhook_id` 字段，代码控制过滤） | N/A |
| Embed 富文本 | 支持（title/description/fields/footer） | 卡片消息（更灵活但格式不同） |
| Threads | 原生支持 | 不支持（仅文字频道和私信） |

## 部署矩阵

### External Gateway Agents（原生 Gateway，不由 discord-nexus 管理）

| 机器 | Agent | Discord Bot | 说明 |
|------|-------|-------------|------|
| Mac | OpenClaw | 小龙虾 | 自带 Gateway，保留原生连接 |
| 云服务器 | Hermes | Hermes | 自带 Gateway，保留原生连接 |

### Managed Coding Agents（由 discord-nexus 托管）

| 机器 | Agent | Discord Bot 名 | adapter |
|------|-------|---------------|---------|
| Mac | Claude | Mclaucode | claude |
| Mac | Codex | Mac Codex | codex |
| Mac | opencode | Mac Ocode | opencode |
| Windows | Claude | Wclaucode | claude |
| Windows | opencode | Winopcode | opencode |
| Windows | OpenClaw | Win 小龙虾 | openclaw |

共 9 个 bot，通过 Discord 频道自然互联。跨机器 handoff 由 Discord Gateway 自动路由。

## 架构

```
每台机器：
  进程1: python bot.py --agent mac-claude
    → 独立 Discord bot 连接
    → on_message：只响应 @自己 或 !bang 自己的别名
    → channel.send() 发消息（不用 webhook）
  进程2: python bot.py --agent mac-codex
    → 同上
  ...

跨机器 agent 通信：
  Mac-Claude 发 "@Mac-Codex 继续"
    → Discord Gateway 投递 MESSAGE_CREATE 给 Mac-Codex
    → Mac-Codex 的 on_message 检测到自己被 @mention → 处理
```

### 消息过滤（核心改动）

```python
# 改前（bot.py:463）
if message.webhook_id or message.author.bot:
    return  # 过滤所有 bot/webhook 消息

# 改后（第一层只过滤自己，第二层按消息来源和协议判断）
if message.author.id == self.user.id:
    return

if message.author.bot:
    # bot-to-bot 只允许正式 handoff / coordinator handoff 协议触发。
    # 普通 bot 状态消息、thinking 消息、coordinator 状态广播都不触发 agent。
    if not is_handoff_message(message.content):
        return
```

过滤规则需要区分来源：

- 人类消息：`@我` 或自己的 `!bang` 别名即可触发。
- 其他 agent bot 消息：必须 `@我`，且必须带正式 handoff 协议。
- Coordinator 状态通知：默认不触发 agent，只进入可见审计流。
- Coordinator agent handoff：必须是专门的 handoff delivery，显式允许目标 bot mention。

### Handoff 机制

kook-nexus 用 `[handoff] @AgentName task` 文本协议。discord-nexus 统一使用**协议前缀 + Discord 原生 mention**：

**所有 bot-to-bot handoff 必须使用 `[handoff]` 前缀**，包括跨类型（managed → external、external → managed）：

```
[handoff] <@target_bot_uid> task description
```

1. Agent 输出含 `[handoff] @Codex 请继续`
2. 解析目标 agent 名 → 查找目标 bot 的 Discord user ID
3. 替换为 Discord mention `<@{user_id}>` 放入响应文本，并保留 `[handoff]` 前缀
4. 目标 bot 通过 Gateway 收到 MESSAGE_CREATE → 检测到 @自己 → 触发处理

跨类型 handoff 示例：
- Mac Claude → 小龙虾：`[handoff] <@小龙虾_uid> 帮我搜索资料`
- 小龙虾 → Mac Codex：`[handoff] <@Mac_Codex_uid> 请写代码`（需要小龙虾原生支持 `[handoff]` 协议）

**安全规则：** bot 普通回复里引用、总结或误 @ 另一个 agent 时不触发。只有带 `[handoff]` 前缀的 @mention 才触发新任务。

跨机器 handoff 无需额外代码 — Discord 自动投递。

保留 `[handoff]` 前缀的原因：

- 避免 bot 普通回复里引用、总结或误 @ 另一个 agent 时触发新任务。
- 方便 coordinator 生成机器可读的 assignment handoff。
- 与 kook-nexus 的安全经验保持一致。

### Session / Context 生命周期（必须前置设计）

当前旧 discord-nexus 会把 Claude/Codex CLI session id 存在 SQLite 的 `agent_workspace` 中，同一频道/线程再次触发同一 agent 时会调用 `claude --resume <session_id>` 或 `codex resume <session_id>`。

这个机制能保留连续工作上下文，但不能无限使用：

- CLI session 内部上下文会持续增长，迟早超过模型上下文窗口。
- CLI session 内的隐含上下文不完全等同于 Discord 群消息，人类不一定能看到。
- 多 agent 协作时，如果某个 agent 依赖只有自己 session 内部才有的状态，会破坏共享可见上下文。
- coordinator/harness 才是可恢复、可审计的长期状态源；Discord 群聊是共享可见操作界面；CLI session 只能是短期执行缓存。

因此新架构必须内建 session 生命周期管理，而不是默认无限 resume。

#### 上下文权威层级

| 层级 | 用途 | 是否权威 | 生命周期 |
|---|---|---|---|
| Discord 群消息 | 人和 agents 共享可见上下文、操作记录 | 可见上下文权威 | 长期保留，按平台/本地策略归档 |
| multi-agent-coordinator / harness | task、event、job、delivery、review、closeout 状态 | 工程状态权威 | 长期、可恢复、可审计 |
| SQLite conversation/context store | 最近消息、摘要、agent 本地 scratch | 辅助上下文 | 可压缩、可清理 |
| Claude/Codex CLI session | 单 agent 的短期连续执行缓存 | 非权威 | 必须可 reset / rotate |

Agent 在做严肃状态判断时，不应只相信 CLI session 记忆；应该读取群消息摘要、coordinator CLI、harness state 或明确的任务上下文。

#### Session Scope

新架构建议支持三种 session scope：

| Scope | 适用场景 | Session key |
|---|---|---|
| `thread` | 普通聊天、轻量问答 | `channel_id/thread_id + agent_id` |
| `task` | coordinator 分配的工程任务 | `workspace_id + task_id + agent_id` |
| `ephemeral` | 一次性工具调用/短任务 | 不持久化 session |

默认策略：

- 人类普通 @agent：使用 `thread` scope。
- coordinator handoff：使用 `task` scope。
- 明确一次性命令、health check、摘要生成：使用 `ephemeral` scope。

#### Session Rotation

每个 agent session 至少记录：

- `agent_id`
- `scope`
- `scope_key`
- `cli_session_id`
- `created_at`
- `updated_at`
- `turn_count`
- `last_message_id`
- `last_summary`
- `estimated_context_chars` 或 `estimated_tokens`（能估算就记录）
- `status`: `active` / `rotated` / `reset` / `archived`

触发 rotate 的条件：

- turn_count 超过阈值，例如 20-40 轮。
- session idle 超过阈值，例如 12-24 小时。
- 最近上下文估算超过预算，例如 60%-80% context window。
- agent 输出或 CLI 报上下文过长。
- coordinator task closeout/done 后归档 task-scoped session。
- 人类显式执行 reset/rotate 命令。

Rotate 流程：

1. 从 Discord 最近群聊、SQLite context、coordinator task state 和旧 session scratch 生成 summary。
2. 把 summary 写入 SQLite context store，并可选发一条可见状态消息：
   `Session rotated for Mac Codex / task smoke-001; summary saved.`
3. 标记旧 session `rotated`。
4. 新建 CLI session；首轮 prompt 注入 summary + 当前任务状态 + 最近群聊。

不能 silent rotate。至少要有本地可审计记录；工程任务最好有可见状态或 coordinator event。

#### Session Commands

多 bot 架构需要提供最小 session 操作命令，方便人类和 operator 排障：

```text
!session status
!session reset
!session rotate
!session archive
```

如果使用 slash command，可设计为：

```text
/session status agent:<agent> scope:<thread|task> task_id:<optional>
/session reset agent:<agent> scope:<thread|task> task_id:<optional>
/session rotate agent:<agent> scope:<thread|task> task_id:<optional>
```

`status` 输出应包含：

- 当前 agent
- scope / scope_key
- CLI session id（可截断显示）
- created_at / updated_at
- turn_count
- 是否接近 rotation 阈值
- 最近 summary 是否存在

`reset` 必须清除本地 session id，但不删除 Discord 消息、coordinator event 或 harness state。

#### Terminal 可见性

Discord bot 调用 Claude/Codex 时是 subprocess JSON/stream-json 模式，不会打开可交互终端窗口。终端能看到的是：

- bot 进程日志
- CLI stdout/stderr 的解析结果或 tail
- SQLite 中记录的 session id
- agent run/job 记录

如果需要人工接管，可以从 session status 里拿到 CLI session id，再在终端手动 resume：

```bash
claude -p --resume <session_id>
codex resume <session_id>
```

这不是接入原来的 live process，而是用同一个 CLI session 继续发新 prompt。接管操作也应该回写群聊或 coordinator，避免隐性状态。

#### Coordinator Handoff 与 Session

coordinator 主动分配任务时，handoff 消息必须带足够上下文，让目标 agent 创建或恢复 task-scoped session：

```text
[handoff] <@Mac-Codex-Bot-ID> coordinator assignment
workspace_id=mac-smoke
task_id=smoke-001
owner=mac-codex
session=coordinator-session-id
action=assignment.accept
```

目标 agent 收到后：

1. 用 `workspace_id + task_id + agent_id` 查找 task-scoped CLI session。
2. 如果没有，创建新 session。
3. 第一件事调用 coordinator CLI `assignment accept`。
4. prompt 注入 coordinator task state、最近群聊、必要 summary，而不是依赖旧 thread session。

任务 closeout/done 后，该 task-scoped session 应归档，不再作为默认上下文继续使用。

## 配置格式

对齐 kook-nexus 的 TOML 格式：

```toml
# agents.toml

[defaults]
timeout = 360
activity_timeout = 120
channels = ["1503350765295767623"]
respond_to_bots = true
context_db_path = "data/discord_context.sqlite3"
context_recent_messages = 40
context_budget_chars = 12000
wiki_enabled = true
wiki_path = "wiki"
discoveries_channel_id = "1503350765295767623"

[[agents]]
id = "mac-claude"
adapter = "claude"
token_env = "DISCORD_MAC_CLAUDE_TOKEN"
aliases = ["Mac Claude", "Claude"]
channels = ["1503350765295767623"]
work_dir = "/Users/yinxin/projects"

  [agents.system_prompt]
  text = """
  You are Claude, running on Mac via Discord.
  ...
  """

[[agents]]
id = "mac-codex"
adapter = "codex"
token_env = "DISCORD_MAC_CODEX_TOKEN"
aliases = ["Mac Codex", "Codex"]
channels = ["1503350765295767623"]
work_dir = "/Users/yinxin/projects"

[[agents]]
id = "mac-openclaw"
adapter = "openclaw"
token_env = "DISCORD_MAC_OPENCLAW_TOKEN"
aliases = ["Mac OpenClaw", "OpenClaw"]
channels = ["1503350765295767623"]
openclaw_agent_id = "main"

[[agents]]
id = "mac-opencode"
adapter = "opencode"
token_env = "DISCORD_MAC_OPENCODE_TOKEN"
aliases = ["Mac OpenCode", "opencode"]
channels = ["1503350765295767623"]

[[agents]]
id = "server-hermes"
adapter = "hermes"
token_env = "DISCORD_SERVER_HERMES_TOKEN"
aliases = ["Hermes"]
channels = ["1503350765295767623"]
work_dir = "/home/ubuntu/projects"
```

`.env` 存放实际 token（不入库）：

```
DISCORD_MAC_CLAUDE_TOKEN=...
DISCORD_MAC_CODEX_TOKEN=...
DISCORD_MAC_OPENCLAW_TOKEN=...
DISCORD_MAC_OPENCODE_TOKEN=...
DISCORD_SERVER_HERMES_TOKEN=...
```

## 新文件结构

```
discord-nexus/
  bot.py                       ← 瘦入口：读 TOML config → 启动 DiscordClient
  agents.toml                  ← 多 agent 配置
  agents.toml.example          ← 示例
  .env                         ← bot tokens

  discord_nexus/
    __init__.py
    config.py                  ← TOML 配置加载（参考 kook-nexus/config.py）
    models.py                  ← AgentConfig dataclass
    client.py                  ← DiscordClient 类（discord.Client 子类）
    adapters/
      __init__.py
      base.py                  ← BaseAdapter ABC
      claude.py                ← Claude CLI（从 kook-nexus 移植）
      codex.py                 ← Codex CLI（从 kook-nexus 移植）
      openclaw.py              ← OpenClaw CLI（从 kook-nexus 移植）
      opencode.py              ← OpenCode CLI（从 kook-nexus 移植）
      hermes.py                ← Hermes CLI（从 kook-nexus 移植）
      factory.py               ← adapter 工厂
    context/
      __init__.py
      store.py                 ← SQLite 上下文存储（WAL 模式支持多进程）
      prompt.py                ← Prompt 构建（含 wiki/scratch 注入）
    sessions/
      __init__.py
      store.py                 ← CLI session id / scope / rotate 状态
      policy.py                ← rotate/reset/archive 判断
    routing/
      __init__.py
      mentions.py              ← @mention 解析和路由
    wiki/
      __init__.py
      store.py                 ← 文件 wiki 系统
    security/
      __init__.py
      allowlist.py
      filter.py                ← secrets 过滤
    utils/
      __init__.py
      chunker.py               ← Discord 消息分片（2000 字符限制）
      tags.py                  ← SCRATCH/DISCOVERY/WIKI/RESEARCH 标签提取
```

## 核心类设计

### DiscordClient（client.py）

```python
class DiscordClient(discord.Client):
    """一个 agent = 一个 DiscordClient 实例。"""

    def __init__(self, agent_config, shared_config):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.agent_config = agent_config
        self.shared_config = shared_config
        self.adapter = create_adapter(agent_config)
        self.context_store = ContextStore(agent_config.context_db_path)
        self.wiki_store = WikiStore(...) if shared_config.wiki_enabled else None

    async def on_ready(self):
        # 记录自己的 user_id 到共享存储，供其他 bot handoff 使用
        await self._register_bot_user_id()

    async def on_message(self, message):
        # 1. 过滤自己的消息
        if message.author.id == self.user.id:
            return

        # 2. 判断是否 addressed to me
        is_mentioned = self.user in message.mentions
        is_banged = self._matches_bang(message.content)

        if not (is_mentioned or is_banged):
            # 仍保存人类消息到上下文
            if not message.author.bot:
                await self.context_store.save_human_message(message)
            return

        # 3. 安全检查
        if not message.author.bot and not self.allowlist.is_allowed(message.author.id):
            return

        # 4. 处理请求
        await self._handle_request(message)

    async def _handle_request(self, message):
        # 1. 发 "thinking..." 占位
        placeholder = await message.channel.send("🔄 thinking...")

        # 2. 构建 prompt
        prompt = await self.context_store.build_prompt(
            message, self.agent_config, self.wiki_store
        )

        # 3. 调用 adapter（支持 streaming）
        response_text = await self.adapter.call(prompt, ...)

        # 4. 提取标签
        tags, clean_text = extract_tags(response_text)

        # 5. 解析 handoff mention（@AgentName → <@{user_id}>）
        clean_text = self._resolve_handoff_mentions(clean_text)

        # 6. 发送响应（编辑占位 + 分片）
        chunks = chunk_message(clean_text)
        if chunks:
            await placeholder.edit(content=chunks[0])
            for chunk in chunks[1:]:
                await message.channel.send(chunk)

        # 7. 保存上下文
        await self.context_store.save(...)

        # 8. 处理标签
        await self._process_tags(tags, message)
```

### Adapter（参考 kook-nexus）

Adapter 直接从 kook-nexus 移植，接口基本一致（都是 subprocess CLI 调用）：

```python
# discord_nexus/adapters/base.py
class BaseAdapter(ABC):
    @abstractmethod
    async def call(self, prompt: str, **kwargs) -> str: ...

    @abstractmethod
    async def health_check(self) -> dict: ...
```

## 保留的 discord-nexus 特有功能

| 功能 | 处理方式 |
|------|---------|
| Wiki | 每个进程读写共享 wiki 目录（文件锁） |
| Discoveries | 写入 Discord #discoveries 频道（任何 bot 都能发） |
| Scratch zones | 每个进程独立处理自己的 SCRATCH 标签 |
| Conversation history | SQLite WAL 模式支持多进程并发读写 |
| CLI session persistence | 保留但必须 task/thread scoped，可 status/reset/rotate |
| Tag 处理 (SCRATCH/DISCOVERY/WIKI/RESEARCH) | 每个进程独立处理 |
| Streaming placeholder | channel.send + message.edit（不用 webhook） |
| !bang commands | 保留，每个进程只处理自己的 bang 别名 |
| Channel missions | 从配置读取，注入 prompt |
| 安全过滤 (secrets) | 每个进程独立执行 |

## 暂不保留/简化的功能

| 功能 | 原因 |
|------|------|
| `!all` / `@team` 广播 | 每个 bot 独立响应 @mention 即可 |
| Rate-limit fallback chain | 每个 bot 独立处理限流 |
| Agent Webhook 发送 | agent 不再用 webhook 假扮身份，改为 bot 自己发消息 |
| `cogs/agents.py` 中央路由 | 拆到每个 client.py 的 on_message |
| 单 bot NexusBot 类 | 完全替换为 DiscordClient |
| Cogs 框架 | 不再需要，逻辑直接写在 DiscordClient 里 |
| Memory washer | 独立定时任务，不依赖 bot |
| Orchestration (多 agent 分阶段) | 简化，agent 间通过 Discord 消息自然协调 |

## 与 multi-agent-coordinator 的集成

### 当前状态

coordinator 和 discord-nexus 目前是**独立系统**：

- coordinator 有自己的 Discord delivery worker（用 `DISCORD_BOT_TOKEN` 通过 REST API 发消息）
- discord-nexus 有自己的 agent 调度（通过 CLI subprocess）
- 两者之间没有直接调用关系

### 集成目标

```
用户 @Mac-Claude "请实现 feature X"
  → Claude agent 工作
  → Claude 调用 coordinator CLI 更新 task 状态
  → coordinator 写事件（ci.passed、pr_review.approved 等）
  → coordinator delivery worker 发状态消息到 Discord 频道
  → 用户在 Discord 看到完整的状态更新流
```

### Coordinator 需要的改动

#### 1. 添加 WebhookBus 支持（bus.py）

当前 coordinator 用 Bot Token 发 Discord 消息。多 bot 架构下，状态广播改为 webhook 更干净：

```python
# 新增 WebhookBus（bus.py）
class WebhookBus:
    """通过 Discord Webhook URL 发送状态消息，不需要 bot token。"""

    def __init__(self, webhook_url: str):
        # 解析 webhook_url: https://discord.com/api/webhooks/{id}/{token}
        ...

    def send(self, *, destination, payload, message_key) -> str:
        # POST {webhook_url}?wait=true
        # Body: {"content": text, "username": "coordinator", "allowed_mentions": {"parse": []}}
        ...
```

**好处：**
- 不需要额外的 bot token
- 不需要在服务器里多加一个 bot 用户
- Webhook 消息在频道里显示为 "coordinator" 名字和头像
- discord-nexus 可以在目标频道创建 webhook，把 URL 传给 coordinator

**重要边界：WebhookBus 只用于状态通知，不用于启动 agent。**

状态通知示例：

```text
[ASSIGN] smoke-001 assigned to codex (session=sess-1)
[BLOCKER] smoke-001 CI failed: tests
[DONE] smoke-001 marked done by coordinator
```

这些消息应该可见、可审计，但默认不应该触发 agent。

#### 2. 添加 AgentHandoff delivery（后续能力）

如果 coordinator 要主动启动某个 Discord agent，不能复用普通状态通知。需要单独的 handoff delivery 类型，例如：

```text
[handoff] <@TARGET_BOT_USER_ID> coordinator assignment
workspace_id=mac-smoke
task_id=smoke-001
owner=mac-codex
session=...
action=assignment.accept
```

这类消息必须：

- 使用 Discord 原生 user mention，而不是纯文本 `@Mac Codex`。
- `allowed_mentions` 只允许目标 bot user id，不能开放 `parse=["users"]`。
- 包含 `workspace_id`、`task_id`、`owner/session` 等 coordinator 必需字段。
- 明确要求目标 agent 调用 coordinator CLI 回写 `assignment accept` 或后续结果。

也可以选择不用 webhook，而是新增一个 dedicated Coordinator Bot 发送 handoff。两种方案都可以，但职责不同：

| 发送者 | 用途 | 是否触发 agent |
|---|---|---|
| Coordinator Webhook | 状态广播、审计流 | 默认否 |
| Coordinator Bot / AgentHandoffBus | 主动分配任务给 agent | 是，仅目标 bot |

**改动范围：**
- `bus.py`：新增 `WebhookBus` 类，修改 `bus_for_platform()` 支持 `"discord_webhook"` 平台
- `policy.py`：普通 event 仍生成状态 delivery；后续为 assignment/handoff 增加专门 agent handoff 渲染
- `db.py`：Workspace 的 `default_bus` 字段支持 `"discord_webhook"`，后续可增加 agent handoff bus 类型
- CLI/配置：destination 字段存 webhook URL 而不是 channel ID

#### 3. 不需要改动的部分

| 模块 | 原因 |
|------|------|
| `worker.py` | 平台无关，只调用 bus.send() |
| `policy.py` | 平台无关，只生成 delivery 行 |
| `assignments.py` | 平台无关，只写事件 |
| `cli.py` | 平台无关，所有子命令不变 |
| `db.py`（schema） | 不变，只新增 bus 类型支持 |
| `ci.py`、`reviews.py` | 不变，纯业务逻辑 |

### Discord-Nexus 需要为 Coordinator 做的适配

#### 1. Agent 系统提示注入 coordinator CLI 路径

在 agent 的 `system_prompt` 中加入 coordinator 使用说明：

```
COORDINATOR 集成：
你可以调用 multi-agent-coordinator CLI 来跟踪任务状态：
  cd /Users/yinxin/projects/multi-agent-coordinator
  MAC_DB=... skills/multi-agent-coordinator-operator/scripts/mac.sh assignment accept <workspace> --task-id <id> --owner <agent> --session <session>
  MAC_DB=... skills/multi-agent-coordinator-operator/scripts/mac.sh ci check <workspace> --task-id <id>
  MAC_DB=... skills/multi-agent-coordinator-operator/scripts/mac.sh merge gate <workspace> --task-id <id>

不要直接修改 harness JSON。所有状态变更必须通过 coordinator CLI 或 harnessctl mutation service。
```

#### 2. Agent 工作目录包含 coordinator 项目

确保 agent 的 `work_dir` 下能访问 coordinator CLI（已安装到 PATH 或通过 `mac.sh` 脚本）。

#### 3. Coordinator 任务上下文注入

当 agent 是由 coordinator handoff 触发时，消息必须携带：

- `workspace_id`
- `task_id`
- `owner`
- `session`
- `expected action`（例如 `assignment.accept`、`handoff.accept`、`review-result`）

Agent 收到后第一步应回写 coordinator，例如：

```bash
MAC_DB=... skills/multi-agent-coordinator-operator/scripts/mac.sh \
  assignment accept "$WORKSPACE_ID" --task-id "$TASK_ID" --owner "$OWNER" --session "$SESSION"
```

Coordinator handoff 必须使用 `task` scope session，不能复用普通频道 thread session。

#### 4. Webhook 创建（可选）

discord-nexus 启动时在目标频道创建一个 webhook 供 coordinator 使用，将 webhook URL 存入 coordinator 的 workspace 配置。

### 集成后的完整流程

#### A. Agent 主动使用 coordinator

```
1. 用户在 Discord: "@Mac-Claude 请实现 feature X，创建 PR"
2. Mac-Claude bot 收到消息 → 触发 ClaudeAgent
3. Claude 工作：
   a. 调用 coordinator CLI: assignment accept / branch allocate
   b. 写代码、提交、push
   c. 调用 coordinator CLI: pr link
   d. 调用 coordinator CLI: ci check / review check
   e. 调用 coordinator CLI: merge gate
4. Coordinator 后台：
   a. 事件写入 SQLite
   b. policy pump → 创建 deliveries
   c. delivery worker → 通过 webhook 发状态消息到 Discord
5. 用户在 Discord 看到：
   - Claude 的响应（agent bot 直接发）
   - coordinator 的状态更新（webhook 发，显示为 "coordinator" 用户）
   - 两类消息共存于同一频道
```

#### B. Coordinator 主动分配任务给 agent

```
1. 用户或系统调用 coordinator:
   assignment request WORKSPACE --task-id TASK --owner mac-codex --session SESSION
2. Coordinator 写 assignment.requested event
3. Policy 生成两类 delivery：
   a. 状态广播：[ASSIGN] TASK assigned to mac-codex
   b. agent handoff：[handoff] <@Mac-Codex-Bot-ID> ...workspace_id/task_id/session...
4. Discord delivery worker 发送 handoff，只允许目标 bot mention
5. Mac-Codex bot 收到 bot/webhook 消息，因包含 [handoff] 且 @自己 → 启动 Codex
6. Codex 第一件事调用 coordinator CLI:
   assignment accept WORKSPACE --task-id TASK --owner mac-codex --session SESSION
7. 后续代码、结果、blocker、closeout 都继续通过 coordinator 回写
```

这条路径才是“coordinator-driven assignment”。它和普通状态通知必须分开设计。

## 分阶段实施

### Phase 1：基础架构 + 单 agent 验证 ✅

已完成。`discord_nexus/` 包结构、client.py、claude adapter、context store、mention routing 全部实现，19 个单元测试通过。

### Phase 1.5：消息过滤 + handoff 修复 ✅

已完成。6 个问题修复（handoff 正则支持 `<@id>`、channel 过滤前置、respond_to_bots、allowed_user_ids），19 个单元测试通过。

### Phase 1.8：移植 Hermes adapter ✅

已完成。hermes.py + factory.py + config.py work_dir 修复 + 13 个测试，32 tests 全部通过。

### Phase 2：混合架构部署 + handoff 验证（当前阶段）

**架构决策：混合模式**

两类 agent 的 Discord 连接方式不同：

| 类型 | Agent | Discord 连接 | discord-nexus 管理 |
|------|-------|-------------|-------------------|
| 个人助理 | 小龙虾/OpenClaw、Hermes | 原生 Gateway（自带） | 不管理，不启动进程 |
| Coding | Claude、Codex、OpenCode | discord-nexus adapter | 启动进程，管理 handoff |

**为什么不用 discord-nexus 管理所有 agent：**
- 一个 bot token 只能有一个 Gateway 连接
- 小龙虾和 Hermes 已有原生 Gateway，再起会冲突
- 个人助理自带常驻进程，不需要 adapter 包装

**Handoff 链路（全部通过 Discord 消息，必须使用 `[handoff]` 协议）：**
```
用户 @Mclaucode "请实现 X"
  → Mac Claude (discord-nexus) 处理
  → Claude 回复含 [handoff] <@小龙虾_uid> 帮我搜索资料
  → 小龙虾 (原生 Gateway) 收到 bot 消息 → 处理
  → 小龙虾回复含 [handoff] <@Mac_Codex_uid> 请写代码
  → Mac Codex (discord-nexus) 收到 → 处理
```

跨类型 handoff 不需要额外代码——只要小龙虾/Hermes 能接收 bot 消息（已确认可以），Discord 自然投递。

**前提条件：** 用户操作（已完成 ✅）
1. 测试频道已创建（`1507289970459803738`）
2. Coding agents 的 Discord bot 已创建：
   - Mclaucode (mac-claude) — ID: 1507329791982833775
   - Mac Codex (mac-codex) — ID: 1507330121235697794
   - Mac Ocode (mac-opencode) — ID: 1507326063745957898
   - Wclaucode (win-claude) — ID: 1507330641694298242
   - Winopcode (win-opencode) — ID: 1507331957988524072
   - Win 小龙虾 (win-openclaw) — ID: 1507331342780727326
3. External agents 使用已有 bot：
   - 小龙虾 (mac-openclaw) — 保留原生 Gateway
   - Hermes (server-hermes) — 保留原生 Gateway

**代码改动（前置：external_agents 配置支持）：**

1. **`models.py`**：`KnownAgentMention` 无需改动，已支持 external-only 用途
2. **`config.py`**：新增 `[[external_agents]]` TOML 配置读取，构建 `KnownAgentMention` 列表追加到 `known_agents`
3. **`routing/mentions.py`**：无需改动，`MentionRouter` 已通过 `known_agents` 统一处理
4. **`agents.toml`**：新增 `[[external_agents]]` 配置段
5. **补测试**：验证 external_agents 能被 handoff 路由识别

**`agents.toml` 格式：**
```toml
# External agents: 保留原生 Gateway，不启动 adapter，不需要 token
[[external_agents]]
id = "mac-openclaw"
display_name = "小龙虾"
aliases = ["小龙虾", "OpenClaw"]
discord_user_id = <小龙虾_user_id>

[[external_agents]]
id = "server-hermes"
display_name = "Hermes"
aliases = ["Hermes", "爱马仕"]
discord_user_id = <Hermes_user_id>
```

**验证步骤（先人工测试 handoff，再测自动 handoff）：**

| 步骤 | 操作 | 预期 |
|------|------|------|
| 2a | `python nexus.py --agent mac-claude` | 控制台输出 ready |
| 2b | `@Mclaucode 你好` | Mac Claude 回复 |
| 2c | `@Mclaucode 请回复：[handoff] <@小龙虾_uid> 请回复收到` | 验证 resolve_handoff_mentions 正确转换 |
| 2d | 人工在频道发 `[handoff] <@Mclaucode_uid> 测试跨类型` | Mac Claude 收到并处理 |
| 2e | 启动 Mac Codex，测试三方 handoff | 完整链路验证 |

**关键文件：**
- `agents.toml`（新建，含 coding agents + external_agents）
- `.env`（更新，coding agent tokens）
- `discord_nexus/config.py`（新增 external_agents 读取）
- `tests/test_config.py` 或 `tests/test_mentions.py`（补 external_agents 路由测试）
- `agents.toml`（新建，含 coding agents + external_agents）
- `.env`（更新，coding agent tokens）

### Phase 3：高级功能

1. Slash 命令（每个 bot 注册自己的命令）
2. Wiki 系统迁移
3. Discoveries 频道
4. Scratch zones
5. Conversation history + 摘要
6. Session rotate/archive policy
7. Streaming placeholder
8. 安全过滤（secrets）
9. Channel missions
10. 移植 opencode / codex adapter（hermes adapter 已在 Phase 1.8 完成，保留为非 gateway worker/CLI 调用能力）

### Phase 4：Coordinator 集成

1. coordinator `bus.py` 添加 `WebhookBus`
2. coordinator CLI `workspace add` 支持 `--default-bus discord_webhook`
3. discord-nexus agent system_prompt 注入 coordinator CLI 路径
4. 端到端测试 A：agent 调 coordinator → coordinator 通过 webhook 发状态
5. 设计并实现 coordinator agent handoff delivery（只允许目标 bot mention）
6. 端到端测试 B：coordinator assignment → Discord handoff → 目标 agent accept → coordinator 状态回写

### Phase 5：部署 + 清理

1. launchd 配置（Mac 多进程）
2. systemd 配置（云服务器）
3. Windows 启动脚本
4. 移除旧代码（NexusBot、cogs/、webhook 逻辑）
5. 更新文档

## Discord Developer Portal 准备工作

**只为 discord-nexus 托管的 coding agents 新建 bot：**
- Mclaucode (mac-claude)、Mac Codex、Mac Ocode、Wclaucode (win-claude)、Winopcode、Win 小龙虾

**小龙虾/Hermes 使用已有 bot，不新建、不复用 token。**

每个新 bot 需要：
1. 创建 Discord Application → Bot → 获取 token
2. 启用 **Message Content Intent**（Bot 设置页）
3. 生成邀请链接：scope = `bot` + `applications.commands`
4. 权限：Send Messages、Read Message History、Use Slash Commands、Manage Webhooks
5. 邀请到目标服务器
6. 加入 `Nexus Agents` 身份组（统一权限管理）

## 参考

- kook-nexus 架构：`/Users/yinxin/projects/kook-nexus/`（一进程一 agent，已验证）
- kook-nexus 配置：`/Users/yinxin/projects/kook-nexus/agents.toml`
- kook-nexus adapter：`/Users/yinxin/projects/kook-nexus/kook_nexus/adapters/`
- discord-nexus 现有功能：wiki、scratch、discoveries、streaming
- coordinator Discord delivery：`/Users/yinxin/projects/multi-agent-coordinator/src/multi_agent_coordinator/bus.py`
- Discord API 事实：Bot 能收到其他 bot 消息（`author.bot=True`）和 webhook 消息（`webhook_id` 有值），代码层面控制过滤
