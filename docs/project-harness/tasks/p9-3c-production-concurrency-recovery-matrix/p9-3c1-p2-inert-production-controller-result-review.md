# P9-3C1 P2 Inert Production Controller — Result Review

状态：`APPROVED_AND_INERT_DEPLOY_GATE_OPEN`

日期：2026-07-16 Asia/Shanghai

## Exact revision and scope

- Worker base：`ba8ded97646a24233ee722719ef97eae3714fbf5`。
- Implementation candidate：`d60805d`，exact commit message
  `feat(p9-3c1): add inert production controller`。
- Candidate 相对 worker base exactly one implementation commit、20-path allowlist、clean diff；新增
  shell entrypoint mode `100755`，Python/config/tests/docs mode `100644`。
- Approved plan SHA-256：
  `7c78a2609435751add2a7aeba94d089921239d6a83ac424792230644a7110f00`。
- Corrected approved bootstrap SHA-256：
  `fea507f042406d1d415b5759b3871f0cf08aa4a6949662076f891314f067cd38`；其 durable correction
  以独立 docs commit `eac012e` 保留，不改变 candidate implementation bytes。

## Worker and Codex correction evidence

- Coding worker 使用 native `provider=kat-coder`、`model=kat-coder-pro-v2.5`，session
  `019f6943-535d-7000-9618-dad9c74d7586`。JSONL：
  `sessions/p9-3c1-p2-controller-state-machine-kat-coder-pro-v2.5/2026-07-16T04-50-47-773Z_019f6943-535d-7000-9618-dad9c74d7586.jsonl`，SHA-256
  `adf282076323df0c895659cef44a7530b8b154956bf5aebbfc0906b0e7b71ce6`。
- Operator 从 JSONL 看到 worker 使用错误 attempt-token、nonexistent schema、controller-direct claim
  和自造 evidence，立即 `SIGINT`，exit `130`；不接受其 completion claim。
- Codex 逐段保留可用代码并重建：真实 agentd J1-J5 authority、exact renewal/J3 recovery/stale-token/
  delivery evidence、production helper generation/cgroup authority、cleanup residue fence、final gate、
  deploy contract 与动态测试。

## Verification

Codex final candidate evidence：

```text
agentd focused: 137 passed, 19 subtests passed
controller: 42 passed
focused gate: 490 passed, 45 subtests passed
full gate: 1027 passed, 2 skipped, 81 subtests passed
bash -n helper/entrypoint: PASS
py_compile agentd/controller/tests: PASS
git diff --check: PASS
```

Full gate相对 baseline `953 passed, 2 skipped, 81 subtests` 增加 74 passes，没有新增 failure或 skip。

## Independent result review

- Fresh OMP reviewer 使用 native `provider=kat-coder`、`model=kat-coder-pro-v2.5`，与 coding worker
  为不同 session：`019f6985-3438-7000-a4f4-e0ebebf16b5d`。
- Native session JSONL：
  `sessions/p9-3c1-p2-inert-production-controller-result-review-round1-kat-coder-pro-v2.5/2026-07-16T06-02-45-176Z_019f6985-3438-7000-a4f4-e0ebebf16b5d.jsonl`，SHA-256
  `1732e4239e3c9160715c6168724874ad73a366f5fc5b3fc8f461f8256d8713ee`。
- Raw JSON stream：
  `sessions/p9-3c1-p2-inert-production-controller-result-review-round1-kat-coder-pro-v2.5/reviewer-stream.jsonl`，
  SHA-256 `143dd6d9f85cff59db1d96d8ddcac9bc0e9f6e94da598eae7a20e542bb430a11`。
- Reviewer读取真实 plan/diff/关键 implementation/tests，独立复跑 395 relevant tests、compile 与
  diff-check，最终返回：

```text
VERDICT: APPROVE
No blocking findings.
```

Codex 最终 adversarial review没有发现新的 blocker。

## Inert deploy correction review

- First inert deploy of `3772112` completed with `--no-restart` and `server smoke OK`，but the first
  installed `prepare` failed in controller argparse before any state root/write：thin wrapper consumed
  validation `$@` and then forwarded only the subcommand。
- Zero-mutation proof：failed run root absent、P0 lock free、Coordinate/bridge PID/NRestarts仍为
  `836234/0` 与 `1276892/0`、DB/fixture residue未变。
- Correction commit `44ba89b` saves the post-subcommand original argv array before validation shifts and
  execs exact `"${_original_args[@]}"`。A dynamic transformed-wrapper/fake-Python test fails on the old
  bug and proves exact argv order/element boundaries。
- Correction gates：controller `43 passed`；full `1028 passed, 2 skipped, 81 subtests passed`；
  `bash -n`/diff-check PASS。
- Fresh independent reviewer native route `provider=kat-coder`、`model=kat-coder-pro-v2.5`，session
  `019f699a-bacb-7000-9291-219f799330ac`，returned `VERDICT: APPROVE` with no residual risk。Native
  JSONL SHA-256 `2ff8ec57cfa4ecd3a19caa156f211b9615123a7ce0eddcb8b6c3b4bb8eede556`；raw stream
  SHA-256 `c1ec9d94f2e119561b8f582feb38679ad33e30bf478cec008e240b6a098183f6`。
- Dogfood also corrected one documentation overclaim：canonical deploy parity may issue idempotent
  roster/executor/capacity sync；acceptance is no added/removed/updated entry and no fixture source，
  while controller/helper/job/fixture activation remains forbidden。

## Accepted contract clarifications

- J3 exact crash contract需要 helper新增 `production-stop --crash`；这是 bounded public surface，
  不是 production activation。
- Recovery复用 exact E1 unit identity并生成新 generation；distinct unit identity budget仍严格为
  E1/E2 两个，latest generation cgroup是 recovery authority。
- Cleanup遇到本轮 nonterminal job或 active lease会写 `cleanup-blocked.json`、保留 lock并停止；
  不伪造强制终态。
- P2 manifest的 `p3_authorization_digest` 仍为 `None`；P3 authorization必须是后续独立审核 artifact。

## Authorization boundary

本 review与 correction review关闭 P2 local/result gate，允许 fast-forward merge/push、在既有 P0 production mutation
lock 下执行一次 `multinexus --no-restart` inert deploy，并只运行 fresh `prepare`、双次
`preflight/status` read-only dogfood。P2不得调用 `run` 或 `cleanup`，不得启动 fixture unit、创建
workspace/agent/catalog/job/lease/delivery mutation、重启 canonical service或访问 paid provider。

P9_3C1_P2_RESULT_APPROVED_FOR_INERT_DEPLOY
