# P9-3C1 P1 Coordinate Scoped Primitives — Result Review

状态：`APPROVED_AND_DEPLOY_GATE_OPEN`

日期：2026-07-16 Asia/Shanghai

## Exact revision and scope

- Base：`9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- Candidate：`a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。
- Branch：`agents/fallback/p9-3c1-p1-coordinate-scoped-primitives`。
- Candidate 相对 base exactly one commit、clean worktree、`git diff --check` PASS。
- Commit message：`feat(p9-3c1): add scoped production primitives`。
- Diff 精确包含 worker bootstrap 的八文件 allowlist：
  `src/coordinate/runtime_lease.py`、`src/coordinate/runtime.py`、
  `src/coordinate/execution_cli.py`、`tests/test_runtime_lease.py`、
  `tests/test_runtime.py`、`tests/test_execution_cli.py`、
  `tests/test_cli_contract.py`、`tests/fixtures/cli_contract.json`。
- Candidate CLI fixture SHA-256：
  `52891195af4c879e0d425b09a2263792a0137c36103590020e59c40b49872f26`。

## Worker and Codex correction evidence

- Claude Code 使用明确的 `--model sonnet` 进入 Kimi route，但在 repo write 前返回 billing-cycle
  `403`。Native JSONL 位于
  `sessions/p9-3c1-p1-coordinate-scoped-primitives-worker-claude-kimi/worker-stream.jsonl`，
  session `23f5c946-ab1d-4a1a-90c2-656b3dae4d9a`，SHA-256
  `a8c28fe9174daf4ff6a30cd24ed5f9254916f1bc8409f5e1ab45a9de2d5e3ff6`。
- DeepSeek fallback 的 native stream 证明 `provider=deepseek`、
  `model=deepseek-v4-pro`，session
  `019f6821-76fd-7000-8f51-97f1a378e637`。Worker 在实现期间将 bootstrap 强制要求的
  file-backed/two-connection deterministic race 降级为 single-connection sequential tests；
  Operator 因此立即发送 `Ctrl-C`，process exit `130`，不接收其完成声明。Native JSONL：
  `sessions/p9-3c1-p1-coordinate-scoped-primitives-worker-deepseek-v4-pro/worker-stream.jsonl`，
  SHA-256 `be592e1cc5a15da741ce8312ffebad995eed3ef66ddb9d6c84ba455ab6585558`。
- Codex 在 exact 八文件边界内逐段审计并保留可用实现，随后修复：typed claim handler 丢失
  JSON result、deactivate blocker 漏计 due active lease、CAS/previous-event chain错误、offline audit
  证据不完整、post-commit snapshot race、explicit empty actor default 化、bad sequential races、
  recoverable-none/explicit-global sentinel、exact path neighbor invariant、CLI P1-only golden rewind 和
  historical rewind chain。
- Claim/deactivate winner interleavings 最终使用 real file-backed SQLite、independent connections、
  real threads 与 explicit BEGIN/barrier events；不再用 sleep 或文件改动推断 worker/transaction 状态。

## Verification

Base evidence：

```text
focused: 214 passed, 37 subtests passed, 8 known failures
full: 2461 passed, 517 subtests passed, 9 known failures
```

Codex 在 final candidate tree 上得到：

```text
compileall -q: PASS
git diff --check: PASS
focused: 261 passed, 52 subtests passed, 8 known failures
full: 2508 passed, 532 subtests passed, 9 known failures
```

Focused/full failure names 与 base 完全一致：八个 historical CLI SHA tests，加 full suite 的一个
pre-existing `IssueCLIOwnershipTests` AST hash failure；无新增失败、无修改 historical SHA constant、
无 skip/xfail laundering。P1-only rewind test 证明移除本包 parser delta 后逐字节恢复 base fixture
SHA-256 `13cb4f3b748fdf7dc1d91dfbb27d9a214d23dfff1112d253d0e01aa0c701ad3d`。

## Independent result review

- Claude Code `--model sonnet` result-review attempt 连到 local provider gateway，但六分钟内未产生
  native init/message/result event，CPU idle；Operator 按 bounded timeout 中止。保留的原始
  `reviewer-stream.jsonl` 为 zero-byte，SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`；不将其伪称为一次 review。
- Fresh OMP reviewer 使用 native `provider=deepseek`、`model=deepseek-v4-pro`，session
  `019f6852-750c-7000-987c-1c7e2f6118b7`。完整 JSONL 位于：
  `sessions/p9-3c1-p1-coordinate-scoped-primitives-result-review-round1-deepseek-v4-pro/reviewer-stream.jsonl`，
  SHA-256 `7bc7b351eccd60c53a22f4704e31907aaa35182c2248b4a0df0d068045f3fa95`。

Reviewer 独立读取 plan/reviews/bootstrap、完整八文件 diff，重跑 focused/full 和专项 tests，得到：

```text
P0 findings: None
P1 findings: None
P2 findings: None
focused: 261 passed, 52 subtests passed, 8 known failures
full: 2508 passed, 532 subtests passed, 9 known failures
VERDICT: APPROVE
```

它逐项接受 exact reap isolation/rollback、global compatibility、typed claim 双层 policy/fence、
deactivate four blockers/CAS/full audit chain、same-second generation、dual-connection races、
sentinel invariants、CLI dispatch 和 P1-only golden proof。Codex 最终 adversarial review未发现新的
blocker。

## Residual boundary

- Legacy untyped claim 的 pretransaction online race仍由 P3 intake/routing closure处理；P1 只关闭
  typed managed agents，且不改变 legacy default/global语义。
- Exact reap CLI 的 pair/mixed shape在 opening `_conn` 前拒绝，individual id/actor authority由 core
  在任何 transaction/write 前重复验证；打开本地连接本身不构成 durable mutation。
- Deactivate CAS 使用同一个 `BEGIN IMMEDIATE` 中刚读取并验证的 host id；write lock 下不存在
  row-change窗口。

## Authorization boundary

本 review 关闭 P1 local/result gate，并允许 fast-forward merge/push、在既有 P0 production mutation
lock 下执行一次 `--no-restart` inert deploy，以及只读 help/hash/status/DB integrity/FK/residue smoke。
部署不得调用新 `runtime job lease reap`、`runtime job claim --reap-mode none` 或
`runtime agent deactivate` production mutation；不得 restart service、activate fixture/controller、
submit paid job 或推进 P2/P3 live matrix。

P9_3C1_P1_RESULT_APPROVED_FOR_INERT_DEPLOY
