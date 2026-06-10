> **Historical record.** Current source of truth: `docs/project-harness/progress.md` and `docs/project-harness/scope.md`. This file is preserved as part of the dogfood development audit chain.

# Plan: Phase 4.5 — Coordinator Agent Handoff Delivery (v3)

## Context

Phase 4.1-4.4 完成：WebhookBus 能发状态广播到 Discord 频道。但这是单向通知——coordinator 不能主动触发 agent 开始工作。

Phase 4.5 的目标：coordinator 通过 Discord webhook 发送 `[handoff] <@BOT_ID>` 消息，触发 multinexus bot 启动 adapter 执行任务。

**参考**：master plan flow B——assignment.requested → policy 生成两种 delivery（status broadcast + agent handoff）→ Discord webhook 发送 → 目标 bot 收到 `[handoff]` + @self → 开始工作。

---

## 当前状态

**已有**：
- WebhookBus（status broadcast，`allowed_mentions: {"parse": []}`）
- `worker.handoff.prepared` 事件（payload 含 `handoff_text`）
- Policy 渲染 `worker.handoff.prepared` 为 `[HANDOFF]` 可见消息
- `discord_webhook` 支持 platform
- 当前 policy 架构：`render_event()` → 单 delivery（message_key = `{workspace_id}:{event_id}:{platform}:{destination}`）

**本 phase 需新增**：
1. WebhookBus mention support（`mention_users` → `allowed_mentions`）
2. Agent registry（workspace `agents_json` 列 + `get_agent_discord_id()`）
3. `--target-agent` 参数 → event payload 追加 `target_agent` + `bootstrap_path`
4. `render_event_deliveries()` 支持 dual delivery（status + agent handoff）
5. Idempotency key 绑定 `target_agent`（不同 target 产生不同 event）
6. Agent handoff delivery 仅限 `discord_webhook` 平台

---

## Design

### 核心思路

一次 `worker.handoff.prepared` 事件产生 **两个** delivery：
- **Status broadcast**：现有逻辑，`[HANDOFF] task_id ...`，无 mention
- **Agent handoff**：新逻辑，`[handoff] <@BOT_ID> task_id=... workspace_id=... bootstrap=...`，只 mention 目标 bot

两者共用同一个 WebhookBus（同一个 webhook URL），但 `allowed_mentions` 不同。

### 1. `--target-agent` 参数（修复 #3）

在 `task handoff` 新增 `--target-agent` 参数，写入 event payload。

```python
# cli.py — task handoff subcommand
task_handoff.add_argument("--target-agent", default=None,
    help="Target agent name for handoff (e.g. mac-codex)")
```

handoff.py 的 `prepare_handoff()` 新增 `target_agent: str | None = None` 参数。当非 None 时，写入 event payload：

```python
# handoff.py — event payload 追加字段
payload = {
    ...existing fields...,
    "target_agent": target_agent,
    "bootstrap_path": bootstrap_recommended_path,
}
```

**Idempotency key 绑定 target_agent**：当前 key 格式为 `{workspace_id}:{task_id}:worker.handoff.prepared:gate_{approved_gate_id}`。Phase 4.5 改为：

```python
target_suffix = f":target_{target_agent}" if target_agent else ""
idempotency_key = f"{workspace_id}:{task_id}:worker.handoff.prepared:gate_{approved_gate_id}{target_suffix}"
```

效果：
- `task handoff --target-agent mac-codex` → key 含 `:target_mac-codex`，产生新 event
- `task handoff`（无 target）→ key 不含 target 后缀，产生新 event
- 同一 task 不同 target 不会复用旧 event，避免拿到不含 `target_agent` 的旧 payload

**注意**：`bootstrap_text` 太大不适合放 event payload，但 `bootstrap_path`（相对路径）必须放进去，policy 渲染时要用。

### 2. Agent Registry（修复 #3）

在 workspace 新增 `agents_json` 列（TEXT, nullable）。

```python
{
    "mac-claude": {"discord_user_id": "1507329791982833775"},
    "mac-codex":  {"discord_user_id": "1507330121235697794"},
    "mac-opencode": {"discord_user_id": "1507326063745957898"}
}
```

**专用 CLI**（修复 #6，避免 `workspace add` 覆盖配置）：

```bash
workspace agent add multinexus --name mac-claude --discord-user-id 1507329791982833775
```

此命令只操作 `agents_json`，不触碰 `default_bus`/`default_destination` 等字段。

**Service**：`get_agent_discord_id(conn, workspace_id, agent_name) -> str | None`

### 3. WebhookBus Mention Support

扩展 `WebhookBus.send()`：检查 `payload` 中的 `mention_users` 字段。

```python
def send(self, *, destination, payload, message_key):
    mention_users = payload.get("mention_users")
    if mention_users:
        allowed_mentions = {"users": mention_users}
    else:
        allowed_mentions = {"parse": []}

    body = {
        "content": message_text(payload),
        "username": "coordinator",
        "allowed_mentions": allowed_mentions,
    }
```

`mention_users` 不进入 Discord message body——它只控制 `allowed_mentions`。`message_text()` 仍然只取 `payload["text"]`。

### 4. Dual Delivery API（修复 #2）

当前 `render_event()` 返回 `RenderEventResult`（单个 payload + message_key）。改为：

**新增 `render_event_deliveries()`**：返回 `list[RenderEventResult]`。

```python
def render_event_deliveries(
    conn: sqlite3.Connection,
    event_id: str,
    *,
    platform: str,
    destination: str,
) -> list[RenderEventResult]:
```

逻辑：
1. 调用现有 `render_event()` 得到 status delivery result（第一个元素）
2. 检查 event_type 是否为 `worker.handoff.prepared` + payload 有 `target_agent`
3. 如果有：查找 agent registry → 构建 agent handoff delivery result（第二个元素）
4. 返回 list

**兼容**：
- `render_event()` 不变，继续返回第一个 delivery
- `create_delivery_for_event()` 不变，继续创建单个 delivery（status）
- **新增 `create_deliveries_for_event()`**：调用 `render_event_deliveries()`，遍历 list 逐一 create_delivery
- `pump_events()` 改为调用 `create_deliveries_for_event()`，返回的 `deliveries` list 包含所有 delivery
- CLI `policy create-delivery` 保持不变（单 delivery，向后兼容）
- CLI `delivery pump` 不变（bus 层 pump，与 policy 层无关）

### 5. Agent Handoff Delivery Renderer（修复 #1, #4）

```python
def _agent_handoff_delivery(conn, event, workspace, *, platform, destination):
    # Agent handoff 仅限 discord_webhook 平台
    if platform != "discord_webhook":
        return None

    target_agent = event["payload"].get("target_agent")
    if not target_agent:
        return None

    discord_id = get_agent_discord_id(conn, workspace["id"], target_agent)
    if not discord_id:
        return None

    task_id = event["payload"]["task_id"]
    workspace_id = event["payload"]["workspace_id"]
    bootstrap_path = event["payload"].get("bootstrap_path", "")

    text = (
        f"[handoff] <@{discord_id}> "
        f"workspace_id={workspace_id} task_id={task_id} "
        f"bootstrap={bootstrap_path} "
        f"action=assignment.accept"
    )

    message_key = f"{workspace_id}:{event['id']}:agent_handoff:{platform}:{destination}"

    return RenderEventResult(
        supported=True,
        event=event,
        payload={"text": text, "mention_users": [discord_id]},
        message_key=message_key,
    )
```

**关键变更**：
- agent_name 来自 `event.payload.target_agent`（由 `--target-agent` 写入），不是 `role`
- bootstrap_path 来自 `event.payload.bootstrap_path`（由 handoff 写入），不是硬编码
- message_key 使用 **event-scoped** 格式（修复 #5）

### 6. Event-scoped message_key（修复 #5）

Status delivery 的 message_key 不变：`{workspace_id}:{event_id}:{platform}:{destination}`

Agent handoff delivery 的 message_key：`{workspace_id}:{event_id}:agent_handoff:{platform}:{destination}`

两者共用 `{event_id}` 前缀，保证：
- 同一事件重新 pump 不会重复发送
- 不同 event（重新 handoff 产生新 event）有不同 key，可以重新派发

### 7. DB Schema

```sql
ALTER TABLE workspaces ADD COLUMN agents_json TEXT;
```

Migration: 在 `initialize()` 中检查列是否存在，不存在则 ALTER TABLE。

### 8. 测试

**tests/test_handoff.py**：
- `test_handoff_payload_includes_target_agent` — `--target-agent` 写入 event payload
- `test_handoff_payload_includes_bootstrap_path` — `bootstrap_path` 写入 event payload
- `test_handoff_without_target_agent_omits_field` — 不传 `--target-agent` 时 payload 无此字段
- `test_handoff_idempotency_key_includes_target_agent` — 不同 target 产生不同 idempotency key
- `test_handoff_different_target_creates_new_event` — 同 task 不同 target 不复用旧 event

**tests/test_bus.py**：
- `test_webhook_send_with_mention_users` — `allowed_mentions` 使用 `{"users": [...]}`
- `test_webhook_send_without_mention_users` — 默认 `{"parse": []}`

**tests/test_policy.py**：
- `test_render_event_deliveries_returns_two_for_handoff_with_target` — 有 target_agent + discord_webhook 返回 2 个
- `test_render_event_deliveries_returns_one_without_target` — 无 target_agent 返回 1 个
- `test_render_event_deliveries_returns_one_on_stdout_platform` — stdout 平台不生成 agent handoff
- `test_agent_handoff_uses_target_agent_not_role` — 用 target_agent 查 registry，不是 role
- `test_agent_handoff_event_scoped_message_key` — message_key 包含 event_id
- `test_agent_handoff_uses_event_bootstrap_path` — bootstrap 来自 event payload
- `test_agent_handoff_discord_webhook_only` — 非 discord_webhook 平台返回 None
- `test_pump_events_creates_both_deliveries` — pump 创建 status + agent handoff
- `test_old_event_without_target_agent_produces_single_delivery` — 旧 event（无 target_agent/bootstrap_path）只生成 status delivery，不报错

**tests/test_db.py**：
- `test_workspace_agents_json_crud` — 存取 agent mapping
- `test_get_agent_discord_id_not_found` — 无匹配返回 None

**tests/test_cli.py**：
- `test_workspace_agent_add_cli` — `workspace agent add` 命令
- `test_task_handoff_target_agent_flag` — `--target-agent` 写入 payload

---

## 实现顺序

1. `db.py` — `agents_json` 列 + `get_agent_discord_id()` + `workspace agent add`
2. `handoff.py` + `cli.py` — `--target-agent` 参数 + event payload 追加 `target_agent`/`bootstrap_path`
3. `bus.py` — WebhookBus mention_users 支持
4. `policy.py` — `render_event_deliveries()` + `_agent_handoff_delivery()` + `pump_events()` 改用新 API
5. Tests for each layer
6. E2E 验证

---

## Verification

```bash
cd /Users/yinxin/projects/multi-agent-coordinator
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'

# 1. 注册 agent（专用命令，不覆盖 workspace 配置）
PYTHONPATH=src python3 -m multi_agent_coordinator --db ~/.multi-agent-coordinator/coordinator.sqlite3 \
  workspace agent add multinexus --name mac-codex --discord-user-id 1507330121235697794

# 2. 触发 handoff（指定目标 agent）
PYTHONPATH=src python3 -m multi_agent_coordinator --db ~/.multi-agent-coordinator/coordinator.sqlite3 \
  task handoff multinexus --task-id phase-4-coordinator-integration \
  --role worker --target-agent mac-codex

# 3. 创建 delivery（应生成两个）
PYTHONPATH=src python3 -m multi_agent_coordinator --db ~/.multi-agent-coordinator/coordinator.sqlite3 \
  policy pump-events --workspace-id multinexus --platform discord_webhook --destination ""

# 4. 发送
DISCORD_WEBHOOK_URL="..." PYTHONPATH=src python3 -m multi_agent_coordinator \
  --db ~/.multi-agent-coordinator/coordinator.sqlite3 \
  delivery pump --platform discord_webhook
```
