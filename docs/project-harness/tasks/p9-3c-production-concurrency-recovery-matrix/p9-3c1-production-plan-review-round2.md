# P9-3C1 Production Plan — Independent Review Round 2

状态：`APPROVED_P0_BOOTSTRAP_ONLY`

日期：2026-07-15 Asia/Shanghai

## Reviewer authority and evidence

- Reviewer surface：Claude Code CLI `--model sonnet`。
- Provider-native assistant event actual model：`kimi-for-coding`。
- Session id：`15ff14fe-44f6-4478-b737-0fd49439ceb0`。
- Full inspection stream：
  `sessions/p9-3c1-production-plan-review-round2-claude-kimi/reviewer-stream.jsonl`。
- Bounded final conclusion stream：
  `sessions/p9-3c1-production-plan-review-round2-claude-kimi/reviewer-conclusion-stream.jsonl`。
- Reviewed Coordinate revision：
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- Reviewed MultiNexus revision：
  `d09e0f8fba0f6d189934173027ca5a756e5f36ce`。
- Operator pre-review SHA-256：
  - measurement：
    `cd57fcdbb1a3ec9a3f9478f95f068d2378653c233646f14a5167253405fb9214`；
  - plan：
    `b9a4fc51aa56a8656b6bda4b4aff5f784171855da928baa7c83c3b540696f190`。

Reviewer 的 tool allowlist 只有 `Read/Glob/Grep`，因此它核验了 exact file content 与源码
约束，但没有在 reviewer session 内自行执行 hash 命令；上述 SHA-256 由 operator 在启动
review 前本地计算并传入，reviewer 将其作为 reviewed file identifiers。Conclusion 正常
退出，`terminal_reason=completed`、permission denials 为空。

Full inspection 因 high-effort 多次 context compaction 后继续扩散读取，由 operator 在保留
完整 JSONL 后中止；同一 session 随后以无 tools 的 bounded conclusion pass 收口。最终
assistant event 与 result 都返回同一 verdict。

## Verdict

`APPROVE`

## Round 1 blocker closure

1. Claim 内部 global reap：`CLOSED`。P1.2 定义 default-compatible
   `reap_mode=global|none`，fixture normal/recovery 固定 `none` + bounded reason，并要求
   nonfixture due sentinel zero-mutation tests。
2. Fixture helper allowlist：`CLOSED`。复用 `p9-3c-fixture-e1/e2`，P9-3C1 namespace
   保留在 workspace/source/run ids，并增加 helper allowlist preflight cross-check。
3. Recovery automatic-complete race：`CLOSED`。Recovery unit 固定 `hold`，等 N+1/L3b
   active 后由 controller terminal report，禁止 recovery `complete`。
4. Exact reap parser/dispatch：`CLOSED`。`--batch-size` parser default `None`，legacy default
   只在无 exact ids 的 dispatch 使用；exact ids 成对且与 explicit batch mutually exclusive。
5. Runtime agent deactivate：`CLOSED`。Exact host/client、job/lease blockers、runner/history
   retention、idempotent offline、dry-run 与 heartbeat incident boundary 已定义。
6. Shared production mutation lock：`CLOSED`。First helper bootstrap、所有 mutation deploy
   modes、smoke/rollback、root authority、token ownership 与 read-only status 已覆盖。

## Authorization boundary

本 approval 只授权生成 **P0 detailed bootstrap**。它不授权 P0 implementation、worker
dispatch、merge、push、deploy、production mutation、service restart 或 P3 activation。

P0 bootstrap 完成后还必须由独立 plan/bootstrap reviewer 对 exact bootstrap SHA-256 返回
`APPROVE`；之后才能派发 coding worker。P0 implementation 仍须经过 worker evidence、Codex
review、独立 exact-revision result review，以及 merge/push/inert deploy gate。

P9_3C1_PLAN_REVIEW_ROUND2_APPROVED_P0_BOOTSTRAP_ONLY
