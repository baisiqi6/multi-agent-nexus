# P9-3C1 P2 Inert Production Controller — Fresh Measurement

状态：`MEASURED_DETAILED_PLAN_REQUIRED_NO_IMPLEMENTATION`

日期：2026-07-16 Asia/Shanghai

本文件是 source、test 与 production runtime 的只读测量。它不授权 coding、worker、commit、
push、deploy、service restart、catalog sync、workspace/agent/job creation、production DB write、
lease claim/reap/report、fixture unit start/stop 或 P9-3C1 live matrix。

## 1. Exact revisions and live boundary

- MultiNexus source/origin：`7cd1c049d3157a778d79a0a69981032b2c9b2a02`。
- MultiNexus deployed：`1b1d1fd1c5c160e3ede16ee2f07fb2989990e3c2`；这是 P0
  implementation projection，P1 closeout docs 尚未部署，不影响 runtime bytes。
- Coordinate source/origin/deployed：
  `a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。
- Production host：`VM-0-15-ubuntu`，SSH alias `kook-hermes-admin`。
- Production DB：`/var/lib/coordinate/coord.sqlite3`；schema `13`、
  `integrity_check=ok`、FK violations `0`。
- Global mutation lock：`state=free, phase=free`；installed helper SHA-256：
  `7dd71c31595c7135a8a75ef3d8e459788682f6a30272ea5bdeb66bb7c2a2ebd4`。
- Current production executable state：pending/running jobs `0`、active leases `0`；
  P9-3C/P9-3C1 agents、runner profiles、jobs、executor sources、capacity sources与 transient
  units均为 `0`。
- Canonical sources only：executor `multinexus.discord` v2，capacity
  `multinexus.discord.capacity` v1。
- Process identity：Coordinate PID `836234`，Discord bridge PID `1276892`，KOOK Hermes PID
  `4551`。`coordinate.service` 为 `active/running, NRestarts=0`。系统中
  `multinexus-kook-bridge.service` 显示 inactive，但真实 Discord bridge process 仍以 PID
  `1276892` 运行；P2/P3 不能把错误 unit name 当成 service identity evidence，必须同时使用
  exact process argv/PID 与实际受管 unit inventory。

P2 production boundary 只允许：部署 inert source/assets、不重启服务，以及对 fresh run id 执行
`prepare`、`preflight`、`status`。不得调用 `run`/`cleanup`，不得创建 Coordinate row 或启动
fixture unit。

## 2. Current MultiNexus test authority

Fresh focused base：

```bash
.venv/bin/python -m pytest -q \
  tests/test_agentd.py \
  tests/test_agentd_execution_lease.py \
  tests/test_p9_3c0_fixture_assets.py \
  tests/test_p9_3c0_package3_scripts.py \
  tests/test_deploy_contract.py \
  tests/test_production_mutation_lock.py
```

Result：`379 passed, 45 subtests passed`。

Fresh full base：

```text
953 passed, 2 skipped, 81 subtests passed
```

P2 candidate must add no failure/skip and must keep all P9-3C0 isolation, unit, cgroup, recovery and
deploy contracts green。P2-specific tests must be independently identifiable and pass without root、
systemd、production DB、network 或 provider credentials。

## 3. P1 claim policy propagation gap

Coordinate P1 now exposes：

```text
coordinate runtime job claim \
  --agent-id <id> \
  --reap-mode {global,none} \
  --reap-reason <reason>
```

Current MultiNexus `CoordinateRuntimeClient.claim_job()` still emits only `--agent-id` plus optional
recovery evidence。`AgentdWorker.run()` and `python -m multinexus.agentd` have no reap-policy input。
Therefore every current agentd claim still exercises Coordinate default `global`，including a future
P9-3C1 fixture recovery claim。

P2 must propagate the policy through all three layers while preserving the exact existing default：

```text
agentd CLI -> AgentdWorker.run() -> CoordinateRuntimeClient.claim_job()
```

- default remains `global` and should preserve legacy argv by omitting new flags；
- `none` requires one bounded、stripped-stable、control-character-free reason；
- `global + reason`、unknown mode、missing reason and partial combinations fail before config load、
  worker start or subprocess invocation；
- P9-3C1 normal and recovery units both use a controller-sealed `none` reason；
- recovery evidence remains a separate all-or-none contract and cannot substitute for reap reason。

Current `CoordinateRuntimeClient.reap_leases()` is an unused global helper outside tests。P9-3C1 must
not call it。P2 should not delete a public compatibility method merely to enforce a P9-3C1-specific
policy；the production controller must use exact P1 reap CLI arrays only。

## 4. P9-3C0 unit helper reuse boundary is insufficient as-is

The reviewed helper `multinexus/fixture/bin/p9-3c0-unit.sh` contains the required hardening：

- exact allowlist `p9-3c-fixture-e1/e2`；
- maximum two transient units；
- fixed cgroup/process stop authority；
- `KillMode=control-group`、network deny、credential denylist、unit identity checks；
- sealed static unit definition、post-start semantic verification、recovery evidence handling；
- exact status/stop/cleanup and ledger-bound cgroup proof。

Its current isolation contract also deliberately rejects every production path：

- `_p9c0_enforce_wrapper_authority()` rejects `/usr/local/bin/coord-local` and any resolved alias；
- it rejects `/var/lib/coordinate/coord.sqlite3` and requires DB containment under isolated state root；
- `render` repeats both hard refusals；
- wrapper ownership requires the isolated root/group/mode matrix，while live
  `/usr/local/bin/coord-local` is root:root `0755`；
- current agentd argv has no `--reap-mode none --reap-reason ...`。

This means “call P9-3C0 helper unchanged against production” is impossible and attempting to relax its
existing gates would regress P9-3C0 safety。P2 needs an explicit reviewed deviation：add a distinct
production-authorized path inside the same helper，sharing the existing sandbox/start/stop/cgroup
internals but leaving the existing `render/preflight/start` isolation path byte-for-byte semantic
compatible。It must not copy stop/cgroup logic into the Python controller or a second shell helper。

## 5. Catalog/config gap

Current fixture config is P9-3C0-only：

- source ids are `p9-3c0-fixture-executors` and `p9-3c0-fixture-capacity`；
- executor capability is `coding`；
- agent template uses isolated placeholders `__P9C0_*__`；
- no P9-3C1 config directory or installed controller exists。

P9-3C1 requires separate immutable assets：

- executor source `p9-3c1-fixture-executors` v1 disabled、v2 enabled、v3 disabled、v4 empty；
- capacity source `p9-3c1-fixture-capacity` v1 capacity-1 per agent、v2 empty；
- exact capability only `p9-3c1-fixture`；
- fixed agents remain `p9-3c-fixture-e1/e2` to match the reviewed helper allowlist；
- production agent template points only at the installed Coordinate CLI/DB and local zero-provider
  fixture binary；no Discord/KOOK/Webhook token or destination。

Preflight must parse both helper allowlist declarations and config assets，then prove exact set equality。
A grep-presence assertion is insufficient because an extra third agent or a near-match id would remain
dangerous。

## 6. Controller and state gap

There is no `p9-3c1-production-verify.sh`、`p9_3c1_controller.py`、P9-3C1 state root、phase
ledger、authorization manifest or controller test seam。P9-3C0 controller is a Bash controller for an
isolated DB and cannot be pointed at production。

P2 must provide a production-aware controller with these boundaries：

- thin root/run-id shell entrypoint，all orchestration in Python list argv with `shell=False`；
- `prepare` creates only a fresh sealed run directory、read-only baseline/backup evidence and immutable
  expected hashes；production DB is opened URI `mode=ro` only；
- `preflight` and `status` are truly read-only，including no phase/ledger timestamp update；
- `run` requires a separate exact P3 authorization artifact and holds the P0 global lock from before
  baseline mutation through final evidence fsync；
- `cleanup` is resume-only from a validated ledgered mutation phase and also requires the lock；
- forward phase file is atomic；ledger is O_APPEND、fsync’d、sequence-numbered and hash-chained；
- no skip-gate、skip-cleanup、allow-dirty、force-reuse、global-reap or whole-DB-restore option；
- all DB evidence uses allowlisted read-only queries；all mutations use reviewed Coordinate CLI arrays。

The parent state machine contains `preflight-ok` as a forward phase，but standalone `preflight` is
read-only。Therefore only a lock-held `run` may persist the `sealed -> preflight-ok` transition after it
reruns the same preflight gates；the inert `preflight` command returns JSON evidence without state
transition。

## 7. Deployment measurement

`scripts/deploy-server.sh multinexus --no-restart` already：

- acquires the shared P0 lock before staging/snapshot/source mutation；
- deploys the complete repository tree including new scripts and fixture assets；
- validates/restores canonical registry/capacity projection on failure；
- can finish without service restart；
- releases the lock only after checked cleanup。

No deploy-driver feature is required for P2。Adjacent deploy tests should prove the new assets are not
excluded and inert deployment does not execute the controller。P2 deploy still replays the unchanged
canonical sync contract；it must not sync P9-3C1 catalog assets。

## 8. Planning conclusion

P2 is one MultiNexus-only package because agentd reap-policy propagation、production unit authority、
catalog assets and controller state machine must agree on one sealed run contract。Splitting them would
create an installed controller whose worker claim path could still global-reap，or an agentd policy with
no production authority consumer。

Before implementation：write a detailed P2 plan with the explicit helper deviation，obtain fresh
independent plan approval，then generate and independently review an exact-SHA worker bootstrap。

P9_3C1_P2_MEASUREMENT_COMPLETE_IMPLEMENTATION_BLOCKED
