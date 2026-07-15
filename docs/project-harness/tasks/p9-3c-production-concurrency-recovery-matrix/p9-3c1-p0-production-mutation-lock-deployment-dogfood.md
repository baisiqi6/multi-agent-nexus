# P9-3C1 P0 Production Mutation Lock — Inert Deployment and Dogfood

状态：`P0_CLOSED_P1_NEXT`

日期：2026-07-16 Asia/Shanghai

## Integrated revision

- Reviewed candidate `ec748dc040b9ebf8f456c6bc0ab6db28e0dd26c6` fast-forward merged to
  MultiNexus `main` and pushed to `origin/main`。
- Merge 前 fresh `git fetch origin main` 证明 remote base 仍为
  `d09e0f8fba0f6d189934173027ca5a756e5f36ce`；implementation diff 仍为 exact four-file
  allowlist。
- Implementation commit remains the single commit `feat(p9-3c1): add production mutation lock`。

## Read-only preflight

首次 production preflight 证明：

- host `VM-0-15-ubuntu`；
- `coordinate.service` PID/NRestarts `836234/0`，
  `multinexus-discord-bridge.service` PID/NRestarts `1276892/0`；两者均 `active`；
- installed helper absent，global lock path absent；
- deployed MultiNexus revision 为 base `d09e0f8...`；
- `deploy-server.sh status` 稳定输出 `lock_helper=absent`，继续完成
  `server smoke OK`，并按 contract 返回 nonzero；没有 install/acquire/release mutation。

## Fail-closed local parity retry

第一次运行：

```bash
scripts/deploy-server.sh multinexus --host kook-hermes-admin --no-restart
```

在本地 `local-parity` gate 返回：

```text
error: missing local runtime config: <isolated-worktree>/agents.toml (stage: local-parity)
```

失败发生在 remote acquire 之前，production helper/lock/source/service 均未改变。隔离 worktree
缺少主 checkout 中被 ignore 的 runtime config；Operator 只创建指向当前本地
`/Users/yinxin/projects/multinexus/agents.toml` 的 ignored symlink，供 parity read 使用。
`sync_to_remote_staging` 仍显式 exclude `agents.toml`，因此该文件及其内容没有传输或覆盖 server
runtime config。Worktree 保持 tracked-clean，exact candidate 不变。

这次偏差说明：clean isolated deployment worktree 也需要显式、只读、不可传输的 runtime parity
input；不能用 `--allow-dirty` 绕过，也不能在 parity 未完成时 acquire production lock。

## Successful inert deploy

同一命令第二次成功。执行顺序为：

```text
local parity
-> streamed acquire
-> same-token atomic helper install/validation
-> locked MultiNexus staging/sync/catalog exact retries/install
-> server smoke
-> installed-helper exact release
```

部署使用 exact commit `ec748dc...`，明确带 `--no-restart`；未使用 `--allow-dirty`、fault
injection、fixture sync、job/lease submission、reap、recover 或 controller。Roster、executor 和
capacity catalog 都是 unchanged/exact retry：无 added、removed 或 updated identity/definition/
binding/policy，executor/capacity `changed=false`。Final smoke 为 `server smoke OK`。

Production `VERSION_DEPLOYED`：

```text
commit=ec748dc040b9ebf8f456c6bc0ab6db28e0dd26c6
deployed_at=2026-07-15T22:55:42Z
```

## Installed lock proof

Local source、installed helper 和 deployed source 的 SHA-256 exact match：

```text
7dd71c31595c7135a8a75ef3d8e459788682f6a30272ea5bdeb66bb7c2a2ebd4
```

- `/usr/local/sbin/coordinate-production-mutation-lock`：ordinary file、single link、
  `root:root`、mode `0755`、size `36897`；
- `/opt/multinexus/scripts/production-mutation-lock.py`：ordinary file、single link、mode
  `0755`、same bytes；
- installed `status` 返回 `{"phase":"free","state":"free"}`；
- `/run/lock/coordinate-production-mutation.lock` absent；
- bounded `deploy-server.sh status` 返回 0 并再次完成 `server smoke OK`。

## Post-deploy zero-activation gate

- canonical PID/NRestarts 与 preflight 完全相同：`836234/0`、`1276892/0`；两服务 active；
- production DB integrity/schema/FK：`ok / 13 / 0`；
- pending/running jobs `0`，active leases `0`；
- P9-3C1/P9 fixture agents、runner profiles、jobs、executor sources、capacity sources 全部 `0`；
- P9-3C1 unit files、loaded units、processes全部 `0`；
- deploy staging、capacity snapshot 和 registry backup residue search 为空。

因此本次只部署并实际 dogfood 了 shared production mutation lock；没有 production fixture
activation、matrix job、lease/reap、canonical restart 或 paid provider call。

## Closeout

P9-3C1 P0 已完成 plan/bootstrap review、worker/correction、Codex review、fresh independent result
review、merge、push、inert deploy、lock status smoke 与 zero-activation verification。P1 Coordinate
exact scoped reap、claim-time `reap_mode=none` 和 audited runtime-agent deactivate 是下一个独立
reviewed package；P2/P3 和 live matrix 仍保持 blocked。

P9_3C1_P0_SHARED_PRODUCTION_MUTATION_LOCK_CLOSED
