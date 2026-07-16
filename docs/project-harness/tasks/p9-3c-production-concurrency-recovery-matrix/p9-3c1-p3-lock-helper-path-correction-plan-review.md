# P9-3C1 P3 Lock Helper Path Correction — Plan Review

状态：`APPROVED_FOR_WORKER_BOOTSTRAP_ONLY`

日期：2026-07-16 Asia/Shanghai

## 1. Reviewed authority

- Plan commit：`33641e1e40482487e39add9b4c3fe5e36c119c03`。
- Measurement SHA：`09fac782b7e0e758df4aecdcf8b2b4a3ff134deb788b96d6069ced5a63d2dda1`。
- Plan SHA：`3c4f28386e2553102d887a170ea69f0bd8266b4b58f80f02ff8e45c4e69f602e`。
- Reviewer provider/model：`deepseek/deepseek-v4-pro`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-lock-helper-path-correction-plan-review-deepseek-v4-pro/2026-07-16T09-20-39-676Z_019f6a3a-64fc-7000-83a3-f46ceb12f036.jsonl`。
- Final JSONL SHA：`b00d43abc193ec9a85bad6a964fb59a1dd4498e184708fb9a0acf7d4a5093645`。
- Final exact receipt：`APPROVE`；`P0/P1/P2: none`。

This approval authorizes only generation and independent review of a Coding worker bootstrap。It does not
authorize implementation、merge/push、deploy、prepare、auth、run、cleanup or recover。

## 2. Approved findings

The reviewer independently confirmed：

- failed run terminal classification is `cleanup-completed failure`；
- controller and deploy agree on `/usr/local/sbin/coordinate-production-mutation-lock`；
- shell constant `/opt/multinexus/scripts/production-mutation-lock.sh` is stale and is the exact
  deterministic failure source；
- the minimum correction is one literal plus an unmodified-source cross-contract invariant and an exact
  path-mismatch fail-closed regression；
- no compatibility alias、second installed helper、controller redesign or recover action is acceptable；
- failed root/auth/backup/ledger/reviewer evidence remains immutable and any retry needs a fresh full chain。

## 3. INFO dispositions

1. **Optional shell `readlink -f` normalization — rejected for this package.** Controller manifest already
   seals `os.path.realpath` and deploy/identity validation requires an ordinary single-link installed file。
   Adding path normalization would widen the runtime change and obscure the exact literal mismatch。Worker
   must make only the approved literal correction。
2. **Invariant test location — resolved.** Worker may place the unmodified-source invariant in
   `tests/test_deploy_contract.py` or `tests/test_p9_3c0_package3_scripts.py`，but it must read all three
   shipped source constants without executing a test seam override。
3. **Stub override — retained only for behavior tests.** `_p9c1_helper_state` may continue overriding the
   helper path for temporary fake execution。A separate invariant test must prove the untouched production
   source literal；the worker must not remove dependency injection needed by unit tests。

P9_3C1_P3_LOCK_HELPER_PATH_CORRECTION_PLAN_APPROVED_FOR_WORKER_BOOTSTRAP_ONLY
