# P9-3C1 P1 Coordinate Scoped Primitives — Inert Deployment and Dogfood

状态：`P1_CLOSED_P2_NEXT`

日期：2026-07-16 Asia/Shanghai

## Integrated revision

- Reviewed candidate `a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7` fast-forward merged to
  Coordinate `main` and pushed to `origin/main`。
- Merge 前 fresh `git fetch origin main` 证明 remote base仍为
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`；implementation remains exact one commit / eight
  files，message `feat(p9-3c1): add scoped production primitives`。
- User-owned untracked `/Users/yinxin/projects/coordinate/.qoder/` 保持未触碰。

## Read-only preflight

- P0 installed lock helper `status`：`{"phase":"free","state":"free"}`；global lock path absent。
- `coordinate.service`：`active`，PID/NRestarts `836234/0`。
- `multinexus-discord-bridge.service`：`active`，PID/NRestarts `1276892/0`。
- Coordinate deployed revision仍为 base `9804bbd...`；MultiNexus deployed P0 docs/helper revision为
  `1b1d1fd...`。
- Production DB：integrity/schema/FK `ok / 13 / 0`；pending/running jobs `0`，active leases `0`，
  P9-3C1/P9-3C pattern agents/jobs `0`。
- P9-3C1 unit absent、lock path absent；没有 fixture/controller process。

## Successful inert deploy

Operator 从 tracked-clean Coordinate candidate worktree运行：

```bash
scripts/deploy-server.sh coordinate \
  --host kook-hermes-admin \
  --coordinate-src /Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3c1-p1-scoped-primitives \
  --no-restart
```

Deploy driver使用已部署 P0 shared production mutation lock；执行 local parity、lock acquire、
Coordinate staging/sync/install、server smoke、exact release并返回 0。没有使用 `--allow-dirty`、
`--skip-install`、`--no-smoke`、fault injection、recover、fixture activation 或 service restart。

Production `VERSION_DEPLOYED`：

```text
component=coordinate
commit=a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7
deployed_at=2026-07-16T00:35:31Z
```

Final output：`server smoke OK`；P0 lock最终为 free且 lock path absent。

## Source/install identity

Local source、`/opt/coordinate/src` 与 installed wheel package精确匹配：

```text
runtime_lease.py  5bdfd1543ebbf306d3d817b4ab7417af235852605d11fa9a30731f7ea4a0752a
runtime.py        d5d928ccbc6406f12dcdc75f54749016f3465ed7fd935f4b200abe2403e5cabd
execution_cli.py  6a8f7ea0bd73802e93124c10e5295fc72d8c97c4b4c55afd6ce2fea8ed7faf28
```

这同时证明本次没有只同步 source 而遗漏 runtime install。

## Read-only CLI surface smoke

只运行 installed CLI `--help`，没有调用任何新 mutation：

- `runtime agent --help` 显示 `register,heartbeat,deactivate`；
- `runtime job claim --help` 显示 `--reap-mode {global,none}` 与 `--reap-reason`；
- `runtime job lease reap --help` 显示 mutually-exclusive `--batch-size | --lease-id` 与 paired
  `--job-id`。

没有运行 `runtime agent deactivate`、`runtime job claim` 或 `runtime job lease reap` against
production DB。

## Post-deploy zero-activation proof

- Canonical PID/NRestarts与 preflight完全相同：`836234/0`、`1276892/0`；两服务 active。
- DB integrity/schema/FK仍为 `ok / 13 / 0`。
- pending/running jobs `0`，active leases `0`，P9-3C1/P9-3C pattern agents/jobs `0`。
- P9-3C1 unit absent、fixture/controller process absent、global lock path absent，installed helper
  `status=free`。
- Coordinate local `main`、`origin/main`、deployed revision均为 exact `a8fc317...`。

因此本轮只部署并 read-only dogfood了 P1 primitives surface；没有改变 production runtime state、
创建 audit event、执行 reap/claim/deactivate、重启 canonical service 或启动 paid provider job。

## Closeout

P9-3C1 P1 已完成 measurement/plan、plan review、worker bootstrap/review、bounded non-Codex worker
attempt、Codex correction/review、fresh independent result review、merge、push、P0-locked inert deploy、
installed-source identity、CLI help smoke 与 zero-activation verification。

P2 controller/production orchestration contract是下一个独立 detailed-plan package；P3 intake/routing
closure和 live matrix仍 blocked，必须继续经过 plan review、bootstrap review、worker、result review和
production mutation gate。

P9_3C1_P1_COORDINATE_SCOPED_PRIMITIVES_CLOSED
