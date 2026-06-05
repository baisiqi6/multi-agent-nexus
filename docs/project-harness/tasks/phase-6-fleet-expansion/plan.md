# Phase 6: Fleet Expansion（多设备 Agent 舰队）

## 背景

Phase 5 已经把 coordinator + discord-nexus 单机协作闭环打牢。现在进入下一个维度：
**多设备、多后端、跨平台 agent 舰队**。

当前全部 managed agent 都跑在一台 Mac 上（mac-claude、mac-codex、mac-opencode、mac-hermes）。现实场景需要把工作负载分散到多台设备：
- 一台 Windows 机器跑 Windows 专属工具链（VS build、MSVC 编译、PowerShell 脚本）
- 一台 Linux 服务器跑长时间训练或 benchmark
- 可能还有第二台 Mac 分担负载

这就引出了 Phase 6 的核心问题：**coordinator 如何跨设备调度 agent**。

## 目标

1. **Phase 6.1**: 接入新的 agent 后端（omp），验证 adapter 模式的可扩展性
2. **Phase 6.2**: 设计跨设备调度方案（coordinator ↔ 远程 agent 通信协议）
3. **Phase 6.3+**: 部署 Windows / Linux agent，实际验证多设备协同

## Phase 6.1: omp Adapter 基础接入

### 范围

`discord-nexus`：

1. **新增 `adapters/omp.py`** — `OmpAdapter(AgentAdapter)`：
   - `call(prompt, *, timeout, work_dir, on_progress)` — 运行 `omp -p --auto-approve --no-session "prompt"`
   - `resume(session_id, prompt, *, timeout, work_dir, on_progress)` — 运行 `omp -p --resume <session_id> --auto-approve "prompt"`
   - `health_check()` — 检查 `omp --version` 返回码
   - 参考 `ClaudeAdapter` 结构，但不含 streaming milestone 解析（后续补）
   - 超时使用 `asyncio.wait_for` 包裹整个 subprocess

2. **注册 adapter** — 更新 `adapters/factory.py`：`adapter == "omp"` → `OmpAdapter(config)`

3. **扩展 `models.py` / `AgentConfig`**：
   - `omp_bin: str = "omp"` — omp 可执行文件路径
   - `omp_model: str | None = None` — 默认 model
   - `omp_thinking: str | None = None` — thinking level
   - `omp_auto_approve: bool = True` — 自动批准（headless 必需）

4. **更新 `config.py`** — 从 agents.toml 解析新字段

5. **新增 `agents.toml` 配置块** — `mac-omp`

6. **测试** — 新增 `tests/test_omp_adapter.py`：
   - `test_build_cmd_uses_auto_approve`
   - `test_build_cmd_includes_model_when_set`
   - `test_build_cmd_includes_thinking_when_set`
   - `test_build_cmd_resume_uses_session_id`
   - `test_config_loads_omp_fields`
   - `test_health_check`

### 非目标

- 不实现 omp streaming milestone 解析（后续按需补）
- 不在 coordinator 中增加 omp 特化逻辑
- 不修改 `[handoff]` / `[agent-report]` 协议

### 验收标准

- `OmpAdapter` 可通过 `make_adapter(AgentConfig(adapter="omp", ...))` 构造
- `--auto-approve` flag 出现在 call 和 resume 的 CLI 参数中
- resume 模式正确传递 `--resume <session_id>`
- health check 返回 `{"adapter": "omp", "bin": "omp", "available": true/false}`
- `tests/test_omp_adapter.py` 全部通过
- 不影响现有 agent 测试

## Phase 6.2: 跨设备调度方案设计（待细化）

### 核心问题

Coordinator 当前通过 Discord webhook + bot message 与 agent 通信。Discord 是天然的消息总线，不关心 agent 跑在哪台设备上——只要 agent 的 Discord bot 在线就能收到消息。

但这只是"信令面"。实际跨设备调度还需要解决：

1. **工作目录同步** — coordinator 创建 task 后生成的 bootstrap 文件、workspace 文件，远程 agent 怎么访问？
2. **代码仓库同步** — agent 需要在本地有仓库副本才能工作。Push/pull 通过 GitHub 可以解决，但 coordinator 如何知道远程仓库状态？
3. **Session 管理** — agent 在远程设备上的 session（Claude/Codex/omp 的 session 持久化）如何与 coordinator 的 task 状态关联？
4. **状态回传** — agent 执行完后的结果（done/fail/blocker）、产物（代码 commit、PR）如何可靠回传？
5. **健康监控** — coordinator 如何确认远程 agent 在线且健康？

### 候选方案（待评估）

| 方案 | 信令 | 文件同步 | 优点 | 缺点 |
|---|---|---|---|---|
| A. 纯 Discord 消息 | Discord bot | GitHub push/pull | 零基础设施改动 | 大文件不行，latency 高 |
| B. SSH 反向隧道 + socat | Discord bot | SSH tunnel 转发 git/file | 安全，已有 skill | agent 需要能建立隧道 |
| C. Tailscale / WireGuard VPN | Discord bot | 虚拟局域网内直接访问 | 透明，双向通信 | 引入新依赖，需维护网络 |
| D. 中心 Git 仓库 + webhook | Discord bot + GitHub webhook | GitHub 作为唯一真相源 | 简单，GitHub 已有 CI 集成 | 依赖外部服务，PR 流程开销 |

### 待评估维度

- 安全性（每个 agent 的 token/credential 隔离）
- 可靠性（断线重连、幂等交付）
- 运维复杂度（新增设备时的配置流程）
- coordinator 侧改动量
- agent 侧改动量

### 交付物

- `docs/cross-device-design.md` — 方案对比、选型决策、架构图
- 原型验证（至少一条跨设备端到端链路跑通）

## Phase 6.3+: Windows / Linux Agent 部署（待细化）

### 目标

- 在 Windows 机器上部署第一个 `win-xxx` agent
- 在 Linux 服务器上部署第一个 `linux-xxx` agent
- 验证 Phase 6.2 选定的跨设备方案在实际环境中可行

### 范围（待 Phase 6.2 设计完成后确定）

- Windows 平台 subprocess 适配（路径、编码、signal）
- Linux 平台适配
- 各平台 agent 的 `agents.toml` 配置
- 跨设备端到端 smoke test

## 命名规范

| Agent ID | 平台 | 示例 |
|---|---|---|
| `mac-omp` | macOS ARM64 | 当前 Mac 上的 omp |
| `mac-claude` | macOS ARM64 | 当前 Mac 上的 Claude Code |
| `win-claude` | Windows x64 | 未来 Windows 上的 Claude Code |
| `win-codex` | Windows x64 | 未来 Windows 上的 Codex |
| `linux-claude` | Linux x64 | 未来 Linux 上的 Claude Code |

前缀规则：`mac-` / `win-` / `linux-` + agent 后端名。

## 执行模型

- Phase 6.1 worker implementation 交给 `mac-claude`（已派发，running 中）
- 我（codex-operator）负责规划、审查 diff、审核测试结果
- Phase 6.2 需要在动手前仔细设计方案，**不急于写代码**
- 每个 phase 切小块，单独 review
- 没有人类明确批准时不 merge、不 deploy
- 协议 token 保持稳定：`[handoff]`、`[agent-report]`、`workspace_id=`、`task_id=`、`action=...`、`bootstrap=...`
