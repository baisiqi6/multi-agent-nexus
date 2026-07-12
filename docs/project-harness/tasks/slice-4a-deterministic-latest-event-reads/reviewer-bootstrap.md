# Slice 4A Independent Plan Reviewer Bootstrap

你是本包的独立 plan reviewer，不是 coding worker。只读审核，不得修改文件。

## Exact authority

- Task: `slice-4a-deterministic-latest-event-reads`.
- Plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4a-deterministic-latest-event-reads/plan.md`.
- Exact plan SHA-256:
  `dd4f8e5fde556ebd5fac9156230fd3bd05e555863dff1b3a4aacb8f87f051360`.
- Coordinate read-only checkout:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-s4a-plan-review`.
- Required Coordinate HEAD:
  `084419c5b36b32a81a39634c7ebbbf8b8b71d04c`.

开始前核验 plan SHA、cwd、HEAD和clean status。完整读取计划、
`plan-review-round-1.md`、当前`daemon.py`、
`policy.py`、`db.py`和相关tests；身份不符立即停止。

## Independent review questions

1. 全部production SQL audit是否真的只剩两个timestamp-only event-ledger newest reads？
2. daemon `tasks ORDER BY updated_at`为何应排除，它是否是decision authority还是普通display？
3. `created_at DESC, rowid DESC`是否与当前ledger insertion authority一致？
4. daemon六条same-second事件测试能否证明limit window与显示顺序，而非只证明SQL文本？
5. policy测试能否在task mirror owner为空时证明后插入owner胜出，同时不破坏mirror-first？
6. 四路径scope、189 focused / 1,572 full baseline是否准确可复现？
7. 是否遗漏malformed payload、event allowlist、limit、owner identity或import side effect？
8. 是否存在不必要schema/index/helper/refactor、Slice 4B/C/D或Phase 9 scope creep？

重点红队：同timestamp时`rowid`必须是明确tie-breaker，不能替换timestamp主排序；测试必须
构造相同`created_at`且不同rowid，不能依赖运行速度碰巧同秒。

## Boundaries and verdict

- 只可使用 read/grep/glob/bash；禁止 edit/write、subagent、commit、push、deploy、SSH、
  production DB/harness/lifecycle。
- 测试只可在指定Coordinate checkout运行。
- 最终中文优先报告，verdict只能是`APPROVE`、`CHANGES_REQUESTED`或`BLOCKED`；列出
  must-fix、非阻塞建议、exact SHA、test counts和provider session。
- 不得生成worker bootstrap或实现代码。
