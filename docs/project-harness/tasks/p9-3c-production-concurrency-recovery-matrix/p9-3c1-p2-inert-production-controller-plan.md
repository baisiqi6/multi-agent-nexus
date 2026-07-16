# P9-3C1 P2 Inert Production Controller — Detailed Plan

状态：`DRAFT_FOR_INDEPENDENT_PLAN_REVIEW_NO_IMPLEMENTATION`

日期：2026-07-16 Asia/Shanghai

Measurement：`p9-3c1-p2-inert-production-controller-measurement.md`。

Parent：`p9-3c1-production-plan.md`。Parent Round 2 approval only authorizes P0/P1/P2 to proceed
package-by-package；it does not replace this P2 plan review and does not authorize P3 live activation。
This exact file must receive independent `APPROVE` before a worker bootstrap is generated。

## 1. Goal and non-goals

P2 delivers one inert-deployable MultiNexus package：

1. propagate Coordinate P1 claim `reap_mode=global|none` through agentd CLI/worker/client；
2. add immutable P9-3C1 executor/capacity/agent templates with isolated capability；
3. add a production-authorized unit path that reuses the P9-3C0 sandbox/cgroup implementation without
   weakening the P9-3C0 isolated path；
4. add a production-aware controller、sealed state/ledger and complete locally testable state machine；
5. inert-deploy exact assets，then run only `prepare/preflight/status` against production。

Non-goals for P2 execution：

- no P9-3C1 workspace/host/agent/catalog/job/lease/delivery row mutation；
- no transient fixture unit/process start、stop、crash or cgroup mutation；
- no production `claim/reap/report/deactivate` invocation；
- no service restart；
- no P3 authorization artifact and no production `run/cleanup`；
- no schema/migration/dependency/version change；
- no change to canonical `config/agent-registry.toml` or runtime `agents.toml`；
- no global reap as P9-3C1 evidence、no route-capability submission、no external bus、no provider；
- no whole-DB restore、direct production SQL write or deletion of terminal history。

The P2 code must contain the complete bounded `run/cleanup` machinery needed by P3；P2 validation uses
fake system/temp DB seams only。Production activation remains mechanically blocked by a separate P3
authorization manifest and procedurally blocked until fresh exact-revision review。

## 2. Exact base, branch and allowlist

- MultiNexus base：`7cd1c049d3157a778d79a0a69981032b2c9b2a02`。
- Coordinate deployed reference：`a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。
- Implementation must use a fresh isolated worktree/branch bound by the later bootstrap。
- Worker allowlist（may be narrowed，must not be widened without plan rereview）：

1. `multinexus/agentd/coordinate_client.py`
2. `multinexus/agentd/worker.py`
3. `multinexus/agentd/__main__.py`
4. `multinexus/fixture/bin/p9-3c0-unit.sh`
5. `scripts/p9-3c1-production-verify.sh`
6. `scripts/p9_3c1_controller.py`
7. `multinexus/fixture/config/p9-3c1/agents.production.toml`
8. `multinexus/fixture/config/p9-3c1/executor.v1-disabled.toml`
9. `multinexus/fixture/config/p9-3c1/executor.v2-enabled.toml`
10. `multinexus/fixture/config/p9-3c1/executor.v3-disabled.toml`
11. `multinexus/fixture/config/p9-3c1/executor.v4-empty.toml`
12. `multinexus/fixture/config/p9-3c1/capacity.v1.toml`
13. `multinexus/fixture/config/p9-3c1/capacity.v2-empty.toml`
14. `tests/test_agentd.py`
15. `tests/test_agentd_execution_lease.py`
16. `tests/test_p9_3c0_fixture_assets.py`
17. `tests/test_p9_3c0_package3_scripts.py`
18. `tests/test_p9_3c1_production_controller.py`
19. `tests/test_deploy_contract.py`
20. `multinexus/fixture/docs/runbook.md`

Do not modify P0 lock helper/deploy driver、P9-3C0 controller/cleanup、canonical config、packaging、
dependencies or unrelated tests。If implementation proves one of these files must change，stop and write an
exact deviation plan；do not silently widen scope。

The hyphenated executable `p9-3c1-production-verify.sh` and underscored importable Python module
`p9_3c1_controller.py` are intentional：shell entrypoints follow command naming，Python source follows
module identifier naming。Tests and installed-hash manifests bind both exact paths。

## 3. Shared validation and command rules

- All ids/modes/reasons/paths are runtime type-checked；bool is never accepted as string/int。
- Run id exact regex：`^p9-3c1-prod-[0-9]{8}t[0-9]{6}z-[a-f0-9]{8}$`，ASCII lower-case，
  maximum 42 bytes，no normalization。
- Other ids/actors/reasons use existing stricter contract where available；P9-3C1 claim reap reason
  maximum 512 Unicode code points and 2048 UTF-8 bytes，nonblank、
  `value == value.strip()`、no C0/DEL control。This byte limit is an intentional additional
  client/controller bound for the new claim-reap policy only；existing `normalize_recovery_reason()`
  remains unchanged for compatibility，and the two validators are not silently unified。
- Every filesystem path is absolute、canonicalized through existing ancestors、rejects symlink leaf and
  path escape；security decisions do not use string-prefix without separator-aware containment。
- Every external command is a Python `list[str]` with `shell=False`、fixed executable、bounded timeout、
  allowlisted environment、captured stdout/stderr and maximum output bytes。No `eval`、`bash -c`、
  interpolated SSH command or command string round-trip。
- Successful Coordinate CLI output must be exactly one bounded JSON object with the expected envelope；
  unknown/missing/extra authority fields fail closed before the next mutation。
- Controller never logs prompt、credential value、raw recovery/reap reason、lock token or full env。
  Reasons are stored as SHA-256 plus a fixed public reason id。
- All mutation commands require root and an exact held P0 lock token。Token is stored only in a
  root-owned mode `0600` file under the run control directory and is never passed in argv or unit env。
- Read-only DB access uses SQLite URI `mode=ro`、`PRAGMA query_only=ON` and an authorizer rejecting
  write/DDL/attach/detach；connection code must prove `in_transaction=False` after every evidence read。

## 4. Agentd claim reap-policy propagation

Add one shared validator in `coordinate_client.py`，suggested interface：

```python
normalize_claim_reap_policy(
    reap_mode: Any = "global",
    reap_reason: Any = None,
) -> tuple[str, str | None]
```

Contract：

- exact modes only `global|none`；
- `global` accepts only `None`，not empty string；
- `none` requires the bounded stripped-stable reason；
- validation happens before `_base_env()` or subprocess invocation；
- `CoordinateRuntimeClient.claim_job()` default `global/None` preserves current argv exactly and omits
  both flags；`none` appends exact `--reap-mode none --reap-reason <reason>`；
- `AgentdWorker.run()` validates once before `_running=True` and forwards the canonical pair on every
  normal/recovery poll；
- agentd CLI adds `--reap-mode {global,none}` and `--reap-reason`，validates before `load_config()`；
- `none` works with normal and recovery modes；recovery’s three evidence flags remain separately
  all-or-none；
- no change to automatic renewal、lease-loss cancellation、reporting or default nonfixture behavior。

Required tests：

1. default client command byte/order compatibility and no new flags；
2. explicit `none` exact argv；
3. all invalid combinations perform zero subprocess/config/adapter call；
4. worker forwards policy on repeated queue-empty polls without mutating it；
5. normal and recoverable paths both forward the sealed policy；
6. agentd CLI parser rejects partial policy before config load；
7. existing recovery tests remain exact green。

## 5. Immutable P9-3C1 config assets

All seven files are static reviewed TOML；the controller never rewrites source assets in place。

### Executor catalogs

- source id exact `p9-3c1-fixture-executors`；versions 1/2/3/4；
- one definition id `p9-3c1-local-fixture`，provider `local-fixture`，adapter `claude`；
- capability exact singleton `p9-3c1-fixture`；never `coding`、`review` or wildcard；
- v1/v3 include both fixed bindings disabled；v2 both enabled；v4 has no definition/binding；
- binding ids exact `p9-3c-fixture-e1/e2`，runner ids equal agent ids；
- display metadata may differ，but no real Discord user id. Use deterministic inert unique numeric
  placeholders that are never accepted into canonical workspace roster and are not delivery targets。

### Capacity catalogs

- source id exact `p9-3c1-fixture-capacity`；
- v1 has exactly E1/E2 each `max_concurrent_jobs=1`；
- v2 has no policies。

### Agent template

- exactly E1/E2，`agentd_mode=true`，adapter points to installed zero-provider fixture binary；
- exact production DB `/var/lib/coordinate/coord.sqlite3` and CLI `/usr/local/bin/coord-local`；
- distinct per-agent work/context placeholders under the sealed run root；
- every placeholder uses the dedicated `__P9C1_*__` prefix；no `__P9C0_*__` marker is accepted；
- no token、bus、destination、proxy、provider endpoint or real model；
- controller renders to a fresh file with exact-once placeholder replacement，then seals SHA/owner/mode；
- helper and controller independently parse assets and cross-check exact agent set against both
  `P9C0_AGENT_ALLOWLIST` declarations。Duplicate declaration、extra id、near match or parser ambiguity
  fails closed。

Tests load every catalog through the real MultiNexus authority parsers，verify v1→v4 monotonicity、
disjoint source ids from canonical/P9-3C0，exact capability and empty terminal versions。

## 6. Reviewed helper deviation: distinct production-authorized mode

Do not weaken or branch around current P9-3C0 `render/preflight/start` production refusal。Add separate
subcommands to the same helper：

```text
production-render
production-preflight
production-start
production-status
production-stop
production-cleanup
```

The production path must reuse/factor the existing internal implementations for unit naming、static
definition、systemd properties、post-start verification、ledger unit record、cgroup authority、exact
stop and cleanup。It must not duplicate those blocks in the Python controller or another shell file。

Exact public interfaces：

```text
production-render \
  --state-root <exact-root> --run-id <id> \
  --controller-manifest <path> --controller-manifest-sha256 <sha> \
  --lock-token-file <path>

production-preflight|production-status \
  --state-root <exact-root> --run-id <id> \
  --controller-manifest <path> --controller-manifest-sha256 <sha> \
  --agent-id <E1|E2>

production-start \
  --state-root <exact-root> --run-id <id> \
  --controller-manifest <path> --controller-manifest-sha256 <sha> \
  --lock-token-file <path> --agent-id <E1|E2> --mode <complete|hold> \
  [--recoverable --recovery-reason <reason> --prior-process-stopped]

production-stop|production-cleanup \
  --state-root <exact-root> --run-id <id> \
  --controller-manifest <path> --controller-manifest-sha256 <sha> \
  --lock-token-file <path> --agent-id <E1|E2>
```

`production-render` does **not** accept CLI overrides for wrapper、DB、fixture bin、Python、repo root、
work dir、user/group、template、reap policy or installed hashes；it reads them from the exact validated
controller manifest。Unknown or duplicate option fails before filesystem mutation。`production-render`
is invoked only inside P3 `run` after the global lock is held；P2 `prepare` never invokes it。

Production-specific authority：

- requires `--controller-manifest` and `--controller-manifest-sha256` under exact P9-3C1 run root；
- mutation subcommands additionally require `--lock-token-file` and validate installed P0 helper
  `status --expect-token` returns held owner/action for this run；
- manifest is root-owned、single-link、regular、non-symlink、mode `0600`，canonical JSON and SHA exact；
- manifest binds run id、state root、unit user/group uid/gid、installed repo/Coordinate revisions、all
  installed source hashes、production CLI/DB dev+inode+owner+mode identity、config hashes、helper
  allowlist、reap policy and P3 authorization digest；
- production paths are allowed only when they equal the manifest exact canonical values；any alternate
  production DB/wrapper is rejected；
- normal/recovery agentd argv always includes sealed `--reap-mode none --reap-reason <reason>`；
- recovery `production-start` requires the existing three recovery evidence flags and only `mode=hold`；
- normal start may use `complete|hold` according to the controller matrix；
- exact two-unit budget is across primary and recovery run suffixes，not merely per helper invocation；
- `production-status` is read-only；`production-stop/cleanup` require exact ledgered unit and lock；
- credential/network sandbox stays at least as strict as P9-3C0；no production convenience relaxation。

The P9-3C0 isolated `wrapper.manifest` and the P9-3C1 controller manifest are deliberately different
authorities。`wrapper.manifest` remains isolated-only and keeps its current dev/inode/size/nlink/owner/
group/mode/SHA schema。The production path does not forge or reinterpret that file；instead the P9-3C1
controller manifest contains a separately named `production_launcher_identity` object for
`/usr/local/bin/coord-local` and DB identity。Helper production subcommands parse that exact object and
must reject a P9-3C0 wrapper-manifest line as the controller manifest。

P9-3C0 regression tests must explicitly prove its old subcommands still reject production DB/wrapper，
do not accept production authority flags and keep current argv when used in isolated mode。

## 7. Controller filesystem and sealed evidence

Fixed root：`/var/tmp/multinexus-p9-3c1/<run-id>`。

Required layout：

```text
<run-id>/
  control/manifest.json
  control/manifest.sha256
  control/phase.json
  control/controller.lock
  control/live-authorization.json        # absent after P2 prepare
  control/production-lock.token          # exists only while held
  ledger/events.jsonl
  evidence/baseline.json
  evidence/preflight.json
  evidence/final.json
  backup/coord.sqlite3
  runtime/work/e1/
  runtime/work/e2/
  runtime/context/
  runtime/unit/
```

Ownership/modes：control/ledger/backup root:root `0700`，files `0600`；runtime root:coord `0750`，
per-agent work/context coord:coord `0700`。No world/group write。Every component rejects symlink、hard
link count other than one and unexpected entry。Backup is SQLite online backup from read-only source，
mode `0600`，hash + source data-version/time recorded；ordinary cleanup never restores it。

Ledger records canonical JSON lines with `seq`、UTC timestamp、phase、event、bounded evidence refs、
`prev_sha256` and `record_sha256`。Open with `O_APPEND|O_CLOEXEC|O_NOFOLLOW`，verify full chain before
each mutation，write one record，`fsync(fd)` and parent directory。Phase update uses same-directory
`O_EXCL` temporary file、file fsync、atomic replace、directory fsync。Phase and ledger tail must agree；
neither is repaired automatically from the other。

`prepare` creates a fresh root only。Any existing path—including an empty directory、terminal prior run
or symlink—fails；there is no reuse/force flag。On mid-prepare failure，leave a loud non-runnable forensic
directory with `prepare-failed` marker rather than guessing cleanup。

## 8. Controller CLI and live authorization fence

Thin entrypoint：

```text
sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh <subcommand> ...
```

It only validates EUID、fixed Python/controller path、run-id shape and `exec`s Python with original argv。
No sourceable mode、environment override of production paths or arbitrary Python path。

### `prepare`

```text
prepare --run-id <id> --unit-user coord --unit-group coord
```

- requires global lock currently free and performs a double-read revision/hash stability check；
- reads production DB only through the read-only evidence connection and online backup API；
- seals installed revisions/hashes、host/service/process identities、canonical projection、DB health、
  exact CLI help surface、config/helper allowlists and budgets；
- creates phase `sealed` and first ledger record；
- does not create workspace/agent/catalog/job/unit or live authorization。

### `preflight`

```text
preflight --run-id <id>
```

- truly read-only：no ledger append、phase rewrite、atime-dependent decision or DB write；
- validates manifest/ledger/phase、live installed hashes/revisions、lock free、DB health、canonical
  projection、fixture absence、service/process identity、backup freshness/mode and CLI features；
- emits one canonical JSON evidence object to stdout；
- any drift/nonzero probe fails without repairing state。

### `status`

```text
status --run-id <id>
```

Read-only summary of sealed/live revision match、phase/ledger tail、lock state、known unit status and
fixture DB counts。It does not claim success for unknown/unreadable evidence。

### `run`

```text
run --run-id <id> \
  --authorization-file <absolute-path> \
  --authorization-sha256 <sha256>
```

There is no authorization file after P2 inert prepare。P3 supplies a separately reviewed root-owned
mode `0600` canonical JSON artifact binding exact run id、manifest SHA、installed revisions/hashes、P3
bootstrap SHA、review artifact SHA、reviewer verdict `APPROVE`、five-job/two-unit budgets、UTC expiry
and one-time nonce。Controller copies it atomically into `control/live-authorization.json` only after
validating source identity/hash；an expired/mismatched/reused artifact fails before lock acquire or DB
mutation。

Then `run` acquires the P0 lock once、writes token file、reruns full preflight under held-lock semantics，
persists `preflight-ok` and executes the state machine。No skip cleanup/gate、dry-run-live、force、
allow-dirty or alternate DB/host flags。

### `cleanup`

```text
cleanup --run-id <id>
```

Allowed only when a valid ledger proves the run reached `workspace-ready` or later and is not `done`。
It acquires the P0 lock and resumes fixed cleanup from authoritative phase。A merely `sealed` P2 inert run
cannot use cleanup to mutate production。Terminal DB history and sealed evidence remain。

If a handled `run` failure occurs after lock acquisition but before the first production mutation
(`workspace-ready`)，the controller writes/fsyncs bounded `preactivation-failed` evidence，proves no
workspace/agent/catalog/job/unit mutation occurred，then releases its own exact token；`cleanup` is not
used。If the controller process crashes or token/evidence authority is uncertain in this window，the lock
remains held and only the reviewed P0 `recover` flow may release it after its unit/process probes and
operator reason。No age-based or automatic unlock。

## 9. Forward state machine and resume authority

Exact phases：

```text
sealed
-> preflight-ok
-> lock-held
-> baseline-captured
-> workspace-ready
-> agents-online
-> executor-v1-disabled
-> capacity-v1-active
-> executor-v2-enabled
-> matrix-running
-> matrix-verified
-> intake-frozen
-> units-quiescent
-> executor-v3-disabled
-> capacity-v2-empty
-> executor-v4-empty
-> agents-offline
-> canonical-compared
-> done
```

Each transition：verify current phase/ledger/authorization/lock token；execute at most one bounded
mutation command or one atomic evidence group；exact-read back；append ledger；advance phase。A command
success without readback is not a transition。A readback that already matches is accepted only when the
prior ledger record proves the exact command/idempotency key；directory or DB state alone cannot infer a
past success。

On any failure after `workspace-ready`，freeze intake and enter fixed cleanup。If authority/lock/canonical
projection is uncertain，stop exact known units and preserve evidence，but do not perform speculative DB
mutation or release a token that cannot be verified。Release lock only after `done` evidence fsync；a
release failure makes the run nonzero and leaves an incident marker。

## 10. Exact production mutation surface implemented for P3

Controller allowlists these Coordinate command families only：

- `workspace add p9-3c1-production ...` with empty default bus/destination；
- `workspace host-profile set p9-3c1-production --host-id VM-0-15-ubuntu ...`；
- `runtime agent register/heartbeat/deactivate` for exact E1/E2；
- `runtime executor sync --source <sealed v1..v4>`；
- `runtime capacity sync --source <sealed v1..v2>`；
- `runtime request submit p9-3c1-production --target-agent <E1|E2> --worktree-path ...` with
  namespaced idempotency and `reply-json` platform `stdout`；
- `runtime job claim` only for controller negative probes，always `--reap-mode none`；
- `runtime job progress/report/lease renew` only with exact ledgered job/attempt/lease authority；
- `runtime job lease reap --lease-id ... --job-id ...` only；never `--batch-size`；
- `delivery send <exact-id>` only for ledgered fixture response，then exact DB/stdout readback。

All other Coordinate commands are rejected by command-construction types，not string filtering。
Direct SQLite writes are forbidden。Read-only SQL is limited to named evidence queries over exact schema
13 columns and exact namespaced ids/source ids；`SELECT *` is not accepted as evidence serialization。

The five-job matrix implements the parent plan exactly：J1/J2 E1 sequential capacity proof；J3 E1/W1
hold；J4 E2/W2 overlap；J5 E2/W1 resource block then post-recovery success。Every managed job observes at
least two monotonic renewals where specified。J3 recovery unit is always `hold`、claims same job N+1 with
sealed `none` policy，then controller proves stale progress/report/renew rejection and performs current
N+1 empty-result terminal report。Only stdout deliveries are sent，by exact returned id。

Budgets are hard counters sealed in ledger before each submit/start：exactly five total requests，maximum
two simultaneously active units，zero provider/network/external delivery。Exceeding or losing counter
authority halts。

## 11. Preflight and final evidence gates

Preflight must prove all parent gates plus：

1. source/origin/deployed revision exact and no task-overlap dirty state；
2. installed controller、entrypoint、helper、fixture、agentd modules and seven configs exact hashes；
3. Coordinate P1 module hashes and CLI help include deactivate、exact reap、claim reap policy；
4. global lock free for standalone preflight，or exact own token for in-run preflight；
5. schema/integrity/FK `13/ok/0` and zero due active lease inventory at evidence time；
6. exact fixture absence for a fresh run and no matching process/unit/cgroup；
7. canonical projection exact sealed hash over explicit ordered columns from canonical executor source/
   definitions/bindings、capacity source/policies、workspace roster source/effective entries and the
   existing `discord-nexus` workspace/host projection；fixture sources and P9-3C1 workspace are separate
   evidence sets，never folded into the canonical hash；
8. helper/config agent-set equality、unique capability/source ids and terminal empty catalogs；
9. actual unit user/group ids and production CLI/DB/file identities exact；
10. service/process PID/argv identity captured without assuming a stale unit name；
11. backup regular/single-link/root-owned/mode `0600`、fresh and hash-valid；
12. P3 authorization exact and unexpired for `run` only。

Final acceptance additionally proves zero fixture executable state，agents offline，only v4/v2 empty
source metadata，terminal namespaced audit residue，canonical projection exact，DB healthy，service PIDs/
restart counts unchanged，external messages/provider/network zero and ledger/phase `done` consistent。

## 12. Required dynamic tests

Use dependency-injected filesystem/clock/subprocess/lock/system/DB seams，but exercise real temp files、
real SQLite schema and real authority parsers where the invariant concerns bytes or rows。

At minimum：

1. prepare permissions、fresh-only behavior、symlink/hardlink/path traversal rejection and mid-failure
   forensic state；
2. read-only preflight/status produce byte-identical state tree before/after；
3. manifest/phase/ledger canonical serialization、hash-chain corruption、sequence gap、tail mismatch、
   short write/fsync/rename failure；
4. P3 authorization absent/mode/owner/hash/run/revision/reviewer/expiry/nonce failures before mutation；
5. global lock contention/token mismatch/release failure and no command beyond the failed gate；
6. every forward phase success/readback/resume plus crash between command、ledger and phase writes；
7. failure from every mutable phase enters only the valid cleanup suffix；
8. command-array exactness、timeout/output bounds、environment whitelist and `shell=False`；
9. DB read-only authorizer rejects INSERT/UPDATE/DELETE/DDL/ATTACH/PRAGMA mutation；
10. exact canonical projection drift and fixture/canonical overlap halt；
11. job/unit budgets and forbidden route/global-reap/external delivery are unconstructable；
12. five-job fake-system trace exact ordering、renewal counts、resource blocker、exact reap、N+1 recovery、
    three stale mutations、stdout delivery and cleanup；
13. unrelated due sentinel evidence remains byte/row exact across every P9-3C1 claim/reap fake trace；
14. production helper subcommands validate manifest/lock/policy and reuse exact stop/cgroup internals；
15. old P9-3C0 paths still reject production and all existing fixture/package3 tests pass；
16. deploy archive/sync includes every exact new script/config path and deploy script never invokes
    controller；`test_deploy_contract.py` must inspect the staged/installed fake tree，not only grep
    excludes or assume tar includes the files；
17. config parser/cross-set tests reject duplicate/extra/near-match agents、wrong source/version/capability；
18. agentd propagation tests from section 4。

No test may assert only source text where a dynamic state/argv/filesystem/DB proof is practical。

## 13. Verification gates and baselines

Worker must run targeted tests during implementation。Final candidate gates：

```bash
.venv/bin/python -m pytest -q \
  tests/test_agentd.py \
  tests/test_agentd_execution_lease.py \
  tests/test_p9_3c0_fixture_assets.py \
  tests/test_p9_3c0_package3_scripts.py \
  tests/test_p9_3c1_production_controller.py \
  tests/test_deploy_contract.py \
  tests/test_production_mutation_lock.py

.venv/bin/python -m pytest -q
```

Base focused：`379 passed, 45 subtests passed`。Base full：
`953 passed, 2 skipped, 81 subtests passed`。Candidate must have no new failure/skip；all P2 tests pass。

Also run：

```bash
bash -n scripts/p9-3c1-production-verify.sh
bash -n multinexus/fixture/bin/p9-3c0-unit.sh
.venv/bin/python -m py_compile scripts/p9_3c1_controller.py
```

The worker must not run production/SSH/deploy commands。

## 14. Review, worker and model policy

- Codex remains architect/operator/final reviewer and does not write the main P2 implementation unless
  correcting reviewed residual defects after worker output；
- independent plan reviewer is separate from plan author；
- implementation worker priority：Claude Code `--model sonnet` using actual native
  `kimi-for-coding`，never Opus；
- every session must preserve provider-native JSONL and prove actual provider/model from assistant
  events，not label/CLI argument；
- if Claude/Kimi unavailable，fallback order is DeepSeek V4 Pro then MiniMax M3；no silent switch；
- independent result reviewer is separate from implementation worker and reviews exact candidate SHA；
- plan approval -> reviewed bootstrap -> worker -> Codex review/corrections -> fresh independent result
  review -> ff merge/push -> inert deploy/dogfood。

## 15. P2 production deployment and dogfood gate

After exact-revision result approval：

1. ff merge/push MultiNexus；
2. capture lock、DB、canonical projection、PIDs/restarts and residue pre-state；
3. deploy with `scripts/deploy-server.sh multinexus --host kook-hermes-admin --no-restart` from a
   clean exact-revision worktree；
4. verify deployed VERSION/hashes and P0 lock free；
5. create one fresh inert P2 run id with `prepare --unit-user coord --unit-group coord`；
6. execute read-only `preflight` and `status`，capture exact stdout/hashes；
7. repeat preflight/status and prove state tree hash unchanged；
8. verify zero P9-3C1 DB row/unit/process/catalog mutation，canonical projection exact，services/PIDs/
   restarts unchanged，DB `ok/13/0`，lock free；
9. do not call `run` or `cleanup` and confirm live authorization absent；
10. independent reviewer approves deployed inert evidence before P3 bootstrap creation。

Inert run state remains as sealed audit evidence；P3 uses a new fresh run id and fresh prepare after its
own exact-revision approval。

## 16. Acceptance and authorization boundary

P2 is complete only when：

- all implementation/test/config/helper/controller requirements above exist on one reviewed SHA；
- Codex and fresh independent result reviewer both approve；
- source/origin/deployed SHA and installed hashes exact；
- inert prepare/preflight/status dogfood passes twice with state-byte stability；
- production executable state and canonical projection remain unchanged；
- result review、deployment dogfood、progress、dogfood-feedback and roadmap/Phase 9 docs are synced。

Approval of this plan authorizes only generation of the P2 worker bootstrap after independent plan
review。Approval and completion of P2 do not authorize P3 live activation。P3 still requires a fresh
operator bootstrap and independent exact live-preflight review。

P9_3C1_P2_DETAILED_PLAN_READY_FOR_INDEPENDENT_REVIEW_IMPLEMENTATION_BLOCKED
