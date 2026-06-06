# Phase 4: Coordinator Integration — Implementation Plan

## Scope

Phase 4.1-4.4: agent 主动使用 coordinator 的完整路径。

- 4.1: WebhookBus（coordinator 侧）
- 4.2: workspace bus 配置（无改动，已支持）
- 4.3: system prompt 注入（multinexus 侧）
- 4.4: 端到端测试 A（操作验证）

Phase 4.5-4.6（coordinator 主动分配给 agent）留后续 phase。

## Phase 4.1: WebhookBus

### coordinator `src/multi_agent_coordinator/bus.py`

新增 `WebhookBus` 类，参考现有 `DiscordBus` 模式：

```python
class WebhookBus:
    def __init__(self, *, webhook_url: str, http_post: HttpPost | None = None):
        self.webhook_url = webhook_url.rstrip("/")
        self.http_post = http_post or post_json

    @classmethod
    def from_env(cls) -> "WebhookBus":
        url = os.environ.get("DISCORD_WEBHOOK_URL")
        if not url:
            raise BusError("DISCORD_WEBHOOK_URL is required for discord_webhook delivery")
        return cls(webhook_url=url)

    def send(self, *, destination: str, payload: dict[str, Any], message_key: str) -> str:
        response = self.http_post(
            f"{self.webhook_url}?wait=true",
            {"Content-Type": "application/json", "User-Agent": "multi-agent-coordinator/0.1"},
            {
                "content": message_text(payload),
                "username": "coordinator",
                "allowed_mentions": {"parse": []},
            },
        )
        message_id = response.get("id")
        if not message_id:
            raise BusError("discord webhook response did not include message id")
        return f"discord_webhook:{message_id}"
```

- destination 参数忽略（webhook URL 已绑定 channel）
- `?wait=true` 确保返回 message ID
- `allowed_mentions: {"parse": []}` 防止意外 ping
- **webhook URL 只从 `DISCORD_WEBHOOK_URL` 环境变量读取，不存入 workspace 配置**

### `bus_for_platform()` 新增分支

```python
if platform == "discord_webhook":
    return WebhookBus.from_env()
```

### `policy.py` SUPPORTED_PLATFORMS

```python
SUPPORTED_PLATFORMS = {"discord", "discord_webhook", "kook", "stdout"}
```

### `tests/test_bus.py` 新增 WebhookBusTests

7 个测试用 mock HttpPost：
- send posts to webhook_url with wait=true
- send returns discord_webhook:{id}
- send uses "coordinator" username
- send allows no mentions
- from_env raises without DISCORD_WEBHOOK_URL
- bus_for_platform returns WebhookBus
- destination is ignored

## Phase 4.2: Workspace 配置

`workspace add --default-bus discord_webhook --default-destination discord-nexus-status`

- **`default_bus`**: `"discord_webhook"`
- **`default_destination`**: 非敏感标签（如 `"discord-nexus-status"`），不是 webhook URL。仅用于 message_key 去重和日志标识
- **webhook URL**: 只在运行时从 `DISCORD_WEBHOOK_URL` 环境变量获取

## Phase 4.3: System Prompt 注入

### multinexus `agents.toml`（本地文件，.gitignore'd）

mac-claude、mac-codex、mac-opencode 的 system_prompt 追加：

```
## Coordinator 集成

你可以调用 multi-agent-coordinator CLI 来跟踪任务状态：

cd /Users/yinxin/projects/multi-agent-coordinator && \
MAC_DB=~/.multi-agent-coordinator/coordinator.sqlite3 \
  skills/multi-agent-coordinator-operator/scripts/mac.sh <command> multinexus [options]

常用命令：
- mac.sh assignment accept multinexus --task-id <id> --owner <agent> --session <sid>
- mac.sh branch allocate multinexus --task-id <id> --owner <agent>
- mac.sh pr link multinexus --task-id <id> --pr-url <url>
- mac.sh ci check multinexus --task-id <id>
- mac.sh merge gate multinexus --task-id <id>
- mac.sh assignment closeout multinexus --task-id <id> --reviewer <name>
- mac.sh assignment mark-done multinexus --task-id <id>

所有状态变更必须通过 coordinator CLI。不要直接调用 harnessctl 或修改 harness JSON 文件。
harnessctl 仅限 operator 在 harness repair 场景下使用。
```

### `docs/project-harness/templates/agent-coordinator-prompt.md`（已创建，tracked）

将 coordinator system_prompt 片段作为模板存入 tracked 文件，供 agent 配置参考。文件已创建，内容见 `docs/project-harness/templates/agent-coordinator-prompt.md`。

关键内容：
- coordinator CLI 使用说明（完整路径）
- 所有命令示例带 `multinexus` workspace_id
- 明确：所有状态变更通过 coordinator CLI，harnessctl 仅限 operator/harness repair
- placeholder 注释供其他项目复用

无 multinexus 代码改动。`build_agent_prompt()` 已会传 system_prompt 给 adapter。

## Phase 4.4: 端到端测试 A

操作验证步骤（手动）：

1. Discord 频道创建 webhook，获取 URL
2. 设置环境变量：`export DISCORD_WEBHOOK_URL="<webhook-url>"`
3. 更新 workspace: `mac.sh workspace add multinexus --default-bus discord_webhook --default-destination discord-nexus-status`（不含 URL）
4. 创建测试 task，触发事件，pump deliveries
5. 验证 Discord 频道出现 webhook 消息

## 文件变更

| 操作 | 项目 | 文件 |
|------|------|------|
| 修改 | coordinator | `src/multi_agent_coordinator/bus.py` |
| 修改 | coordinator | `src/multi_agent_coordinator/policy.py` |
| 修改 | coordinator | `tests/test_bus.py` |
| 修改 | multinexus | `agents.toml`（本地，untracked） |
| 新增 | multinexus | `docs/project-harness/templates/agent-coordinator-prompt.md` |

## Verification

```bash
# coordinator 单元测试
cd ~/projects/multi-agent-coordinator
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'

# WebhookBus 手动 smoke test
DISCORD_WEBHOOK_URL="<url>" PYTHONPATH=src python3 -c "
from multi_agent_coordinator.bus import WebhookBus
bus = WebhookBus.from_env()
print(bus.send(destination='', payload={'text': '[TEST] Phase 4.1 smoke'}, message_key='test:4.1'))
"
```
