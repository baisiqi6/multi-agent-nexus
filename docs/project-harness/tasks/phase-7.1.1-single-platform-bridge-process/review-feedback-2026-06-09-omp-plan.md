# Phase 7.1.1 Plan Review Feedback (omp 视角)

Reviewer: `omp` (代写：codex 不可用，operator 代行 omp 视角)
Date: 2026-06-09
Related: `phase-7.1.1-single-platform-bridge-process` (plan 阶段)

## 范围

按 plan.md 验收标准，7.1.1 目标：bridge 合并到 1 process / platform，agentd 保持 1 process / agent。本 review 反馈**仅针对 plan 阶段**（实现前的设计审查），不评估实现质量（那是 closeout 阶段的事）。

## 整体判断

plan 整体方向正确，目标与 7.1 plan ASCII 图、SKILL.md 第 53 行"bridge + 1 agentd/agent" 描述、用户 6-09 口头澄清完全对齐。

## 必须解决（不解决不 approve plan）

### 1. config.py token 校验改造路径需要明确选型

plan 第 165-166 行提到两种方案：
- `skip_token_validation` flag
- 把校验挪到 `multinexus.py` 启动层

omp 倾向**第二种**（挪到启动层）：
- `load_config` 不应该被两个入口共用但行为不同，破坏"单一事实"原则
- `multinexus.py` 入口加 5 行 token check 即可（已经有 `--agent` 逻辑，加 `--platform` 时一并加 token check）
- `multinexus/agentd/__main__.py` 入口不传 `--platform` 自然跳过 token check

**建议实现**：在 `load_config` 里只**校验** `token_env` 字段**存在性**（不是 token 值存在性），由 `multinexus.py` 在解析 `--platform` 时显式 `os.environ.get(token_env)` 拿 token 并 fail-fast。

### 2. 旧 4 个 mac-X.bridge.plist 不应保留

plan 第 188-194 行说"旧的 4 个 mac-X.bridge.plist 文件保留（legacy fallback）"。**omp 反对**：
- 保留 legacy bridge plist 意味着 launchd 会同时拉两套 bridge（4 个 legacy + 1 个新），违反 plan "1 platform 1 bridge" 不变量
- 应该是：把旧 4 个 plist 从 `launchd/` 仓库**移到 `launchd/legacy/` 子目录**（或加 `.legacy` 后缀），不参与 bootstrap，但保留 git history 便于回溯
- 或者直接删，让 git history 兜底

**建议**：移走而非保留，文件不在 `~/Library/LaunchAgents/` 加载路径里就行。

### 3. 进程数验收要写"最小可证"和"完整拓扑"两套

plan 验收第 121-127 行只写"4 agent + Discord bridge + KOOK bridge = 7 进程"，但**没说明**：
- 如果只启用 Discord bridge 不启 KOOK bridge，**几进程 = 6**？
- 如果 mac-claude / mac-codex / mac-omp / mac-opencode 之一临时下线，**几进程 = 1 coord + 1 discord + (1 kook) + (M-1) agentd**？

omp 建议：验收写"**N + M 进程模型**，N = 启用的平台数 (1 或 2)，M = 启用的 agentd 数"。closeout 报告里**实际跑**的 ps 截图说明 N 和 M 是多少。

## 可选改进（建议但不强求）

### A. 旧 `multinexus.py --agent X` 兼容期明确化

plan 第 153 行说"保留 backward compat 至少到 7.1.1 closeout 之后"。**omp 建议**：
- 7.1.1 closeout 之前：legacy 模式 + 新多 agent 模式共存
- 7.1.1 closeout 之后（= 7.2 启动前）：删除 legacy 模式入口，硬切到 `--platform` 必需
- 写入 `docs/agent-report-protocol.md` 标明 deprecation 时间

### B. MentionRouter 共享路径要写 in-memory cache 而非 DB

plan 第 80-83 行说"in-memory mention map"。**omp 确认**这是对的，但需要强调：
- 1 bridge 进程崩溃 → in-memory map 丢失
- 重启后从 4 个 `discord.Client` 各自 `on_ready` 重新建 map（每 client 拿到自己 user_id，其他 client 通过 gateway `GUILD_MEMBER_UPDATE` 或 message event 拿到对方 user_id）
- **不要**落 DB / 文件持久化（启动时所有 client 同时 ready，window 极短）

### C. KOOK bridge 启用决策

plan 第 16-17 行把 KOOK 标为 "(optional)"，但验收第 121 行写"`1 KOOK bridge optional`"。**omp 建议**：
- 如果本任务不启用 KOOK，**closeout 时显式说明** "KOOK bridge plist 不在本任务范围，单独 task 启用"
- **不要**用 `optional` 这种模糊措辞，要么启用要么不启用

## 不属于 plan 范围（closeout 才看）

- 7.1 plan 第 113-119 行原始验收（bridge 进程数、agent reply 回原频道、task-scoped session 保留）的实际验证 → closeout 阶段
- launchd plist plutil lint 实际通过 → closeout 阶段
- ps 拓扑截图 → closeout 阶段
- Discord mention 端到端 smoke → closeout 阶段

## 结论

**Plan 待 3 项必须解决 + 3 项建议改进后才能 approve**：
1. config.py token 校验改造选第二种（挪到启动层）
2. 旧 4 个 mac-X.bridge.plist 移走不保留
3. 验收写"N + M 进程模型"不写死 6/7

worker (mac-claude) 接到 reject 后，**重新写 plan.md**（或修订 plan.md）→ `plan review-request` → 走第二轮 review（omp 这次看到更新版）→ approve。

或者 worker 不重写 plan，**只在 worker bootstrap 时按上面 3 条调整实现**，plan.md 修订由 reviewer (operator) 跟进。无论哪条路，**closeout 时 closeout packet 必须明确说"按 omp plan review 第 N 条意见修改了"**。
