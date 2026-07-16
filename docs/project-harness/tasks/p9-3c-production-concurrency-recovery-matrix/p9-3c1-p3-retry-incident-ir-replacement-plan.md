# P9-3C1 P3 Retry Incident Package IR — Replacement Plan

状态：`READY_FOR_INDEPENDENT_PLAN_REVIEW_ALL_PRODUCTION_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Purpose and authority

Replace rejected commit `344ca2c6b349181423e915769c0ab1aa873a9786` with a clean、tested Package IR
implementation while preserving the already-approved incident recovery plan。The rejected commit is negative
evidence only：no cherry-pick、no amend、no merge、no deploy、no source streaming。

This plan changes implementation packaging，not the production recovery sequence or authorization boundary。
It authorizes only independent plan review。No code change、P0 recover/release、deploy、cleanup、service/DB
mutation or production probe is authorized yet。

## 2. Why replacement is split

The first worker attempted two security-sensitive runtimes plus all tests in one bounded session，produced
`428 insertions` with zero new tests，and missed three execution-blocking invariants。Replacement is therefore
serial and narrow：

1. **IR-A — P0 recover input/probes**：one helper runtime + its tests；
2. exact Codex/result review、merge/push of IR-A only；
3. **IR-B — controller incident recovery**：one controller runtime + its tests，based on merged IR-A；
4. exact Codex/result review、combined full-suite gate，then merge/push IR-B。

Neither partial merge is deployable to production。Only the combined exact IR-A+IR-B main tree may enter the
separately reviewed source-streamed unlock-to-deploy gate。

## 3. Package IR-A — helper and token-file boundary

### 3.1 Scope

Allowed：

- `scripts/production-mutation-lock.py`；
- `tests/test_production_mutation_lock.py`。

No controller、shell entrypoint、deploy、config、Coordinate or docs change。

### 3.2 Unit and process authority

Systemd must reject active/reloading/activating/deactivating exact families：

```text
p9-3c-fixture-e1-*.service
p9-3c-fixture-e2-*.service
```

Process classification must inspect exact argv components，not arbitrary command-line substrings。On the
Linux production host，enumerate PIDs with one direct bounded subprocess and inspect NUL-delimited
`/proc/<pid>/cmdline` for exact controller script basename or exact fixture agent-id argument。Exclude only
the current helper/probe authority by PID/argv identity；do not hide another real controller。Missing/incomplete
PID enumeration or unreadable candidate authority fails closed。Provide seams so macOS tests do not depend on
a local `/proc` filesystem。

Required negative proofs include recovery argv、token path、`ssh ... '...'`/`bash -c ...` parent command、probe
command、editor/grep text and unrelated process rows，all non-matching unless the NUL argv identifies the real
controller or fixture agent。Real E1/E2/controller matches block。

### 3.3 `recover --token-file`

Keep exactly-one `--token`/`--token-file` and direct-token compatibility。For `--token-file`：absolute path；
immediate parent root:root directory 0700 non-symlink；final `O_RDONLY|O_NOFOLLOW` regular root:root 0600
nlink 1；bounded exact size；one lowercase 64-hex token plus optional one newline；all decode/read/stat/open
errors become redacted structured `LockError` with zero recovery mutation。

Raw token bytes never enter argv/stdout/stderr/error/audit when `--token-file` is selected。Core recovery
ordering and audit durability remain unchanged。

### 3.4 IR-A gates

Tests cover every required probe and file authority case，including both/none parser flags、short read、invalid
UTF-8/shape/size、symlink/hardlink/mode/owner/parent failures、valid success、probe errors、audit failure and
existing direct-token behavior。Run helper focused suite、deploy contract regression if needed、full suite with
an adequate timeout，shell/diff checks。One exact implementation commit。

## 4. Package IR-B — controller incident recovery

### 4.1 Scope

Allowed：

- `scripts/p9_3c1_controller.py`；
- `tests/test_p9_3c1_production_controller.py`；
- `tests/test_deploy_contract.py` only for an exact installed/entrypoint invariant。

No helper、shell、config epoch/EP、Coordinate、deploy or docs change。Start from the reviewed merged IR-A main
SHA，not from the rejected candidate。

### 4.2 Exact catalog decision before mutation

Read a strict executor/capacity envelope。Require lists/row objects、at most one exact source、integer non-bool
versions、source path/hash consistency and exact row shapes for the relevant source。Bind source paths to sealed
config files and manifest file hashes；bind row catalog hashes to the source row。

Only two state classes are accepted：

1. executor absent/v1/v2/v3 with its exact version rows **and** capacity absent/v1 with its exact rows：run the
   existing v3 → capacity v2 → executor v4 monotonic cleanup；
2. executor exact empty v4 **and** capacity exact empty v2：skip all three lower catalog syncs。

Reject before mutation：v4/v2 with executable rows、higher/non-int/duplicate/malformed source、path/hash/row
drift、executor v4 without capacity v2、capacity v2 without executor v4 or any other partial combination。
Owned lock remains held。

### 4.3 Fixed incident receipt and authorization

Define fixed root-only authorities：

```text
control/p0-recovery-receipt.json
control/resume-cleanup-authorization.json
archive/recovered-production-lock.token
```

The P0 receipt is exact canonical JSON + newline with only `state="recovered"`、`phase="free"` and
`receipt_digest="sha256:<64hex>"`，root:root/0600/single-link。The auth field
`p0_recovery_receipt_digest` must equal that receipt value。The auth field `stale_lock_token_digest` also uses
`sha256:<64hex>`；all named `*_sha256` values remain bare lowercase 64 hex。Use separate validators and strict
types (`bool` never satisfies an integer field)。

Before any copy/acquire，prove exact current phase `agents-online`、exactly eight ledger records、valid full
hash chain、tail event `cleanup.initiated` and tail `record_sha256` equal auth；fixed live-authorization SHA；
manifest/deployed revisions/installed hashes；P0 receipt；expiry/verdict/nonce；and canonical auth bytes。

Copy auth once with `O_CREAT|O_EXCL|O_NOFOLLOW` semantics to fixed control path，fsync file+directory，then
revalidate exact bytes/owner/mode/nlink before every subsequent authority-changing boundary。Existing fixed
copy is replay and blocks。

### 4.4 Exact incident pre-acquire gate

Before acquiring the new token，prove again：global lock free；stale standard token authority/digest；fixed
archive target absent；E1/E2 units inactive or not-found with `MainPID=0`；no other controller/fixture process；
E1/E2 registry online on exact host with `current_load=0`；zero P9 jobs/leases/deliveries；zero executor
definitions/bindings and capacity policies；exact terminal v4/v2；workspace/profile still point to this run；
DB integrity `ok`、schema `13`、FK `0`；canonical projection/manifests/revisions/hashes unchanged。Any uncertainty
consumes the one-shot auth but performs no lock/catalog/DB/service mutation。

### 4.5 Separate global acquire and stale-token transaction

Factor ordinary acquire into：

1. acquire+verify one in-memory global P0 token without touching a state token path；
2. ordinary fresh-run persistence wrapper，unchanged externally。

Only `resume-cleanup` may call the first primitive while the reviewed stale standard file exists。After the
new global token is verified held：create/validate state-root `archive/` root:root/0700 non-symlink；create,
chown/chmod/fsync new temp in `control/`；rename stale to fixed archive；rename temp to standard；fsync both
directories；append digest/receipt ledger authority；then call the fixed cleanup suffix。

Explicit failure states：

- before stale rename：remove temp，release exact new token only after proving stale unchanged；
- after stale rename/before standard install：rename archive back，fsync，prove exact restoration，then release；
- rollback failure：preserve new global lock and all evidence；
- after standard install，including fsync/ledger/catalog/unit/DB/cleanup failure：never release or restore；keep
  new standard token and held global lock；
- success only：cleanup writes `cleanup.completed`/phase done，then existing `_release_lock` releases exact new
  token and removes standard token；archive remains forensic evidence。

No broad `finally`/catch release and no swallowed rollback failure。

### 4.6 IR-B gates

Tests start with contract/auth and failure-boundary tests before implementation。Inject acquire race、archive
preexistence/create failure、temp write/chown/fsync、stale rename、new install、both directory fsyncs、ledger,
rollback rename/fsync/release and cleanup failure。Assert exact global lock、standard token、archive、auth copy,
ledger and mutation-call state after every injection。

Also cover every live drift field、auth type/digest/canonical/replay/expiry failure、every catalog accepted/rejected
envelope、terminal skip success through agents offline/done/release and unchanged ordinary run/cleanup paths。
Run controller focused suite、deploy contract、combined full suite with adequate timeout、syntax/diff checks。
One exact implementation commit。

## 5. Review and worker policy

Each package requires its own detailed worker bootstrap and independent bootstrap review before delegation。
Worker and reviewer must be different agent sessions。KAT has already served as the first candidate and failed
the result gate；a smaller IR-A may use KAT again，while IR-B should use a fresh stronger available non-Codex
worker such as Claude-hosted Kimi in Sonnet mode。Codex remains architect/operator/result reviewer。

No package result is accepted from summaries alone：native JSONL model/provider、exact commit parent/subject/
allowlist、changed lines、focused/full tests and independent result verdict are all required。

## 6. Exit boundary

Only after IR-A and IR-B both receive `APPROVE` and the combined main full suite passes may Codex author the
separate unlock-to-deploy bootstrap。This replacement plan itself authorizes no production action。

P9_3C1_P3_RETRY_INCIDENT_IR_REPLACEMENT_PLAN_READY_FOR_INDEPENDENT_REVIEW_ALL_PRODUCTION_MUTATION_BLOCKED
