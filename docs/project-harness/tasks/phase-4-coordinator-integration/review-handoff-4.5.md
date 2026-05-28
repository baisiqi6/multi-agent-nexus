# Review Handoff: Phase 4.5 — Agent Handoff Delivery (v3)

## 任务概要

Phase 4.5 在 Phase 4.1-4.4（WebhookBus + worker bootstrap）基础上，实现 coordinator 主动向 Discord 频道中的 agent 派发任务。

**核心变更**：`worker.handoff.prepared` 事件触发时，生成两种 delivery：
1. Status broadcast（现有，无 mention）
2. Agent handoff（新增，`[handoff] <@BOT_ID>` 格式，mention 目标 bot）

## 修改文件清单

### multi-agent-coordinator（coordinator 项目）

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/multi_agent_coordinator/db.py` | 修改 | workspaces 表新增 `agents_json` 列；新增 `get_agent_discord_id()` |
| `src/multi_agent_coordinator/handoff.py` | 修改 | `prepare_handoff()` 新增 `target_agent` 参数；event payload 追加 `target_agent` + `bootstrap_path`；idempotency key 绑定 target_agent |
| `src/multi_agent_coordinator/bus.py` | 修改 | WebhookBus.send() 支持 `mention_users` payload 字段 |
| `src/multi_agent_coordinator/policy.py` | 修改 | 新增 `render_event_deliveries()` 返回 list；新增 `_agent_handoff_delivery()` 渲染器（仅限 discord_webhook）；`pump_events()` 改用新 API |
| `src/multi_agent_coordinator/cli.py` | 修改 | `task handoff` 新增 `--target-agent`；新增 `workspace agent add` 子命令 |
| `tests/test_handoff.py` | 修改 | 5 个新测试：target_agent 写入 payload、bootstrap_path 写入 payload、无 target 省略字段、idempotency key 含 target、不同 target 产生新 event |
| `tests/test_bus.py` | 修改 | 2 个新测试：mention / no-mention 场景 |
| `tests/test_policy.py` | 修改 | 9 个新测试：dual delivery、单 delivery、stdout 平台跳过 agent handoff、target_agent 来源、event-scoped key、bootstrap 路径、discord_webhook only、pump 双创建、旧 event 兼容 |
| `tests/test_db.py` | 修改 | 2 个新测试：agents_json CRUD、get_agent_discord_id not found |
| `tests/test_cli.py` | 修改 | 2 个新测试：workspace agent add CLI、--target-agent flag |

### discord-nexus（本项目）

无代码变更。Phase 4.5 纯粹是 coordinator 侧功能。

## 设计决策

### 1. `--target-agent` 而非 `--role` 做映射（修复 reviewer v1 高优 #1）

**选择**：`task handoff --role worker --target-agent mac-codex`
**理由**：`--role` 是角色类型（worker/reviewer），不是 agent 标识。registry 里是 `mac-claude`/`mac-codex` 等，`role=worker` 查不到任何 bot。`--target-agent` 明确指定目标 agent，写入 event payload 的 `target_agent` 字段。policy 用此字段查 registry。

### 2. Idempotency key 绑定 target_agent（修复 reviewer v2 高优 #1）

**选择**：key 格式改为 `{workspace_id}:{task_id}:worker.handoff.prepared:gate_{approved_gate_id}:target_{target_agent}`
**理由**：旧 key 不含 target_agent，导致 `task handoff`（无 target）后再 `task handoff --target-agent mac-codex` 会复用旧 event（payload 无 target_agent），agent handoff delivery 被跳过。新 key 保证不同 target 产生不同 event。无 target 时不加 target 后缀。

### 3. Agent handoff 仅限 discord_webhook 平台（修复 reviewer v2 高优 #2）

**选择**：`_agent_handoff_delivery()` 开头检查 `if platform != "discord_webhook": return None`
**理由**：agent handoff 消息含 Discord mention 协议（`<@ID>`），泄露到 stdout/KOOK 平台无意义且可能产生格式错误。Status delivery 仍可在所有平台正常生成。

### 4. `render_event_deliveries()` 返回 list（修复 reviewer v1 高优 #2）

**选择**：新增内部函数返回 `list[RenderEventResult]`，不修改 `render_event()` 签名
**理由**：
- `render_event()` 和 `create_delivery_for_event()` 保持不变，向后兼容
- 新增 `create_deliveries_for_event()` 调用 `render_event_deliveries()` + 逐一 create_delivery
- `pump_events()` 改用 `create_deliveries_for_event()`
- CLI `policy create-delivery` 保持单 delivery 不变

### 5. Event-scoped message_key（修复 reviewer v1 高优 #3）

**选择**：
- Status delivery：`{workspace_id}:{event_id}:{platform}:{destination}`（不变）
- Agent handoff delivery：`{workspace_id}:{event_id}:agent_handoff:{platform}:{destination}`

**理由**：与现有 message_key 格式一致（都含 event_id），重新 handoff 产生新 event 就有新 key，不会阻止重新派发。

### 6. Bootstrap path 来自 event payload（修复 reviewer v1 中优 #4）

**选择**：`prepare_handoff()` 把 `bootstrap_recommended_path` 写入 event payload 的 `bootstrap_path` 字段
**理由**：实际 bootstrap 文件路径是 `{harness_rel}/tasks/{task_id}/worker-bootstrap.md`（harness_rel 是相对于 workspace.path 的路径），硬编码 `tasks/{task_id}/...` 会漏掉 harness_rel 前缀。

### 7. 专用 `workspace agent add` 命令（修复 reviewer v1 中优 #6）

**选择**：新增 `workspace agent add <workspace_id> --name <agent> --discord-user-id <id>` 子命令
**理由**：`workspace add` 需要必填 `--path` 和 `--harness-root`，且可能覆盖 `default_bus`/`default_destination`。专用命令只操作 `agents_json` 列，安全追加不覆盖。

### 8. Agent Registry 存储位置

**选择**：`workspaces.agents_json`（JSON 列）
**理由**：agent 映射是 workspace 级别配置——不同 workspace 对应不同 Discord server，agent ID 不同。不单独建表，避免 schema 复杂化。

## 向后兼容

- `agents_json` 列 nullable，无 registry 时行为与 Phase 4.1-4.4 完全一致
- WebhookBus 无 `mention_users` 时保持 `{"parse": []}` 行为不变
- `render_event()` / `create_delivery_for_event()` 不变，旧 CLI 调用不受影响
- `--target-agent` 可选参数，不传时不生成 agent handoff delivery
- 旧 `worker.handoff.prepared` event（无 target_agent/bootstrap_path）只生成 status delivery，不报错
- Agent handoff delivery 仅 `discord_webhook` 平台生成，stdout/KOOK pump 不受影响

## v2 → v3 变更对照

| 问题 | v2 | v3 |
|------|----|----|
| Idempotency key | 不含 target_agent，不同 target 复用旧 event | key 追加 `:target_{agent}`，不同 target 产生不同 event |
| Agent handoff 平台 | 未限制，可能在 stdout/KOOK 生成含 `<@discord_id>` 的消息 | 仅 `discord_webhook` 平台生成，其他平台跳过 |
| 当前状态描述 | "已有"含 target_agent/bootstrap_path 但"缺口"又说缺 | 改为"已有"只列 handoff_text，"本 phase 需新增"列 target_agent/bootstrap_path 等 |
| 旧 event 兼容测试 | 无 | 新增：旧 event（无 target_agent）只生成 status delivery |

## v1 → v2 变更对照（历史）

| 问题 | v1 | v2 |
|------|----|----|
| agent 映射来源 | `role` 字段 | `--target-agent` 参数 → `target_agent` payload 字段 |
| 双 delivery API | 未说明 render_event 怎么改 | 新增 `render_event_deliveries()` 返回 list，旧 API 不变 |
| message_key | `agent_handoff:{workspace_id}:{task_id}` | `{workspace_id}:{event_id}:agent_handoff:{platform}:{destination}` |
| bootstrap 路径 | 硬编码 `tasks/{task_id}/...` | 从 event payload `bootstrap_path` 读取 |
| event payload 状态描述 | 说"含 bootstrap_text" | 改为"含 `handoff_text`/`target_agent`/`bootstrap_path`" |
| agent 注册 CLI | `workspace add --agent` | 专用 `workspace agent add` 命令 |

## 风险

- **Discord mention 权限**：webhook 需要 mention 目标 bot 的权限。如果 bot 设置不允许被 mention，消息会发但 @ping 不生效。需要在 E2E 阶段验证。
- **agents_json 手动维护**：agent 注册目前通过 CLI 手动添加。后续可考虑从 agents.toml 自动同步。

## 验证方式

1. 单元测试：`PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`
2. E2E：`workspace agent add` → `task handoff --target-agent` → `policy pump-events` → `delivery pump` → 检查 Discord 频道是否出现 `[handoff] <@BOT_ID>` 消息

## 参考

- 详细计划：`plan-4.5.md`
- Phase 4 计划：`plan.md`
- Phase 4 review 反馈：`review-feedback-2026-05-29-codex.md`
- agents.toml 中 agent discord_user_id 数据源
