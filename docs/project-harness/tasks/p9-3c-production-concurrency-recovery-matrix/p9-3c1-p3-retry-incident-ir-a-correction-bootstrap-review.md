# P9-3C1 P3 Retry Incident Package IR-A — Replacement Correction Bootstrap Review

状态：`APPROVED_FOR_BOUNDED_LOCAL_KAT_IMPLEMENTATION_ONLY_ALL_PRODUCTION_MUTATION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Exact reviewed authority

- Initial bootstrap commit：`89565d26b3bec40449095a6738552868188b5e25`。
- Initial bootstrap SHA：`0ec41e2bb7a17f4e44dd0d73b161efc34f6b12e666c462eb6681e6157384dece`。
- Final bootstrap SHA：`9d6c3b0780409eaa27d3c3a4da12dc5c182cd46f00b346d12372163f4df2cbc9`。
- Exact worker base：`f76e4b51eda38f658237590e412a425e29c7b8d0`。
- Exact worker branch/worktree and two-file allowlist are those recorded by the final bootstrap。

## 2. Independent reviewer evidence

- Reviewer provider/model：`xfyun/xopglm52`（GLM 5.2）。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-correction-bootstrap-review-glm52/2026-07-16T16-57-58-613Z_019f6bdd-1455-7000-8b0b-46dad7f0e7a4.jsonl`。
- Final JSONL SHA：`1418cb02e8290a27e0ea17b2553f1122d589afc9df700404682698a0f5ca4633`。
- Final protocol message：`APPROVE` / `No remaining P0/P1`。

The reviewer inspected the complete bootstrap、plan/review chain、rejected candidate and original base。It
verified release fall-through、systemd row structure、default PID parser、`65536/65537` sentinel、leading/
interior/trailing NUL authority、confirmed-exit race、fixture extra args、token-file structured errors and direct
test seams。

## 3. Final clarification adopted

The initial review had no P0/P1。Its only actionable P2 was that the bootstrap said to keep the existing
`systemctl` argv without spelling out every flag。The final bootstrap now fixes the exact command：

```text
systemctl list-units --type=service --state=running,reloading,activating,deactivating --no-pager --no-legend
```

It also fixes `shell=False`、timeout、capture and text behavior。The reviewer verified final SHA
`9d6c3b07...` and confirmed no new P0/P1。

## 4. Authorization boundary

This review authorizes one bounded local OMP `kat-coder/kat-coder-pro-v2.5` worker in the exact clean worktree。
It may mechanically apply the rejected allowlisted diff，then must add correction tests first、preserve failing
evidence、implement only the bootstrap、run canonical gates and create one exact commit。

It does not authorize implementation merge/push、SSH/network、sessions read、production files/DB/token/auth、
P0 recover/release、cleanup/resume、deploy、service/run or any production mutation。Worker completion requires
Codex and a different non-Codex result review。

P9_3C1_P3_RETRY_INCIDENT_IR_A_CORRECTION_BOOTSTRAP_APPROVED_FOR_BOUNDED_LOCAL_KAT_IMPLEMENTATION_ONLY
