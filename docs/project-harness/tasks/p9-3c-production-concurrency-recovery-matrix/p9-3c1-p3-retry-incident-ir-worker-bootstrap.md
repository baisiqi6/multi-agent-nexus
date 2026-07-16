# P9-3C1 P3 Retry Incident — Package IR Worker Bootstrap

状态：`DRAFT_FOR_INDEPENDENT_REVIEW_IMPLEMENTATION_AND_PRODUCTION_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Role and authority

Worker role：non-Codex Coding worker。Codex remains architect/operator/result reviewer。

This bootstrap authorizes only local implementation/tests/one commit in an isolated worktree **after** a
fresh independent bootstrap review returns `APPROVE`。It never authorizes reading user `sessions/`、SSH、
deploy、source-streamed recover、token access、DB/service mutation、controller cleanup/run or P0 recover。

Required authorities：

- plan base：`87d54c97053b06fa63677b5db42ef1a8c3d49d15`；
- measurement SHA：`b6f05c8b3d9756871d0e18ae56e3f2449e10b968ede11ed32dd844582d933724`；
- detailed plan SHA：`c4fdac88ed16a65f1c4a11f2d7e1d84d65443f71e82f1312aaae2c10a4bcc66a`；
- plan-review SHA：`10146047b3bcc7a27a4d37d4e40e42488a922c1d2adcd9f6031a7584e85b0637`；
- incident controller SHA：`31ca28804c2a5d9252002124c324acb7353a2431af6da82e37e3b9c3ffcecf82`；
- incident reviewer JSONL SHA：`6c2564c6e1fc279570161b94327b683473bdac1a2d405aef08d755d1e1e94fb6`。

After this bootstrap and its review are merged，operator sets `WORKER_BASE` to exact
`main == origin/main`。Require：

```bash
git diff --quiet 87d54c97053b06fa63677b5db42ef1a8c3d49d15..$WORKER_BASE -- \
  multinexus scripts tests config agents.toml
```

Only reviewed docs may differ。Worker must branch from exact `WORKER_BASE`。

## 2. Exact allowed files

Runtime：

- `scripts/production-mutation-lock.py`；
- `scripts/p9_3c1_controller.py`；
- `scripts/p9-3c1-production-verify.sh` only for the exact usage/subcommand surface。

Tests：

- `tests/test_production_mutation_lock.py`；
- `tests/test_p9_3c1_production_controller.py`；
- `tests/test_deploy_contract.py` only if an installed-source/entrypoint invariant genuinely requires it。

No other runtime/config/test/docs file may change。No Coordinate repository、schema、migration、catalog CLI
semantics、deploy script、fixture epoch asset or EP work belongs here。

## 3. P0 recover probe and token-file contract

### 3.1 Systemd probe

The default recover probe must reject any active/reloading/activating/deactivating service matching exact
real families：

```text
p9-3c-fixture-e1-*.service
p9-3c-fixture-e2-*.service
```

It must not rely on the wrong `p9-3c1-` prefix。Unrelated services remain allowed。Missing/systemctl error
remains fail closed。

### 3.2 Process probe

Replace `pgrep -f p9-3c1` with a direct-subprocess exact expression covering real controller/fixture
processes，for example the semantic equivalents of：

```text
p9_3c1_controller.py
p9-3c-fixture-e1
p9-3c-fixture-e2
```

The recovery invocation、token-file path、SSH shell and probe itself must not self-match。Any matched real
PID or probe error blocks recover。

### 3.3 Recover-only token file

The `recover` parser requires exactly one of `--token` or `--token-file`。Existing direct `--token` callers
remain compatible。`--token-file` must：

- accept only an absolute path；
- open final component `O_RDONLY|O_NOFOLLOW`；
- require regular、root:root、0600、nlink 1；
- require its immediate parent root:root directory、mode 0700 and non-symlink；
- read exactly one 64-lowercase-hex token plus optional single newline，reject other bytes/size；
- never echo/store raw bytes in argv、stdout/stderr/error detail/audit。

The core `recover(token=...)` ordering remains：authority/token compare → corrected probes → durable audit →
release。No `allow_already_free` or weakened audit behavior。

Required tests：real unit/process block；self invocation and unrelated rows do not；probe errors fail closed；
both token flags/none rejected；symlink/hardlink/mode/owner/parent/shape failures zero mutation；valid
token-file success；existing direct-token tests unchanged；audit/release fsync gates unchanged。

## 4. Exact legacy cleanup behavior

Do not change ordinary `cmd_cleanup` authorization boundary。Factor a bounded catalog-state reader and make
the cleanup suffix handle these cases：

- executor exact v4 + zero definitions/bindings and capacity exact v2 + zero policies：already terminal，
  skip all lower catalog syncs；
- source absent or executor versions 1/2/3 and capacity absent/1：retain the existing monotonic cleanup
  progression to exact empty v4/v2；
- executor/capacity higher than 4/2、same terminal version with executable rows、unexpected source/hash/
  envelope or partial incompatible combination：fail closed and keep the owned lock。

The current incident must then deactivate both agents、verify canonical projection/DB、write cleanup evidence、
append `cleanup.completed`、phase done and release the **new** owned token。No Coordinate downgrade acceptance、
delete/reset source or arbitrary version no-op。

Tests must reproduce retained empty v4/v2 at phase `agents-online`，prove no v3/v2/v4 sync command occurs，
then prove agents offline、done and release。Also test every rejected state and unchanged first-run cleanup paths。

## 5. Incident authorization contract

Add a separate canonical resume-cleanup authorization，not the P3 live authorization。Use an exact key set
and strict types：

```text
contract_version = 1
action = "p9-3c1-resume-cleanup"
run_id
incident_phase = "agents-online"
incident_ledger_records = 8
incident_tail_event = "cleanup.initiated"
incident_tail_sha256
stale_lock_token_digest
p0_recovery_receipt_digest
live_authorization_sha256
manifest_sha256
installed_revisions
installed_hashes
incident_bootstrap_sha256
review_artifact_sha256
reviewer_verdict = "APPROVE"
expiry_utc
nonce
```

`stale_lock_token_digest` and `p0_recovery_receipt_digest` must use the helper's existing exact
`sha256:<64hex>` form。All fields named `*_sha256` use bare 64 lowercase hex。The future bootstrap/reviewer
SHA is not self-referential：`review_artifact_sha256` is the completed basis reviewer JSONL，while the final
auth review JSONL SHA is closeout evidence only。

Add `resume-cleanup --run-id --authorization-file --authorization-sha256` to Python parser/entrypoint usage。
Validate canonical JSON + newline、root/single-link/mode、exact key set/value types、expiry、fresh nonce、
manifest/live-auth/deployed hashes and current exact phase/ledger/tail before copying once to fixed
`control/resume-cleanup-authorization.json` as root:root/0600/single-link。No overwrite/reuse。

## 6. New-lock acquisition and stale-token transaction

`resume-cleanup` is the only path allowed to expect the stale standard token file after the separately
reviewed P0 sidecar has made the global lock free。

Before acquire require：global lock free；stale token file root:root/0600/nlink 1 and digest exact auth；
archive target absent；P0 receipt、live auth、manifest、runtime/DB/unit/process authority exact。

Then：

1. acquire a new P0 global token without first rejecting the expected stale state token；
2. create/validate a root:root/0700 state-root `archive/` directory and absent fixed archive target
   `archive/recovered-production-lock.token`；
3. create and fsync a new-token temporary file under `control/`；
4. rename the stale standard token to the archive target；
5. rename the new-token temporary file to the standard token path；
6. fsync both directories，append only digest/receipt authority to ledger，then run cleanup。

If any failure occurs before cleanup mutation：

- before stale rename，release the new in-memory token and leave stale authority unchanged；
- after stale rename but before new install，rename archive back first，fsync，then release new token；
- after new token becomes standard，do not release on uncertain state；preserve the new held lock/token and
  incident evidence unless the code can prove zero cleanup mutation and fully restore the old transaction。

Archive remains root-only forensic evidence。Raw tokens never enter ledger/result/error。There is no blanket
`finally` release。

Required tests inject every boundary failure，including acquire race、archive preexistence、rename/fsync/
ledger failure、rollback failure、receipt/digest/auth drift and cleanup failure。Assert exact lock/token/archive
state for each case。

## 7. Entry point and receipt scope

If edited，the shell entrypoint changes only its usage string to name `resume-cleanup`；it remains a thin fixed
EUID/path/run-id `exec` wrapper。Bash pipeline/SSH status capture belongs to the later operator bootstrap，not
this runtime entrypoint。

## 8. Worker execution and acceptance

Preferred worker：OMP `kat-coder/kat-coder-pro-v2.5`。Create an isolated worktree/branch named for Package IR。
No SSH/network/production/session access。Read only repo authorities。

Required gates from the canonical repository venv：

```bash
bash -n scripts/p9-3c1-production-verify.sh
python -m pytest -q tests/test_production_mutation_lock.py
python -m pytest -q tests/test_p9_3c1_production_controller.py
python -m pytest -q tests/test_deploy_contract.py
python -m pytest -q
git diff --check
```

Worker must create exactly one implementation commit，report parent/commit/subject/diffstat/tests and stop。
No amend after review。Native JSONL must prove exact provider/model。

Codex independently reviews every line and reruns proportional/full gates。Then a fresh non-Codex result
reviewer must return strict `APPROVE` with no P0/P1/P2 before merge。Implementation approval still does not
authorize source-streamed recover or deploy；those require a separate exact incident operator bootstrap and
fresh review。

## 9. Forbidden shortcuts

- no manual lock/token deletion or direct installed-helper replacement；
- no current-run ordinary cleanup、second run or P0 recover by the worker；
- no raw token fixture copied from production；tests generate isolated tokens；
- no Coordinate downgrade/no-op/delete/reset change；
- no EP dynamic version/rendered config work；
- no broad refactor、schema/DB/service/deploy change；
- no weakened owner/mode/nlink/fsync/audit/lock checks。

P9_3C1_P3_RETRY_INCIDENT_IR_WORKER_BOOTSTRAP_DRAFT_FOR_INDEPENDENT_REVIEW_IMPLEMENTATION_AND_PRODUCTION_MUTATION_BLOCKED
