# P9-3C1 P3 Retry Incident Package IR Replacement — Plan Review

状态：`APPROVED_FOR_IR_A_AND_IR_B_BOOTSTRAPS_ONLY_ALL_PRODUCTION_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Reviewed authority

- Base HEAD：`29c8dd9e5c1b29d1f560e1efe2bb1fe5d43eecdc`。
- Reviewed plan：`p9-3c1-p3-retry-incident-ir-replacement-plan.md`。
- Exact reviewed plan SHA：`1a5f068d2b88668b26de6c09d995ff8ee68ae1a7cc26484f70a9bcaf3f0c8767`。
- Rejected implementation evidence：`p9-3c1-p3-retry-incident-ir-result-review.md`，SHA
  `bbecec9bdaff9fb466bdb6a19a9116cea20b25bcf7b366dc5d7ff1bc639dc2db`。

## 2. Independent review evidence

- Reviewer provider/model：`deepseek/deepseek-v4-pro`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-replacement-plan-review-deepseek-v4-pro/2026-07-16T15-42-39-760Z_019f6b98-2090-7000-8a09-076a118b6c62.jsonl`。
- JSONL SHA：`67af0dd5eee17a56a3754410e0cb7e6f6d2f685d97558073ec1aba8f702ce1b9`。
- Exact first-line verdict：`APPROVE`。
- Reviewer reported no P0/P1 plan findings and confirmed the split preserves the original production sequence、
  partial main commits remain non-deployable、all rejected-candidate blockers have explicit replacement
  contracts，and the test/review gates are proportionate。

## 3. Mandatory bootstrap refinements

The reviewer raised three P2 implementation details。They are incorporated as bootstrap requirements rather
than plan changes：

1. IR-A must bound PID enumeration timeout/output/PID count。Production fixture argv is the actual exact
   `python -m multinexus.agentd --agent p9-3c-fixture-e{1,2}` shape，not an invented `--agent-id` flag。
   NUL argv matching also recognizes an exact controller script component。A PID that exits between enumeration
   and `/proc` read may be treated as exited only after a second exact absence check；permission/I/O/parse drift
   remains fail closed。
2. A copied fixed resume authorization is consumed forensic evidence。It is **not** deleted automatically and
   there is no manual-removal workaround。Any pre-acquire rejection requires a separately reviewed new recovery
   disposition，not silent replay or overwrite。
3. “stale unchanged” requires re-opened single-link/root/mode/shape/digest authority and fsynced directory proof，
   not mtime alone，before a pre-rename safe failure may release the new in-memory token。

## 4. Approval boundary

This review approves：

- merge/push of the result-review、replacement plan and this plan review；
- detailed IR-A bootstrap authoring + independent bootstrap review；
- after IR-A result acceptance/merge，detailed IR-B bootstrap authoring + independent bootstrap review。

It does not authorize worker implementation yet，nor any P0 recover/release、token retirement、source-streaming、
deploy、cleanup、fresh run/auth、service/DB change or production mutation。Only the later exact reviewed worker
bootstrap may authorize its bounded local implementation。

P9_3C1_P3_RETRY_INCIDENT_IR_REPLACEMENT_PLAN_APPROVED_FOR_IR_A_AND_IR_B_BOOTSTRAPS_ONLY_ALL_PRODUCTION_MUTATION_BLOCKED
