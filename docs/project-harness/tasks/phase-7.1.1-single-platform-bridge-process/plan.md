# Phase 7.1.1: 单平台单 Bridge 进程

## 上下文

Phase 7.1 在 2026-06-08 走完 closeout → mark-done，但 2026-06-09 复盘发现 plan 验收标准（`docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/plan.md` 第 35-42 行 ASCII 图 + 第 113-119 行验收）未被完整满足：

- plan 要求 **1 个 Discord bridge 进程 + 1 个 KOOK bridge 进程 + 每个 agent 1 个 agentd 进程 + 1 个 coord 进程**
- 实际实现是 4 agent × 1 bridge = 4 个 bridge 进程（`multinexus.py:6` "one-process-per-agent"），违反 plan
- agentd 拆分在 7.1 round 2/3 已正确，**本任务专门补完 bridge 合并**

详细 review 上下文：`docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/review-feedback-2026-06-09-operator-postcloseout.md`

## 目标

让 **1 个 bridge 进程承载 1 个 IM 平台上的所有 agent**，按 mention 路由到对应 agentd。完成后系统进程数：

```text
Mac:
  coordinate                (1)
  discord-bridge            (1)  ← 本任务改
  kook-bridge               (1, optional)  ← 本任务改
  mac-codex agentd          (1)  ← 7.1 已完成
  mac-claude agentd         (1)  ← 7.1 已完成
  mac-omp agentd            (1)  ← 7.1 已完成
  mac-opencode agentd       (1)  ← 7.1 已完成
```

4 agent + Discord bridge + KOOK bridge 时 = **1 + 1 + 1 + 4 = 7 进程**（KOOK 起时）/ **6 进程**（KOOK 不起）。

## 现状

### 7.1 已正确（不要破坏）

- `multinexus/agentd/worker.py`：`AgentdWorker` 是 1 agent 1 进程，调 `make_adapter(config)` 跑 CLI 子进程，**不读 `config.token`**
- `multinexus/agentd/coordinate_client.py`：bridge 侧用 `CoordinateRuntimeClient` 走 `bridge -> coord -> agentd`，不直接调 adapter
- 平台 token (Discord/KOOK bot token) 归 bridge 进程；adapter (claude/codex/omp) 归 agentd 进程
- 258 multinexus tests + 731 coord tests 全过
- coord 端到端 `runtime request submit` / `job claim` / `job report` 通过（5 个 phase-7.1 smoke job 全部 done）

### 7.1 未实现（本任务要补完）

- **`multinexus.py` 注释第 6 行**："one-process-per-agent Discord bot runner" → 需改为多 agent 模式
- **`multinexus/client.py:84`**：`DiscordClient.__init__(self, config: AgentConfig)` 单 config → 需改造支持"1 进程 1 平台 多 agent"
- **`multinexus/kook/bot.py`**：KOOK bridge 模块在但未在 launchd 起；同样 1 process 1 agent 形态
- **`MentionRouter` 跨进程同步靠 `register_peer_bot`**（`multinexus/client.py:147-150`）→ 改为 bridge 进程内共享 mention map
- launchd plist：当前 4 个 `com.multinexus.mac-X.bridge.plist` 需改造为 1 个 `com.multinexus.discord.bridge.plist` + 1 个 `com.multinexus.kook.bridge.plist`

## 范围

### 1. `multinexus.py` 改造

- 新增 `--platform {discord,kook}` 参数
- 不传 `--agent` 时遍历 `agents.toml` 所有 `[[agents]]`，按 `token_env` 在 1 个进程内为每个 agent 起 1 个 client
- 传 `--agent` 时退回 legacy 单 agent 模式（保留 backward compat 至少到 7.1.1 closeout 之后）
- 共享 1 个 asyncio event loop

### 2. `DiscordClient` 重构

- 拆 `DiscordClient` 为 `DiscordAgentClient`（per-agent token 子组件）+ `DiscordBridge`（bridge 进程级协调器）
- `DiscordBridge` 持有 N 个 `DiscordAgentClient` 共享 asyncio loop
- mention 路由：在 `DiscordBridge` 层面建 `dict[agent_id, int]` 提到 bot user_id 表，1 个 message 进入时按 mention 解析出 target_agent
- on_message → `CoordinateRuntimeClient.submit_request(target_agent=...)`
- webhook 身份：reply 时按 `target_agent` 选对应 webhook user
- slash commands：每个 `DiscordAgentClient` 各自 sync（per-agent slash scope）
- 删除 `register_peer_bot` 跨进程同步路径（被 1 进程内 mention map 取代）

### 3. `KookBridge` 重构

- 接受 `list[AgentConfig]`，内部按 agent 路由（同 Discord）
- 加 `multinexus/kook/__main__.py` launcher
- KOOK 不在本机启用时该 plist 不强求 bootstrap

### 4. `config.py` 改造

- `multinexus/config.py:117-120` 的 `token_env` 校验是给 bridge 入口用的；agentd 入口走 `python -m multinexus.agentd` 时也需要 `load_config` 但不需要 token
- **改造方案（omp 选型）**：把 token 值校验从 `load_config` 挪到 `multinexus.py` 启动层
  - `load_config` 只校验 `token_env` **字段存在性**（不是 token 值存在性），保持单一事实
  - `multinexus.py` 解析 `--platform` 时显式 `os.environ.get(token_env)` 拿 token 并 fail-fast
  - `multinexus/agentd/__main__.py` 入口不传 `--platform` 自然跳过 token check
- 改完确保 `multinexus/agentd/__main__.py` 跑起来仍然 0 token 环境不报"Discord token missing"

### 5. launchd plist 改造

**当前 4 个 bridge plist**：
```
com.multinexus.mac-claude.bridge.plist
com.multinexus.mac-codex.bridge.plist
com.multinexus.mac-omp.bridge.plist
com.multinexus.mac-opencode.bridge.plist
```

**目标 1-2 个 bridge plist**：
```
com.multinexus.discord.bridge.plist   # python multinexus.py --platform discord
com.multinexus.kook.bridge.plist      # python -m multinexus.kook --platform kook
```

**旧 plist 处理（omp 要求）**：不保留在 `launchd/` 仓库根目录。移到 `launchd/legacy/` 子目录（或加 `.legacy` 后缀），不参与 bootstrap；保留 git history 便于回溯。或者直接删除（git history 兜底）。**目标 bootstrap 路径下不再有 legacy 4 个 plist 出现**。

### 6. 测试覆盖

- `tests/test_discord_bridge_multi_agent.py`：
  - 1 bridge 进程内 N agent mention 路由到不同 `coordinate.request_submit(target_agent=...)`
  - 跨 agent 引用（`@Codex 帮我问 @Claude`）→ 2 次 coord submit
  - 1 bridge 进程内多 agent slash commands 各自 sync
  - mention 表共享（不需要 `register_peer_bot` 跨进程同步）
  - 1 bridge 进程崩溃 → 所有 agent 的 Discord 入口下线（**这是 N+M 的有意取舍**，不是 bug）
- `tests/test_kook_bridge_multi_agent.py`：KOOK 侧同等覆盖
- 回归：`multinexus.py --agent X` legacy 模式仍然可用，224 个 multinexus 既有 tests 全过

### 7. closeout evidence

- `ps` 输出显示 **1 coord + 1 Discord bridge + (1 KOOK bridge, optional) + 4 agentd = 6/7 进程**，不再是 9 进程
- launchd `plutil -lint` 全部 OK
- 端到端 smoke：Discord 消息 `@Mac Claude <task>` 走 `bridge -> coord -> mac-claude agentd -> claude CLI -> reply` 全链路，reply 用 `Mclaucode#9906` 身份
- 跨平台 smoke（KOOK 启用时）：KOOK 消息 `@Codex <task>` 走 `kook-bridge -> coord -> mac-codex agentd -> codex CLI -> reply` 全链路，回复到 KOOK

## 非目标

- 不做跨主机 bridge（bridge 仍跑在 Mac，agentd 可远程，跨主机是 7.2 范围）
- 不做 bridge 高可用（plan 显式排除）
- 不合并 Discord 和 KOOK bridge 成 1 进程（plan 显式禁止）
- 不改 `multinexus/adapters/` 任何代码
- 不改 `multinexus/agentd/worker.py` 任何代码（已经是 1 agent 1 进程）
- 不动 coord 端
- 不动 `agents.toml` 结构（除非要补 `kook` 平台 token 配置，本任务不强求）

## 验收标准

**进程数模型（omp 修正）**：N + M 进程模型
- N = 启用的平台数（1 表示只 Discord，2 表示 Discord + KOOK）
- M = 启用的 agentd 数（≤ `[[agents]]` 总数，缺 agentd 不破坏运行）
- 启动顺序：coord 第一个，agentd / bridge 任意顺序
- 关闭顺序：bridge 第一个（防止新消息进 queue），agentd 第二个（消费完剩余 job），coord 最后

**本任务（7.1.1）专属**（4 agent + Discord + KOOK 全启 = 7 进程）：

- `multinexus.py --platform discord` 不传 `--agent` 时启动 1 个 bridge 进程，包含所有 `[[agents]]` 的 Discord 入口
- 1 个 bridge 进程内 N agent mention 路由测试全过
- 跨 agent mention 测试通过
- 实际 ps 输出 **1 coord + 1 discord-bridge + 1 kook-bridge + 4 agentd = 7 进程**（N=2, M=4）
- 如果 KOOK 不启用：**1 coord + 1 discord-bridge + 4 agentd = 6 进程**（N=1, M=4）— closeout 报告必须显式说明 N=几 M=几
- legacy `multinexus.py --agent X` 单 agent 模式**保留到 7.1.1 closeout 之后删除**（7.2 启动前必须删掉）
- `multinexus/agentd/__main__.py` 在没有 platform token 的环境仍能启动（config validation 修对）
- 旧 4 个 `com.multinexus.mac-X.bridge.plist` 移出 bootstrap 路径（移到 `launchd/legacy/` 或删）

**7.1 plan 验收重新跑**（补完 closeout 漏项）：

- 1 个 Discord bridge 进程 = 全部 4 agent 的 Discord 入口 ✓
- 1 个 KOOK bridge 进程（启用时）= 全部 4 agent 的 KOOK 入口 ✓
- 每个 agent 1 个 agentd 进程 ✓（7.1 已通过）
- 1 个 coord 进程 ✓（7.1 已通过）
- bridge 代码不直接调用 `make_adapter()` ✓（7.1 已通过）
- agent 回复能回到原始 Discord 或 KOOK 频道（端到端 smoke 验证）
- 现有 task-scoped session 行为保留（agentd 侧不变，bridge 侧无 session 概念）

## 建议实现顺序

1. 读 `review-feedback-2026-06-09-operator-postcloseout.md` 作为入站 context
2. 写 `worker-bootstrap.md` 在 task 目录下（参考 7.1 自身的 `worker-bootstrap.md`）
3. 走 worker bootstrap：`harnessctl session-init` 准备环境
4. 写 `DiscordAgentClient` 和 `DiscordBridge` 骨架 + 单元测试
5. 改 `multinexus.py` 支持 `--platform discord` 多 agent
6. 跑 6 个 multi-agent bridge 测试 + 224 legacy 回归测试，确认全过
7. 改造 KOOK bridge + 写 KOOK multi-agent 测试
8. 改造 `config.py` 让 agentd 入口不需要 platform token
9. 写新的 launchd plist（`com.multinexus.discord.bridge.plist` + `com.multinexus.kook.bridge.plist`），plutil lint
10. 端到端：起 1 coord + 1 Discord bridge + 4 agentd，ps 验证 6 进程，smoke 走一遍 Discord mention → agentd → reply
11. `assignment closeout` → reviewer 做 `review-result`（这次按 7.1 plan 7 条标准 + 7.1.1 验收对照检查）
12. closeout 报告里写明 ps 拓扑截图 / 测试结果 / 7.1 plan 验收逐条对照

## 风险

- 1 bridge 进程崩了 = 全部 agent 的 Discord 入口同时断（之前 1/4 断）—— **这是 N+M 的有意取舍**，要在 progress.md / runbook 里写清楚
- 4 个 `discord.Client` 共享 1 个 event loop，要保证 1 个 client 卡了不拖死其他
- `MentionRouter` 当前是 per-client 持有，需要重构为 bridge 进程级共享
- `config.py` 改造可能影响 `multinexus.py --agent X` legacy 路径，需要回归测试
- KOOK 端 khl 库未安装时，KOOK bridge launcher 应当 fail fast 而非静默退

## 依赖

- 7.1 已完成（agentd 拆出，coord 端到端已通）
- 258 multinexus tests + 731 coord tests 全过
- `multinexus/agentd/worker.py` 1 agent 1 进程
- `multinexus/agentd/coordinate_client.py` 已支持 `bridge -> coord -> agentd` 路径
- coord runtime `request submit` / `job claim` / `job report` 端到端通过

## 实施人

- `mac-claude`（7.1 实施 owner，continuity）
- branch: `agents/mac-claude/phase-7.1.1-single-platform-bridge-process`
