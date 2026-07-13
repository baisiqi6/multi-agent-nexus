# P9-2B Worker Correction Bootstrap — Round 4

你是 bounded coding worker。只修复 Codex Round 4 的三个 finding：selected
candidate capabilities cross-link、capability cardinality bound、以及 range-based
diff gate。不要扩展到 P9-3/P9-4，不要 push、cherry-pick、deploy、restart、访问
生产 DB 或关闭 lifecycle。

## 强制身份与基线

- Model 必须是普通 `kimi-code/kimi-for-coding`，禁止任何 highspeed 变体。
- Approved plan SHA-256：`328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate worktree：`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-2b-kimi`
- Coordinate HEAD：`091c9e86f23dc627ea7131757de889b425eb8f3e`
- MultiNexus worktree：`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-2b-kimi`
- MultiNexus HEAD：以启动时包含本 bootstrap 的 exact HEAD 为准，并在报告中记录。
- 两个 worktree 启动时必须 clean。

先完整阅读两个 repo 的 `CLAUDE.md`、approved `plan.md`、
`result-review-round4.md`、当前实现与 `implementation-report.md`。所有文件工具
使用 absolute path。

## 任务 1 — cross-bind selected capabilities

在 `_validate_routing_cross_links()` 中，把 selected candidate 的 canonical
`capabilities` 与 stored `executor_binding.capabilities` 做 exact equality 校验。
保持现有 source/version/catalog/id/assignment/context links 和 replay ordering。

新增永久测试，至少证明：

1. 只把 selected candidate capabilities 改成另一个合法、sorted、仍满足 request
   的 superset，并重算 `routing_decision_id` 时，`routing_claim_evidence()` 拒绝；
2. event/job 都携带同一个上述 forged decision 时，routed replay 拒绝且 event/job
   零变化；
3. claim 路径在 CAS 之前拒绝，job status、attempt count、payload 和 event count
   均不变。

## 任务 2 — enforce the shared 32-capability bound

复用 `coordinate.executor_identity.MAX_CAPABILITIES`，不要新建另一套 magic number。
在 caller normalization 和 strict stored-envelope validation 两处执行 cardinality
上限，因此 `routing_request.required_capabilities` 与 candidate `capabilities` 都受
同一 authority 约束。

新增边界测试：

- caller `build_routing_request()`：32 accepted，33 rejected；
- strict stored `routing_request`：32 accepted，33 rejected（使用正确 digest，确保
  真正命中 cardinality gate）；
- stored candidate evidence：32 accepted，33 rejected（必要时重算 decision digest）。

保留 empty、unsafe、duplicate、unsorted、bool 等现有 fail-closed 行为和已断言的
错误优先级。

## 任务 3 — correct diff evidence

- 删除 `tests/test_executor_routing.py` 的 extra EOF blank line。
- 最终运行并记录：

```text
git diff --check eec9b233f6c797c73aec9d535fa723e037a0af65..HEAD
```

必须 empty output。不要用 bare `git diff --check` 代替 committed-range gate。

## 验证与交付

1. 先运行新增的 capability-bound/cross-link tests 与 reviewer probes。
2. 最终 focused P9-2B gate unpiped，预期原 173 加本轮新增 tests。
3. Coordinate full suite只能保留 exact nine historical CLI-contract/AST failures。
4. MultiNexus full：`503 passed, 2 skipped`；运行两个 repo `compileall`。
5. 运行 inline duplicate-test AST detector，不创建持久化 detector script。
6. 更新 `implementation-report.md`，增加 Round 4 correction section，明确纠正
   之前 bare diff gate 的证据，不覆盖或伪造旧记录。
7. Coordinate 新建一个 follow-up commit；MultiNexus 新建一个 docs-only follow-up
   commit；不 amend。
8. 最终返回 model、两个 exact SHA、全部命令/count、range diff empty output、两个
   clean status，然后等待 Codex Round 5 review。
