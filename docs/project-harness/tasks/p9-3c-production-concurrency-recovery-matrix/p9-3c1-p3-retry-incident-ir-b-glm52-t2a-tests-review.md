# P9-3C1 P3 Retry Incident IR-B — GLM 5.2 T2-A Tests Review

状态：`T2A_APPROVED_PREPARE_T2B_BOOTSTRAP_ONLY`

日期：2026-07-17 Asia/Shanghai

## 1. Candidate and immutable evidence

- worker base：`dd41f28bf013661d3ceb6e4506454a19714f5207`；
- branch：`agents/glm52/p9-3c1-p3-retry-incident-ir-b-r1`；
- worker provider/model：`xfyun/xopglm52`；
- accepted changed path：`tests/test_p9_3c1_production_controller.py` only；
- accepted test-file SHA-256：
  `1364d7710a22fd570eb871e09c902b9cd63ccb23d1dfa45f3469151999fa8914`；
- accepted binary diff SHA-256：
  `8bb438b53603f22d0569012bea322d059210e195cb0ab0b654ecf85a6f6668d7`；
- accepted recovery patch：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-b-worker-glm52-t2a/t2a-approved.patch`；
- accepted recovery patch lines：`2602`；
- accepted recovery patch SHA-256：
  `8bb438b53603f22d0569012bea322d059210e195cb0ab0b654ecf85a6f6668d7`；
- final native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-b-worker-glm52-t2a/2026-07-16T20-39-29-109Z_019f6ca7-e054-7000-86e0-e31812d3155f.jsonl`；
- final JSONL lines：`587`；
- final JSONL SHA-256：
  `479543f6396e662d1de6e5de885b629f16baa87003f2287f8f9051bb22723073`。

The worker session ended normally before these immutable hashes were recorded. No worker process remains.

## 2. Review history

Codex rejected four earlier checkpoints before accepting R5：

1. R1 rejected placeholder or unrelated authority values、fake path/metadata boundaries and incomplete positive
   semantics；
2. R2 required real link counts、separate external authorization bytes、exact fd/path tracking and correct
   destination create/revalidation boundaries；
3. R3 required proof of the exact destination `os.open(..., mode=0o600)` argument and a reachable deterministic
   revalidation failpoint；
4. R4 required a real separate P0 evidence file and corrected incident authority provenance bound to the
   approved IR-B controller-recovery bootstrap/review；
5. R5 removed a same-source evidence-byte assertion and made the revalidation read fault one-shot so a correct
   looping reader is not rejected.

The accepted candidate now derives incident authority from the actual worker-base documents：

- controller-recovery bootstrap SHA-256：
  `1248434ca50a8d779cf25595114567ce00d519951e18ee9ef06627203bbd7f8e`；
- controller-recovery bootstrap-review SHA-256：
  `dabec4a4f12c68d4016d1b4f0ea03e00b0b4c4cdd82d01445d964f352b585fee`。

Import-time assertions bind both constants to the actual document bytes. The GLM correction bootstrap/review
does not masquerade as incident authority.

## 3. Accepted T2-A matrix

The checkpoint contains `205` T2-A cases：

| Group | Contract | Cases | Accepted purpose |
|---|---|---:|---|
| A1 | common fd/path authority | 18 | exact bytes/open flags plus independent path、metadata、bounded-read、drift and non-disclosure boundaries |
| A2 | fixed receipt and stale token | 45 | exact fixed paths、canonical schemas、digest grammar、metadata drift and raw-token non-disclosure |
| A3 | sealed TOML | 19 | all seven positive manifest-bound assets、negative path/type/hash/parse/drift cases and one tracked-file safety meta-test |
| A4 | fixed auth copy and replay | 25 | exact source/destination bytes、flags/mode/root identity、replay and every reviewed pre/post-create failpoint |
| A5 | exact 18-key validator | 98 | one complete positive plus exhaustive key/type/constant/digest/time/nonce/live-binding/replay rejection matrix |

The shared fixture now proves：

- one real eight-record incident chain ending `cleanup.initiated`；
- actual fixed live P3 authorization、stale-token and sealed-manifest bytes；
- a separate `evidence/p0-recovery-audit-entry.json` whose intended canonical bytes plus one LF equal an
  independent disk readback，whose final mode is `0600`，and whose readback digest is stored in the fixed receipt；
- actual incident bootstrap/review byte hashes；
- future expiry derived from the injected `now_utc` seam；
- absolute external/fixed authority paths and the reviewed `authority_fstat` seam.

## 4. Independent Codex verification

Codex independently ran the repository canonical venv and confirmed：

- `py_compile`：PASS；
- `git diff --check`：PASS；
- T2-A：`204 failed, 1 passed, 51 deselected`；
- all `204` T2-A failures are exactly `AttributeError` escapes for the six not-yet-implemented runtime helpers；
- T2-A helper histogram：A1 `18`、A2 receipt `26`、A2 token `19`、A3 `18`、A4 `25`、A5 `98`；
- accepted T1 remains exactly four runtime-negative failures：missing parser/dispatch、wrong terminal sync behavior、
  missing global acquire and missing token transaction；
- all pre-existing controller tests：`47 passed, 209 deselected`；
- complete controller file：`208 failed, 48 passed`；
- controller SHA-256 remains
  `31ca28804c2a5d9252002124c324acb7353a2431af6da82e37e3b9c3ffcecf82`；
- verify entrypoint SHA-256 remains
  `1c18e9f594de794db6760a7eb54fe64fb2b385b36011549a82ec78507676ef6d`；
- runtime/deploy-contract diff is empty；
- no worker commit exists at the reviewed checkpoint.

## 5. Authorization boundary

Codex accepts exact checkpoint token `T2A_APPROVED_PREPARE_T2B_BOOTSTRAP_ONLY`.

This token authorizes only the operator to prepare a detailed T2-B tests-only bootstrap for the strict catalog
snapshot/classifier checkpoint and to send that bootstrap through a separate plan-review gate. It does not yet
authorize a T2-B coding worker.

The operator may commit and push only this acceptance-review document so the checkpoint is durable on `main`.
The accepted red-test patch remains uncommitted in the same isolated worktree and in the immutable recovery
patch above until T2-B/C/D and the later implementation gate are complete.

T2-C、T2-D、runtime implementation、any non-review-doc commit/push/merge、network/SSH、production access、P0
recover/release、cleanup/resume invocation and deployment remain blocked. Only accepted T2-A/B/C/D checkpoints
may later produce exact `T2_APPROVED_IMPLEMENT`.

P9_3C1_P3_RETRY_INCIDENT_IR_B_T2A_APPROVED_PREPARE_T2B_BOOTSTRAP_ONLY_RUNTIME_AND_PRODUCTION_BLOCKED
