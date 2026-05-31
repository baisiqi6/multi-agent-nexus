# Agent-Report 协议

`agent-report` 是 discord-nexus managed agent 在 coordinator handoff 执行期间发回 Discord 的结构化状态报告。它的目标是让 coordinator daemon 能摄取 agent 进展，同时让频道里的人能读懂当前状态。

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

## 支持的 Action

| Action | 何时使用 | 生命周期影响 |
|--------|----------|--------------|
| `accept` | runtime auto-accept 成功 | 记录接收事实；真正的 assignment 状态已由 runtime 先调用 coordinator CLI 改掉 |
| `progress` | worker 完成一个小阶段 | 可见进度事件，不改变任务生命周期 |
| `blocker` | worker 无法继续 | 记录阻塞报告，通常需要 operator 或 reviewer 决策 |
| `done` | worker 认为实现完成 | 只记录完成报告；不会自动 closeout 或 mark-done |

`done` 不等于任务关闭。正式进入 closeout / review / mark-done 仍然必须通过 coordinator CLI：

```bash
mac.sh assignment closeout discord-nexus --task-id <id> --reviewer <name>
mac.sh assignment mark-done discord-nexus --task-id <id>
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
