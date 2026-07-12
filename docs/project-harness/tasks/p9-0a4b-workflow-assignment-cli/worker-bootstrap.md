# Worker Bootstrap: P9-0A4b Workflow and Assignment CLI Extraction

你是本包唯一 coding worker。严格执行经两轮审核批准的计划，不做架构扩展或顺手清理。

## Exact identity

- Task: `p9-0a4b-workflow-assignment-cli`.
- Worker worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a4b-kimi`.
- Branch: `agents/mac-omp/p9-0a4b-workflow-assignment-cli`.
- Required start HEAD:
  `4526d098ba4edcdcf669c41b6b6d827373088e5a`.
- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a4b-workflow-assignment-cli/plan.md`.
- Approved plan SHA-256:
  `62a7f267d5e68a42c68cc18553866302d18490b772b3472bc1f998dd1b622f7c`.
- Read both `plan-review-round-1.md` and `plan-review-round-2.md` before editing.

开始前核验 `pwd`、branch、HEAD、clean status、plan SHA；任一不符立即停止。不要
switch/reset/rebase/cherry-pick 或碰共享 checkout。

## Authorized implementation

1. 新增 `src/coordinate/workflow_cli.py`；
2. 实现 `register_branch_command`、`register_forge_commands`、
   `register_assignment_commands` 三个 registrar；
3. 原样移动批准的 12 个 handler / 254 行；
4. root 在三个精确 seam 调用 registrar 并 re-export 全部名称；
5. `register_assignment_commands` 保持 8 个 workflow leaves 后调用
   `register_completion_commands` 注册 6 个 receipt leaves；
6. 扩展 fixture 和七层 rewind proof，新增 `tests/test_workflow_cli.py`；
7. 窄改 `tests/test_completion_cli.py` 中 Round 1 指出的那一个 root-definition
   assertion：改成 root alias 与 workflow/completion owner 断言，不改其他 completion
   测试与 receipt 语义。

依赖必须保持 `cli -> workflow_cli -> completion_cli`，无回边。PR registrar 与所有
middle domain registrar 的顺序不可改变。

## Allowed paths only

- `src/coordinate/cli.py`;
- `src/coordinate/workflow_cli.py`;
- `tests/test_cli_contract.py`;
- `tests/fixtures/cli_contract.json`;
- `tests/test_workflow_cli.py`;
- `tests/test_completion_cli.py` only for the exact Round 1 assertion;
- `tests/test_cli.py` only if the new boundary file cannot hold one narrow facade proof.

禁止修改 `completion_cli.py`、service/schema/daemon/harness/docs、其他 completion
tests 或 P9-0A5。若需要超范围，停止并报告 blocker。

## Validation

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_workflow_cli tests.test_completion_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_assignments tests.test_branches tests.test_ci \
  tests.test_reviews tests.test_transitions tests.test_completion
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

记录 21/75/99、old/new fixture SHA、七层 rewind、12 AST hashes、三 registrar 顺序、
focused/full counts、exact paths。测试不得访问 production DB、harness、GitHub、SSH。

全部通过后创建一个 local commit。禁止 subagent、push、merge、deploy、restart、SSH、
Coordinate lifecycle 或 MultiNexus 修改。最终中文优先报告 commit、paths、证据和风险。
