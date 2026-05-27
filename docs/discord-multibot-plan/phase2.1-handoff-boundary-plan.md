# Phase 2.1：Handoff 触发边界固化计划

## 背景

Phase 2 已验证混合架构可以跑通：discord-nexus 托管 coding agents，小龙虾/OpenClaw 和 Hermes 保留原生 Gateway。真实 Discord 验收后，触发边界应按**目标 agent 类型**划分，而不是按消息来源简单放宽。

核心结论：

- Adapter/managed agents（Claude、Codex、OpenCode）必须由正式 handoff 触发。
- External gateway agents（小龙虾/OpenClaw、Hermes）由各自原生 Gateway 决定触发规则，当前可以被普通 Discord @mention 触发。
- discord-nexus 不应该让任意 bot 的普通 @mention 触发 managed agent，否则容易产生误触发和 bot 循环。

这一步是 Phase 2 到 Phase 3 的收口，不引入 slash command、embed、wiki、scratch 等高级功能。

## 目标规则

### 1. 目标是 managed adapter agent

Bot 消息必须同时满足：

1. `respond_to_bots=true`
2. Discord 原生 mention 命中当前 managed bot
3. 消息包含正式 `[handoff]` 行

适用例子：

- 小龙虾 → Mac Claude：必须 `[handoff] <@Mac_Claude_uid> ...`
- Hermes → Mac Codex：必须 `[handoff] <@Mac_Codex_uid> ...`
- Mac Codex → Mac Claude：必须 `[handoff] <@Mac_Claude_uid> ...`

不允许：

```text
<@Mac_Claude_uid> 你继续处理这个任务
```

原因：managed adapter agent 是工程执行入口，不能被 bot 普通聊天、引用、总结或误 @ 触发。

### 2. 目标是 external gateway agent

由 external agent 自己的 Gateway 和配置决定。discord-nexus 只需要发送 Discord 原生 mention。

适用例子：

- Mac Claude → 小龙虾：`<@小龙虾_uid> 帮我看一下需求`
- Hermes → 小龙虾：`<@小龙虾_uid> ...`
- 小龙虾 → Hermes：`<@Hermes_uid> ...`

这些 agent 不由 discord-nexus 启动，也不走 discord-nexus adapter，因此是否需要 `[handoff]` 不是由 discord-nexus 强制。

### 3. 人类用户

人类消息保持宽松：

- `@managed bot ...` 可以触发。
- `!bang ...` 可以触发。
- 仍受 `allowed_user_ids` 和 channel allowlist 限制。

## 触发矩阵

| 来源 | 目标 | 条件 | 是否触发 | 执行方 |
|------|------|------|----------|--------|
| 人类 | Managed | @managed bot 或 `!bang` | 是 | discord-nexus |
| Managed bot | Managed | `[handoff]` + @managed bot | 是 | discord-nexus |
| Managed bot | Managed | 仅 @managed bot，无 `[handoff]` | 否 | discord-nexus |
| External bot | Managed | `[handoff]` + @managed bot | 是 | discord-nexus |
| External bot | Managed | 仅 @managed bot，无 `[handoff]` | 否 | discord-nexus |
| Unknown bot | Managed | @managed bot | 否 | discord-nexus |
| 任意可见用户/bot | External | @external bot | 取决于 external Gateway | external agent |
| Coordinator 状态通知 | Managed | 普通状态消息 | 否 | discord-nexus |
| Coordinator assignment | Managed | 专用 handoff delivery + @managed bot | 是 | discord-nexus |

## 当前实现期望

`DiscordClient.on_message()` 对 bot 消息应保持严格：

```python
if message.author.bot:
    if not self.agent_config.respond_to_bots:
        return

    addressed = self._is_addressed_to_me(message)
    handoff = self.mention_router.is_handoff_message(message.content)

    if not addressed or not handoff:
        return

    self._record_message(message)
    await self._handle_request(message)
```

这正是 managed adapter agents 的安全边界。

## 需要固化的点

### 1. 文档一致性

所有文档都应避免写成“external bot 只要 @mention 就能触发 managed bot”。正确说法是：

- external gateway agent 自己可以被普通 @mention 触发；
- managed adapter agent 被任何 bot 触发时都要求 `[handoff] + @mention`。

### 2. 测试补强

补充或确认以下测试：

1. managed bot + `[handoff]` + @managed bot → 触发。
2. managed bot + @managed bot + 无 `[handoff]` → 不触发。
3. external bot + `[handoff]` + @managed bot → 触发。
4. external bot + @managed bot + 无 `[handoff]` → 不触发。
5. unknown bot + `[handoff]` + @managed bot → 是否触发需要明确策略；建议未知 bot 不触发。
6. `respond_to_bots=false` 时，所有 bot 消息都不触发。
7. human @managed bot 仍能触发，不需要 `[handoff]`。

如果现有 `DiscordClient` 不容易直接单测，可先把过滤判断抽成纯函数：

```python
should_handle_bot_message(
    *,
    respond_to_bots: bool,
    addressed: bool,
    handoff: bool,
    known_bot: bool,
) -> bool
```

建议策略：known managed / known external / coordinator handoff 可以触发；unknown bot 不触发。

### 3. External agent 输出建议

虽然 external gateway agent 不需要 `[handoff]` 才能被触发，但当它们要交给 managed adapter agent 时，prompt 或配置应鼓励它们输出正式 handoff：

```text
[handoff] <@Mac_Codex_uid> 请继续实现...
```

这不是为了 external agent 自己，而是为了让目标 managed adapter agent 安全地接收任务。

## 验收标准

1. 单元测试通过。
2. 真实 Discord 中，小龙虾只 @Mac Codex、不写 `[handoff]`，Mac Codex 不响应。
3. 真实 Discord 中，小龙虾发 `[handoff] <@Mac_Codex_uid> ...`，Mac Codex 响应。
4. 真实 Discord 中，Mac Codex 只 @Mac Claude、不写 `[handoff]`，Mac Claude 不响应。
5. 真实 Discord 中，Mac Codex 发 `[handoff] <@Mac_Claude_uid> ...`，Mac Claude 响应。
6. 真实 Discord 中，Claude 直接 @小龙虾，小龙虾按自己的 Gateway 规则响应。

## 不做的事

- 不要求 external gateway agents 改成 adapter 模式。
- 不要求 external gateway agents 被触发时必须识别 `[handoff]`。
- 不引入 slash commands。
- 不引入 embed/status dashboard。
- 不引入 coordinator delivery。
- 不改变 session persistence 策略。
