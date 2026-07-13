# P9-3A Ordinary Kimi Coding Worker Bootstrap

你是 P9-3A coding worker，不是 architect、plan reviewer、operator、result reviewer 或
deployer。只在下列两个隔离 worktree 中实现、测试并分别 commit；不要 push、merge、
deploy、SSH、访问生产 DB、重启服务、执行 harness repair/review/receipt/mark-done，
不要修改主 checkout，也不要启动 subagent。

本文件覆盖 Coordinate `worker.handoff.prepared` 事件中的通用 bootstrap 冲突项。可以通过
Coordinate 接受 assignment 和发送有界 progress/done report，但不得执行 closeout 或生产
操作。

## Immutable authority

- Approved plan:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3a-kimi/docs/project-harness/tasks/p9-3a-capacity-resource-lease-foundation/plan.md`
- Exact approved plan SHA-256:
  `77f467f1d9555552b236f0958d0f08fd267f3cb8193ab83541580de8f0ab7c0f`.
- Final independent approval:
  `plan-review-round3.md`, ordinary Kimi session
  `019f5c4d-8aa6-7000-a928-b262cb779e0b`, must-fix none, should-fix none.
- Durable `plan.ready`: `80b2c163-8108-407a-ac52-294ac80fffe3`.
- Durable `plan.approved`: `c9c338b3-2947-4936-8a4f-b9e4143b89d3`.
- Durable handoff: `c5aa80a4-d920-4315-a74e-b83c3ec868a7`.
- Coordinate code start:
  `90783b2c77933287ba163c4bb598f4a862e8b416`.
- MultiNexus implementation-code start:
  `ccb2b6aee4c66903ebabae2451c657cf815c36ab`; later commits through the worker
  worktree start are reviewed plan/checklist/bootstrap documentation only.

开始前完整阅读两个 repo 的 `CLAUDE.md`（如存在）、`plan.md`、`measurement.md`、
`plan-review-round3.md` 和 `plan-approval.md`；重新计算 plan SHA，确认 worktree 路径、
branch 和 HEAD。任何不一致立即停止并报告，不要自行换 baseline、改 plan 或扩大范围。

本任务必须使用普通 `Kimi for Coding`：`kimi-code/kimi-for-coding`。不得切换到
`kimi-for-coding-highspeed`。模型切换只由 operator 决定。

## Isolated worktrees

- Coordinate:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3a-kimi`
- Coordinate branch:
  `agents/mac-omp/p9-3a-capacity-resource-lease-foundation-coordinate`
- MultiNexus:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3a-kimi`
- MultiNexus branch:
  `agents/mac-omp/p9-3a-capacity-resource-lease-foundation`

只允许在这两个路径内写文件。主 checkout
`/Users/yinxin/projects/coordinate` 与 `/Users/yinxin/projects/multinexus` 只读；不得触碰
Coordinate 主 checkout 中用户所有的 `.qoder/`。

## Implementation contract

完整落实 approved plan Stage A-D 的本地实现与测试部分。不可协商边界：

1. capacity 是 `config/agent-registry.toml` 中独立 versioned projection，不进入 P9-2A
   executor/roster canonical bytes。当前全部 enabled typed instances capacity=1；external/
   untyped 不得被错误纳入。
2. Coordinate 新建 focused modules `executor_capacity.py`、`execution_resources.py`、
   `execution_leases.py`；MultiNexus 新建 `executor_capacity_authority.py`。不要把新逻辑塞进
   `runtime.py` 或继续膨胀 `registry_authority.py`。
3. Schema v13、table/check/index/FK 必须严格符合 plan。capacity policy 不 FK 到
   replace-style executor binding；lease 只 FK 到 stable jobs/agents/runner profiles，
   capacity policy id 是历史 snapshot。
4. path normalization 必须是 host-scoped lexical contract：POSIX 与 Windows drive/UNC
   规则、NFC/casefold、reject bounds 必须精确；禁止 `realpath`、filesystem probe、symlink/
   junction/network inference 或 cwd/env 依赖。
5. lease reserve/renew/release/expire 都由 caller-owned transaction 驱动，不 hidden commit。
   reserve 的到期处理只覆盖 target agent OR target resource；initial/renew TTL 都是 integer
   30..600，boolean/out-of-range zero-write。
6. two-connection `BEGIN IMMEDIATE` race、partial unique active resource index、capacity count、
   exact replay/conflicting replay 和 newer-attempt safety 都必须有测试，不能只测单连接 happy
   path。
7. capacity sync 是 atomic/version-monotonic/same-version-conflict-rejecting/complete-coverage
   validating。policy-id canonical object 与跨仓 fixture 必须 byte-identical。
8. deploy script/parity/smoke 只实现计划规定的 guarded capacity stage 和 fault-injection
   contract；worker 不实际部署。跨 sync failure 不得写 version/restart/success，必须能恢复
   previous accepted projection。
9. P9-2A executor catalog hash、binding ids、roster hash与 exact/routed behavior 必须保持不变。
   capacity roots只被旧 parser 显式 allow/ignore，不得偷偷加入 identity hash。
10. 严禁 P9-3B/P9-4 泄漏：不修改 runtime claim/report/progress；不增加 managed lease token、
    heartbeat、job reap/recovery、provider cancellation/session observation；不改 MultiNexus
    agentd/client/adapter/provider behavior。

如果实现证明需要修改 `runtime.py`、agentd/provider、P9-2 identity bytes、生产数据，或需要
超出 approved modules/contract，立即以 `blocked_scope_expansion` 报告，不要静默扩张。

## Allowed change surface

Coordinate expected:

- new `src/coordinate/executor_capacity.py`;
- new `src/coordinate/execution_resources.py`;
- new `src/coordinate/execution_leases.py`;
- focused `schema.py`, `executor_identity.py`, `execution_cli.py`, root composition edits;
- focused fixtures/tests for capacity, resource, lease, migration, CLI and unchanged identity.

MultiNexus expected:

- new `multinexus/executor_capacity_authority.py`;
- `config/agent-registry.toml` plus capacity fixture;
- minimal `registry_authority.py` allow/ignore edit;
- deploy verification/sync/smoke scripts and focused tests;
- `implementation-report.md` in this task directory.

No unrelated refactor, dependency/framework addition, production config/secret edit, broad formatting,
or cleanup of user files is allowed.

## Required verification

至少运行并记录精确命令、counts 与失败详情：

- Coordinate focused capacity/resource/lease/schema/CLI/identity tests；
- SQLite two-connection race and migration rollback/tamper/replay tests；
- Coordinate existing exact/routed runtime compatibility suites；
- Coordinate full suite，逐项比对 accepted baseline 的 2,156 passed + exactly nine historical
  CLI-fixture/AST failures；不得把新增失败写成 “known”；
- MultiNexus capacity authority/deploy/smoke/registry focused tests；
- MultiNexus full suite，基线 503 passed, 2 skipped；
- both `compileall`、`git diff --check`、changed-file scope；
- cross-repo canonical fixture/hash/policy ids exact parity；
- unchanged P9-2 catalog hash
  `f4cdf79897755c173e97ddae1dfd88047436039f3447d4d6257105715ba5551d`
  and binding ids/roster bytes；
- static search proving no `runtime.py` claim/report/progress and no agentd/provider/session behavior
  changes；
- deploy fault injection proving no version/restart/success before complete capacity parity and previous
  projection restoration。

可以复用主 checkout 的 Python/venv 执行器，但必须显式设置 worktree `PYTHONPATH`，避免误测
主 checkout。不要为了追绿放宽测试或修改历史 baseline expectation。

## Assignment and observation

启动后可通过 `/Users/yinxin/.local/bin/coord-ssh assignment accept` 接受本任务，owner 使用
`mac-omp`，session 使用本次 OMP session id。只发送有界 start/milestone/done report，
不得把私有 reasoning 发到 Discord。operator 将用 provider JSONL、进程、git diff/commits、
tests 与 Coordinate events 交叉判断状态；quiet diff 不等于 inactive。

## Commit and final report

验证完成后，在有改动的两个 repo 分别创建清晰 commit，不 push。MultiNexus 必须提交
`implementation-report.md`，记录准确测试、cross-repo evidence、未部署声明和残余风险。

最终返回：

```text
status=implemented|blocked
model=kimi-code/kimi-for-coding
plan_sha256=<exact>
coordinate_start=<sha>
coordinate_commit=<sha or none>
multinexus_start=<sha>
multinexus_commit=<sha or none>
files_changed=<per repo>
tests=<exact commands and counts>
historical_failures=<exact baseline comparison>
cross_repo_contract=<fixture/hash/policy ids and unchanged P9-2 evidence>
scope_expansion=<none or blocked request>
notes=<important choices and residual risks>
```

不要声称 accepted、pushed、merged、deployed、dogfooded、receipt-closed 或 task-closed；这些
只由 Codex reviewer/operator 在后续 gate 判定。
