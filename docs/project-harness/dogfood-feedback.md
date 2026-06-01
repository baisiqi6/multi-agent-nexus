# Dogfood Feedback

本文件记录真实使用 coordinator + discord-nexus 多 agent 协作时暴露的 UX、协议和运行体验问题。

记录原则：

- 保留原始问题，不只记录最终修复。
- 标注状态：`fixed`、`mitigated`、`open`、`deferred`。
- 能顺手修的小问题可以直接修，但仍要留下问题和修复记录。
- 默认将 Claude 作为 coding worker，Codex 优先用于 review/operator；只有明确需要 Codex worker 时再派给 Codex。

## 2026-06-01

### 1. Codex worker 额度限制导致任务中断

- 状态：mitigated
- 原始现象：Phase 5.3 派给 `mac-codex` 后，Codex CLI 返回 usage limit，需要等到 23:27 后再试。
- 影响：任务不是因为代码或 coordinator 协议失败，而是 worker 额度不可用；如果继续默认派 Codex，会浪费调度时间。
- 临时处理：将 Phase 5.3 reroute 给 `mac-claude`，任务完成。
- 后续规则：默认 coding worker 使用 Claude；Codex 主要承担 review/operator。
- 待修方向：coordinator 的 worker selection 可以支持 agent availability / quota 状态，避免把任务派给当前不可用的 agent。

### 2. 历史 lifecycle 事件被新协议补发到 Discord

- 状态：open
- 原始现象：Phase 5.3 dogfood 时，`policy pump-events` 因 message key 变化，为历史 Phase 5.1 lifecycle 事件补发了一条新的 Discord 消息。
- 影响：不会再触发 worker 执行，但会造成频道噪声，并让人误以为旧任务刚刚发生。
- 当前处理：已记录到 `multi-agent-coordinator/docs/operator-needs-backlog.md`。
- 待修方向：`policy pump-events` 增加 `--since-event-id`、`--created-after`、`--task-id` 或 migration guard。

### 3. Managed agent 缺少稳定的中途进展通道

- 状态：open
- 原始现象：Phase 5.4 dogfood 中，`mac-claude` 成功 auto-accept 并执行任务，但在长时间运行期间 Discord/Coordinator 只看到 accept，没有看到阶段性 progress。
- 影响：人类观察者很难判断 worker 是在正常执行、卡住、还是忘记汇报；群聊看起来仍像 coordinator 单向广播。
- 当前处理：已记录到 `multi-agent-coordinator/docs/operator-needs-backlog.md`。
- 待修方向：
  - 增加明确的 `agent report` / `assignment progress` CLI。
  - worker bootstrap 中给出可执行的中途汇报命令，而不是只提示最终回复里写 `[agent-report]`。
  - daemon 将 progress report 渲染成 Discord 可见消息。

### 4. Agent 最终 report 可能被 message.edit 吃掉

- 状态：fixed
- 原始现象：如果 agent 的最终回复通过编辑 placeholder 发送，外部 watcher 只监听 `MESSAGE_CREATE` 时看不到 `[agent-report]`。
- 影响：worker 明明回复了 done/progress，但 coordinator 可能 ingest 不到。
- 修复：`discord-nexus` 将 `[agent-report]` 行拆出来，用独立 `channel.send()` 发送，避免只出现在 edited message 中。
- 验证：Phase 5.4 中 `mac-claude` 的 `action=done` 已被 coordinator ingest。

### 5. Workspace doctor 可能把 validation failure 包装成绿色状态

- 状态：fixed
- 原始现象：Phase 5.4 review 时发现 `workspace doctor` 先根据文件和 harnessctl 可执行性判断 `full_harness_runtime`，CLI 退出码只看 mode；如果 `harnessctl validate` 失败，仍可能退出 0。
- 影响：新项目接入时会把无效 harness 误判为健康，后续 assignment mutation 才失败。
- 修复：`workspace doctor` 现在在 `harnessctl validate` 或 `harnessctl doctor` 失败时返回非 0。
- 验证：新增测试覆盖 validate failure；coordinator 665 tests OK。

### 6. Discord 可见消息仍偏原始文本

- 状态：open
- 原始现象：coordinator 的 handoff、state、lifecycle、review summary 仍以大段纯文本为主。结构化字段存在，但没有充分利用 Discord embeds/cards/fields。
- 影响：群聊可读性差，人工扫描成本高；状态、owner、branch、风险、下一步等信息没有视觉层级。
- 建议方向：新增 Discord renderer，把内部 event/delivery payload 渲染成 Discord embeds。
- 设计原则：
  - `[handoff]` 和 `[lifecycle]` 这类需要触发 bot 的协议行仍保留纯文本正文，避免破坏触发规则。
  - 状态、review、done、progress、doctor 这类面向人看的消息用 embeds fields 展示。
  - 长文本放摘要 + 链接/文件路径，不直接刷屏。
  - Discord 没有真正表格，优先用 embed fields、bullet list、code block 小表格。

### 7. Handoff packet 中部分字段不够可读

- 状态：open
- 原始现象：reroute 时生成的 `current/handoff-packet.md` 中 `Current Handoff` 出现 `{'from': None, 'to': None, 'reason': None}` 这类原始 dict 表达。
- 影响：不影响运行，但 review/审计文档可读性差。
- 待修方向：harness packet 生成器应把空 handoff 渲染为 `None` 或更友好的字段列表。

## 后续建议排期

1. Phase 5.5: Discord Message Rendering
2. Maintenance: pump-events 历史 delivery 过滤
3. Maintenance: agent progress CLI / worker 中途汇报通道
4. Maintenance: handoff/closeout packet 可读性修复
