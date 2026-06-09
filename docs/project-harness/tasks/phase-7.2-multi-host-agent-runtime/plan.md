# Phase 7.2: 多主机 Agent Runtime

## 目标

在 Phase 7.1 单机 N+M 跑通后，把 agentd 分布到不同主机，同时保持 bridge/coordinator 的位置和 agent 的位置解耦。

目标形态：

```text
Mac:
  coordinate
  discord-bridge
  kook-bridge
  mac-codex agentd
  mac-claude agentd

Windows:
  win-claude agentd
  win-opencode agentd

Linux:
  server-hermes agentd
```

之后可以把 coordinate 和 bridges 迁到服务器：

```text
Server:
  coordinate
  discord-bridge
  kook-bridge

Mac:
  mac-codex agentd
  mac-claude agentd

Windows:
  win-claude agentd

Linux:
  server-hermes agentd
```

## 核心原则

- 每个 agent identity 全局只有一个 agentd。
- 每个 IM 平台只有一个 active logical bridge。
- bridge 不绑定本机 agent。
- agentd 通过 `COORDINATE_URL` 找 coordinate。
- Git 分支、PR、CI、review 仍然是代码协作的 source of truth。
- harness 文件继续跟项目走 Git。
- coordinate DB 是唯一 canonical runtime DB。

## 范围

### 1. Agentd 远程连接

- agentd 支持 `COORDINATE_URL`。
- agentd 支持认证 token。
- agentd 可以 register/heartbeat。
- agentd 可以 claim job。
- agentd 可以 report result。

### 2. Host identity

agent registry 需要能表达：

- agent id
- host id
- host label
- platform/OS
- capabilities
- last heartbeat
- online/offline/stale 状态

host 是执行位置，不是路由边界。Discord bridge 跑在 Mac 上时，也可以路由到 Windows agentd。

### 3. Job claim 安全性

- 多个 agentd polling 时不能重复领取同一个 job。
- job result report 必须幂等。
- 网络断开后不能让已完成任务重复执行。
- stale heartbeat 的 agent 不能继续接新任务。

### 4. 网络路径

第一版建议使用私有网络：

```text
Tailscale / ZeroTier / SSH tunnel / Cloudflare Tunnel
```

应用层只依赖：

```text
COORDINATE_URL
COORDINATE_TOKEN
```

不要把 Mac 本地路径、内网 IP 或某台机器的特殊路径写死在业务逻辑里。

### 5. Server 迁移准备

从一开始就让 bridge/agentd 只通过配置找 coordinate。这样从 Mac 迁到服务器时只需要改：

- `COORDINATE_URL`
- credentials
- process supervisor 配置
- token/env 文件位置

不改业务代码。

## 非目标

- 不做多 coordinate 数据库同步。
- 不做 SQLite 跨主机文件共享。
- 不强制切 PostgreSQL。
- 不做完整 HA。
- 不允许每台主机都跑一套 platform bridge 并绑定本机 agents。

## 验收标准

- 远程 agentd 可以从 Mac-hosted coordinate 领取并完成任务。
- Discord bridge 可以触发非本机 agentd。
- KOOK bridge 可以触发同一个非本机 agentd。
- 同一个 agent identity 没有平台维度的重复 adapter 进程。
- stale heartbeat 后 coordinate 不再给该 agent 分配新 job。
- result report 重放不会重复发消息或重复关闭任务。
- coordinate 迁到服务器时，bridge/agentd 只改配置即可继续工作。

## 建议实现顺序

1. 在 Mac 上用 `COORDINATE_URL` 跑本地 agentd，避免依赖隐式本地路径。
2. 接入一个远程 agentd，优先选已有服务器 Hermes 或 Windows opencode/Claude。
3. 验证 heartbeat 和 stale detection。
4. 验证 job claim/result report 幂等。
5. 验证 Discord 请求路由到远程 agentd。
6. 验证 KOOK 请求路由到同一个远程 agentd。
7. 编写 Mac -> Server 迁移 runbook。

## 风险

- NAT、睡眠、Wi-Fi 切换会影响 Mac-hosted coordinate 的可达性。
- Windows subprocess 行为和 Unix 不一致，agentd 需要保留平台差异处理。
- 远程 agentd 失败时，coordinate 的 retry/cancel/dead-letter 语义必须清楚。
- 如果 bridge 和本机 agent 重新绑定，会退回 `n * m` 复杂度。
