# P9-2A Kimi Coding Worker Bootstrap

你是 P9-2A coding worker，不是架构师、plan reviewer、operator 或 deployer。只在下列
两个隔离 worktree 中实现、测试并分别 commit；不要 push、merge、deploy、SSH、访问生产
DB、重启服务、执行 lifecycle/receipt、修改主仓库或启动 subagents。

## Immutable authority

- Approved plan:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-2a-kimi/docs/project-harness/tasks/p9-2a-executor-identity-registry/plan.md`
- Exact approved plan SHA-256:
  `0f3fa12469b1a5587c94e386c0da13e32111383ccdc640c227e7564ba7f0ec45`
- Independent approval:
  `plan-review-round2.md`, Kimi JSONL session
  `019f5a13-d353-7000-802e-caf3d34d0e62`, `must_fix=0`.
- Plan approval event: `6db26c20-496a-4353-bed3-31bd6b61a432`.
- Coordinate baseline: `b732159c4a1bbced39dc6ab9cde8841e7959a8cb`.
- MultiNexus implementation baseline:
  `7675586593495aae643fe9901c62d27915780f98` (P9-1 code plus P9-2A planning docs only).

开始前必须完整阅读两个 repo 的 `CLAUDE.md`、approved plan、Round-1/2 review；重新计算
plan SHA 并确认两个 HEAD。任何不一致立即停止并报告，不要自行换 baseline 或扩大范围。

## Isolated worktrees

- Coordinate:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-2a-kimi`
- MultiNexus:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-2a-kimi`

只允许在这两个路径内写文件。主 checkout
`/Users/yinxin/projects/coordinate`、`/Users/yinxin/projects/multinexus` 只读且不得切分支。

## Implementation contract

完整落实 approved plan 的 Stage A-E，不做 P9-2B routing、P9-3 lease/capacity 或 P9-4
heartbeat/JSONL。关键不可协商点：

1. Coordinate schema `11 -> 12` additive migration，三个 catalog/binding tables、明确 FK/
   indexes、fresh/upgrade/idempotent/rollback tests。
2. 新建 `coordinate.executor_identity`，由 Coordinate 直接解析同一个
   `config/agent-registry.toml` source，严格 canonicalize 并原子 sync；不要接收
   MultiNexus 生成的中间 JSON。
3. Exact canonical catalog JSON/fixture/hash 必须跨 repo byte-identical；新增 executor keys
   前后 existing roster hash byte-identical。
4. P9-2A managed binding 强制 `runner_profile_id == agent_id`；`adapter` 是 bounded identity
   label 并必须匹配 `AgentConfig.adapter`；`provider` 只作 bounded/non-executable audit
   metadata，禁止作为 command/model/bin/env。
5. provider/adapter parser 必须拒绝 path separators、shell metacharacters、空白控制字符和
   command-like payload；测试证明没有命令执行面。
6. Catalog version/hash/source ownership、multi-source preserve/takeover、unknown reference、
   downgrade/same-version conflict 全部在 transaction 内 zero mutation。
7. Catalog change 的 pending/claimed typed-job guard 必须在同一 `BEGIN IMMEDIATE`
   transaction 内检查；same-version/same-hash retry 可通过，禁止 deploy-only racy preflight。
8. Typed exact submit 在任何 durable write 前 snapshot binding；legacy exact target 显式
   `executor_binding=null`；replay 不升级 binding；claim mismatch 在 CAS/attempt/status 前失败。
9. Claim mismatch 返回 bounded machine-readable error，必须能和 queue-empty 区分；
   `job.claimed`/result evidence 不包含 prompt、command、env、token、credential。
10. MultiNexus 用独立 strict parser，不 import Coordinate Python、不读 Coordinate SQLite；
    typed mismatch 在 adapter invocation 前失败，P9-1 execution-context bytes/semantics 不变。
11. Deploy contract 必须在 VERSION write/restart 前证明 roster + executor catalog parity；
    本 worker 只实现与测试 deploy code，不实际 deploy。
12. 不引入 ORM、DI framework、plugin loader、generic repository framework、provider-specific
    dispatch branch 或第二份 config source。

## Expected change surface

Coordinate 预期只涉及：

- `src/coordinate/schema.py`
- new `src/coordinate/executor_identity.py`
- `src/coordinate/runtime.py`
- `src/coordinate/execution_cli.py` and only required CLI composition/export seams
- `src/coordinate/db.py` only if compatibility re-export is required
- focused tests under `tests/` and one executor binding fixture

MultiNexus 预期只涉及：

- `config/agent-registry.toml`
- `multinexus/registry_authority.py`
- new `multinexus/agentd/executor_binding.py`
- only required `multinexus/agentd` claim/result integration files
- `scripts/agent_registry_deploy_verify.py`
- `scripts/deploy-server.sh`
- focused tests under `tests/` and the byte-identical fixture
- optional `implementation-report.md` in this task directory

若必须修改范围外文件，先在最终报告中列为 blocked expansion；不要静默修改 plan、review、
checklist、progress、dogfood、runbook、release/deploy receipt 或 unrelated CLI fixture。

## Verification before commit

至少执行并保存结果：

- Coordinate focused schema/executor/runtime/execution-CLI/contract tests；
- MultiNexus focused registry/deploy/agentd tests；
- both full suites；
- both `compileall`；
- both `git diff --check`；
- cross-repo fixture byte comparison and SHA-256；
- static no-cross-import/no-SQLite/no-provider-command/no-routing/no-lease gates；
- exact diff scope and `git status --short` in both worktrees。

不要修改历史 test expectation 只为追绿；若出现 approved plan 未覆盖的真实设计冲突，停止并
报告 `blocked`，不要自行决定新架构。

## Commit and final report

验证通过后在两个 repo 分别创建一个清晰 commit，不 push。最终返回：

```text
status=implemented|blocked
plan_sha256=<exact>
coordinate_start=<sha>
coordinate_commit=<sha or none>
multinexus_start=<sha>
multinexus_commit=<sha or none>
files_changed=<per repo>
tests=<exact commands and counts>
fixture_sha256=<sha>
known_failures=<none or exact baseline-matched list>
scope_expansion=<none or blocked request>
notes=<important implementation choices>
```

不要声称 accepted/deployed/closed；这些判断只由 Codex reviewer/operator 在后续 gate 作出。
