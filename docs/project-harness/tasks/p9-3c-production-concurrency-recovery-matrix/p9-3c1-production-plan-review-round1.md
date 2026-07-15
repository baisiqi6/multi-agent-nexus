# P9-3C1 Production Plan — Independent Review Round 1

状态：`REQUEST_CHANGES_ADDRESSED_PENDING_REREVIEW`

日期：2026-07-15 Asia/Shanghai

## Reviewer authority

- Reviewer surface：Claude Code CLI `--model sonnet`。
- Provider-native assistant event actual model：`kimi-for-coding`。
- Reviewer 与 plan writer 分离；Codex 仍为 architect/operator/final reviewer。
- Full raw stream：
  `sessions/p9-3c1-production-plan-review-round1-claude-kimi/reviewer-stream.jsonl`。
- Resumed conclusion stream：
  `sessions/p9-3c1-production-plan-review-round1-claude-kimi/reviewer-conclusion-stream.jsonl`。
- Reviewed Coordinate revision：
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- Reviewed MultiNexus revision：
  `d09e0f8fba0f6d189934173027ca5a756e5f36ce`。
- Initial measurement SHA-256：
  `3d28e63be7e015e82e3e2bf91cd53d612a992b305b342c37615cc5b3cd980677`。
- Initial detailed plan SHA-256：
  `e0ec08aaae92bb38e984442ce87a9aea04b733c71133824c4ce5608bab549816`。

第一次 stream 在 Claude plan mode 尝试写其内部 plan file 时因未提供 Write tool 停住；该
stream 只作为完整过程 evidence，不当作 verdict。随后从同一 review session 恢复，禁用
tools，只要求基于已完成的 inspection 给出 bounded conclusion；该 conclusion 正常退出并
返回 `REQUEST_CHANGES`。

## Verdict

`REQUEST_CHANGES`

## Blocking findings and disposition

1. **Claim 内部仍会 global reap。** `claim_leased_job()` 无条件调用
   `_reap_due_leases_in_transaction()`；只增加 exact reap CLI 无法保护 real due lease。
   - disposition：新增 P1.2 claim-time `reap_mode=global|none` contract；default 保持
     `global`，fixture normal/recovery agentd 固定显式 `none` + bounded reason，并用
     nonfixture due sentinel tests 证明 zero mutation。
2. **Agent id 与 reviewed helper allowlist 不一致。** `p9-3c0-unit.sh` 只允许
   `p9-3c-fixture-e1/e2`，原计划写成 `p9-3c1-fixture-e1/e2`。
   - disposition：复用原 allowlisted agent ids；只让 workspace/source/run id 使用
     `p9-3c1-*` namespace，preflight cross-check helper allowlist。
3. **Recovery terminal-report 存在 automatic complete race。** 原文没有明确 recovery
   adapter mode。
   - disposition：recovery unit 固定 `hold`；controller read-only 等到 N+1/L3b active
     后才做 stale probes 和 current empty terminal report；明确禁止 recovery `complete`。
4. **Exact reap parser/dispatch contract 不完整。** 现有 `--batch-size` default `100` 会让
   exact-mode mutual exclusion 难以区分 implicit/explicit value。
   - disposition：parser default 改 `None`；无 exact ids 时才在 dispatch 使用 legacy
     `100`；exact ids 必须成对，且与 explicit batch-size mutually exclusive。
5. **Deactivate contract 需更精确。** 必须覆盖 pending/running/recoverable-timeout、runner
   retention、host/client fail-closed、idempotent offline retry。
   - disposition：逐项写入 P1.3，并加入 read-only `--dry-run` 和 post-cleanup heartbeat
     incident gate。
6. **Shared production mutation lock 的部署边界不足。** 需要覆盖 first helper deploy、
   `--no-restart`/inert path、rollback/smoke、root authority 与 status read-only semantics。
   - disposition：首次 helper install 使用同 directory/token contract 的 inline atomic
     bootstrap acquire；所有 mutation deploy mode 从 first copy 前持锁到 smoke/rollback 后；
     status 严格只读。

## Non-blocking findings incorporated

- live preflight 增加 zero due active lease inventory，明确它只是 defense-in-depth；
- stdout delivery 增加 exact id、job/request linkage、platform、payload hash/message id 与
  captured stdout readback；
- cleanup 后 unexpected heartbeat/reactivation 提升为 incident；
- mutation lock status 返回 bounded owner/action/start/phase，不创建或刷新状态。

## Gate

Round 1 不授权 P0 bootstrap、implementation、deploy 或 production activation。修订后的
measurement/plan 必须重新计算 SHA-256，并由 fresh independent reviewer 做 Round 2 exact-file
review。只有 `APPROVE` 才能进入 P0 detailed bootstrap。

P9_3C1_PLAN_REVIEW_ROUND1_REQUEST_CHANGES_ADDRESSED_PENDING_REREVIEW
