# Phase 3.1：运行可维护性 — Operator Commands

## 背景

Phase 2.5 完成了 session 持久化和 handoff 链路验证，57 个测试通过，所有 handoff 路径双向验证。但真实运行时，session 出问题只能查 SQLite 或看日志，无法在 Discord 里直接排障。

Phase 3.1 目标：补齐最小运行时排障能力，不碰 wiki/scratch/embeds/coordinator。

## 命令设计

所有 operator commands 通过 **@mention + 命令文本** 触发，不走 adapter（不发给 LLM）。

| 命令 | 权限 | 效果 |
|------|------|------|
| `@bot session status` | allowed_user_ids（空=所有人） | 显示当前 scope 的 session 信息 |
| `@bot session reset` | allowed_user_ids **非空且命中** | 标记当前 scope 的 session 为 stale |
| `@bot agents` | allowed_user_ids（空=所有人） | 列出所有已知 agents（区分 managed/external） |
| `@bot health` | allowed_user_ids（空=所有人） | 执行 adapter health check |

触发条件：
- 必须是**人类消息**（`message.author.bot == False`）
- 必须 **addressed to bot**：@mention 或 !bang（`_is_addressed_to_me` 判断）
- 消息内容（去掉 mention/bang 后）匹配命令关键词
- `session reset` 额外要求 `allowed_user_ids` 非空且命中

不触发条件：
- Bot 消息不触发 operator commands
- 不需要 `[handoff]` 前缀
- 不匹配 operator command 的普通消息照常走 adapter

## 修改文件清单

| 文件 | 改动 |
|------|------|
| `multinexus/models.py` | KnownAgentMention 增加 `kind` 字段 |
| `multinexus/config.py` | 加载时正确填充 kind="managed" / "external" |
| `multinexus/sessions/store.py` | 添加 `list_by_agent()` 方法 |
| `multinexus/commands.py` | **新建** — 命令检测 + 执行 |
| `multinexus/client.py` | on_message 人类分支插入拦截 |
| `tests/test_commands.py` | **新建** — 命令检测、输出、client 拦截测试 |

## 实现步骤

### Step 1：KnownAgentMention 增加 kind 字段

`multinexus/models.py`：

```python
@dataclass
class KnownAgentMention:
    id: str
    primary_name: str = ""
    names: set[str] = field(default_factory=set)
    role_ids: set[str] = field(default_factory=set)
    discord_user_id: int | None = None
    kind: str = "managed"  # "managed" | "external"
```

`multinexus/config.py`：
- `_build_toml_roster()` 构建 managed agents 时设 `kind="managed"`
- `_build_external_agents()` 构建 external agents 时设 `kind="external"`

这样 `agents` 命令就能区分输出，不靠猜。

### Step 2：SessionStore.list_by_agent

`multinexus/sessions/store.py` 新增：

```python
def list_by_agent(self, *, agent_id: str, include_stale: bool = False) -> list[dict]:
    """列出某个 agent 的所有 sessions。默认只返回 active。"""
    with self._connect() as conn:
        if include_stale:
            rows = conn.execute(
                "SELECT scope_id, agent_id, adapter, session_id, work_dir, "
                "status, turn_count, created_at, updated_at "
                "FROM sessions WHERE agent_id = ? ORDER BY updated_at DESC",
                (agent_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT scope_id, agent_id, adapter, session_id, work_dir, "
                "status, turn_count, created_at, updated_at "
                "FROM sessions WHERE agent_id = ? AND status = 'active' ORDER BY updated_at DESC",
                (agent_id,),
            ).fetchall()
    return [_row_to_dict(row) for row in rows]
```

把现有 `get()` 里的 dict 构建抽取为 `_row_to_dict(row)` 复用。

### Step 3：新建 commands.py

`multinexus/commands.py`：

```python
OPERATOR_COMMANDS = {"session status", "session reset", "agents", "health"}

def parse_operator_command(text: str) -> str | None:
    """检查去掉 @mention 后的文本是否是 operator command。"""
    cleaned = text.strip().lower()
    for cmd in OPERATOR_COMMANDS:
        if cleaned == cmd:
            return cmd
    return None

def is_dangerous_command(cmd: str) -> bool:
    """需要严格权限的命令（破坏性操作）。"""
    return cmd == "session reset"
```

各命令 handler（在 `handle_operator_command` 里分发）：

**session status：**
- `scope_id = str(message.channel.id)` — thread 用自己的 id，**不使用 parent**
- 先 `session_store.get(scope_id, agent_id)` 获取当前 scope
- 再 `session_store.list_by_agent(agent_id)` 获取总览
- 无 active session 时显示 "No active session in this scope"
- 输出格式：
  ```
  Session Status — mac-claude

  Current scope (channel 12345):
    session_id: abc123...
    adapter: claude
    work_dir: /Users/yinxin/projects
    status: active
    turns: 5
    updated: 2026-05-27 14:30

  Active sessions: 2 total
  ```

**session reset：**
- `scope_id = str(message.channel.id)`
- 先 `get()` 检查是否有 active session
- 有 → `mark_stale()`，回复确认
- 没有 → 回复 "No active session in this scope"
- 输出格式：
  ```
  Session reset — mac-claude

  Marked session in scope 12345 as stale.
  Next call will start fresh.
  ```

**agents：**
- 读 `client.agent_config.known_agents`
- 按 `kind` 分组显示 managed / external
- 每个 agent 显示 id、primary_name、Discord mention
- 输出格式：
  ```
  Known Agents

  Managed:
    mac-claude (Mclaucode) — <@1507329791982833775>
    mac-codex (Mac Codex) — <@1507330121235697794>

  External:
    mac-openclaw (小龙虾) — <@1503023508836450477>
    server-hermes (Hermes) — <@1505562531706568928>
  ```

**health：**
- 调 `client.adapter.health_check()`
- 附带 config 信息（work_dir、model、timeout）
- 输出格式：
  ```
  Health Check — mac-claude

  adapter: claude
  bin: claude
  available: yes (/Users/yinxin/.claude/local/claude)
  work_dir: /Users/yinxin/projects
  model: sonnet
  timeout: 360s
  ```

输出控制在 Discord 消息长度内（1900 字符）。`handle_operator_command()` 返回字符串，由 client.py 负责发送和分片。不直接 import client.py 的 `_chunk_message`，避免循环依赖。

### Step 4：修改 client.py on_message

在 `multinexus/client.py` 的 `on_message` 方法中，人类消息分支（line 131-139）。

在 `_is_addressed_to_me` 返回 true 之后、`_handle_request` 之前插入拦截：

```python
if self._is_addressed_to_me(message):
    # Operator command 拦截
    prompt_text = self._get_prompt_text(message)
    op_cmd = parse_operator_command(prompt_text)
    if op_cmd:
        if is_dangerous_command(op_cmd):
            if not self.agent_config.allowed_user_ids or message.author.id not in self.agent_config.allowed_user_ids:
                await message.channel.send("Unauthorized: this command requires explicit operator permission.")
                return
        self._record_message(message)
        response = await handle_operator_command(op_cmd, self, message)
        await message.channel.send(response)
        return
    # 正常走 adapter
    self._record_message(message)
    await self._handle_request(message)
else:
    self._record_message(message)
```

### Step 5：测试

**tests/test_commands.py：**

命令检测测试：
- `parse_operator_command("session status")` → "session status"
- `parse_operator_command("agents")` → "agents"
- `parse_operator_command("health")` → "health"
- `parse_operator_command("session reset")` → "session reset"
- `parse_operator_command("你好")` → None
- `parse_operator_command("session")` → None（不完整匹配）
- `is_dangerous_command("session reset")` → True
- `is_dangerous_command("session status")` → False

命令输出测试（mock client 和 stores）：
- session status 有 active session → 包含 session_id 和 turns
- session status 无 active session → "No active session in this scope"
- session reset 有 active session → mark_stale 被调用，输出确认
- session reset 无 active session → "No active session in this scope"
- agents → 包含 managed 和 external 分组
- health → 包含 adapter 和 available

Client 拦截测试：
- mock adapter，发 `@bot session status` → adapter.call() **未被调用**
- mock adapter，发 `@bot 你好` → adapter.call() **被调用**
- bot 消息含 `session status` → 不触发 operator command

## 验证

1. `python -m unittest discover tests/` — 57+ 现有测试 + 新测试全部通过
2. 启动 bot，Discord 中测试：
   - `@Mac Claude session status` → 显示 session 信息
   - `@Mac Claude session reset` → stale 确认（需权限）
   - `@Mac Claude agents` → agent 列表（分 managed/external）
   - `@Mac Claude health` → health check
   - `@Mac Claude 你好` → 正常走 adapter，不被拦截
3. session reset 后 `@Mac Claude session status` → 显示 "No active session in this scope"

## 不做的事

- 不引入 Discord slash commands（Phase 3.2）
- 不引入 embeds（Phase 3.2）
- 不碰 wiki / scratch / discoveries
- 不碰 coordinator 集成
- 不改变 session 持久化策略
