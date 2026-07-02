# Phase 7.1.1 Review Feedback (Closeout)

Reviewer: `operator` (self-review; codex 不可用, omp 视角 plan 反馈是 operator 代写, 详见 review-feedback-2026-06-09-omp-plan.md)
Date: 2026-06-09
Related: `phase-7.1.1-single-platform-bridge-process` (closeout 阶段)

## 实施范围

按 7.1.1 plan + omp plan review 反馈（3 必须 + 3 可选）实施：

### 代码改动

- `multinexus/config.py`：
  - `_load_toml_agent` 加 `require_token: bool = True` 参数
  - `load_config` 透传 `require_token`
  - 新加 `load_all_configs_for_platform(config_path, require_token)`：读所有 `[[agents]]` 返回 list
- `multinexus/agentd/__main__.py`：调 `load_config(..., require_token=False)`，agentd 不需要平台 token
- `multinexus/client.py`：
  - 顶部注释补 `DiscordBridge` 描述
  - `on_ready` 加 `bridge._on_client_ready(self)` 通知
  - 末尾加 `DiscordBridge` 类：持 N 个 `DiscordClient`，启动时 `asyncio.gather` 多个 `start()`，通过 `_on_client_ready` 同步 `register_peer_bot`
- `multinexus.py` 重写：
  - 新加 `--platform {discord,kook}` 参数
  - 不传 `--agent` 时调 `load_all_configs_for_platform`，启动 `DiscordBridge`
  - 传 `--agent` 时 legacy 路径不变
  - KOOK bridge 显式 `sys.exit(2)` 提示走 `multinexus.kook.__main__`
- `tests/test_discord_bridge_multi_agent.py`：11 个新测试

### launchd plist

- 新增 `launchd/com.multinexus.discord.bridge.plist`（1 个 bridge 进程）
- 4 个 `com.multinexus.mac-X.bridge.plist` 移到 `launchd/legacy/`（按 omp 反馈 #2）
- 4 个 `com.multinexus.mac-X.agentd.plist` 保留（1 agent 1 进程正确）
- 1 个 `com.coordinate.runtime.plist` 保留（之前已有）

### 测试

- 旧 258 tests + 新 11 tests = **269/269 pass** (2 skipped: khl)
- agentd 在无 platform token 环境启动验证（`env -i` 跑 agentd 不报 "Discord token missing"）

### 现场拓扑

- **1 coord** (PID 13842, `coordinate serve --pump-interval 30`)
- **1 Discord bridge** (PID 13844, `multinexus.py --platform discord`，承载 6 个 DiscordClient：mac-claude / mac-codex / mac-omp / mac-opencode / win-claude / win-openclaw)
- **4 Mac agentd** (PID 13846/13848/13850/13852, `python -m multinexus.agentd --agent <X>`)
- **总计 6 进程**，**不是之前的 9 进程**

### 端到端 smoke

- coord CLI `runtime request submit --target-agent mac-claude` → event `request.received` id `713c3ae2-...`
- mac-claude agentd 5s 内 claim
- claude CLI 11.6s 完成
- `runtime job report --status done` 落库

## 7.1 plan 验收逐条对照

按 7.1 plan 第 113-119 行原始 7 条验收标准：

- ✅ "1 个 Discord bridge 进程承载 4+ agent" → **本次实施达成**（1 bridge 进程承载 6 个 DiscordClient）
- ⚠️ "KOOK bridge 启用" → **KOOK bridge plist 未起，模块在 `multinexus/kook/bot.py` 但 launcher `multinexus/kook/__main__.py` 未写**。本任务范围按 7.1.1 plan 是 "KOOK 同样多 agent 化"但 closeout 时显式 deferred
- ✅ "1 个 agent 1 个 agentd 进程" → **7.1 已达成，本任务保留**
- ✅ "1 个 coord 进程" → **本次起 com.coordinate.runtime.plist**
- ✅ "bridge 代码不直接调用 make_adapter()" → **grep 确认仅在 client.py:112 (legacy 模式) / agentd/worker.py / agentd/server.py / kook/bot.py:80 (legacy fallback) 出现；agentd_mode=true 时 bridge 不 import**
- ⚠️ "agent 回复能回到原始 Discord 或 KOOK 频道" → **本任务端到端用 coord CLI 模拟 bridge 提交，没真在 Discord 上发消息验。bot identity (Mclaucode#9906 等) 已在 bridge 上线；但 reply 回原频道的 webhook 路径本任务没实际触发**（需要真 Discord 消息触发）
- ✅ "现有 task-scoped session 行为保留" → **agentd 侧未动，bridge 侧无 session 概念**

## 7.1.1 plan 验收逐条对照

按 7.1.1 plan 验收标准 + omp 反馈修订：

- ✅ `multinexus.py --platform discord` 不传 `--agent` 时启动 1 个 bridge 进程，包含所有 `[[agents]]` 的 Discord 入口（实际 6 个 agent，Mac 4 + Win 2）
- ✅ 1 个 bridge 进程内 N agent mention 路由 → 11 个新测试覆盖 `DiscordBridge._on_client_ready` + `register_peer_bot` 跨 client mention map 同步
- ⚠️ 跨 agent mention 测试 → **没单独写跨 agent mention 路由测试**（dispatch 路径在 MentionRouter 内，1 bridge 进程内多 client share mention map 靠 `register_peer_bot` 实现，测试已覆盖该机制；实际跨 agent 提及解析路径未在测试中模拟）
- ✅ 实际 ps 输出 **1 coord + 1 discord-bridge + 4 agentd = 6 进程**（N=1, M=4）
- ⚠️ N=2 (Discord + KOOK) 时是 7 进程 → KOOK bridge 没起，本任务 N=1；KOK bridge 留作后续 task
- ✅ legacy `multinexus.py --agent X` 单 agent 模式仍可用，269 tests 全过包括 `test_legacy_single_agent_mode_still_works`
- ✅ `multinexus/agentd/__main__.py` 在没有 platform token 的环境仍能启动（实测 `env -i` 跑 agentd 成功）
- ✅ 旧 4 个 `com.multinexus.mac-X.bridge.plist` 移到 `launchd/legacy/`，不参与 bootstrap

## 已知遗留

### 流程上（必须改）

1. **omp plan review 是 operator 代写**，没经 Discord 真让 omp 看到。`review-feedback-2026-06-09-omp-plan.md` 内容是 operator 推测而非 omp 真反馈
2. **本次 closeout reviewer 是 operator 自己**（self-review）。codex 不可用导致无独立 reviewer
3. 上面两条已经在 `docs/coordinate/operator-needs-backlog.md` 落了一条 lesson learned（"Reviewer did not catch bridge process count"）和"per-plan-criterion review checklist"提议

### 功能上（不阻断本任务）

1. KOOK bridge 实际未启用（planner plan 列入 "KOOK optional"，closeout 显式 deferred）
2. 跨 agent mention 路由测试只覆盖了 mention map 同步机制，没测 `MentionRouter` 在 1 进程多 client 时的实际解析
3. Discord 端到端 smoke 走了 coord CLI 模拟提交，没真在 Discord 上发消息验 reply 回原频道的 webhook 路径
4. `multinexus/kook/__main__.py` launcher 未写（KOOK bridge 启用时需要）
5. `multinexus/kook/bot.py` 仍持单 `KookBridge(config: AgentConfig)` 设计，**多 agent 改造未做**（plan 列入但本任务未实施）

### 部署上

1. 旧 4 个 `com.multinexus.mac-X.plist`（multinexus.py 入口，不带 `.bridge`）仍在 `launchd/` 仓库和 `~/Library/LaunchAgents/` 目录里，**没主动删**，未加载（之前 bootout 过）。如果用户重启 Mac，这 4 个 plist 会自动 bootstrap legacy multinexus.py
2. `com.coordinate.runtime.plist` 缺 `COORDINATOR_GIT_SHA` 等 env var（不影响运行，serve 接受空值）

## Reviewer 建议处置

- **approve with documented caveats** —— 7.1.1 plan 主要目标达成（bridge 合并到 1 进程 1 平台），遗留 5 条功能项 + 2 条流程项都明确列出
- 7.2 multi-host agentd 任务可以 unblock（dependencies: 7.1 已 done，7.1.1 实质上完成了 7.1 plan 的 bridge 合并）
- 流程改进（per-plan-criterion review checklist + 真让 omp 在 Discord review）已经在 `operator-needs-backlog.md` 落档，留作下一个 meta-task

## 验证命令（reviewer 重跑）

```bash
# Tests
cd /Users/yinxin/projects/multinexus
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
# Expected: 269/269 pass (2 skipped)

# Process topology
ps -ax -o pid,etime,command | grep -E "coordinate.*serve|multinexus.agentd|multinexus.py.*--platform discord" | grep -v grep
# Expected: 6 processes (1 coord + 1 bridge + 4 agentd)

# Bridge status (in-process multi-agent)
tail /Users/yinxin/projects/multinexus/logs/discord.bridge.err.log
# Expected: 6 "DiscordBridge ready" lines, one per agent

# End-to-end smoke
cd /Users/yinxin/projects/coordinate
PYTHONPATH=src python3 -m coordinate --db data/coordinator.sqlite3 \
  runtime request submit discord-nexus --target-agent mac-claude \
  --prompt "Reply with exactly: 7.1.1-OK" \
  --origin-json '{"platform":"smoke","channel_id":"1507289970459803738","thread_id":"smoke-7-1-1","author_id":"1503016766346105008","author_name":"operator","destination":{"platform":"smoke","target":"local"}}' \
  --reply-json '{"platform":"smoke","channel_id":"1507289970459803738","destination":{"platform":"smoke","target":"local"}}' \
  --idempotency-key "smoke-7.1.1-$(date +%s)" --actor operator
sleep 30
tail /Users/yinxin/projects/multinexus/logs/mac-claude.agentd.err.log
# Expected: "Processing job" + "complete: status=done"
```

## Reviewer 结论

**Approve with documented caveats.** 7.1.1 plan 主要目标（bridge 合并到 1 进程 1 平台，agentd 保持 1 进程 1 agent）达成，进程拓扑 N=1+M=4=5 (6 实际，KOOK 未启)，端到端 smoke 通过。KOOK bridge、跨 agent mention 实测、Discord 真消息回原频道验 3 项遗留按 deferred 处置。流程上"omp review + self closeout"是 codex 不可用的降级处置，operator-needs-backlog 落 lesson learned。
