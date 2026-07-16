# P9-3C1 P3 Live Matrix — Independent Plan Review

状态：`APPROVE_BOOTSTRAP_DRAFT_ONLY_LIVE_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Exact reviewed authority

- branch：`agents/fallback/p9-3c1-p3-live-matrix-plan`；
- reviewed HEAD：`cce85c522bb99d88c4e26ab43f47938e66cbfbc8`；
- base：`33773c16fe7a12174b55e8e1731dbb2705e9e56b`；
- measurement SHA-256：
  `7b84344dccf02d0164565f4a1bc127cb9f5860663cea697e4f64712b6639cf13`；
- approved plan SHA-256：
  `7e8d8846f56d4d62870c63f30705855586adcf34caf2d593f80839952d175fe2`；
- changed-file set：only `p9-3c1-p3-live-matrix-measurement.md` and
  `p9-3c1-p3-live-matrix-plan.md` before this review artifact；zero code/test/config/script change。

Verdict只覆盖上述 exact plan bytes。Any later edit invalidates this approval and requires a fresh
independent review。

## 2. Independent reviewer route

Reviewer使用 OMP `deepseek/deepseek-v4-pro`，只开放 `read,grep,glob,bash`；prompt禁止 edit/write、
git mutation、SSH production mutation、deploy、service/DB mutation、controller
`prepare/run/cleanup` and subagents。

### Round 1

- session id：`019f69e8-8fed-7000-a1be-fa49e829e993`；
- native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-plan-review-deepseek-v4-pro/2026-07-16T07-51-16-717Z_019f69e8-8fed-7000-a1be-fa49e829e993.jsonl`；
- JSONL SHA-256：
  `a8e06ab26cb03eadfb5ea8f8c6af468d7533ba932a745d6451bdf5a88c6b5792`；
- native model evidence：model-change and assistant events both report
  `deepseek/deepseek-v4-pro`；
- old plan SHA：`41468dda72f4c6502835515ef3573d4a6cb1f0db2336f6328b4db2731493dd78`；
- verdict：`APPROVE`，`P0/P1/P2: none`；two INFO precision findings。

Round 1 INFO were dispositioned rather than waived：

1. measurement now says exact `19-label phase machine with 18 forward transitions`；
2. incident branch now states that `cmd_cleanup` has no external authorization validation，therefore
   its new incident authorization is an explicit procedural hard gate。

Those byte changes invalidated Round 1 approval，so it was not reused。

### Fresh Round 2

- session id：`019f69f1-54db-7000-a9a3-8735c928b1e0`；
- native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-plan-review-deepseek-v4-pro-round2/2026-07-16T08-00-51-419Z_019f69f1-54db-7000-a9a3-8735c928b1e0.jsonl`；
- JSONL SHA-256：
  `681a341e09045daa61b0d23e8f85206c417bb74fce1cf23bd4bb1dac3f4a8055`；
- native model evidence：model-change and assistant events both report
  `deepseek/deepseek-v4-pro`；
- exact plan SHA：`7e8d8846f56d4d62870c63f30705855586adcf34caf2d593f80839952d175fe2`；
- test evidence：`tests/test_p9_3c1_production_controller.py` -> `47 passed`；
- verdict：`APPROVE`，`P0/P1/P2: none`；Round 1 dispositions accepted。

Round 2 reviewed the full plan/controller/tests/P2 artifacts，not only the two-line disposition diff。

## 3. Reviewer findings and Codex disposition

### Blocking findings

`P0/P1/P2: none`。

### INFO-1 — plan SHA is procedurally chained through bootstrap

Authorization carries `p3_bootstrap_sha256`，while controller validates that field's format and exact
auth bytes but cannot itself prove the bootstrap text embeds this plan SHA。Disposition：accepted as an
explicit review responsibility，not a code gap for this operations package。The P3 bootstrap and both
bootstrap/basis reviewers must recompute the exact bootstrap SHA and verify that it embeds this approved
plan SHA。Any mismatch stops before authorization creation/install。

### INFO-2 — renewal timestamp wording

The wait/verification predicates require at least three distinct `renewed_at` observations，representing
at least two renewals after the initial timestamp。Disposition：plan wording “at least two renewals” is
correct and executable；no plan edit required。

## 4. Codex correction to reviewer narrative

Round 2's evidence section briefly described the lock-race failure as if it entered `cmd_run`'s
`except` branch。The code places `_acquire_lock(run_id)` before the `try`。Therefore a lock acquisition
failure does **not** write `preactivation-failed.json` or call `_release_lock`；the already copied live
authorization consumes the root，which must be abandoned。The approved plan and measurement already
state this exact behavior，so the reviewer wording does not create a plan finding or change the verdict。

## 5. Accepted safety conclusions

Independent review and Codex disposition agree that the exact plan：

- preserves P2/failed roots as immutable evidence and requires a fresh P3 root；
- aligns docs-only deployed revision before fresh prepare without restart/runtime-byte delta；
- contains no hidden implementation work；
- matches authorization keys/types/canonical bytes and removes review self-reference；
- accurately separates pre-lock consumed-root、preactivation failure、fixed cleanup and incident states；
- keeps zero provider/network/external delivery budgets；
- matches the five-job/two-unit recovery/resource matrix and dormant-history final state；
- prohibits speculative cleanup、manual unlock、direct DB repair、restart and unreviewed restore；
- authorizes no live mutation。

## 6. Authorization boundary

This approval authorizes only drafting the exact P3 operator bootstrap against plan SHA
`7e8d8846f56d4d62870c63f30705855586adcf34caf2d593f80839952d175fe2`。The bootstrap requires a fresh
independent review before merge/push or any production action。

This review does **not** authorize deploy、fresh `prepare`、authorization creation/install、controller
`run/cleanup`、service restart、catalog/fixture/DB mutation or cleanup of any retained root。

P9_3C1_P3_PLAN_APPROVED_BOOTSTRAP_DRAFT_ONLY_LIVE_MUTATION_BLOCKED
