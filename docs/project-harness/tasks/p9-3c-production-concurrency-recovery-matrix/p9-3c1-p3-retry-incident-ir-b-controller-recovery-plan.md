# P9-3C1 P3 Retry Incident IR-B — Controller Recovery Detailed Plan

状态：`DRAFT_FOR_INDEPENDENT_PLAN_REVIEW_ALL_IMPLEMENTATION_AND_PRODUCTION_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Outcome and authority boundary

Implement the controller half of the reviewed P9-3C1 incident recovery protocol from exact merged IR-A main
`6ba82a90d3cf0390eba97c472d8eff62261a9d90`。IR-B adds one incident-only `resume-cleanup` path that can consume
one reviewed authorization，acquire a new global P0 lock while the old state-root token is retained as evidence，
atomically archive that stale token，install the new token，and finish the existing cleanup suffix without a
catalog downgrade。

This plan authorizes only its own independent review。It does **not** authorize code changes、worker dispatch、
P0 recover/release、source streaming、token retirement、`resume-cleanup` invocation、ordinary `cleanup`、deploy、
SSH、service/DB mutation、fresh P3 prepare/run or any production write。

The exact production incident remains frozen：

- run id：`p9-3c1-prod-20260716t140135z-dde26886`；
- phase：`agents-online`；
- ledger：exactly eight valid records，tail `cleanup.initiated`；
- standard state token：stale but preserved；
- global P0 lock：held by an absent historical PID until the later separately reviewed IR unlock bootstrap；
- retained catalog：executor exact empty v4，capacity exact empty v2；
- E1/E2：registered online with load zero，units inactive/not-found；
- P9 jobs/leases/deliveries：zero。

No production fact above is treated as evergreen authority：the later runtime command must re-prove every
bound field from live state after the independently reviewed P0 recovery sidecar has made the global lock free。

## 2. Inputs and supersession

Normative inputs：

1. `p9-3c1-p3-retry-incident-ir-replacement-plan.md` and its `APPROVE` review；
2. merged/result-approved IR-A implementation at `6ba82a90...`；
3. the current controller and tests at the same SHA；
4. the earlier rejected all-in-one candidate only as negative evidence，never as source to copy。

This plan refines Package IR-B only。Where a broad older IR bootstrap conflicts with this document，this
document and the approved replacement plan govern。Package EP dynamic epochs remain a later package and must
not leak into IR-B。

## 3. Exact implementation scope

Allowed runtime path：

- `scripts/p9_3c1_controller.py`。

Allowed test paths：

- `tests/test_p9_3c1_production_controller.py`；
- `tests/test_deploy_contract.py` only if one exact installed-controller/entrypoint invariant cannot be covered
  dynamically in the focused controller suite。

No change is allowed to：

- `scripts/production-mutation-lock.py` or its tests；
- `scripts/p9-3c1-production-verify.sh`；the existing wrapper forwards the subcommand and original argv without a
  shell allowlist，so `resume-cleanup` needs no shell change；
- deploy scripts、fixture helper、TOML assets、Coordinate、schema/migrations、daemon/services or docs in the worker
  commit；
- `sessions/` or any production/state-root file。

The worker produces exactly one implementation commit with subject：

```text
fix(p9-3c1): add reviewed incident cleanup resume
```

Its parent must be the exact post-bootstrap `main == origin/main` chosen by the operator。The bootstrap must
prove that runtime/config/test bytes between `6ba82a90...` and that worker base differ only by reviewed docs。

## 4. Current code seams and required decomposition

Current behavior is intentionally insufficient for this incident：

- `cmd_cleanup()` calls `_acquire_lock()`；
- `_acquire_lock()` rejects an existing `control/production-lock.token` before global acquisition；
- `_execute_cleanup_suffix()` appends a new `cleanup.initiated` and，from `agents-online+`，unconditionally runs
  executor v3 → capacity v2 → executor v4；
- `_execute_cleanup_suffix()` releases through the standard token path only after success，which is correct for
  ordinary cleanup but has no incident token-swap transaction；
- no fixed P0 receipt、resume authorization、archive path or incident live-state gate exists。

Implement narrow helpers instead of growing `cmd_resume_cleanup()` into one opaque function。Names may vary，
but responsibilities and call ordering must remain separately testable：

1. fixed path helpers for receipt、resume auth、archive and new-token temp；
2. fd-based root authority reader/copy validator；
3. resume authorization parser and static incident proof；
4. strict catalog snapshot reader/classifier；
5. incident runtime/unit/process/DB observer and validator；
6. in-memory global lock acquire/verify and release helpers；
7. explicit stale-token transaction with named pre-rename、post-rename and post-install states；
8. cleanup suffix options/callbacks that preserve ordinary callers while allowing an already-ledgered incident
   initiation and live-auth revalidation before every mutation。

No generic framework、new class hierarchy or broad controller refactor belongs in IR-B。

## 5. Fixed filesystem authorities

Add exact state-root paths：

```text
control/p0-recovery-receipt.json
control/resume-cleanup-authorization.json
control/.resume-cleanup-new-lock.token.tmp
archive/recovered-production-lock.token
```

The first two and the archived token are durable evidence。The hidden new-token path is transaction-local and
must be absent before acquire；it must not survive a safe pre-rename rollback or a successful standard-token
install。

### 5.1 Common authority read

Security-sensitive reads must use an fd opened with `O_RDONLY|O_NOFOLLOW|O_CLOEXEC`，then require a regular
file、root:root、mode `0600`、`st_nlink == 1`、bounded exact size and stable first/second `fstat` identity around
the read。Convert `OSError`、`ValueError`、decode and parse failures into bounded `ControllerError` messages that
never include token or authorization bytes。

Directory gates use `lstat`/`O_DIRECTORY|O_NOFOLLOW` and exact root:root authority：

- existing `control/` remains the prepared root-only directory；
- `archive/` must be a real directory，root:root，mode `0700`；
- if absent，it may be created only after the new global token is verified held；
- a symlink、wrong type/owner/mode or pre-existing fixed archive target blocks。

### 5.2 P0 recovery receipt

`control/p0-recovery-receipt.json` must be exact canonical JSON plus one LF，with exactly：

```json
{"phase":"free","receipt_digest":"sha256:<64-lowercase-hex>","state":"recovered"}
```

No extra key、alternate ordering/spacing、missing LF or boolean/string coercion is accepted。The resume auth field
`p0_recovery_receipt_digest` must equal the receipt's exact `receipt_digest` value using constant-time string
comparison where practical。

### 5.3 Stale token digest domain

The incident standard token must be the controller's canonical 65-byte representation：64 lowercase hex bytes
plus exactly one LF。`stale_lock_token_digest` is defined unambiguously as：

```text
sha256:<SHA-256 of those exact 65 file bytes>
```

The raw token may exist only in process memory and the root-only token files。It must never enter argv、JSON
result、exception detail、ledger、evidence、stdout/stderr or review artifacts。

## 6. Resume-cleanup authorization contract

Add a separate exact contract，not an extension of `AUTH_EXACT_KEYS`：

```text
contract_version = 1                         # int, bool rejected
action = "p9-3c1-resume-cleanup"
run_id
incident_phase = "agents-online"
incident_ledger_records = 8                 # int, bool rejected
incident_tail_event = "cleanup.initiated"
incident_tail_sha256                        # bare lowercase 64 hex
stale_lock_token_digest                     # sha256:<64 hex>
p0_recovery_receipt_digest                  # sha256:<64 hex>
live_authorization_sha256                   # bare lowercase 64 hex
manifest_sha256                             # bare lowercase 64 hex
installed_revisions                         # exact manifest/current dict
installed_hashes                            # exact manifest/current dict
incident_bootstrap_sha256                   # bare lowercase 64 hex
review_artifact_sha256                      # bare lowercase 64 hex
reviewer_verdict = "APPROVE"
expiry_utc                                  # canonical UTC Z, strictly future
nonce                                       # existing AUTH_NONCE_RE grammar
```

The set is exact and contains 18 keys。`stale_lock_token_digest` and
`p0_recovery_receipt_digest` use a dedicated prefixed-digest validator；all named `*_sha256` values use the
existing bare hash validator。Every integer check explicitly excludes `bool`。Nested revision/hash dicts must
have the same exact key/value types as the sealed manifest；no coercion is allowed。

The external artifact must be absolute、root:root/0600/single-link/regular，not the fixed destination，and its
caller-provided bare SHA must match its exact canonical bytes。Before any copy or acquire，validate：

- exact current phase and full ledger chain；
- exactly eight records and phase/tail agreement；
- tail phase `agents-online`、event `cleanup.initiated` and record SHA bound by the auth；
- manifest canonical bytes/detached SHA/run/state-root；
- live authorization fixed-file identity/SHA and its canonical P3 run/manifest/revision/hash bindings；the old
  P3 authorization need not still be unexpired because it is forensic authority，not the new action authority；
- current installed revisions/hashes equal both manifest and resume auth；
- exact P0 receipt and matching receipt digest；
- stale standard token authority/digest；
- archive target and fixed temp absent；
- an initial strict catalog snapshot already classifies the live executor/capacity state as exact
  `TERMINAL_SKIP`；this is re-read after auth copy、before acquire and again under the new lock；
- reviewer verdict、expiry and nonce。

Only after all zero-write checks pass，copy the exact external auth bytes once to
`control/resume-cleanup-authorization.json` using the destination itself with
`O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`，mode `0600`，then chown/chmod if needed，write exactly all bytes，
`fsync` the file and `control/`，and re-open/revalidate the exact bytes/metadata。Once destination creation
succeeds it is consumed forensic evidence：never overwrite、delete or silently repair it，including on partial
copy failure。Replay always blocks and requires a separately reviewed disposition。

Store the expected fixed bytes/digest in memory and re-open/revalidate the fixed copy before **every** later
authority-changing boundary：pre-acquire、archive creation、temp creation/write、stale rename、new-token install、
directory fsync completion、token-swap ledger append and each cleanup mutation callback。Expiry is rechecked on
every guard；auth drift or expiry after acquisition preserves the new lock according to the transaction state。

## 7. Strict catalog snapshot and decision

### 7.1 Snapshot source

Use the controller's read-only SQLite evidence connection and explicit-column queries，not a lossy CLI `list`
projection。Read target executor/capacity source rows and every authoritative target row：

- executor source：`source_id, source_version, catalog_hash, source_path`；
- definitions：`id, source_id, provider, adapter, capabilities_json, metadata_json`；
- bindings：`agent_id, source_id, executor_definition_id, runner_profile_id, enabled`；
- capacity source：`source_id, source_version, catalog_hash, source_path`；
- policies：`agent_id, source_id, source_version, catalog_hash, capacity_policy_id,
  max_concurrent_jobs`。

Expose one snapshot seam so tests can inject duplicate/non-object/malformed rows that SQLite constraints would
normally prevent。The production reader remains bounded、ordered and read-only。

Derive the expected semantic catalog hashes from the exact immutable TOML content already parsed by
`_validate_config_contract()` using Coordinate's documented canonical objects，without importing mutable
Coordinate runtime state。Before derivation，the TOML file byte SHA must equal the sealed manifest
`config_hashes` entry；the live source path must equal the exact `_config_asset(filename)` path。Expected policy
ids are recomputed as `sha256:` digests from the exact source/version/catalog/policy tuple。Do not compare a
semantic catalog hash to the different raw TOML file hash。

### 7.2 Accepted state classes

The classifier returns exactly one of：

```text
LOWER_MONOTONIC
TERMINAL_SKIP
```

`LOWER_MONOTONIC` accepts the Cartesian set：

- executor absent，or exact v1/v2/v3 source with the exact config-derived definition/binding rows for that
  version；and
- capacity absent，or exact v1 source with its exact two policy rows。

When cleanup entered at `agents-online+`，this decision executes only the existing monotonic sequence：

```text
executor.v3-disabled.toml -> capacity.v2-empty.toml -> executor.v4-empty.toml
```

`TERMINAL_SKIP` accepts only executor exact v4 source/hash/path with zero definitions/bindings **together with**
capacity exact v2 source/hash/path with zero policies。It skips all three catalog sync calls。

Reject before any cleanup mutation and retain the owned lock for every other envelope，including：

- non-list/non-object/extra or missing authoritative keys；
- duplicate target source/definition/binding/policy authority；
- non-integer or boolean version/capacity/enabled drift；
- version below zero、above v4/v2 or unrecognized；
- source id/path/catalog hash drift；
- definition/provider/adapter/capabilities/metadata drift；
- binding agent/definition/profile/enabled drift；
- capacity source/version/hash/policy-id/max drift；
- target rows without their source，foreign rows claiming target agent/definition ids，or partial row sets；
- executor v4 with any executable row；capacity v2 with any policy；
- terminal v4 paired with absent/v1 capacity，or terminal v2 capacity paired with absent/v1/v2/v3 executor。

Unrelated non-target sources remain outside this incident authority and are preserved。

The classification runs at the beginning of `_execute_cleanup_suffix()` before its ledger/helper/Coordinate
mutations whenever the current phase is `agents-online+`。For incident resume，re-read and reclassify after the
new token is installed and before the first suffix mutation。Cleanup from `workspace-ready` or earlier keeps
its existing no-catalog behavior。

## 8. Incident pre-acquire proof

After the fixed auth is durably consumed and immediately before global acquire，perform one fresh bounded
read-only snapshot and require all of the following together：

1. fixed auth still exact and unexpired；
2. global P0 lock is `state in {free, absent}` and `phase == free`；
3. stale standard token metadata/bytes/digest still exact；
4. archive target and fixed temp still absent；
5. phase、ledger count/full chain/tail event/tail SHA still exact；
6. manifest、live-auth、deployed revisions、installed hashes and config byte hashes still exact；
7. P0 receipt still exact；
8. both exact unit names are `inactive` or not-found with `MainPID == 0`；probe command failure、unknown
   state、duplicate/malformed property or nonzero PID blocks；
9. direct bounded PID enumeration and NUL argv classification find no other exact
   `p9_3c1_controller.py` process and no real `python -m multinexus.agentd --agent
   p9-3c-fixture-e{1,2}` process；the current resume controller PID is excluded only by exact PID identity；
   unreadable candidate/probe uncertainty blocks；
10. E1/E2 registry contains exactly two rows，both `online`、`current_load == 0` with bool rejected，and host
    `VM-0-15-ubuntu`；
11. zero jobs in workspace `p9-3c1-production`，zero leases joined to those jobs and zero deliveries through
    that workspace's events；
12. zero executor definitions/bindings and capacity policies，plus the classifier returns exact
    `TERMINAL_SKIP` v4/v2；
13. workspace `p9-3c1-production` and its exact host profile still point to this run's
    `runtime/work`、`runtime`、production CLI and production DB paths；
14. DB integrity `ok`、schema `13`、foreign-key violations `0`；
15. canonical non-fixture projection、launcher identities and manifest-bound backup/revisions/hashes remain
    unchanged。

Use injectable unit/process/incident-observer seams so macOS tests never depend on local systemd or `/proc`。
Default process enumeration follows the already reviewed IR-A bounded discipline：single direct bounded
enumeration，PID count/range limit，NUL argv exact-component classification and fail-closed read/parse errors。
Do not invoke the IR-A `recover` command or duplicate its token-file reader。

Any failure here leaves the stale token and catalogs unchanged and acquires no new lock，but the fixed auth copy
remains consumed。There is no automatic retry or deletion workaround。

## 9. Split global acquisition without changing ordinary behavior

Factor `_acquire_lock()` into：

1. `_acquire_global_lock(run_id)` semantic primitive：require global free，invoke the existing acquire seam/helper，
   parse the returned token and verify `_require_owned_lock(run_id, token)`，but do not inspect or write a state
   token path；
2. existing `_acquire_lock(run_id)` wrapper：retain its existing standard-token absence gate，call the primitive，
   durably persist the canonical token and verify it。

Ordinary `run` and `cleanup` continue to use only `_acquire_lock()` and retain their external behavior/tests。
Only `cmd_resume_cleanup()` may use `_acquire_global_lock()` while the reviewed stale standard token exists。

Add an in-memory release helper used only on proven safe transaction branches：verify exact ownership with the
new token，call exact release，require global free and never touch the stale standard path。If acquire output is
malformed or ownership cannot be proved，do not guess or release。

## 10. Explicit stale-token transaction

The implementation must track at least these monotonic states in local control flow：

```text
NEW_LOCK_HELD
STALE_ARCHIVED
NEW_STANDARD_INSTALLED
SWAP_LEDGERED
CLEANUP_STARTED
```

No broad `finally` or catch-all release is allowed。

### 10.1 Normal sequence

While `NEW_LOCK_HELD`：

1. revalidate auth and stale authority；create/validate root-only `archive/` and exact target absence；
2. create fixed temp with `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`，write canonical new token plus LF，
   `fchmod 0600`、`fchown root:root`、`fsync`、close and re-open/validate it；
3. guard again，rename standard stale token to fixed archive，enter `STALE_ARCHIVED`；
4. guard again，rename fixed temp to standard path，enter `NEW_STANDARD_INSTALLED`；
5. validate archived bytes/digest and new standard bytes/ownership token，then `fsync` both `archive/` and
   `control/` directories；
6. guard again and append one `resume-cleanup.token-swapped` ledger record containing only：external/fixed auth
   SHA、stale token digest、new token **file-byte digest**、P0 receipt digest and archive relative identifier；
7. enter `SWAP_LEDGERED`，guard and invoke the cleanup suffix with incident options；
8. terminal success writes cleanup evidence、`cleanup.completed` and phase `done`，then existing
   `_release_lock()` proves/releases the new standard token and removes only the standard file；the fixed auth、
   receipt and archived stale token remain。

The original record 8 already is `cleanup.initiated`。Incident cleanup must not append a second initiation。
Factor an `initiation_already_ledgered=True` option for this caller；ordinary cleanup defaults remain unchanged。

### 10.2 Failure table

| Boundary | Required state after failure |
|---|---|
| acquire fails before token returned | auth consumed；stale standard unchanged；archive target/temp absent；global state is whatever exact helper reports；no guessed release |
| after new lock verified，before stale rename | remove/fsync temp if created；re-open and prove stale metadata/bytes/digest unchanged and archive target absent；only then release exact in-memory new token |
| temp removal or stale reproof fails | preserve new global lock；do not release；retain all evidence |
| after stale rename，before new standard install | rename archive back to standard；fsync both directories；re-open and prove exact stale restoration and temp cleanup；only then release new token |
| rollback rename/fsync/reproof/cleanup fails | preserve new global lock and observed file evidence；surface original plus rollback boundary without raw bytes |
| new standard rename succeeds | point of no safe release；all later failures keep new global lock and new standard token |
| archive/control fsync fails post-install | keep new standard + global lock；archive remains；no rollback/release |
| token-swap ledger append fails | keep new standard + global lock；archive remains |
| auth expires/drifts post-install | keep new standard + global lock；archive remains |
| catalog/unit/agent/DB/evidence/phase/cleanup fails | keep new standard + global lock；archive remains；never restore stale token |
| success release fails | phase/evidence may be terminal，but new standard/global lock remain for a new reviewed incident disposition |
| full success | phase done；tail cleanup.completed；standard/temp absent；archive/auth/receipt retained；global free |

An empty correctly-owned archive directory may remain after a safe pre-rename failure；the fixed archive target
must remain absent。The implementation must not silently swallow rollback or cleanup exceptions。

## 11. Cleanup suffix compatibility

Extend `_execute_cleanup_suffix()` only through narrow keyword-only controls：

- `initiation_already_ledgered: bool = False`；
- an optional incident `before_mutation` guard callback；
- catalog decision may be injected/read for deterministic tests but must be freshly verified under the held lock。

The guard is called before every suffix authority change：helper stop、helper cleanup、each catalog sync、each
agent deactivate、cleanup evidence write、`cleanup.completed` append、phase write and final lock release。
Read-only checks may run without a guard but any drift blocks。

Ordinary state-machine fallback and `cmd_cleanup()` must retain：

- their existing authorization boundary；
- exactly one `cleanup.initiated` for a newly entered cleanup；
- existing lower-version cleanup behavior；
- existing success release semantics；
- existing active-job/lease fail-closed behavior。

No direct DB write、catalog delete/reset/downgrade or service restart is introduced。

## 12. Test-first implementation matrix

Add failing dynamic tests before runtime implementation。Tests use temp roots、real temp files/SQLite and injected
command/probe seams；none reads production tokens、DB or `sessions/`。

### 12.1 Contract and one-shot copy

Cover：

- valid exact 18-key auth；
- every missing/extra key and wrong constant；
- bool for both integer fields；malformed bare and prefixed digest forms；
- noncanonical JSON、missing/extra LF、bad owner/mode/nlink/type/symlink、external SHA mismatch；
- expired/noncanonical expiry、bad nonce/verdict；
- manifest/live-auth/revision/hash/receipt/stale digest mismatch；
- phase/count/tail event/tail SHA/full-chain mismatch；
- fixed destination replay；
- O_EXCL open、short write、chown/chmod/fsync/dir-fsync and fixed-copy re-read failures；
- once destination creation happens it remains consumed and no acquire/catalog/service/DB mutation occurs。

### 12.2 Catalog classifier

Positive matrix：executor absent/v1/v2/v3 × capacity absent/v1，each exact，returns
`LOWER_MONOTONIC`；exact empty v4+v2 returns `TERMINAL_SKIP` and emits zero sync calls。

Negative parameterization includes every malformed/duplicate/type/path/hash/row/policy-id/foreign-target and
partial terminal combination listed in section 7。Assert the classifier blocks before ledger append、helper
call、Coordinate call or agent deactivation and preserves the owned lock。

Prove exact terminal incident cleanup reaches agents offline、canonical/DB evidence、phase done and exact release
without v3/v2/v4 sync。Prove exact lower states retain the three ordered syncs。Prove ordinary cleanup from earlier
phases remains unchanged。

### 12.3 Pre-acquire live proof

One negative test per field/boundary：global not free；stale/archive/temp drift；unit active/unknown/nonzero PID/
probe error；real controller or E1/E2 argv；PID enumeration/read uncertainty；agent missing/duplicate/offline/
load/host drift；job、lease or delivery residue；workspace/profile path drift；catalog drift；DB integrity/schema/
FK drift；canonical projection、manifest、launcher、revision/hash or P0 receipt drift。Each asserts auth consumed，
no acquire and zero production mutation calls。

### 12.4 Acquire and transaction failures

Inject and assert exact state after：

- free-to-held acquire race；malformed acquire token；owned-lock verification mismatch；
- archive preexistence、mkdir/lstat/chown/chmod failure；
- temp open/write/short-write/fchmod/fchown/file-fsync/close/re-read failure；
- stale rename failure；new-standard rename failure；
- archive-dir and control-dir fsync failure；
- stale archive/new-standard validation drift；
- token-swap ledger failure；
- auth drift/expiry at every guard boundary；
- rollback rename、both rollback fsyncs、temp unlink/reproof and safe release failure；
- catalog、helper stop/cleanup、agent deactivate、canonical、DB、evidence、cleanup ledger、phase and final release
  failures after install。

Assertions cover exact global lock state、standard token bytes/digest/identity、archive target bytes/digest、temp
presence、fixed auth retention、ledger tail/count and complete ordered mutation call trace。Raw tokens are checked
absent from exception/result/captured stdout/stderr/ledger/evidence。

### 12.5 Compatibility and CLI

Cover parser/dispatch for exact `resume-cleanup --run-id --authorization-file --authorization-sha256`，unknown/
missing/duplicate argparse behavior，and prove the thin shell need not change because it forwards the original
subcommand。Rerun existing P3 `run`、ordinary `_acquire_lock/_release_lock`、state-machine fallback and cleanup
tests unchanged。

`tests/test_deploy_contract.py` may change only if a dynamic test is needed to prove the installed controller
contains/dispatches `resume-cleanup` while the wrapper remains byte-unchanged。No source-text-only assertion may
substitute for controller behavior。

## 13. Worker and review routing

After this plan receives independent `APPROVE`：

1. Codex authors a separate exact worker bootstrap with this plan/review SHA、base/allowlist/subject/gates；
2. a fresh non-worker agent independently reviews the bootstrap；
3. preferred Coding worker is OMP `kat-coder/kat-coder-pro-v2.5` in a fresh isolated worktree/session；
4. if KAT is unavailable，use an approved non-Codex fallback，never silently switch provider/model；
5. Codex reviews every changed line and reruns gates；
6. a fresh independent non-worker reviewer returns `APPROVE` with no unresolved P0/P1/P2 before merge。

Native JSONL must prove the exact provider/model，test-first negative evidence，tool calls，commit parent/subject/
allowlist and final tests。A summary without JSONL is not acceptance。

## 14. Required gates

Run from the canonical repository environment with adequate timeout：

```bash
python -m pytest -q tests/test_p9_3c1_production_controller.py
python -m pytest -q tests/test_deploy_contract.py
python -m pytest -q
python -m py_compile scripts/p9_3c1_controller.py
bash -n scripts/p9-3c1-production-verify.sh
git diff --check
git show --check --stat --oneline HEAD
```

Acceptance additionally requires：

- exact one implementation commit and allowed paths only；
- no raw-token literal or logging path added；
- no runtime/config/test drift outside allowlist；
- ordinary controller tests and combined IR-A+IR-B full suite pass；
- independent result verdict `APPROVE` with no unresolved finding。

## 15. Exit boundary

IR-B merge/push remains non-deployable by itself。Only after IR-A+IR-B combined main passes the full gates and
the independent result review is accepted may Codex author the separate exact unlock-to-deploy bootstrap。

That later package must independently review and bind：source-streamed IR-A P0 recovery、receipt capture under
explicit Bash、exact IR-B deploy、fresh incident basis/auth review、one foreground `resume-cleanup` and terminal
dogfood/closeout。None of those production actions is authorized here。

P9_3C1_P3_RETRY_INCIDENT_IR_B_CONTROLLER_RECOVERY_DETAILED_PLAN_DRAFT_FOR_INDEPENDENT_REVIEW_ALL_IMPLEMENTATION_AND_PRODUCTION_MUTATION_BLOCKED
