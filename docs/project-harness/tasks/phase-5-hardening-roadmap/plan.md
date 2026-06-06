# Phase 5 硬化路线图

## 背景

Phase 4 已经证明 coordinator 可以驱动一条真实的 Discord 任务流：

1. coordinator bot 发送定向 handoff。
2. multinexus managed agent 自动接受 assignment。
3. agent 读取 task-scoped `worker-bootstrap.md`。
4. agent 通过结构化 `[agent-report]` 消息回报进展。
5. coordinator 记录事件、推送 Discord 可见状态，并镜像 harness state。

下一阶段不应急着扩展更多平台和部署能力，而应先把这条已经在使用的核心链路打牢。

## 目标

让 coordinator + multinexus 的协作闭环足够可靠，可以支撑长程、多 agent 的工程开发。

优先加固已经投入使用的 runtime 路径：

- coordinator 定向 handoff
- managed agent 自动 accept
- task-scoped bootstrap 和 session state
- 结构化 progress / blocker / done / review report
- operator 可观测性和新项目接入体验

## 执行模型

这些 phase 默认按下面方式推进：

- Worker implementation 可以交给 Claude Code 这类 coding agent。
- 默认优先指定 Claude 作为 coding worker；Codex 额度较少，优先用于 review/operator。
- Codex/operator 负责审核计划、diff、测试结果和协议边界，除非明确需要 Codex 亲自实现。
- 每个 phase 都应切成小块，便于单独 review。
- 没有人类明确批准时，不 merge、不 deploy、不启动长驻服务。
- 不直接编辑 harness JSON。状态变更应通过 coordinator 或合适的 harness tooling 路径完成。
- 协议 token 必须保持稳定：`[handoff]`、`[agent-report]`、`workspace_id=`、`task_id=`、`action=...`、`bootstrap=...`。
- dogfood 期间发现的 UX/运行问题应记录到 `docs/project-harness/dogfood-feedback.md`；控制面/CLI 缺口同步记录到 `multi-agent-coordinator/docs/operator-needs-backlog.md`。

## Phase 5.1: Handoff Runtime Hardening And Agent-Report Protocol

### 目标

让现有 coordinator handoff runtime 路径可测试、可复现、可文档化。

### 范围

`multinexus`：

- 为 `DiscordClient._try_coordinator_handoff` 补 runtime 单元测试。
- 验证 accept 失败时会发送 `[agent-report] action=blocker`，并且不会调用 adapter。
- 验证 accept 成功时会发送 accept report、读取 bootstrap，并用 bootstrap prompt 调用 adapter。
- 验证 bootstrap 缺失时仍会调用 adapter，但 prompt 必须明确说明 bootstrap missing。
- 断言 report 发送使用 `AllowedMentions.none()`，避免误触发其他 bot。
- 自动动作范围继续只允许 `assignment.accept`。

`multi-agent-coordinator`：

- 文档化 coordinator 接受的 `[agent-report]` 格式。
- 验证 daemon ingest 支持 `progress`、`blocker`、`done` 以及当前支持的 review 类 report。
- 保持 `progress.reported` 可见，但不改变 lifecycle 状态。

Docs：

- 新增或更新 agent-report protocol 文档。
- 明确 runtime auto-accept 已经发生在 worker prompt 开始之前。
- 明确什么时候用 Discord report，什么时候用 coordinator CLI。

### 非目标

- 不从 Discord 文本自动执行 `mark-done`、`closeout`、merge、deploy 或 PR 操作。
- 不改变 session persistence 设计。
- 不改变 plan gate 或 merge gate 语义。
- 不增加新的生产依赖。

### 验收标准

- `multinexus` 测试覆盖 handoff 成功、失败、bootstrap 缺失等 runtime 行为。
- `multi-agent-coordinator` 测试覆盖已支持 report 的 ingest 和可见 progress 渲染。
- Agent-report 格式写入 tracked docs。
- 两个 repo 的相关测试全部通过。

## Phase 5.2: Task-Scoped Session Lifecycle

### 目标

防止长期 task session 无限增长，或在任务完成后继续污染后续上下文。

### 范围

`multinexus`：

- 定义 task scope 规则：
  - channel/thread scope 继续用于普通聊天。
  - coordinator handoff 在存在 `workspace_id` + `task_id` 时优先使用 task scope。
  - task 到达 closeout / done 后，task-scoped session 应 archive 或 stale。
- 在可行范围内增加 task-scoped session status/reset。
- 更新 session status 输出，区分 channel/thread scope 和 task scope。
- 为 task closeout/done 后 session archive/stale 行为补测试。

`multi-agent-coordinator`：

- 确保 task lifecycle 事件足够可观测，使 multinexus 能判断何时 stale/archive session。
- 能事件驱动就优先事件驱动，避免不必要轮询。

Docs：

- 更新 `docs/agent-session-persistence-design.md`。
- 文档化 task scope、thread scope、channel scope 的使用场景。

### 非目标

- 不删除 Claude/Codex/OpenCode 的 CLI 原生 session 历史。
- 不修改 adapter resume 参数，除非发现明确 bug。
- 不引入远程 session service。

### 验收标准

- closeout/done 后的 task session 不会被意外复用。
- operator 可以查看和 reset task-scoped session。
- 现有 channel/thread session 行为保持兼容。
- 测试覆盖 stale/archive 行为。

## Phase 5.3: Agent Registry Auto-Sync

### 目标

减少 multinexus `agents.toml` / `external_agents` 与 coordinator workspace agent registry 之间的配置漂移。

### 范围

`multi-agent-coordinator`：

- 增加命令或服务，从 multinexus TOML 文件同步 workspace agent registry。
- 默认保留手工 override，除非显式要求替换。
- 校验缺失或重复的 `discord_user_id`。
- 输出变更摘要，但不打印 token 或被忽略的敏感配置。

`multinexus`：

- 确保 `agents.toml.example` 文档化 coordinator sync 需要的字段。
- 继续避免提交真实 `agents.toml`。

Docs：

- 在 runbook 中加入 targeted handoff 测试前的 registry sync 步骤。

### 非目标

- 不要求 coordinator import multinexus runtime modules。
- 不把 Discord bot token 存进 coordinator DB。
- 本 phase 不做后台连续自动同步。

### 验收标准

- 一个命令可以把 managed 和 external agent ID 同步到 coordinator。
- target agent 未注册时 handoff fail closed。
- 测试覆盖 add、update、no-op 和 invalid config。

## Phase 5.4: Workspace Doctor And Full Harness Init

### 目标

降低新项目接入 coordinator/harness 的出错率。

### 范围

`multi-agent-coordinator`：

- 改进 `workspace add` 或 `workspace doctor` 输出，至少显示：
  - harness root 是否存在
  - `harnessctl` 是否存在且可执行
  - checklist/state 文件是否有效
  - mutation lifecycle 是否可用
  - default bus/destination 是否已配置
- 增加完整 harness 初始化路径，可以从已知 harness template 实例化 `scripts/harness/` runtime。
- 保留现有 minimal file-backed harness 路径作为 fallback。

Docs：

- 更新 coordinator operator 文档和 multinexus runbook，写明推荐 onboarding 顺序。

### 非目标

- 不静默重写已有 harness state。
- 不把 validation failure 包装成绿色状态。
- 不强制非 Discord workspace 配 Discord 配置。

### 验收标准

- 新 workspace 可以在不手工复制 harness runtime 文件的情况下完成初始化和诊断。
- Doctor output 能清楚暴露缺失能力。
- 测试覆盖 missing harnessctl、invalid checklist、healthy workspace。

## Phase 5.5: Discord Message Rendering

### 目标

将 coordinator 和 agent 的结构化事件渲染成更适合 Discord 阅读的消息，而不是把大段原始文本直接丢进频道。

### 范围

`multi-agent-coordinator`：

- 为 Discord delivery 增加 renderer 层，把 event/delivery payload 转成 Discord embeds。
- 覆盖以下消息类型：
  - `plan.ready` / `plan.approved`
  - worker handoff prepared / targeted handoff
  - `assignment.accepted`
  - `progress.reported`
  - `review.completed`
  - `task.done`
  - `reconciliation.completed`
  - `workspace doctor` summary（如果通过 Discord 展示）
- 输出应包含清晰字段：
  - workspace
  - task
  - owner / target agent
  - status / action
  - branch
  - tests / validation
  - next step
  - risk / blocker
- 长文本只保留摘要，详细内容引用计划路径、bootstrap 路径、closeout packet 或 commit。

`multinexus`：

- 保持 managed agent 的触发协议稳定：
  - `[handoff]` 必须仍作为普通 message content 出现。
  - `[lifecycle]` 必须仍作为普通 message content 出现。
  - `allowed_mentions` 仍严格限制在目标 user。
- 如果 coordinator 通过 bot API 支持 embed delivery，multinexus 不需要重复渲染。

### 非目标

- 不改变 `[handoff]` / `[lifecycle]` / `[agent-report]` 机器协议。
- 不把所有 agent 自然语言回复强制改成 embed。
- 不引入 Discord button/modal/select menu，除非后续单独规划。
- 不牺牲 external gateway agent 的兼容性。

### 验收标准

- Discord 中 status/review/done/progress 类消息可读性明显提升。
- Handoff/lifecycle 仍能触发目标 managed agent。
- 单元测试覆盖 renderer 输出和 allowed_mentions。
- 真实 Discord dogfood 验证至少一条 handoff、一条 progress、一条 review/done 消息。

## 维护小切片

这些任务有价值，但建议穿插在 Phase 5 大块之间做，避免长期积累。

### SQLite ResourceWarning Cleanup

- 修复 coordinator full test suite 中 unclosed sqlite connection warning。
- 作为独立小 commit 处理。
- 验收：full tests 通过，且没有 `ResourceWarning` 噪声。

### Operator Backlog Triage

- 审查 `/Users/yinxin/projects/multi-agent-coordinator/docs/operator-needs-backlog.md`。
- 将条目标成 `done`、`partial`、`superseded` 或 `open`。
- 已完成项尽量链接到对应 commit 或文档。

### Documentation Sync

- 更新仍把 coordinator integration 描述为未来工作的过时文档。
- 重点检查：
  - `docs/discord-multibot-plan/multi-bot-refactor-plan.md`
  - `docs/multi-agent-harness-overview.md`
  - `docs/project-harness/runbook.md`
  - coordinator operator skill docs，如果 workflow 有变化

## 暂缓到确实需要时再做

这些需求是真实的，但应等核心闭环稳定后再投入：

- systemd 云服务器部署
- Windows service/startup scripts
- 日志轮转和更丰富的 status scripts
- long-running coordinator job worker

## 建议执行顺序

1. Phase 5.1: Handoff Runtime Hardening And Agent-Report Protocol
2. Maintenance: SQLite ResourceWarning cleanup
3. Phase 5.2: Task-Scoped Session Lifecycle
4. Maintenance: Operator backlog triage
5. Phase 5.3: Agent Registry Auto-Sync
6. Maintenance: Documentation sync
7. Phase 5.4: Workspace Doctor And Full Harness Init
8. Phase 5.5: Discord Message Rendering
9. 重新评估 systemd / Windows / long-running job worker

## Review Gates

每个 phase 都应包含：

- worker implementation 前先做 plan review
- implementation 后做 code review
- 跑完整相关测试
- diff 中不能包含 secrets
- 除非明确声明为 harness maintenance，否则不直接改 harness JSON
- Discord runtime 行为只在人类批准 live testing 后手动验证
