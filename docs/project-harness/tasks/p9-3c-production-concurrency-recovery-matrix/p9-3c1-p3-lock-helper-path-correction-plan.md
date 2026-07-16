# P9-3C1 P3 Lock Helper Path Correction — Detailed Plan

状态：`DETAILED_PLAN_READY_FOR_INDEPENDENT_REVIEW_IMPLEMENTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Outcome and authority boundary

Correct the single production lock-helper path mismatch exposed by the first P3 live run，add a durable
cross-contract regression test，deploy the reviewed bytes without restart，and return P3 to a completely
fresh prepare/review/auth/run chain。

This plan authorizes only independent plan review。It does not authorize implementation、merge/push、
deploy、fresh `prepare`、authorization creation/install、controller `run/cleanup`、P0 `recover` or any
manual production repair。

## 2. Fixed facts

- Base SHA：`1faf26066c5edaa5902f69a68cfb468fc6a4077a`。
- Failed run：`p9-3c1-prod-20260716t083723z-1faf2606`；immutable，never retry。
- Independent result review JSONL SHA：
  `7fb16803b443b450a267cd70eeba1dece5cc968dcbed9da07d2cbb6e3a4e0360`。
- Correct production path：`/usr/local/sbin/coordinate-production-mutation-lock`。
- Stale shell path：`/opt/multinexus/scripts/production-mutation-lock.sh`。
- P0 recover unit-prefix residual is not part of this correction；`recover` remains forbidden。

## 3. Artifact and review sequence

1. measurement + this detailed plan；
2. fresh independent plan review；
3. exact Coding worker bootstrap；
4. fresh independent bootstrap review；
5. KAT-Coder-Pro V2.5 Coding worker in an isolated branch/worktree；
6. Codex review + focused/full local gates；
7. fresh independent implementation result review；
8. merge/push exact correction；
9. no-restart deployment + production read-only verification；
10. fresh P3 run id、prepare、basis review、new nonce/auth、final auth review and one-shot run；
11. fresh post-run result review and durable dogfood/closeout sync。

A rejection at any review returns to the preceding artifact。No artifact silently authorizes a later
mutation gate。

## 4. Exact implementation scope

Allowed runtime change：

- `multinexus/fixture/bin/p9-3c0-unit.sh`：replace only the stale
  `P9C1_INSTALLED_LOCK_HELPER` literal with
  `/usr/local/sbin/coordinate-production-mutation-lock`。

Allowed test changes：

- add a source-level production invariant in the most relevant existing test module，proving the shell
  constant、controller `PRODUCTION_LOCK_HELPER` and deploy `LOCK_HELPER_REMOTE` all equal the exact
  production path；
- retain/add a focused negative test where manifest `lock_helper_path` differs from the effective shell
  helper and `production-render` fails with `installed lock helper path drift` before rendered authority or
  fixture unit creation；
- if a test helper currently hides the shipped constant，make that override explicit and ensure a separate
  test reads the unmodified source constant。

Forbidden changes：controller phase/budget/authorization/cleanup logic、Coordinate code、schema/DB、deploy
destination semantics、new symlink/compatibility file at the stale path、service definitions、fixture timing、
P0 recover behavior or unrelated refactor。

Do not “fix” this by installing a second helper at `/opt/multinexus/...`。The single source of runtime
authority remains the root-owned deploy target under `/usr/local/sbin`。

## 5. Test design and acceptance

Required focused gates：

```bash
bash -n multinexus/fixture/bin/p9-3c0-unit.sh
python3 -m pytest -q tests/test_p9_3c0_package3_scripts.py
python3 -m pytest -q tests/test_p9_3c1_production_controller.py
python3 -m pytest -q tests/test_deploy_contract.py
```

Then run the repository's canonical full gate from a clean worker checkout。Acceptance requires：

- the new invariant would fail on base SHA `1faf260...` and pass only after correction；
- existing fail-closed mismatch behavior still passes；
- no skipped/newly xfailed regression hiding the production literal；
- `git diff --check` clean；
- only the exact runtime/test files plus reviewed task docs change；
- no access to user-owned `sessions/` data and no production/network/deploy action by the worker。

## 6. Worker bootstrap requirements

After plan approval，the bootstrap must pin：base SHA、allowed files、forbidden files、exact literal、test
commands、commit requirement and native JSONL evidence。KAT-Coder-Pro V2.5 is first Coding worker choice；
provider/model must be verified from native JSONL。Worker receives no SSH、deploy、production DB or
credentials authority。

The worker must commit its changes on an isolated branch and report commit SHA、diff、tests and assumptions。
Codex independently reviews every changed line and reruns proportional gates。

## 7. Result review and merge gate

A fresh non-Codex result reviewer must verify：

- exact production path agreement across shell/controller/deploy；
- negative fail-closed behavior remains intact；
- no compatibility alias or duplicated helper authority was introduced；
- focused/full test evidence and native worker JSONL are valid；
- diff stays inside scope。

Only `APPROVE` with P0/P1/P2 none opens fast-forward merge/push。Any correction to code after review requires
new tests and a new result-review round。

## 8. Deployment gate

Deploy exact reviewed main SHA using the canonical MultiNexus deployment path with `--no-restart`。Before
and after deploy require：

- P0 lock free；failed P3 root remains immutable；
- canonical services active/running with PID/NRestarts unchanged；
- DB `ok/13/0`，zero nonterminal/recoverable job and active/due lease；
- zero P9 executable state；dormant audit rows from the failed run remain；
- installed shell helper hash equals reviewed source；installed mutation lock helper remains the single
  root-owned `/usr/local/sbin/...` authority；stale `/opt/multinexus/...sh` remains absent；
- bounded smoke passes or is classified with exact time boundary without restart/override。

Do not mutate or remove the failed root/auth/backup/reviewer artifacts。

## 9. Fresh P3 retry boundary

The correction does not make the failed root resumable。A later one-shot P3 attempt must use：

- fresh run id derived from the new deployed SHA；
- fresh prepare and double stable read-only packet；
- fresh basis live-preflight review JSONL；
- fresh nonce、auth bytes/SHA and final exact-auth review；
- at least 50 minutes TTL at install and immediate pre-run gates；
- exactly one foreground controller and separate read-only monitoring。

The existing P3 live-matrix plan/bootstrap remains the operational contract except where a new exact SHA/
run identity is required。If another runtime mismatch appears，retain the new root and return through a new
reviewed correction package；never stack ad-hoc server repair onto the run。

## 10. Closeout

P3 closes only after a fresh corrected run reaches the existing success gate and a fresh independent live
review returns `APPROVE`。Then update deployment dogfood、progress、dogfood feedback、roadmap and Phase 9
status with both the failed forensic run and the successful replacement run。

P9_3C1_P3_LOCK_HELPER_PATH_CORRECTION_PLAN_READY_FOR_INDEPENDENT_REVIEW_IMPLEMENTATION_BLOCKED
