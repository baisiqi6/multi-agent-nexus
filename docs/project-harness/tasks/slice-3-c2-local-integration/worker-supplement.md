# Worker Supplement: slice-3-c2-local-integration

本文件修正通用 `worker-bootstrap.md` 中不适用于本任务的 workspace、branch、deploy、
commit 与 lifecycle 指令。两者冲突时，以本 supplement 和已审核的 canonical plan 为准。

## 身份与固定输入

- Worker: `oh-my-pi/zhipu-coding-plan/glm-5.2`
- Task: `slice-3-c2-local-integration`
- 唯一工作目录：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-s3-c2-omp`
- 唯一允许分支：`agents/mac-omp/slice-3-c2-local-integration`
- 固定 base：`8fadd687d68032cf656291e6bf537ec481fb3e25`
- 固定 source：`1b862129897be001e5a9078b7b4fad48d90d89c2`
- source stable patch ID：`eb204296bd6a09e4caccabfe4bb05802e7ef7b37`
- canonical plan：
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-3-c2-local-integration/plan.md`
- reviewed plan SHA256：
  `aea8b2dd7a8348904fd1ffadc3a649c79355c76eba9c2d806d8adbff78e898ee`
- plan review：
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-3-c2-local-integration/plan-review-round-1.md`
- approved event：`c13bf777-85e3-4228-8996-6fe182ce3994`

开始前必须确认 `pwd`、branch、`HEAD`、clean status 以及上述 plan SHA256。任何不一致均
直接停止并报告 `blocked`，不得自行修复。

## 唯一允许的写动作

在隔离 worktree 中运行且仅运行一次：

```bash
git cherry-pick 1b862129897be001e5a9078b7b4fad48d90d89c2
```

如果出现 conflict、empty patch、hook failure 或其他异常，立即停止并保留现场。不得
`--continue`、`--abort`、resolve、stage、edit、amend、rebase、reset 或再做一次
cherry-pick。成功后也不得手工修改、创建额外 commit 或改写 integrated commit。

## 允许的只读诊断

仅允许下列等价的非变更命令：`pwd`、`git status --short --branch`、
`git branch --show-current`、`git rev-parse`、`git merge-base`、`git log --oneline`、
`git show --stat`、`git diff`、`git diff --name-only`、`git diff --name-status`、
`git patch-id --stable`、`sha256sum`、`rg`、`sed`、`wc`，以及下方测试/校验命令。
不得调用 Coordinate lifecycle、delivery、DB、daemon、service、network、SSH、deploy、
push、PR 或 merge 命令。

## 结构检查

成功 cherry-pick 后记录 integrated SHA 与 parent SHA，并验证：

1. integrated parent 等于固定 base；
2. source 与 integrated stable patch ID 都等于固定 patch ID；
3. integrated commit 只包含下列八个路径：
   - `docs/runbook.md`
   - `src/coordinate/cli.py`
   - `src/coordinate/completion.py`
   - `src/coordinate/db.py`
   - `src/coordinate/transitions.py`
   - `tests/test_cli.py`
   - `tests/test_completion.py`
   - `tests/test_transitions.py`
4. `src/coordinate/schema.py` 不得出现在 diff；
5. 对 integrated `src/coordinate/db.py` diff 运行
   `rg -n 'CREATE TABLE|ALTER TABLE|PRAGMA|schema_version|user_version'`，预期无匹配；
6. `git diff --check <base>..<integrated>` 通过。

## 测试与 adversarial 映射

运行 canonical plan 中的 focused、full-suite 与 checklist validation 命令，设置
`PYTHONDONTWRITEBYTECODE=1`。focused 最低计数为 completion 42、transitions 131、
CLI 169；full suite 预期 1,347 tests passed，并记录实际 count、duration、exit status。

最终报告必须把 adversarial 类别映射到具体测试方法，至少包括：

- actor / workspace / task isolation：
  `test_claim_rejects_actor_mismatch`、`test_claim_rejects_cross_workspace`、
  `test_claim_rejects_cross_task`；
- harness / forge fail-closed：
  `test_prepare_fails_closed_when_checklist_unreadable`、
  `test_prepare_fail_closed_when_harness_unavailable`、
  `test_prepare_rejects_when_latest_ci_failed`、
  `test_prepare_rejects_when_latest_ci_pending`；
- fingerprint fail-before-write：
  `test_claim_rejects_before_fingerprint_mismatch`、
  `test_apply_rejects_after_fingerprint_mismatch`、
  `test_normal_path_rejects_before_fingerprint_drift_before_write`；
- expiry：`test_claim_rejects_expired_receipt`、
  `test_consume_rejects_malformed_expiry`；
- ordering / replay / callback loss：
  `test_apply_rejects_when_not_claimed`、`test_consume_requires_applied_not_claimed`、
  `test_apply_idempotent_on_retry_after_callback_loss`、
  `test_consume_replay_no_second_terminal`；
- prior claimed/applied drift：
  `test_claim_rejects_drifted_before_under_prior_claimed`、
  `test_claim_rejects_drifted_before_under_prior_applied`；
- repair-only：`test_requires_receipt_or_repair_reason`、
  `test_repair_path_mutates_and_stamps_repair_only`；
- atomic terminal behavior：
  `test_consume_happy_path_atomic_task_done_and_consumed`。

## 返回边界

不得执行通用 bootstrap 中的 assignment accept/closeout/mark-done、Discord 更新、
worker commit、deploy 或 self-test deployment。返回 base/source/integrated/parent SHA、
两个 patch ID、精确路径、schema scan、diff check、测试结果、JSONL/session handle（若可用）
和剩余风险。最后只输出一个 `[agent-report]`，`action=done` 或 `action=blocker`。

这次 worker 成功仅表示隔离分支产生了待审核的 integration candidate。Codex 将独立复核；
Coordinate `main` 的任何推进仍需用户之后明确授权。
