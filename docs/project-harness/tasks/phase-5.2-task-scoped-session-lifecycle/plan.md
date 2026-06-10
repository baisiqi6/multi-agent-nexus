> **Historical record.** Current source of truth: `docs/project-harness/progress.md` and `docs/project-harness/scope.md`. This file is preserved as part of the dogfood development audit chain.

# Phase 5.2：Task-Scoped Session Lifecycle

## 背景

当前 multinexus 的 managed agent 已经支持 CLI session resume，但 session scope 仍主要来自 Discord channel/thread id。对于 coordinator 派发的工程任务，这会带来两个问题：

- 同一个频道里的不同任务可能复用同一个 agent session，旧上下文会污染新任务。
- task closeout / done 后，旧 session 仍可能保持 active，后续消息误触发 resume。

Phase 5.2 的目标是把 coordinator handoff 产生的工程任务切到 task-scoped session，并在任务结束后能明确 stale/archive。

## 范围

### multinexus

1. 定义统一 scope key 规则：
   - 普通频道消息：`channel:<channel_id>`
   - thread 消息：`thread:<thread_id>`
   - coordinator task handoff：`task:<workspace_id>:<task_id>`
2. coordinator handoff prompt 调用 adapter 时，优先使用 task scope。
3. SessionStore 增加按 scope 前缀或 task scope 管理 session 的能力：
   - 查询 active/stale session。
   - 将 task scope session 标记为 stale 或 archived。
4. operator command / slash command 输出中明确 scope 类型：
   - channel scope
   - thread scope
   - task scope
5. 为 task-scoped session lifecycle 增加测试：
   - handoff 使用 task scope，而不是 channel scope。
   - 同一 task、同一 agent 第二次调用 resume 同一 session。
   - 不同 task 不复用 session。
   - closeout/done 后 task session 被 stale/archive 后不再 resume。

### multi-agent-coordinator

1. 确认已有 `task.done`、`assignment.closeout` 等 lifecycle event 足够让 multinexus 判断 session 结束。
2. 如果需要新增 delivery/event 语义，应保持窄范围，只服务 session lifecycle。
3. 不允许从 Discord 文本直接触发 destructive lifecycle 操作。

### 文档

1. 更新 `docs/agent-session-persistence-design.md`：
   - 明确 channel/thread/task 三种 scope 的优先级。
   - 明确 coordinator task 完成后 session 应 stale/archive。
2. 更新 `docs/project-harness/runbook.md`：
   - 增加 operator 排查 task session 污染的步骤。

## 非目标

- 不删除 Claude/Codex/OpenCode CLI 自己保存的历史文件。
- 不重写 adapter resume 协议，除非发现明确 bug。
- 不引入远程 session service。
- 不把所有 agent 合并成共享 session。
- 不改变 coordinator plan gate、merge gate 或 deploy gate 语义。

## 建议实现顺序

1. 小步实现 scope key helper，并为 helper 写单元测试。
2. 让 coordinator handoff runtime 将 `workspace_id/task_id` 传入 adapter request scope。
3. 扩展 SessionStore 的 stale/archive 能力，保留旧 schema 的兼容路径。
4. 更新 session status/reset 输出，避免 operator 混淆当前 scope。
5. 补文档和 runbook。
6. 跑完整测试后请求 review。

## 验收标准

- coordinator handoff 进入 adapter 时使用 `task:<workspace_id>:<task_id>` scope。
- 不同 task 不复用同一个 CLI session。
- task session stale/archive 后，下一次同 task 调用走 fresh call。
- 普通 channel/thread session 行为保持兼容。
- `/session status` 和文本 `session status` 能看出当前 scope 类型。
- 相关单元测试和现有全量测试通过。

## Worker 注意事项

- 不要直接编辑 `docs/project-harness/mvp-checklist.json`。
- 不要提交真实 `agents.toml`、`.env`、token、webhook。
- 如果实现需要 coordinator 侧配合，先做最小可测试改动，并在 Discord 里用 `[agent-report] action=blocker` 或 progress 说明。
- 每个可见阶段应在 Discord 中发人类可读进度，并在最后单独一行附 `[agent-report]`。
