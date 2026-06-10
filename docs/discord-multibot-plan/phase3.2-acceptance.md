> **Historical design note.** Current source of truth: `docs/project-harness/architecture.md` and `docs/project-harness/scope.md`. This file is preserved for historical context only.

# Phase 3.2 验收记录

## 概述

Phase 3.2 完成了 Discord 原生 slash commands 的 operator 入口，并在 Round 2 将主要 operator slash 输出升级为 embeds。该阶段目标是提升 Discord cockpit 的可操作性和可读性，不改变 Phase 2/2.1 已固化的 managed/external agent 边界。

## 基线

Round 1 基线提交：

```text
b04326b Add slash commands (/agents, /health, /session status, /session reset)
```

Round 2 当前仍在工作区，提交 SHA 待提交后补充。

测试命令：

```bash
.venv/bin/python -m unittest discover tests/
```

当前验证结果：

```text
106 tests OK
```

说明：本项目测试应使用 `.venv/bin/python` 运行；裸 `python` 可能缺少 `discord.py` 等项目依赖。

## Round 1：Slash Commands

已实现并在 Discord 真实验证：

| Slash command | 状态 | 说明 |
|---|---|---|
| `/agents` | 通过 | 列出 known agents，区分 managed / external |
| `/health` | 通过 | 执行当前 agent adapter health check |
| `/session status` | 通过 | 查看当前 channel/thread scope 的 session 状态 |
| `/session reset` | 通过 | 将当前 scope 的 active session 标记为 stale |

验收结果：

- Slash commands 在 Discord UI 中可见。
- 四个命令均可执行。
- 回复为 ephemeral。
- channel allowlist 对 slash commands 生效。
- `session reset` 权限逻辑保持不变，需要 explicit operator permission。
- 文本 operator commands 保持兼容。

## Round 2：Embed Operator 输出

已实现并在 Discord 真实验证：

| Slash command | 输出形式 | 状态 | 说明 |
|---|---|---|---|
| `/agents` | Embed | 通过 | 使用 `Managed` / `External` fields 分组展示 |
| `/health` | Embed | 通过 | 使用结构化字段展示 adapter、bin、available、work_dir、model、timeout |
| `/session status` | Embed | 通过 | 展示 scope、session_id、adapter、work_dir、status、turns、updated、active sessions |
| `/session reset` | Ephemeral text | 通过 | 保持简单确认文本，避免扩大改动范围 |

颜色规则：

- `/agents` 使用 neutral / blurple 风格。
- `/health` 可用时为 green，不可用或 health check error 时为 red。
- `/session status` 有 active session 时为 green，无 active session 时为 gold。

验收结果：

- `/agents`、`/health`、`/session status` 已 embed 化。
- `/session reset` 保持简单 ephemeral text。
- 所有 slash 回复继续为 ephemeral。
- Embed 输出未破坏文本命令兼容。
- Discord 手测通过。

## 安全边界

Phase 3.2 后仍保持以下边界：

- Managed adapter agent 被 bot 触发时，仍必须满足 `[handoff] + Discord @mention`。
- External gateway agent 的触发规则仍由各自 Gateway 决定。
- Operator slash 输出继续使用 `allowed_mentions=discord.AllowedMentions.none()`。
- Operator 输出不使用 `<@id>` 展示 agent，避免 ping external bots。
- `/agents` 使用 `discord_id: \`...\`` 展示 Discord ID。
- Slash commands 不改变 `respond_to_bots` 行为。
- Slash commands 不改变 session scope。
- Slash commands 不改变 adapter 调用逻辑。
- 本阶段未启动 Hermes / 小龙虾 adapter。

## 文本命令兼容

以下文本 operator commands 继续可用，且仍为纯文本输出：

- `@bot agents`
- `@bot health`
- `@bot session status`
- `@bot session reset`

保留纯文本的原因：

- 降低回归风险。
- 兼容已有操作习惯。
- 将 Round 2 的改动范围限制在 slash UX。

## 已知限制

1. Slash command sync 仍以当前单 Discord server 使用场景为目标；多 guild 部署暂不扩展。
2. `/session reset` 暂不 embed 化，保持简单 confirmation text。
3. 尚未引入 Discord buttons/select menus/modal。
4. 尚未接入 multi-agent-coordinator 的 task/status/assignment。
5. 运行常驻化仍未完成，managed bots 仍需要后续 launchd/scripts 支持。

## 下一步

建议进入运行可靠性小切片：

1. 为 Mac 上 managed bots 增加 launchd 常驻化配置。
2. 提供 `scripts/start.sh`、`scripts/stop.sh`、`scripts/status.sh`。
3. 固定日志到 `logs/*.log`。
4. 待 Discord 侧和运行侧稳定后，再接入 multi-agent-coordinator。
