# Discord 卡片与消息中文化计划

**状态**：A+B 已 implemented / merged / deployed；C/D 仍 optional，未启动
**创建**：2026-06-18（commit `3812096`）
**刷新**：2026-07-03，基于 `main` `ddafb46980df8ed7441821a225c5578461ceeef0` 核对目标文件状态
**A+B closeout**：2026-07-03，见文末「A+B 落地记录」
**C pre-audit**：2026-07-03，见文末「C pre-audit（剩余英文清单）」
**预估总时长**：A+B 共 45 分钟（实际约 30 分钟）；A+B+C 共 1.5 小时；D 单独评估

> **本轮范围（plan refresh 确认）**：只做 A+B。C/D 保持 optional，不在第一轮内。

## 背景

当前 Discord bot 输出的 embed 卡片和状态消息**中英文混杂**，对中文用户不友好。已经做完 `CLAUDE.md` 中文化、`deploy-server.sh` 跨平台化，bot 用户可见文案是下一个明显的杠杆点。

## 改造范围（4 个层次，按 ROI 排序）

### A. `multinexus/embeds.py` 字段名翻译（高 ROI，30 分钟）

**现状（refresh 核对）**：标题已经是中文（"可用 Agent"、"健康检查"、"会话状态"），但 `add_field` 的 name 字段大量英文。2026-07-03 核对 `multinexus/embeds.py`，下列英文 name 仍存在，清单准确。

**需要翻译的字段名**（`grep 'embed.add_field'`）：

| 当前（英文）| 建议（中文）| 备注 |
|---|---|---|
| `adapter` | `适配器` | 保留 adapter 名（claude/codex/...）原文 |
| `available` | `可用` | value 已经是 "是"/"否" |
| `bin` | `可执行文件` | value 是路径，原样保留 |
| `error` | `错误` | |
| `model` | `模型` | |
| `path` | `路径` | |
| `scope` | `scope` | 保留，是多 agent 系统术语 |
| `scope_type` | `scope_type` | 保留，是多 agent 系统术语 |
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

**主锚点（refresh）**：`cogs/utility.py` 的 `_build_dashboard_embed(self)` 方法（refresh 时位于 `283-319`，行号可能随代码漂移，以方法名为准）。同时 `dashboard_cmd`（`321` 起）含 `ctx.send(...)` 文案。

**需要翻译的字符串**（`_build_dashboard_embed` / `dashboard_cmd`）：

| 当前 | 建议 |
|---|---|
| `title=f"{bot_name} Health Dashboard"` | `title=f"{bot_name} 健康面板"` |
| `name="Uptime"` | `name="运行时长"` |
| `value=f"Online\n`{model}`"` | `value=f"在线\n`{model}`"` |
| `value=f"OFFLINE\n{...}"` | `value=f"离线\n{...}"` |
| `set_footer(text=f"Updated: {time.strftime('%H:%M:%S')}")` | `set_footer(text=f"更新于：{time.strftime('%H:%M:%S')}")` |
| `await ctx.send("Dashboard posted. It will auto-update every 60 seconds.")` | `await ctx.send("面板已发送，每 60 秒自动刷新。")` |

**注意**：dashboard 卡片刷新用 `_dashboard_loop` → `await self._dashboard_message.edit(embed=embed)` 更新已发的卡片。翻译字段名不会破坏 edit 机制，但 title 文案改动会让旧卡片和新卡片短暂不一致（refresh 时已确认仍是 `edit()` 模式）。

### C. `bot.py` + `cogs/agents.py` 错误/状态文案（中 ROI，1 小时）— optional

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

### D. Agent 输出强制中文（低 ROI / 高复杂度，2 小时+）— optional

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
1. `pytest tests/test_embeds.py` 通过 —— **注意：当前测试直接断言英文字段名，A 翻译必须同步改测试断言**（见下"已知风险"）
2. 在 Discord 跑 slash command `/agents` / `/health` / `/session` / `/dashboard`，肉眼检查中文
3. 让 agent 报错（比如 `@UnknownAgent`），看错误消息
4. 部署到 server：`scripts/deploy-server.sh multinexus`，在 Discord 真实环境验证

## 已知风险（refresh 重点核对）

- **`tests/test_embeds.py` 直接断言英文字段名 —— A 翻译会破坏测试，必须 lockstep 改**。refresh 时核对的具体断言点（以方法名为主锚点，行号可能漂移）：
  - `test_fields_present`：`for expected in ["adapter", "bin", "available", "work_dir", "model", "timeout"]: assertIn(expected, names)` —— 这 6 个 name 必须同步翻成中文。
  - `test_active_session_fields`：`for expected in ["scope", "scope_type", "session_id", "adapter", "work_dir", "轮次", "活跃会话"]` —— 注意 `scope`/`scope_type`/`session_id` 在 plan 里保留英文，`adapter`/`work_dir` 要翻；断言要相应调整。
  - `test_available_shows_yes` / `test_unavailable_shows_no`：用 `next(f for f in embed.fields if f.name == "available")` 定位字段 → `available` 翻成 `可用` 后定位逻辑要改。
  - `test_error_included`：`next(f for f in embed.fields if f.name == "error")` → `error` 翻成 `错误` 后定位逻辑要改。
  - `test_scope_type_field_for_channel` / `test_scope_type_field_for_thread`：用 `f.name == "scope_type"` 定位 → `scope_type` 按计划保留英文，定位逻辑不变（确认即可）。
  - `test_session_id_truncated`：用 `f.name == "session_id"` 定位 → `session_id` 按计划保留英文，定位逻辑不变。
  - **已是中文、断言不动**：`test_has_managed_and_external_fields`（`托管 Agent`/`外部 Gateway Agent`）、`test_no_session_description`（`没有活跃会话`）、`test_no_session_shows_active_count`（`活跃会话`）。
  - **结论**：A 的 commit 必须同时改 `tests/test_embeds.py` 里上述断言，不能只改 `embeds.py`。
- **dashboard 自动刷新**：`_dashboard_loop` 用 `await msg.edit(embed=...)` 更新已发的卡片（refresh 已确认仍是此模式）。翻译字段名不会破坏 edit 机制，但注意 title 文案改动会让旧卡片和新卡片不同（短暂不一致）。
- **多语言 fallback**：bot 没做 i18n 框架（gettext / babel），这次是硬编码中文。如果以后要支持英文用户，得回滚或做真正的 i18n。

## 文件清单（执行时改的）

- `multinexus/embeds.py`（A 必改）
- `tests/test_embeds.py`（A 必改 —— 字段名断言 lockstep，见"已知风险"）
- `cogs/utility.py`（B 必改，`_build_dashboard_embed` + `dashboard_cmd`）
- `bot.py`（C 可选）
- `cogs/agents.py`（C 可选）
- `agents.toml`（D 路径 1 可选）

## Commit 策略

建议一个范围一个 commit：
- `feat(i18n): translate embed field names to Chinese`
- `feat(i18n): translate dashboard card to Chinese`
- `feat(i18n): translate bot status messages to Chinese`（如做 C）
- `feat(prompt): require Chinese reply in agent system prompts`（如做 D）

不要打包一个巨大的 i18n commit，方便回滚和 code review。

## 刷新记录

- **2026-07-03**：基于 `main` `ddafb46980df8ed7441821a225c5578461ceeef0` 核对。确认 `multinexus/embeds.py` 字段名仍全英文（A 清单准确）；确认 `cogs/utility.py` `_build_dashboard_embed` 仍存在、字符串仍英文、`edit()` 刷新模式不变（B 行号此时仍为 283-319，但改为方法名主锚点以防漂移）；强化测试耦合风险——列出 `tests/test_embeds.py` 中按方法名锚点的具体断言点，明确 A 必须 lockstep 改测试。本轮 plan refresh 不改任何代码 / 配置。

## A+B 落地记录（2026-07-03）

| 项 | 结果 |
|---|---|
| A commit | `feat(i18n): translate embed field names to Chinese` (`3836607`) |
| B commit | `feat(i18n): translate dashboard card to Chinese` (`42c6834`，含 slash_dashboard 补翻) |
| merge commit | `Merge Discord card i18n A+B` (`e8346ee99c57f65e4bd24a864bbc68cce68b210c`，`--no-ff`) |
| deployed | `e8346ee99c57f65e4bd24a864bbc68cce68b210c` → `/opt/multinexus`（`deployed_at=2026-07-03T15:52:11Z`）|
| full suite | **341 passed, 2 skipped, 12 subtests passed**（pre + post merge 一致）|
| server-smoke | `server-smoke.sh` clean pass（systemd `multinexus-discord-bridge` active + `coordinate` active + breaker scan clean）|

**A 实际落地**（`multinexus/embeds.py`，9 个 name 翻译）：`adapter→适配器` / `bin→可执行文件` / `available→可用` / `work_dir→工作目录` / `model→模型` / `timeout→超时` / `path→路径` / `error→错误` / `status→状态`。保留英文：`scope` / `scope_type` / `session_id`（策略自洽，见 2026-07-03 scope_type 修复）。value 全部不动。`tests/test_embeds.py` 断言 lockstep 更新。

**B 实际落地**（`cogs/utility.py`）：`_build_dashboard_embed` title/Uptime/Online/OFFLINE/footer + `dashboard_cmd` 与 `slash_dashboard` 两个入口的确认消息 + slash description。`_dashboard_loop` 的 `edit()` 刷新机制未动。

**D 状态**：未启动，仍 optional。不做 post-processing 翻译钩子。

## C pre-audit（2026-07-03，只读扫描，未改代码）

扫描 `bot.py` / `cogs/agents.py` / `cogs/utility.py` 中剩余用户可见英文文案，按是否值得翻译分类。**plan C 原始范围是 `bot.py` + `cogs/agents.py`；本 audit 一并覆盖 `cogs/utility.py` 的非 dashboard 残留（slash 错误消息、help、get_status），因为它们同属"bot 状态/错误文案"语义。**

### 1. 高频用户路径（建议翻）

| 文件:行 | 当前文案 | 出现场景 | 建议译文 |
|---|---|---|---|
| `cogs/utility.py:50` | `**{bot_name} Status**` | `/monitor` + `!status` 标题 | `**{bot_name} 状态**` |
| `cogs/utility.py:56` | `Uptime: {h}h {m}m {s}s` | `/monitor` 运行时长 | `运行时长：{h}时 {m}分 {s}秒` |
| `cogs/utility.py:73` | `{label}: Online (\`{model}\`)` | `/monitor` agent 行 | `{label}：在线（\`{model}\`）` |
| `cogs/utility.py:75` | `24h tokens: ...` | `/monitor` token 统计 | `24h token：...` |
| `cogs/utility.py:79` | `{label}: OFFLINE ({error})` | `/monitor` agent 离线 | `{label}：离线（{error}）` |
| `cogs/utility.py:82` | `- Database: Connected` | `/monitor` 数据库行 | `- 数据库：已连接` |
| `cogs/utility.py:90-95` | help 文案（commands / Agents / Wiki / Utility 说明）| `!help` + `/help` | 整体翻译（slash 命令名保留）|
| `cogs/utility.py:89` | `{bot_name} commands (use \`/help\` for...)` | help 前缀 | `{bot_name} 命令（用 \`/help\` 查看完整列表）：` |

> 说明：`get_status()` 同时驱动 `/monitor`、`!status` 和 dashboard 卡片外的纯文本状态，是 C 范围里 ROI 最高的单点（改一处函数影响多条命令输出）。

### 2. 错误/操作反馈路径（建议翻，低风险）

| 文件:行 | 当前文案 | 场景 | 建议译文 |
|---|---|---|---|
| `bot.py:455` | `Back online.` | bot 启动后回主频道 | `已上线。` |
| `bot.py:488` | `Restarting...` | `!restart` | `重启中…` |
| `bot.py:493` | `Cleared {n} messages from context. Discord messages remain visible.` | `!clear` | `已清除上下文中 {n} 条消息。Discord 消息仍可见。` |
| `bot.py:538` | `↩️ Cancelled — reprocessing edited message...` | 编辑消息后重处理 | `↩️ 已取消 —— 正在重新处理编辑后的消息…` |
| `bot.py:319-322` | `<#{cid}> registered for...` / `Config updated.` / `Use !restart to fully reload.` | `!new-channel` | 整体翻译（保留 channel ID / 命令名）|
| `bot.py:326-328` | `Live registration ok, but config write failed...` / `Add channel ID manually...` | `!new-channel` 失败 | 整体翻译（保留 `e` 错误原文 + channel ID）|
| `cogs/utility.py:220` | `Discovery posted!` | `/discover` 成功 | `已记录发现！` |
| `cogs/utility.py:235` | `Done.` | `/new-channel` 成功 | `完成。` |
| `cogs/utility.py:251/269` | `Not authorized.` | `/stop` / `/restart` 权限拒绝 | `未授权。` |
| `cogs/utility.py:255` | `Agents cog not loaded.` | `/stop` cog 缺失 | `Agents 模块未加载。` |
| `cogs/utility.py:260` | `No agent is running in this channel.` | `/stop` 无 agent | `当前频道没有正在运行的 agent。` |
| `cogs/utility.py:262` | `Stopping {agent.name}...` | `/stop` 执行中 | `正在停止 {agent.name}…` |
| `cogs/utility.py:271` | `Restarting...` | `/restart` | `重启中…` |
| `cogs/agents.py:323` | `Usage: @team <your question>` | `@team` 无参数 | `用法：@team <你的问题>` |
| `cogs/agents.py:388` | `Usage: {names} <your question>` | `@agent` 无参数 | `用法：{names} <你的问题>` |
| `cogs/agents.py:423/487` | `{names} isn't active in this channel.` | agent 未激活 | `{names} 在当前频道未激活。` |
| `cogs/agents.py:242` | `⚠️ {error}` | 多 agent 流程错误 | `⚠️ {error}`（保留 error 原文）|

### 3. 技术日志/告警（建议保留英文或仅翻标签）

| 文件:行 | 当前文案 | 建议 |
|---|---|---|
| `bot.py:253` | `[ALERT] {message}` | `[告警] {message}` 或保留 `[ALERT]` 前缀（operator 频道，告警内容多变）|
| `bot.py:559` | `[LOG] {message}` | `[日志] {message}` 或保留（同上，operator 频道）|
| `bot.py:267-268` | `{agent} discovery: {finding}` | `{agent} 发现：{finding}`（finding 内容不翻译）|
| `cogs/utility.py:116/129/142/155` | slash command `description="Ask X a question"` 等 | 翻译 description（slash 菜单可见）：`向 X 提问` / `发送网络研究查询` 等 |
| `cogs/utility.py:170/186/215/223/248/266` | slash `description=`（monitor/help/discover/new-channel/stop/restart）| 翻译 description |
| `cogs/utility.py:117/130/143/156/216/225` | `@app_commands.describe(prompt="Your question...")` | 翻译参数描述：`你的问题或 prompt` |

### 4. 不建议翻译

| 文件:行 | 文案 | 原因 |
|---|---|---|
| `cogs/agents.py:656` | `🔄 thinking...` | placeholder 状态指示，emoji 已跨语言；翻成"思考中…"可接受但收益低 |
| `cogs/agents.py:691-702` | webhook `content={chunk}` | agent 输出本身，属 D 范畴（agent 回复语言），不在 C 内 |
| slash command `name=`（如 `claude`/`codex`/`monitor`）| 命令名 | 命令名是协议契约，翻译会破坏 Discord slash command 注册 |

### 推荐结论

**建议启动 C，优先做"高频用户路径"（第 1 类）+ slash description/describe（第 3 类的 description 部分）**，因为：
- 第 1 类（`get_status()` / help 文案）单点影响多条命令，ROI 最高。
- slash description 在 Discord 命令菜单里中文对发现性帮助大。

**第 2 类（错误/操作反馈）可一并做**，风险低（多为 send 字面量，无测试耦合，与 B 的 dashboard 文案同性质）。

**第 3 类的 `[ALERT]`/`[LOG]` 前缀**：建议保留英文前缀或仅翻成 `[告警]`/`[日志]`，因为这是 operator/日志频道内容，内容多变，强翻收益不确定。

**估算**：第 1+2+3(description) 约 40-50 分钟，无测试耦合风险（C 范围内无 pure embed builder 测试，文案都是 cog 运行时 send 字面量）。第 4 类不做。

> 注：C 范围内没有任何测试需要 lockstep 改（`tests/test_embeds.py` 只覆盖 pure embed builder，已在 A 阶段处理完）。C 的验证靠 Discord 真实环境跑 `/monitor` / `!help` / `@team` / `/stop` 等命令肉眼检查。
