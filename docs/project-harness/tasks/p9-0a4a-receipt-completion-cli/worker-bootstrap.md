# Worker Bootstrap: P9-0A4a Receipt Completion CLI Extraction

你是本包唯一 coding worker。严格执行已批准计划，不做架构扩展或顺手清理。

## Exact identity

- Task: `p9-0a4a-receipt-completion-cli`.
- Workspace id: `discord-nexus`.
- Worker repo/worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a4a-kimi`.
- Required branch: `agents/mac-omp/p9-0a4a-receipt-completion-cli`.
- Required start HEAD:
  `cfcb56f6605b381d54d6a9ca335b602c41e6e8ab`.
- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a4a-receipt-completion-cli/plan.md`.
- Approved plan SHA-256:
  `3f060777f40210a23ff6781c4937eccff32e060b8abf34c226436fc6e1556b28`.
- Plan review:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a4a-receipt-completion-cli/plan-review-round-1.md`.

开始前必须核验 `pwd`、branch、HEAD、clean status、plan SHA。任一不符立即停止并
报告 blocker；不要切换、reset、rebase、cherry-pick 或修复共享 checkout。

## Authorized implementation

实现计划中的静态、行为保持提取：

1. 新增 `src/coordinate/completion_cli.py`；
2. 增加 `register_completion_commands(assignment_subcommands)`，只注册六个
   receipt-aware leaves；
3. 原样移动已测量的 14 个函数；
4. root 用一个 registrar call 替换当前连续 parser block，并直接 re-export 所有
   14 个名称；
5. 扩展 contract fixture 与六层 rewind proof；
6. 新增隔离的 `tests/test_completion_cli.py`，锁定 alias、AST body、parser order、
   import direction、两阶段顺序和远端 argv/JSON failure contract。

安全不变量：preflight -> claim -> local write -> apply；`ReceiptEvidence` 只来自
authoritative remote claim；record 只消费有效 applied receipt。不要改变任何 reason、
JSON envelope、argv、help、exit code、fingerprint、repair 或 idempotency 行为。

## Allowed paths only

- `src/coordinate/cli.py`;
- `src/coordinate/completion_cli.py`;
- `tests/test_cli_contract.py`;
- `tests/fixtures/cli_contract.json`;
- `tests/test_completion_cli.py`;
- `tests/test_cli.py` only when a narrow facade assertion cannot live in the new file.

禁止修改 `completion.py`、`transitions.py`、DB/schema/service/daemon/harness/docs 或
任何 P9-0A4b 路径。禁止 opportunistic import cleanup。若发现必须超范围，停止并报告。

## Required validation

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_completion_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_completion tests.test_transitions
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

必须记录：21/75/99、old/new fixture SHA、六个 rewind hashes、14 个 canonical AST
body proofs、focused/full counts、精确 changed paths。测试不得使用 production DB、
SSH、`coord-ssh`、真实 receipt 或真实 checklist。

## Completion boundary

在全部验证通过后创建一个 descriptive local commit。不要 push、merge、deploy、restart、
SSH、调用 Coordinate lifecycle、修改 MultiNexus，或启动 subagent。最终报告 commit、
changed files、测试结果、风险；由 Codex 独立审查和集成。
