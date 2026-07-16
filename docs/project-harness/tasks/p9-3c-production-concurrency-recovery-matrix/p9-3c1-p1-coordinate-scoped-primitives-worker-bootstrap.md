# P9-3C1 P1 Coordinate Scoped Primitives — Worker Bootstrap

> **状态：draft；只授权 independent exact-SHA bootstrap review。** 在 reviewer 对本文件 exact
> SHA-256 返回 `APPROVE` 前，不授权 worktree、coding worker、repo write、commit、push、merge、
> deploy、SSH、production DB mutation、lease reap、agent deactivate、service restart、fixture/
> controller/P2/P3/live matrix。本文件不得自我授权。

日期：2026-07-16 Asia/Shanghai

## 1. Authorization chain

- Fresh measurement SHA-256：
  `4b7e59ce4b249c65059f08ec43ef1577b028876d1ab3e2fd4c22740c2da397b7`。
- Approved detailed plan SHA-256：
  `30a9764fe15391c47320d7c1636cebcee695665bfca8ac6876f03eb64d188a9c`。
- Independent plan review：
  `p9-3c1-p1-coordinate-scoped-primitives-plan-review-round1.md`。
- Plan verdict：`APPROVE`，P0/P1 findings none；authorization is bootstrap draft only。
- Coordinate implementation base：
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- MultiNexus/P0 read-only reference：
  `1b1d1fd1c5c160e3ede16ee2f07fb2989990e3c2`。

Any bootstrap edit changes SHA and invalidates a prior review。Approval of this bootstrap will authorize
only the local implementation/test/one-commit handoff below；push/merge/deploy/production operations
remain separate result gates。

## 2. Worker route and evidence

Primary route：

- outer worker：Claude Code，fixed `--model sonnet`；never Opus；
- intended provider-native model：`kimi-for-coding`；
- native stream assistant event must prove actual model；outer selector/UI label is not proof。

Quota-only fallback：if primary returns explicit quota/auth failure before any repo write，preserve full
JSONL/session and launch a fresh session，never silent-switch：

1. OMP `deepseek/deepseek-v4-pro`，native stream must prove
   `provider=deepseek`、`model=deepseek-v4-pro`；
2. OMP `minimax-code-cn/MiniMax-M3` only if DeepSeek is unavailable/limited，native stream must prove
   both provider/model。

Kimi has recently returned billing-cycle `403`，but primary must still be tried once because quota may
refresh。GLM is not the default fallback for this package due current latency。Fallback changes only
the worker route，not scope/tests/review bar。If a route changes after any repo write，stop；Codex audits
dirty state before deciding whether any bytes are retained。

Save every attempt's full JSONL、session id、outer route、actual native provider/model、completion
receipt。JSONL proves activity/route；diff/tests/review decide acceptance。Worker does not approve its
own result or use subagents/agent teams/workflows。

## 3. Exact repo, branch and worktree

- Repository：`/Users/yinxin/projects/coordinate`。
- Base branch：`main`。
- Exact base：`9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- Required branch：`agents/fallback/p9-3c1-p1-coordinate-scoped-primitives`。
- Required isolated worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3c1-p1-scoped-primitives`。

Operator creates worktree/branch only after bootstrap approval。Worker begins by verifying exact path、
branch、HEAD、clean status。Any mismatch stops。Never implement in main checkout；never read or modify
the user-owned untracked `/Users/yinxin/projects/coordinate/.qoder/`、credentials、production DB、
runtime secrets or unrelated untracked files。

## 4. Exact changed-file allowlist

Worker may change exactly these paths and no others：

1. `src/coordinate/runtime_lease.py`
2. `src/coordinate/runtime.py`
3. `src/coordinate/execution_cli.py`
4. `tests/test_runtime_lease.py`
5. `tests/test_runtime.py`
6. `tests/test_execution_cli.py`
7. `tests/test_cli_contract.py`
8. `tests/fixtures/cli_contract.json`

No schema/migration/version/dependency/docs/MultiNexus change。Do not run formatting over unrelated
regions。If a ninth file appears necessary，stop with a plan deviation；do not widen silently。

Produce exactly one local commit on the required branch，message：

```text
feat(p9-3c1): add scoped production primitives
```

No push/merge/deploy/SSH。Do not amend Coordinate history outside this one candidate commit。

## 5. Shared validation rules

Add focused validators close to their owning module；do not create a generic validation framework。

- Reject non-string ids/reasons/actors；bool is not a string substitute。
- `lease_id/job_id/agent_id/host_id/actor`：nonblank、exact stripped-stable、max 128、no C0/DEL
  control chars。
- reap/deactivate reasons：nonblank、exact stripped-stable、max 512、no control chars。
- Validate public API inputs before `BEGIN IMMEDIATE`/durable write。Core functions repeat authority
  validation so CLI is not a security boundary。
- Test invalid values with snapshots of relevant rows/events and `conn.in_transaction`；error-text-only
  assertions are insufficient。
- Preserve current exception families (`RuntimeLeaseError` / runtime `RuntimeError`, both ValueError
  compatible) so top-level CLI keeps bounded nonzero stderr behavior。

Do not add env/CLI bypass、force、allow-stale、age-based recovery or global fallback。

## 6. Exact lease reap core

Add public：

```python
reap_exact_lease(
    conn,
    *,
    lease_id: str,
    job_id: str,
    actor: str = "runtime",
    now: str | None = None,
) -> dict[str, Any]
```

### 6.1 Transaction and selection

1. Validate ids/actor before transaction。
2. Sample/validate `now` using existing canonical UTC conventions；tests may inject only through the
   Python API，not CLI。
3. `BEGIN IMMEDIATE` exactly once。
4. `SELECT * FROM execution_attempt_leases WHERE lease_id = ?` only。
5. Missing row -> `RuntimeLeaseError`；no global search。
6. Require stored row `job_id == requested job_id` before any mutation。
7. Revalidate stored resource snapshot、active status、due time、attempt/agent tuple and matching
   running job inside the transaction。
8. Expire exact lease、CAS exact job timed_out/recoverable、append the existing exact idempotent
   `execution_lease.expired` and `job.timed_out` events。
9. Commit on success；rollback on every failure，including event/CAS failure。

Never call `_find_due_active_leases()`。Do not implement “global scan then filter”。Do not mutate an
unrelated due row。

### 6.2 Preserve global behavior by a narrow refactor

Extract only the post-revalidation mutation/CAS/event portion from `_reap_one_lease()` into one private
helper，suggested shape `_expire_revalidated_lease(conn, current, actor, now)`。Then：

- existing `_reap_one_lease()` keeps its current revalidation and converts benign released/renewed races
  to `{"skipped": true}` for global reap exactly as before；
- exact path converts not-active/not-due into loud `RuntimeLeaseError`，then calls the shared post-
  revalidation helper；
- do not change `_find_due_active_leases()`、global ordering/batch/error summary or transaction-per-row
  contract。

Success result exact keys：

```text
mode = "exact"
reaped_count = 1
lease_id
job_id
attempt_token
agent_id
```

Not-found、job mismatch、not-active、not-due、snapshot corruption、job missing/state/attempt/agent
mismatch、CAS/event failure and retry-after-success are nonzero and zero durable mutation。

### 6.3 Race evidence

Use real file-backed SQLite connections：

- renew commits first -> exact reap recheck says not due，zero mutation；
- exact reap commits first -> renew fails stale/expired；
- terminal report commits first -> exact reap sees non-active，no duplicate terminal event；
- exact reap commits first -> stale terminal report fails，one timeout terminal event only；
- second unrelated due sentinel job/lease/events remain exact unchanged in every exact path。

## 7. Reap CLI dispatch

In `register_runtime_commands()`：

- change `--batch-size` default from `100` to `None`；preserve `type=int`；
- add `--lease-id` and `--job-id`；
- parser may use a mutual-exclusion group for `--batch-size` vs `--lease-id`，but handler/core still
  validate the complete pair and all mixed states。

In `handle_runtime_job_lease_reap()`，before opening `_conn(args)`：

| Inputs | Dispatch |
| --- | --- |
| no ids，`batch_size is None` | global `reap_due_leases(..., batch_size=100)` |
| no ids，explicit batch | global with exact batch |
| both exact ids，`batch_size is None` | `reap_exact_lease(...)` |
| only one id | nonzero before `_conn`/core |
| both ids + explicit batch | nonzero before `_conn`/core |

Success stays one `{"result": ...}` JSON object。Do not return global success for a partial exact
request。Add parser and handler tests proving invalid combinations do not call `_conn`、global or exact
core。

## 8. Typed claim reap policy

Extend both public layers：

```python
runtime.claim_job(..., reap_mode: str = "global", reap_reason: str | None = None)
runtime_lease.claim_leased_job(..., reap_mode: str = "global", reap_reason: str | None = None)
```

Add one focused `_validate_claim_reap_policy()` in `runtime_lease.py` returning canonical
`(mode, reason)`：

- exact string `global|none` only；
- global requires `reason is None`；empty string is still invalid because it was supplied；
- none requires exact bounded reason；
- invalid values fail before transaction/reap/select/mutation。

### 8.1 `runtime.claim_job()`

- Validate policy before `_require_online_agent()` and before `BEGIN IMMEDIATE`。
- Resolve typed binding as today。
- `none` on untyped/no exact binding fails before job/event mutation；legacy untyped default/global path
  remains byte-for-byte behaviorally unchanged and gains no implicit global reaper。
- Pass canonical policy only to typed `claim_leased_job()`。

### 8.2 Transaction-internal authority in `claim_leased_job()`

At function entry，before recovery evidence、global reap or candidate selection：

1. validate policy again；
2. re-read `agents` row inside caller-owned `BEGIN IMMEDIATE`；
3. require row exists、`online_state == "online"`、stored `host_id == requested host_id`；
4. for `none`，resolve/require exact executor binding inside the transaction before skipping global reap。

This is the deactivate fence，not an optional defense-in-depth check。Do not rely only on the existing
pretransaction `_require_online_agent()`。

### 8.3 Reap and event behavior

- global executes existing `_reap_due_leases_in_transaction()` and preserves current error behavior；
- none never calls global selector/reaper；
- successful typed `job.claimed` event payload always contains exact keys：
  `reap_mode` and `reap_reason`（JSON null for global，canonical string for none）；
- no-claim queue/capacity/resource result creates no claim event；P2 controller ledger will record CLI
  argv/result later。

CLI claim adds：

```text
--reap-mode {global,none}    default global
--reap-reason TEXT
```

Handler passes both exact values。Recovery evidence requirements remain independent；none normal and
recoverable tests each preserve a real unrelated due sentinel lease/job/events。

## 9. Runtime agent deactivate

Add runtime result type and API，suggested：

```python
deactivate_agent(
    conn,
    *,
    agent_id: str,
    host_id: str,
    reason: str,
    actor: str = "runtime",
    dry_run: bool = False,
) -> RuntimeAgentDeactivateResult
```

Result `to_dict()` is bounded and deterministic。It includes：

```text
agent
changed
deactivated
dry_run
blocked
reason
blockers
event
event_created
```

`blockers` uses counts plus at most one deterministic first id per category，never an unbounded list：

```text
active_leases: {count, first_lease_id}
pending_jobs: {count, first_job_id}
running_jobs: {count, first_job_id}
recoverable_timed_out_jobs: {count, first_job_id}
```

### 9.1 One transaction

After public input validation：

1. `BEGIN IMMEDIATE`；
2. read exact agent；require agent exists、exact host、`client_type=agentd`、known online/offline state；
3. query exact active leases and all three blocking job categories in the same transaction；
4. any blocker -> no update/event，finish transaction，return `blocked=true`；CLI prints JSON and returns
   nonzero；
5. dry-run with no blocker -> no update/event，return projected `deactivated=false, blocked=false`；
6. online success -> CAS exact row to offline，append exact audit event with `commit=False`，then commit；
7. exception/CAS/event failure -> rollback and re-raise；top-level API leaves no open transaction。

Blocker checks happen before offline-retry acceptance too；an offline agent with executable state is not
reported clean。

### 9.2 Collision-free deactivation generation

Do not use only second-resolution `last_seen_at`/`updated_at` in the idempotency key。Inside the write
transaction：

- count/query prior `agent.deactivated` events for exact target in deterministic order；
- derive `generation = prior_count + 1` and bind it to the immediately previous deactivation event id
  (or null for first)；
- first online deactivation key suggested：
  `runtime:agent:<agent_id>:deactivated:<generation>`；
- event payload exact keys include agent_id、host_id、actor、reason、previous_online_state、
  deactivated_at、generation、previous_deactivation_event_id；
- `append_event(..., commit=False)` must return `created=True` for an online transition；an unexpected
  existing generation is invalid and rolls back。

Because `BEGIN IMMEDIATE` serializes writers，rollback/retry sees the same prior_count；a committed
deactivation increments it。Same-second heartbeat/deactivate cycles therefore cannot collide。

### 9.3 Offline retry and reactivation

- If agent is already offline and no blockers，query latest exact `agent.deactivated` event for the
  target；parse payload and require exact agent_id/host_id/generation chain；return the stored event with
  `changed=false, deactivated=true, event_created=false`；do not append/update。
- Offline without a valid matching audit event ->
  `offline_without_deactivation_audit` nonzero、zero mutation；never fabricate history。
- Existing same-host `heartbeat_agent()` remains unchanged and may reactivate；different host remains
  blocked。
- After heartbeat，a new deactivation uses next generation/new event。Tests force two cycles within one
  frozen UTC second to prove no key collision。

### 9.4 CLI

Add：

```text
coordinate runtime agent deactivate \
  --agent-id ID --host-id HOST --reason TEXT \
  [--actor ACTOR] [--dry-run]
```

All identity/reason args required as specified；actor default `runtime`。Handler opens DB only after
argument-shape validation，prints one `{"result": ...}` object，and returns `1` for blocker result、`0`
for dry-run/success/idempotent retry。Identity/audit errors use existing bounded nonzero stderr path。

## 10. Deterministic claim/deactivate concurrency tests

Use a file-backed DB、two independent connections and threading events/barriers。Do not add production
sleep/hooks or depend on timing luck。

### Claim wins

- typed claim begins `BEGIN IMMEDIATE` and is paused through a test monkeypatch at a known internal seam
  after transaction acquisition but before commit；
- deactivate starts on second connection and must wait；
- release claim；it commits running job + active lease；
- deactivate then acquires lock，returns blocker nonzero，agent remains online，claim authority remains
  exact。

### Deactivate wins after claim's stale precheck

- claim performs existing pretransaction online read and is paused before `BEGIN IMMEDIATE` using a
  test-only monkeypatch/barrier；
- deactivate on second connection commits offline + audit event；
- release claim；inside its transaction it re-reads offline and fails before global reap/select/CAS；
- pending target job、unrelated due sentinel job/lease/events and all lease counts remain unchanged。

Also sequentially prove offline typed claim with pending job cannot execute。Thread tests must use
bounded joins/timeouts and surface worker exceptions；no daemon thread leak。

## 11. CLI golden contract

Update `tests/fixtures/cli_contract.json` through existing deterministic generation logic only for：

- `runtime agent deactivate` path/handler/help；
- claim `--reap-mode/--reap-reason`；
- reap exact selector/batch help。

Base fixture SHA-256：
`13cb4f3b748fdf7dc1d91dfbb27d9a214d23dfff1112d253d0e01aa0c701ad3d`。

Add one P1 delta proof that takes the **candidate generated contract**，removes only P1 additions，and
exactly equals base fixture bytes/hash。Preserve all historical expected SHA constants。Do not update old
baseline hashes to make failures green。Argparse unrelated help reflow must cause the P1 delta proof to
fail rather than be masked。

Base known focused failures（all in `tests/test_cli_contract.py`）：

1. `test_contract_cumulative_rewind_matches_p9_0a1_baseline`
2. `test_contract_cumulative_rewind_matches_p9_0a2a_baseline`
3. `test_contract_cumulative_rewind_matches_p9_0a2b_baseline`
4. `test_contract_cumulative_rewind_matches_p9_0a2c_baseline`
5. `test_contract_cumulative_rewind_matches_p9_0a3a_baseline`
6. `test_contract_differs_from_p9_0a4a_baseline_only_at_12_handlers`
7. `test_contract_s4b1_rewind_matches_baseline`
8. `test_contract_s4c1_rewind_matches_baseline`

Full ninth known failure：

9. `tests/test_issue_cli.py::IssueCLIOwnershipTests::test_all_five_handler_ast_bodies_match_start_revision`

Candidate failure-name set must be exactly these nine，unless the P1-only delta work legitimately makes
one of the eight pass **without changing its historical expected hash**。No new failure is allowed；do
not touch `test_issue_cli.py`。

## 12. Required tests

At minimum add dynamic coverage for every item：

### Exact reap

1. success expires only exact target with second due sentinel exact unchanged；
2. not found；job id mismatch；not active；not due；retry after success；
3. resource snapshot corruption；job missing/status/attempt/agent drift；CAS rowcount 0；event append
   failure；each exact pre/post rows/events and rollback；
4. renew-first/reap-first and terminal-first/reap-first dual-connection races；
5. global default/explicit batch results and current benign skip/error summary unchanged。

### Claim policy/fence

6. mode/reason type、unknown、blank、whitespace、oversize、control、global-with-reason validation before
   transaction；
7. none untyped rejection zero mutation；
8. typed none normal/recoverable preserve unrelated due sentinel exact；
9. default/explicit global reaps as before；
10. successful claimed event exact mode/reason evidence，queue-empty no claim event；
11. in-transaction agent missing/offline/host drift fails before any reap/select；
12. two claim/deactivate winner interleavings and offline typed claim。

### Deactivate

13. success exact offline row/audit payload/generation；event failure rollback；
14. dry-run exact zero mutation；
15. blocked individually by active lease、pending、running、recoverable timed_out and multiple blockers；
16. unknown agent、host mismatch、bridge、unknown online state、bad id/reason/actor zero mutation；
17. offline exact retry returns stored event；offline without audit fails；
18. heartbeat reactivation then new same-second generation/event；different-host heartbeat unchanged。

### CLI/golden

19. parser/help valid/default/partial/mixed cases；handlers delegate exact args and blocker exit code；
20. P1 delta rewind exact base fixture；historical hash constants unchanged。

Mock only CLI delegation/failure injection。Use real SQLite rows/connections for transaction/state/races。
Retain all existing test intent；do not delete/skip/xfail/relax old assertions。

## 13. Verification and handoff

First capture exact base failure names in `/tmp` or worker log，not in repo。Then run：

```bash
.venv/bin/python -m py_compile \
  src/coordinate/runtime_lease.py src/coordinate/runtime.py \
  src/coordinate/execution_cli.py \
  tests/test_runtime_lease.py tests/test_runtime.py \
  tests/test_execution_cli.py tests/test_cli_contract.py

.venv/bin/python -m pytest -q \
  tests/test_runtime_lease.py tests/test_runtime.py tests/test_execution_cli.py \
  -k 'not CLIContractTests'

# Run new P1 CLI/delta tests explicitly; they must all pass.
.venv/bin/python -m pytest -q tests/test_cli_contract.py -k 'p9_3c1 or scoped_primitives'

.venv/bin/python -m pytest -q \
  tests/test_runtime_lease.py tests/test_runtime.py \
  tests/test_execution_cli.py tests/test_cli_contract.py

.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
git diff --check
git diff --name-only 9804bbd74c4b826d0620c5939b00e01be9c1120d...HEAD
git status --short
```

If worker chooses different new test names，replace only the explicit P1 `-k` selector and report exact
names；do not skip the P1-only pass gate。

Base evidence：

```text
focused: 214 passed, 37 subtests passed, 8 known failures in 4.40s
full: 2461 passed, 517 subtests passed, 9 known failures in 65.41s
```

Acceptance：

- every new P1 test passes；
- candidate focused/full have no new failure name；
- known failure set is explained exactly；
- pass/subtest counts do not regress after added tests；
- py_compile/compileall/diff-check PASS；
- exact eight-file allowlist；
- exactly one local commit above base。

Worker final handoff reports actual model evidence、HEAD/base/branch/worktree、changed files、exact test
results/failure-name comparison、race tests、residual risks。Worker must not claim approval or deploy。

## 14. Post-worker hard gates

After worker handoff：

1. Codex inspects full diff and runs adversarial tests；
2. corrections use the same eight-file boundary and amend the single candidate commit；
3. fresh independent exact-revision result reviewer must return APPROVE；
4. only then may fast-forward merge/push occur；
5. Coordinate inert deploy uses installed P0 lock and explicit `--no-restart`；
6. post-deploy only read-only help/version/hash/integrity/FK/zero-residue/lock/status smoke；do not invoke
   new reap/deactivate CLI in production；
7. P2 remains blocked until durable P1 deployment dogfood closes。

P9_3C1_P1_BOOTSTRAP_DRAFT_REVIEW_ONLY
