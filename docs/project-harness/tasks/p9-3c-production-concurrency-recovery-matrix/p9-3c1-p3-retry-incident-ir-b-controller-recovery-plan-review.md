# P9-3C1 P3 Retry Incident IR-B — Controller Recovery Plan Review

状态：`APPROVED_FOR_EXACT_WORKER_BOOTSTRAP_ONLY_ALL_IMPLEMENTATION_AND_PRODUCTION_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Reviewed authority

- Reviewed base commit：`0b58d706c3ea1dfe35bb1687bfcd21fad9e2caad`。
- IR-A merged implementation base：`6ba82a90d3cf0390eba97c472d8eff62261a9d90`。
- Reviewed plan：`p9-3c1-p3-retry-incident-ir-b-controller-recovery-plan.md`。
- Exact reviewed plan SHA：`39b074be0fe13945694e4e81d13614fdf4bfd0030b2228a972fc033443943f35`。
- Plan size：533 inserted lines；the reviewed commit changes only that plan document。

## 2. Independent review evidence

- Reviewer provider/model：`xfyun/xopglm52`（GLM 5.2）。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-b-plan-review-glm52/2026-07-16T19-00-20-707Z_019f6c4d-1c62-7000-92f0-79cdc1b9a3bb.jsonl`。
- JSONL SHA：`10cc45cf153129a753c36e8b24ebbd70eaf0a226846e54a7a592722591ee1d0a`。
- Native `model_change`：`xfyun/xopglm52`。
- Exact first-line verdict：`APPROVE`。
- Reviewer summary：P0 `0`，P1 `0`，three non-blocking P2 implementation refinements；the reviewer explicitly
  concluded there are no unresolved P0/P1/P2 and that the plan is complete、internally consistent、implementable
  and aligned with the approved replacement authority。

## 3. Confirmed plan properties

The reviewer independently confirmed：

- the 18-key resume authorization separates bare `*_sha256` fields from prefixed receipt/token digests and
  rejects boolean integers；
- one-shot fixed auth copy uses exact `O_EXCL|O_NOFOLLOW`、file+directory fsync and permanent replay blocking；
- catalog state has only `LOWER_MONOTONIC` and exact v4/v2 `TERMINAL_SKIP` accepted classes，with malformed、
  partial、higher、path/hash/row drift rejected before mutation；
- the fresh pre-acquire proof covers phase/ledger/live auth/receipt/token/unit/process/agent/job/lease/delivery/
  workspace/profile/catalog/DB/canonical/revision authority；
- global acquisition is split from standard token persistence without widening ordinary `run/cleanup`；
- the token-swap state machine and failure table preserve the new lock after standard installation or any
  uncertain rollback/cleanup boundary；
- the cleanup suffix avoids a duplicate incident `cleanup.initiated` while retaining ordinary behavior；
- the test matrix covers the previously missing contract、copy、catalog、pre-acquire、transaction、rollback、
  post-install preservation and compatibility proofs；
- scope and exit gates keep helper/shell/config/Coordinate/deploy/production work blocked。

## 4. Mandatory bootstrap refinements

The three reviewer P2 notes are accepted as mandatory bootstrap details，so they are no longer open design
questions for the worker：

1. Use one explicit helper based on `hmac.compare_digest` for the two prefixed-digest equality checks and cover
   both matching and mismatching paths dynamically。
2. State and test the distinction between the `archive/` directory and its fixed target：after
   `NEW_LOCK_HELD` the correctly-owned empty directory may exist，but
   `archive/recovered-production-lock.token` must remain absent until the stale-token rename；safe pre-rename
   failures may leave only the empty directory。
3. Read each sealed TOML used for semantic catalog derivation through `O_RDONLY|O_NOFOLLOW|O_CLOEXEC` with
   regular-file/single-link and stable first/second `fstat` identity around the bounded read，then verify the byte
   SHA against manifest `config_hashes` before deriving semantic hashes。A path-only or two unrelated reads are
   insufficient。

## 5. Approval boundary

This review approves only：

1. fast-forward merge/push of this review document；
2. authoring one exact IR-B worker bootstrap bound to the reviewed plan/review SHAs；
3. a fresh independent bootstrap review。

It does not yet authorize worker implementation，nor any P0 recover/release、source streaming、token access or
retirement、`resume-cleanup`/ordinary cleanup、deploy、SSH、service/DB/catalog mutation、fresh P3 run or other
production write。Only a later independently approved bootstrap may authorize bounded local worker work。

P9_3C1_P3_RETRY_INCIDENT_IR_B_CONTROLLER_RECOVERY_PLAN_APPROVED_FOR_EXACT_WORKER_BOOTSTRAP_ONLY_ALL_IMPLEMENTATION_AND_PRODUCTION_MUTATION_BLOCKED
