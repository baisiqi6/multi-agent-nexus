# P9-3C1 P3 Lock Helper Path Correction — Coding Worker Bootstrap

状态：`DRAFT_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_WORKER_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Role and exact authority

You are the Coding worker only。You are not architect、reviewer、operator or production runner。Before any
write，read completely：

1. `p9-3c1-p3-lock-helper-path-correction-measurement.md`；
2. `p9-3c1-p3-lock-helper-path-correction-plan.md`；
3. `p9-3c1-p3-lock-helper-path-correction-plan-review.md`；
4. this bootstrap；
5. existing `p9-3c1-p3-live-matrix-plan.md` failure/incident sections。

Exact approved authorities：

- implementation ancestor：`33641e1e40482487e39add9b4c3fe5e36c119c03`；
- measurement SHA：`09fac782b7e0e758df4aecdcf8b2b4a3ff134deb788b96d6069ced5a63d2dda1`；
- plan SHA：`3c4f28386e2553102d887a170ea69f0bd8266b4b58f80f02ff8e45c4e69f602e`；
- plan-review JSONL SHA：`b00d43abc193ec9a85bad6a964fb59a1dd4498e184708fb9a0acf7d4a5093645`；
- failed immutable run：`p9-3c1-prod-20260716t083723z-1faf2606`；never access、reuse or mutate it。

The operator launch prompt must supply the exact docs-only commit containing this bootstrap as
`WORKER_BASE_SHA`。Before writing，require `HEAD == WORKER_BASE_SHA`，tracked status empty，and
`git diff --quiet 33641e1e..$WORKER_BASE_SHA -- multinexus scripts tests config agents.toml`。This proves
that only reviewed docs were added after the implementation ancestor。If any authority differs，stop with
`BOOTSTRAP_AUTHORITY_MISMATCH`。

## 2. Worker route and evidence

First choice：

```text
provider/model = kat-coder/kat-coder-pro-v2.5
```

Use one fresh OMP session in an isolated worktree/branch supplied by the operator。No silent model switch、
resume from another model、subagent or task delegation。Native JSONL must contain exact `model_change` and
assistant provider/model evidence。If KAT quota/auth/transport fails before write，stop and preserve JSONL；
fallback requires a new operator-selected session under the approved order。

## 3. Exact permissions

Authorized：read repo/source/tests/docs；edit only the allowlist；run local tests and Git read-only checks；
create exactly one local implementation commit after all gates pass。

Forbidden：

- SSH/network、deploy、push、merge、rebase、sudo、systemd/service/process operations；
- production DB、`/var/lib`、`/opt` or failed run/session evidence access；
- `prepare/preflight/status/run/cleanup/recover` against production；
- direct DB mutation、catalog/job/lease/delivery mutation、provider/external request；
- compatibility symlink、second helper install path or edits to deploy destination semantics；
- weakening/skipping/removing tests、adding xfail/skip、unrelated refactor or destructive Git；
- editing planning/dogfood/roadmap docs。

## 4. Exact file allowlist

Only these paths may differ from `WORKER_BASE_SHA`：

1. `multinexus/fixture/bin/p9-3c0-unit.sh`；
2. `tests/test_p9_3c0_package3_scripts.py`；
3. `tests/test_deploy_contract.py`。

No other runtime、test、config or doc file may change。The shell helper must retain executable mode；tests
remain ordinary non-executable files。If the correction cannot be completed inside this allowlist，stop and
report an exact deviation；do not widen scope yourself。

## 5. Required runtime correction

Make exactly this production literal change：

```diff
-P9C1_INSTALLED_LOCK_HELPER="/opt/multinexus/scripts/production-mutation-lock.sh"
+P9C1_INSTALLED_LOCK_HELPER="/usr/local/sbin/coordinate-production-mutation-lock"
```

Do not add `readlink -f` normalization、environment override、fallback path、symlink、wrapper or duplicate
helper。Do not alter `_p9c1_validate_lock_token` comparison/status semantics。It must still fail closed if
manifest and effective helper paths differ。

## 6. Required regression coverage

Add both：

1. **Unmodified-source invariant**：read the shipped shell、controller and deploy sources without sourcing
   the test prelude that overrides `P9C1_INSTALLED_LOCK_HELPER`。Assert exact equality of：
   - shell `P9C1_INSTALLED_LOCK_HELPER`；
   - controller `PRODUCTION_LOCK_HELPER`；
   - deploy `LOCK_HELPER_REMOTE`；
   - exact `/usr/local/sbin/coordinate-production-mutation-lock`。
   The test must fail on ancestor `33641e1e...` and pass after the literal correction。
2. **Exact negative path mismatch**：using the existing isolated shell fake，set the manifest
   `production_launcher_identity.lock_helper_path` and effective shell constant to different values，run
   `production-render`，and require nonzero plus exact `installed lock helper path drift`。Also prove no
   `helper-events.log`、rendered agents config or fixture unit authority was created。

Do not confuse the existing `LOCK_MISMATCH=1` token/owner rejection with the required **path** mismatch。
Keep the temporary stub override for other helper behavior tests。

## 7. Required local gates

Run in this order：

```bash
bash -n multinexus/fixture/bin/p9-3c0-unit.sh
python3 -m pytest -q tests/test_p9_3c0_package3_scripts.py
python3 -m pytest -q tests/test_p9_3c1_production_controller.py
python3 -m pytest -q tests/test_deploy_contract.py
python3 -m pytest -q
git diff --check
```

If the repo canonical full gate has additional documented subtests，run it too。No test may touch production
or network。Record exact pass/skip/subtest counts and command exits。

Before commit：

```bash
git status --short
git diff --name-only "$WORKER_BASE_SHA"..HEAD
git diff --check
```

Because `HEAD` does not include uncommitted changes，also inspect `git diff --name-only` and staged diff。
Require all changed paths inside the allowlist and no mode drift except preserved shell `0755`。

## 8. Commit and handoff

After all gates pass，create exactly one commit with a concise message such as：

```text
fix(p9-3c1): align production lock helper path
```

Return：branch/worktree、`WORKER_BASE_SHA`、implementation commit SHA、native JSONL path、provider/model、
exact diff summary、test commands/counts、any INFO。Do not push or merge。

The worker commit does not authorize deploy or a live retry。Codex review plus a fresh independent result
review are required before merge/push。

P9_3C1_P3_LOCK_HELPER_PATH_CORRECTION_BOOTSTRAP_READY_FOR_INDEPENDENT_REVIEW_WORKER_BLOCKED
