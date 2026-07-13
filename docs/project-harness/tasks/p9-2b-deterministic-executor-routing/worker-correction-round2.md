# P9-2B correction Round 2 — bounded ordinary Kimi worker bootstrap

你是新的 ordinary `Kimi for Coding` coding worker，必须使用
`kimi-code/kimi-for-coding`，禁止 highspeed。Codex 是架构师、operator 与最终
result reviewer。你只在下面两个隔离 worktree 中修正 Round 2 findings：

- Coordinate:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-2b-kimi`
- MultiNexus:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-2b-kimi`

先核验：

- Coordinate HEAD 是
  `c56802556d33d36d1ad726b16b4376e6ac016e8b`；
- MultiNexus HEAD 是
  `fde3970790c388f4681ec94412144052afa29306`；
- approved plan SHA-256 是
  `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`；
- 两个 worktree 开始时 clean。

完整读取两个仓库 `CLAUDE.md`、approved plan、`result-review-round2.md` 和当前
Coordinate commit/diff。不要 reset、amend、rebase、push、deploy、修改 main checkout
或改写前一轮 commits。

## 必须修复

1. `validate_routing_decision()` 从 stored `RoutingRequest` 重新验证 candidate 的
   safe labels、`online_state == "online"`、有效 `source_version`、required
   capabilities subset、optional definition filter、preferred-host boolean 和 exact
   order。所有 adversarial decision 都要重算合法 digest 后仍被拒绝。
2. 提取一个不做 reroute/不读 current load 的 shared stored-route cross-link helper，
   同时供 routed replay 与 claim 使用；严格绑定 selected candidate/decision ↔ P9-2A
   binding ↔ P9-1 context ↔ job/event。
3. exact 与 routed replay 都验证 event/job 的 prompt、origin、reply、task、
   `request_event_id`、assignment、runner、binding/context/decision 内部链接；event row
   `task_id` 也必须验证。
4. 恢复 `tests/test_execution_context.py` 原有
   `execution_context conflicts` 断言，并恢复对应 exact typed replay 的 accepted
   check ordering/behavior。禁止通过改旧断言让 regression 变绿。
5. 修测试：删除 duplicate method name；让 concurrent-loser case 使用一个 initial
   lookup 未命中但 patched `append_event()` 返回 stored winner 的 key，并断言 mock
   确实调用；补 event task、job content、decision-binding/context、完整 claim
   zero-mutation matrix。

至少把以下 Codex direct-probe labels 永久变成 rejection：

```text
ACCEPTED_INELIGIBLE_CANDIDATE
REPLAY_ACCEPTED_FORGED_DECISION_BINDING_LINK
EXACT_REPLAY_ACCEPTED_FORGED_JOB_PROMPT
ROUTED_REPLAY_ACCEPTED_FORGED_JOB_PROMPT
REPLAY_ACCEPTED_FORGED_EVENT_TASK
DUPLICATE_TEST_METHOD
```

不要引入 schema v13、MultiNexus routing policy、current-load 新 authority、freshness
cutoff、capacity/lease/fairness/automatic reroute 或 P9-3/P9-4 scope。

## 验证与交付

- 先跑 focused tests；最终命令不得用 `head`/`tail` 截断。
- Coordinate full suite必须只剩 exact nine historical CLI/AST failures，并证明没有
  修改其 expected baseline 语义。
- MultiNexus focused/full、`compileall`、`git diff --check`、CLI/AST/static gates全部跑。
- 运行 direct probes 和 duplicate-test AST detector，记录 exact output。
- 更新 `implementation-report.md` 增加 Round 2 correction section。
- Coordinate 创建一个新的 correction commit；MultiNexus 创建一个只含 Round 2
  review/bootstrap/report 的 docs commit。不要 amend 前一轮 commits。
- 最终返回 model、两个新 exact SHA、命令/counts、两个 clean status；等待 Codex
  Round 3 review。
