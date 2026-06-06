# Phase 3.3：Managed Bots 运行常驻化计划

## 背景

Phase 2/2.1 已完成混合架构：

- multinexus 只托管 managed coding agents：Claude、Codex、OpenCode。
- 小龙虾/OpenClaw 和 Hermes 是 external gateway agents，不由 multinexus 启动。
- managed adapter agent 被 bot 消息触发时，必须满足 `[handoff] + Discord @mention`。

Phase 3.1/3.2 已完成 operator commands 和 slash embeds。Discord 侧 cockpit 已经可用，下一步应提升运行可靠性：让 Mac 上的 managed bots 从手动启动变为可自动重启、可检查、可排障的常驻服务。

## 目标

将 Mac 上的 managed bots 接入 `launchd`：

- `mac-claude`
- `mac-codex`
- `mac-opencode`

实现：

- 开机/登录后自动启动。
- 进程异常退出后自动重启。
- 日志固定写入 `logs/*.log`。
- 提供统一脚本：
  - `scripts/start.sh`
  - `scripts/stop.sh`
  - `scripts/uninstall.sh`
  - `scripts/status.sh`
- 不泄露 `.env`、`agents.toml`、bot token、真实 webhook URL。

## 非目标

本阶段不做：

- 不做 coordinator 集成。
- 不做 `/task` commands。
- 不做 Hermes / 小龙虾 adapter 常驻化。
- 不改 handoff 协议。
- 不改 session persistence schema。
- 不改 slash command 行为。
- 不删除旧 `bot.py`、`cogs/`、`config.yaml`。
- 不引入 PM2 作为新多 bot 架构的主方案。

## 当前运行方式

当前 managed bot 手动启动方式：

```bash
.venv/bin/python multinexus.py --agent mac-claude
.venv/bin/python multinexus.py --agent mac-codex
.venv/bin/python multinexus.py --agent mac-opencode
```

配置来源：

- `agents.toml`：真实本地 agent 配置，不入库。
- `.env`：真实 token 环境变量，不入库。
- `agents.toml.example`：可提交的示例配置。

测试命令：

```bash
.venv/bin/python -m unittest discover tests/
```

当前 Phase 3.2 验收基线为 106 tests OK。

## 推荐文件结构

新增：

```text
scripts/
  start.sh
  stop.sh
  uninstall.sh
  status.sh
  lib/
    launchd.sh

launchd/
  com.multinexus.mac-claude.plist
  com.multinexus.mac-codex.plist
  com.multinexus.mac-opencode.plist
```

运行时目录：

```text
logs/
  mac-claude.log
  mac-claude.err.log
  mac-codex.log
  mac-codex.err.log
  mac-opencode.log
  mac-opencode.err.log
```

`logs/` 已应在 `.gitignore` 中，不提交实际日志。

## Launchd 设计

每个 managed bot 一个 LaunchAgent：

| Agent | launchd label | plist |
|---|---|---|
| `mac-claude` | `com.multinexus.mac-claude` | `launchd/com.multinexus.mac-claude.plist` |
| `mac-codex` | `com.multinexus.mac-codex` | `launchd/com.multinexus.mac-codex.plist` |
| `mac-opencode` | `com.multinexus.mac-opencode` | `launchd/com.multinexus.mac-opencode.plist` |

建议使用用户级 LaunchAgent，安装到：

```text
~/Library/LaunchAgents/
```

不要使用系统级 `/Library/LaunchDaemons/`，原因：

- Bot token 和 agent CLI 登录态属于当前用户。
- Claude/Codex/opencode CLI 通常依赖当前用户 home 目录。
- 用户级服务更容易排障和清理。

### Plist 关键字段

每个 plist 应包含：

- `Label`
- `ProgramArguments`
- `WorkingDirectory`
- `RunAtLoad`
- `KeepAlive`
- `ThrottleInterval`
- `StandardOutPath`
- `StandardErrorPath`
- `EnvironmentVariables`

`ProgramArguments` 不走 shell，直接调用 `.venv/bin/python`：

```xml
<key>ProgramArguments</key>
<array>
  <string>/Users/yinxin/projects/multinexus/.venv/bin/python</string>
  <string>/Users/yinxin/projects/multinexus/multinexus.py</string>
  <string>--agent</string>
  <string>mac-claude</string>
</array>
```

`WorkingDirectory`：

```xml
<key>WorkingDirectory</key>
<string>/Users/yinxin/projects/multinexus</string>
```

日志：

```xml
<key>StandardOutPath</key>
<string>/Users/yinxin/projects/multinexus/logs/mac-claude.log</string>
<key>StandardErrorPath</key>
<string>/Users/yinxin/projects/multinexus/logs/mac-claude.err.log</string>
```

防止配置错误时高频重启：

```xml
<key>ThrottleInterval</key>
<integer>30</integer>
```

环境变量至少包含：

```xml
<key>HOME</key>
<string>/Users/yinxin</string>
<key>PYTHONUNBUFFERED</key>
<string>1</string>
<key>PATH</key>
<string>/Users/yinxin/.local/bin:/Users/yinxin/.nvm/versions/node/v24.14.1/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
```

是否需要额外 PATH 待实现时根据 CLI 位置决定。优先策略：

- Python 入口使用绝对路径。
- Claude/Codex/opencode binary 通过 `agents.toml` 的 `claude_bin` / `codex_bin` / `opencode_bin` 显式配置。
- 避免依赖 interactive shell 的 PATH。
- `HOME` 必须显式设置，避免 CLI 登录态、缓存目录、配置目录解析到错误位置。
- `PATH` 只是保守兜底，不能替代 `agents.toml` 中的绝对 binary 配置。

## 脚本设计

### `scripts/lib/launchd.sh`

共享逻辑：

- repo root 检测。
- agent list：

```bash
AGENTS=("mac-claude" "mac-codex" "mac-opencode")
```

- label 生成：

```bash
com.multinexus.${agent}
```

- plist 源路径：

```bash
launchd/com.multinexus.${agent}.plist
```

- plist 安装路径：

```bash
~/Library/LaunchAgents/com.multinexus.${agent}.plist
```

- 支持参数：
  - 无参数：作用于全部 agents。
  - 一个 agent id：只作用于该 agent。
- 手动进程检测：
  - `pgrep -fl "multinexus.py --agent ${agent}"`
  - 如果发现同 agent 已有非 launchd 管理进程，`start.sh` 必须拒绝启动并打印 PID。
  - 原因：同一个 Discord bot token 不能同时有两个 Gateway 连接。

### `scripts/start.sh`

用途：

```bash
scripts/start.sh
scripts/start.sh mac-claude
```

行为：

1. 创建 `logs/`。
2. 创建 `~/Library/LaunchAgents/`。
3. 检查 `agents.toml` 和 `.env` 存在，但不打印内容。
4. 检查同 agent 是否已有手动进程；如有则拒绝启动。
5. 复制或安装对应 plist。
6. 执行：

```bash
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.multinexus.mac-claude.plist"
launchctl kickstart -k "gui/$(id -u)/com.multinexus.mac-claude"
```

如果 service 已经 bootstrap，脚本应友好处理，不应把已运行状态当作失败。

### `scripts/stop.sh`

用途：

```bash
scripts/stop.sh
scripts/stop.sh mac-codex
```

行为：

```bash
launchctl bootout "gui/$(id -u)/com.multinexus.mac-codex"
```

如果 service 不存在，应输出 already stopped，不应硬失败。

语义：

- `stop.sh` 是临时停止当前 LaunchAgent。
- `stop.sh` 不删除 `~/Library/LaunchAgents/*.plist`。
- 如果 plist 仍保留，用户下次登录后 launchd 可能再次启动该服务。

### `scripts/uninstall.sh`

用途：

```bash
scripts/uninstall.sh
scripts/uninstall.sh mac-codex
```

行为：

1. 先执行对应 agent 的 `bootout`，忽略 already stopped。
2. 删除安装到 `~/Library/LaunchAgents/` 的对应 plist。
3. 不删除 repo 内 `launchd/*.plist` 模板。
4. 不删除 `logs/`、`data/`、`.env`、`agents.toml`。

语义：

- `uninstall.sh` 是永久取消当前用户级常驻注册。
- 后续需要重新常驻时，再执行 `scripts/start.sh` 安装并启动。

### `scripts/status.sh`

用途：

```bash
scripts/status.sh
scripts/status.sh mac-opencode
```

行为：

1. 对每个 agent 执行：

```bash
launchctl print "gui/$(id -u)/com.multinexus.mac-opencode"
```

2. 输出简洁状态：

- loaded / not loaded
- pid（如果有）
- last exit status（如果可取）
- log path
- 是否存在同 agent 手动进程（如存在，输出 warning + PID）

可以先用 `launchctl print` 原始输出作为第一版，后续再格式化。

## 安全要求

必须保持：

- 不提交 `.env`。
- 不提交 `agents.toml`。
- 不在脚本中写 token。
- 不在 plist 中写 token。
- 不打印 token。
- 不提交真实 webhook URL。
- 不启动 Hermes / 小龙虾 adapter。

启动前建议检查：

```bash
test -f agents.toml
test -f .env
```

但脚本不应打印文件内容。

## 配置要求

真实 `agents.toml` 中：

- `[[agents]]` 只放 managed coding agents。
- `[[external_agents]]` 放小龙虾/Hermes 的 Discord user id，用于 handoff 路由。
- Mac 常驻阶段只启动：
  - `mac-claude`
  - `mac-codex`
  - `mac-opencode`

不要把 Hermes / 小龙虾 放入本阶段 launchd plist。

## 实现步骤

### Step 1：确认当前基线

```bash
git status --short
.venv/bin/python -m unittest discover tests/
```

预期：

- 当前未提交改动可理解，不覆盖他人改动。
- 测试通过，当前 Phase 3.2 基线为 106 tests OK。

### Step 2：新增 launchd plist

新增：

```text
launchd/com.multinexus.mac-claude.plist
launchd/com.multinexus.mac-codex.plist
launchd/com.multinexus.mac-opencode.plist
```

每个 plist 只差：

- `Label`
- `--agent`
- stdout/stderr log path

### Step 3：新增 scripts

新增：

```text
scripts/lib/launchd.sh
scripts/start.sh
scripts/stop.sh
scripts/uninstall.sh
scripts/status.sh
```

脚本应：

- 使用 `set -euo pipefail`。
- 使用 repo root 相对定位。
- 支持 all agents 和单 agent。
- 避免打印 secrets。
- 对 already loaded / already stopped 做友好处理。
- `start.sh` 必须拒绝同 agent 手动进程和 launchd 进程并存。
- `status.sh` 应提示同 agent 手动进程，避免双 Gateway 风险。

### Step 4：文档更新

更新 `docs/platform-setup.md`，新增一节：

```text
## Persistent Operation with launchd (new multi-bot multinexus.py)
```

说明：

- 旧 `bot.py` / PM2 仍是 legacy single-bot 路线。
- 新多 bot 架构使用 `multinexus.py --agent <id>`。
- Mac 推荐使用本阶段新增的 launchd scripts。

### Step 5：验证

本地静态验证：

```bash
plutil -lint launchd/*.plist
bash -n scripts/*.sh scripts/lib/*.sh
.venv/bin/python -m unittest discover tests/
```

手动启动验证：

```bash
scripts/start.sh mac-claude
scripts/status.sh mac-claude
tail -f logs/mac-claude.log
```

Discord 验证：

```text
@Mac Claude health
/health
```

停止验证：

```bash
scripts/stop.sh mac-claude
scripts/status.sh mac-claude
```

卸载验证：

```bash
scripts/uninstall.sh mac-claude
test ! -f "$HOME/Library/LaunchAgents/com.multinexus.mac-claude.plist"
```

全部启动验证：

```bash
scripts/start.sh
scripts/status.sh
```

## 验收标准

1. `plutil -lint launchd/*.plist` 通过。
2. `bash -n scripts/*.sh scripts/lib/*.sh` 通过。
3. `.venv/bin/python -m unittest discover tests/` 通过。
4. `scripts/start.sh mac-claude` 能启动 Mac Claude。
5. `scripts/status.sh mac-claude` 能看到 loaded/running 状态。
6. `logs/mac-claude.log` 或 `logs/mac-claude.err.log` 有运行日志。
7. Discord 中 `@Mac Claude health` 或 `/health` 可用。
8. `scripts/stop.sh mac-claude` 能停止服务。
9. `scripts/start.sh` 能启动 `mac-claude`、`mac-codex`、`mac-opencode`。
10. `scripts/uninstall.sh mac-claude` 能停止并移除用户级 LaunchAgent plist。
11. `start.sh` 在发现同 agent 手动进程时拒绝启动，避免双 Gateway。
12. plist 包含 `ThrottleInterval`、`HOME`、`PYTHONUNBUFFERED`。
13. 没有启动 Hermes / 小龙虾 adapter。
14. 没有提交 secret 文件或真实 token。

## 已知风险

### PATH 与 CLI 登录态

Launchd 不加载 interactive shell 配置。`claude`、`codex`、`opencode` 如果只存在于 shell PATH 中，launchd 可能找不到。

缓解：

- 在 `agents.toml` 中使用绝对路径配置 CLI binary。
- 或在 plist 的 `EnvironmentVariables` 中设置明确 PATH。
- plist 显式设置 `HOME=/Users/yinxin`。

优先推荐绝对路径，避免 shell 环境差异。

### 日志增长

Launchd stdout/stderr 会持续追加到日志文件。第一版可以接受，后续可增加日志轮转。

后续方案：

- 使用 macOS `newsyslog` 配置。
- 或脚本提供 `scripts/logs.sh --truncate`。

### 多 agent 重复启动

如果用户手动运行 `python multinexus.py --agent mac-claude`，同时 launchd 也启动同一个 agent，会出现同 token 双 Gateway 连接风险。

验收时需确认：

- 启动 launchd 前停止手动进程。
- 每个 bot token 同时只由一个进程使用。

### agents.toml 不存在

Launchd 启动时如果缺少 `agents.toml`，服务会快速失败并被 KeepAlive 重启，造成日志刷屏。

缓解：

- `scripts/start.sh` 启动前检查 `agents.toml` 存在。
- 文档明确先创建真实本地配置。
- plist 使用 `ThrottleInterval` 限制失败重启频率。

## 后续阶段

Phase 3.3 完成后，再进入 coordinator 集成：

1. coordinator 状态事件使用 Discord embed delivery。
2. coordinator handoff delivery 使用 `[handoff] <@target>`。
3. 后续再考虑 `/task status`、`/task assign` 等操作命令。
