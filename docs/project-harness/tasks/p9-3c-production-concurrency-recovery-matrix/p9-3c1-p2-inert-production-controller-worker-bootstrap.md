# P9-3C1 P2 Inert Production Controller — Worker Bootstrap

状态：`DRAFT_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_WORKER_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Exact approved authorities

Worker must read these files completely before any repo write：

1. `p9-3c1-p2-inert-production-controller-measurement.md`
2. `p9-3c1-p2-inert-production-controller-plan.md`
3. `p9-3c1-p2-inert-production-controller-plan-review-round1.md`
4. `p9-3c1-p2-inert-production-controller-plan-review-round2.md`
5. parent `p9-3c1-production-plan.md`

Exact authorities：

- MultiNexus base：`7cd1c049d3157a778d79a0a69981032b2c9b2a02`；
- approved plan SHA-256：
  `7c78a2609435751add2a7aeba94d089921239d6a83ac424792230644a7110f00`；
- measurement SHA-256：
  `103791a22f66a1f927e40347eacf60fa369c5537f81108f098e18faea84a6d87`；
- Round 2 verdict：P0/P1/P2/residual risks all `None`；
- deployed Coordinate reference：
  `a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。

If any SHA/base/path differs，stop before write and report `BOOTSTRAP_AUTHORITY_MISMATCH`。

## 2. Exact branch/worktree and route

- Required branch：`agents/fallback/p9-3c1-p2-inert-production-controller`。
- Required worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p2-inert-production-controller`。
- Branch must start exactly at base `7cd1c049...` and be clean before the first write。
- Do not modify the planning worktree or `/Users/yinxin/projects/multinexus` main worktree。

Claude Code `--model sonnet` was attempted for the preceding independent review and its native Kimi
route returned quota `403` before tool/write。Evidence SHA-256：
`e03cac42f1d36472bfa22fae0c2c730bdb1b131f9f272fa0e9c4a61d52b17ef5`。
Therefore this bootstrap explicitly selects fallback Coding worker：

```text
provider/model = deepseek/deepseek-v4-pro
thinking = high
```

Worker native JSONL must contain exact `model_change` plus assistant message provider/model evidence。
No Codex、Kimi、GLM、Opus or silent provider switch。If DeepSeek fails by explicit quota/auth/transport
before any repo write，stop；operator may authorize a fresh MiniMax M3 session。Do not reuse a partially
writing session under a different model。No subagents。

## 3. Role and authorization

You are Coding worker，not architect、reviewer、operator or production runner。Authorized：

- read current source/tests/docs；
- edit exact allowlisted files in the isolated worktree；
- run local tests、shell syntax、compile and Git read-only commands；
- create exactly one local implementation commit after all gates pass。

Forbidden：

- push、merge、rebase、deploy、SSH、service/systemd mutation、sudo；
- production DB/file access or any `/var/lib`、`/run/lock`、`/opt` write；
- real `prepare/preflight/status/run/cleanup` against production；
- real fixture unit/process/cgroup start/stop/crash；
- catalog/workspace/agent/job/lease/delivery mutation outside temp fakes；
- global reap、direct SQL production write、external bus/provider/network credential use；
- modifying docs outside the one allowlisted runbook；
- weakening/skipping/deleting tests、changing baseline to fit output、using destructive Git。

If the approved contract is impossible within allowlist，stop and produce an exact deviation report；do
not invent a smaller implementation or compatibility shim。

## 4. Exact file allowlist

Only these 20 paths may differ from base：

1. `multinexus/agentd/coordinate_client.py`
2. `multinexus/agentd/worker.py`
3. `multinexus/agentd/__main__.py`
4. `multinexus/fixture/bin/p9-3c0-unit.sh`
5. `scripts/p9-3c1-production-verify.sh`
6. `scripts/p9_3c1_controller.py`
7. `multinexus/fixture/config/p9-3c1/agents.production.toml`
8. `multinexus/fixture/config/p9-3c1/executor.v1-disabled.toml`
9. `multinexus/fixture/config/p9-3c1/executor.v2-enabled.toml`
10. `multinexus/fixture/config/p9-3c1/executor.v3-disabled.toml`
11. `multinexus/fixture/config/p9-3c1/executor.v4-empty.toml`
12. `multinexus/fixture/config/p9-3c1/capacity.v1.toml`
13. `multinexus/fixture/config/p9-3c1/capacity.v2-empty.toml`
14. `tests/test_agentd.py`
15. `tests/test_agentd_execution_lease.py`
16. `tests/test_p9_3c0_fixture_assets.py`
17. `tests/test_p9_3c0_package3_scripts.py`
18. `tests/test_p9_3c1_production_controller.py`
19. `tests/test_deploy_contract.py`
20. `multinexus/fixture/docs/runbook.md`

New shell entrypoint and existing helper remain executable。New Python/config/tests/docs are regular
non-executable files。Do not change `scripts/deploy-server.sh`、P0 helper、P9-3C0 controller/cleanup、
canonical config、dependencies or packaging。

## 5. Agentd reap policy implementation

Implement shared `normalize_claim_reap_policy()` in `coordinate_client.py`：

- exact `global|none` only；
- `global` accepts only `None` and returns `("global", None)`；
- `none` requires `str`、nonblank、stripped-stable、no C0/DEL、<=512 code points and <=2048 UTF-8
  bytes；
- bool/non-string/unknown/empty reason fail before environment/subprocess；
- do not alter `normalize_recovery_reason()`。

Extend `CoordinateRuntimeClient.claim_job()`、`AgentdWorker.run()` and agentd CLI：

- defaults `global/None` preserve existing argv exactly and omit both Coordinate flags；
- `none` appends exact ordered `--reap-mode none --reap-reason <canonical-reason>`；
- worker validates once before `_running=True` and passes exact policy on every poll；
- CLI validates before config load；
- normal and recoverable both support policy；recovery evidence remains separate all-or-none；
- no change to renewal、lease-loss、report or queue-blocker behavior。

Tests must prove default exact compatibility、none argv、all invalid pairs zero call、repeated poll、
normal/recovery forwarding and pre-config CLI failure。

## 6. Exact immutable configs

Create seven static TOML files：

- executor source `p9-3c1-fixture-executors` v1 disabled、v2 enabled、v3 disabled、v4 empty；
- capacity source `p9-3c1-fixture-capacity` v1 E1/E2 each 1、v2 empty；
- one definition `p9-3c1-local-fixture` with provider `local-fixture`、adapter `claude`、capability
  exact singleton `p9-3c1-fixture`；
- fixed agents/runner ids `p9-3c-fixture-e1/e2` only；
- no `coding`/`review` capability、real Discord id/destination/token/provider/model；
- agent template has `agentd_mode=true`、installed fixture binary、production CLI/DB and distinct
  run-rooted work/context placeholders；all markers exact `__P9C1_*__`。

Use real authority/config parsers in tests。Controller and helper independently parse both
`P9C0_AGENT_ALLOWLIST` declarations and config agent set；require exact set equality。Reject duplicate、
extra、near-match、wrong source/version/capability and any `__P9C0_*__` marker。

## 7. Helper production subcommands

Add distinct dispatch only；do not weaken old `render/preflight/start` and their production refusal：

```text
production-render \
  --state-root <root> --run-id <id> \
  --controller-manifest <path> --controller-manifest-sha256 <sha> \
  --lock-token-file <path>

production-preflight|production-status \
  --state-root <root> --run-id <id> \
  --controller-manifest <path> --controller-manifest-sha256 <sha> \
  --agent-id <E1|E2>

production-start \
  --state-root <root> --run-id <id> \
  --controller-manifest <path> --controller-manifest-sha256 <sha> \
  --lock-token-file <path> --agent-id <E1|E2> --mode <complete|hold> \
  [--recoverable --recovery-reason <reason> --prior-process-stopped]

production-stop|production-cleanup \
  --state-root <root> --run-id <id> \
  --controller-manifest <path> --controller-manifest-sha256 <sha> \
  --lock-token-file <path> --agent-id <E1|E2>
```

Unknown/duplicate option fails before write。Production-render accepts no wrapper/DB/fixture/Python/
repo/work/user/group/template/reap/hash override；all come from exact canonical controller manifest。
Mutation paths validate root EUID、single-link root-owned mode-0600 manifest/token files、manifest SHA、
exact held P0 token and expected owner/action/run。Read-only production preflight/status do not accept
token and write nothing。

Reuse/factor current unit-name、definition、systemd property、post-start、ledger unit、cgroup stop and
cleanup code。Do not copy process/cgroup logic into Python or a new helper。Sandbox remains at least
P9-3C0 strict。Normal/recovery argv always include sealed `none` policy；recovery is hold-only with all
three evidence flags。Two-unit budget spans primary/recovery suffixes。

P9-3C0 `wrapper.manifest` remains isolated-only。P9-3C1 uses controller-manifest object
`production_launcher_identity` and rejects a wrapper-manifest line as controller manifest。Regression
tests prove every old production refusal and argv contract remains。

## 8. Controller state/evidence primitives

Implement fixed root `/var/tmp/multinexus-p9-3c1/<run-id>` and exact run-id regex from plan。Use
dependency-injected seams for tests，production constants cannot be environment-overridden。

Implement：

- safe canonical path/type/owner/mode/nlink validation；
- canonical JSON and SHA helpers；
- O_APPEND/O_NOFOLLOW hash-chained ledger with seq/prev/record SHA and fsync；
- atomic phase temp+fsync+replace+dir-fsync，phase/tail exact agreement；
- root/control/ledger/backup and coord/runtime ownership matrix；
- read-only SQLite URI/query-only/authorizer evidence connection；
- allowlisted explicit-column queries only；
- bounded `shell=False` command runner with list argv、env whitelist、timeout/output cap；
- online read-only SQLite backup，mode 0600 and source/hash/freshness evidence；
- exact controller manifest with `production_launcher_identity`、revisions/hashes、ids、paths、config/
  helper sets、claim policy、budgets、canonical projection and absent P3 authorization digest slot。

Ledger/phase short-write/fsync/replace/corruption/sequence/tail mismatch must fail closed。Read-only
preflight/status tests compare state-tree bytes before/after。

## 9. Controller commands and P3 fence

Thin `p9-3c1-production-verify.sh`：EUID/fixed paths/run-id only，then `exec` installed Python with
original argv；no source mode、eval or env override。

Implement：

- `prepare --run-id ... --unit-user coord --unit-group coord`：fresh-only，double-read free-lock and
  revision/hash stability，read-only DB evidence/backup，sealed phase+ledger；zero Coordinate/unit
  mutation and no authorization file；
- `preflight --run-id ...`：fully read-only exact revision/hash/lock/DB/canonical/absence/service/
  helper/config/backup/CLI gates，canonical JSON stdout；
- `status --run-id ...`：fully read-only bounded authority summary；
- `run --run-id ... --authorization-file ... --authorization-sha256 ...`：requires external P3
  root-owned 0600 canonical artifact binding exact run/manifest/revisions/plan+review SHA/verdict/budgets/
  expiry/nonce，copies after validation，acquires/holds P0 lock，reruns gates and state machine；
- `cleanup --run-id ...`：only validated `workspace-ready+` non-done ledger，lock-held resume cleanup；
  sealed inert run cannot cleanup/mutate production。

Handled failure after lock but before first production mutation：fsync `preactivation-failed` evidence，
prove no workspace/agent/catalog/job/unit mutation，release own exact token。Crash/uncertain authority
leaves lock held for P0 reviewed recover only；never age/auto unlock。

## 10. State machine and command authority

Implement exact 18 phases from approved plan，one bounded mutation/readback/ledger/phase transition at a
time。Never infer success from directory/DB state without prior exact ledger command/idempotency proof。

Only construct allowlisted command families：workspace add/host-profile set；exact E1/E2 agent register/
heartbeat/deactivate；executor v1-v4/capacity v1-v2 sync；five exact-target requests with stdout reply；
controller negative claim always none；exact progress/report/renew；exact lease+job reap only；exact
delivery send/readback。No routed request、global batch reap、external platform or direct SQLite write。

Implement parent five-job matrix and fixed cleanup semantics in controller；P2 tests exercise it only via
temp DB/fake system。J1/J2 capacity sequential，J3 hold/crash/exact expiry-reap/N+1 hold recovery/stale
progress-report-renew rejection/current empty-result report，J4 distinct-work overlap，J5 same-worktree
block then completion。Required renewals >=2，exact five jobs、two units、zero provider/network/external
message。Failure freezes intake and enters only valid cleanup suffix。

Canonical projection hash uses explicit ordered columns for canonical executor/definitions/bindings、
capacity/policies、roster source/effective entries and `discord-nexus` workspace/host；fixture/P9-3C1
sets remain separate。

## 11. Mandatory tests and local gates

Implement every dynamic test in approved plan §12，including：

- agentd policy compatibility/invalid/normal/recovery；
- all seven configs through real parsers/cross-set failures；
- old helper isolation regression + new production authority/lock/reap policy/shared cgroup behavior；
- prepare/path/permissions/fresh-only/forensic failure；
- ledger/phase atomic corruption/fsync/short-write；
- read-only state-tree/SQLite mutation denial；
- authorization and P0 lock every failure branch；
- every phase/resume/crash point/cleanup suffix；
- exact command arrays/env/timeout/output/forbidden command unconstructability；
- canonical drift、budgets、unrelated due sentinel、five-job trace；
- staged **and installed fake tree** contains every exact new asset，deploy never invokes controller。

Before write，record base full and the approved measurement focused command，which omits the not-yet-
existing `tests/test_p9_3c1_production_controller.py` and must reproduce
`379 passed, 45 subtests`。Do not add an empty placeholder merely to make a base command resolve。
Candidate final gates：

```bash
.venv/bin/python -m pytest -q \
  tests/test_agentd.py \
  tests/test_agentd_execution_lease.py \
  tests/test_p9_3c0_fixture_assets.py \
  tests/test_p9_3c0_package3_scripts.py \
  tests/test_p9_3c1_production_controller.py \
  tests/test_deploy_contract.py \
  tests/test_production_mutation_lock.py

.venv/bin/python -m pytest -q
bash -n scripts/p9-3c1-production-verify.sh
bash -n multinexus/fixture/bin/p9-3c0-unit.sh
.venv/bin/python -m py_compile scripts/p9_3c1_controller.py
git diff --check
```

Base focused：`379 passed, 45 subtests`。Base full：
`953 passed, 2 skipped, 81 subtests`。Candidate may increase pass/subtest counts，must add no failure/
skip。Do not claim full gate without exact terminal output。

## 12. Commit and handoff

After all gates：

1. `git status --short` contains only allowlisted paths；
2. inspect full diff and remove temp/cache/session artifacts；
3. create exactly one commit：
   `feat(p9-3c1): add inert production controller`；
4. do not amend after reporting commit；if correction needed，operator will issue a new reviewed round；
5. do not push。

Final response must include：

- actual native session/provider/model evidence path；
- base/candidate SHA、commit and exact file list/modes；
- focused/full/syntax/compile/diff outputs；
- implementation map for sections 5-10；
- known residuals/deviations（`None` if none）；
- explicit statement that no SSH/deploy/production `prepare/preflight/status/run/cleanup` occurred。

P9_3C1_P2_WORKER_BOOTSTRAP_READY_FOR_INDEPENDENT_REVIEW_WORKER_BLOCKED
