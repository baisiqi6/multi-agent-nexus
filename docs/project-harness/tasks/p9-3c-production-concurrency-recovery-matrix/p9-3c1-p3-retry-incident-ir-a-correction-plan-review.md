# P9-3C1 P3 Retry Incident Package IR-A — Replacement Correction Plan Review

状态：`APPROVED_FOR_BOUNDED_LOCAL_KAT_IMPLEMENTATION_ONLY_ALL_PRODUCTION_MUTATION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Exact reviewed authority

- Result-review/initial-plan commit：`c79070f91fa798c666702185376e0e1b66354a8b`。
- Result review SHA：`61e65548e8f76cc34b84558c19d9ba5ea701975fc5f16fca23e2f3f13a5a770d`。
- Initial correction plan SHA：`9e38670cd357cc342a141c185ede33710a5a71acfe58c943bcafc4fe3cddd61a`。
- Final correction plan SHA：`e467320dcd470fc4f29a7b3ec7261be6b6523b3caf54f643abca032b970cf4ff`。
- Worker base/parent remains exact `f76e4b51eda38f658237590e412a425e29c7b8d0`。
- Exact implementation allowlist remains the helper and its one test module only。

## 2. Independent reviewer evidence

- Reviewer provider/model：`xfyun/xopglm52`（GLM 5.2）。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-correction-plan-review-glm52/2026-07-16T16-46-28-223Z_019f6bd2-8b7f-7000-ba84-0d0d4f6f71dc.jsonl`。
- Final JSONL SHA：`0859db24160d81dfee99d810f3dc6d98e533452bbee849d3ce3dd709a5b9577c`。
- Final protocol message：first line `APPROVE`；second line `No remaining P0/P1`。

The reviewer independently inspected the rejected commit object、original bootstrap/review、result review and
correction plan。It confirmed exact coverage for the release P0、PID stderr、`65537` sentinel、default-enumerator
test gap、wrong-owner fixture gap and token-file `ValueError` boundary。

## 3. Adopted P2 wording corrections

The initial review approved the plan but identified three non-blocking clarity issues。All were adopted before
final authorization：

1. systemd malformed-row language now distinguishes invalid unit-name authority from well-formed unrelated/
   obsolete units；
2. the production prohibition explicitly enumerates P0 recover、release、cleanup、resume、deploy、service and DB；
3. PID count wording now matches the bootstrap's `131072 unique positive decimal PIDs` contract。

The reviewer re-read the exact final SHA and confirmed these edits introduced no P0/P1。

## 4. Authorization boundary

This review authorizes one bounded local replacement-worker attempt from exact base。First candidate is OMP
`kat-coder/kat-coder-pro-v2.5`。It authorizes applying the rejected allowlisted diff only as an uncommitted
starting tree，adding the mandatory failing regressions first，correcting runtime，running canonical gates and
creating one exact replacement commit。

It does not authorize merge/push of implementation、SSH/network、sessions read、production DB/token/auth、P0
recover/release、cleanup/resume、deploy、service or any production mutation。Worker completion still requires
Codex result review and a different non-Codex independent result review。

P9_3C1_P3_RETRY_INCIDENT_IR_A_CORRECTION_PLAN_APPROVED_FOR_BOUNDED_LOCAL_KAT_IMPLEMENTATION_ONLY
