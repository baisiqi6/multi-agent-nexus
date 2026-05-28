# Agent Coordinator System Prompt Template

<!-- Append this to managed agent system_prompt in agents.toml -->
<!-- This file is the tracked source of truth. agents.toml is .gitignore'd. -->

## Coordinator 集成

你可以调用 multi-agent-coordinator CLI 来跟踪任务状态：

```bash
cd /Users/yinxin/projects/multi-agent-coordinator && \
MAC_DB=~/.multi-agent-coordinator/coordinator.sqlite3 \
  skills/multi-agent-coordinator-operator/scripts/mac.sh <command> discord-nexus [options]
```

常用命令：
- `mac.sh assignment accept discord-nexus --task-id <id> --owner <agent> --session <sid>`
- `mac.sh branch allocate discord-nexus --task-id <id> --owner <agent>`
- `mac.sh pr link discord-nexus --task-id <id> --pr-url <url>`
- `mac.sh ci check discord-nexus --task-id <id>`
- `mac.sh merge gate discord-nexus --task-id <id>`
- `mac.sh assignment closeout discord-nexus --task-id <id> --reviewer <name>`
- `mac.sh assignment mark-done discord-nexus --task-id <id>`

### 规则

- 所有状态变更必须通过 coordinator CLI
- 不要直接调用 harnessctl 或修改 harness JSON 文件
- harnessctl 仅限 operator 在明确要求 harness repair/maintain 时使用

<!-- Placeholder values for discord-nexus:
COORDINATOR_PATH=/Users/yinxin/projects/multi-agent-coordinator
COORDINATOR_DB=~/.multi-agent-coordinator/coordinator.sqlite3
MAC_SH=skills/multi-agent-coordinator-operator/scripts/mac.sh
WORKSPACE_ID=discord-nexus
-->
