# Worker Bootstrap: slice-4d-projection-doctor-evidence

你是本包的 coding worker，不是 architect、plan reviewer、operator、deployer 或
result reviewer。只在 Codex 创建的专用 Coordinate worktree 中实现已经批准的计划。

## Mandatory identity gate

编辑前运行：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
shasum -a 256 \
  /Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan.md
```

必须精确得到：

- Worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-s4d-kimi`
- Branch: `agents/mac-omp/slice-4d-projection-doctor-evidence`
- Start SHA: `a21d946e4d6be78f3f481d38eb2571229a4d3a9f`
- Plan SHA-256:
  `4a16f55005567a6640b98130ec9cf83391224b8e5f25622bf17cac0b0c6d4c64`
- Plan review: `plan-review-round2.md`, APPROVE
- `plan.ready`: `ef80e0a4-63c5-46c1-b3d4-393949a4048f`
- `plan.approved`: `b5176124-d930-4617-bb74-6e784006ec52`

任一身份不符时，不得编辑，直接报告 mismatch。

## Read first

完整阅读下列文件；approved plan 是实现 source of truth：

```bash
cat /Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan.md
cat /Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan-review-round1.md
cat /Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan-review-round2.md
cat /Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan-approval.md
```

随后只读检查相关当前代码和测试，尤其是：

- `src/coordinate/doctor.py`, `audit.py`, `harness.py`, `db.py`;
- `src/coordinate/split_operations.py`, `completion.py`, `completion_cli.py`;
- `src/coordinate/workspace_cli.py` 与 CLI contract fixture；
- registry、C1/C2、task mirror、receipt、doctor/audit 现有测试。

## Implementation assignment

完整实现批准的 S4-D：

1. 新增 `projection_doctor.py` 中的 immutable finding/report 与单一只读 collector；
2. 诊断 registry source/effective/`agents_json`/override projection；
3. 诊断 C1/C2 checklist envelope、v11 ledger、record event 与冲突；
4. 按 `events.rowid` 诊断 operation-aware task mirror，接受合法的后续 lifecycle；
5. 按 receipt event chain 派生 authoritative state，并修复
   `assignment mark-done-preflight` 的 stale-authorized 返回；
6. additive 集成 `workspace doctor`，保留 audit authority，并提供可见但不得用于
   gate 的 `--no-projections`；
7. 为每个计划列出的 finding、排序、severity、evidence、repairability、no-write
   与 compatibility case 提供测试。

## Hard boundaries

- 不得新增 schema/table/index，不得调用或实现 generic repair/mutation executor。
- projection collector 不得调用 `harnessctl`、`subprocess`、`refresh_state`、
  `apply_*` 或任何 harness/registry/event/delivery/receipt mutation。
- 只允许复用批准计划枚举的 canonical split-operation helpers；若需要公开 wrapper，
  必须是无 commit/rollback/file write 的纯只读 wrapper，不得复制 hash 格式。
- `registry_source_unreadable` 不得伪装成 mismatch；`agents_json` 不是 authority。
- receipt precedence 必须是 `consumed > applied > claimed > authorized`；partial、
  duplicate conflict、unknown chain 均 fail-closed。
- file-pending envelope 不包含完整 record-half intent 时必须
  `repairable=false`，不得猜 actor/defaults 或生成可执行 repair command。
- 不得更改 S4-B/C mutation semantics、receipt transitions、daemon、scheduler、
  Phase 9、MultiNexus 或 production state。
- `--no-projections` 不得出现在任何 acceptance、full test wrapper、dogfood、deploy
  smoke 或 release-gate 命令中；测试必须证明该 flag 只作为可见 compatibility path。
- 若实现需要超出 plan 的 module/scope 或改变 authority，停止并请求 plan revision。

## Allowed implementation surface

- 新增 `src/coordinate/projection_doctor.py`。
- 仅在必要时聚焦、additive 修改：`doctor.py`, `audit.py`, `workspace_cli.py`,
  `completion_cli.py`, `db.py`, `split_operations.py`。
- 新增/修改聚焦测试：projection doctor、doctor、audit、completion、workspace CLI、
  split operation、CLI contract。
- 不得修改 MultiNexus。不得修改 unrelated production modules 或历史 baseline。

## Verification

使用当前共享 venv：

```bash
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest ...
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m compileall -q src tests
/Users/yinxin/projects/coordinate/.venv/bin/python -m ruff check <touched paths>
git diff --check
```

必须完成：

- 新 focused projection suite；
- doctor/audit/completion/workspace CLI/split-operation/registry/receipt regressions；
- exact CLI contract 与独立于 Git topology 的 C2-to-D delta proof；
- 完整 Coordinate suite；
- DB `total_changes`/`data_version` 与完整 harness manifest/bytes 的成功和失败路径
  no-write 证明；
- 确认所有 gate 命令均未使用 `--no-projections`。

当前 Python 3.12 baseline 有 9 个已知 argparse/AST historical failures；不得更新
历史 SHA、重新 baseline 或把它们算作本包回归。S4-D 新增测试必须全部通过，并在报告
中分别列出新通过数和完全相同的历史失败。

## Provider and evidence

- Primary model: `kimi-for-coding-highspeed`, high thinking。
- 只有出现明确 quota/auth/provider failure 才停止并报告原始错误；Codex 才能决定
  是否用 GLM 重启。不得因普通测试/实现失败静默换模型。
- provider-native JSONL 是主要活动证据；不得启动 nested agents。

## End protocol

1. 对照 plan 和 allowed paths 审阅完整 diff。
2. 运行 focused、regression、full、ruff、compileall、`git diff --check`。
3. 在当前 worker branch 上提交所有本包代码/测试；不得 push、merge、deploy、SSH、
   访问 production DB、调用 Coordinate lifecycle 或修改 MultiNexus。
4. 返回 commit SHA、changed paths、每条验证命令/计数、历史失败、residual risks，
   以及唯一一个：

```text
[agent-report]
action=done
workspace_id=discord-nexus
task_id=slice-4d-projection-doctor-evidence
summary="Implemented S4-D on <sha>; <focused/full evidence>; no deploy"
```
