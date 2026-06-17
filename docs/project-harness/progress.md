# Project Harness Progress

Harness root: `docs/project-harness/`

## 2026-06-17

### Phase 8 dogfood cleanup — win-opencode degraded service

- **目标**: 收口 Windows `win-opencode` 接入，避免 Discord job 出现假成功、永久 thinking 或 SSH wrapper 卡死。
- **代码修复**:
  - `2b8a3a3`: Windows adapter 子进程环境不再注入 `PWD`。
  - `d1cdb93` / `8066e0c`: OpenCode 空 text 做有限重试；重试后仍为空时返回错误，并由 agentd 标记 job `failed`，不再生成 `"(no response)"` 假成功。
  - `6c926a4`: Windows `coord-ssh-win.py` 支持显式 `COORD_SSH_TARGET`、identity file、timeout。
  - `c662313`: SSH wrapper 加 `BatchMode=yes`、`StrictHostKeyChecking=accept-new`、可选 known_hosts，避免服务态交互等待。
  - `3fa17c2`: Windows wrapper 避免 OpenSSH stdin pipe；改为传单个 POSIX-quoted remote command arg，解决 `ssh -T ... sh` 在 Windows 下卡 EOF 的问题。
- **运维修复**:
  - Windows NSSM `win-claude` / `win-opencode` 服务增加 `COORD_SSH_TARGET=ubuntu@124.221.111.209`、`COORD_SSH_IDENTITY_FILE`、`COORD_SSH_KNOWN_HOSTS_FILE`。
  - 纠正服务私钥：服务器授权的是 `id_ed25519_coord_win_v2`，不是旧 `id_ed25519_coord_win`。
  - 为 LocalSystem 服务复制专用私钥到 `C:\ProgramData\ssh\coord\id_ed25519_coord_win_v2`，ACL 限制为 `SYSTEM` / `Administrators`，解决 OpenSSH `UNPROTECTED PRIVATE KEY FILE`。
- **验证结果**:
  - Windows wrapper `--version` 通过显式 v2 key 返回 `coordinate 0.1.0`。
  - `win-opencode` NSSM 服务恢复 claim/report，不再因为 SSH alias、stdin pipe 或私钥 ACL 卡住。
  - 5 个 pending smoke job 被消费：2 done (`WIN-OPENCODE-ENV-2`, `WIN-OPENCODE-ENV-4`)，3 failed (`OpenCode returned no text (events=step_start)`)。
- **结论**: `win-opencode` 链路已从“假 done / pending / SSH 卡死”降级为“明确 failed”，但 NSSM LocalSystem 下 OpenCode 仍不稳定；暂不作为默认 worker。后续需要 per-user runner 或 NSSM ObjectName=ADMIN 后再验收。

### Phase 8 preflight — manual server deploy/sync

- **目标**: 在进入 GitHub PR / review automation 前，先解决腾讯云 `/opt/coordinate` / `/opt/multinexus` 运行副本与本地开发 checkout 漂移的问题。
- **落地内容**:
  - `scripts/deploy-server.sh`: 手动部署入口，支持 `status` / `coordinate` / `multinexus` / `all`。
  - `scripts/server-smoke.sh`: 服务器健康检查，验证 systemd、`VERSION_DEPLOYED`、`coord-local`、mihomo proxy、agent registry、近期 breaker log。
  - `docs/deploy-runbook.md`: 记录 source-of-truth 边界；`/opt/*` 是部署副本，不是开发源。
- **验证**:
  - `scripts/deploy-server.sh status` 通过，coordinate / bridge 均 active，Discord proxy 可达。
  - `scripts/deploy-server.sh multinexus --skip-install` 已将腾讯云 `/opt/multinexus` 同步到 `f465a1f91ead938b355d2ca935fb48e4323dc3a8` 并重启 bridge；smoke 通过。
  - `/opt/coordinate/VERSION_DEPLOYED` 已是本地 coordinate tip `244f95f6026857fef8cd74362792435955f2c72d`，本轮无需重复部署。
- **边界**: 这是最小手动 deploy/sync，不是 GitHub Actions 自动生产发布。后续 CI/CD 应复用该脚本作为唯一部署路径。

### Phase 8 host-profile handoff smoke — dogfood closeout

- **目标**: 验证 A0 形态下 `coordinate` / Discord bridge 跑在腾讯云、worker agentd 跑在各宿主机时，handoff bootstrap 使用目标宿主机自己的 repo path，而不是服务器部署副本 `/opt/multinexus`。
- **代码/部署前提**:
  - `coordinate` branch `agents/mac-claude/phase-8-preflight-dogfood-cleanup`
    - `a9ba1c7` host-aware bootstrap / `workspace_host_profiles`
    - `fb25b78` daemon internal pump guard
    - `244f95f` relaxed handoff state preflight for summary state
  - `multinexus` branch `agents/mac-claude/phase-8-preflight-dogfood-cleanup`
    - `d315eea` bridge uses `assignment accept` returned `bootstrap_text`
    - `7ef76aa` host-profile smoke task
    - `8ca4e6e` smoke task lease release
- **Host profiles verified**:
  - `macbook-local`: `/Users/yinxin/projects/multinexus`, coordinator wrapper `/Users/yinxin/.local/bin/coord-ssh`
  - `win-admin`: `C:\Users\ADMIN\projects\multinexus`, coordinator wrapper `python C:\Users\ADMIN\projects\multinexus\scripts\coord-ssh-win.py`
- **Mac handoff result**:
  - Handoff bootstrap correctly used `/Users/yinxin/projects/multinexus` and did not leak `/opt/multinexus` as worker execution path.
  - Execution blocked in environment: Mac Claude CLI could not reach local API proxy (`ConnectionRefused` / local `claude -p` timed out). This is recorded as dogfood feedback item 12.
- **Windows handoff result**:
  - Windows checkout was first synced from `agents/mac-claude/phase-7.2-multi-host-agent-runtime` to `agents/mac-claude/phase-8-preflight-dogfood-cleanup`.
  - Handoff event `6bf3aad2-ea9d-4da3-8381-16cffa085214` generated bootstrap for `C:\Users\ADMIN\projects\multinexus`.
  - Job `request:651a60b4-327b-4aa7-95c6-b53e8bba7856` was claimed by `win-claude` and completed `done` in ~97.5s.
  - Worker result verified: Windows path present, `/opt/multinexus` not used as execution directory, branch matched, no source files/services/tokens touched.
- **Lifecycle closeout**:
  - Worker response included `[agent-report] action=done`, but coordinate did not ingest it as `agent.reported done`; bridge emitted fallback `progress.reported` instead. This is recorded as dogfood feedback item 13.
  - Operator reviewed the visible result, recorded `assignment review-result ... approved`, then `assignment mark-done`; task `phase-8-host-profile-handoff-smoke` is closed on the remote harness.

## 2026-06-10

### Phase 7.1.1 后续维护 + 回归 (mac-* agentd)

> **上下文**: phase-7.1.1 closeout 后, operator 在本机做 Discord reply path + 跨 agent handoff 回归, 发现 4 项遗留需要修. 该 commit 落在 phase-7.1.1 的 worker 分支 `agents/mac-claude/phase-7.1.1-single-platform-bridge-process` 上.

#### 修改

1. **mac-opencode context 窗口对齐** (`agents.toml`, runtime config 不入仓)
   - `context_recent_messages: 10 → 40`
   - `context_budget_chars: 4000 → 12000`
   - 理由: mac-opencode 原来只有其他 agent 的 1/3 context, 跨 agent handoff 时 `[handoff]` 头部可能被截断

2. **`{available_peers}` 占位符 + loader 注入** (`multinexus/config.py`)
   - 新增 `_render_system_prompt_placeholders()` helper, 支持 `{available_peers}` 和 `{self_id}` 占位符
   - 4 个 mac agent 的 `system_prompt` 里硬编码的 "可用 agent: xxx" 全部替换为 `{available_peers}`
   - 行为: 从 `agents.toml` 其他 `[[agents]]` 自动生成 peer 列表 (不含自己, 含所有其它 agent 包括 win-*)
   - 决策记录: 保留 win-* 在 peer 列表内 (F 阶段腾讯云部署后自动生效, 不用改 toml)

3. **`agents.toml` mac.sh 路径漂移修复** (4 处 `system_prompt` block, runtime config 不入仓)
   - `multi-agent-coordinator` → `coordinate` (项目实际目录名)
   - 全仓 grep 验证 `.py / .toml / .yaml / .sh / .json` 中残留 = 0 处
   - 历史背景: 昨天 `discord.bridge.err.log` 里 `invalid choice: 'runtime'` 错误的根因是 mac.sh 旧版本 + agents.toml 路径漂移双重叠加. agent 按旧 prompt 去 `multi-agent-coordinator/skills/coordinate-operator/scripts/mac.sh runtime ...`, 旧 binary 不认识 `runtime` 子命令. 12 小时前已自动停止.

4. **4 个 mac agentd 重启加载新 prompt** (运维动作, 不入仓)
   - `launchctl kickstart -k` 重启, **注意 launchd label 是带 `.agentd` 后缀的** (plist Label 是 `com.multinexus.mac-claude`, launchd 注册的是 `com.multinexus.mac-claude.agentd`)
   - 新 PID: 48703 / 48706 / 48709 / 48712 (启动 14:35:28)
   - 启动日志全部 `Agentd worker started`, 5 秒实时扫描 0 新错误

#### 验证

- **C — Discord reply path 终验**: PASS
  - 测试消息: `@Mclaucode 报一下时间`, message_id `1514143348888174593`
  - 链路 22 秒: `request.received (05:45:06) → job.claimed (05:45:08) → job.completed (05:45:28)`
  - jobs 表 `request:48fd85f1-10bd-4dc0-af81-179ce60c42c3` status=done
  - 0 处 "Job done" / "✅ Job 完成" 卡片
- **E — 跨 agent handoff 测试**: PASS
  - 测试文案: `@Mac Codex 请用 [handoff] @Mac Claude 让它只回复 "E-HANDOFF-OK"`
  - 5 个 job 时序: codex 收到指令 → 生成 handoff → bridge 路由 → claude 回复
  - handoff 链路总耗时 54 秒 (含两次手动触发间隔)
  - 无 mention cascade, 无 "Job done" 残留
- 配置加载相关轻量回归: 27 tests OK

#### 已知非阻塞观察

- `events` 表**没有专门的 `handoff.detected` 事件类型** — handoff 路由链路靠 jobs 表时间序列拼接追溯, 不是显式事件
- `deliveries` 表 22 个 pending 是历史积累孤儿, agent reply 不走 deliveries 表 (走 Discord API 直发)

#### 文档边界澄清

- `~/.openclaw/plans/findings.md` 是 **OpenClaw 本地工作目录生成的笔记**, 不是 multinexus 项目文档, **不应 commit 到本仓**. 它的内容是关于 multinexus 的盘点, 但权威来源应该是本目录的 `progress.md` / `dogfood-feedback.md` / `mvp-checklist.json`
- 类似地, `~/.openclaw/` 目录本身的命名属于历史遗留, 等 F 阶段腾讯云部署时统一重命名 (涉及 launchd plist / log 路径 / sqlite db 路径 / env var)

#### 遗留 (deferred, 留作后续 phase 钩子)

- KOOK bridge plist + `multinexus/kook/__main__.py` (与 phase-7.1.1 同样的 deferred, 参见原 review)
- 跨 agent mention router 在 1 进程多 client 下的实际解析路径 (phase-7.1.1 closeout 已有, 但仅覆盖 mention map 同步机制)
- `~/.openclaw/` 目录重命名
- `:memory:*` / `docs/project-harness/current/` 等 runtime 产物补进 `.gitignore` (跟今天的 commit 无关, 单独处理)

#### Harness state 回填

- `docs/project-harness/events.jsonl`: 回填 phase-5.5 / phase-7.1 / phase-7.1.1 的 closeout 事件 (22 条), 这些是 harness 之前写过但未 commit 的
- `docs/project-harness/harness-state.json`: `current_item` 从 phase-6.1-omp-smoke 更新到 phase-7.1.1, status `todo` (等待 human gate 后转 `done`)
- **入仓原因**: harness state 是项目状态权威来源的一部分, 跟 working tree 同步后才能反映当前 phase

## 2026-06-09

### Phase 7.1.1: Single Platform Single Bridge Process — implementation + closeout

- **Codex 不可用**，operator 代行 worker + reviewer 全流程
- **实施概要**：
  - `multinexus/config.py`: token 值校验抽出为 `require_token` flag；新增 `load_all_configs_for_platform()` 读所有 `[[agents]]`
  - `multinexus/agentd/__main__.py`: 调 `load_config(..., require_token=False)`
  - `multinexus/client.py`: 加 `DiscordBridge` 类（持 N 个 `DiscordClient` 共享 asyncio loop，`_on_client_ready` 跨 client 同步 `register_peer_bot`）
  - `multinexus.py`: 加 `--platform {discord,kook}` 参数；`--platform discord` 走 `DiscordBridge` 启动 N client
  - `tests/test_discord_bridge_multi_agent.py`: 11 个新测试
  - launchd: 新 `com.multinexus.discord.bridge.plist`（1 bridge）；旧 4 个 `com.multinexus.mac-X.bridge.plist` 移到 `launchd/legacy/`
- **测试**: multinexus 269/269 pass (258 legacy + 11 new), coord 731/731 pass
- **现场拓扑**（6 进程）:
  - PID 13842 coord serve
  - PID 13844 multinexus.py --platform discord（bridge, 承载 6 个 DiscordClient: mac-claude / mac-codex / mac-omp / mac-opencode / win-claude / win-openclaw）
  - PID 13846/13848/13850/13852 multinexus.agentd --agent <4 Mac agents>
- **端到端 smoke**: coord CLI `runtime request submit --target-agent mac-claude` → job `713c3ae2-...` → agentd claim → claude CLI → report done 11.6s
- **遗留 / deferred** (见 `tasks/phase-7.1.1-single-platform-bridge-process/review-feedback-2026-06-09-operator-closeout.md`):
  - KOOK bridge plist + `multinexus/kook/__main__.py` 未实现（plan 标 optional，closeout 显式 deferred）
  - 跨 agent mention 路由测试只覆盖了 mention map 同步机制（`register_peer_bot`），没测 `MentionRouter` 在 1 进程多 client 实际解析路径
  - Discord 真消息触发 reply 回原频道的 webhook 路径没测（用 coord CLI 模拟提交）
  - 流程上 omp plan review 是 operator 代写（codex 不可用），已在 `operator-needs-backlog.md` 落档
- **Coord events timeline**:
  - 17:15:04 `assignment.requested` operator
  - 17:30:19 `plan.review_requested` operator (round 1)
  - 17:30:38 `plan.approved` operator (round 1)
  - 17:36:00 `plan.rejected` omp (3 must-fix items)
  - 17:36:58 `plan.review_requested` operator (round 2)
  - 17:37:08 `plan.approved` operator (round 2, after omp feedback)
  - 18:07:06 `closeout.requested` coordinator
  - 18:08:27 `review.completed` operator (approved with caveats)
  - 18:09:10 `task.done` operator (via `harnessctl mark-done`)
- **mvp-checklist.json**: phase-7.1.1 status `done`, workflow `closed`, owner `operator` (harnessctl 自动更新)

### Phase 7.1 review (operator-side retrospective)

- 7.1 task 在 2026-06-08 15:51 由 `codex-operator` 走完 closeout → mark-done 路径
- 2026-06-09 复盘发现 plan 验收标准（`docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/plan.md` 第 38-39 行 ASCII 图）要求 "1 Discord bridge 进程 + 1 KOOK bridge 进程 + 1 coord + 1 agentd/agent" 的 N+M 拓扑，**但当前 `multinexus.py` 是 1 process 1 agent**，bridge 没合并
- 7.1 报告 closeout 时此问题未被记录，也未在 review feedback 中提出
- 处置：开 `phase-7.1.1-single-platform-bridge-process` 任务（本段之上记录的实施段）
- 现场：原 4 legacy multinexus.py 已 bootout，6 进程 N+M 拓扑（1 coord + 1 bridge + 4 agentd）已上线

## 2026-06-08

### Dogfood feedback: agent-report fallback after accept

- Observed Phase 7.1 Round 3 feedback in Discord, but coordinate did not ingest a done/closeout event; state only showed the runtime auto `action=accept`.
- Root cause in MultiNexus runtime: `_send_missing_report_fallback()` treated any `[agent-report]` in adapter output as sufficient. If the output contained an `action=accept` line plus natural-language completion, fallback did not emit progress.
- Added `contains_execution_agent_report()` so only `done`, `blocker`, or `progress` suppress the fallback; `accept` no longer counts as execution completion.
- Added regression coverage for accept-only report plus natural-language completion.

### Phase 7.1: 单机 N+M 运行架构 — round 3 rework (job polling + session resume)

- Fixed coordinate job polling: `_get_job()` was parsing `result.result.jobs` but coordinate outputs top-level `{"jobs":[...]}`. Removed `--status all` (not a valid coordinate filter), added `--workspace-id` filter.
- Preserved session resume in agentd worker mode: bridges now include `session_scope_id` and `legacy_scope_ids` in origin_json. `AgentdWorker._call_or_resume()` checks session store, calls `adapter.resume()` for existing sessions, falls back on error.
- 9 new regression tests: job polling format parsing, status filter omission, wait_for_job_result finding done jobs, worker resume flow, fresh call, resume error fallback, bridge origin scope fields.
- 256/256 pass (2 skipped: khl). harnessctl validate passes.

### Phase 7.1: 单机 N+M 运行架构 — round 3 rework (shutdown + test coverage)

- Fixed agentd worker shutdown: replaced `asyncio.sleep` with `asyncio.Event` for immediate wake on stop().
- Simplified `__main__.py` _shutdown callback: only calls `worker.stop()` (no `loop.stop()`), lets `run_until_complete` exit cleanly.
- Added `RuntimeError` catch alongside `KeyboardInterrupt` in main loop.
- Updated tests: shutdown test now verifies `_wake` event is set, worker stops immediately.
- Full suite 247/247 pass, 2 skipped (khl not installed). Harness validate passes.

### Phase 7.1: 单机 N+M 运行架构 — round 2 rework

- Addressed codex round 2 review: implemented bridge -> coordinate -> standalone agentd flow.
- Created `multinexus/agentd/worker.py`: `AgentdWorker` claims jobs from coordinate runtime via CLI, executes adapter, reports results.
- Rewrote `multinexus/agentd/__main__.py`: replaced HTTP-based `AgentDaemon` with coordinate-based `AgentdWorker`. Uses `run_until_complete` instead of `run_forever`, signal handler calls `worker.stop()` + `loop.stop()`.
- Both Discord and KOOK bridges submit via `CoordinateRuntimeClient` (committed in prior commit).
- Added 6 new tests: worker job processing (success + error + invalid payload), graceful stop, shutdown testability, shutdown callback verification.
- `khl>=0.4.0` was already committed in an earlier commit.
- Full suite 247/247 pass (2 skipped: khl not installed). harnessctl validate passed.

### Phase 7.1: 单机 N+M 运行架构 — blocker fix

- Fixed reviewer blocker: removed embedded `AgentDaemon` from both `DiscordClient` and `KookBridge`.
- Both bridges now connect to a standalone agentd via `AgentdClient` (HTTP client only).
- Created `multinexus/agentd/__main__.py`: standalone agentd launcher (`python -m multinexus.agentd --agent <id> --port <port>`).
- One agentd process per agent identity, shared by all bridges. Prevents duplicate adapter instances.
- `agentd_mode=true` now requires `agentd_port` to be set in config — fails fast if missing.
- `khl>=0.4.0` already in requirements.txt (reviewer finding was stale).
- Full suite 224/224 pass. 1 new commit.

### Phase 7.1: 单机 N+M 运行架构 — review blocker

- Reviewed `agents/mac-claude/phase-7.1-single-host-n-plus-m-runtime` after Claude's Discord completion report.
- Validation observed: `.venv/bin/python -m unittest discover tests/` passed 224 tests; `scripts/harness/harnessctl validate` passed after checklist repair; `git diff --check` passed.
- Blocker recorded through coordinate as `blocker.raised` event `3c28dada-bfa2-4d60-a04c-438673caae04`.
- Blocking findings:
  - The implementation starts an embedded `AgentDaemon` inside each bridge process. If Discord and KOOK bridges both run for the same agent, they can still create two adapter/agentd instances, so the acceptance goal "only one agentd per agent identity shared by all IM bridges" is not met.
  - The actual chain is `bridge -> local HTTP agentd -> adapter`; it bypasses the planned `bridge -> coordinate -> agentd` control-plane boundary for Phase 7.1 dogfood.
  - `multinexus.kook.bot` cannot import in the current environment because `khl` is not in `requirements.txt`; current tests cover KOOK mention parsing but not KOOK bridge startup/import.
- Also repaired missing Phase 7 checklist metadata: added `phase-7-n-plus-m-runtime`, `phase-7.1-single-host-n-plus-m-runtime`, and `phase-7.2-multi-host-agent-runtime` to `mvp-checklist.json` so future assignment/review/blocker transitions can be tracked.

### Phase 7.1: 单机 N+M 运行架构 — rework handoff

- Added reviewer feedback at `docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/review-feedback-2026-06-08-codex.md`.
- Unblocked the task through coordinate and re-handed it to `mac-claude` with `task handoff --target-agent mac-claude`.
- Confirmed agent-specific Discord handoff was sent with `<@1507329791982833775>` and bootstrap path `docs/project-harness/tasks/phase-7.1-single-host-n-plus-m-runtime/worker-bootstrap.md`.
- `mac-claude` auto-accepted; checklist is now `status=doing`, `workflow.status=running`, owner `mac-claude`.
- Dogfood issue found during handoff: public `[HANDOFF]` status text triggered duplicate accept before the agent-specific `[handoff]` message. Fixed in coordinate by changing public handoff status rendering to `[HANDOFF_STATUS]` while keeping agent-specific protocol messages unchanged.

### Phase 7.1: 单机 N+M 运行架构 — implementation

- Created `multinexus/protocol.py`: platform-agnostic `AgentRequest`/`AgentResponse` envelope with `Platform` enum, `PlatformOrigin`/`PlatformDestination` for cross-platform routing. JSON serialization round-trip tested.
- Created `multinexus/agentd/server.py`: `AgentDaemon` HTTP server (aiohttp) that accepts `AgentRequest` via POST, processes through existing adapters, manages session lifecycle, returns `AgentResponse`. One agentd per agent identity. Includes health check endpoint.
- Created `multinexus/agentd/client.py`: `AgentdClient` HTTP client for bridges to submit requests to agentd.
- Modified `multinexus/client.py`: added bridge mode (`agentd_mode=true`). When enabled, `DiscordClient` no longer calls `make_adapter()` directly — it submits `AgentRequest` to local agentd. Legacy mode preserves existing behavior.
- Created `multinexus/kook/`: KOOK bridge module ported from kook-nexus.
  - `kook/bot.py`: `KookBridge` — WebSocket + HTTP polling, message dedup, transient filtering, handoff dedup. Submits to agentd in bridge mode.
  - `kook/mentions.py`: `KookMentionRouter` — KMarkdown `(met)ID(met)` / `(rol)ID(rol)` parsing, agent addressing, outbound mention conversion.
- Updated `multinexus/models.py`: added `agentd_mode`, `agentd_port`, `agentd_host`, `kook_poll_*` fields.
- Updated `multinexus/config.py`: parse new fields from TOML.
- Updated `docs/project-harness/architecture.md`, `domain-model.md`, `scope.md` for N+M architecture.
- 41 new tests: 10 protocol, 9 agentd HTTP, 21 KOOK mentions + 1 lazy import. Full suite 224/224 pass.
- 5 commits on `agents/mac-claude/phase-7.1-single-host-n-plus-m-runtime`.

## 2026-06-03

### Phase 6.1: omp Adapter 基础接入 — implementation

- Created `multinexus/adapters/omp.py`: `OmpAdapter(AgentAdapter)` with `call()`, `resume()`, `health_check()`.
  - Uses `omp -p --auto-approve` for non-interactive mode.
  - `resume()` passes `--resume <session_id>`.
  - Optional `--model` and `--thinking` flags via `omp_model` / `omp_thinking` config.
  - Simple subprocess communicate (no streaming), with timeout via `asyncio.wait_for`.
- Extended `multinexus/models.py`: added `omp_bin`, `omp_model`, `omp_thinking`, `omp_auto_approve` fields to `AgentConfig`.
- Updated `multinexus/config.py`: parse omp fields from TOML with `_first_existing_command` for `omp_bin`.
- Registered in `multinexus/adapters/factory.py`: `adapter == "omp"` → `OmpAdapter(config)`.
- Added mac-omp config block to `agents.toml` (local, gitignored) with `omp_model = "opus"`, `omp_thinking = "high"`.
- 16 new tests in `tests/test_omp_adapter.py`: CLI arg construction (auto-approve, model, thinking, resume), call/resume/failure/timeout/missing CLI/health check/factory.
- Full test suite: 183/183 pass (167 existing + 16 new).

### Phase 6.1: mac-omp Smoke Test — verification

- **omp CLI**: `omp/15.7.6` available at `/Users/yinxin/.bun/bin/omp`
- **Health check**: `{"adapter": "omp", "bin": "omp", "available": true, "path": "/Users/yinxin/.bun/bin/omp"}` — PASS
- **Real call**: `omp -p --auto-approve "Reply with exactly: OK smoke-test-passed"` returned "OK smoke-test-passed" — PASS
- **Unit tests**: 16/16 omp adapter tests pass; full suite 183/183 pass
- **plist**: `com.multinexus.mac-omp.plist` validated with `plutil -lint` — OK
- **Shell scripts**: `bash -n` all pass; `launchd.sh` AGENTS includes `mac-omp`
- **Known gap**: `session_id` is not captured from `omp -p` output (omp print mode does not output session IDs); resume support is limited without interactive mode
- All Phase 6.1 acceptance criteria met:
  1. OmpAdapter constructable via `make_adapter()` ✅
  2. `--auto-approve` in call/resume CLI args ✅
  3. `--resume <session_id>` passed correctly ✅
  4. Health check format correct ✅
  5. All omp adapter tests pass ✅
  6. No existing test regression (183/183) ✅

## 2026-06-01

### Phase 5.4: Workspace Doctor And Full Harness Init — implementation

- Created `src/multi_agent_coordinator/doctor.py`: workspace harness diagnostics module with `diagnose_workspace()` function. Produces a `DoctorReport` that checks workspace path, harness root, harnessctl availability/executability, required and optional file presence, checklist validity, harnessctl validate/doctor health, and distinguishes between `none`, `minimal_file_backed`, and `full_harness_runtime` modes.
- Added `workspace doctor <workspace_id>` CLI subcommand. Returns exit 0 for full_harness_runtime, 1 otherwise.
- Enhanced `init_file_harness()` in `onboarding.py` with `init_full_harness()`: copies `scripts/harness/` runtime from a `--source` directory, creates protocol file stubs (scope.md, architecture.md, domain-model.md, runbook.md), ensures minimal harness files exist. Supports `--dry-run`, never overwrites existing files, validates harness_root is within workspace path (security boundary), updates workspace `harnessctl_path` when harnessctl is created.
- Updated `workspace init-harness` CLI to accept `--mode full|minimal`, `--source`, and `--dry-run` flags. Full mode requires `--source`, minimal mode requires `--root`/`--task-id`/`--plan-doc`.
- 22 new tests in `tests/test_doctor.py`: doctor (missing path, missing root, missing harnessctl, not executable, healthy full, invalid checklist, bus note, to_dict), full init (dry-run, creates files, no overwrite, updates harnessctl_path, missing source, root outside workspace, unknown workspace, empty source, to_dict), CLI integration (doctor unknown/minimal, init full requires source, init minimal requires root).
- Coordinator test suite: 664/664 pass (642 existing + 22 new).
- Updated `docs/project-harness/runbook.md` with new workspace onboarding order (register → doctor → init-harness full → doctor verify → task create → audit).

### Phase 5.3: Agent Registry Auto-Sync — implementation

- Created `src/multi_agent_coordinator/agent_registry.py`: TOML parser for `[[agents]]` and `[[external_agents]]` that extracts `id`, `display_name`, `discord_user_id`, and `agent_type`. Skips entries missing `discord_user_id`, fails closed on duplicate IDs or Discord user IDs.
- Added `sync_workspace_agents` batch helper to `db.py` with merge (default, preserves manual overrides) and `--replace` (replaces entire registry) semantics.
- Added `workspace agent sync` CLI subcommand with `--source` and `--replace` flags. Outputs JSON summary: `added`, `updated`, `unchanged`, `skipped`, `removed` (replace only).
- 16 new tests: 6 TOML parsing, 6 DB sync, 4 CLI integration (including token leak prevention).
- Coordinator test suite: 640/640 pass. multinexus test suite: 165/165 pass.
- End-to-end verified: synced 8 agents from real `agents.toml` to coordinator DB.
- Updated `agents.toml.example` to mark `discord_user_id` as required for registry sync.
- Updated runbook with `workspace agent sync` commands.

### Phase 5.2: Task-Scoped Session Lifecycle — implementation

- Added canonical session scope helpers for `channel:<channel_id>`, `thread:<thread_id>`, and `task:<workspace_id>:<task_id>`, with legacy numeric scope fallback for existing sessions.
- Extended `SessionStore` with active lookup fallback, scope-prefix/task queries, and task stale/archive lifecycle operations.
- Updated coordinator handoff runtime so accepted task handoffs use task scope, resume the same task session, isolate different tasks, and archive local task sessions on coordinator closeout/done lifecycle notices without executing coordinator mutations from Discord text.
- Updated text and slash session status/reset output to show scope type.
- Updated session persistence design and runbook with task scope priority, archive semantics, and contamination troubleshooting.
- Validation: targeted session/command/handoff tests passed; full suite `.venv/bin/python -m unittest discover tests/` passed with 161 tests.

### Phase 5.1: Handoff Runtime Hardening — runtime tests and protocol docs

- Added 12 runtime tests in `tests/test_coordinator_handoff_runtime.py` covering:
  - Accept failure: sends `[agent-report] action=blocker`, adapter NOT called.
  - Accept success: sends accept report, reads bootstrap, calls adapter with bootstrap prompt.
  - Bootstrap missing: adapter still called, prompt notes bootstrap missing.
  - All report sends use `AllowedMentions.none()`.
  - Action scope: only `assignment.accept` auto-executed; `mark-done`, `closeout`, `merge`, `deploy`, `pr` all rejected.
- Created `docs/agent-report-protocol.md`: documents report format, supported actions, auto-accept behavior, and when to use Discord report vs coordinator CLI.
- Full test suite: 134 pass (122 existing + 12 new).

## 2026-05-29

### Round 1 — Initial implementation

- Worker implemented all Phase 3.3 launchd artifacts:
  - 3 plist templates (`launchd/com.multinexus.mac-{claude,codex,opencode}.plist`)
  - Shared lib (`scripts/lib/launchd.sh`)
  - 4 management scripts (`scripts/{start,stop,status,uninstall}.sh`)
- Fixed `start.sh` plist update semantics: `bootout` + `bootstrap` cycle replaces `kickstart -k` so launchd reloads changed plists.
- Added launchd documentation section to `docs/platform-setup.md`.
- Static validation passed: `plutil` 3/3, `bash -n` all pass, 106 tests OK.
- Submitted for review.

### Round 2 — Review findings addressed

- **Finding 1**: `check_manual_process` in `scripts/lib/launchd.sh` used a narrow `pgrep -f "multinexus.py --agent $agent"` pattern that missed invocations with intervening flags (e.g. `python multinexus.py --config agents.toml --agent mac-claude`). Fixed to `nexus\.py.*--agent[= ]${agent}\>` which matches `--agent X` and `--agent=X` regardless of flag order.
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
- Synced wording around coordinator Discord daemon, targeted agent handoff delivery, multinexus coordinator handoff auto-accept, and the rule that task lifecycle state changes go through coordinator CLI rather than direct harness JSON edits.
- Sanity-checked documented coordinator commands against current `mac.sh --help` output.
- Validation: `git diff --check` passed; `scripts/harness/harnessctl validate` passed; `scripts/harness/harnessctl doctor` exited 0 with existing optional/current file misses (`current/task_plan.md`, `init.sh`).
