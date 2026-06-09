# Phase 7.1 Post-Closeout Review Feedback (Retroactive)

Reviewer: `operator` (codex 不可用，operator 代行 reviewer 角色)
Date: 2026-06-09
Related: `phase-7.1-single-host-n-plus-m-runtime` (status: done, closed 2026-06-08 15:51)

## 目的

7.1 在 2026-06-08 已经过 codex-operator 走完 closeout → mark-done 路径。但 2026-06-09 复盘时发现 **7.1 实质是 partial，bridge 进程数违反 plan 验收标准**。本文不重开 7.1，而是为新任务 `phase-7.1.1-single-platform-bridge-process` 提供执行 context。

## 7.1 plan 要求的 N+M 拓扑

`docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/plan.md` 第 35-42 行：

```text
Discord bridge ┐
KOOK bridge    ├── coordinate ── mac-codex agentd
               │             └── mac-claude agentd
```

**plan 隐含的不变量**（从 ASCII 图 + 验收标准推断）：
- 1 个 Discord bridge 进程（不按 agent 拆分）
- 1 个 KOOK bridge 进程
- 每个 agent 1 个 agentd 进程
- 1 个 coord 进程
- 4 agent 时总进程数 = **7 进程**（1 coord + 1 Discord bridge + 1 KOOK bridge + 4 agentd）

## 7.1 实际完成状态

### ✅ 已正确

- `multinexus/agentd/worker.py`：`AgentdWorker` 是 1 agent 1 进程，调用 `make_adapter(config)` 跑 adapter，**不读 `config.token`**（adapter 只调 CLI 子进程如 `claude -p`、`codex exec`，不需要平台 token）
- `multinexus/agentd/coordinate_client.py`：bridge 侧用 `CoordinateRuntimeClient` 走 `bridge -> coord -> agentd` 路径，不直接调 adapter
- `multinexus/agentd/__main__.py`：standalone agentd launcher，从 coord claim job
- `multinexus/kook/bot.py:43` `class KookBridge`：KOOK bridge 模块合入
- `multinexus/protocol.py`：`AgentRequest`/`AgentResponse` 平台无关 envelope
- 258 multinexus tests + 731 coord tests 全过
- launchd plist：4 个 `com.multinexus.mac-X.agentd.plist`（1 agent 1 进程）— **这部分 plist 正确**
- coord runtime `request submit` / `job claim` / `job report` 端到端 smoke 通过（job 87891d7b、52d7d418、ff5c0ce9、aed04fbb、c828f16e 全部 done）

### ❌ 未实现

- **`multinexus.py` 仍是 1 process 1 agent**（注释第 6 行："one-process-per-agent Discord bot runner"）→ 4 agent = 4 个 bridge 进程，违反 plan 要求 1 platform 1 bridge
- **`multinexus/client.py:84` `DiscordClient.__init__(self, config: AgentConfig)`** 单 config 设计，没改造支持"1 进程 1 平台 多 agent"
- **`multinexus/kook/bot.py` 未在 launchd 起**，KOOK bridge 实际未启用
- **bridge 进程数 1 platform = M agents** — plan 显式要求 1 platform 1 bridge，实际是 1 platform M bridges
- **`MentionRouter` 跨进程同步靠 `register_peer_bot`**（`multinexus/client.py:147-150`）—— 在 1 bridge 进程内应该直接共享 mention map，不需要跨进程通信

## 7.1 review 漏抓原因

- codex round 2 review 抓了"embedded AgentDaemon"（bridge 里 inline 起 agentd）→ 改 standalone ✓
- **没抓"bridge 进程数 1 platform = M agents 而不是 1"** —— review checklist 没强制对照 plan 第 38-39 行的 ASCII 图
- 41 个测试全过是因为测的是 agentd 边界，**bridge 多 agent 路由的测试根本没写**（因为没实现）
- 224 tests pass、5 commits closeout，**closeout 报告里完全没提 bridge 没合并**

## 修复路径（7.1.1 worker 参考）

### 改造点

1. `multinexus.py` 支持 `--platform {discord,kook}`，不传 `--agent` 时遍历 `agents.toml` 所有 `[[agents]]` 按 `token_env` 起 1 个 client per agent
2. `multinexus/client.py` 拆分 `DiscordClient` → `DiscordAgentClient`（per-agent token client）+ `DiscordBridge`（bridge 进程级协调器，持有 N 个 agent client 共享 asyncio loop）
3. `multinexus/routing/mentions.py` 改成 bridge 进程级共享 mention map（不再需要 `register_peer_bot` 跨进程同步）
4. `multinexus/kook/bot.py` 同样多 agent 化
5. launchd plist 改造：4 bridge plist → 1 个 `com.multinexus.discord.bridge.plist` + 1 个 `com.multinexus.kook.bridge.plist`（optional）

### token / adapter 边界（重要不变量）

- 平台 token (Discord / KOOK bot token) → **只在 bridge 进程**，每个 agent 1 个 token
- adapter (claude / codex / omp / opencode) → **只在 agentd 进程**，调用 CLI 子进程
- **bridge 不持有 adapter，agentd 不持有 platform token**（这条 7.1 已正确，不要破坏）
- `multinexus/config.py:117-120` 的 `token_env` 校验是给 bridge 入口用的；agentd 入口需要 `skip_token_validation` 路径，或把校验挪到 `multinexus.py` 启动层

### 测试覆盖

- `test_discord_bridge_multi_agent.py`：1 bridge 进程内 N agent mention 路由
- 跨 agent 引用（`@Codex 帮我问 @Claude`）→ 2 次 coord submit
- 1 bridge 进程崩溃 → 所有 agent 的 Discord 入口下线（**这是 N+M 的有意取舍**）
- 回归：legacy 单 agent 模式（`multinexus.py --agent X`）仍能用

### 验收端到端

- 进程数 = 1 coord + 1 Discord bridge + (1 KOOK bridge, optional) + 4 agentd = **6 或 7 进程**
- 不是当前 9 进程（4 bridge 4 agentd 1 coord）
- Discord 端到端 mention → coord → agentd → reply 用对应 bot identity

## 当前现场状态

- 9 个新增 7.1 plist 已 bootout，0 进程
- 旧 4 个 legacy `com.multinexus.mac-*.plist` 保留在 `launchd/` + `~/Library/LaunchAgents/`，但 launchd 不在加载（之前 bootout 过）
- coord 数据库里有 5 个 phase 7.1 端到端 smoke 留下的 `request.received` + 报告事件，可作 7.1.1 回归基线
- `~/.coordinator/daemon.env` + `run-daemon.sh` 路径下旧 `local.multi-agent-coordinator.daemon.plist` 也被 bootout，**新 coord runtime 接管需要从 `daemon.env` 抄 env 或者 launchd plist 里 inline**

## 7.1.1 checklist 模板参考

新 checklist item 至少需要：
- `id`: `phase-7.1.1-single-platform-bridge-process`
- `title`: "Phase 7.1.1 Single Platform Single Bridge Process"
- `status`: `open`（新任务）
- `blocked_by`: `[]`（无前置；7.1 实质 partial 但已 mark-done）
- `dependencies`: 至少包含 `phase-7.1-single-host-n-plus-m-runtime`（语义上 7.1.1 是 7.1 的补完）
- `plan_path`: `docs/project-harness/tasks/phase-7.1.1-single-platform-bridge-process/plan.md`（worker 自己写）

## 流程提醒（给 worker）

- 走正常 worker bootstrap：读 `progress.md` / `harness-state.json` / `mvp-checklist.json` / `scope.md` / `architecture.md` / `domain-model.md` / `runbook.md`
- plan 自己写（不要拿本文件当 plan，plan 要通过 `plan.ready` 走 review）
- 7.1.1 plan 引用本文作为 review context 即可
- 跑过 coord `task handoff` / `assignment accept` 走正常 worker 流程
- closeout 报告要明确对照 7.1 plan 验收标准（不是只对 7.1.1 自己的子目标）
