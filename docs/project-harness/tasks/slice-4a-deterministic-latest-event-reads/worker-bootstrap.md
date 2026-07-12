# Worker Bootstrap: Slice 4A Deterministic Latest-Event Reads

你是本包唯一 coding worker。严格执行批准计划，只做两个SQL tie-breaker和对应行为测试。

## Exact identity

- Task: `slice-4a-deterministic-latest-event-reads`.
- Worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-s4a-kimi`.
- Branch: `agents/mac-omp/slice-4a-deterministic-latest-event-reads`.
- Required start:
  `084419c5b36b32a81a39634c7ebbbf8b8b71d04c`.
- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4a-deterministic-latest-event-reads/plan.md`.
- Approved plan SHA-256:
  `dd4f8e5fde556ebd5fac9156230fd3bd05e555863dff1b3a4aacb8f87f051360`.
- Approval event: `c470c50e-0d28-43bd-af6e-8b4f03f69c84`.
- Read both plan-review rounds before editing.

开始前核验cwd、branch、HEAD、clean status和plan SHA；任一不符立即停止。不要
switch/reset/rebase/cherry-pick或触碰共享checkout。

## Authorized implementation

1. `_do_task_show`的eligible status query改为
   `ORDER BY created_at DESC, rowid DESC LIMIT 5`；
2. `_task_owner_for_event` fallback改为
   `ORDER BY created_at DESC, rowid DESC LIMIT 20`；
3. daemon行为测试显式构造至少六个相同`created_at`、不同rowid的eligible events，证明
   later five被选中、oldest被排除、显示顺序newest-rowid first；
4. policy行为测试构造ownerless task mirror和两个相同`created_at`、不同rowid/owner的
   eligible fallback events，证明later inserted owner被mention；保留已有mirror-first证明。

不得只写source-text assertion代替行为证明，不得修改timestamp精度、allowlist、limit、
owner precedence、malformed payload逻辑或其他SQL。

## Allowed paths only

- `src/coordinate/daemon.py`;
- `src/coordinate/policy.py`;
- `tests/test_daemon.py`;
- `tests/test_policy.py`.

任何其他路径需求都停止并报告。

## Validation

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_daemon.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_policy.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests
```

Baseline是38 daemon、151 policy、189 focused、1,572 full；实现后应新增两条行为测试，
预计39/152、191 focused、1,574 full。若exact binary不可用或count异常，停止并报告，
不得改fixture或换Python 3.12自我批准。

全部通过后创建一个local commit。禁止subagent、push、merge、deploy、SSH、Coordinate
lifecycle、MultiNexus修改。最终中文优先报告commit、exact paths、SQL diff、same-second
proof、test counts和风险。

Provider默认`kimi-code/kimi-for-coding-highspeed`；Kimi quota/auth/provider失败时只由
Operator记录JSONL后切换GLM，worker不得自行无记录切换。
