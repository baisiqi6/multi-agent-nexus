# Discord 卡片与消息中文化计划

**状态**：parked（2026-06-18 创建，待执行）
**预估总时长**：A+B 共 45 分钟；A+B+C 共 1.5 小时；D 单独评估

## 背景

当前 Discord bot 输出的 embed 卡片和状态消息**中英文混杂**，对中文用户不友好。已经做完 `CLAUDE.md` 中文化、`deploy-server.sh` 跨平台化，bot 用户可见文案是下一个明显的杠杆点。

## 改造范围（4 个层次，按 ROI 排序）

### A. `multinexus/embeds.py` 字段名翻译（高 ROI，30 分钟）

**现状**：标题已经是中文（"可用 Agent"、"健康检查"、"会话状态"），但 `add_field` 的 name 字段大量英文。

**需要翻译的字段名**（来自 `grep 'embed.add_field'`）：

| 当前（英文）| 建议（中文）| 备注 |
|---|---|---|
| `adapter` | `适配器` | 保留 adapter 名（claude/codex/...）原文 |
| `available` | `可用` | value 已经是 "是"/"否" |
| `bin` | `可执行文件` | value 是路径，原样保留 |
| `error` | `错误` | |
| `model` | `模型` | |
| `path` | `路径` | |
| `scope` | `scope` | 保留，是多 agent 系统术语 |
| `scope_type` | `scope 类型` | 同上 |
| `status` | `状态` | |
| `timeout` | `超时` | |
| `work_dir` | `工作目录` | |

**已是中文、不动**：`托管 Agent` / `外部 Gateway Agent` / `活跃会话` / `轮次`

**示例 diff**：
```python
# Before
embed.add_field(name="adapter", value=health.get("adapter", "?"), inline=True)
embed.add_field(name="available", value="是" if available else "否", inline=True)

# After
embed.add_field(name="适配器", value=health.get("adapter", "?"), inline=True)
embed.add_field(name="可用", value="是" if available else "否", inline=True)
```

**注意**：value 保持原样（adapter 名、路径、英文状态值）。只翻 name。

### B. `cogs/utility.py` dashboard 翻译（高 ROI，15 分钟）

**位置**：`cogs/utility.py:283-319`（`_build_dashboard_embed` 函数）

**需要翻译的字符串**：

| 当前 | 建议 |
|---|---|
| `title="{bot_name} Health Dashboard"` | `title="{bot_name} 健康面板"` |
| `name="Uptime"` | `name="运行时长"` |
| `value="Online"` | `value="在线"` |
| `value="OFFLINE"` | `value="离线"` |
| `set_footer(text=f"Updated: {timestamp}")` | `set_footer(text=f"更新于：{timestamp}")` |
| `await ctx.send("Dashboard posted. It will auto-update every 60 seconds.")` | `await ctx.send("面板已发送，每 60 秒自动刷新。")` |

**注意**：dashboard 卡片刷新可能用 `edit()`，要看完整代码确认 footer / title 改动后不会破坏 message_id 引用。

### C. `bot.py` + `cogs/agents.py` 错误/状态文案（中 ROI，1 小时）

**待评估**：技术用户可能倾向英文错误信息（更精确、方便 Google）。需要先讨论是否做。

**典型的用户可见英文（grep `channel.send`）**：

```
bot.py:
- "Back online."
- "Restarting..."
- "[ALERT] ..."
- "[LOG] ..."
- "Cleared X messages from context. Discord messages remain visible."

cogs/agents.py:
- "Usage: @team <your question>"
- "X isn't active in this channel."
- "Unknown agent: X"
- "↩️ Cancelled — reprocessing edited message..."
```

**建议**：先做 A+B，看用户反馈。如果用户反馈"bot 错误也是英文看不懂"，再做 C。

### D. Agent 输出强制中文（低 ROI / 高复杂度，2 小时+）

**问题**：即使 system_prompt 已经说"回复简洁"，agent（Claude/Codex/OpenCode/OMP）处理英文技术内容时仍倾向用英文回复。

**两条路径**：

1. **Prompt 加强路径**（便宜但不彻底）
   - 在 `agents.toml` 每个 agent 的 `system_prompt` 加一行：
     ```
     ## 语言规则（强制）
     所有非代码回复必须用简体中文。代码、命令、路径、错误信息原文保留。
     ```
   - 适合常规对话；处理纯英文文档/代码时模型可能仍切英文

2. **Post-processing 路径**（彻底但侵入）
   - 在 adapter 层（`agents/cli.py`、`agents/local_llm.py`）加翻译钩子
   - 用 LLM 翻译 agent 输出（成本高、延迟高）
   - **不推荐做** —— 用户体验损失比收益大

**建议**：只做路径 1（prompt 加强），不做路径 2。

## 执行顺序

1. **第一步（必须）**：A + B
2. **第二步（看反馈）**：C
3. **第三步（仅 prompt 改）**：D 路径 1

## 测试方案

执行后验证：
1. `pytest tests/test_embeds.py` 通过（已有测试，确认字段名改动不破坏断言）
2. 在 Discord 跑 slash command `/agents` / `/health` / `/session` / `/dashboard`，肉眼检查中文
3. 让 agent 报错（比如 `@UnknownAgent`），看错误消息
4. 部署到 server：`scripts/deploy-server.sh multinexus`，在 Discord 真实环境验证

## 已知风险

- **`tests/test_embeds.py`** 已经断言了一些字段值（比如 "没有活跃会话"），改字段名时不要破坏这些断言。**翻译前先看测试**。
- **dashboard 自动刷新**：`_build_dashboard_message` 用 `await msg.edit(embed=...)` 更新已发的卡片。翻译字段名不会破坏 edit 机制，但注意 title 文案改动会让旧卡片和新卡片不同（短暂不一致）。
- **多语言 fallback**：bot 没做 i18n 框架（gettext / babel），这次是硬编码中文。如果以后要支持英文用户，得回滚或做真正的 i18n。

## 文件清单（执行时改的）

- `multinexus/embeds.py`（A 必改）
- `cogs/utility.py`（B 必改）
- `bot.py`（C 可选）
- `cogs/agents.py`（C 可选）
- `agents.toml`（D 路径 1 可选）
- `tests/test_embeds.py`（如果测试断言需要同步改）

## Commit 策略

建议一个范围一个 commit：
- `feat(i18n): translate embed field names to Chinese`
- `feat(i18n): translate dashboard card to Chinese`
- `feat(i18n): translate bot status messages to Chinese`（如做 C）
- `feat(prompt): require Chinese reply in agent system prompts`（如做 D）

不要打包一个巨大的 i18n commit，方便回滚和 code review。
