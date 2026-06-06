# Agent Session 持久化设计

## 背景

当前 MultiNexus/MultiNexus 已经能把 Discord 消息路由到不同 coding agent，并通过 adapter 调用 Claude、Codex、OpenCode 等 CLI。但 agent 会话的生命周期还没有形成稳定设计。

两个极端方案都不理想：

- **每条消息新开 session**：上下文干净，但 agent 每次都要重新理解项目、重复读代码，工程任务会变慢。
- **每个 agent 永久固定一个 session**：短期方便，但不同任务、不同项目、不同用户上下文会混在一起，时间长了必然污染和爆上下文。

推荐方案是：**按任务维度持久化 session**。

## 目标

一个工程任务内，agent 应该能连续工作；不同工程任务之间，agent 上下文应该隔离。

核心关系：

```text
workspace_id + task_id + agent_id -> cli_session_id
```

在 Discord 层可以先退化为：

```text
discord_thread_id + agent_id -> cli_session_id
```

长期设计应以 coordinator task 为主，Discord thread 只是这个 task 的可视化工作区。

当前落地的 SQLite `sessions.scope_id` 采用统一 key：

```text
channel:<channel_id>
thread:<thread_id>
task:<workspace_id>:<task_id>
```

读取时按当前语义优先使用上述 canonical key；旧版纯数字 channel/thread scope 只作为兼容 fallback，命中后会在下一次成功调用时迁移到 canonical scope。

## 非目标

- 不把所有 agent 合并成一个共享 session。
- 不让 agent 直接维护全局长期记忆。
- 不把 session id 写进 prompt 作为主要控制方式。
- 不绕过 coordinator/harness 直接修改任务状态文件。

## Session 归属模型

推荐语义：

```text
一个 coordinator task / Discord thread
+ 一个 agent
= 一个可恢复 CLI session
```

示例：

```text
workspace_id: multinexus
task_id: fix-opencode-handoff-timeout
discord_thread_id: 1507...
agent_id: mac-opencode
adapter: opencode
work_dir: /Users/yinxin/projects/multinexus
cli_session_id: ses_...
```

同一个 task 里：

- `mac-claude` 有自己的 session。
- `mac-codex` 有自己的 session。
- `mac-opencode` 有自己的 session。

它们共享任务语义，但不共享底层 CLI session。

## 建议数据模型

短期可以放在 `multinexus` 的 SQLite。长期建议迁入 `multi-agent-coordinator`，因为 coordinator 才是工程控制面。

```sql
CREATE TABLE agent_sessions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT,
    task_id TEXT,
    discord_channel_id TEXT,
    discord_thread_id TEXT,
    agent_id TEXT NOT NULL,
    adapter TEXT NOT NULL,
    work_dir TEXT,
    cli_session_id TEXT,
    generation INTEGER NOT NULL DEFAULT 1,
    summary TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    closed_at_ms INTEGER
);
```

建议约束：

```sql
CREATE UNIQUE INDEX idx_agent_sessions_task_agent
ON agent_sessions(workspace_id, task_id, agent_id, generation)
WHERE task_id IS NOT NULL;

CREATE UNIQUE INDEX idx_agent_sessions_thread_agent
ON agent_sessions(discord_thread_id, agent_id, generation)
WHERE discord_thread_id IS NOT NULL;
```

状态含义：

| status | 含义 |
|--------|------|
| active | 当前可恢复 |
| closed | 任务完成后关闭 |
| stale | resume 失败或底层 session 不再可用 |
| archived | coordinator closeout/done 后归档，不再用于 resume |
| failed | adapter 多次失败，需要人工处理 |

## Adapter 约定

每个支持持久化的 adapter 应提供两个能力：

```python
call(prompt, *, work_dir, ...)
resume(session_id, prompt, *, work_dir, ...)
```

返回结果应包含：

```python
{
    "text": "...",
    "cli_session_id": "...",
    "adapter": "claude|codex|opencode",
}
```

不要把 session id 塞进 prompt 作为控制指令。session id 应该通过对应 CLI 的正式参数传递。

### Claude

新会话：

```bash
claude -p --verbose --output-format stream-json ...
```

从 JSON 事件中读取 `session_id`。

恢复：

```bash
claude -p --resume <session_id> --verbose --output-format stream-json ...
```

prompt 仍然通过 stdin 传入。

### Codex

新会话：

```bash
codex exec --json -
```

从 `session_meta.payload.id` 读取 session id。

恢复：

```bash
codex resume <session_id> --json -
```

prompt 通过 stdin 传入。

### OpenCode

新会话：

```bash
opencode run --format json ...
```

从 JSON event 的 `sessionID` 读取 session id。

恢复：

```bash
opencode run --session <session_id> --format json ...
```

需要实测 `--session` 与 `--continue` 的具体行为。若 `--session` 不适合当前版本，则 adapter 应记录实际可用参数，而不是靠 prompt 模拟恢复。

OpenCode 还需要特别注意：

- 子进程 `cwd` 和 env 里的 `PWD` 必须一致。
- `work_dir` 应尽量指向具体 repo，而不是 `~/projects` 这种父目录。
- 必须有 first-byte timeout 和 activity timeout，不能只靠总超时。

## Discord 路由规则

### 主频道普通消息

用户在主频道直接 `@Agent`：

- 使用 `channel:<channel_id>` scope。
- 若存在 active session，则 resume。
- 若不存在，则 fresh call，并保存返回的 `cli_session_id`。

### Discord thread 内消息

用户在 thread 内 `@Agent`：

- 使用 `thread:<thread_id>` scope，不使用 parent channel 作为 session scope。
- 若存在 active session，则 resume。
- 若不存在，则 fresh call，并保存返回的 `cli_session_id`。

### Coordinator task 消息

如果消息关联 coordinator task：

- 优先使用 `task:<workspace_id>:<task_id>` scope。
- Discord thread 只作为这个 task 的 UI 容器。
- `assignment.closeout`、`assignment.mark-done` 或 `task.done` lifecycle notice 只会让 multinexus 归档本地 task session，不会从 Discord 文本执行 coordinator 生命周期变更。
- task session 归档后不再 resume；同一 task 后续再次 handoff 会 fresh call 并写入新的 active session。

### Handoff

`[handoff] @AgentName ...` 应继承当前 task/thread 语义：

- 目标 agent 使用同一个 `workspace_id/task_id`。
- 但目标 agent 拥有自己的 `cli_session_id`。
- 如果目标 agent 第一次参与此 task，则创建新 session。

## Prompt 与 Session 的分工

Session 负责：

- agent 在同一个任务内的连续推理状态。
- 已读代码、已形成的任务上下文。
- CLI 工具自己的内部历史。

Prompt 负责：

- 当前用户请求。
- 当前 thread 中必要的最近消息。
- coordinator task 状态摘要。
- handoff 任务描述。

不要把所有历史都重复塞进 prompt。恢复 session 后，prompt 应更短、更明确。

建议恢复时 prompt 结构：

```text
[Task Context]
workspace_id: ...
task_id: ...
thread_id: ...
work_dir: ...
current_status: ...

[Recent Discord Context]
...

[Current Message]
...
```

## Session Rollover

即使 task-scoped session，也会遇到上下文过长。需要 rollover 机制。

触发条件：

- session 年龄超过阈值。
- CLI 报 context limit。
- resume 多次失败。
- task 进入新阶段，例如从实现转 review。

处理方式：

1. 让当前 agent 生成任务摘要。
2. 将旧 session 标记为 `stale` 或 `closed`。
3. 创建 `generation + 1` 的新 session。
4. 新 session 首次 prompt 注入上一代 summary。

示例：

```text
generation 1: 实现阶段
generation 2: 修 bug 阶段，带 generation 1 summary
generation 3: closeout 阶段，带前两代摘要
```

## 与 Coordinator 的关系

Coordinator 的角色类似控制面，不等同于 MCP，但理念相近：

- MCP 把 API 包装成 AI 可调用的工具，避免 AI 猜参数。
- Coordinator 把工程状态变更包装成 CLI/service，避免 AI 直接改 JSON、SQLite 或 harness 文件。

因此 session 最终应该进入 coordinator 的控制范围：

```text
agent session
task mirror
branch allocation
PR link
CI status
review gate
delivery outbox
```

这些都应该能被审计、恢复、重试。

长期可以再为 coordinator 提供 MCP server，让 AI 直接调用：

```text
coordinator.assignment_request
coordinator.branch_allocate
coordinator.pr_link
coordinator.session_get_or_create
coordinator.session_close
```

但 MCP 是调用界面，coordinator 仍是状态权威。

## 最小落地计划

### Phase A：multinexus thread-scoped session

1. 在 `ChatContextStore` 或独立 SQLite 中增加 `agent_sessions` 表。
2. Claude/Codex/OpenCode adapter 返回 `cli_session_id`。
3. adapter 增加 `resume(session_id, prompt, work_dir)`。
4. `DiscordClient` 按 `discord_thread_id + agent_id` 查找 session。
5. resume 失败时 fallback fresh call，并把旧 session 标记 `stale`。

验收：

- 同一个 Discord thread 内第二次 @同一个 agent 会 resume 旧 session。
- 不同 thread 不共享 session。
- session id 能在本地 DB 中查到。

### Phase B：coordinator task-scoped session

1. coordinator 增加 session service。
2. session 绑定 `workspace_id + task_id + agent_id`。
3. Discord thread 和 coordinator task 建立映射。
4. `[handoff]` 消息继承 task id。
5. task closeout 自动关闭 sessions。

验收：

- 同一个 task 中不同 agent 分别有独立 session。
- handoff 后目标 agent 能绑定同一 task。
- task 完成后 session 不再被误用。

### Phase C：rollover 与 summary

1. 记录 session generation。
2. 增加 session summary 字段。
3. context limit 或 resume failure 时创建新 generation。
4. 新 generation 首次 prompt 注入 summary。

验收：

- 长任务不会无限复用一个过大的 session。
- rollover 后 agent 仍能继续任务。
- DB 能看到 session generation 历史。

## 当前应优先修复的问题

在实现 session 持久化前，先修以下基础问题：

1. OpenCode adapter 子进程 env 的 `PWD` 必须等于实际 `cwd`。
2. OpenCode adapter 必须加 first-byte/activity timeout。
3. `work_dir` 配置应支持按项目或 task 动态选择。
4. `recent_messages()` 应支持只取当前消息之前的历史，避免重放旧消息时被未来消息污染。
5. `handoff_dedupe_seconds` 应真正接入 `client.py`，避免重复 handoff 反复触发。

这些是 session 持久化之前的前置稳定性工作。

## 推荐结论

最终形态：

```text
coordinator task = 工程事实
Discord thread = 人和 agent 的可视化工作区
agent session = 某个 agent 在某个 task 内的连续执行状态
```

不要使用 agent 全局永久 session。  
不要让每条消息都新开 session。  
使用 task-scoped session，并用 summary + generation 控制生命周期。
