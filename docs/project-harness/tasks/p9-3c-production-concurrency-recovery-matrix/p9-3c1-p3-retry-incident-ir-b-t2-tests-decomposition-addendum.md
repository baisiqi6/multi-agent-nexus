# P9-3C1 P3 Retry Incident IR-B — T2 Tests Decomposition Addendum

状态：`DRAFT_FOR_INDEPENDENT_REVIEW_T2_CORRECTION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Purpose and unchanged authority

This addendum does not weaken or replace the approved IR-B plan、bootstraps or T1 review。It decomposes the very
large T2 tests-only gate into independently reviewable checkpoints while runtime implementation remains blocked：

1. T2-A：fixed paths、fd authority、P0 receipt、stale token、sealed TOML、fixed auth copy and exact 18-key auth；
2. T2-B：strict catalog snapshot/classifier；
3. T2-C：fresh fifteen-field pre-acquire proof；
4. T2-D：global acquire、token transaction、rollback、post-install failure matrix、compatibility and disclosure。

Only all four accepted checkpoints may produce exact `T2_APPROVED_IMPLEMENT`。A partial checkpoint may never
emit or imply `T2_READY_FOR_CODEX_REVIEW`。

## 2. Rejected T2/T2-A evidence

The first T2 candidate was incomplete and would fail against a correct implementation because rejection tests
did not catch their expected `ControllerError`。Its catalog fixtures hard-coded placeholder hashes/policy ids。

The replacement T2-A candidate is also rejected。It：

- retained a placeholder receipt digest and substituted unrelated controller/entrypoint hashes for actual
  bootstrap/review artifact hashes；
- created the P0 receipt outside the exact fixed state-root path；
- called replay copy without first consuming the fixed destination；
- labeled an actually canonical receipt as noncanonical；
- supplied positive root-authority files owned by the local user while requiring root ownership，without a
  controlled fd-stat seam；
- omitted owner、nlink、second-fstat drift、short/bounded read and file/directory-fsync failpoints；
- gave sealed-TOML read no `run_id` or expected manifest hash authority and mutated a tracked TOML in place；
- asserted too little after the positive auth copy and omitted most partial-copy failure boundaries。

Delete the rejected T2 block before rebuilding；preserve accepted T1 byte-for-byte。

## 3. T2-A exact test-facing contracts

Names are now fixed so tests and implementation share one reviewed surface：

```python
_read_root_authority_fd(path, *, max_bytes, expected_mode=0o600) -> bytes
_read_canonical_p0_receipt(run_id) -> dict[str, str]
_compute_stale_token_digest(run_id) -> str
_read_sealed_toml(run_id, filename) -> dict[str, Any]
_copy_fixed_resume_auth_once(run_id, external_path, external_sha256) -> bytes
_validate_resume_authorization(run_id, auth) -> dict[str, Any]
```

The fd reader uses an `authority_fstat` seam whose production default is `os.fstat`。Tests override only this
seam to model root uid/gid while preserving the real fd's dev、inode、mode、size、nlink、mtime_ns and ctime_ns。
The seam may be stateful to inject second-fstat identity drift。No test bypasses regular-file、single-link、mode
or bounded-read checks。

The sealed-TOML reader receives `run_id` and the exact manifest key `filename`，opens only
`_config_asset(filename)`，verifies its byte SHA against that run's sealed manifest `config_hashes[filename]`，
then parses those same stable fd bytes。It must not accept an arbitrary expected hash from its caller。

The fixed copy receives the exact run id first，then an absolute external path and bare digest。It copies the
same canonical bytes directly to the fixed destination with `O_EXCL` and returns the retained bytes for the
live guard。A correct replay test performs one successful copy，then calls it again and expects rejection。

## 4. T2-A fixture authority

Build one shared exact incident fixture：

- real eight-record chain and tail assertions from T1；
- fixed live P3 auth at `control/authorization.json` with its actual canonical byte SHA；
- stale standard token at the exact fixed controller path，with digest over its actual 65 bytes；
- P0 receipt at `control/p0-recovery-receipt.json`。Create a separate fixture evidence file，hash its real bytes，
  and place that derived `sha256:<hex>` in the canonical receipt；
- actual sealed manifest/revisions/hashes/config hashes；
- `incident_bootstrap_sha256` and `review_artifact_sha256` derived from the actual approved bootstrap and review
  document bytes in the worker base，never from unrelated installed binaries；
- strictly future time derived relative to the injected `now_utc` seam，not a semantic placeholder；
- valid nonce using the existing grammar。

Every external/fixed authority path is absolute and fd-valid。Where local ownership cannot be root，use the
reviewed `authority_fstat` seam；do not weaken expected production ownership。

## 5. Mandatory T2-A matrix

### A1. Common fd/path authority

Prove positive bytes plus each independent rejection：`O_NOFOLLOW` symlink、directory/non-regular、nlink != 1、
uid、gid、mode、empty/oversized/truncated or short bounded read、first/second fstat dev/inode/size/mtime_ns/ctime_ns
drift、open/read/decode failure and bounded error non-disclosure。Capture the actual open flags and require
`O_RDONLY|O_NOFOLLOW|O_CLOEXEC`。

### A2. Fixed receipt and stale token

Positive receipt and stale digest use the exact fixed paths。Reject every receipt extra/missing key、wrong type、
noncanonical ordering/spacing、missing/extra LF、bad prefix/length/hex、state/phase drift、wrong owner/mode/nlink、
symlink and receipt digest mismatch。Reject stale token missing/extra LF、uppercase/nonhex/wrong length、metadata
drift and raw-token disclosure。

### A3. Sealed TOML

Read all seven manifest-bound TOMLs positively。Reject unknown filename、path redirection、symlink、non-regular、
nlink、first/second identity drift、oversize/decode/parse failure and manifest hash drift。Never mutate a tracked
file；copy a source into a temporary config directory，switch only the `config_dir` seam，and preserve the sealed
manifest hash to create drift。

### A4. Fixed auth copy and replay

Positive copy asserts exact bytes/digest、fixed path、0600、single link and retained return bytes。Reject relative
source、source==destination、source symlink/type/nlink/owner/group/mode、noncanonical JSON、caller SHA mismatch、
pre-existing destination and second-call replay。Inject open/create/write/short-write/fchmod/fchown/file-fsync/
close/control-dir-open/dir-fsync/reopen/revalidation failures。After destination creation，every failure proves the
fixed path remains consumed and is never deleted/repaired；before creation it remains absent。

### A5. Exact 18-key validator

Include one complete positive acceptance。Every rejection uses
`with pytest.raises(ControllerError, match=<boundary>)`，so a correct implementation passes and the current
missing helper's `AttributeError` escapes。Cover every missing key、extra key、every key's wrong top-level type、
bool-as-int、all constants、bare and prefixed digest prefix/length/case/hex、expiry parse/canonical/future、nonce、
run/phase/count/tail、manifest/live-auth/revision/hash/receipt/stale/bootstrap/review bindings and nested exact
key/value types。Add canonical external bytes and fixed-copy drift/replay guard cases。

## 6. T2-A checkpoint gate

Before reporting `T2A_READY_FOR_CODEX_REVIEW`：

- T1 remains the same expected four runtime-negative failures；
- every positive/negative T2-A fixture is shown to reach its intended future helper boundary；
- all pre-existing 47 tests pass；
- only `tests/test_p9_3c1_production_controller.py` changed；
- runtime and deploy-contract tests are byte-identical；
- no commit。

Report exact groups/counts and list T2-B/C/D as still blocked。No T2-A result authorizes implementation，T2-B，
production access or any commit unless Codex sends the next exact checkpoint token。

P9_3C1_P3_RETRY_INCIDENT_IR_B_T2_DECOMPOSITION_AWAITING_INDEPENDENT_REVIEW_ALL_TEST_CORRECTION_RUNTIME_AND_PRODUCTION_BLOCKED
