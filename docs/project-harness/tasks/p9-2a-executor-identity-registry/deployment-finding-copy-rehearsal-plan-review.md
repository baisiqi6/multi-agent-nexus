# P9-2A production-copy rehearsal amendment review

Date: 2026-07-13  
Reviewer: DeepSeek V4 Pro through OpenCode  
Reviewer session: `ses_0a52426d8fferuIup6dzfrteQI`  
Plan SHA-256: `8b2679f453c01e858ce61349179e0edf4c7dd4c0d4428cf01af052ef97141ac7`  
Verdict: **APPROVE**  
Must-fix plan findings: **none**

GLM 5.2 was attempted first as configured, read the plan and reference artifacts,
but produced no verdict across repeated observed windows. Ordinary Kimi was already
quota-exhausted. The operator therefore used the approved lower-priority DeepSeek
fallback for this bounded read-only review; Codex retains implementation result
review and production execution authority.

## Reviewer notes carried into implementation

The plan is complete for authority, transaction boundaries, idempotency, doctor
acceptance, rollback, and production data safety. Current code intentionally does
not yet satisfy the new amendment, so implementation must:

1. validate record-event payload phase and require exact agreement with
   `tasks.phase` before any write;
2. implement missing/equal/conflicting phase states;
3. add exact `repaired_fields` and `restored_phase` audit fields and validate them
   on retry;
4. return `already_repaired` only when both phase and split metadata are exact;
5. merge only whichever validated field or fields are missing.

The reviewer confirmed that retaining one deterministic idempotency key for this
single atomic two-field repair is appropriate. No ledger, historical event,
doctor, schema, task-column, executor, or P9-2B behavior may change.
