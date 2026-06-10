# Worker Bootstrap: phase-7.2-tencent-cloud-impl

## 任务性质

**部署任务**（不是 coding 任务）。**不**走 coord CLI（coord 还没装上腾讯云！这是要装的！）。**不**发 Discord updates（这是**部署**，**不**用 coord runtime 协调）。**不**用 `[agent-report]` 块（**这阶段不通过 coord runtime 协调**）。

实施 agent 的工作：执行 `plan.md` 的 6 步骤（步骤 0-5） + 步骤 6 closeout。

## 任务 ID

`phase-7.2-tencent-cloud-impl`

## Session Startup

### Step 1: 确认工作目录

```bash
pwd
```

期望: `/Users/yinxin/projects/multinexus`。

### Step 2: 检查 workspace state

```bash
git status --short
git branch --show-current
git log --oneline -5
```

期望:
- branch = `agents/mac-claude/phase-7.2-multi-host-agent-runtime`
- 最近 commit = `40da1db docs: add 7.2 tencent cloud preflight plan` 或更新

**Rule**: **不**覆盖/还原**不**属于本任务的文件。如果发现不相关 dirty 文件 (`M agents.toml` from 之前 worktree)，**记下**但**不**清理。

**Shared-worktree guard**: 当前 worktree 是 phase-7.2 tencent cloud preflight 专用。如果 `pwd` 不对或 branch 不对 → **停止**报 blocker，**不**切 branch。

**不**跑 `git reset` / `git rebase` / `git checkout` / `git switch` / `git cherry-pick` / `git push --force` 除非 operator 明确要求。

### Step 3: 读本任务 plan + preflight

```bash
cat docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/plan.md
cat docs/project-harness/tasks/phase-7.2-tencent-cloud-preflight/plan.md
cat docs/project-harness/tasks/phase-7.2-multi-host-agent-runtime/plan.md
```

**`plan.md` 是实施清单**（6 步骤 + 14 步 smoke [8 步 CLI S1-S8 + 6 步 Discord D1-D6] + 5 步回滚）。**`preflight/plan.md` 是上游调研**。**`phase-7.2-multi-host-agent-runtime/plan.md` 是源真值**（phase-7.2 总目标 + 拓扑）。

### Step 4: 读 SSH / 防火墙 / 腾讯云状态

**实施前**（**不**是本 bootstrap 步骤，是 plan 步骤 0 之前）：

```bash
# Mac 出口 IP:
curl -s https://api.ipify.org; echo

# SSH key 存在:
ls -la ~/.ssh/id_ed25519_coord 2>&1

# 腾讯云 VM 可达 (用 kook-hermes-admin = KHC):
ssh -o ConnectTimeout=5 -o BatchMode=yes ubuntu@kook-hermes-admin "echo ok && id" 2>&1
# 期望: ok\nubuntu\nuid=1000(ubuntu) gid=1001(ubuntu) groups=...,27(sudo),...

# launchd plist label 反查 (实施前确认哪些 plist 跑):
launchctl print gui/$(id -u)/com.coordinate.runtime 2>&1 | grep -E "^\s*path = " | head -1
launchctl print gui/$(id -u)/com.multinexus.discord.bridge 2>&1 | grep -E "^\s*path = " | head -1
launchctl print gui/$(id -u)/com.multinexus.mac-claude.agentd 2>&1 | grep -E "^\s*path = " | head -1
# 期望: 三个都是 /Users/yinxin/projects/multinexus/launchd/*.plist
# (如果 label 跟 plan 不一致, 报 blocker)
```

**任何一项不通过** → **停止**报 blocker（**不**开始实施）。

## 你的 Assignment

- **Task**: phase-7.2-tencent-cloud-impl
- **Title**: Phase 7.2 腾讯云单机部署
- **Branch**: agents/mac-claude/phase-7.2-multi-host-agent-runtime（**只** plan 文档在此 branch）
- **Plan**: docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/plan.md
- **Phase**: approved
- **Source-of-truth upstream**: docs/project-harness/tasks/phase-7.2-multi-host-agent-runtime/plan.md
- **Preflight**: docs/project-harness/tasks/phase-7.2-tencent-cloud-preflight/plan.md

## 工具

| 工具 | 用途 |
|---|---|
| `ssh ubuntu@kook-hermes-admin` (Mac → 腾讯云 admin) | 装 coord / multinexus / systemd / secret 落档 / sqlite 查询 / log 查询 |
| `rsync ... ubuntu@kook-hermes-admin:/tmp/<x>-staging/` | 同步 code (一次性, 用 ubuntu 临时目录, 再 sudo install 到 /opt) |
| `scp ... ubuntu@kook-hermes-admin:/tmp/<x>.staging` | 同步 secret (一次性) |
| `sudo -u coord` / `sudo -u multinexus` (腾讯云) | **仅一次性** install / venv 装（如 `sudo -u coord pip install ...`）；**不**用于 wrapper / runtime 路径 |
| `plutil -extract <key> raw <plist>` (Mac 本机) | 读 plist 的 Label / StandardOutPath / StandardErrorPath (**不写死** log 路径) |
| `sed -i` (Mac 本机) | 改 `agents.toml` 一行 |
| `launchctl` (Mac 本机) | 停 Mac coord/bridge plist (`com.coordinate.runtime` / `com.multinexus.discord.bridge`) |
| `systemctl` (腾讯云) | 启停 coordinate / multinexus-discord-bridge (走 sudo) |
| `sqlite3` (腾讯云) | 验证 coord DB 内容 (走 sudo) |
| `tail` / `grep` (Mac 本机) | 看 Mac agentd log (路径从 plutil 读) |
| `ps` (Mac + 腾讯云) | 验证进程拓扑 |

**`tmux` / `screen`**：可选；如果 SSH 长 session 易断，**用**。

**`sudo -u coord`** (腾讯云)：**仅一次性 install / venv 装**用（如 1.2 段 `sudo -u coord pip install -e /opt/coordinate[daemon]`）；coord / multinexus 是 system user 无 shell，**wrapper / runtime / systemd 路径不**通过 `sudo -u` 切 user —— runtime 走 `User=coord` / `User=multinexus` 字段 + group 共享（blocker 1 权限方案）。

## 不要做（实施边界 = preflight 边界）

### 不改业务代码

| 不改 | 引用 |
|---|---|
| `multinexus/agentd/coordinate_client.py` | preflight line 380 |
| `multinexus/agentd/worker.py` | preflight line 381 |
| `multinexus/client.py` | preflight line 382 |
| `coord/cli.py` / `coord/runtime.py` / `coord/daemon.py` / `coord/db.py` schema | preflight line 386-389 |

### 不改 plist 内容

| 不改 | 引用 |
|---|---|
| `multinexus/launchd/*.plist` 内容 | preflight line 390（**Mac plist 改动是停旧 plist**，**不**改 plist 文件） |
| `mac.sh` 内部 | preflight B1 段（**mac.sh 留作本机 fallback，阶段 A 不动**） |

### 不做协议升级

| 不做 | 引用 |
|---|---|
| HTTP API（`COORDINATE_URL` / `COORDINATE_TOKEN`） | preflight line 144-154，**阶段 B 范围** |
| 多 coord 副本 / 跨主机 SQLite 共享 / PostgreSQL / HA | preflight line 375-378 |
| KOOK bridge 部署 | preflight line 379 |

### 不做 git 动作（实施完）

| 不做 | 引用 |
|---|---|
| `git commit`（实施完**不**commit，等用户明确要求） | 用户指示 |
| `git push` | 用户指示 |
| `gh pr create` | 用户指示 |

## 实施协议

### 工作节奏

1. **每步独立** — 完成 1 步 → 验证 → 进下步
2. **每步 timeout** — 步骤 1 装 30 分钟、步骤 2 装 15 分钟、步骤 3 装 10 分钟、步骤 4 smoke 1 小时、步骤 5 回滚 15 分钟
3. **超时** → 停 → 报 blocker
4. **失败** → **不**自动回滚，**先报**用户决定走"回滚步骤 5"还是"修复 + 重试"

### 顺序

- 步骤 0 (备份) → 步骤 1 (装) → 步骤 2 (起 service) → 步骤 3 (wrapper + agents.toml) → 步骤 4 (smoke: 8 步 CLI + 6 步 Discord = 14 步) → 步骤 5 (可选回滚) → 步骤 6 (closeout)
- **步骤 1-3 可以**并行（不同机器/不同目录）
- **步骤 4 必须**串行：
  - **CLI smoke (S1-S8)** 必须**全过**才能进 **Discord smoke (D1-D6)**
  - **D 段是真发 Discord 消息**（**不**用 `runtime request submit` CLI 模拟）
- **步骤 5 只在**失败时跑

### 权限链路关键约束（**blocker 1 + 2**）

**远端权限方案**：用 group 共享代替 `sudo -u coord`。

- **`/var/lib/coordinate/`** 目录 owner `coord:coord`，`chmod 2770`（setgid + group rwx）
- **`multinexus` / `ubuntu` 加到 `coord` group**（`usermod -aG coord`）
- **systemd `coordinate.service` 加 `UMask=0007`** —— coord daemon 创建的 SQLite 文件 inherit group `coord`
- **systemd `multinexus-discord-bridge.service` `UMask=0007`** —— bridge daemon 创建的所有文件 inherit group
- **`/usr/local/bin/coord-local` 加 `umask 0007`** —— bridge 调 coord CLI 时新建文件 inherit group
- **Mac `coord-ssh` wrapper SSH 远端命令 = `/usr/local/bin/coord-local`**，**不**用 `sudo -u coord`（agentd 每 2s 调一次 claim，sudo 不可行）

**绝对不能做**：
- Mac wrapper 用 `ssh ... "sudo -u coord /opt/.../coordinate ..."`（blocker 2：sudo 失败率 100%）
- 远端 `/var/lib/coordinate` 用 `chmod 750`（multinexus 读不到 SQLite）
- 直接改 `chown multinexus /var/lib/coordinate/coord.sqlite3`（破坏 coord daemon 写入）

### token 检查约束（**blocker 5**）

**Mac 端 rsync / cp agents.toml 到远端前必须 2 项 grep 检查**：

1. `if grep -E "^\s*token\s*=" agents.toml; then` —— 显式 `token = "..."` 字段（**不**含 `token_env`）
2. `if grep -E "DISCORD_[A-Z_]+_TOKEN\s*=\s*['\"]?[A-Za-z0-9._-]{20,}" agents.toml; then` —— token 字段 value 是长字符串

**任一命中 → exit 1**，**不**拷到远端。

### 进度记录

- 实施过程**不**发 Discord（**这阶段不通过 coord runtime 协调**）
- **本地**记实施日志到 `~/.multinexus/phase-7.2-impl-session.log`（一次性）：
  ```bash
  exec > >(tee -a ~/.multinexus/phase-7.2-impl-session.log) 2>&1
  ```
- closeout 报告写到 `docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/closeout-<YYYY-MM-DD>.md`

### commit 边界

**只** 4 类文件可 commit（**实施完 commit 是用户责任**）：

1. `docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/plan.md` (实施计划)
2. `docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/worker-bootstrap.md` (本文件)
3. `docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/closeout-<YYYY-MM-DD>.md` (实施报告)
4. `agents.toml` (`coordinator_cli_path` 改一行)

**不** commit：
- `~/.local/bin/coord-ssh`（Mac 本机，**不**入库）
- `~/.ssh/id_ed25519_coord`（Mac 本机 SSH 私钥，**不**入库）
- `/etc/coordinate/coord.env` / `/etc/multinexus/discord.env`（腾讯云 secrets，**不**入库）
- `/etc/systemd/system/coordinate.service` / `multinexus-discord-bridge.service`（腾讯云 systemd，**不**入库 multinexus repo，**不**入库 coord repo）

## Session End Protocol

### 成功结束

1. 8 步 CLI smoke (S1-S8) + 6 步 Discord smoke (D1-D6) 全过（V1-V9 验收全过）
2. **不** commit / **不** push（等用户）
3. 写 closeout 报告到 `docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/closeout-<YYYY-MM-DD>.md`
4. 报告：什么改了 + smoke 结果 + V1-V9 验收结果 + 剩余风险 + 文件清单

### 失败结束

1. **跑步骤 5 回滚**（让 Mac 回到 6 进程 N+M 拓扑）
2. 验证 R4（ps 显示 6 进程）
3. **不** commit / **不** push
4. 写 closeout 报告标注"FAILED + ROLLED BACK"

### 阻塞结束

1. **不**跑步骤 5 回滚（保留现场）
2. **不** commit / **不** push
3. 写 closeout 报告标注"BLOCKED, awaiting <decision>"

## 约束

- **Human gate**：**不** commit / **不** push / **不**开 PR 除非 operator 明确批准
- **No deploy without approval**：腾讯云 service 一旦 `systemctl start`，**算**部署，**不**回滚除非步骤 5 走起
- **No out-of-scope changes without asking**：发现本任务没列的硬件/配置问题，**不**修，**报** blocker
- **If stuck 3+ attempts on the same issue**：停 + 报 blocker
- **不**碰 Mac 业务代码（preflight 边界）
- **不**碰 `mac.sh` 内部
- **不**碰 plist 内容
- **不**改 `coordinator_db_path` 字段（preflight 改 4）
- **不** push（用户指示）
- **不** 开 PR（用户指示）
