# P9-3C1 P2 Inert Production Controller — Deployment and Dogfood

状态：`P2_CLOSED_P3_PLAN_NEXT`

日期：2026-07-16 Asia/Shanghai

## Integrated revision

- MultiNexus `main`、`origin/main` 与 deployed revision均为
  `06f98f25f3ef5f51b6bc191c66fbe041c0e006a6`。
- Runtime implementation commit为 `17d0bcc1d0aeb56a821b88f096379e6dcb547fc9`；后续
  `06f98f2`只增加 correction review/progress/dogfood文档。
- Coordinate production revision保持
  `a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。
- User-owned untracked `/Users/yinxin/projects/multinexus/sessions/`保持未触碰。

## Local and independent gates

- Controller：`47 passed`；ledger-focused：`7 passed`。
- Full gate：`1032 passed, 2 skipped, 81 subtests passed`。
- `py_compile`、`git diff --check`：PASS。
- Fresh read-only KAT reviewer session `019f69bd-9bcd-7000-acb7-c495eb8d66b8` reviewed exact
  `c2bee4d..17d0bcc` and returned `APPROVE` with no blocker；native JSONL SHA-256：
  `7d59b9616836c995af95346b941e0a7c45e9078cfb8c1f93cc8943100c9490f5`。

## Corrected no-restart deploy

Operator从 tracked-clean exact worktree执行：

```bash
scripts/deploy-server.sh multinexus \
  --host kook-hermes-admin \
  --multinexus-src <exact-worktree> \
  --no-restart
```

Roster、executor、capacity canonical parity均为 exact retry：added/removed/updated为空，catalog
`changed=false`，没有 fixture source delta。Deploy写入 exact `VERSION_DEPLOYED=06f98f2`，没有重启
canonical service。

第一次 deploy smoke因运行中 Discord gateway TLS reset/reconnect日志返回 1；安装、lock、DB、PID与
revision gate均已完成。这是网络运行面 breaker，不能被记成 deploy PASS。Bridge随后在
`15:13:03`恢复 session，之后又经历一次 reconnect并在 `15:14:49`完成新 session ready；以该 exact
ready boundary复跑 bounded smoke最终 `server smoke OK`。全程 PID/NRestarts保持
`836234/0`、`1276892/0`，没有 restart或新进程替换。

## Installed identity

Controller source/install SHA-256 exact：

```text
p9_3c1_controller.py  31ca28804c2a5d9252002124c324acb7353a2431af6da82e37e3b9c3ffcecf82
entrypoint              1c18e9f594de794db6760a7eb54fe64fb2b385b36011549a82ec78507676ef6d
unit helper             9a694959f830ee8eeaec9b06493b111a10305f105bf852657682b329867bd552
fixture bin             31a4647ac716e90ecd29cb4e77cec51007d5fb590dd4ab571e41c46dac073015
agentd __main__         000f6f9b16e1060ac725014e0ab8c3b4f8bcf8c5d4c762089b7e9a09039e304c
agentd worker           00199d07969ee9f5193ad04d1c9e6374efd7dd2e53de47d8ae807a60a79c2c88
agentd client           c23cbcf60f4d307d206b526ef6d810a2b12270caf0ebd499d2cc78c4fb1f77f4
system Python           e1efa562c2cc2e35521a5c9c9b9939921001ff8ca9708a13ef15ace68cc2ccd7
P0 lock helper          7dd71c31595c7135a8a75ef3d8e459788682f6a30272ea5bdeb66bb7c2a2ebd4
```

`/usr/bin/python3.12`为 single-link ordinary file、`root:root 0755`。Controller manifest封存的
MultiNexus/Coordinate revisions、installed hashes与 live authority一致。

## Fresh inert run

Successful run：

```text
p9-3c1-prod-20260716t071325z-06f98f25
```

只调用：

```text
prepare --unit-user coord --unit-group coord
preflight
status
preflight
status
```

没有调用 `run` 或 `cleanup`。`prepare`返回 `status=sealed`；owner/mode tree为：

- root `root:root 0750`；`control/ledger/evidence/backup`为 `root:root 0700`；
- `runtime`与 `runtime/work`为 `root:coord 0750`；
- `runtime/context`、`runtime/work/e1`、`runtime/work/e2`为 `coord:coord 0700`；
- every evidence/manifest/phase/ledger/backup file为 `root:root 0600`。

`control/live-authorization.json`与 `control/production-lock.token`始终 absent。

## Read-only stability proof

Prepare后、Round 1后、Round 2后的 full tree bytes+metadata aggregate SHA-256完全一致：

```text
4dca4e1d2f3908ee4d6effdd7f5cfafcc2951dd854c0993198d74286b061c207
```

Canonical aggregate formula：

```bash
ROOT=/var/tmp/multinexus-p9-3c1/p9-3c1-prod-20260716t071325z-06f98f25
(sudo find "$ROOT" -xdev -printf '%P|%y|%m|%U|%G|%s|%T@|%n\n'; \
 sudo find "$ROOT" -xdev -type f -exec sha256sum {} +) \
  | LC_ALL=C sort | sha256sum
```

两轮 `preflight`精确返回：

- `status=preflight_passed`、`phase=sealed`、`lock_mode=free`；
- DB integrity/schema/FK/due active lease：`ok / 13 / 0 / 0`；
- manifest SHA：`778e61a66de4501622ec42d9d2f59bb5de89c3ce623ca33e2d90837b40863c82`；
- backup SHA：`8afab30d7d71b06a499a8f5ba19f25bb91b57abb5b64a7a3c610f1ae313d812e`；
- canonical projection SHA：
  `a84c040bd7fb9bde7f970c950ce4469e3edd1c2d7e0db2182fb0636593fd00cb`。

两轮 `status`精确返回：`phase=sealed`、`ledger_records=1`、
`tail_event=prepare.completed`、tail SHA
`1a4e3904ff6c828ccf3850691da0fed110a58e1b579e31eb2e824d073c0f518a`、lock free、token absent。

## Zero-activation final gate

- Services active/running；PID/NRestarts仍为 `836234/0`、`1276892/0`。
- P0 production mutation lock：`state=free, phase=free`。
- DB integrity/schema/FK：`ok / 13 / 0`；pending/running jobs `0`；active leases `0`。
- P9-3C1 workspace、host profile、agents、jobs、executor source/definition/binding、capacity
  source/policy均为 `0`。
- P9-3C1 loaded/transient unit、unit file与 controller/fixture process均为 `0`。
- Canonical projection hash两轮相同；deploy canonical parity为 zero delta。
- No authorization、lock token、paid provider call、job submission、claim/reap/report、fixture unit、
  canonical restart或 production controller mutation occurred。

## Retained failure evidence

此前失败证据不删除、不复用：

- argv forwarding failure：在 root创建前停止，run root absent；
- `p9-3c1-prod-20260716t062904z-90d00e16`：venv symlink authority failure root；
- `p9-3c1-prod-20260716t064920z-c2bee4d4`：旧双时钟 ledger sealed root，首次 read-only
  validation fail-closed且 tree hash不变。

Successful inert run同样保留为 sealed audit evidence。P3必须使用新的 run id与新 prepare，并继续需要
独立 authorization/review；本 P2 evidence不授权 `run` 或 `cleanup`。

## Independent deployed-evidence review

- KAT first-choice attempt在 provider/session init前停滞两分钟且没有 native JSONL，exit 130；不计为
  review。
- Exact `zhipu-coding-plan/glm-5.2` route产生 native 429，明确 quota reset
  `2026-07-17 16:50:49`；不计为 review。
- First DeepSeek attempt因 non-interactive `always-ask`拒绝所有 bash/SSH，无法验证 live evidence，
  exit 130；不计为 review。
- Fresh effective reviewer session `019f69d0-e674-7000-bd04-98a6cf6516f1`使用 native
  `provider=deepseek`、`model=deepseek-v4-pro`，只读检查 source/origin/deployed/install SHA、
  VERSION、service PID/NRestarts、lock、SQLite mode=ro、run tree、两轮额外 preflight/status、failure
  evidence、unit/process与 network smoke boundary。
- Reviewer初稿误把 `90d00e16`标为 argv failure；Operator未固化该错误。Same-session corrected addendum
  重新证明 argv run `37721127` root absent、`90d00e16`是 symlink forensic root、`c2bee4d4`是
  dual-clock sealed root；并用上方 exact formula复算得到
  `4dca4e1d2f3908ee4d6effdd7f5cfafcc2951dd854c0993198d74286b061c207`，关闭 INFO finding。
- Final corrected verdict：`APPROVE — P2 close authorized；P3 run/cleanup remains unauthorized`。
  Native JSONL SHA-256：
  `ed34445b72b3df3d958fa119a2a661cfabc06b68f0cc84b0cbc5e8f23cf35dae`。

## Closeout

P9-3C1 P2 已完成 reviewed implementation、三轮 installed fail-closed correction、merge/push、
`--no-restart` deployment、exact installed identity、fresh sealed prepare、双轮 read-only stability、
zero-activation final gate和 independent live review。P2 closed。

下一步是 P3 fresh measurement/detailed plan/independent plan review/bootstrap review。P3必须使用新的 run
id、fresh prepare和 separately reviewed authorization artifact；在这些 gate关闭前，production
`run`/`cleanup`、fixture catalog activation和 five-job live matrix仍未授权。

P9_3C1_P2_INERT_PRODUCTION_CONTROLLER_CLOSED
