# P9-3C1 P0 Production Mutation Lock Bootstrap — Independent Review Round 1

状态：`APPROVED_LOCAL_IMPLEMENTATION_ONLY`

日期：2026-07-15 Asia/Shanghai

## Reviewer authority and evidence

- Reviewer surface：Claude Code CLI `--model sonnet`。
- Provider-native assistant event actual model：`kimi-for-coding`。
- Session id：`92da1a1f-7f36-4f65-8336-504894869717`。
- Full inspection stream：
  `sessions/p9-3c1-p0-bootstrap-review-round1-claude-kimi/reviewer-stream.jsonl`。
- First bounded-conclusion stream：
  `sessions/p9-3c1-p0-bootstrap-review-round1-claude-kimi/reviewer-conclusion-stream.jsonl`。
- Final bounded-conclusion stream：
  `sessions/p9-3c1-p0-bootstrap-review-round1-claude-kimi/reviewer-final-stream.jsonl`。
- Reviewed bootstrap SHA-256：
  `5638d3a0ad17c53cf78496fc8447452b42767d181de895c282133258b68e76d8`。
- Reviewed MultiNexus base：
  `d09e0f8fba0f6d189934173027ca5a756e5f36ce`。
- Read-only Coordinate dependency base：
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`。

Full inspection stream 持续产生 provider-native thinking events，并完成了源码、现有 deploy
contract 与 bootstrap contract 的检查，但没有在合理边界内返回 verdict。Operator 保留完整
JSONL 后中止生成，并在同一 session 请求无 tools 的 bounded conclusion；第一次续跑仍只产生
thinking stream，因此再次中止。最终使用同一 session、`--effort low --max-turns 1` 收口，
assistant event 与 result 均正常返回相同 verdict，`terminal_reason=completed`、permission
denials 为空。中止的 inspection/conclusion stream 不是 verdict，最终 stream 才是授权依据。

Claude CLI init event 显示外层 selector `claude-sonnet-4-6`，但 provider-native assistant event
的 `message.model` 为 `kimi-for-coding`；后者是本轮实际 worker/reviewer model 证据。

## Verdict

`APPROVE`

Reviewer 没有提出 implementation blocker。

## Authorization boundary

本 approval 只授权 approved bootstrap 定义的本地 P0 coding：

- 新增 `scripts/production-mutation-lock.py`；
- 修改 `scripts/deploy-server.sh`；
- 新增 `tests/test_production_mutation_lock.py`；
- 修改 `tests/test_deploy_contract.py`；
- 在规定的 isolated worktree/branch 中运行测试并生成恰好一个本地 commit。

本 approval 不授权修改 allowlist 外文件，不授权 P1–P3、Coordinate、schema/DB，也不授权
push、merge、deploy、SSH、production mutation、service restart 或 live lock operation。
任何 scope deviation 都必须重新接受 bootstrap review。

P9_3C1_P0_BOOTSTRAP_REVIEW_ROUND1_APPROVED_LOCAL_IMPLEMENTATION_ONLY
