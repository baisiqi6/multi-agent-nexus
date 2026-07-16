# P9-3C1 P3 Retry Incident IR-B — KAT-Coder-Pro V2.5 T2-B Tests Bootstrap Review

状态：`APPROVED_FOR_KAT_T2B_TESTS_ONLY_WORKER_RUNTIME_AND_PRODUCTION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Reviewed authority

- Candidate commit：`975913566c026e9ce62f7635ea90d4fbd5879770`。
- Candidate parent：`fa6c67d710cce5a5fe497ab056ff6feebc502d63`。
- Reviewed document：
  `p9-3c1-p3-retry-incident-ir-b-kat25-t2b-tests-worker-bootstrap.md`。
- Exact document SHA-256：
  `4e3d91af54bddd6cb14a61d30e959f0f5743b78b1ed59dd526ea267bd148996d`。
- Document size：247 lines，12314 bytes。
- Candidate commit is docs-only and adds only the reviewed bootstrap。

This review authorizes only creation of the fresh KAT T2-B tests worktree and dispatch of one tests-only worker
under the reviewed bootstrap。T2-C、T2-D、runtime implementation and every production mutation remain blocked。

## 2. Independent reviewer evidence

- Provider/model：`xfyun/xopglm52`（GLM 5.2）。
- Native model evidence：JSONL `model_change == xfyun/xopglm52`；all 34 assistant messages report
  `model == xopglm52`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-b-plan-review-glm52-t2b/2026-07-16T22-41-27-627Z_019f6d17-8c4b-7000-b3dc-f98064b4e328.jsonl`。
- JSONL SHA-256：
  `52f6aef5cf059ec095be41622bf06376b5166799e7ce73a370719b61e076383e`。
- JSONL size：154 lines，696594 bytes。
- Reviewer verdict：`VERDICT: APPROVE`。
- Exact reviewer token：`T2B_BOOTSTRAP_REVIEW_APPROVED`。

The reviewer performed a read-only cross-check of the approved IR-B plan/reviews、T2 decomposition、T2-A
acceptance、controller/tests、all six sealed TOMLs and Coordinate schema/canonical algorithms。It made no
repository、runtime、network or production mutation and invoked no subagent。

## 3. Independently verified conclusions

The reviewer confirmed：

1. candidate commit/document SHA and the operator-applied T2-A patch/prefix/append-only boundary are coherent；
2. `_read_strict_catalog_snapshot()`、`_classify_catalog(run_id)` and the `catalog_snapshot` seam are minimal、
   implementable and non-conflicting with T2-A seams；
3. all five snapshot row shapes match Coordinate schema v13 columns after intentional timestamp stripping；
4. the ordered SQL predicates capture target authority and foreign claims without pulling unrelated rows；
5. the 64-row bound、read-only connection、close-on-success/error and unchanged-DB checks are sufficient；
6. independent recomputation matched all six semantic catalog hashes and both capacity policy ids exactly；
7. B1-B3 cover every malformed、duplicate、type、version、path、hash、row、policy-id、foreign-target and partial
   terminal rejection required by approved plan §7；
8. B2 covers all eight lower Cartesian states and the sole exact v4+v2 terminal state；
9. B4 covers pre-mutation blocking、owned-lock retention、zero-sync terminal cleanup、three ordered lower syncs
   and earlier-phase compatibility without opening T2-C/D；
10. stop tokens、count reporting and no-commit/no-runtime/no-production prohibitions are exact。

## 4. Reviewer residual risks and Codex adjudication

Four non-blocking observations were recorded：

1. T2-A is intentionally an accepted uncommitted recovery patch，not part of `main`。The operator must apply the
   exact patch in the fresh worktree before launch，then enforce diff/file/prefix SHA and byte gates；failure is
   `T2B_BLOCKED`。
2. The accepted byte count `175494` is redundant with the stronger accepted prefix SHA。Codex already verified
   both against the accepted T2-A worktree and exported patch；the worker must verify them again before editing。
3. Owned-lock retention is a future-facing red test while runtime helpers remain absent。This is the intended
   tests-first checkpoint and does not authorize implementation。
4. `max_concurrent_jobs` range drift is covered by the mandatory `policy ... max drift` requirement，in addition
   to explicit bool/non-integer cases。The result reviewer must reject representative-only coverage。

None blocks T2-B tests-only dispatch。

## 5. Exact authorization and next gate

Codex accepts the independent verdict and issues：

`T2B_BOOTSTRAP_APPROVED_START_KAT_TESTS_ONLY_WORKER`

The operator may now：

1. create the exact fresh worktree/branch from the reviewed `WORKER_BASE`；
2. apply the exact accepted T2-A patch without exposing prior sessions to the worker；
3. verify the full-file and accepted-prefix gates；
4. invoke OMP exact `kat-coder/kat-coder-pro-v2.5 --thinking high` under the reviewed bootstrap；
5. supervise native JSONL and submit the resulting uncommitted tests to Codex review。

This token does not authorize T2-C、T2-D、runtime implementation、commit、push/merge、SSH、production access、
P0 recover/release、cleanup/resume invocation or deploy。

P9_3C1_P3_RETRY_INCIDENT_IR_B_T2B_BOOTSTRAP_APPROVED_START_KAT_TESTS_ONLY_WORKER_RUNTIME_AND_PRODUCTION_BLOCKED
