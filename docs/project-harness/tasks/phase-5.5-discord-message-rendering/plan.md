> **Historical record.** Current source of truth: `docs/project-harness/progress.md` and `docs/project-harness/scope.md`. This file is preserved as part of the dogfood development audit chain.

# Phase 5.5 Discord 消息渲染

## 背景

当前 coordinator、harness、agent 的任务事件已经比较结构化，但 Discord 频道里看到的仍然主要是大段纯文本。真实 dogfood 时，这带来几个问题：

- 人很难快速区分任务派发、进度、阻塞、评审、完成等不同事件。
- 重要字段如任务、owner、状态、测试结果、风险、下一步混在正文里，不利于扫读。
- 部分 handoff packet 会把内部 dict 或长文本直接扔进频道，阅读成本高。
- 频道应该更像协作面板，而不是日志转储。

Discord 原生支持 embeds、fields、颜色、标题、footer 等展示能力。Phase 5.5 的目标是把适合人看的结构化事件渲染成 Discord 卡片，同时保留现有协议文本，避免破坏 bot-to-bot 触发链路。

## 目标

实现一个最小但可靠的 Discord 消息渲染层，让 coordinator 发到 Discord 的协作消息更容易理解：

- 任务派发、进度、阻塞、评审、完成等事件使用 embed/card 展示。
- 关键字段用 fields 展示，例如 task、agent、status、tests、risk、next step。
- `[handoff]`、`[lifecycle]`、`[agent-report]` 等机器协议仍保留在普通 content 中，不能只放在 embed 里。
- handoff 和 lifecycle 的 `allowed_mentions` 仍然只允许目标 agent，不能因为渲染层变宽。
- 长文本要截断或摘要，避免超过 Discord embed 限制。

## 范围

### multi-agent-coordinator

1. 新增或整理 Discord 渲染模块。
   - 可以放在 `src/multi_agent_coordinator/discord_rendering.py`，或按现有结构放在 `policy.py` / `bus.py` 附近。
   - 输入为已有 event / delivery payload。
   - 输出为 Discord webhook/bot 可发送的结构：`content`、`embeds`、`allowed_mentions`。

2. 扩展 delivery payload。
   - 保持现有 `content` / `text` 行为兼容。
   - 增加可选 `embeds`。
   - delivery pump / webhook bus 发送时，如果 payload 有 embeds，就带上 embeds。

3. 覆盖以下事件类型的渲染。
   - task handoff / worker handoff prepared：显示任务、目标 agent、bootstrap 路径、分支、scope。
   - assignment accepted：显示 agent 已接收任务、任务 ID、下一步。
   - progress reported：显示阶段进度、已完成、测试结果、风险。
   - blocker reported：显示阻塞原因、需要谁决策、建议动作。
   - review completed：显示 reviewer、结论、主要发现、是否需要修改。
   - task done / closeout：显示完成状态、提交、测试结果、残余风险。

4. 渲染约束。
   - handoff/lifecycle 必须保留普通 content 行，因为 Discord bot 通常只从 message content 触发。
   - embed 只用于人类可读展示，不作为唯一协议载体。
   - `allowed_mentions` 必须由原有路由逻辑决定，渲染层不能自动扩大 mention 范围。
   - 长字段需要安全截断，避免 Discord 400 或消息发送失败。

5. 测试。
   - renderer 单测：不同事件生成期望 embed 标题、字段、颜色或状态。
   - delivery 单测：payload 带 embeds 时 WebhookBus 正确发送。
   - mention 单测：handoff 渲染后 `allowed_mentions` 仍只包含目标 agent。
   - 兼容单测：旧 payload 没有 embeds 时仍按纯文本发送。

### multinexus

本阶段默认不要求修改 multinexus runtime。只有在真实 E2E 暴露问题时，才允许做小范围修复：

- 如果 managed bot 对 embed 消息误触发或漏触发，修复 handoff/lifecycle handler。
- 如果 worker/bootstrap 文档里需要补充“Discord 卡片只是展示，协议以 content 为准”，同步更新文档。
- 记录 dogfood UX 反馈到 `docs/project-harness/dogfood-feedback.md`。

## 非目标

- 不做 Discord buttons、select menus、modals。
- 不改 `[handoff]`、`[lifecycle]`、`[agent-report]` 的协议语义。
- 不把任意 LLM 长回复都转成 embed。
- 不改 external gateway agents 的行为。
- 不做 systemd / Windows 部署。
- 不做 session 生命周期新功能，这属于 Phase 5.2。

## 验收标准

1. coordinator 单测通过。
   - `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`

2. multinexus 单测通过。
   - `.venv/bin/python -m unittest discover tests/`

3. Discord 真机验证至少覆盖：
   - coordinator 派发一个 worker handoff，频道看到短 content + embed 卡片。
   - 目标 agent 仍能被正常唤醒并 auto-accept。
   - worker 发一个 progress / done / review report 后，频道显示结构化卡片。
   - `allowed_mentions` 没有扩大到非目标 agent。

4. 失败模式可控。
   - embed 生成失败时 fallback 到纯文本。
   - 字段过长时截断而不是发送失败。
   - 旧 delivery payload 没有 embeds 时不报错。

5. 文档同步。
   - `docs/project-harness/dogfood-feedback.md` 记录原始 UX 问题和本阶段处理状态。
   - 如新增 renderer 行为，coordinator 对应文档或 runbook 中补充简短说明。

## 建议分工

- Coding worker：优先使用 `mac-claude`。
- Reviewer：Codex 审核实现和测试覆盖。
- Operator：通过 coordinator 派发任务、观察 Discord 真实交互、记录 dogfood 问题。

## Worker 注意事项

- 不要直接修改 harness JSON，状态变更走 coordinator CLI。
- 不要打印或提交 token、webhook URL、`.env`、`agents.toml`。
- 不要为了美化消息破坏协议触发。机器可读 content 优先，embed 是人类可读层。
- 如果发现 bot daemon 与 webhook delivery 的发送路径不同，需要同时确认两条路径的兼容性。
- 遇到 Discord API 限制时，优先做小而确定的截断策略，不要引入复杂渲染框架。
