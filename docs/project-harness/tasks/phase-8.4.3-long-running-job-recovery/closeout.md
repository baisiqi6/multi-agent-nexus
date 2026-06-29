# Phase 8.4.3 Closeout Packet — Long-Running Job Recovery (4 P1 fixes)

> Status: 4 P1 code-level blockers fixed + pushed; **not mark-done/merged/deployed** (awaiting final review-result, then deploy gate). self_test_evidence = unit/integration green; deploy+smoke pending gate.

## Scope

修复 review 发现的 4 个 P1(每个违反 8.4.3 自己的 invariant,补齐设计,不改 invariant)。原 plan:`docs/project-harness/tasks/phase-8.4.3-long-running-job-recovery/plan.md`(8 invariants + workstream A/B)。P1 修复 implementation plan:`docs/superpowers/plans/2026-06-29-phase-8.4.3-p1-fixes.md`。

## 两仓 commit(origin 对齐)

**coordinate** — `16a0b81`
- `161d941` P1 #1 — `claim_job` 默认 `recoverable=False` + CLI `--no-recoverable`→`--recoverable`
- `e37f16a` P1 #2 — attempt token SQL CAS(report/progress/`_accept_late_result`)+ `rowcount==0` rollback raise
- `16a0b81` P1 #4 — `_normalize_reply_platform(platform, default_bus)` per-workspace

**multinexus** — `5b69e61`
- `b659b0f` P1 #2 — agentd 透传 `attempt_token`(claim → progress/report)
- `5b69e61` P1 #3 — `recovery_session_id` 优先于 existing,始终 fail-closed

## 4 P1 修复

| # | invariant 违反 | 修法 |
|---|---|---|
| #1 claim 默认领 recoverable | inv 8 + A2 | `claim_job` 默认 `recoverable=False`(普通 poll 只领 pending);显式 `--recoverable` 才领 timed_out。agentd 普通 poll 不传 flag → 自动安全 |
| #2 无 attempt token CAS | inv 5 + A2 | `RuntimeClaimResult.attempt_token`;report/progress/`_accept_late_result` 用 **SQL CAS** `WHERE ... AND attempt_count=?`,`rowcount==0` → rollback + raise(不 append event、不 delivery)。agentd 透传 token。`attempt_token=None` 保留兼容路径 |
| #3 recovery resume 不 fail-closed | inv 4 | `recovery_session_id` 存在时**始终**走 `_resume_recoverable_session`(fail-closed,不 fresh duplicate),即使 existing session 也在。legacy existing-resume 的 fresh fallback 只对非 recovery 场景 |
| #4 reply platform 硬编码 | A4 | `_normalize_reply_platform(platform, default_bus)`:discord→discord_webhook **仅当** `default_bus != "discord"`。DiscordBus workspace 保持 discord |

## 测试

- **coordinate**: 1107 passed(`test_runtime` 19 含 claim/CAS/late-result/platform;`test_cli` 136 含 CLI CAS report+progress)
- **multinexus**: 324 passed, 2 skipped(`test_n_plus_m_invariant` 37 含 fail-closed + existing+recovery;`test_claude_adapter` 3)
- targeted(codex 复跑):coordinate test_runtime 19 OK / test_cli 136 OK;multinexus n_plus_m 37 OK / claude_adapter 3 OK
- diff --check clean(两仓)

## self_test_evidence

- ✅ unit/integration:两仓全绿(见上)
- ⏳ **deploy + recoverable timeout/resume smoke:待 deploy gate**(approve 后 deploy,跑最小 recoverable timeout→resume→`--attempt-token` CAS + fail-closed 真实 agentd 路径 smoke)
- 当前**未 deploy**(review 阶段)

## deploy order(强制)

**coordinate `16a0b81` 必须先于 multinexus `5b69e61`**。新 multinexus agentd 传 `--attempt-token`,旧 coordinate 不认该 flag → CLI 报错。两仓一起 deploy 时 coordinate 先 restart。无版本探测/兼容 fallback(8.4.3 一起 deploy、coordinate 先即可)。

## 未跟踪文件说明

- `agents.recovery.toml` — agentd recovery 测试的**临时本地配置**(含本地路径),**不提交**
- `docs/superpowers/` — P1 修复 implementation plan(`2026-06-29-phase-8.4.3-p1-fixes.md`),**计划产物**,随本 closeout 提交

## 待办(按 gate 顺序)

1. 最终 review-result(reviewer 审 closeout + 4 P1)
2. approve → deploy(coordinate `16a0b81` 先,multinexus `5b69e61` 后)
3. deploy 后 recoverable timeout/resume smoke(真实 agentd 验 `--attempt-token` + fail-closed)
4. mark-done(smoke 通过后,按 gate)
