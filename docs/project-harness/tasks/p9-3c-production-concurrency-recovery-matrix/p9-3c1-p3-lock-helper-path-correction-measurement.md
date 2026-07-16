# P9-3C1 P3 Lock Helper Path Correction — Measurement

状态：`MEASURED_CORRECTION_PLAN_REQUIRED_IMPLEMENTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

本文只记录首个 P3 live run 的已审核 failure evidence 与 source/runtime mismatch。它不授权
code change、deploy、fresh `prepare`、authorization install、controller `run/cleanup` 或 P0
`recover`。

## 1. Failed run identity and immutable evidence

- MultiNexus source/deployed：`1faf26066c5edaa5902f69a68cfb468fc6a4077a`。
- Coordinate deployed：`a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。
- Run id：`p9-3c1-prod-20260716t083723z-1faf2606`。
- Auth SHA：`a358e18e252857fe0238b07c3a6f82ca64b0deed1f4ecccb004aa10f5e078e48`。
- Manifest SHA：`84bd363b0d4277f0e40929f813082453b2fa78436fbfdc96196c6c1f4f6805b5`。
- Foreground exit：`1`；stdout empty；exact stderr：
  `production helper production-render failed (exit 1): p9-3c0-unit: installed lock helper path drift`。

The controller reached `baseline-captured+`，then its fixed failure path completed cleanup。The root、auth、
backup、ledger and review JSONL are immutable forensic evidence and must never be reused、repaired、deleted
or cleaned。

## 2. Independently reviewed terminal classification

Fresh KAT reviewer native JSONL：

```text
/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-failure-result-review-kat-coder-pro-v2.5/2026-07-16T09-12-53-560Z_019f6a33-4838-7000-b880-3ce2a58d5478.jsonl
```

- provider/model：`kat-coder/kat-coder-pro-v2.5`；
- JSONL SHA：`7fb16803b443b450a267cd70eeba1dece5cc968dcbed9da07d2cbb6e3a4e0360`；
- first non-empty verdict：`APPROVE`；`P0/P1/P2: none`；
- classification：`cleanup-completed failure`；do not call `cleanup` or P0 `recover`。

Reviewed state：

- phase `done`；13-record ledger；tail `cleanup.completed`；lock free；token absent；
- exact fixture units not found/inactive，zero P9 process/cgroup；
- canonical Coordinate/bridge PID/NRestarts unchanged at `836234/0` and `1276892/0`；
- DB `ok/13/0`；zero nonterminal/recoverable job、active lease、P9 job/lease；
- E1/E2 offline；workspace/profile and executor v4/capacity v2 sources retained as dormant audit；
- zero executor definition/binding/capacity policy executable state；
- no evidence of accepted stale mutation、duplicate resource lease、provider request or external delivery。

The prompt given to the reviewer contained a typo in the **local file hash** for
`post-failure-tree.sha256`。The reviewer independently recomputed the correct full SHA as
`37b38a3bb2026bd969e7a467c1d5b9ed6e822d23c3fa7c75cf45de866d2db3c6` and the file content still
records tree aggregate `855e116ab4de8be0f7ad989f3717ddbc3b0ee02fae73ea18b9659fc66ce26134`。

## 3. Exact source/runtime mismatch

The production authority has three agreeing sources：

- `scripts/p9_3c1_controller.py`：
  `PRODUCTION_LOCK_HELPER=/usr/local/sbin/coordinate-production-mutation-lock`；
- controller manifest `production_launcher_identity.lock_helper_path` is the real path of that constant；
- `scripts/deploy-server.sh` installs and verifies the helper only at
  `/usr/local/sbin/coordinate-production-mutation-lock`。

Remote read-only proof：the `/usr/local/sbin/...` ordinary executable exists；
`/opt/multinexus/scripts/production-mutation-lock.sh` does not exist。

But `multinexus/fixture/bin/p9-3c0-unit.sh` hard-codes：

```bash
P9C1_INSTALLED_LOCK_HELPER="/opt/multinexus/scripts/production-mutation-lock.sh"
```

`_p9c1_validate_lock_token` compares the manifest path with this stale constant before invoking status，
so `production-render` deterministically fails with `installed lock helper path drift`。

## 4. Why the existing suite passed

`tests/test_p9_3c0_package3_scripts.py` sources the production shell but overwrites
`P9C1_INSTALLED_LOCK_HELPER` with a temporary stub path that also populates the fake manifest。The helper
behavior is covered，but the shipped production constant is not。Controller tests similarly inject a fake
launcher identity。There is no cross-file source-level invariant tying shell、controller and deploy paths。

## 5. Correction boundary

The measured minimum is：

1. align the shell production constant to
   `/usr/local/sbin/coordinate-production-mutation-lock`；
2. add a regression invariant that fails if shell/controller/deploy production paths diverge；
3. retain a negative mismatch test proving fail-closed behavior；
4. run focused helper/controller/deploy tests and the full suite；
5. deploy the reviewed correction with no service restart，then use a completely fresh run id、prepare、
   reviews、nonce and auth chain。

No controller algorithm、schema、DB contract、phase machine、budget、lock protocol or cleanup behavior needs
redesign based on current evidence。The known P0 recover unit-prefix residual remains a separate package and
P0 recover stays forbidden here。

P9_3C1_P3_LOCK_HELPER_PATH_CORRECTION_MEASURED_IMPLEMENTATION_BLOCKED
