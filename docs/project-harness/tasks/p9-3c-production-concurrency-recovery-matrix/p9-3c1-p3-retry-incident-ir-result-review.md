# P9-3C1 P3 Retry Incident Package IR — Result Review

状态：`REQUEST_CHANGES_ALL_MERGE_DEPLOY_RECOVER_RESUME_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Exact candidate authority

- Worker base/parent：`29c8dd9e5c1b29d1f560e1efe2bb1fe5d43eecdc`。
- Rejected worker commit：`344ca2c6b349181423e915769c0ab1aa873a9786`。
- Exact subject：`fix(p9-3c1): add incident recovery primitives`。
- Changed paths only：
  - `scripts/p9_3c1_controller.py`；
  - `scripts/production-mutation-lock.py`。
- Diffstat：`428 insertions(+), 26 deletions(-)`；`git show --check` exit `0`。
- The candidate branch remains immutable evidence and is not merged。

## 2. Worker evidence boundary

- Native provider/model：`kat-coder/kat-coder-pro-v2.5`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-worker-kat-coder-pro-v2.5/2026-07-16T15-02-38-838Z_019f6b73-7df6-7000-99f4-62388277067c.jsonl`。
- JSONL SHA：`4c60279c880ba22ebf85c780e55558e93ff1d459e050847c90c82fbf9b0cf4d9`。
- Focused existing suites：lock `58 passed`；controller `47 passed`；deploy contract `39 passed`。
- Worker full suite exceeded its 300-second command timeout。This is `TIMEOUT`，not `PASS`。
- No test file or test function changed，so none of the bootstrap-mandated new behavior/failure boundaries
  has direct regression coverage。

## 3. Codex blocking findings

### P0 — every valid incident authorization is rejected

`scripts/p9_3c1_controller.py:1276-1279` validates `stale_lock_token_digest` and
`p0_recovery_receipt_digest` with bare `AUTH_SHA_RE`。The reviewed contract requires exact
`sha256:<64hex>` for those two fields。A canonical contract-shaped artifact reproduces：

```text
ControllerError: resume-cleanup authorization stale_lock_token_digest is malformed
```

Separate bare `*_sha256` and prefixed digest validators are required，with strict non-bool field types。

### P0 — `resume-cleanup` cannot acquire the new lock

`cmd_resume_cleanup()` proves the stale standard token exists，then calls ordinary `_acquire_lock()`。
Ordinary acquire rejects `os.path.lexists(lock_token_path(run_id))` before any acquire seam/helper call。
An isolated exact-path reproduction returns：

```text
ControllerError: production lock token file already exists
```

IR requires a distinct acquisition primitive that acquires only the global P0 token while intentionally
leaving the reviewed stale state-root token untouched until the transaction begins。

### P0 — uncertain cleanup releases the new lock

The single broad `except Exception` covers archive creation、token swap、ledger append and the complete
cleanup suffix，then always attempts `_call_lock_release(new_token)`。If failure occurs after new-standard
install or after any cleanup mutation，this releases the only exclusion authority and directly violates the
reviewed held-lock preservation rule。

The transaction must track explicit boundaries。Only a proven pre-standard safe failure may restore stale
authority，fsync and release the in-memory new token。After new-standard install，any uncertain failure keeps
the new global lock and standard token held。

### P1 — incident authority is not live-bound or one-shot

The candidate compares `incident_phase`、record count and tail event only with constants。It does not prove
the current phase、ledger count、tail event/record SHA；does not compare `live_authorization_sha256` to the
fixed live authorization；does not bind an installed P0 recovery receipt；and does not perform the required
pre-acquire exact runtime/DB/unit/process/job/lease checks。

`RESUME_CLEANUP_AUTH_FILE` is unused。The external auth is never copied once to fixed
`control/resume-cleanup-authorization.json`，so there is no `O_EXCL|O_NOFOLLOW` replay boundary、root
single-link receipt or live-copy revalidation。

### P1 — stale-token archive and rollback authority are wrong

The candidate constructs `control/archive/recovered-production-lock.token`。The reviewed authority is
state-root `archive/recovered-production-lock.token`。The archive directory is not explicitly rejected as a
symlink/non-directory；rollback after stale rename does not fsync the restored directory；rollback errors are
silently swallowed before new-lock release。These paths can leave forensic and lock authority split。

### P1 — catalog fail-closed envelope is incomplete

The bounded reader selects the first matching source row and counts filtered rows，but does not require exact
one-source envelope、integer version、expected catalog hash/source path or compatible exact row sets。The
decision explicitly rejects only versions above v4/v2。Terminal v4/v2 with executable rows、duplicate or
malformed sources and partial terminal/lower combinations fall into lower sync attempts rather than being
rejected before mutation。

This is not accepted as “eventually Coordinate rejects a downgrade”。The bootstrap requires an explicit
pre-mutation fail-closed decision and owned-lock retention for every incompatible state。

### P1 — process probe does not meet the no-self-match contract

Replacing `pgrep` with direct `ps` removes the probe command's own query text，but matching arbitrary argv
substrings and excluding only the helper PID can still classify an SSH parent shell/editor/grep whose command
contains a controller or fixture token as a live controller。The reviewed contract explicitly requires the
recovery invocation、token-file path、SSH shell and probe itself not to self-match。This needs exact argv/process
classification and direct tests，not an assumption about the future shell command line。

### P1 — mandatory tests are absent

No tests were added for token-file authority、corrected real probes、exact v4/v2 idempotence、rejected catalog
envelopes、canonical incident auth、one-time copy/replay、receipt/live drift、special acquire race、every token
swap boundary、rollback/fsync failure or cleanup-failure lock preservation。The existing green tests therefore
prove only that old paths were not obviously broken。

## 4. Independent result review

- Reviewer provider/model：`deepseek/deepseek-v4-pro`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-result-review-deepseek-v4-pro/2026-07-16T15-34-00-460Z_019f6b90-340c-7000-ae81-88069ef99893.jsonl`。
- JSONL SHA：`a9eedbe184c639554c5ef012d133fec2619bcd8bd34c76c4385d9433b906a120`。
- Exact verdict：`VERDICT: REQUEST_CHANGES`。
- Reviewer independently confirmed the three P0s、wrong archive、missing fixed auth/live ledger binding、no
  new tests and full-suite timeout。

Two reviewer statements are not adopted as authority：the JSONL briefly misidentified the already-verified
KAT worker identity；and it downgraded incomplete catalog/process envelopes to P2。The reviewed bootstrap is
stricter，so Codex retains both as correction-blocking P1 findings。Neither discrepancy changes the shared
`REQUEST_CHANGES` verdict。

## 5. Replacement boundary

The rejected commit must not be amended、merged、deployed or source-streamed。A replacement implementation
starts from exact main `29c8dd9e...` and produces a clean independently reviewed tree with the complete test
matrix。The correction bootstrap may narrow work into separately reviewable helper/controller packages，but
the production incident remains locked until both are merged and reviewed together。

No P0 recover、manual release、ordinary cleanup、`resume-cleanup`、deploy、service or DB mutation is authorized
by this review。The existing production lock/token/ledger/root and canonical services remain untouched。

P9_3C1_P3_RETRY_INCIDENT_IR_RESULT_REQUEST_CHANGES_ALL_MERGE_DEPLOY_RECOVER_RESUME_BLOCKED
