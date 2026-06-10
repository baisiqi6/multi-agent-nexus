# Phase 7.2 腾讯云单机部署 — 实施清单

## 任务 ID

`phase-7.2-tencent-cloud-impl`

## 上游文档（preflight = 调研；本文件 = 实施）

- **本任务源真值**：`docs/project-harness/tasks/phase-7.2-multi-host-agent-runtime/plan.md`（phase-7.2 总目标 + 拓扑）
- **本任务前置调研**：`docs/project-harness/tasks/phase-7.2-tencent-cloud-preflight/plan.md`（preflight，已 commit `40da1db`）
- **本文件**：可执行 step-by-step 清单

## 目标（来自 preflight）

A0 形态（preflight line 164-178）：
```
Tencent Cloud VM:
  coord serve
  Discord bridge (multinexus.py --platform discord)

Mac:
  4 个 Mac agentd
```

**Mac 不再跑 coord / bridge**。**Mac agentd 通过 SSH 加密 tunnel 调腾讯云 coord**。

## 本计划 SSH / 用户 / 路径 约定（**实施前必读**）

### SSH host 约定

| 简写 | 实际 host | User | 用途 | 实施前确认 |
|---|---|---|---|---|
| `KHC` | `kook-hermes-admin` (124.221.111.209) | `ubuntu` (uid=1000, sudo group 27) | **admin 入口**：rsync / scp / sudo 装 systemd / 改 env | `ssh -o BatchMode=yes kook-hermes-admin "echo ok && id"` 应返回 `uid=1000(ubuntu) gid=1001(ubuntu) groups=...,27(sudo),...` |
| `KH` | `kook-hermes` (124.221.111.209) | `hermes` (uid=普通 user) | 普通 user 入口（**不**用于本任务） | （**不**用于本任务） |
| `TENCENT` | `tencent-cloud` | **本机 `~/.ssh/config` 暂**没**这个 alias** | （可选 alias） | 实施前**要么**确认 alias 存在**要么**用 `KHC` 替代 |

**plan 全文用 `KHC` 引用腾讯云 admin 入口**（`ubuntu@kook-hermes-admin`）。**不**用 `root@tencent-cloud` / `coord@tencent-cloud` / `multinexus@tencent-cloud`——这些 host 暂不存在。

**实施前**：如果想用更短的 `TENCENT` 别名，**先**在 `~/.ssh/config` 加：

```sshconfig
Host tencent-cloud
    HostName 124.221.111.209
    User ubuntu
    IdentityAgent /var/run/com.apple.launchd.Ji3qVSPxld/Listeners
```

**然后**把 plan 里 `kook-hermes-admin` 全替换为 `tencent-cloud`。**默认**用 `KHC` 跑，**不**要求先加 alias。

### 用户约定

| User | Shell | 能否 SSH | 用途 |
|---|---|---|---|
| `ubuntu` (uid=1000) | `/bin/bash` | ✓ | admin 入口：装 systemd / 改 /opt/ 改 /etc/ |
| `coord` (system user) | `/usr/sbin/nologin` | ✗（**不能**直接 SSH） | coord.service 跑时身份 |
| `multinexus` (system user) | `/usr/sbin/nologin` | ✗ | multinexus-discord-bridge.service 跑时身份 |
| `root` | `/bin/bash` | （**不**用 root，**不**开 `PermitRootLogin yes`） | 禁用 root SSH |

**关键约束**：
- `coord` / `multinexus` 是 **system user with nologin**（preflight B3 接受**不**暴露 SSH）
- **不**能用 `rsync coord@host:/...` —— nologin user 没法 SSH 认证
- **所有**远端写操作通过 `ubuntu@kook-hermes-admin` + `sudo` 实施
- 远端 systemd unit 用 `User=coord` / `User=multinexus` 切换，**不**走 SSH

### 路径约定

| 路径 | 用途 |
|---|---|
| `/opt/coordinate/` (远端) | coord repo（**不**含 `.venv`，venv 远端独立装） |
| `/opt/multinexus/` (远端) | multinexus repo（**不**含 `.venv`） |
| `/var/lib/coordinate/coord.sqlite3` (远端) | coord SQLite DB |
| `/etc/coordinate/coord.env` (远端) | coord secrets (chmod 640, root:coord) |
| `/etc/multinexus/discord.env` (远端) | bridge secrets (chmod 640, root:multinexus) |
| `/etc/systemd/system/coordinate.service` (远端) | coord systemd unit |
| `/etc/systemd/system/multinexus-discord-bridge.service` (远端) | bridge systemd unit |
| `~/.local/bin/coord-ssh` (Mac) | SSH wrapper，**不进**仓库 |
| `~/.ssh/id_ed25519_coord` (Mac) | Mac → 远端 SSH 私钥，**不进**仓库 |
| `/Users/yinxin/projects/multinexus/launchd/*.plist` (Mac) | launchd 实际跑的 plist（**不**在 `~/Library/LaunchAgents/`，launchd 用绝对路径 bootstrap） |
| `/Users/yinxin/projects/multinexus/logs/mac-<agent>.agentd.{log,err.log}` (Mac) | agentd log 真实路径（**不**是 `~/Library/Logs/`） |

### Log 路径读取约定（**重要**）

agentd / bridge / coord 的 log 路径**应当**从 launchd plist 读取，**不**写死。

```bash
# 读 plist StandardOutPath (agentd 例子)
LOG_OUT=$(plutil -extract StandardOutPath raw ~/...plist  # 实际路径见下
           /Users/yinxin/projects/multinexus/launchd/com.multinexus.mac-claude.agentd.plist)
LOG_ERR=$(plutil -extract StandardErrorPath raw \
           /Users/yinxin/projects/multinexus/launchd/com.multinexus.mac-claude.agentd.plist)
```

**实际 plist 路径**（**本计划默认**）：
- agentd: `/Users/yinxin/projects/multinexus/launchd/com.multinexus.mac-<agent>.agentd.plist`
- bridge: `/Users/yinxin/projects/multinexus/launchd/com.multinexus.discord.bridge.plist`
- coord: `/Users/yinxin/projects/multinexus/launchd/com.coordinate.runtime.plist`

**实施前**先 `plutil -extract StandardOutPath raw <plist>` 验证路径，**不**假设。

## 验收（必须全过才能 closeout）

| # | 验收 | 验证命令 |
|---|---|---|
| V1 | 腾讯云 `systemctl is-active coordinate multinexus-discord-bridge` 都 `active` | `ssh ubuntu@kook-hermes-admin "systemctl is-active coordinate multinexus-discord-bridge"` |
| V2 | 远端 secret 文件存在 + 权限 **640** + owner root:coord / root:multinexus + 长度非零 | `ssh ubuntu@kook-hermes-admin "stat -c '%a %U %G %s %n' /etc/coordinate/coord.env /etc/multinexus/discord.env"` |
| V3 | Mac `coord-ssh wrapper` 存在 + 可执行 | `ls -la ~/.local/bin/coord-ssh` |
| V4 | `agents.toml` 改 `coordinator_cli_path = /Users/yinxin/.local/bin/coord-ssh`，**`coordinator_db_path` 保留本机值** | `grep coordinator_cli_path /Users/yinxin/projects/multinexus/agents.toml` |
| V5 | 14 步 smoke test 全过（CLI smoke S1-S8 + Discord smoke D1-D6） | 见下"步骤 4：Smoke test" |
| V6 | 失败 → 回滚后 Mac 仍是 6 进程 N+M 拓扑跑通 | 见下"步骤 5：回滚" |
| V7 | **拆成两步验**: 远端 2 systemd service active + 本机 4 agentd PID alive（**不**用一个本机 ps 声称覆盖两台机器） | 远端: `ssh ubuntu@kook-hermes-admin "systemctl is-active coordinate multinexus-discord-bridge"` + 本机: `launchctl list | grep -E "com\.multinexus\.mac-.*\.agentd"` |
| V8 | **repo 里只允许 3 类文件变化**: `agents.toml` (一行 `coordinator_cli_path`) + `docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/plan.md` + `closeout-*.md`（**没**碰业务代码）；wrapper `~/.local/bin/coord-ssh` 在 Mac 本机，**不**在 repo，**不**用 `git status` 验 | 远端: `git status` 只看 3 类文件;  本机 wrapper: `ls -la ~/.local/bin/coord-ssh` |
| V9 | **没**碰 `mac.sh` / `com.coordinate.runtime.plist` / `com.multinexus.discord.bridge.plist`（阶段 A preflight 边界） | `git diff --name-only` 应当不含上述 3 文件 |

## 不做（preflight 边界 = 实施边界）

| 不做 | 引用 |
|---|---|
| 改 `multinexus/agentd/coordinate_client.py` | preflight line 380 |
| 改 `multinexus/agentd/worker.py` | preflight line 381 |
| 改 `multinexus/client.py` | preflight line 382 |
| 改 `coord/cli.py` / `coord/runtime.py` / `coord/daemon.py` / `coord/db.py` schema | preflight line 386-389 |
| 改任何 `multinexus/launchd/*.plist` | preflight line 390（**Mac plist 改动是停掉旧 plist，不是改 plist 内容**） |
| 改 `mac.sh` 内部 | preflight B1 段（**改迁后 mac.sh 留作本机 fallback，阶段 A 不动**） |
| 启停 launchd 服务**之前**没备份 | **实施第一步必须先 backup，见步骤 0** |
| HTTP API（`COORDINATE_URL` / `COORDINATE_TOKEN`） | preflight line 144-154，**阶段 B 范围** |
| 多 coord 副本 / 跨主机 SQLite 共享 / PostgreSQL / HA | preflight line 375-378 |
| KOOK bridge 部署 | preflight line 379（**7.2 阶段 A 不做**） |
| `git push`（实施完**不**push，等用户明确要求） | 用户指示 |
| PR（实施完**不**开 PR，**不**进 main） | 用户指示 |

## 步骤 0：备份 + 准备（**做任何改动前必做**）

```bash
# 0.1 备份当前 Mac 单机状态（plist + 进程清单）
mkdir -p ~/.multinexus/phase-7.2-impl-backup-$(date +%Y%m%d)
launchctl list | grep -E "coordinate|multinexus" > ~/.multinexus/phase-7.2-impl-backup-$(date +%Y%m%d)/launchctl-list.txt
ls /Users/yinxin/Library/LaunchAgents/ | grep -E "coordinate|multinexus" > ~/.multinexus/phase-7.2-impl-backup-$(date +%Y%m%d)/launchagents.txt
cp /Users/yinxin/projects/multinexus/agents.toml ~/.multinexus/phase-7.2-impl-backup-$(date +%Y%m%d)/agents.toml.bak

# 0.2 验证 Mac 当前进程拓扑
ps aux | grep -E "coordinate|multinexus|agentd" | grep -v grep
# 应当看到 6 进程：1 coord serve + 1 discord-bridge + 4 agentd

# 0.3 验证当前 agents.toml 状态
grep -E "coordinator_cli_path|coordinator_db_path" /Users/yinxin/projects/multinexus/agents.toml
# 应当看到指向本机 /Users/yinxin/.../mac.sh 和 /Users/yinxin/projects/coordinate/data/coordinator.sqlite3
```

**为什么先备份**：回滚步骤 5 要用 `agents.toml.bak` + `launchctl list` 清单。

### 步骤 0.4 部署前 git status gate (P2.2 + Codex review)

**rsync 之前**先验 working tree 干净 — 只允许**预期**修改项, 其他 untracked / modified 全部停止:

```bash
# 实施前 git status 应当**只**有:
#   M agents.toml
#   M docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/plan.md
#   M docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/worker-bootstrap.md
# **不**应有其他 untracked / modified

PORCELAIN=$(git status --porcelain)
ALLOWED_PATTERNS=(
    '^ M agents\.toml$'
    '^ M docs/project-harness/tasks/phase-7\.2-tencent-cloud-impl/plan\.md$'
    '^ M docs/project-harness/tasks/phase-7\.2-tencent-cloud-impl/worker-bootstrap\.md$'
)
ALLOWED_OK=true
while IFS= read -r line; do
    [ -z "$line" ] && continue
    matched=false
    for pat in "${ALLOWED_PATTERNS[@]}"; do
        if [[ "$line" =~ $pat ]]; then
            matched=true
            break
        fi
    done
    if ! $matched; then
        echo "ABORT: 部署前 git status 含未预期项:" >&2
        echo "  $line" >&2
        ALLOWED_OK=false
    fi
done <<< "$PORCELAIN"

if ! $ALLOWED_OK; then
    echo "" >&2
    echo "参考: 当前 worktree 还有这些非预期项, 处理 (commit / stash / 删) 后再部署." >&2
    git status --short >&2
    exit 1
fi
echo "Git status gate: 全部为预期修改项, 继续."
```

**为什么必要**: rsync 走本地 worktree 复制, 本机 dirty/untracked 文件 (如 phase-5.5 旧任务目录 / :memory: 临时 sqlite) 会被拷到远端. 显式 exclude 是双保险, 但**更可靠**是部署前 working tree 干净.

**特例豁免**:
- `M agents.toml` 是**预期**的 (`coordinator_cli_path` 一行修改)
- `M docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/plan.md` 是**预期**的 (closeout 时**可能**会改)
- 实施过程中 closeout 报告会生成新文件 `closeout-*.md`, **这**个**不**在 ALLOWED 列表 — 因为 closeout 报告在**实施后**写, 跟 rsync 时序**不**冲突

## 步骤 1：腾讯云装 coordinate + multinexus

### 1.1 准备腾讯云 VM

**先**装基础依赖（**P1.3 finding** —— fresh Ubuntu 缺这些会直接 fail）：

```bash
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    sqlite3 \
    rsync
# 验证 (每条应当非空)
python3 --version
python3 -m venv --help >/dev/null && echo "venv OK"
which sqlite3 && sqlite3 --version
which rsync && rsync --version | head -1
EOF
# 期望: Python 3.10.x / 3.11.x / 3.12.x  (coord requires-python >=3.10)
#       venv OK
#       sqlite3 3.x
#       rsync 3.x
```

| 项 | 要求 |
|---|---|
| OS | Ubuntu 22.04 LTS (or 24.04) |
| 防火墙 | 安全组放行 **22/TCP inbound from Mac 出口 IP**（**B3 风险**：Mac ISP 动态 IP，preflight 接受 fail2ban 风险） |
| User | `coord` (system user, no shell) + `multinexus` (system user, no shell) |
| Python | system python3 (apt) — **不**用 pyenv（preflight H4 改迁方案：systemd unit 引用 system python） |
| 路径 | `/opt/coordinate/`, `/opt/multinexus/`, `/var/lib/coordinate/`, `/etc/coordinate/`, `/etc/multinexus/` |

### 1.2 装 coord repo 到 `/opt/coordinate`

```bash
# Mac 端: rsync 到 ubuntu 临时目录 (用 KHC 简称 = kook-hermes-admin)
# **P2.2**: 排除 git 内部, 临时 sqlite 文件, current/ worktree artifacts,
# 还有 .venv/__pycache__/.pyc/.env 等. 防止本机 dirty/untracked 文件污染远端.
rsync -avz --delete /Users/yinxin/projects/coordinate/ \
    ubuntu@kook-hermes-admin:/tmp/coordinate-staging/ \
    --exclude='.git/' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='data/*.sqlite3' \
    --exclude='data/*.sqlite3-shm' \
    --exclude='data/*.sqlite3-wal' \
    --exclude=':memory:' \
    --exclude=':memory:-shm' \
    --exclude=':memory:-wal' \
    --exclude='docs/project-harness/current/' \
    --exclude='.env'

# 腾讯云端 (KHC ssh + sudo): 创建 system user + 拷到 /opt
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
# **幂等**: user 存在时跳过 (id -u 返 0 = exists, || 后面才跑 adduser)
id -u coord >/dev/null 2>&1 || sudo adduser --system --no-create-home --shell /usr/sbin/nologin coord
id -u multinexus >/dev/null 2>&1 || sudo adduser --system --no-create-home --shell /usr/sbin/nologin multinexus

sudo mkdir -p /opt/coordinate /var/lib/coordinate /etc/coordinate

# **关键 (blocker 1 权限方案)**: 用 group read/write 代替 sudo 链
# 原因: Discord bridge 进程以 User=multinexus 跑, 它调 coord-local 时
# 不能 sudo -u coord (multinexus 是 nologin, 也没 sudo 权限).
# 方案: 把 multinexus / ubuntu 加到 coord group, chmod 2770 + UMask 0007
sudo usermod -aG coord multinexus
sudo usermod -aG coord ubuntu
sudo chown -R coord:coord /opt/coordinate
sudo chown -R coord:coord /var/lib/coordinate
sudo chmod 2770 /var/lib/coordinate
# 2770 = setgid bit + rwx for owner (coord) + rwx for group (coord 含 multinexus / ubuntu)
# setgid: 新建文件自动 inherit coord group

# 拷到 /opt (preserve attrs)
sudo cp -a /tmp/coordinate-staging/. /opt/coordinate/
sudo chown -R coord:coord /opt/coordinate
sudo rm -rf /tmp/coordinate-staging

# Python 检测 (coord requires-python >=3.10, 不要硬假设 3.12)
PYTHON_BIN=$(sudo -u coord bash -c 'command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3')
if [ -z "$PYTHON_BIN" ]; then
    echo "No python3.10+ found, installing..."
    sudo apt-get update
    sudo apt-get install -y python3.10 python3.10-venv python3-pip
    PYTHON_BIN=/usr/bin/python3.10
fi
$PYTHON_BIN --version
# 期望: Python 3.10.x 或 3.11.x 或 3.12.x

# 装 venv (用 sudo -u coord, 因 systemd unit User=coord 跑时要 umask 0007 兼容)
sudo -u coord $PYTHON_BIN -m venv /opt/coordinate/.venv
sudo -u coord /opt/coordinate/.venv/bin/pip install --upgrade pip

# coord 装 [daemon] extra (含 discord.py >=2.3, bridge 进程需要)
# 注意 [daemon] 用 quote 避免 shell glob 解释
sudo -u coord /opt/coordinate/.venv/bin/pip install -e '/opt/coordinate[daemon]'
EOF
```

### 1.3 装 multinexus repo 到 `/opt/multinexus`

```bash
# Mac 端: rsync (排除 launchd / logs / 仓库本机配置)
# **P2.2**: 排除 git 内部, 临时 sqlite 文件, current/ worktree artifacts.
# **额外 (Codex review)**: 显式排除 phase-5.5-discord-message-rendering 旧 untracked 任务目录
rsync -avz --delete /Users/yinxin/projects/multinexus/ \
    ubuntu@kook-hermes-admin:/tmp/multinexus-staging/ \
    --exclude='.git/' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='data/*.sqlite3' \
    --exclude='data/*.sqlite3-shm' \
    --exclude='data/*.sqlite3-wal' \
    --exclude=':memory:' \
    --exclude=':memory:-shm' \
    --exclude=':memory:-wal' \
    --exclude='docs/project-harness/current/' \
    --exclude='docs/project-harness/tasks/phase-5.5-discord-message-rendering/' \
    --exclude='.env' \
    --exclude='.multinexus' \
    --exclude='logs' \
    --exclude='launchd' \
    --exclude='agents.toml'  # **关键**: 不要直接 rsync Mac 端 agents.toml (见 1.3.1 sanitized copy)

# 腾讯云端:
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
sudo mkdir -p /opt/multinexus
sudo cp -a /tmp/multinexus-staging/. /opt/multinexus/
sudo chown -R multinexus:multinexus /opt/multinexus
sudo rm -rf /tmp/multinexus-staging

# Python 检测 (multinexus 同样要 >=3.10, 跟 coord 共用即可)
PYTHON_BIN=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3)
$PYTHON_BIN --version

# 装 venv
sudo -u multinexus $PYTHON_BIN -m venv /opt/multinexus/.venv
sudo -u multinexus /opt/multinexus/.venv/bin/pip install --upgrade pip

# **关键**: multinexus **没有** pyproject.toml / setup.py, 用 requirements.txt
sudo -u multinexus /opt/multinexus/.venv/bin/pip install -r /opt/multinexus/requirements.txt
EOF

**注意**：multinexus repo (`/opt/multinexus/`) **不**需要 coord group 读 —— 桥进程以 `User=multinexus` 跑，**只** multinexus 自己读写。**唯一**跨 user 共享的文件是 SQLite DB（`/var/lib/coordinate/coord.sqlite3`），由 1.2 段 group 方案处理。
```

### 1.3.1 写 sanitized `agents.toml` 到腾讯云（**blocker 6**）

**不**直接 rsync Mac 端 `agents.toml`（**潜在 secret 风险** —— Mac 端当前实际是 `token_env` 字段，**不**含真实 token，但**防御性**约束必须）。

**两步走**：

**Step 1: Mac 端生成 sanitized copy**（**不**含真实 token）

```bash
# Step 1a: 检查 Mac 端 agents.toml 是否含真实 token (defensive check, 应当 0 命中)
# **用 if grep ... then 形式** (无命中时 grep 返 1, 避免 set -e 误中断)
# **POSIX 写法** ([[:space:]] 不用 \s) — macOS/BSD grep 不识别 \s (P1.4)
# 检查 1: 显式 token 字段 (token = "...")
if grep -E "^[[:space:]]*token[[:space:]]*=" /Users/yinxin/projects/multinexus/agents.toml; then
    echo "ABORT: Mac 端 agents.toml 含显式 token = 字段 (应只含 token_env 字段名)" >&2
    exit 1
fi
# 检查 2: DISCORD_*_TOKEN=<长字符串> 模式 (防御: 即便字段名是别的, value 是 token)
if grep -E "DISCORD_[A-Z_]+_TOKEN[[:space:]]*=[[:space:]]*['\"]?[A-Za-z0-9._-]{20,}" \
    /Users/yinxin/projects/multinexus/agents.toml; then
    echo "ABORT: Mac 端 agents.toml 含疑似真实 token (应只含 token_env 字段名)" >&2
    exit 1
fi
# 期望: 上面两个 if 块都不进入 then 分支 (无真实 token)

# Step 1b: 直接 cp (保留注释/格式, 不依赖 tomli_w)
cp /Users/yinxin/projects/multinexus/agents.toml /tmp/agents.toml.sanitized

# 验证: diff 应当 0 差异 (因为 Mac 端本来就没真实 token, cp 是 identity)
diff /Users/yinxin/projects/multinexus/agents.toml /tmp/agents.toml.sanitized
# 期望: 无输出
```

**为什么不用 tomli_w 改写 TOML**：
- `tomli_w` 不一定装（系统 python 没装，venv 也没装）
- tomli_w 改写会**丢注释** / **重排 section 顺序** / 可能改 key 格式（虽然 spec 允许但 git diff 会变）
- 既然 Mac 端实际**没**真实 token（已 step 1a 验证），`cp` 已经是 sanitized copy
- 远端再 `sed` 改**仅一行** `coordinator_cli_path` 即可

**Step 2: 拷到腾讯云 + 改 `coordinator_cli_path` 指 `/usr/local/bin/coord-local`**

```bash
# scp sanitized copy
scp /tmp/agents.toml.sanitized ubuntu@kook-hermes-admin:/tmp/agents.toml.staging
rm -f /tmp/agents.toml.sanitized  # Mac 端不留

# 远端: install + 改 coordinator_cli_path 指本地 wrapper
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
sudo install -m 0644 -o multinexus -g multinexus /tmp/agents.toml.staging /opt/multinexus/agents.toml
sudo rm -f /tmp/agents.toml.staging

# 改 coordinator_cli_path 指 /usr/local/bin/coord-local (blocker 1)
# (mac.sh 路径是 Mac 本机 wrapper, 远端没这个文件)
sudo sed -i 's|coordinator_cli_path = ".*"|coordinator_cli_path = "/usr/local/bin/coord-local"|' /opt/multinexus/agents.toml
# 验证 (远端应当指向 /usr/local/bin/coord-local, 不是 mac.sh)
sudo grep coordinator_cli_path /opt/multinexus/agents.toml
EOF
# 期望: coordinator_cli_path = "/usr/local/bin/coord-local"
```

### 1.3.2 写 `/usr/local/bin/coord-local` 远端 coord CLI wrapper（**blocker 1 + 2**）

**为什么需要**：远端 Discord bridge 进程调 `CoordinateRuntimeClient` 时走 `subprocess.run(coordinator_cli_path)`；如果 path 是 Mac 的 `mac.sh`，bridge 启动**直接 fail**。

```bash
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
sudo tee /usr/local/bin/coord-local >/dev/null <<'WRAPPER'
#!/usr/bin/env bash
# Tencent Cloud bridge → 本机 coord CLI wrapper
# 显式带 --db 远端路径 (bridge 跑在同一台 VM, coord CLI 也在本机)
# **不**走 sudo -u coord (blocker 2: agentd 每 2s 调一次, sudo 不可行)
# **走** group coord 方案 (blocker 1: multinexus 已是 coord group member)
umask 0007  # 新建文件 inherit group = coord (配 chmod 2770 + setgid)
exec /opt/coordinate/.venv/bin/coordinate --db /var/lib/coordinate/coord.sqlite3 "$@"
WRAPPER
sudo chmod 0755 /usr/local/bin/coord-local
sudo chown root:root /usr/local/bin/coord-local

# 验证
ls -la /usr/local/bin/coord-local
# 期望: -rwxr-xr-x 1 root root ... /usr/local/bin/coord-local
/usr/local/bin/coord-local --help | head -3
# 期望: 看到 coord CLI help (说明 binary 跑得动)
EOF
```

**远端 wrapper 跟 Mac wrapper 区别**：
- Mac `~/.local/bin/coord-ssh`: `remote_cmd=$(printf '%q ' /usr/local/bin/coord-local "$@"); ssh ubuntu@kook-hermes-admin "$remote_cmd"`（**走 SSH**，**不** `sudo -u`；shell-quoting 用 printf %q 避免 $@ 远端展开为空）
- 远端 `/usr/local/bin/coord-local`: `umask 0007; exec /opt/coordinate/.venv/bin/coordinate --db ... "$@"`（**本地直调**，group coord 方案）
- **两个** wrapper **都不**用 `sudo -u coord`（**blocker 2** —— agentd 每 2s 调 claim，sudo 需要 TTY / 时间戳会刷爆）
- **两个** wrapper 各自指**对应当地主机的 `--db` 远端路径**
- **不**混淆

### 1.4 装 secrets 到 `/etc/coordinate/coord.env` + `/etc/multinexus/discord.env`（**统一 640**）

**不** `cat` 内容。**统一 chmod 640 + root:coord / root:multinexus owner**（systemd 进程以 coord / multinexus 身份跑，靠 group read 读 env file，**不**用 600 + 走 root）。

```bash
# Mac 端: 准备临时 env 文件 (chmod 600, 只 Mac 端)
umask 077
cat > /tmp/coord.env <<'EOF'
COORDINATOR_BOT_TOKEN=<paste from Mac ~/.coordinator/daemon.env>
COORDINATOR_CHANNEL_ID=<paste>
COORDINATOR_ALLOWED_USER_IDS=<paste>
EOF
chmod 600 /tmp/coord.env

cat > /tmp/discord.env <<'EOF'
DISCORD_MAC_CLAUDE_TOKEN=<paste from multinexus/.env>
DISCORD_MAC_CODEX_TOKEN=<paste>
DISCORD_MAC_OMP_TOKEN=<paste>
DISCORD_MAC_OPENCODE_TOKEN=<paste>
DISCORD_WIN_CLAUDE_TOKEN=<paste>
DISCORD_WIN_OPENCODE_TOKEN=<paste>
DISCORD_WIN_OPENCLAW_TOKEN=<paste>
EOF
chmod 600 /tmp/discord.env

# scp 到 ubuntu 临时目录 (一次性, 不留 Mac /tmp 副本)
scp /tmp/coord.env ubuntu@kook-hermes-admin:/tmp/coord.env.staging
scp /tmp/discord.env ubuntu@kook-hermes-admin:/tmp/discord.env.staging
rm -f /tmp/coord.env /tmp/discord.env  # Mac 端不留

# 腾讯云端: sudo cp + chown + chmod 640 (root:coord / root:multinexus)
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
sudo install -d -m 0750 -o root -g coord /etc/coordinate
sudo install -d -m 0750 -o root -g multinexus /etc/multinexus

sudo install -m 0640 -o root -g coord /tmp/coord.env.staging /etc/coordinate/coord.env
sudo install -m 0640 -o root -g multinexus /tmp/discord.env.staging /etc/multinexus/discord.env
sudo rm -f /tmp/coord.env.staging /tmp/discord.env.staging
EOF

# 验证 (S3 提前验):
ssh ubuntu@kook-hermes-admin "stat -c '%a %U %G %s %n' /etc/coordinate/coord.env /etc/multinexus/discord.env"
# 期望: 640 root coord <size> /etc/coordinate/coord.env
#        640 root multinexus <size> /etc/multinexus/discord.env
# size > 100
```

**注意**：Mac 端 `/tmp/coord.env` 临时文件用 `chmod 600`（Mac 单机用户私有）；**远端** `/etc/.../coord.env` 用 `chmod 640` + group（systemd 进程能读）。**两个不同点**——前者保护 Mac 端原始 token，后者保护腾讯云 systemd 跑时能 group read。

### 1.5 推 SSH 公钥（B4 依赖）

```bash
# Mac 端: 生成密钥 (一次性, ~/.ssh/id_ed25519_coord 永久保存)
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_coord -N '' -C "mac-multinexus-coord"

# Mac 端: 推公钥到 ubuntu (KHC 入口)
ssh-copy-id -i ~/.ssh/id_ed25519_coord.pub ubuntu@kook-hermes-admin

# 腾讯云端: 限 ssh 入口 (B3 安全强化, 可选)
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
# coord / multinexus 是 nologin user, 无 .ssh dir — 不需要推
# ubuntu 已有公钥, 不重复
# 验证: ssh ubuntu@kook-hermes-admin "id" 应免密成功
EOF
```

**`/etc/ssh/sshd_config` 安全加固**（可选，preflight B3 接受 fail2ban 风险）：

```bash
# 腾讯云 /etc/ssh/sshd_config.d/coord.conf
PasswordAuthentication no
PermitRootLogin no  # 禁用 root SSH, 用 ubuntu + sudo 提权
AllowUsers ubuntu
```

## 步骤 2：腾讯云起 systemd units

### 2.1 `/etc/systemd/system/coordinate.service`

**先** `sudo tee` 写文件，**再** daemon-reload。

```bash
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
sudo tee /etc/systemd/system/coordinate.service >/dev/null <<'UNIT'
[Unit]
Description=multinexus coordinate daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=coord
Group=coord
WorkingDirectory=/opt/coordinate
EnvironmentFile=/etc/coordinate/coord.env
ExecStart=/opt/coordinate/.venv/bin/coordinate --db /var/lib/coordinate/coord.sqlite3 serve --pump-interval 30
# **blocker 1**: UMask=0007 让 coord daemon 创建的 SQLite 文件 inherit group=coord
# (配 chmod 2770 + setgid, 配合 /usr/local/bin/coord-local 的 umask 0007)
UMask=0007
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable coordinate
sudo systemctl start coordinate
sudo systemctl status coordinate
EOF
# 应当看到 active (running)

# 验证 unit 内容
ssh ubuntu@kook-hermes-admin "cat /etc/systemd/system/coordinate.service | head -20"
# 期望: 跟上面 ini 块一致
```

### 2.2 `/etc/systemd/system/multinexus-discord-bridge.service`

```bash
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
sudo tee /etc/systemd/system/multinexus-discord-bridge.service >/dev/null <<'UNIT'
[Unit]
Description=multinexus Discord bridge
After=network-online.target coordinate.service
Wants=network-online.target

[Service]
Type=simple
User=multinexus
Group=multinexus
# **blocker 1 + P2.1**: bridge 进程以 multinexus 跑, 调 /usr/local/bin/coord-local
# 时需 coord group 写 /var/lib/coordinate. SupplementaryGroups=coord 把 coord
# group 加到 multinexus 进程 (primary group 仍是 multinexus).
# UMask=0007 让 bridge 创建的文件 inherit group (跟 coord.service 一致)
SupplementaryGroups=coord
UMask=0007
WorkingDirectory=/opt/multinexus
EnvironmentFile=/etc/multinexus/discord.env
ExecStart=/opt/multinexus/.venv/bin/python /opt/multinexus/multinexus.py --config /opt/multinexus/agents.toml --platform discord
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable multinexus-discord-bridge
sudo systemctl start multinexus-discord-bridge
sudo systemctl status multinexus-discord-bridge
EOF
# 应当看到 active (running) + Discord gateway RESUMED log (S4 验证)

# 验证 unit 内容
ssh ubuntu@kook-hermes-admin "cat /etc/systemd/system/multinexus-discord-bridge.service | head -20"
# 期望: 跟上面 ini 块一致
```

### 2.3 验证 V1 + V2

```bash
ssh ubuntu@kook-hermes-admin "systemctl is-active coordinate multinexus-discord-bridge"
# 应当: active\nactive
ssh ubuntu@kook-hermes-admin "stat -c '%a %U %G %s %n' /etc/coordinate/coord.env /etc/multinexus/discord.env"
# 应当: 640 root coord <size> /etc/coordinate/coord.env
#        640 root multinexus <size> /etc/multinexus/discord.env
# size > 100
```

## 步骤 3：Mac 写 wrapper + 改 agents.toml

### 3.1 写 `~/.local/bin/coord-ssh` wrapper（**关键**）

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/coord-ssh <<'EOF'
#!/usr/bin/env bash
# Mac → 腾讯云 coord wrapper
# **不**走 sudo -u coord (blocker 2: agentd 每 2s 调一次 claim, sudo 不可行)
# **走** 远端 /usr/local/bin/coord-local (group coord 方案, blocker 1)
# 远端 coord-local 已显式带 --db /var/lib/coordinate/coord.sqlite3

# **关键 (shell quoting)**: 远端命令用 printf '%q' 拼, 避免 $@ 远端展开为空
# 或 JSON arg 含空格/引号被破坏
# 例: agentd 调 `coord-ssh runtime job claim --agent-id mac-claude`
#   -> printf '%q ' 拼成 'runtime' 'job' 'claim' '--agent-id=mac-claude'
#   -> ssh 远端 shell exec `/usr/local/bin/coord-local runtime job claim --agent-id=mac-claude`
# **不能**直接写 "$@" 或 \$@, 远端 shell 看到的 $@ 是空 (positional params 未设)
remote_cmd=$(printf '%q ' /usr/local/bin/coord-local "$@")

exec ssh \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=10 \
    -o ConnectTimeout=10 \
    -o StrictHostKeyChecking=accept-new \
    -i ~/.ssh/id_ed25519_coord \
    ubuntu@kook-hermes-admin \
    "$remote_cmd"
EOF
chmod +x ~/.local/bin/coord-ssh
```

**实施约束**：
- **远端命令**只调 `/usr/local/bin/coord-local`，**不** `sudo -u coord`（blocker 2：每 2s 一次 sudo 会刷爆 sudo timestamp / 要求 TTY / sudo 不可行）
- **shell quoting 关键**：用 `printf '%q ' "$@"` 把每个 arg 拼成 shell-safe 字符串，**绝对不能**用 `\$@` / `$@`（远端 shell 看到 `$@` 展开为空，agentd 参数全丢）
- **`--db` 显式** 在远端 `coord-local` wrapper 内部（preflight line 139-142）—— **不**在 Mac wrapper 里写（避免重复 + Mac wrapper 不依赖远端路径细节）
- `-i ~/.ssh/id_ed25519_coord` 显式密钥（**不**走默认 key 误连错 host）
- `ubuntu@kook-hermes-admin` SSH 用 ubuntu admin 入口（**不**用 `root@tencent-cloud` 因为本机 `~/.ssh/config` 没那个 alias）
- 远端 SSH session 走 ubuntu，**走 coord-local**（ubuntu 在 coord group，**有** group rwx）

### 3.2 改 `agents.toml`（**只改一行**）

```bash
# 备份:
cp /Users/yinxin/projects/multinexus/agents.toml /Users/yinxin/.multinexus/phase-7.2-impl-backup-$(date +%Y%m%d)/agents.toml.bak 2>/dev/null || true

# 改一行 (sed):
sed -i.bak 's|coordinator_cli_path = ".*"|coordinator_cli_path = "/Users/yinxin/.local/bin/coord-ssh"|' /Users/yinxin/projects/multinexus/agents.toml

# 验证:
grep coordinator_cli_path /Users/yinxin/projects/multinexus/agents.toml
# 应当: coordinator_cli_path = "/Users/yinxin/.local/bin/coord-ssh"

grep coordinator_db_path /Users/yinxin/projects/multinexus/agents.toml
# 应当: coordinator_db_path = "/Users/yinxin/projects/coordinate/data/coordinator.sqlite3" (本机值, 保留)
```

**实施约束**：
- **只改 `coordinator_cli_path` 一行**
- **`coordinator_db_path` 不动**（preflight B7 / line 365-368 / 改 4 强化）
- **`mac.sh` 内部不动**（preflight B1 段末）

### 3.3 停 Mac 单机 coord + bridge

**注意**：停**之前**确认腾讯云 systemd unit 都 active（步骤 2.3 V1 验证过），否则会断线。

```bash
# 实施前先验证 launchd 跑的 plist label (用 launchctl print 反查):
launchctl print gui/$(id -u)/com.coordinate.runtime 2>&1 | grep -E "^[[:space:]]*path = " | head -1
# 期望: path = /Users/yinxin/projects/multinexus/launchd/com.coordinate.runtime.plist
launchctl print gui/$(id -u)/com.multinexus.discord.bridge 2>&1 | grep -E "^[[:space:]]*path = " | head -1
# 期望: path = /Users/yinxin/projects/multinexus/launchd/com.multinexus.discord.bridge.plist
# (label 和 plist 文件 path 可能不同! 实施前必查)

# 停 Mac 进程 (label = 实际 launchd label):
launchctl bootout gui/$(id -u)/com.coordinate.runtime
launchctl bootout gui/$(id -u)/com.multinexus.discord.bridge
# (plist 文件保留, 仅 bootout — 实施约束: 不动 plist 内容)

# 验证 Mac 进程:
ps aux | grep -E "coordinate serve|multinexus.*--platform discord" | grep -v grep
# 应当: 空 (没有本机 coord/bridge 进程)
```

**实施约束**：
- **launchd label 跟 plist 文件名可能不同**（如 `com.multinexus.mac-claude` label 用 `com.multinexus.mac-claude.agentd.plist` 文件）—— 实施前**用 `launchctl print gui/$UID/<label>` 反查 path**
- **Mac agentd 4 个 plist 不 bootout**（要继续跑，调腾讯云 coord）—— 验证它们在 `launchctl list` 里仍 PID 48703 / 48706 / 48709 / 48712

## 步骤 4：Smoke test

**两套独立 smoke**：
- **CLI smoke (S1-S8)**：验证 Mac agentd 能 claim/report 远端 coord job
- **Discord smoke (D1-D6)**：验证腾讯云 bridge 收 Discord 消息 → coord → Mac agentd → bridge 回原频道

**为什么拆**：`runtime request submit` CLI 直接提交 job **不**经过 bridge 进程，**不能**验证 bridge 回原频道。**只有真实 Discord 消息**能验证整链路。

**每步必须独立 pass，failed step 必须先回滚到上一步成功状态再继续**。

### Log 路径读取（**所有** log 命令前置**这一步**）

```bash
# 实施前先验证 plist 路径, 再读 log 路径 (不写死)
PLISTS=(
    /Users/yinxin/projects/multinexus/launchd/com.coordinate.runtime.plist
    /Users/yinxin/projects/multinexus/launchd/com.multinexus.discord.bridge.plist
    /Users/yinxin/projects/multinexus/launchd/com.multinexus.mac-claude.agentd.plist
    /Users/yinxin/projects/multinexus/launchd/com.multinexus.mac-codex.agentd.plist
    /Users/yinxin/projects/multinexus/launchd/com.multinexus.mac-omp.agentd.plist
    /Users/yinxin/projects/multinexus/launchd/com.multinexus.mac-opencode.agentd.plist
)
for p in "${PLISTS[@]}"; do
    label=$(plutil -extract Label raw "$p" 2>/dev/null)
    out=$(plutil -extract StandardOutPath raw "$p" 2>/dev/null)
    err=$(plutil -extract StandardErrorPath raw "$p" 2>/dev/null)
    echo "$label | out=$out | err=$err"
done
# 期望: 6 行, 各自 log 路径
# 实施中以下变量用 plutil 输出:
#   COORD_LOG=/Users/yinxin/projects/coordinate/logs/runtime.err.log (来自 com.coordinate.runtime.plist)
#   BRIDGE_LOG=/Users/yinxin/projects/multinexus/logs/discord.bridge.err.log (来自 com.multinexus.discord.bridge.plist)
#   AGENTD_LOG_mac_claude=/Users/yinxin/projects/multinexus/logs/mac-claude.agentd.err.log
#   (其他 3 个 agentd 同形式)
```

**警示**：
- **`COORD_LOG` / `BRIDGE_LOG` Mac 端路径仅在 Mac 跑本机 coord/bridge 时用**
- **阶段 A** (本 plan) **Mac coord/bridge 已 `launchctl bootout`**（步骤 3.3），**真实 log 在腾讯云 systemd journal**：
  - coord: `ssh ubuntu@kook-hermes-admin "sudo journalctl -u coordinate"`
  - bridge: `ssh ubuntu@kook-hermes-admin "sudo journalctl -u multinexus-discord-bridge"`
- **D 段**（Discord smoke）**只用**远端 journalctl，**不**用 Mac plist 路径
- **AGENTD_LOG_*` Mac 路径仍有效**（agentd 在 Mac 跑，没动），CLI smoke 的 S5-S8 看 Mac agentd log 用 plutil 变量

### A. CLI smoke (S1-S8)

#### S1. 远端 coord daemon 活

```bash
ssh ubuntu@kook-hermes-admin "systemctl is-active coordinate"
# 期望: active
```

#### S2. 远端 bridge daemon 活

```bash
ssh ubuntu@kook-hermes-admin "systemctl is-active multinexus-discord-bridge"
# 期望: active
```

#### S3. 远端 secret 落档验证（**不 cat 内容**）

```bash
ssh ubuntu@kook-hermes-admin "stat -c '%a %U %G %s %n' /etc/coordinate/coord.env /etc/multinexus/discord.env"
# 期望: 640 root coord <size1> /etc/coordinate/coord.env
#        640 root multinexus <size2> /etc/multinexus/discord.env
# size > 100
```

#### S4. 远端 bridge 启动 log 看 Discord gateway

```bash
ssh ubuntu@kook-hermes-admin "sudo journalctl -u multinexus-discord-bridge --since '5 minutes ago' --no-pager | tail -20"
# 期望: 看到 "Discord gateway RESUMED" 或 "Gateway ready" 或 "Logged in as ..."
```

#### S5. Mac wrapper 调 register (CLI 直调远端 coord)

```bash
~/.local/bin/coord-ssh runtime agent register \
    --agent-id mac-claude \
    --host-id macbook-local \
    --client-type agentd
# 期望: JSON {"ok": true, "agent_id": "mac-claude"} 或同等成功标志
```

#### S6. Mac wrapper 调 claim (queue 空)

```bash
~/.local/bin/coord-ssh runtime job claim --agent-id mac-claude
# 期望: {"claimed": false, "job": null} 或同等空队列
```

#### S7. 验证远端 agents 表有 mac-claude

```bash
ssh ubuntu@kook-hermes-admin "sudo sqlite3 /var/lib/coordinate/coord.sqlite3 \"SELECT id, status, host_id, last_seen_at FROM agents WHERE id = 'mac-claude'\""
# 期望: mac-claude|online|macbook-local|<recent timestamp>
```

#### S8. stale detection

```bash
# 停一个 Mac agentd (例如 mac-claude) — 用 launchctl label (实施前查 plutil -extract Label raw)
launchctl bootout gui/$(id -u)/com.multinexus.mac-claude.agentd
sleep 360  # 6 分钟, 超过 heartbeat 间隔
ssh ubuntu@kook-hermes-admin "sudo sqlite3 /var/lib/coordinate/coord.sqlite3 \"SELECT id, status, last_seen_at FROM agents WHERE id = 'mac-claude'\""
# 期望: status=stale 或 offline
# 重新启动 — 用仓库内 plist 路径 (不是 ~/Library/LaunchAgents/)
launchctl bootstrap gui/$(id -u) /Users/yinxin/projects/multinexus/launchd/com.multinexus.mac-claude.agentd.plist
sleep 30
ssh ubuntu@kook-hermes-admin "sudo sqlite3 /var/lib/coordinate/coord.sqlite3 \"SELECT id, status, last_seen_at FROM agents WHERE id = 'mac-claude'\""
# 期望: status=online
```

**S8 期望** coord `pump-interval=30` (preflight line 187) + heartbeat 间隔 (preflight 7.1.1 plan line 13-19) 决定 stale 时间，**6 分钟是保守值**。

### B. Discord smoke (D1-D6) — **真实 Discord 端到端**

**目的**：验证 `腾讯云 bridge 收 Discord 消息 → coord 写 job → Mac agentd claim → claude CLI 跑 → bridge 收 result 回原频道`。

**前置**：
- Mac 端有 1 个 agentd plist 跑通 S1-S8（即 agentd 实际能 claim 远端 coord job）
- 腾讯云 bridge 实际连上 Discord gateway（S4 验证）
- Mac 端**不**需要 `runtime request submit` CLI —— 真实 Discord 消息就是 trigger

#### D1. 准备：记录原 Discord channel 状态

```bash
# 截图 Discord channel 状态 (实施时手动)
# 记录最近 5 条消息 (作为 baseline, 跟 D6 对比)
```

#### D2. 准备：起 agentd log tail (background)

```bash
# 实施前先读 plist 拿 log 路径:
AGENTD_LOG=$(plutil -extract StandardOutPath raw \
    /Users/yinxin/projects/multinexus/launchd/com.multinexus.mac-claude.agentd.plist)
echo "Watching $AGENTD_LOG"
tail -F "$AGENTD_LOG" | grep -E "Processing job request|complete:" &
TAIL_PID=$!
# 留 $TAIL_PID 给 D5 用
```

#### D3. 准备：起 bridge log tail (background)

**重要**：阶段 A Mac 端的 bridge 已 `launchctl bootout`（步骤 3.3），**真实 bridge 在腾讯云 systemd 里**。**bridge log 必须用远端 journalctl 看**，**不**用 Mac plist 路径。

```bash
# 起 ssh 跟远端 journalctl -fu (跟 tail -F 等价, 远端 systemd journal 持续)
ssh -t ubuntu@kook-hermes-admin "sudo journalctl -fu multinexus-discord-bridge" 2>&1 | grep -E "submit_request|received message|reply|resumed|ready" &
BRIDGE_TAIL_PID=$!
```

#### D4. 真发 Discord 消息 (手动)

```text
在 Discord channel 发消息:
  @Mac Claude ping

(实施时: 用手机 / 另一台设备 / 浏览器, 在 multinexus 启用的 Discord server
 找到 #nexus 之类的 channel @Mac Claude bot, 发短消息)
```

**消息内容要求**：
- mention `@Mac Claude`（触发 DiscordBridge mention 路由到 mac-claude agentd）
- 内容简单（"ping" / "echo hi" / "smoke test"）—— claude CLI 能秒答
- **不**超 200 字（避免 chunking 干扰）

#### D5. 看 agentd log 收到 claim

```bash
# 5s 内应当看到 (来自 D2 tail):
# "Processing job request:request:xxx: agent=mac-claude"
# 30s 内应当看到:
# "complete: status=done duration=...ms"
```

**失败排查**：
- 5s 内**没**看到 "Processing job request" → bridge **没** submit 到 coord（看 D6 bridge log）
- 30s 内**没**看到 "complete" → agentd claim 了但 claude CLI 卡（看 stderr log）

#### D6. 看 bridge log 收 result + 回原频道

```bash
# 看 D3 ssh -t journalctl 输出:
# 期望看到 "received message" / "submit_request" / "reply" / "RESUMED" 之类条目
# 30s 内 Discord channel 出现 bot reply (mac-claude webhook 身份)
# bot reply **不**是 "Job done", 是真实 claude 输出

# **如果 D3 ssh 已 exit** (D4-D5 完成, ssh 断开), 重新拉一次完整 log:
ssh ubuntu@kook-hermes-admin "sudo journalctl -u multinexus-discord-bridge --since '5 minutes ago' --no-pager | tail -30"
# 期望: 看到 "submit_request" / "reply sent" / "RESUMED" 等条目
```

### C. 全 smoke test 通过

| 项 | 期望 |
|---|---|
| Mac agentd stderr | 没 `coordinate CLI failed` 累积 |
| 腾讯云 coord CPU | < 5% 稳态 |
| 腾讯云 bridge log | Discord gateway RESUMED, 0 disconnect |
| Mac Discord bot | 4 个 mac-* bot 全在线（status=online in S7 类似查询） |
| 腾讯云 bridge 进程能收 Discord 消息 | D5 + D6 验证 |
| 腾讯云 bridge 进程能回原频道 | D6 验证 |

## 步骤 5：失败回滚

**任何一步失败** → **不**继续往下做，**回滚**到 Mac 单机 6 进程拓扑。

### R1. 停腾讯云 service

```bash
ssh ubuntu@kook-hermes-admin <<'EOF'
set -euo pipefail
sudo systemctl stop coordinate multinexus-discord-bridge
sudo systemctl disable coordinate multinexus-discord-bridge
sudo rm /etc/systemd/system/coordinate.service /etc/systemd/system/multinexus-discord-bridge.service
sudo systemctl daemon-reload
EOF
```

### R2. 还原 Mac `agents.toml`

```bash
# 用步骤 0 备份:
cp ~/.multinexus/phase-7.2-impl-backup-*/agents.toml.bak /Users/yinxin/projects/multinexus/agents.toml
# 验证:
grep -E "coordinator_cli_path|coordinator_db_path" /Users/yinxin/projects/multinexus/agents.toml
# 应当: 还原到本机 /Users/yinxin/.../mac.sh 和 /Users/yinxin/projects/coordinate/data/coordinator.sqlite3
```

### R3. 重启 Mac 单机 coord + bridge

```bash
# launchd 跑的是仓库内 plist, **不**是 ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) /Users/yinxin/projects/multinexus/launchd/com.coordinate.runtime.plist
launchctl bootstrap gui/$(id -u) /Users/yinxin/projects/multinexus/launchd/com.multinexus.discord.bridge.plist
```

### R4. 验证回滚成功

```bash
ps aux | grep -E "coordinate serve|multinexus.*--platform" | grep -v grep | wc -l
# 期望: 2 (1 coord + 1 bridge, **不**算 4 agentd)
# 加 agentd: ps aux | grep -E "agentd" | grep -v grep | wc -l
# 期望: 4
# 合计 6 进程 (1 coord + 1 bridge + 4 agentd)

# Discord smoke: 发消息看 bot reply 仍走 Mac coord
```

**R4 失败**（回滚后 Mac 仍不工作）→ **保留**腾讯云 service 启动 + 报 blocker（**不**删腾讯云 service，等用户决定）。

## 步骤 6：Closeout

### 6.1 收集 evidence

- 8 步 CLI smoke (S1-S8) 输出
- 6 步 Discord smoke (D1-D6) 输出 + 截图
- 远端 coord DB 截图（`agents` 表 + `jobs` 表）
- Mac `ps` 输出（V7 验证）
- Mac Discord channel 截图（D6 验证）
- 实施时间日志（每步 start/end）

### 6.2 closeout 报告写在哪

- 实施完 **不** commit
- 实施完 **不** push
- 实施完 **不** 开 PR
- closeout 报告写到 `docs/project-harness/tasks/phase-7.2-tencent-cloud-impl/closeout-<YYYY-MM-DD>.md`
- **等用户明确指示**才 commit / push / PR

## 风险 + 缓解

| 风险 | 缓解 |
|---|---|
| Mac ISP 出口 IP 动态 → SSH 失败 | preflight B3：fail2ban + 接受风险；阶段 B 改 Tailscale |
| SSH 长连断 → Mac agentd 刷 `coordinate CLI failed` 日志 | preflight B6：刷日志不崩；阶段 B 加断连告警 |
| 远端 coord CLI 启动 + SSH 握手 > 30s → agentd timeout | preflight B5：wrapper SSH option `ConnectTimeout=10` 让 SSH 10s 失败 |
| 远端 systemd unit 启动失败（缺 env、缺 db path） | 步骤 2.3 V1 + 步骤 4 S1 + S2 验证 + 步骤 5 R1 回滚 |
| `mac.sh` 内部 `coord` binary 找不到了（**没**改 mac.sh） | preflight B1：mac.sh 留作本机 fallback，阶段 A 不动；**回滚**时 Mac 仍能用 mac.sh 跑本机 coord |
| 腾讯云 systemd unit 启动后但 bridge 找不到 `/etc/multinexus/discord.env`（权限错） | 步骤 1.4 group read + 步骤 4 S2 + S3 验证 |
| `agents.toml` 改错字段名 | 步骤 3.2 改**前**备份，**后** grep 验证；步骤 5 R2 还原 |
| 实施时间窗口超过 ISP 限流（VPN / SSH 限流） | 实施前确认 ISP 状态；fail2ban 风险已 preflight 接受 |

## 依赖

| 依赖 | 状态 |
|---|---|
| 腾讯云 VM 已购买 | **实施前确认**（用户责任） |
| 腾讯云防火墙放行 22/TCP inbound from Mac 出口 IP | **实施前确认**（用户责任） |
| `coord` repo 可在 Mac `/Users/yinxin/projects/coordinate/` 访问 | **已具备**（commit `c91d45b` / `08b5bcc` 都在） |
| `multinexus` repo 可在 Mac `/Users/yinxin/projects/multinexus/` 访问 | **已具备**（当前 branch `agents/mac-claude/phase-7.2-multi-host-agent-runtime`，commit `40da1db`） |
| `agents.toml` 当前修改备份存在 | **步骤 0 必做** |
| Mac 出口 IP 已知（写安全组时用） | **实施前确认**（用户责任） |
| `~/.ssh/id_ed25519_coord` Mac 私钥未泄露 | **实施前确认**（用户责任） |
