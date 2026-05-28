# Phase 3.2 Round 2：Embed 化 Operator Slash 输出

## 背景

Phase 3.2 Round 1 已经实现并真实验证 Discord slash commands：

- `/agents`
- `/health`
- `/session status`
- `/session reset`

这些命令已经可见、可用，并且回复为 ephemeral。当前输出仍是纯文本。Round 2 的目标是把 slash command 的 operator 输出升级为 Discord embeds，让 Discord cockpit 更接近结构化控制台。

当前基线提交：

```text
b04326b Add slash commands (/agents, /health, /session status, /session reset)
```

当前测试基线：

```bash
python -m unittest discover tests/
```

预期基线为 88 tests OK。

## 目标

只改展示层，不改变行为语义：

- Slash commands 使用 embeds。
- 文本 operator commands 保持纯文本。
- 继续保持 ephemeral。
- 继续使用 `allowed_mentions=discord.AllowedMentions.none()`。
- 不改变 handoff、session、adapter、权限和 external gateway agent 边界。

## 范围

### Slash Commands

#### `/agents`

输出一个 embed：

- Title: `Known Agents`
- Color: `discord.Color.blurple()`
- Fields:
  - `Managed`
  - `External`

每个 agent 显示：

- `agent.id`
- `agent.primary_name`
- Discord ID

不要输出真实 Discord mention `<@id>`，避免 ping 外部 bot。使用：

```text
discord_id: `123456789`
```

没有 Discord ID 时显示：

```text
no Discord ID
```

示例字段内容：

```text
mac-claude (Mac Claude) - discord_id: `...`
mac-codex (Mac Codex) - discord_id: `...`
```

```text
mac-openclaw (小龙虾) - discord_id: `...`
server-hermes (Hermes) - discord_id: `...`
```

#### `/health`

输出一个 embed：

- Title: `Health Check - <agent_id>`
- Fields:
  - `adapter`
  - `bin`
  - `available`
  - `work_dir`
  - `model`
  - `timeout`

颜色规则：

- Green：`health["available"] is True`
- Red：`health["available"] is False` 或 health check 抛异常
- Yellow：预留给未来 warning，目前可不使用；如果存在 `warning` 字段，可以使用 `discord.Color.gold()`

`available` 字段显示：

```text
yes
```

或：

```text
no
```

`bin` 字段可以包含 binary 名称和 resolved path，例如：

```text
claude
/Users/yinxin/.claude/local/claude
```

#### `/session status`

输出一个 embed：

- Title: `Session Status - <agent_id>`
- Fields:
  - `scope`
  - `session_id`
  - `adapter`
  - `work_dir`
  - `status`
  - `turns`
  - `updated`
  - `active sessions`

有 active session 时：

- Color: `discord.Color.green()`
- `session_id` 截断显示，例如前 16 字符：

```text
`sess-abc123...`
```

没有 active session 时：

- Color: `discord.Color.gold()`
- Description: `No active session in this scope.`
- 仍显示 `scope` 和 `active sessions`

#### `/session reset`

本轮推荐保持简单 ephemeral text，不强制 embed 化：

```text
Session reset - mac-claude

Marked session in scope 12345 as stale.
Next call will start fresh.
```

原因：

- reset 是确认型反馈，不需要复杂结构。
- 减少改动范围。
- 权限和 session 行为必须保持不变。

## 文本命令兼容

以下文本 operator commands 保持纯文本输出：

- `@bot agents`
- `@bot health`
- `@bot session status`
- `@bot session reset`

不要把文本命令一起改成 embed。Round 2 只聚焦 slash UX。

## 安全与行为边界

必须保持：

- Slash replies 使用 `ephemeral=True`
- Slash replies 使用 `allowed_mentions=discord.AllowedMentions.none()`
- Operator 输出不包含 `<@id>`，避免 ping external bots
- 不改变 `respond_to_bots`
- 不改变 `[handoff] + @mention` 触发边界
- 不改变 session scope
- 不改变 adapter 调用逻辑
- 不启动 Hermes / 小龙虾 adapter
- 不改变 external gateway agent 行为

## 推荐实现

新增文件：

```text
discord_nexus/embeds.py
```

建议放纯展示层 builder，避免继续膨胀 `client.py`。

推荐函数：

```python
import discord

def build_agents_embed(config) -> discord.Embed:
    ...

def build_health_embed(config, health: dict) -> discord.Embed:
    ...

def build_session_status_embed(client, channel_id: int) -> discord.Embed:
    ...
```

职责划分：

- `client.py` 负责 slash handler、权限检查、channel allowlist、调用 adapter health check。
- `embeds.py` 只负责把 config/session/health 数据渲染成 Discord embed。
- `commands.py` 继续负责文本 operator command 输出。

### `/agents` handler

从文本响应：

```python
response = await handle_operator_command("agents", self, interaction.channel_id)
await interaction.response.send_message(
    response,
    allowed_mentions=discord.AllowedMentions.none(),
    ephemeral=True,
)
```

改为 embed 响应：

```python
embed = build_agents_embed(self.agent_config)
await interaction.response.send_message(
    embed=embed,
    allowed_mentions=discord.AllowedMentions.none(),
    ephemeral=True,
)
```

### `/health` handler

建议在 handler 中捕获 health check 异常：

```python
try:
    health = await self.adapter.health_check()
except Exception as exc:
    health = {
        "adapter": self.agent_config.adapter,
        "bin": "?",
        "available": False,
        "error": str(exc),
    }

embed = build_health_embed(self.agent_config, health)
await interaction.response.send_message(
    embed=embed,
    allowed_mentions=discord.AllowedMentions.none(),
    ephemeral=True,
)
```

### `/session status` handler

```python
embed = build_session_status_embed(self, interaction.channel_id)
await interaction.response.send_message(
    embed=embed,
    allowed_mentions=discord.AllowedMentions.none(),
    ephemeral=True,
)
```

### `/session reset` handler

保持现状，继续调用：

```python
response = await handle_operator_command("session reset", self, interaction.channel_id)
await interaction.response.send_message(
    response,
    allowed_mentions=discord.AllowedMentions.none(),
    ephemeral=True,
)
```

## 测试计划

建议新增：

```text
tests/test_embeds.py
```

覆盖：

1. `build_agents_embed()`
   - 有 `Managed` field
   - 有 `External` field
   - 包含 `discord_id:`
   - 不包含 `<@`

2. `build_health_embed()` available true
   - title 包含 agent id
   - color 是 green
   - fields 包含 adapter/bin/available/work_dir/model/timeout
   - available 显示 `yes`

3. `build_health_embed()` available false
   - color 是 red
   - available 显示 `no`

4. `build_health_embed()` health error
   - color 是 red
   - embed 包含 error 信息，注意截断到 Discord 合理长度

5. `build_session_status_embed()` 有 active session
   - title 包含 agent id
   - fields 包含 scope/session_id/turns/updated/active sessions
   - session_id 被截断
   - color 是 green

6. `build_session_status_embed()` 无 active session
   - description 包含 `No active session`
   - color 是 gold
   - 仍显示 active sessions count

注意：

- 不要把 `tests/test_commands.py` 的文本 command 断言改成 embed。
- 原有 `handle_operator_command()` 行为应保持。

运行：

```bash
python -m unittest discover tests/
```

预期：

- 所有测试通过。
- 测试数量高于当前 88。

## 手动验收

在 Discord 中验证：

1. `/agents`
   - 回复是 ephemeral embed
   - Managed / External 分组清晰
   - 没有 ping 外部 bot

2. `/health`
   - 回复是 ephemeral embed
   - adapter 可用时为绿色
   - adapter 不可用或 health check error 时为红色
   - 字段包含 adapter/bin/available/work_dir/model/timeout

3. `/session status`
   - 回复是 ephemeral embed
   - 有 session 时显示 session_id/turns/updated
   - 无 session 时显示 no active session

4. `/session reset`
   - 仍可用
   - 仍是 ephemeral
   - 权限逻辑不变

5. 文本命令仍可用且保持纯文本：
   - `@bot agents`
   - `@bot health`
   - `@bot session status`
   - `@bot session reset`

## 不做的事

本轮不要做：

- 不做 Phase 3.2 acceptance 文档补录
- 不做 launchd 常驻化
- 不做 coordinator 集成
- 不做 `/task` 命令
- 不做 Discord component/button/select menu
- 不改 handoff 协议
- 不改 session persistence schema
- 不改 text operator command 输出
- 不启动 Hermes / 小龙虾 adapter
- 不提交 `.env`、`agents.toml`、真实 token、webhook URL
