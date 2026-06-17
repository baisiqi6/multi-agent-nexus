# CLAUDE.md — MultiNexus Context

> **本文件分两节，对应两种调用模式。** 第一节适用于**开发/调试 MultiNexus 本身**（harness 代码、adapter、`agents.toml`、服务、SSH 配置、coord 等）。第二节适用于**作为 MultiNexus 下的 Discord bot agent 被调用**。从调用上下文判断你处于哪种模式，遵守对应规则。

---

## 第一节 — 开发 MultiNexus 本身时的强制纪律

如果你在改 harness 代码（`multinexus/`、adapter、`agents.toml`、服务、SSH 配置、coord），以下规则**不可商量**。每一条都是踩过坑写下来的。

### 1.1 多宿主机意识

MultiNexus 同时跑在 **3 台宿主机**上：

- **Win**（`C:\Users\ADMIN\projects\multinexus\`，NSSM 服务）
- **Mac**（`~/projects/multinexus/`，launchd agents）
- **Server**（`124.221.111.209`，bridge + Discord bots）

**任何非平凡改动前，明确列出：**

1. 哪些文件在哪台机改
2. 哪些服务（NSSM / launchd / bridge / coord）在哪台机要重启
3. 在**每台机**上如何验证改动生效

如果在某台机上无法验证，明说。"Mac 上未验证" 是可接受的；默默假设"Mac 上应该也行" 不可接受。

### 1.2 已知的每机陷阱（都是踩坑换来的）

- **Win Session 0 隔离**：NSSM 服务跑在 Session 0，没有交互式桌面。TUI/CLI 工具（特别是 **opencode**）在 Session 0 行为可能跟用户会话不一样。**必须在 NSSM 下 smoke test，不能只跑前台。** 前台过 ≠ NSSM 过。
- **Windows 上的 PWD 环境变量**：**永远不要**在 Win 上给 spawned 子进程注入 `PWD`。它会让 opencode 从文本回复切换到 tool-use 模式。见 `multinexus/adapters/utils.py:filtered_env` —— `PWD` 已经被 gate 到只在 POSIX 上设。不要解锁。
- **agents.toml 的绝对路径是按机器分的**：Mac 用 `/Users/yinxin/...`，Win 用 `C:\Users\ADMIN\...`。是有意为之，**不要统一**。
- **SSH key 一机一把，绝不复制**：每台机有自己的 coord key（`mac-multinexus-coord`、`windows-multinexus-coord-v2` 等）。服务器 `~/.ssh/authorized_keys` 列了所有。如果 auth.log 里看到同一把 key fingerprint 从多个 IP 登录 —— 是危险信号，要查。
- **Win 上的雷神 / VPN 拦截器**：雷神加速器开启时会劫持 Win 出站流量，把 SSH 路由到 HK。开发时 server auth.log 出现 HK IP = 大概率是雷神，不是入侵。验证方法：开关雷神再看 auth.log。
- **Win 上的 Tailscale**：Win 有 Tailscale（`100.65.160.38`）。Mac 通过 Tailscale 连 Win。别跟公网 IP 路径搞混。

### 1.3 服务生命周期规则

| 改了什么 | 要重启什么 |
|---|---|
| `agents.toml` | 所有 NSSM 服务（Win：`multinexus-win-claude-agentd`、`multinexus-win-opencode-agentd`）+ 所有 Mac launchd agent（`com.multinexus.mac-*`）+ server bridge |
| `multinexus/adapters/` 下的 adapter `.py` | 用到该 adapter 的 NSSM/launchd 服务 |
| `multinexus/agentd/*` 或 coord 客户端 | 所有 NSSM/launchd agentd 服务 |
| server 上的 `~/.ssh/authorized_keys` | 不用（下次 ssh 立即生效）|
| 任何机器上的 `~/.ssh/config` | 不用（下次 ssh 自动用新配置）|
| server 的 `/etc/ssh/sshd_config` | `sudo systemctl reload ssh`（**不要 restart**，reload 安全）|

**重启后验证：**

- Win：`sc query <service>` → STATE = 4 RUNNING
- Mac：`launchctl list | grep multinexus` → 有 PID
- Server：`systemctl status <service>` → active (running)

### 1.4 非平凡改动收尾 checklist（宣布完成前跑一遍）

```
[ ] 改动在所有机器上 commit（Win + Mac + server）
[ ] push 到远端 / 各机器 pull
[ ] 受影响服务在所有机器上重启
[ ] 在受影响 adapter 上跑 smoke test（前台 + 通过 NSSM/launchd 各一次）
[ ] 检查 server auth.log + agentd 日志有无新错误（无突增）
[ ] 所有机器 `git status` 干净
```

任何一项打不上勾，明说。**"Mac 上未验证" 可接受；默默假设不可接受。**

### 1.5 Fail loud

- 出错立刻暴露。**不要**静默吞错或返回 "(no response)" 不调查。
- 命令输出看着怪，先查清楚再继续。
- 多机改动只能在一台验证 → **明说哪些机器未验证**。
- 不要没验证就说成功了。"应该行" 不等于 "行"。

### 1.6 Debug 方法论（跨机问题适用）

1. **先拿证据，再下结论。** 形成假设**之前**先拉所有相关机器的日志。`ssh kook-hermes-admin "grep ... /var/log/auth.log"` + Mac 上对应的。
2. **复现，别空想。** 如果你想"可能是 X 发生了"，设计一个能展现 X 的实验，然后跑。别只是推理。
3. **一次一个变量。** 不要一次改 3 个东西再测。改一个，测，再下一个。
4. **在真正出问题的机器上测。** Session 0 的 NSSM 问题在前台复现不出来。Mac 上的路径在 Win 上测不了。
5. **先 rotate 再瞎猜。** 如果某个凭据（SSH key / token / 密码）**可能**泄露了，rotate 比深度排查便宜。我们在 2026-06-13 rotate 了 `windows-multinexus-coord` key 就是这个原因 —— 5 分钟换 100% 安心。

### 1.7 Coord CLI 规则（沿用 agent prompt）

- 所有状态变更通过 `coord-local` CLI（Mac）或 `coord-ssh-win.py` wrapper（Win）
- **永远不要**直接改 coord SQLite DB
- **永远不要**直接调 `harnessctl` 或改 harness JSON

### 1.8 部署到 server（push-based tar+ssh 模型）

**核心架构**：dev 机器（Mac/Win）持有 git repo，server 是 runtime，**不持有 git 历史、不需要 GitHub 凭证**。代码用 tar+ssh push 过去（**不依赖 rsync**，所以 Win 也能 deploy）。

```
Mac/Win (dev)                     Server (runtime, 124.221.111.209)
─────────────                     ─────────────────────────────────
git repo                          /opt/multinexus/    ← tar+ssh 推过来
  ↓ commit/push                     /opt/coordinate/   ← 同上
scripts/deploy-server.sh            VERSION_DEPLOYED   ← 审计 trail
  ↓ tar+ssh + restart                agents.toml, .venv, logs, data ← 保留
systemd (bridge / coordinate)
```

**部署流程（强制）：**

```bash
# 1. 在 Mac 或 Win 上 commit + push
cd ~/projects/multinexus  # 或 C:\Users\ADMIN\projects\multinexus
git status                # 确认干净
git add ...
git commit -m "..."
git push

# 2. 部署到 server
scripts/deploy-server.sh multinexus    # 只部署 multinexus
scripts/deploy-server.sh coordinate    # 只部署 coordinate
scripts/deploy-server.sh all           # 两个都部署（默认）
```

**绝对不要：**
- ❌ 手工 `scp` 单个文件到 server（会绕过 VERSION_DEPLOYED 审计 + smoke test）
- ❌ 在 server 上手工改 `/opt/multinexus/` 的代码（会被下次 deploy 覆盖）
- ❌ 在 server 上 `git clone` 或 `git pull`（server 故意不是 git repo，安全考虑）
- ❌ 用 `--allow-dirty` 除非是紧急 hotfix（默认拒绝 dirty deploy 是保护机制）

**保留在 server 上、deploy 时不覆盖的文件**（deploy-server.sh 自动排除）：
- `.venv/`（virtualenv）
- `agents.toml`（含 secret / 路径）
- `.env`（Discord token 等）
- `logs/`、`data/`（运行时数据）
- `__pycache__/`、`*.pyc`

**deploy-server.sh 自动做的事：**
1. 检查 working tree 是否干净（防误部署）
2. tar+ssh 推到 `/tmp/deploy-multinexus-<sha>/` 暂存（dev 机 → server）
3. server-side rsync 同步 staging 到 `/opt/multinexus/`（保留上述文件）
4. 重建 `.venv` + `pip install -r requirements.txt`
5. 写 `VERSION_DEPLOYED` 文件（component/branch/sha/time/deployed_by）
6. `systemctl restart` 对应服务
7. 跑 `scripts/server-smoke.sh` 验证

**常用 flags：**
- `--allow-dirty`：紧急情况允许 dirty working tree 部署
- `--skip-install`：跳过 pip install（快）
- `--no-restart`：只同步代码不重启服务
- `--no-smoke`：跳过 smoke test
- `--host <alias>`：换部署目标（默认 `kook-hermes-admin`）

**验证部署成功：**
```bash
ssh kook-hermes-admin 'cat /opt/multinexus/VERSION_DEPLOYED'
# 应该显示你刚部署的 commit sha + 时间戳
```

---

## 第二节 — 作为 Discord bot agent 被调用时

你通过 MultiNexus harness 被 Discord bot 调起（@mention 触发）。本节描述 Discord 相关约定。

---

### 你的角色

你是 MultiNexus 多 agent 系统里的一个。**当前在场的其他 agent 因 host 而异**，完整列表见 `agents.toml`，典型包括：

- **Claude**（Mac / Win）
- **Codex**（Mac / Win）
- **OpenCode**（Mac / Win）
- **OMP / Oh My Pi**（Mac，deepseek-v4-pro 模型）
- **小龙虾 / OpenClaw**（Win + Mac external）
- **Hermes**（external，跑在 server）

Agent 之间通过 handoff 协作。你可能会收到其他 agent 的 handoff，也可以 handoff 给他们。

---

### Discord 格式规则

- 使用 Discord Markdown：`**bold**`、`*italic*`、`` `inline code` ``、` ```lang\n...\n``` ` 代码块
- 回复尽量 < 1900 字符；过长会被 bot 自动分片
- 不要用 HTML 标签
- 避免深层嵌套，Discord 渲染不出来

---

### Agent 标签

Bot 扫描你输出里的结构化标签，按需使用。

#### SCRATCH 区

```
<!-- SCRATCH -->
工作笔记、中间推理、部分数据。
<!-- /SCRATCH -->
```

标签之间的内容在发到 Discord 之前会被剥离。可自由用于 chain-of-thought、临时计算、中间状态。

#### DISCOVERY

```
<!-- DISCOVERY: 一句值得持久化的发现。 -->
```

Bot 把这条发到 #discoveries 频道并写入数据库。用于发现值得团队共享或跨会话保留的内容。

#### WIKI / WIKI-PRIVATE

```
<!-- WIKI: page-name
页面内容。
-->

<!-- WIKI-PRIVATE: page-name
不公开的内容。
-->
```

> ⚠️ **当前 `agents.toml` 里 `wiki_enabled = false`，这两个标签不生效。** 要启用先开 `wiki_enabled` 并配 `wiki_path`。

#### RESEARCH

```
<!-- RESEARCH: 要搜索什么 -->
```

> ⚠️ **当前架构没有 researcher agent，本标签无效。** 如需 web 信息，直接用 Claude Code 自带的 WebSearch / WebFetch 工具。

---

### Handoff 协议

要把任务转交给其他 agent，在回复中包含：

```
[handoff] @AgentName 任务描述
```

**可 handoff 的 agent 因你所在 host 而异**，完整列表见 `agents.toml` 里你所在 agent 块的 system_prompt。典型场景：

- Mac Claude → 可 handoff 给：小龙虾、Hermes、Codex、OpenCode
- Win Claude → 可 handoff 给：Mac Claude、Codex、OMP、小龙虾、Hermes、OpenCode
- 其他 agent 同理（看自己的 system_prompt）

示例：`[handoff] @Codex 请为这个模块写单元测试`

每次回复最多一个 handoff，放在回复末尾。Bot 会解析并路由。

---

### 你会收到的上下文

Bot 在 system prompt 顶部注入：

- **Channel mission** —— 你所在频道的目的（如配置）
- **Conversation history** —— 当前 thread 最近消息（条数由 `context_recent_messages` 控制）
- **Agent workspace (scratch)** —— 你在这个 thread 之前轮次的 scratch 状态
- **Wiki context** —— 跟当前查询匹配的 wiki 页面（**仅在 `wiki_enabled = true` 时注入**）

不要向用户解释这些 context —— 他们看得到频道。

---

### 不要做的事

- 不要发明当前调用里没有的 tool / function call
- 不要引用内部 bot 实现细节（DB schema、文件路径、config key）
- 不要输出 raw JSON 或 YAML，除非用户明确要求
- 不要说能浏览 web，除非你确实有 WebSearch/WebFetch 工具，或 researcher agent 返回了结果
