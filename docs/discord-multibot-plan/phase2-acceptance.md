# Phase 2 验收记录

## 概述

Phase 2 实现了混合架构部署：discord-nexus 托管 coding agents（Claude、Codex、OpenCode），小龙虾/OpenClaw 和 Hermes 保留原生 Gateway。所有 agent 通过 Discord 消息自然互联。

## 已验证的 Handoff 链路

### Managed → External

| 链路 | 状态 | 备注 |
|------|------|------|
| Mac Claude → 小龙虾 | ✅ 已验证 | 需小龙虾 users 白名单包含 bot ID + `allowBots` |
| Mac Codex → 小龙虾 | ✅ 已验证 | 同上 |
| Mac Claude → Hermes | ✅ 已验证 | Hermes 无白名单限制 |

### External → Managed

| 链路 | 状态 | 备注 |
|------|------|------|
| 小龙虾 → Mac Claude | ✅ 已验证 | `respond_to_bots=true`，小龙虾通过 @mention 触发 |
| 小龙虾 → Mac Codex | ✅ 已验证 | 同上 |
| 小龙虾 → Mac OpenCode | ✅ 已验证 | 同上 |
| Hermes → Mac Codex | ✅ 已验证 | 同上 |
| Hermes → 其他 Managed | ✅ 已验证 | 同上 |

### External ↔ External

| 链路 | 状态 | 备注 |
|------|------|------|
| 小龙虾 ↔ Hermes | ✅ 已验证 | 双向 @mention 互通 |

### Managed → Managed

| 链路 | 状态 | 备注 |
|------|------|------|
| Mac Claude ↔ Mac Codex | ✅ 已验证 | `respond_to_bots=true` + `[handoff]` + @mention |

## Session 持久化

- **实现**：SQLite sessions 表，scope_id + agent_id 为复合主键
- **Scope 隔离**：每个 thread 用自己的 `channel.id`，不共享 parent channel 的 session
- **Resume**：第二次调用同 agent/同 scope 自动 resume CLI session
- **Stale 处理**：resume 失败或 work_dir 变化时标记 stale，自动 fallback 到 fresh call
- **测试**：7 个单元测试覆盖 get/upsert/mark_stale/scope 隔离/turn_count/reactivate

## Adapter 修复

| Adapter | 修复项 |
|---------|--------|
| Codex | resume 命令修正（去掉 --sandbox）、错误检测、timeout/work_dir 透传、stderr 处理 |
| Claude | session ID 从 `init` 事件捕获、`--resume` 参数支持 |
| OpenCode | sessionID 从事件流捕获、`--session` 参数支持 |
| Hermes | AdapterResult 适配（无 session 支持） |

## Handoff 投递修复

- 每条 `[handoff]` 行作为独立 `channel.send()` 发出（MESSAGE_CREATE）
- 显示文本通过 `placeholder.edit()` 更新（MESSAGE_UPDATE）
- 外部 bot 只监听 MESSAGE_CREATE，所以 handoff 必须走 `channel.send()`
- handoff line strip、超长截断 1900 字符
- 7 个单测覆盖各种 handoff 分割场景

## 外部 Agent 约束

### 小龙虾/OpenClaw

- **我们无法控制其 handoff 格式**：小龙虾是独立 LLM bot，它发什么内容取决于自己的 prompt
- **已知要求**：
  1. `guilds.users` 白名单必须包含所有 managed bot 的 user ID
  2. `allowBots` 设置为 `"mentions"` 或 `true`
  3. 小龙虾的 `mentionPatterns` 需要配置 managed bot 的 mention 格式
- **潜在问题**：如果小龙虾回复里 @了我们的 bot 但没写 `[handoff]` 前缀，会被过滤掉。这可能需要放宽约束（对已知外部 bot 只要求 @mention，不要求 `[handoff]`）

### Hermes

- 独立 Gateway bot，handoff 格式取决于其自身配置
- 无 users 白名单问题

## 测试覆盖

- 总计 57 个单元测试
- `test_session_store.py`：7 个（SessionStore CRUD + 隔离）
- `test_handoff_split.py`：7 个（handoff 分割）
- `test_hermes_adapter.py`：13 个（Hermes adapter）
- `test_mentions.py`：11 个（mention 路由 + handoff 检测）
- `test_external_agents.py`：~19 个（external agent 配置）

## 当前限制

1. ~~**外部 bot handoff 格式不可控**~~ — 实测验证外部 bot 通过 @mention 即可触发 managed bot，`[handoff]` 前缀不是硬性障碍
2. **无 slash 命令** — 目前只能通过 @mention 或 !bang 触发
3. **无 wiki/scratch/discoveries** — Phase 3 功能
4. **无 streaming placeholder 增强** — 当前只有心跳计时，无真正的 partial output 展示
5. **nexus.py 日志级别** — 仍为 DEBUG，应改为 INFO
6. **OpenCode `--dangerously-skip-permissions`** — 该 flag 在 opencode CLI 不存在，配置值被忽略但未报错
7. **无自动启动** — 所有 bot 需手动 `python nexus.py --agent <id>` 启动

## Phase 3 前置条件

Phase 3（slash commands、wiki、embeds 等）建立在本阶段的基础上。进入 Phase 3 前建议：

1. ✅ 完成外部 bot → managed bot 的真实 handoff 验证
2. 考虑放宽 managed bot 对外部 bot 消息的 `[handoff]` 前缀要求
3. 将 nexus.py 日志级别改为 INFO
