# P9-2B Worker Correction Bootstrap — Round 5

你是 bounded coding worker。只修复 Codex Round 5 的 capability item length finding，
补齐永久测试和报告证据。不要扩展到 P9-3/P9-4，不要 push、cherry-pick、deploy、
restart、访问生产 DB 或关闭 lifecycle。

## 强制身份与基线

- Model 必须是普通 `kimi-code/kimi-for-coding`，禁止任何 highspeed 变体。
- Approved plan SHA-256：`328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Coordinate worktree：`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-2b-kimi`
- Coordinate HEAD：`5d9b458bd70afb649e25f4a20d9db69e484f9d46`
- MultiNexus worktree：`/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-2b-kimi`
- MultiNexus HEAD：以启动时包含本 bootstrap 的 exact HEAD 为准，并在报告中记录。
- 两个 worktree 启动时必须 clean。

先完整阅读两个 repo 的 `CLAUDE.md`、approved `plan.md`、
`result-review-round5.md`、当前实现与 `implementation-report.md`。所有文件工具使用
absolute path。每次运行 git 命令前显式 `cd` 到目标 worktree 并用 `pwd` 确认，避免
在 Coordinate 与 MultiNexus 之间串错仓库。

## 唯一代码任务 — enforce shared capability item length

复用 `coordinate.executor_identity.MAX_CAPABILITY_LEN`，不要新建 magic number。
在 `_validate_canonical_capabilities()` 中强制每个 capability item 不超过该 authority
（当前 64 字符），使 caller normalization、strict stored request 和 stored candidate
evidence 使用同一长度边界。

保留已有 string type、unsafe grammar、duplicate、32-item cardinality、canonical sort
及其已断言的错误行为。不要改变 selection、load、replay、claim、CLI 或 schema。

新增永久测试，至少证明：

1. caller `build_routing_request()`：64 accepted，65 rejected；
2. strict stored `routing_request`：64 accepted，65 rejected；65 case 必须重算正确的
   `routing_request_id`，确保真正命中长度 gate；
3. stored candidate evidence：64 accepted，65 rejected；65 case 必须重算正确的
   `routing_decision_id`；
4. event/job 同时携带同一个 forged overlong candidate decision 时，routed replay
   拒绝，event count/payload 与 job row/payload/status/attempt count 全部不变；
5. claim 路径在 CAS 前拒绝相同 forged envelope，job status、attempt count、payload
   和 event count 均不变。

## 验证与交付

1. 先运行新增 64/65 boundary tests 与 reviewer probe。
2. 运行 unpiped focused gate：

```text
PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest \
  tests/test_executor_routing.py \
  tests/test_runtime.py::RoutedRuntimeTests \
  tests/test_runtime.py::RoutedRuntimeCorrectionTests \
  tests/test_execution_cli.py
```

3. Coordinate full suite只允许 exact nine historical CLI-contract/AST failures；
   MultiNexus full仍应为 `503 passed, 2 skipped`。
4. 两个 repo 运行 `compileall`；运行 inline duplicate-test AST detector。
5. 最终运行 committed-range gates：

```text
git diff --check eec9b233f6c797c73aec9d535fa723e037a0af65..HEAD
git diff --check 7a06573f8c17c4376c272a68b1201d5c4320675d..HEAD
```

两者必须 empty output。
6. 在 MultiNexus `implementation-report.md` 追加 Round 5 correction section，不覆盖旧
   记录。
7. Coordinate 新建一个 follow-up commit；MultiNexus 新建一个 docs-only follow-up
   commit；严禁 amend 既有提交。
8. 最终返回 model、两个 exact SHA、全部命令/count、range diff empty output、两个
   clean status，然后等待 Codex Round 6 review。
