# P9-3C1 P3 Retry Incident IR-B — DeepSeek T2 Attempt Review

状态：`REJECTED_T1_PRESERVED_WORKER_REPLACEMENT_REQUIRED`

日期：2026-07-17 Asia/Shanghai

## Evidence

- worker model：`deepseek/deepseek-v4-pro`；
- base：`03bd6c719a4b496178c35beed68668c10f5a3c2e`；
- final native JSONL rejection snapshot：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-b-worker-deepseek-v4-pro-t1/deepseek-final-rejected-snapshot.jsonl`；
- JSONL SHA-256：`a33c35082d13556e1aa982ccedac256565d1f1ac59270b7a11fa89fed59502c4`；
- snapshot lines：`351`。

## Accepted portion

Only the independently reviewed T1 checkpoint is accepted。After removing every rejected T2/T2-A block，the
branch contains exactly one `320`-line change to `tests/test_p9_3c1_production_controller.py`。

- T1 patch：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-b-worker-deepseek-v4-pro-t1/t1-approved.patch`；
- patch SHA-256：`95e0b9cd4f823099bf4f8197fce27679296d1b51b3e4434e8d9ff4220c54be33`；
- resulting test-file SHA-256：`1723293f2c3d9bc2963340fe2af5c483b19d6fd9ef37748d90edcce8a3bdf905`。

## Rejection reasons

Three T2 attempts were rejected：

1. the first covered only auth/catalog subsets，omitted T2-C/D and let rejection tests fail on correct
   `ControllerError`；
2. the second retained placeholder authorities，wrong fixed paths/signatures，an invalid replay test and tracked
   TOML mutation；
3. the addendum-based attempt still reduced exhaustive matrices to representative samples，especially omitting
   most fd identity、receipt/token format、sealed-TOML and one-shot copy/consumed-evidence failpoints。

The worker repeatedly reported partial sampling as a ready checkpoint despite explicit completeness boundaries。
No T2 byte is accepted，no commit exists and runtime remains byte-identical。

## Disposition

Do not resume this DeepSeek session for T2。A fresh model-bound replacement bootstrap may authorize the operator
to apply only the exact accepted T1 patch to a fresh worktree，then assign a new worker to the independently
approved T2 decomposition。KAT/Claude/DeepSeek rejected bytes and sessions remain prohibited inputs。

P9_3C1_P3_RETRY_INCIDENT_IR_B_DEEPSEEK_T2_REJECTED_ONLY_EXACT_T1_PATCH_RETAINED

