> **Historical record.** Current source of truth: `docs/project-harness/progress.md` and `docs/project-harness/scope.md`. This file is preserved as part of the dogfood development audit chain.

# Phase 5.3 Agent Registry Auto-Sync

## 背景

Phase 4.5 后，coordinator 可以通过 `workspace agent add` 维护 workspace agent registry，并用 `task handoff --target-agent ...` 精准发送 Discord handoff。

当前问题是 registry 仍然靠人工维护。`multinexus/agents.toml` 里已经有 managed agents 和 external agents 的 `discord_user_id`，coordinator DB 里也有一份 agent registry。两边一旦漂移，handoff 会出现两类问题：

- target agent 未注册，handoff fail closed。
- target agent 注册了旧 ID，handoff 发错人或无人响应。

本 phase 要把同步动作变成显式、可测试、可审计的 coordinator 命令。

## 目标

增加一个从 `multinexus` TOML 配置同步 agent registry 到 coordinator workspace 的能力，降低手工 `workspace agent add` 的维护成本。

## 实施范围

### multi-agent-coordinator

新增 workspace agent sync 能力：

```bash
skills/coordinate-operator/scripts/mac.sh \
  workspace agent sync multinexus \
  --source /Users/yinxin/projects/multinexus/agents.toml
```

行为要求：

- 只读取 agent 元数据，不读取、不输出 token、token env 实际值、`.env` 或 webhook URL。
- 支持 `[[agents]]` 和 `[[external_agents]]`。
- 从每个 agent 读取：
  - `id`
  - `display_name`
  - `discord_user_id`
  - agent 类型：`managed` 或 `external`
- 缺少 `discord_user_id` 的条目默认跳过，并在 summary 中列出 skipped。
- 重复 `id` 或重复 `discord_user_id` 默认 fail closed。
- 默认 merge 到现有 registry，不删除手工 override。
- 增加 `--replace` 时才允许用 TOML 结果替换整个 registry。
- 输出 JSON summary：
  - `added`
  - `updated`
  - `unchanged`
  - `skipped`
  - `errors`
- 保持现有 `workspace agent add` 可用。

建议实现：

- 在 `src/multi_agent_coordinator/db.py` 增加批量 registry 更新 helper。
- 新增 `src/multi_agent_coordinator/agent_registry.py`，使用标准库 `tomllib` 解析 TOML。
- 在 `src/multi_agent_coordinator/cli.py` 增加 `workspace agent sync` 子命令。
- 为 DB helper、TOML 解析、CLI sync 各补单元测试。

### multinexus

只做文档和示例补充：

- `agents.toml.example` 标明 `discord_user_id` 是 coordinator registry sync 的输入字段。
- `docs/project-harness/runbook.md` 加入 targeted handoff 前的 sync 步骤。

## 非目标

- 不让 coordinator import `multinexus.config` 或其他 multinexus runtime module。
- 不把 Discord bot token、`.env`、webhook URL 或真实 `agents.toml` 提交到仓库。
- 不做后台自动同步 daemon。
- 不改变 handoff、lifecycle、agent-report 协议。
- 不改变现有 workspace schema 以外的 task/harness lifecycle 语义。

## 安全边界

- 命令输出必须避免泄露 secrets。
- 真实 `agents.toml` 是 ignored 文件，只可本地读取，不可提交。
- 如果 TOML 里发现重复 ID 或重复 Discord user ID，应返回非零退出码，避免写入不可信 registry。

## 测试计划

在 `multi-agent-coordinator`：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```

新增/覆盖：

- sync managed + external agents 成功。
- 缺少 `discord_user_id` 被 skipped，不报错。
- 重复 `id` fail closed。
- 重复 `discord_user_id` fail closed。
- 默认 merge 不删除已有 override。
- `--replace` 删除 TOML 中不存在的旧 registry entry。
- CLI 输出不包含 token 字段或环境变量实际值。

在 `multinexus`：

```bash
.venv/bin/python -m unittest discover tests
scripts/harness/harnessctl validate
```

## 验收标准

- 可以用一个 coordinator 命令从本地 `agents.toml` 同步 coordinator registry。
- `task handoff --target-agent mac-codex` 仍然只向目标 agent 发送定向 handoff。
- target agent 未注册时仍然 fail closed。
- 文档写清楚 registry sync 是 targeted handoff 前的推荐步骤。
- 两个 repo 的相关测试通过。

## 建议 worker

优先交给 `mac-codex` 实现。该任务需要改 coordinator CLI 和测试，同时补 multinexus 文档。
