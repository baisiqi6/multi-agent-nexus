# Handoff Packet

## Subject

- Checklist item: `phase-5.3-agent-registry-auto-sync`
- From: `mac-codex`
- To: `mac-claude`
- Requested by: `codex-operator`
- Updated at: `2026-06-01`
- Reason: mac-codex Codex CLI usage limit until 23:27; rerouting implementation to mac-claude
- Canonical plan path: `docs/project-harness/tasks/phase-5.3-agent-registry-auto-sync/plan.md`

## Item Snapshot

- Title: Phase 5.3 Agent Registry Auto-Sync
- Status: doing
- Workflow status: running
- Priority: p1
- Current owner: mac-codex
- Current session: auto-mac-codex-1780314286

## Acceptance

Use the plan acceptance criteria as source of truth: docs/project-harness/tasks/phase-5.3-agent-registry-auto-sync/plan.md

## Current Handoff

{'from': None, 'to': None, 'reason': None}

## Canonical Plan Content

```md
# Phase 5.3 Agent Registry Auto-Sync

## 背景

Phase 4.5 后，coordinator 可以通过 `workspace agent add` 维护 workspace agent registry，并用 `task handoff --target-agent ...` 精准发送 Discord handoff。

当前问题是 registry 仍然靠人工维护。`discord-nexus/agents.toml` 里已经有 managed agents 和 external agents 的 `discord_user_id`，coordinator DB 里也有一份 agent registry。两边一旦漂移，handoff 会出现两类问题：

- target agent 未注册，handoff fail closed。
- target agent 注册了旧 ID，handoff 发错人或无人响应。

本 phase 要把同步动作变成显式、可测试、可审计的 coordinator 命令。

## 目标

增加一个从 `discord-nexus` TOML 配置同步 agent registry 到 coordinator workspace 的能力，降低手工 `workspace agent add` 的维护成本。

## 实施范围

### multi-agent-coordinator

新增 workspace agent sync 能力：

```bash
skills/multi-agent-coordinator-operator/scripts/mac.sh \
  workspace agent sync discord-nexus \
  --source /Users/yinxin/projects/discord-nexus/agents.toml
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

### discord-nexus

只做文档和示例补充：

- `agents.toml.example` 标明 `discord_user_id` 是 coordinator registry sync 的输入字段。
- `docs/project-harness/runbook.md` 加入 targeted handoff 前的 sync 步骤。

## 非目标

- 不让 coordinator import `discord_nexus.config` 或其他 discord-nexus runtime module。
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

在 `discord-nexus`：

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

优先交给 `mac-codex` 实现。该任务需要改 coordinator CLI 和测试，同时补 discord-nexus 文档。
```

## Recent Progress

```md
uite: 134 pass (122 existing + 12 new).

## 2026-05-29

### Round 1 — Initial implementation

- Worker implemented all Phase 3.3 launchd artifacts:
  - 3 plist templates (`launchd/com.discord-nexus.mac-{claude,codex,opencode}.plist`)
  - Shared lib (`scripts/lib/launchd.sh`)
  - 4 management scripts (`scripts/{start,stop,status,uninstall}.sh`)
- Fixed `start.sh` plist update semantics: `bootout` + `bootstrap` cycle replaces `kickstart -k` so launchd reloads changed plists.
- Added launchd documentation section to `docs/platform-setup.md`.
- Static validation passed: `plutil` 3/3, `bash -n` all pass, 106 tests OK.
- Submitted for review.

### Round 2 — Review findings addressed

- **Finding 1**: `check_manual_process` in `scripts/lib/launchd.sh` used a narrow `pgrep -f "nexus.py --agent $agent"` pattern that missed invocations with intervening flags (e.g. `python nexus.py --config agents.toml --agent mac-claude`). Fixed to `nexus\.py.*--agent[= ]${agent}\>` which matches `--agent X` and `--agent=X` regardless of flag order.
- **Finding 2**: Closeout file list was incomplete (omitted 5 of 9 artifacts). Corrected.
- Re-validated: `bash -n` all pass. (plutil and tests unchanged from round 1.)

### Manual validation

Human performed terminal and Discord validation:

- `scripts/start.sh mac-claude` → loaded, Gateway connected.
- `scripts/status.sh mac-claude` → pid visible.
- `scripts/stop.sh mac-claude` → stopped.
- `scripts/uninstall.sh mac-claude` → plist removed.
- `scripts/start.sh` (all 3) → mac-claude, mac-codex, mac-opencode all loaded.
- Discord health check → mac-codex responded with adapter/bin/available fields.

### Current status

- Task status: **done** — all static, terminal, and Discord validation passed.
- Human gate: **passed**.
- Ready for commit and merge at human's discretion.

## 2026-05-31

### Dogfood doc sync — coordinator integration docs

- Read harness state, progress, scope, architecture, domain model, and `dogfood-doc-sync` plan before editing.
- Confirmed the task already had an active coordinator lease for `mac-codex` / `auto-mac-codex-1780240587`; a duplicate `assignment accept` attempt through coordinator CLI failed because of that active lease.
- Updated current-state docs for Phase 4 coordinator integration:
  - `docs/discord-multibot-plan/multi-bot-refactor-plan.md`
  - `docs/multi-agent-harness-overview.md`
  - `docs/project-harness/runbook.md`
  - `docs/project-harness/scope.md`
- Synced wording around coordinator Discord daemon, targeted agent handoff delivery, discord-nexus coordinator handoff auto-accept, and the rule that task lifecycle state changes go through coordinator CLI rather than direct harness JSON edits.
- Sanity-checked documented coordinator commands against current `mac.sh --help` output.
- Validation: `git diff --check` passed; `scripts/harness/harnessctl validate` passed; `scripts/harness/harnessctl doctor` exited 0 with existing optional/current file misses (`current/task_plan.md`, `init.sh`).
```

## Current Blocker

```md

```

## Expected Next Action

- Target agent should accept, decline, or raise a blocker explicitly.
- If accepted, target agent should run `scripts/harness/harnessctl accept phase-5.3-agent-registry-auto-sync mac-claude <session-id>`.

