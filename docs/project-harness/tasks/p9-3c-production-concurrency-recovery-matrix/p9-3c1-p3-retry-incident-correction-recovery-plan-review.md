# P9-3C1 P3 Retry Incident — Correction and Recovery Plan Review

状态：`APPROVED_FOR_PLAN_MERGE_AND_IR_BOOTSTRAP_ONLY`

日期：2026-07-16 Asia/Shanghai

## 1. Exact candidate

- Candidate commit：`b82820e89f071d168aeba0d2a55709f0f0cdaeca`。
- Parent：`dde26886cfbd2ba223896db3687d8bd624a11553`。
- Measurement SHA：`b6f05c8b3d9756871d0e18ae56e3f2449e10b968ede11ed32dd844582d933724`。
- Detailed plan SHA：`c4fdac88ed16a65f1c4a11f2d7e1d84d65443f71e82f1312aaae2c10a4bcc66a`。
- Candidate changes exactly two docs files；runtime/config/tests unchanged。

## 2. Reviewer evidence

Primary reviewer：

- provider/model：`deepseek/deepseek-v4-pro`；
- native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-plan-review-deepseek-v4-pro/2026-07-16T14-45-36-145Z_019f6b63-e311-7000-acb6-4387b087c011.jsonl`；
- final JSONL SHA：`c1a0b6d560e69919d1b411b8b7dd4562d1f0eaaab85a0ba3f7bb75eb60435e1d`；
- replacement receipt first line：`APPROVE`；second line：`P0/P1/P2: none`。

An earlier fresh KAT plan-review attempt reached its eight-minute deadline without a verdict。Its incomplete
JSONL is retained at：

`/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-plan-review-kat-coder-pro-v2.5/2026-07-16T14-37-26-807Z_019f6b5c-6b95-7000-9d0f-4137496adb76.jsonl`

with SHA `d4d0d83ff8114134998c9697bbdca59a2afe1a91e6faede800fc3390412f24d4`。It grants no gate。

## 3. Recomputed findings

The approved reviewer independently confirmed：

- hidden forward `v1 < v4` followed by visible cleanup `v3 < v4`；
- phase `agents-online`、eight ledger records、tail `cleanup.initiated`、stale held owner PID absent；
- empty executor v4/capacity v2，E1/E2 online load 0，zero P9 jobs/leases and no active P9 units；
- DB `ok/13/0` and canonical service PID/NRestarts unchanged；
- installed systemd prefix false negative and process probe self-match defects；
- normal deploy blocked until a reviewed source-streamed helper releases only the stale global lock；
- stale state-root token remains after P0 recover and requires distinct incident-authorized re-acquisition；
- IR/EP separation、legacy exact-terminal cleanup and later monotonic epoch protocol are necessary。

## 4. Required bootstrap clarifications

The IR worker/bootstrap must make these non-blocking reviewer INFO items exact acceptance criteria：

1. archive the consumed stale token under a root-only state-root forensic `archive/` authority；
2. make `--token-file` and direct `--token` mutually exclusive；
3. implement a distinct recovery lock acquisition path that expects the stale standard token file；
4. if stale-token archive succeeds but new-token installation fails，rename the archive back before releasing
   the new global token。

These clarify the approved plan；they do not authorize implementation or mutation。

## 5. Approval boundary

This review authorizes fast-forward merge/push of the exact plan docs plus this review，and authoring the
Package IR worker bootstrap。The bootstrap itself requires a fresh independent review before any worker
implementation。No deploy、source-streamed recover、token retirement、cleanup、fresh prepare/auth/run or
other production mutation is authorized。

P9_3C1_P3_RETRY_INCIDENT_CORRECTION_RECOVERY_PLAN_APPROVED_FOR_PLAN_MERGE_AND_IR_BOOTSTRAP_ONLY
