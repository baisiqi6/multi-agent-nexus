# discord-nexus 定制修改记录

基于原版 discord-nexus 做的修改和优化，记录在此以便追踪和后续升级。

---

## 1. Agent 对话历史标注来源

**文件**: `cogs/agents.py` 第 849 行

**原问题**: 所有 agent 回复都以 `role: "assistant"` 保存到 conversations 表，没有区分是哪个 agent 说的。同一频道内多个 agent 共享对话历史，但无法识别消息来源。

**修改**: 保存 assistant 消息时加上 agent 名字前缀：
```python
# 原:
await self.bot.db.save_message(thread_id, "assistant", clean_response)
# 改:
await self.bot.db.save_message(thread_id, "assistant", f"[{agent_name}]: {clean_response}")
```

**效果**: Claude 能看到 `[codex]: ...` 的历史消息，知道是 Codex 说的；反之亦然。

---

## 2. Agent 配置适配

**文件**: `config.yaml`, `.env`

**改动**:
- `display_name` 改为 Discord webhook 名字：`Mac 小龙虾`、`Mac Claude`、`Mac Codex`
- `mac-openclaw.inference_backend` 改为 `openclaw`（走 OpenClaw CLI，而非直连 LM Studio）
- `mac-openclaw.model` 设为 `astron-code-latest`（讯飞 MaaS 模型）
- `.env` 添加 `OPENCLAW_GATEWAY_TOKEN`
- system_prompt 里的 agent 引用从 "Local Agent" 改为 "小龙虾"
- `agent_roles` 清空（暂未创建 Discord 角色）

**原因**: Mac 上不跑本地模型，小龙虾走 OpenClaw gateway（讯飞 MaaS API）。

---

## 3. Webhook 命名对齐

**原问题**: Bot 自动创建 webhook 时使用 `display_name` 作为 webhook 名字。手动创建的 webhook 需要名字一致才能被复用。

**改动**: config.yaml 的 `display_name` 与 Discord 频道里手动创建的 webhook 名字对齐：
- `Mac 小龙虾` → `mac-openclaw`
- `Mac Claude` → claude
- `Mac Codex` → codex

**效果**: Bot 启动时通过 Discord API 查找已有 webhook，按名字匹配复用，不会重复创建。

---

## 4. 频道 ID 配置

**文件**: `config.yaml`

所有频道 ID 统一设为 `1503350765295767623`（#multinexus），包括：
- general, llm-claude, llm-codex, llm-local, coding
- logs, alerts, discoveries, handoffs
- 各 agent 的 active channels

后续可拆分为独立频道。

---

## 5. Bot 权限

在 Discord Developer Portal 创建 bot 时勾选的权限：
- Send Messages
- Manage Webhooks（自动创建/查找 webhook 必需）
- Read Message History
- Attach Files
- Embed Links
- Use Application Commands

---

## 待做

- [ ] 创建 Discord 角色（@Claude、@Codex、@小龙虾），配到 `agent_roles`
- [ ] 拆分独立频道（logs、discoveries、handoffs 等）
- [ ] 配置 `projects` 路径，让 agent 在特定项目目录下工作
- [ ] 考虑给 @bot 直接发消息时触发默认 agent（目前只响应 !bang 和 @role）
- [x] 自动 compaction：历史超过 budget 时用小龙虾做摘要压缩

---

## 6. !clear 命令

**文件**: `bot.py`, `persistence/db.py`

**功能**: `!clear` 清空当前频道在 discord-nexus 数据库里的对话历史，Discord 频道消息不受影响。

**实现**:
- `db.py` 新增 `clear_history(thread_id)` 方法，DELETE conversations 表中对应频道记录
- `bot.py` 的 `on_message` 里检测 `!clear`，调用后回复删除数量

---

## 7. Researcher agent 禁用

**文件**: `bot.py`, `config.yaml`, `routing/dispatcher.py`

**原因**: Claude、Codex、小龙虾都有各自的搜索工具（WebSearch/WebFetch/SearXNG），不需要 researcher 中间层。

**改动**:
- bot.py 里 researcher 注册代码注释掉
- config.yaml 里 researcher 配置注释掉
- dispatcher.py 里移除 researcher 的 BANG_ALIASES 条目
- RESEARCH 标签逻辑保留但静默忽略（researcher agent 不注册，返回 None）

---

## 8. 小龙虾 !bang 别名

**文件**: `routing/dispatcher.py`

**新增别名**: `!小龙虾`、`!openclaw`、`!龙虾` 都路由到 `mac-openclaw`

**完整 !bang 命令表**:

| 命令 | Agent |
|------|-------|
| `!claude` / `!c` | Claude |
| `!codex` / `!g` | Codex |
| `!mac-openclaw` / `!local-agent` / `!m` / `!小龙虾` / `!openclaw` / `!龙虾` | 小龙虾 |
| `!all` / `!a` | 全部 agent |
| `!clear` | 清空频道上下文 |

---

## 9. Managed Context 上下文管理

**文件**: `cogs/agents.py`, `persistence/db.py`, `config.yaml.example`

**原问题**: 旧逻辑只按 `history_budget_chars` 从最近消息开始粗暴截断。频道对话稍长后，早期关键决策会直接丢失，而无关近消息可能继续占用 context window。

**改动**:
- `persistence/db.py` 新增 `conversation_summaries` 表，保存每个 thread 的 compacted summary。
- `cogs/agents.py` 新增 managed context 流程：TTL 过滤、超过阈值后 compaction、最终发送 `summary + recent raw history`。
- compaction 默认调用 `mac-openclaw`，并使用独立 `discord-nexus-context:<thread_id>` session，避免污染正常小龙虾对话。
- Claude/Codex resume 路径现在也会收到整理后的 Discord conversation context。

**默认配置**:
```yaml
conversation:
  managed_context_enabled: true
  context_ttl_hours: 24
  compact_threshold_chars: 12000
  summary_budget_chars: 4000
  recent_budget_chars: 8000
```

**效果**: 接近 OpenClaw 的三层上下文策略，但实现上留在 discord-nexus 内部，避免依赖 OpenClaw 未公开的 context builder API。
