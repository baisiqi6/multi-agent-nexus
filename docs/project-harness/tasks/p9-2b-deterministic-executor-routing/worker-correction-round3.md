# P9-2B Worker Correction Bootstrap — Round 3

你是 bounded coding worker。只修复 Codex Round 3 指出的 exact event-content
replay 缺口。不要扩展到 P9-3/P9-4，不要 push、cherry-pick、deploy、restart、
访问生产 DB 或关闭 lifecycle。

## 强制身份与基线

- Model 必须是普通 `kimi-code/kimi-for-coding`，禁止任何 highspeed 变体。
- Approved plan SHA-256：`328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate worktree：`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-2b-kimi`
- Coordinate HEAD：`7139728435e842e8728739ec6246b5b8eeb17407`
- MultiNexus worktree：`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-2b-kimi`
- MultiNexus HEAD：以启动时包含本 bootstrap 的 exact HEAD 为准，并在报告中记录。
- 两个 worktree 启动时必须 clean。

先完整阅读：

- 两个 repo 的 `CLAUDE.md`；
- approved `plan.md`；
- `result-review-round2.md`；
- `result-review-round3.md`；
- 当前 Coordinate commit/diff 与 `implementation-report.md`。

所有文件工具使用 absolute path。

## 唯一实现任务

修复 `_replay_exact_request()` typed-context 分支仍接受 forged stored-event
payload `origin`、`reply`、payload `task_id` 的问题。

约束：

1. 保持 accepted exact typed compatibility：先比较 P9-1 execution-context
   snapshot；若 current request 的 task/scope 改变，仍优先返回原有
   `execution_context conflicts`，禁止通过修改旧断言收口。
2. context 匹配后，stored event payload 的 `origin`、`reply`、`task_id` 必须与
   current request 以及 stored job authority 一致；event row `task_id`、job row
   `task_id` 和 `request_event_id` 现有校验继续保留。
3. legacy/no-context 分支也必须 fail-closed 校验对应 event payload 内容；不改变
   已接受的 legacy exact replay 成功路径和错误语义。
4. 新增永久 exact-event mutation matrix，至少覆盖 `origin`、`reply`、payload
   `task_id`。每个 subtest 必须证明 replay 被拒绝，且 event count、job status、
   attempt count、event/job stored payload 均零变化。
5. 不改 routing policy、schema、CLI、MultiNexus source，不重写既有 commits。

## Reviewer probes that must become rejection

```text
EXACT_EVENT_ORIGIN_FORGERY_ACCEPTED
EXACT_EVENT_REPLY_FORGERY_ACCEPTED
EXACT_EVENT_TASK_ID_FORGERY_ACCEPTED
```

## 验证与交付

- 先运行新 mutation matrix 与 exact replay compatibility tests。
- 最终 focused P9-2B gate 必须 unpiped；命令和 count 原样记录。
- Coordinate full suite 应只剩 exact nine historical CLI/AST failures。
- 运行 MultiNexus focused/full、`compileall`、duplicate-test AST detector、
  `git diff --check`。
- 更新 `implementation-report.md`，增加 Round 3 correction section，纠正此前
  “event/job 全链路已验证”的过宽表述与实际命令记录。
- Coordinate 新建一个 correction commit；MultiNexus 新建一个 docs-only commit；
  不 amend。
- 最终返回 model、两个 exact SHA、命令/counts、两个 clean status，然后等待
  Codex Round 4 review。
