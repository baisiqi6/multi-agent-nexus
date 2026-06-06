# Agent Coordinator System Prompt Template

<!-- Append this to managed agent system_prompt in agents.toml -->
<!-- This file is the tracked source of truth. agents.toml is .gitignore'd. -->

## Coordinator 集成

你可以调用 multi-agent-coordinator CLI 来跟踪任务状态：

```bash
cd /Users/yinxin/projects/multi-agent-coordinator && \
MAC_DB=~/.multi-agent-coordinator/coordinator.sqlite3 \
  skills/coordinate-operator/scripts/mac.sh <command> multinexus [options]
```

常用命令：
- `mac.sh assignment accept multinexus --task-id <id> --owner <agent> --session <sid>`
- `mac.sh branch allocate multinexus --task-id <id> --owner <agent>`
- `mac.sh pr link multinexus --task-id <id> --pr-url <url>`
- `mac.sh ci check multinexus --task-id <id>`
- `mac.sh merge gate multinexus --task-id <id>`
- `mac.sh assignment closeout multinexus --task-id <id> --reviewer <name>`
- `mac.sh assignment mark-done multinexus --task-id <id>`

### 规则

- 所有状态变更必须通过 coordinator CLI
- 不要直接调用 harnessctl 或修改 harness JSON 文件
- harnessctl 仅限 operator 在明确要求 harness repair/maintain 时使用

<!-- Placeholder values for multinexus:
COORDINATOR_PATH=/Users/yinxin/projects/multi-agent-coordinator
COORDINATOR_DB=~/.multi-agent-coordinator/coordinator.sqlite3
MAC_SH=skills/coordinate-operator/scripts/mac.sh
WORKSPACE_ID=multinexus
-->
