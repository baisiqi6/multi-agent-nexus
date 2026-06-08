# Agent-Report 协议

`agent-report` 是 multinexus managed agent 在 coordinator handoff 执行期间发回 Discord 的结构化状态报告。它的目标是让 coordinator daemon 能摄取 agent 进展，同时让频道里的人能读懂当前状态。

## 格式

推荐每条 report 单独占一行发送：

```
[agent-report] action=<action> workspace_id=<workspace> task_id=<task> [summary=<text>] [reason=<text>]
```

字段：
- `action`：报告类型，必填。
- `workspace_id`：coordinator workspace id，必填。
- `task_id`：任务 id，必填。
- `summary`：人类可读摘要，可选；含空格时需要 shell quote。
- `reason`：错误或阻塞原因，可选；含空格时需要 shell quote。

coordinator daemon 会扫描消息中的结构化 report 行。agent 可以先输出人类摘要，再单独换行输出 `[agent-report] ...`。

## 群聊可见性规则

承接任务的 agent 应该负责执行面沟通；coordinator 只负责控制面事件、handoff、review/closeout/done 汇总。不要让频道只剩 coordinator 在复述状态。

推荐格式：

```text
@Coordinator @Codex Phase 5.2 已完成第一阶段：新增 task scope 查询和 reset 测试，134 tests OK。下一步处理 closeout 后 archive。
[agent-report] action=progress workspace_id=multinexus task_id=phase-5.2-task-session summary="task scope status/reset tests done; tests OK; next archive on closeout"
```

规则：

- **开始任务时**：agent 发一句“我已接收任务，准备先做 A/B/C”。
- **阶段完成时**：agent 说明完成了什么、跑了什么测试、下一步是什么。
- **阻塞时**：agent 明确 `@Coordinator`、`@Codex` 或可见 reviewer/operator，并说明需要什么决策。
- **完成实现时**：agent 明确 `@Coordinator` 和 reviewer/operator，请求 review，并说明改动文件、测试结果、剩余风险。
- `[agent-report]` 行必须单独成行，且从行首开始。
- 自动 runtime 发送的 `accept` report 可以是纯结构化消息；worker 后续的 `progress` / `blocker` / `done` 应优先包含人类可读摘要。

## 支持的 Action

| Action | 何时使用 | 生命周期影响 |
|--------|----------|--------------|
| `accept` | runtime auto-accept 成功 | 记录接收事实；真正的 assignment 状态已由 runtime 先调用 coordinator CLI 改掉 |
| `progress` | worker 完成一个小阶段 | coordinator 摄取进度；来自 Discord 的原始 agent 消息已经可见，coordinator 不应再重复广播 |
| `blocker` | worker 无法继续 | 记录阻塞报告，通常需要 operator 或 reviewer 决策 |
| `done` | worker 认为实现完成 | 只记录完成报告；不会自动 closeout 或 mark-done |

`done` 不等于任务关闭。正式进入 closeout / review / mark-done 仍然必须通过 coordinator CLI：

```bash
mac.sh assignment closeout multinexus --task-id <id> --reviewer <name>
mac.sh assignment mark-done multinexus --task-id <id>
```

## Auto-Accept 行为

收到 coordinator handoff 时：

1. `DiscordClient.on_message` 识别来自 coordinator bot 的 `[handoff]`。
2. `_try_coordinator_handoff` 在 adapter 启动前先通过 coordinator CLI 执行 `assignment.accept`。
3. accept 成功：发送 `action=accept` report，读取 bootstrap，再调用 adapter。
4. accept 失败：发送 `action=blocker` report，不调用 adapter。
5. bootstrap 缺失：仍调用 adapter，但 prompt 会明确说明 bootstrap 缺失。

managed agent 不应该再次运行 `assignment.accept`。bootstrap prompt 会明确说明 runtime 已经完成 accept。

## Action 边界

runtime 只自动执行 `assignment.accept`。其他生命周期动作，例如 `mark-done`、`closeout`、`merge`、`deploy`、`pr`，都会被 `parse_coordinator_handoff` 拒绝，必须由 agent 或 operator 通过 coordinator CLI 发起。

## 发送规则

所有 runtime 自动发送的 `[agent-report]` 都使用 `AllowedMentions.none()`，避免误触发其他 bot。

## Discord Report 与 Coordinator CLI 的分工

| 场景 | 机制 |
|------|------|
| Auto-accept 结果 | `[agent-report]`，由 runtime 自动发送 |
| 任务中途里程碑 | `[agent-report] action=progress`，由 agent 输出 |
| 外部依赖阻塞 | `[agent-report] action=blocker`，由 agent 输出 |
| agent 认为工作完成 | `[agent-report] action=done`，由 agent 输出，仅作报告 |
| 分配分支 | coordinator CLI：`branch allocate` |
| 关联 PR | coordinator CLI：`pr link` |
| CI 状态 | coordinator CLI：`ci check` |
| 请求 closeout review | coordinator CLI：`assignment closeout` |
| 正式 mark done | coordinator CLI：`assignment mark-done` |

Discord report 负责**可见性和摄取**。Coordinator CLI 负责**生命周期状态变更**。不要把二者混用。

## Discord Embed / 卡片展示（Phase 5.5+）

Phase 5.5 之后，coordinator 派发的 `handoff`、`assignment.*`、`progress.*`、`review.completed`、`task.done`、`ci.*` 等事件会在 Discord 频道里同时带 embed 卡片和普通 `content` 文本。

规则（managed agent 端必须遵守）：

- **bot-to-bot 协议仍然只看 `content`**。`[handoff]`、`[lifecycle]`、`[agent-report]` 等触发行必须出现在普通 `content` 中；它们不能只放在 embed 字段里。
- **embed 是给人看的**，用来减少扫读成本。embed 缺失、截断或 Discord 渲染失败时，runtime 必须仍然能识别 `content` 里的协议行。
- **`allowed_mentions` 仍由路由层决定**。embed 渲染层不会扩大 mention 范围；handoff / lifecycle 仍然只 mention 目标 agent，不会因为加了 embed 就多 ping 其他 bot。
- **不要把 LLM 自然语言回复也包成 embed**。embed 是 coordinator 派发的结构化事件的展示，managed agent 给人类的回复保持原样。

实现参考：

- coordinator 侧渲染模块：`coordinate/discord_rendering.py`（`render_embed(event_type, event, payload)`）。
- delivery 兼容：`policy.py` 在派发时把 `embeds` 字段挂到 Discord payload；`WebhookBus`（`bus.py`）和 daemon 都会把 `embeds` 透传。
- 兼容回退：旧 delivery payload 没有 `embeds` 字段时仍按纯文本发送；`render_embed` 在内部异常时返回 `None`，不阻断 `content` 发送。
