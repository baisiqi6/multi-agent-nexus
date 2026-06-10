# Phase 7.2 Tencent Cloud Preflight

## 目标

为 Phase 7.2 multi-host agent runtime 的腾讯云单机部署做准备，**不**做实际迁移、**不**改 runtime 行为、**不**改 agentd / coord / bridge 任何业务代码。本任务只做诊断 + 最小部署方案 + smoke test 路径，作为 7.2 阶段 A 实施任务的入站 context。

## 任务边界

### 做

- 阅读 multinexus 7.1 / 7.1.1 / 7.1.2 + coordinate 7.1.1 / 7.1.2 + Phase 7.2 plan 相关代码和文档
- 梳理当前链路中哪些部分仍**假设** coord DB / CLI 在本机
- 判断如果 coord 迁到腾讯云，**当前 agentd 协议（CLI subprocess）**是否足够；是否需要 HTTP API；是否需要 outbound polling；需要哪些 token / env / 端口 / 防火墙配置
- 输出 7.2 阶段 A 的最小部署方案（哪台机器跑什么进程 / 端口 / secrets / smoke test）
- 列出 blockers 和 explicit 不做

### 不做

- **不**改代码
- **不**改 `agents.toml` / token
- **不**启动或停止任何现有 launchd 服务
- **不**做 KOOK bridge
- **不**做实际腾讯云迁移
- **不**做 HTTP API（**这是 7.2 阶段 B 的范围**，**不是**阶段 A preflight）
- **不**做 PostgreSQL 迁移
- **不**做 HA / 多 coord 副本

## 当前状态盘点（事实）

### 进程拓扑（2026-06-10 实际现场）

```
Mac:
  PID 74532  coord serve (pyenv 3.12.13, 14+ 小时存活)
  PID 68595  multinexus bridge --platform discord (15+ 小时存活)
  PID 48703  multinexus.agentd --agent mac-claude
  PID 48706  multinexus.agentd --agent mac-codex
  PID 48709  multinexus.agentd --agent mac-omp
  PID 48712  multinexus.agentd --agent mac-opencode
```

6 进程 N+M 拓扑，`runtime` error 流 7+ 小时前停。链路通。

### Multinexus 7.1.1 / 7.1.2 在我停手之后又推进了 5 个 commit

```
34d86f6 chore: extend .gitignore to cover special-named sqlite files
1d65a0a docs: mark historical task plans and design drafts with banner
cbb312b docs: replace stale multi-agent-coordinator path with coordinate
48362d0 fix(config): dynamic {available_peers} placeholder + harness state sync
c91d45b dogfood: route coordinator handoffs through agentd
```

`c91d45b` 是关键：把 `_try_coordinator_handoff` 改用 `resolve_workspace_path(db_path, workspace_id, fallback)` 动态解析 workspace path，**摆脱了** `coordinator_workspace_path` 单一来源。**7.2 阶段 A 的 workspace 路径解析已经预埋**。

### Coordinate 7.1.1 / 7.1.2 在我停手之后又推进了 5 个 commit

```
9106687 docs+chore: add docs index and tighten .gitignore for runtime artifacts
629c43f docs: mark historical task plans and design drafts with banner
13f1734 docs: replace stale multi-agent-coordinator path with coordinate
9924110 review: suppress empty runtime dialog result cards
08b5bcc Phase 7.1.2: suppress runtime dialog job result status cards
```

`08b5bcc` 7.1.2 抑制 runtime dialog job 的 `[RESULT]/[BLOCKER]` status card（**这是**"`Job done` 在 Discord 显示"问题**的另一个修复路径**，跟我 push 的 `b1d9f3d` "字段名兼容"修复独立，**两条路都生效**）。

## 本机假设梳理（迁移前必清点）

每条标注：**假设内容** / **改迁时的影响** / **改迁方案**。

### H1. coord DB 路径硬编码

- **假设**：`com.coordinate.runtime.plist` 里 `--db /Users/yinxin/projects/coordinate/data/coordinator.sqlite3`；agents.toml 第 23 行 `coordinator_db_path = "/Users/yinxin/projects/coordinate/data/coordinator.sqlite3"`
- **影响**：腾讯云 coord 写到 `/var/lib/coordinate/coord.sqlite3`（典型）；Mac agentd 通过 SSH wrapper 调远端 coord CLI，**wrapper 显式带 `--db /var/lib/coordinate/coord.sqlite3`**，**不**走 `coordinator_db_path` 字段
- **改迁方案**：腾讯云 systemd unit 写死 `--db /var/lib/coordinate/coord.sqlite3`；Mac agentd 侧 `coordinator_db_path` **保留本机值**（作 fallback / 本机调试用），**不**改成远端路径（避免 7.2 plan 第 116 行"不做 SQLite 跨主机文件共享"约束）

### H2. coord repo 路径硬编码

- **假设**：`com.coordinate.runtime.plist` `WorkingDirectory = /Users/yinxin/projects/coordinate`；agents.toml 第 22 行 `coordinator_cli_path = "/Users/yinxin/projects/coordinate/skills/coordinate-operator/scripts/mac.sh"`
- **影响**：Mac agentd 调 `mac.sh` 实际**是 `subprocess.run(['/Users/yinxin/projects/coordinate/.../mac.sh', ...])` 跑本地脚本**。**腾讯云没有这个路径**
- **改迁方案 A（SSH wrapper 替代，本阶段 A 实施）**：Mac 上写一个独立 wrapper script `~/.local/bin/coord-ssh`，**SSH 调远端 `/usr/local/bin/coord-local`**（远端 wrapper 显式带 `--db` 远端路径；group coord 方案代替 `sudo -u coord`）。改 `agents.toml` 一行 `coordinator_cli_path = "/Users/yinxin/.local/bin/coord-ssh"`；**不改 `mac.sh` 内部**（`mac.sh` 留作 Mac 本机 coord 启动的 fallback，阶段 A 不用）。**正确实现**见 impl plan 3.1（含 `printf '%q'` shell-quoting + 远端 `coord-local`）。
  - **绝不能**用 `coord@tencent-cloud`（host 不存在）
  - **绝不能**用 `\$@`（远端 shell 看到 `$@` 展开为空，agentd 参数全丢）
  - **绝不能**用 `sudo -u coord`（agentd 每 2s 调 claim，sudo 不可行）
- **改迁方案 B（HTTP API）**：agentd 直接 `requests.post("https://coord.tencent.cloud/runtime/claim", ...)` —— **需要 coord 端加 HTTP server**，**这是 7.2 阶段 B 的范围**，阶段 A preflight 不做
- **改迁方案 C（agentd 端改）**：把 `CoordinateRuntimeClient._run_cli` 的 `subprocess.run` 改成 `subprocess.run(['ssh', 'tencent-cloud', '/usr/local/bin/coordinate', ...])` —— **这是改业务代码**，阶段 A preflight 不做，**但可以**作为阶段 A 的实施 task 单独 track

### H3. MAC_DB env var 命名 + mac.sh 内容

- **假设**：`CoordinateRuntimeClient._base_env` 写 `env["MAC_DB"] = self.db_path`；`mac.sh` 调 `python3 -m coordinate --db "$DB"` 用 `DB` 变量
- **影响**：env var 名 `MAC_DB` 字面带 "MAC" —— **语义错**（跟平台无关）
- **改迁方案**：可以保留名字（**纯 cosmetic**），或 rename 为 `COORDINATE_DB`（**改业务代码 + 改测试 + 改 `agents.toml` coordinator_db_path 字段名**）。**阶段 A 不改**（rename 是 7.2 阶段 B 范畴），**接受 cosmetic 错**

### H4. Python interpreter / venv 绝对路径

- **假设**：`com.coordinate.runtime.plist` 用 `/Users/yinxin/.pyenv/versions/3.12.13/bin/python3`；`multinexus/launchd/*.plist` 用 `/Users/yinxin/projects/multinexus/.venv/bin/python`
- **影响**：腾讯云 systemd unit 用 `/usr/bin/python3` (system) 或 `/opt/coordinate/.venv/bin/python`（项目 venv）
- **改迁方案**：腾讯云 plist → systemd unit（`ExecStart=` 引用 venv python），完全独立于 Mac 的 pyenv

### H5. `resolve_workspace_path` 已经预埋

- **实际**：`c91d45b` 改了 `client.py:_try_coordinator_handoff` 用 `resolve_workspace_path(db_path, workspace_id, fallback_workspace_path)` 动态解析
- **含义**：**harness workspace 路径不再是单一来源**，可以从 coord `db_path + workspace_id` 动态算出来
- **影响**：**7.2 阶段 A 不用再改 client.py 路径解析逻辑**（这步已经做完了）

### H6. bridge plist 的 token 已经移走

- **实际**：7.1.1 commit `0af595a` (我 push 之前的) 之后被 GitHub secret scanning 拦截过 token，**重写 commit** 把 `COORDINATOR_BOT_TOKEN` 从 plist 移除
- **影响**：腾讯云 systemd unit **也**不能 inline token —— 用 `EnvironmentFile=` 指向 `/etc/coordinate/coord.env`（chmod 600），service 启动时 `load_dotenv` 读 `.env` 注入（multinexus 这边已经 7.1.1-coord-dotenv commit 修了 `load_dotenv` 兼容）

### H7. agent_id / client_type 已有 host_id 字段

- **实际**：`runtime.register_agent` 写 `agents` 表 `host_id / client_type / online_state / last_seen_at`
- **影响**：7.2 阶段 A 跑腾讯云 `server-claude` / `server-codex` agentd 时，register 用 `host_id="tencent-cloud-vm-01"`；coord registry 能区分 Mac vs 腾讯云 host
- **改迁方案**：无需改 runtime.py，**只需** `agents.toml` 加 `[[agents]]` 块 + 起 agentd 进程

## Mac agentd 远程 claim/report 协议是否够用（核心判断）

### 当前协议

`multinexus/agentd/coordinate_client.py:CoordinateRuntimeClient` 4 个方法：

| 方法 | 调 coord CLI | 频率 | 当前 timeout |
|---|---|---|---|
| `submit_request` | `coord runtime request submit ...` | 每次 bridge 收到 Discord 消息 | 30s |
| `claim_job` | `coord runtime job claim --agent-id ...` | 每 2 秒（agentd poll interval） | 30s |
| `report_job` | `coord runtime job report <job_id> ...` | 每次 adapter 完成 | 30s |
| `wait_for_job_result` | `coord job list --workspace-id ...` (poll) | bridge 端 poll，每 2 秒直到 done/failed | 30s / 单次 |

**全部走 `subprocess.run(coord CLI)`**，**不是** HTTP API。

### 阶段 A preflight 协议判断（**临时**判定）

**答案**：CLI + SSH tunnel wrapper 临时可用，**0 业务代码改动** + Mac agentd plist 改 `coordinator_cli_path` 指 wrapper 即可。

**理由**：
- `CoordinateRuntimeClient` 用 `subprocess.run`，**只要 `cli_path` 指向一个能跑 `coord` CLI 的入口就行**（本地 binary / ssh wrapper / docker exec 都行）
- 4 个方法都返回 JSON dict，stdout/timeout/error handling 已经写好
- 阶段 A preflight 业务代码 0 改动

**SSH wrapper 必须显式带 `--db`**：
- 远端命令是 `python3 -m coordinate --db /var/lib/coordinate/coord.sqlite3 runtime job claim --agent-id mac-claude`
- **不依赖本机 `MAC_DB` env var 透传**（SSH `exec` 默认不传 env，**且本机 MAC_DB 指向 Mac 本机 SQLite 路径，跟远端无关**）
- **每个调 CLI 的 wrapper 入口**都要显式 `--db /var/lib/coordinate/coord.sqlite3` 作为 CLI arg

### 阶段 A 远端协议**最终应走** `COORDINATE_URL` / HTTP API 或等价远程协议

**CLI + SSH wrapper 是临时 preflight 机制**，**最终阶段应当**：
- agentd 引入 `COORDINATE_URL` env var（7.2 plan 第 49 行明示）
- 引入 `COORDINATE_TOKEN` 鉴权（7.2 plan 第 97 行）
- agentd 内部 `CoordinateRuntimeClient` 拆出 **transport layer**：
  - `LocalTransport`: 走本地 `subprocess.run(coord CLI)`
  - `HttpTransport`: 走 `requests.post(COORDINATE_URL/runtime/claim, headers={Authorization: ...})`
  - `SshTransport`: 走 `subprocess.run(['ssh', host, 'coord', ...])` 远端 CLI
- 阶段 A preflight **只**实施 `SshTransport`（mac.sh wrapper 形式）作为可走通的 quick path
- **真正的 COORDINATE_URL/HTTP transport 留到 7.2 阶段 B**（plan 第 137 行"实现顺序"步骤 1 = "在 Mac 上用 `COORDINATE_URL` 跑本地 agentd，避免依赖隐式本地路径" —— 阶段 A 用 wrapper 隐式本地路径，**没**满足 plan 第 100 行的"应用层只依赖 COORDINATE_URL / COORDINATE_TOKEN"）

### 阶段 A **不需要** agentd outbound polling 改动的判断

- 阶段 A Mac agentd 继续跑在 Mac 本机，**不需要 outbound 隧道**
- 远端 coord 只接 inbound（Mac agentd 通过 SSH outbound 调）
- 防火墙：腾讯云安全组只需放行 **SSH inbound** (port 22) 给 Mac 出口 IP，**无需** 其他 inbound 端口

## 最小部署方案

### 方案版本：阶段 A 改 A0（腾讯云跑 coord + bridge，Mac 只跑 agentd）

按 7.2 plan 第 33-41 行 ASCII 图，**阶段 A 终态**：
```
Tencent Cloud VM:
  coord serve
  Discord bridge (multinexus.py --platform discord)
  (KOOK bridge — 7.2 阶段 A 不做)

Mac:
  4 个 Mac agentd
  (无 coord / 无 bridge)
```

**命名**：plan 表格里这个终态叫 **A0**。**A1** 是 "腾讯云只跑 coord，bridge 留 Mac" 的折中方案。**A0 是 7.2 阶段 A 的真正目标形态**（bridge 跟 coord 同侧是 7.2 plan line 33-41 隐含）。

### 腾讯云跑什么

| 进程 | 数量 | 启动方式 | 端口 |
|---|---|---|---|
| `coord serve` | 1 | systemd unit `coordinate.service` | **无 inbound**（Mac agentd 走 SSH 调） |
| `multinexus.py --platform discord` (bridge) | 1 | systemd unit `multinexus-discord-bridge.service` | **Discord outbound to gw.discord.gg** (HTTPS) |
| （**不跑** agentd） | 0 | — | — |

**腾讯云需要**：
- Ubuntu 22.04 LTS (or 24.04)
- Python 3.12.13 (apt 装 system python3 或 pyenv 装用户 python)
- `/opt/coordinate/.venv/` —— 装 `pip install -e /opt/coordinate`
- `/opt/multinexus/.venv/` —— 装 `pip install -e /opt/multinexus`
- `/var/lib/coordinate/coord.sqlite3` —— SQLite single file
- `/etc/coordinate/coord.env` (chmod 600, root:root) —— 含 `COORDINATOR_BOT_TOKEN` / `COORDINATOR_CHANNEL_ID` / `COORDINATOR_ALLOWED_USER_IDS`
- `/etc/multinexus/discord.env` (chmod 600, root:root) —— 含 4 个 `DISCORD_MAC_*_TOKEN` / `DISCORD_WIN_*_TOKEN`
- `/etc/systemd/system/coordinate.service` —— `[Service] EnvironmentFile=/etc/coordinate/coord.env; ExecStart=/opt/coordinate/.venv/bin/coordinate --db /var/lib/coordinate/coord.sqlite3 serve --pump-interval 30; WorkingDirectory=/opt/coordinate; User=coord; Restart=always`
- `/etc/systemd/system/multinexus-discord-bridge.service` —— `[Service] EnvironmentFile=/etc/multinexus/discord.env; ExecStart=/opt/multinexus/.venv/bin/python /opt/multinexus/multinexus.py --config /opt/multinexus/agents.toml --platform discord; WorkingDirectory=/opt/multinexus; User=multinexus; Restart=always`
- 防火墙规则：放行 **22/TCP inbound from Mac 出口 IP**（安全组 + iptables/nftables 双层）+ **egress HTTPS/443 to gw.discord.gg**

**腾讯云不需要**：
- 任何 agentd 进程（Mac agentd 继续 Mac）
- KOOK bridge（7.2 阶段 A 不做）
- HTTPS reverse proxy / nginx（bridge 进程**自己**直连 Discord gateway，**不**需要中间层）
- 公网域名 / TLS 证书（**Discord gateway 由 Discord 提供 TLS**；Mac agentd 走 SSH 调 coord 走 **加密 SSH tunnel** —— SSH 自带 transport encryption）

### Mac 继续跑什么

| 进程 | 数量 | 改动 |
|---|---|---|
| `coord serve` | 0 | **停**（迁到腾讯云后，Mac 不再跑 coord） |
| `multinexus bridge --platform discord` | 0 | **停**（bridge 迁到腾讯云） |
| 4 个 Mac agentd | 4 | **保留**，wrapper script 改走 SSH 远端 coord |

**Mac agentd plist 改动**：
- `agents.toml` 改 `coordinator_cli_path` 指向 `~/.local/bin/coord-ssh`（wrapper script，**显式带 `--db /var/lib/coordinate/coord.sqlite3` 远端路径**）
- `coordinator_db_path` **保留**本机值（仅作 fallback / 用于本机调试时 `--db` 缺省值；**实际**agentd 走 SSH 走远端 coord CLI，远端 DB 路径由 wrapper 显式注入）

**Mac plist 改动**：
- `com.coordinate.runtime.plist` — **bootout + 不再 bootstrap**（已迁腾讯云）
- `com.multinexus.discord.bridge.plist` — **bootout + 不再 bootstrap**（已迁腾讯云）
- `com.multinexus.mac-X.agentd.plist` × 4 — **保留**，但 plist 启动**前** mac 写 `~/.local/bin/coord-ssh` wrapper

### Secrets 放哪

| Secret | 位置 | 权限 | 来源 |
|---|---|---|---|
| `COORDINATOR_BOT_TOKEN` (coord daemon Discord bot) | `/etc/coordinate/coord.env` (腾讯云) | chmod 600, root:root | 现 Mac `~/.coordinator/daemon.env` 的 `COORDINATOR_BOT_TOKEN=...` 复制 |
| `COORDINATOR_CHANNEL_ID` | 同上 | 同上 | 同上 |
| `COORDINATOR_ALLOWED_USER_IDS` | 同上 | 同上 | 同上 |
| `DISCORD_MAC_CLAUDE_TOKEN` / `_CODEX` / `_OMP` / `_OPENCODE` | `/etc/multinexus/discord.env` (腾讯云) | chmod 600, root:root | 现 Mac `multinexus/.env` 4 个 mac-* token 复制 |
| `DISCORD_WIN_CLAUDE_TOKEN` / `_OPENCODE` / `_OPENCLAW` | 同上 | 同上 | 同上（3 个 win-* token — **腾讯云不需启用 win-* Discord 入口**，但 secrets 留作日后 7.2 阶段 B） |
| `COORDINATE_URL` / `COORDINATE_TOKEN` (agentd 鉴权，**未来** 7.2 阶段 B 字段) | 暂**不**在阶段 A 写（preflight 走 CLI + SSH wrapper） | — | 7.2 阶段 B 实施时新增 |
| SSH 私钥 (Mac → 腾讯云) | Mac `~/.ssh/id_ed25519_coord` | chmod 600 | 新生成 `ssh-keygen -t ed25519` |
| `authorized_keys` (腾讯云 → coord user) | 腾讯云 `~coord/.ssh/authorized_keys` | chmod 600 | 贴 Mac 公钥 |

**特别说明**：
- **不再**有"本机 wrapper 私存 token"位置 —— wrapper script 自身**不带 token**，**只** SSH + 远端 daemon 内部读 `EnvironmentFile`
- `multinexus/.env` 留作 Mac 本机 agentd 启动的**backup**（万一 7.2 阶段 A 失败回滚 Mac coord 时仍可工作），**不**删

### 端口开放

| 端口 | 协议 | 方向 | 源 | 目的 |
|---|---|---|---|---|
| 22 | TCP | inbound | Mac 出口 IP (ISP 动态？) | 腾讯云 sshd (Mac agentd 调) |
| 443 | TCP | outbound | 腾讯云 → Discord gateway | bridge Discord gateway 连接（**egress only**） |
| 22 | TCP | outbound | 腾讯云 | Mac (反向 optional) |

**不需要开放**：
- 80 / 443 inbound (no HTTP server in 阶段 A；Discord gateway 不需要 inbound 到腾讯云)
- 5432 (no PostgreSQL)
- 6379 (no Redis)
- 任何 agentd inbound 端口（agentd 跑 Mac 调腾讯云 coord 是 outbound SSH）

**Mac 出口 IP 问题**：ISP 动态 IP 时 SSH `authorized_keys from=` 限制会失效。**阶段 A 缓解**：
- 用 SSH `Match Address` + `AllowUsers` 限制
- 或者**接受** ISP 动态（设 fail2ban + 长 SSH key 限制爆破）
- 真正解决 = 7.2 阶段 B 的 Tailscale / Cloudflare Tunnel（plan 第 87-91 行）

### Smoke test 怎么跑

阶段 A smoke = **A0 端到端跑通**（coord + bridge 在腾讯云，4 个 Mac agentd）。具体步骤（**只描述，不在 preflight 跑**）：

1. 腾讯云 `systemctl start coordinate multinexus-discord-bridge`，`systemctl status` 看两个 service 都 running
2. Mac `ssh ubuntu@kook-hermes-admin "systemctl is-active coordinate multinexus-discord-bridge"` 确认两个 daemon 都活
3. **远端 secret 落档验证**（**不 cat 内容**，只验证文件存在 + 权限 + 长度）：
   - Mac `ssh ubuntu@kook-hermes-admin "stat -c '%a %s %n' /etc/coordinate/coord.env"` —— 应当返回 `640 <size> /etc/coordinate/coord.env`
   - 同上对 `/etc/multinexus/discord.env`
   - 预期 size > 100 字节（确认文件非空）
4. Mac `~/.local/bin/coord-ssh runtime agent register --agent-id mac-claude --host-id macbook-local --client-type agentd` —— **应当**成功（agentd 启动时已经做过，**这里**手验一次）
5. Mac `~/.local/bin/coord-ssh runtime job claim --agent-id mac-claude` —— **应当**返回 `claimed=false`（queue 空）
6. Mac `~/.local/bin/coord-ssh runtime request submit discord-nexus --target-agent mac-claude --prompt "smoke" --origin-json '{...}' --reply-json '{...}'` —— 提交一个真实 job
7. Mac 看 agentd log `Processing job request:request:xxx: agent=mac-claude` —— 5s 内 claim
8. Mac 看 agentd log `complete: status=done duration=...ms` —— claude CLI 完成
9. Mac `~/.local/bin/coord-ssh job list --workspace-id discord-nexus | grep request:xxx` —— 看到 `result.response_text`
10. Mac Discord channel 看 bot reply —— **不是** "Job done"，是真实文本（验证 `b1d9f3d` 字段兼容 + `08b5bcc` 7.1.2 抑制 status card 两者并存）
11. **远端 coord DB 检查**：腾讯云 `ssh ubuntu@kook-hermes-admin "sudo sqlite3 /var/lib/coordinate/coord.sqlite3 'SELECT id, status, host_id, last_seen_at FROM agents WHERE id = \"mac-claude\"'"` —— 看到 `host_id=macbook-local, last_seen_at` 是最近
12. **stale detection**：Mac agentd 停 5 分钟，coord 应当把 mac-claude 标 stale（**这一条 7.2 plan 第 83 行列**）

**smoke test 退出标准**：
- 所有 12 步通过
- Mac agentd stderr 没 `coordinate CLI failed` 累积
- 腾讯云 coord 进程 CPU 正常
- 腾讯云 bridge 进程 Discord gateway RESUMED log 正常
- Mac Discord bot 在线

**smoke test 失败时怎么回滚**：
- 腾讯云 `systemctl stop coordinate multinexus-discord-bridge` —— 回到单 Mac 状态（如果 Mac coord / bridge 还没 bootout 过）
- 或者 `systemctl disable coordinate multinexus-discord-bridge && rm /etc/systemd/system/coordinate.service /etc/systemd/system/multinexus-discord-bridge.service` —— 完整回滚
- Mac 重新 `launchctl bootstrap com.coordinate.runtime` + `launchctl bootstrap com.multinexus.discord.bridge` —— 回到 Mac 单机 6 进程 N+M 拓扑

### SSH wrapper 内容（关键，必须用 `printf '%q'`）

> **统一参考**: Mac `~/.local/bin/coord-ssh` wrapper **正确版**见 `phase-7.2-tencent-cloud-impl/plan.md` 第 3.1 段。**本段不再重复**——避免与 impl plan 不一致。

**关键约束**（worker 必读）:
- **远端命令**只调 `/usr/local/bin/coord-local`（**不**用 `sudo -u coord`，agentd 每 2s 调一次，sudo 不可行）
- **shell quoting 必须用 `printf '%q ' "$@"`**——**绝不能**用 `\$@` 或 `$@`（远端 shell 看到 `$@` 展开为空，agentd 参数全丢）
- **group 共享**（blocker 1）代替 `sudo -u`：multinexus / ubuntu 加到 `coord` group，`/var/lib/coordinate` chmod 2770，systemd `UMask=0007`
- **`coord@tencent-cloud` / `root@tencent-cloud` 是不存在 host**——本机 `~/.ssh/config` 只有 `kook-hermes-admin` / `kook-hermes`
- **远端 systemd 加 `SupplementaryGroups=coord`**（bridge.service）让 multinexus 进程有 coord group 写权限

**为什么** preflight 之前有 `\$@` 示例: preflight 调研时 (commit `40da1db`) 还没意识到 agentd claim 频率 (2s) + 远端 shell 参数展开两个问题。**最终实现**在 impl plan (`c8bb58c`) 修订。

`agents.toml` 改：
```toml
coordinator_cli_path = "/Users/yinxin/.local/bin/coord-ssh"
coordinator_db_path = "/Users/yinxin/projects/coordinate/data/coordinator.sqlite3"  # 留本机值, fallback
```

**阶段 A 不动 `mac.sh`** —— `mac.sh` 是 `CoordinateRuntimeClient` 的本机 fallback 路径（如果 wrapper 失效能跑回 `mac.sh` 调本机 `coord`）；阶段 A preflight **只改 `agents.toml` 的一行 `coordinator_cli_path`**，**不改** `mac.sh` 内部。

## Blockers（必须先解才能进 7.2 阶段 A 实施）

### B1. `agents.toml` 写死了 `coordinator_cli_path` 指向本机 `/Users/yinxin/.../mac.sh`

- **怎么解**：在腾讯云 setup 前，**先在 Mac 写 wrapper script `~/.local/bin/coord-ssh`**，内容（**正确版** —— 用 `printf '%q'` shell-quoting 避免 `$@` 远端展开为空）：
  ```bash
  #!/usr/bin/env bash
  # Mac → 腾讯云 coord wrapper
  # 远端命令调 /usr/local/bin/coord-local (远端 wrapper 显式带 --db 远端路径)
  # group coord 方案代替 sudo -u coord (blocker 1 + 2)
  # **绝不能**用 \$@ (远端 shell 看到 \$@ 展开为空, agentd 参数全丢)
  remote_cmd=$(printf '%q ' /usr/local/bin/coord-local "$@")

  exec ssh \
      -o ServerAliveInterval=30 \
      -o ServerAliveCountMax=10 \
      -o ConnectTimeout=10 \
      -o StrictHostKeyChecking=accept-new \
      -i ~/.ssh/id_ed25519_coord \
      ubuntu@kook-hermes-admin \
      "$remote_cmd"
  ```
  然后 `chmod +x ~/.local/bin/coord-ssh`
- **改 `agents.toml`**：仅一行 `coordinator_cli_path = "/Users/yinxin/.local/bin/coord-ssh"`
- **`coordinator_db_path` 保留本机值**（不改成远端 SQLite 路径）—— wrapper 内部显式带 `--db` 远端路径，**不依赖** `coordinator_db_path` 字段
- **阶段 A 不动 `mac.sh`** —— `mac.sh` 仍指向本机 coord binary，作为 Mac 本机 coord 启动（**腾讯云 setup 之前**）的 fallback；**改迁后** 4 个 Mac agentd 全走 `coord-ssh` wrapper，`mac.sh` 临时 unused 但保留
- **这是配置改动**（一行 `agents.toml` + 一个新 wrapper 文件），**不是业务代码改动**，**不算** preflight 的"不碰 agents.toml"约束违反（**7.2 实施**做，不是 preflight 做）

### B2. `coordinator_db_path` 字段名误导

- **影响**：agentd 不直接用这个字段（仅 `mac.sh` 内部 `MAC_DB` env 注入用），**但**字段名误导
- **怎么解**：阶段 A **不改字段名**（rename 算 7.2 阶段 B 范围），**接受** 字段名跟实际内容不符

### B3. Tencent cloud 安全组要预配 SSH inbound

- **怎么解**：腾讯云控制台 → 安全组 → 放行 22/TCP inbound，源 IP = Mac 出口 IP（**问题**：Mac 出口 IP 可能动态，**要 Mac 出口 IP 静态或用 Tailscale** —— 阶段 A 接受 fail2ban 风险）

### B4. SSH key 从 Mac 推到腾讯云

- **怎么解**：`ssh-keygen -t ed25519` 在 Mac 生成，`ssh-copy-id ubuntu@kook-hermes-admin` 推公钥。**需要 Mac 出口 IP 已知**（B3 依赖）

### B5. Mac agentd 30s subprocess timeout 不够远端

- **影响**：腾讯云 coord CLI 启动 + SSH 握手 + 处理 + 返回 ≥ 30s 时，agentd 会 `subprocess.TimeoutExpired`
- **怎么解**：**阶段 A 不改 `CoordinateRuntimeClient._run_cli` timeout**（业务代码）。**改 wrapper script** 调 `ssh -o ConnectTimeout=10 -o ServerAliveInterval=5`，**让 SSH 本身 10s 失败**而不是 30s 累积

### B6. SSH 隧道断连后 agentd 行为

- **影响**：SSH 断 → `subprocess.run` 返错 → `coordinate_client._run_cli` 返 `{"error": ...}` → agentd 刷 `coordinate CLI failed` log
- **当前行为**：agentd 进程**不**退出，**继续** poll（每 2s 一次）—— **不崩**但刷日志
- **阶段 A 接受**：刷日志，**不**做断连告警

### B7. 跨主机 SQLite 文件共享（plan 第 116 行禁止）

- **实际**：阶段 A 不会真让 Mac 读腾讯云 SQLite。`coordinator_db_path` **仍指本机**（`/Users/yinxin/projects/coordinate/data/coordinator.sqlite3`），**不**改成腾讯云路径
- **wrapper 内部显式带 `--db /var/lib/coordinate/coord.sqlite3`**：Mac agentd 通过 SSH 调远端 coord CLI 时，远端 coord 写到腾讯云 SQLite；**Mac 本机 SQLite 文件不被读 / 不被写**
- **`coordinator_db_path` 字段在阶段 A 语义 = "本机 fallback 路径"**（如果 Mac 本机临时跑 coord 时用）—— **不是** Mac agentd 远端调时的实际路径
- **字段名误解消除方式**：**阶段 A 不改名**（rename 算 7.2 阶段 B 范围）；**接受**字段名跟实际行为脱钩（Mac agentd 走 wrapper，wrapper 内部显式 `--db`）

### B8. KOOK bridge 缺失（阶段 A **不做**）

- **怎么解**：**阶段 A 范围外**，**7.2 阶段 B / C 也不做**（plan 第 124 行 KOOK 是 7.1.1 阶段 closeout deferred 项）。**腾讯云阶段 A 部署时，Mac KOOK 桥继续由 kook-nexus 独立项目承载**（7.1 plan 没迁移 KOOK 进 multinexus，**这本身就是遗留**）

## Explicit 不做（7.2 plan + 当前 preflight 范围限制）

| 不做 | 引用 |
|---|---|
| HTTP API（`COORDINATE_URL` 协议） | 7.2 plan 第 49 行 — 阶段 B 范围 |
| 多 coord 副本同步 | 7.2 plan 第 115 行 |
| SQLite 跨主机文件共享 | 7.2 plan 第 116 行 |
| PostgreSQL | 7.2 plan 第 117 行 |
| 完整 HA | 7.2 plan 第 118 行 |
| KOOK bridge 启用 | 7.1.1 plan deferred 项，7.2 阶段 A 不做 |
| 改 `multinexus/agentd/coordinate_client.py` 业务代码 | preflight 限制 |
| 改 `multinexus/agentd/worker.py` | preflight 限制 |
| 改 `multinexus/client.py` | preflight 限制 |
| 改 `multinexus/adapters/*` | preflight 限制 |
| 改 `multinexus/bridge.py` 路径解析 | preflight 限制（`c91d45b` 已预埋） |
| 改 `coord/cli.py` / `coord/runtime.py` / `coord/daemon.py` | preflight 限制 |
| 改 `coord/db.py` schema | preflight 限制 |
| 改 `agents.toml` | preflight 限制（**只**写 plan，不动 agents.toml） |
| 改任何 plist | preflight 限制 |
| 启动 / 停止任何 launchd 服务 | preflight 限制 |
| 开 GitHub PR | preflight 不开 PR |
| 实际跑腾讯云部署 | preflight 不部署 |
| 改 SSH config | preflight 不动 ssh config |
| 改 `~/.zshenv` / `~/.zprofile` | preflight 不动 shell env |

## Pre-flight 自己验证清单（plan 写完不跑）

写完这份 plan 后**只**做以下**只读**验证：
- [ ] `cat agents.toml` 看 `coordinator_cli_path` / `coordinator_db_path` 字段**没**在 plan 里被改（preflight 边界）
- [ ] `git status` 看工作树**没**改动
- [ ] 6 进程 N+M 拓扑**仍**在跑（plan 写完没启动 / 停止任何服务）
- [ ] 远端 origin **没**新 commit（preflight 不 push）

## 给 7.2 阶段 A 实施 task 的入站 context

如果这份 plan 通过，**下一个 task 应当是 `phase-7.2-stage-a-tencent-deploy`**，其 `worker-bootstrap.md` 应当含：
1. 阶段 A 范围 = plan 第 1-5 段（部署 coord 到腾讯云 + Mac wrapper script + smoke test）
2. 阶段 A 不做 = plan "Explicit 不做" 整段
3. 实施顺序 = 1) Mac wrapper script, 2) 腾讯云 coord systemd unit, 3) agents.toml 改, 4) 12 步 smoke test
4. blocker 解除 = plan "Blockers" 整段
5. 验证 = plan "Smoke test 怎么跑" 12 步全过
6. 风险 = plan "Smoke test 失败时怎么回滚" 段

**实施人建议**：`mac-codex`（7.1.1-coord-dotenv 实施 owner，continuity；或**也**可以 `mac-claude` / 任何有 SSH 远端经验的 agent）。

**branch 建议**：`agents/mac-codex/phase-7.2-stage-a-tencent-deploy`（从 7.1.1-coord-dotenv 拉新 branch）。
