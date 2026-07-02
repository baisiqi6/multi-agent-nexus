> **Historical design note.** Current source of truth: `docs/project-harness/architecture.md` and `docs/project-harness/scope.md`. This file is preserved for historical context only.

# Phase 3.2 Round 1：Slash Commands

## 背景

Phase 3.1 实现了四个 operator commands（session status/reset, agents, health），通过 @mention 或 !bang 文本触发。现在迁移为 Discord 原生 slash commands，保留文本命令兼容。

## 命令映射

| Slash Command | 对应文本命令 | 说明 |
|---------------|-------------|------|
| `/agents` | `@bot agents` | 列出 managed/external agents |
| `/health` | `@bot health` | adapter health check |
| `/session status` | `@bot session status` | 当前 scope session 信息 |
| `/session reset` | `@bot session reset` | 标记 stale（需权限） |

注意：多个 bot 都注册同名 `/agents`、`/health` 是正常的，因为它们是不同 Discord Application。Discord UI 会按 bot/app 名区分。但用户可能看到多个同名命令列表。

## 实现步骤

### Step 1：重构 commands.py — handlers 接受 channel_id

`handle_operator_command` 和内部 handlers 改为接受 `channel_id: int` 替代 `message` 对象：

```python
async def handle_operator_command(cmd: str, client, channel_id: int) -> str:
    if cmd == "session status":
        return _cmd_session_status(client, channel_id)
    ...
```

新增共享权限检查函数：

```python
def can_run_operator_command(config, user_id: int, cmd: str) -> str | None:
    """返回 None 表示允许，否则返回拒绝原因。"""
    if is_dangerous_command(cmd):
        if not config.allowed_user_ids or user_id not in config.allowed_user_ids:
            return "Unauthorized: this command requires explicit operator permission."
    return None
```

文本命令和 slash 命令都调用此函数，避免权限语义分叉。

### Step 2：DiscordClient 挂载 CommandTree

`client.py` 的 `__init__` 加：
```python
self.tree = app_commands.CommandTree(self)
self._commands_synced = False
```

`setup_hook()` 中注册命令（非 on_ready）：
```python
async def setup_hook(self):
    self._register_slash_commands()
```

新增 `_register_slash_commands()` 方法，用 `@self.tree.command` 和 `app_commands.Group` 注册四个命令。

### Step 3：on_ready 中 guild-scoped sync（一次性）

```python
async def on_ready(self):
    # ... existing code ...
    if not self._commands_synced and self.agent_config.channels:
        guild_id = ... # 从 channels 推断或从配置读取
        try:
            self.tree.copy_global_to(guild=discord.Object(id=guild_id))
            await self.tree.sync(guild=discord.Object(id=guild_id))
            self._commands_synced = True
        except Exception:
            log.warning("Failed to sync slash commands", exc_info=True)
```

Guild-scoped sync 立即生效（无传播延迟），适合当前测试阶段。后续稳定了再考虑 global sync。

### Step 4：Slash handler 实现

每个 slash handler 做：
1. **Channel allowlist 检查**：slash command 绕过 `on_message`，必须手动检查。Thread 检查 parent channel。
2. **权限检查**：调用 `can_run_operator_command()`
3. **执行命令**：调用 `handle_operator_command(cmd, self, interaction.channel_id)`
4. **回复**：`interaction.response.send_message(..., allowed_mentions=discord.AllowedMentions.none())`
5. **Session scope**：用 `interaction.channel_id`（thread 用自己的 id）

示例：
```python
@self.tree.command(name="agents", description="List all known agents")
async def slash_agents(interaction: discord.Interaction):
    if not _is_channel_allowed(self, interaction):
        await interaction.response.send_message("Not available in this channel.", ephemeral=True)
        return
    deny = can_run_operator_command(self.agent_config, interaction.user.id, "agents")
    if deny:
        await interaction.response.send_message(deny, ephemeral=True)
        return
    response = await handle_operator_command("agents", self, interaction.channel_id)
    await interaction.response.send_message(response, allowed_mentions=discord.AllowedMentions.none())
```

session 组：
```python
session_group = app_commands.Group(name="session", description="Session management")
@session_group.command(name="status", ...)
@session_group.command(name="reset", ...)
self.tree.add_command(session_group)
```

### Step 5：更新文本命令调用方

`client.py` on_message 中的文本命令拦截改为传 `channel_id`：

```python
response = await handle_operator_command(op_cmd, self, message.channel.id)
```

权限检查也改为调用 `can_run_operator_command`。

### Step 6：更新测试

- `test_commands.py`：适配新签名（channel_id 替代 message）
- 新增 `can_run_operator_command` 测试
- 新增 `_is_channel_allowed` 测试

## 修改文件清单

| 文件 | 改动 |
|------|------|
| `multinexus/commands.py` | handlers 改为 channel_id；新增 can_run_operator_command |
| `multinexus/client.py` | 挂载 CommandTree；setup_hook 注册命令；on_ready guild sync；更新文本命令调用 |
| `tests/test_commands.py` | 适配新签名；新增权限和 channel 检查测试 |

## 注意事项

- Slash command 回复必须加 `allowed_mentions=discord.AllowedMentions.none()`，避免误 ping
- Session scope 始终用 `channel_id`（thread 用自己的 id，不用 parent）
- Channel allowlist 对 thread 检查 parent channel（与 on_message 一致）
- Round 1 不做 embeds，输出控制在 1900 字符内
- 文本命令（@mention）保持兼容，不删除
