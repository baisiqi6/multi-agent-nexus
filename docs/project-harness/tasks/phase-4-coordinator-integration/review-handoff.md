# Review Handoff: Phase 4 Coordinator Integration (v2)

## Review Target

- **Workspace**: multinexus
- **Task ID**: phase-4-coordinator-integration
- **Title**: Phase 4: Coordinator Integration (WebhookBus + system prompt)
- **Plan doc**: `docs/project-harness/tasks/phase-4-coordinator-integration/plan.md`
- **Reviewer feedback**: `docs/project-harness/tasks/phase-4-coordinator-integration/review-feedback-2026-05-29-codex.md`

## v1 → v2 Changes

Addressed reviewer rejection (4 required changes):

1. **Webhook URL 不存入 workspace config** — `default_destination` 改为非敏感标签 `"multinexus-status"`，webhook URL 只从 `DISCORD_WEBHOOK_URL` 环境变量获取
2. **CLI 示例包含 workspace_id** — 所有 coordinator CLI 命令首参为 `multinexus`
3. **禁止普通 agent 直接调 harnessctl** — 默认规则：所有状态变更通过 coordinator CLI；harnessctl 仅限 operator 在 harness repair 场景下使用
4. **新增 tracked template** — `docs/project-harness/templates/agent-coordinator-prompt.md`（implementation deliverable，不在本 plan 阶段创建）

## What Changed

Phase 4.1-4.4 scope only. Two projects involved:

### coordinator (multi-agent-coordinator)

1. **`src/multi_agent_coordinator/bus.py`** — 新增 `WebhookBus` 类
   - `from_env()` 读取 `DISCORD_WEBHOOK_URL`（唯一来源）
   - `send()` POST webhook_url?wait=true, username="coordinator", allowed_mentions={"parse":[]}
   - `bus_for_platform("discord_webhook")` 返回 WebhookBus 实例
   - destination 参数忽略（不传入 HTTP request body）

2. **`src/multi_agent_coordinator/policy.py`** — `SUPPORTED_PLATFORMS` 加入 `"discord_webhook"`

3. **`tests/test_bus.py`** — 7 个新测试用例（mock HttpPost），含 destination 不泄漏到 HTTP body 的验证

### multinexus

4. **`agents.toml`**（本地，untracked）— mac-claude、mac-codex、mac-opencode 的 system_prompt 追加 coordinator CLI 使用说明
5. **`docs/project-harness/templates/agent-coordinator-prompt.md`**（已创建，tracked）— coordinator system_prompt 模板，含完整路径、placeholder 和 multinexus 具体值

## Design Decisions

1. **WebhookBus 忽略 destination 参数**：webhook URL 已绑定 channel，destination 无意义但保留 Protocol 接口一致。destination 值不出现在 HTTP request body 中。
2. **只做状态广播，不做 agent 触发**：WebhookBus 只发 `[ASSIGN]`、`[BLOCKER]`、`[DONE]` 等通知，不发 `[handoff] @Bot`。Agent 触发是 Phase 4.5+ 范围。
3. **system_prompt 静态注入而非动态**：coordinator CLI 路径和 workspace 名写死在 agents.toml 里，不改 prompt.py 代码。简单且够用。
4. **不改 db schema**：workspace.default_bus 已经是 TEXT，直接存 `"discord_webhook"`。
5. **webhook URL 只从环境变量获取**：不在 workspace config、tracked 文件、日志、delivery rows 中存储 webhook URL。`default_destination` 是非敏感标签（如 `"multinexus-status"`），仅用于 message_key 去重和日志标识。
6. **harnessctl 访问限制**：普通 agent 不直接调 harnessctl 或修改 harness JSON。所有状态变更通过 coordinator CLI。harnessctl 仅限 operator 在明确要求 repair/maintain 时使用。
7. **tracked template**：因 agents.toml 是 .gitignore'd，新增 tracked template 文件供 review 和复现。文件已创建于 `docs/project-harness/templates/agent-coordinator-prompt.md`。

## Files to Review

Read these files in order:

1. `docs/project-harness/tasks/phase-4-coordinator-integration/review-feedback-2026-05-29-codex.md` — reviewer 详细反馈
2. `docs/project-harness/tasks/phase-4-coordinator-integration/plan.md` — updated implementation plan (v2)
3. `/Users/yinxin/projects/multi-agent-coordinator/src/multi_agent_coordinator/bus.py` — existing bus code (WebhookBus will be added here)
4. `/Users/yinxin/projects/multi-agent-coordinator/src/multi_agent_coordinator/policy.py` — existing policy (SUPPORTED_PLATFORMS will be extended)
5. `/Users/yinxin/projects/multi-agent-coordinator/tests/test_bus.py` — existing bus tests (new tests will be added)
6. `/Users/yinxin/projects/multinexus/agents.toml` — current agent config (system_prompt will be extended, local only)

Implementation deliverable (created during Phase 4.3):
- `docs/project-harness/templates/agent-coordinator-prompt.md` — coordinator system_prompt template

## What to Check

- plan.md 是否完整覆盖 reviewer feedback 的 4 项 required changes
- WebhookBus 是否复用了现有 DiscordBus 的模式（HttpPost 注入、from_env 工厂、错误处理）
- bus_for_platform 是否正确路由
- SUPPORTED_PLATFORMS 是否一致
- 所有 CLI 示例是否包含 workspace_id `multinexus`
- webhook URL 是否只从 `DISCORD_WEBHOOK_URL` 环境变量获取
- system_prompt 内容是否准确（完整路径、workspace 名、命令列表）
- harnessctl 访问限制是否明确
- tracked template 是否作为 implementation deliverable 标注
- 测试覆盖是否充分（send、from_env、bus_for_platform、destination 不泄漏到 HTTP body）
- 没有引入安全风险（URL 泄露、未限制的 mentions）

## Decision Command

After review, call exactly one of:

```bash
# Approve
cd /Users/yinxin/projects/multi-agent-coordinator
PYTHONPATH=src python3 -m multi_agent_coordinator \
  --db ~/.multi-agent-coordinator/coordinator.sqlite3 \
  plan approve multinexus \
  --task-id phase-4-coordinator-integration \
  --scope "implementation plan" \
  --reviewer "<your-reviewer-id>" \
  --notes "<one-line summary of your finding>"

# Or reject
PYTHONPATH=src python3 -m multi_agent_coordinator \
  --db ~/.multi-agent-coordinator/coordinator.sqlite3 \
  plan reject multinexus \
  --task-id phase-4-coordinator-integration \
  --scope "implementation plan" \
  --reviewer "<your-reviewer-id>" \
  --reason "<what needs to change>"
```
