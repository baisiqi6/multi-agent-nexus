# P9-2B correction Round 1 — bounded continuation

你是新的 ordinary `Kimi for Coding` coding worker，model 必须是
`kimi-code/kimi-for-coding`，禁止 highspeed。接手同一对隔离 worktree 中上一位 worker
保留的未提交改动；不要 reset、checkout、覆盖或修改两个 `main` checkout。

先读取：

- 两个仓库的 `CLAUDE.md`；
- approved plan（SHA-256 必须是
  `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`）；
- `result-review-round1.md`；
- `worker-correction-round1.md`；
- 当前 Coordinate diff，尤其是 `executor_routing.py`、`runtime.py`、
  `execution_cli.py` 和相关 tests。

## 当前已知状态

- Coordinate HEAD 必须仍是
  `eec9b233f6c797c73aec9d535fa723e037a0af65`；MultiNexus HEAD 必须仍是
  `b9416d9df81afb81051bfa19627bbe45d66852f0`。
- 上一轮已实现 R1-1 至 R1-5 的主体，最近 focused gate 为
  `135 passed, 5 subtests passed`。
- `tests/test_executor_routing.py` 已新增部分 strict mutation tests；
  `tests/test_runtime.py` 尚未成功追加完整 R1-4/R1-6 adversarial class；
  CLI correction tests 也仍需补齐。
- provider JSONL 显示上一轮终止原因是大 edit 时反复漏传 `path`，不是代码失败。
  所有文件操作使用明确绝对路径；不要重试空 `path/cwd`。

## 先修一个已识别的语义问题

当前实现把“没有 `preferred_host_id`”时所有 candidate 的 serialized
`preferred_host` 设成了 `true`。这不符合 contract：

- serialized `preferred_host` 只表示 candidate host 是否匹配一个**实际提供的**
  preferred host；未提供时所有 candidate 都应为 `false`；
- 但排序 host rank 在未提供 preference 时必须全部为 `0`。

请把 boolean 与 rank 分离。可以保留 internal rank、让 `sort_key()` 接收/保存 request
preference，或使用等价的不可误用设计；stored decision validator 必须结合
`RoutingRequest` 验证 boolean 与 exact policy order。测试必须同时断言“boolean false”
和“rank zero”。不要通过把 boolean 改成 true 来伪造 rank zero。

## 剩余实现与永久测试

逐项核对 `result-review-round1.md`，不能只相信 todo 状态。至少完成：

1. `routing_request` strict stored mutation matrix，以及 manually constructed
   `RoutingRequest` 无法绕过 parse。
2. decision/candidate unknown keys、bool-as-int、types、canonical capabilities、
   selection-kind/override、selected links、duplicates、candidate order、definition/agent
   tie break、candidate cap。
3. claim forged binding/definition/source/catalog/host/context/job links全部在 CAS 前
   zero mutation；断言 status/attempt/event 均不变。
4. exact/routed explicit key 两方向 collision；forged event target、payload target、
   request_event_id、workspace/task/assignment/runner links；concurrent loser 走 stored replay。
5. event insert 后 job create failure rollback，event/job both-or-neither。
6. same-job timed-out recovery 保留 route decision、assignment、binding、context 和 stale
   attempt authority；generic routed retry 在创建任何新 job/event 前拒绝。
7. exact typed 与 exact legacy compatibility。
8. CLI direct parser/handler tests：exact mode 的每个 route-only flag 都 fail closed；
   override pair/blank/control/overlong；caller capability normalization；invalid input 时
   `submit_request()` 零调用；valid routed JSON output。

必要时修实现，不得弱化断言或把 malformed stored data 当作 caller input normalize。
不得引入 schema v13、MultiNexus routing policy、`agents.current_load` authority、freshness、
capacity/lease/fairness/reroute 或 P9-3/P9-4 scope。

## 验证与 closeout

- 先用 `PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest ...`
  跑 focused tests；最终 gate 不得用 `head/tail` 截断。
- 跑 Coordinate full suite并对比九个 historical CLI/AST failures；跑 MultiNexus
  focused/full；跑 compileall、`git diff --check`、CLI contract/AST/static gates。
- 重新运行 Round 1 中的 adversarial probes，证明所有 `*_ACCEPTED` 变成 rejection。
- 在 MultiNexus task 目录写 `implementation-report.md`，记录 model、plan SHA、exact
  commands/counts、historical comparison、cross-repo contract、known risks。
- Coordinate 创建一个原子 implementation commit；MultiNexus 创建一个只包含本 task
  review/bootstrap/report 文档的原子 commit。
- 不要 push、cherry-pick、deploy、restart、生产 DB/lifecycle mutation。
- 最终输出两个 exact commit SHA、tests、worktree status，等待 Codex Round 2 review。
