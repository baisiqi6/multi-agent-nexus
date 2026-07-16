# P9-3C1 P3 Retry Incident IR-B — Controller Recovery Worker Bootstrap

状态：`DRAFT_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Role and authority

You are the non-Codex OMP `kat-coder/kat-coder-pro-v2.5` Coding worker。Codex remains architect/operator/result
reviewer。Work only in the isolated local worktree assigned after this bootstrap and its independent review are
merged。

This bootstrap never authorizes SSH/network、reading `sessions/`、production/state-root/token/auth/DB/service
access、P0 recover/release、source streaming、`cleanup`/`resume-cleanup` invocation、deploy、push/merge or any
other repository。Do not use OMP `task`/subagents。

Reviewed authorities to read completely before editing：

- `p9-3c1-p3-retry-incident-ir-replacement-plan.md` and plan review；
- `p9-3c1-p3-retry-incident-ir-result-review.md` as rejected-candidate negative evidence；
- `p9-3c1-p3-retry-incident-ir-b-controller-recovery-plan.md`，SHA
  `39b074be0fe13945694e4e81d13614fdf4bfd0030b2228a972fc033443943f35`；
- `p9-3c1-p3-retry-incident-ir-b-controller-recovery-plan-review.md`，SHA
  `5b80b09f4077c89fc0fde84ad65d0ea19aa67a868e29592c3b773a76ed112364`；
- complete current `scripts/p9_3c1_controller.py` and `tests/test_p9_3c1_production_controller.py`；
- the relevant dynamic installed-controller section of `tests/test_deploy_contract.py` only if needed。

Do not copy、apply、cherry-pick or consult the rejected `344ca2c6...` implementation as source。Its review lists
failure modes only。

## 2. Launch-time exact base and worktree

After this bootstrap and its review are committed/pushed，the operator supplies `WORKER_BASE` in the launch
prompt。Require before editing：

```bash
test "$(git rev-parse HEAD)" = "$WORKER_BASE"
test "$(git rev-parse origin/main)" = "$WORKER_BASE"
git status --short
git diff --quiet 6ba82a90d3cf0390eba97c472d8eff62261a9d90.."$WORKER_BASE" -- \
  scripts multinexus tests config agents.toml
```

Only reviewed docs may differ from merged IR-A runtime base。Expected assignment：

- worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p3-retry-incident-ir-b-kat-r1`；
- branch：`agents/kat/p9-3c1-p3-retry-incident-ir-b-r1`；
- parent：exact launch-time `WORKER_BASE`；
- clean tracked tree and no pre-existing implementation commit。

If any start gate fails，stop without edits。

## 3. Exact allowlist and commit

Only these paths may change：

- `scripts/p9_3c1_controller.py`；
- `tests/test_p9_3c1_production_controller.py`；
- `tests/test_deploy_contract.py` only if a dynamic installed-controller/entrypoint invariant is genuinely needed。

Do not change helper/shell/config/deploy/Coordinate/schema/docs/sessions。No generated artifacts or production
fixtures enter the commit。

Create exactly one implementation commit whose parent is `WORKER_BASE` and subject is：

```text
fix(p9-3c1): add reviewed incident cleanup resume
```

Do not commit until every required gate passes。After commit，do not amend。

## 4. Test-first gate

Add dynamic tests before completing the corresponding runtime behavior。Preserve at least one real failing test
run for each of these four blocks in native JSONL：

1. valid exact 18-key authorization currently has no parser/dispatch path；
2. exact terminal executor v4/capacity v2 currently emits forbidden v3/v2/v4 sync calls；
3. ordinary `_acquire_lock()` currently rejects the reviewed stale standard token before a new global acquire；
4. an injected post-new-standard cleanup failure has no incident transaction that can preserve the new standard
   token/global lock/archive evidence。

The failures must reach actual controller functions，not stop in malformed fixtures or mocks。No skip/xfail、
test deletion、exception swallowing、source-text-only assertion or manufactured timeout。Record exact failing
test names/output before implementing each block。

Use temp roots、synthetic tokens and isolated SQLite only。Never read production or user `sessions/`。

## 5. Fixed paths and safe authority I/O

Add only these incident authorities under the prepared state root：

```text
control/p0-recovery-receipt.json
control/resume-cleanup-authorization.json
control/.resume-cleanup-new-lock.token.tmp
archive/recovered-production-lock.token
```

Implement reusable narrow fd readers：`O_RDONLY|O_NOFOLLOW|O_CLOEXEC`，regular root:root `0600` single-link，
bounded exact read，stable first/second `fstat` identity，bounded redacted `ControllerError` on every
`OSError`/`ValueError`/decode/parse failure。Do not expose raw token/auth bytes。

The receipt is exact canonical JSON+LF with only：

```json
{"phase":"free","receipt_digest":"sha256:<64-lowercase-hex>","state":"recovered"}
```

The stale standard token is exactly 64 lowercase hex plus LF；its auth digest is `sha256:` of the exact 65 file
bytes。

Read every sealed TOML used for semantic catalog derivation with the same
`O_RDONLY|O_NOFOLLOW|O_CLOEXEC`、regular/single-link、stable first/second `fstat` discipline。Verify its byte SHA
against manifest `config_hashes` before deriving its semantic hash；do not use path-only or two unrelated reads。

## 6. Exact resume authorization and one-shot copy

Add a separate 18-key contract exactly as plan §6。Mandatory details：

- `contract_version == 1` and `incident_ledger_records == 8` are integers with bool rejected；
- constants are action `p9-3c1-resume-cleanup`、phase `agents-online`、tail `cleanup.initiated`；
- stale/receipt digests use exact `sha256:<64hex>` validator；named `*_sha256` fields use bare 64 hex；
- compare prefixed digest strings through one explicit `hmac.compare_digest` helper，with matching/mismatching
  dynamic tests；
- exact key set、canonical JSON+LF、root/single-link/mode、caller SHA、expiry、nonce、verdict、manifest/live-auth/
  revision/hash/ledger/tail/receipt/stale-token authority all bind before copy；
- the old fixed P3 live auth is forensic identity and need not remain unexpired；the new resume auth must remain
  strictly future at every guard。

Before any write/acquire，strictly classify the catalog as exact terminal v4/v2 and prove all plan §6 zero-write
bindings。Then copy exact external bytes once to the fixed destination using the destination fd itself with
`O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`、root `0600`、file fsync、control-dir fsync and fd-based re-read。

Once destination creation succeeds，never delete/overwrite/repair it，even after a short write or fsync failure。
Replay blocks。Re-open and compare its exact expected bytes/metadata/expiry before every later authority-changing
boundary。

## 7. Strict catalog classifier before mutation

Use read-only SQLite explicit-column queries plus one injectable snapshot seam。Read source path/hash/version and
all authoritative definition/binding/policy fields named in plan §7。Also detect foreign rows claiming target
ids/agents。Reject non-list/non-object/extra/missing keys、duplicates、bool/non-int、path/hash/row/policy-id drift。

Derive expected semantic catalog hashes and capacity policy ids from exact manifest-bound TOML canonical objects；
raw file SHA and semantic catalog hash are different domains。

Only two decisions exist：

- `LOWER_MONOTONIC`：executor absent/exact v1/v2/v3 × capacity absent/exact v1；run existing ordered
  v3 → capacity v2 → executor v4；
- `TERMINAL_SKIP`：executor exact empty v4 **and** capacity exact empty v2；skip all syncs。

Every partial terminal pair，higher/unrecognized version，v4/v2 with rows or malformed state blocks before
cleanup ledger/helper/Coordinate/agent mutation and retains the owned lock。Unrelated sources remain untouched。

Classify at the start of cleanup for `agents-online+`，and re-read under the new incident lock immediately before
the first suffix mutation。Earlier-phase ordinary cleanup keeps its existing no-catalog behavior。

## 8. Exact pre-acquire live proof

After fixed auth consumption and immediately before acquire，re-prove all 15 plan §8 conditions：fixed auth、
global free、stale/archive/temp、phase/ledger、manifest/live-auth/revisions/hashes/config、receipt、units、processes、
agents、zero P9 jobs/leases/deliveries、terminal catalog、workspace/profile、DB and canonical/launcher/backup
identity。

Unit acceptance is only exact inactive or not-found with `MainPID == 0`。Unknown/failed/active/property/probe
drift blocks。

The direct process probe is bounded and injectable：one bounded PID enumeration，strict positive PID range，
NUL-delimited exact argv component classification，exclude only the current resume controller PID，and fail closed
on unreadable candidate/parse/probe uncertainty。Recognize exact controller script component and real
`python -m multinexus.agentd --agent p9-3c-fixture-e{1,2}`。Parent SSH/bash/grep/editor text and token paths do
not match。Tests run via seams on macOS；do not invoke IR-A `recover` or copy its token reader。

Any rejection consumes fixed auth but performs no acquire/catalog/DB/service mutation。

## 9. Split lock acquisition

Factor one in-memory global primitive from `_acquire_lock()`：

- require global free；
- invoke existing acquire seam/helper；
- parse and verify exact owned token；
- do not inspect or write standard state token path。

Keep `_acquire_lock(run_id)` as the ordinary wrapper with its existing token-path absence gate and persistence；
`run` and ordinary `cleanup` continue using only it。Only `resume-cleanup` uses the in-memory primitive while the
reviewed stale standard file exists。

Add an incident safe-release helper that verifies/releases the exact in-memory new token and proves global free
without touching stale standard authority。Malformed/unknown acquire authority is never guessed or released。

## 10. Stale-token transaction and rollback

Use explicit monotonic states，not a broad `finally`：

```text
NEW_LOCK_HELD -> STALE_ARCHIVED -> NEW_STANDARD_INSTALLED -> SWAP_LEDGERED -> CLEANUP_STARTED
```

Under `NEW_LOCK_HELD`：

1. revalidate auth/stale；create or validate real root:root `0700` `archive/`；the empty directory may now exist，
   but the fixed archive target remains absent；
2. create exact fixed temp `O_EXCL|O_NOFOLLOW`，write new token+LF，fchmod/fchown/fsync and revalidate；
3. guard，rename stale standard to fixed archive；
4. guard，rename temp to standard；this is the point of no safe release；
5. validate archived stale digest and new owned standard token；fsync both archive/control directories；
6. guard and append `resume-cleanup.token-swapped` with digests/auth SHA/receipt/relative archive id only；
7. guard and call cleanup suffix without a second `cleanup.initiated`；
8. success alone writes cleanup evidence/completed/done then existing `_release_lock()` releases/removes the new
   standard；archive/auth/receipt remain。

Failure behavior is exact：

- before stale rename，remove+fsync temp，re-open/prove stale unchanged and archive target absent，then release；
- temp cleanup or stale reproof failure preserves new global lock；
- after stale rename/before new install，rename archive back，fsync both dirs，reprove exact restoration and temp
  cleanup，then release；
- rollback failure preserves new lock/evidence and is never swallowed；
- after new standard rename，every fsync、ledger、auth、catalog、helper、agent、DB、evidence、phase、cleanup or
  release failure preserves the new standard/global lock and archive；never restore/release；
- full success leaves phase done，tail cleanup.completed，standard/temp absent，archive/auth/receipt retained，
  global free。

Tests assert exact file bytes/digests/presence、global state、ledger tail/count and ordered call trace at every
injected boundary。Raw token absence is asserted in result/error/stdout/stderr/ledger/evidence。

## 11. Cleanup suffix compatibility

Use only narrow keyword-only controls：defaulted `initiation_already_ledgered=False` and optional
`before_mutation` guard。The incident passes true and its live fixed-auth guard；ordinary callers remain unchanged。

Call the guard before every helper stop/cleanup、catalog sync、agent deactivate、cleanup evidence write、
cleanup.completed append、phase write and final release。Read-only drift blocks。

Preserve current ordinary `run`/cleanup/fallback authorization、single initiation、active job/lease halt、lower
catalog sequence and exact success release。No direct DB write、catalog delete/reset/downgrade、service restart or
new catch-and-release path。

## 12. Parser and tests

Add Python CLI only：

```text
resume-cleanup --run-id --authorization-file --authorization-sha256
```

The thin shell already forwards arbitrary subcommand argv，so it must remain byte-unchanged。

Implement every dynamic test group in plan §12，including：

- full auth/type/digest/canonical/authority/copy/replay/fsync matrix；
- positive lower Cartesian catalog matrix、terminal skip and every rejected envelope；
- one pre-acquire rejection per live field；
- acquire race/malformed/ownership uncertainty；
- archive/temp/write/chown/chmod/fsync/rename/revalidation failures；
- every rollback failure and every post-install cleanup failure；
- ordinary acquire/run/cleanup/state-machine compatibility；
- parser/dispatch and raw-token non-disclosure。

Prefer parameterized rows and shared test fixtures，but do not merge semantically different failure boundaries
into assertions that cannot prove their exact state。

## 13. Required gates

Canonical Python：`/Users/yinxin/projects/multinexus/.venv/bin/python`。

```bash
/Users/yinxin/projects/multinexus/.venv/bin/python -m py_compile \
  scripts/p9_3c1_controller.py tests/test_p9_3c1_production_controller.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q \
  tests/test_p9_3c1_production_controller.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_deploy_contract.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q
bash -n scripts/p9-3c1-production-verify.sh
git diff --check
```

Full-suite timeout at least `20m`；timeout is not PASS。Fix only allowlisted failures。

Before commit prove：

```bash
git diff --name-only "$WORKER_BASE" --
git diff --check
git diff -- scripts/p9-3c1-production-verify.sh scripts/production-mutation-lock.py
```

The last command must be empty。

## 14. Worker completion receipt

Create the one exact commit and stop。Report：

- native provider/model；
- `WORKER_BASE`、commit、parent、subject；
- changed paths and diffstat；
- exact test-first negative commands/failures；
- every final gate command/count/exit；
- exact accepted catalog classes and rejected envelope behavior；
- exact transaction state for each injected boundary；
- confirmation of no session/production/network/push/merge/deploy access。

Do not claim implementation acceptance。Codex line review、independent reruns and a fresh non-worker result review
remain mandatory before merge。Even an approved merged result remains non-deployable until a separate reviewed
unlock-to-deploy bootstrap。

P9_3C1_P3_RETRY_INCIDENT_IR_B_CONTROLLER_RECOVERY_WORKER_BOOTSTRAP_DRAFT_FOR_INDEPENDENT_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED
