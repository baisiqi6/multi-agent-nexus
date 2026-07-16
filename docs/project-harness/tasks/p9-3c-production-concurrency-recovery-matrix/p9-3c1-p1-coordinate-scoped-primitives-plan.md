# P9-3C1 P1 Coordinate Scoped Primitives — Detailed Plan

状态：`DRAFT_FOR_INDEPENDENT_PLAN_REVIEW_NO_IMPLEMENTATION`

日期：2026-07-16 Asia/Shanghai

Measurement：`p9-3c1-p1-coordinate-scoped-primitives-measurement.md`

Parent plan：`p9-3c1-production-plan.md`。Parent Round 2 approval only opened P0 bootstrap；
it does not authorize this P1 implementation。This exact P1 plan must receive independent
`APPROVE` before Codex may generate a worker bootstrap；bootstrap itself then requires a fresh
exact-SHA review。

## 1. Goal and non-goals

P1 delivers three Coordinate primitives required before the inert P9-3C1 controller：

1. exact lease/job scoped reap；
2. typed claim `reap_mode=global|none` with an audited reason for `none`；
3. audited runtime-agent deactivate with transactional claim/deactivate fencing。

Non-goals：

- no schema/migration/version bump；
- no MultiNexus client/agentd propagation（P2）；
- no controller/config/systemd/catalog/fixture assets（P2）；
- no production mutation invocation、fixture activation、job submission、lease/reap/deactivate；
- no service restart；
- no change to global reap default、untyped claim semantics、routing or delivery；
- no cleanup/deletion of historical agent/runner/job/lease/event rows。

## 2. Exact source and package boundary

- Coordinate base：`9804bbd74c4b826d0620c5939b00e01be9c1120d`。
- MultiNexus read-only reference：`1b1d1fd1c5c160e3ede16ee2f07fb2989990e3c2`。
- Required isolated worktree/branch will be bound by the later bootstrap。
- Proposed allowlist（worker bootstrap may narrow but not widen without plan rereview）：

1. `src/coordinate/runtime_lease.py`
2. `src/coordinate/runtime.py`
3. `src/coordinate/execution_cli.py`
4. `tests/test_runtime_lease.py`
5. `tests/test_runtime.py`
6. `tests/test_execution_cli.py`
7. `tests/test_cli_contract.py`
8. `tests/fixtures/cli_contract.json`

No MultiNexus file、schema file、dependency、version、docs or unrelated test is modified by worker。

## 3. Shared input and transaction rules

- All new ids/reasons/actors are runtime type-checked；bool is not accepted as string/int。
- `lease_id/job_id/agent_id/host_id/actor` use nonblank stripped-stable bounded text with no control
  characters；reason maximum is 512 chars, actor/id maximum 128 unless an existing stricter contract
  applies。
- Values with leading/trailing whitespace are rejected, not silently normalized, except CLI parser
  passes exact bytes and the validator may compare `value == value.strip()`。
- Validation errors occur before `BEGIN IMMEDIATE` and before durable writes；core functions repeat
  required validation so direct API use cannot bypass CLI。
- Every multi-row operation is one transaction。Any CAS/event/validation exception rolls back all
  job/lease/agent/event changes and leaves `conn.in_transaction == False` for top-level APIs。
- Tests compare exact rows/events before/after failure；asserting only an error string is insufficient。

## 4. P1.1 exact scoped reap

Add a distinct public primitive, suggested name：

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

It must：

1. validate exact inputs before transaction；
2. `BEGIN IMMEDIATE` once；
3. select only `WHERE lease_id = ?`，never call `_find_due_active_leases()` and never scan global
   due rows；
4. require selected row `job_id` exact match、status active、canonical resource snapshot、due at
   transaction clock；
5. reuse/refactor `_reap_one_lease()` correctness for stored attempt/agent/running job/CAS/events；
6. commit one target outcome or rollback；
7. return bounded deterministic JSON-ready result with mode、lease/job/attempt/agent and
   `reaped_count=1` on success。

Not found、job mismatch、released/expired/not-due、resource corruption、missing/mismatched job、
attempt/agent mismatch、CAS or event failure all return nonzero through the CLI and perform zero
durable mutation。Exact retry after success is a loud non-mutating failure；P9-3C1 controller must
ledger the original success rather than use idempotent global semantics。

Concurrency：

- renew commits first -> exact reap observes not due and fails with zero mutation；
- exact reap commits first -> renew/terminal report sees expired stale authority and fails closed；
- terminal report commits first -> exact reap sees non-active and fails without a second terminal event；
- unrelated due sentinel lease/job/events remain byte-for-byte/row-for-row unchanged。

### CLI dispatch

Extend：

```text
coordinate runtime job lease reap \
  --lease-id <lease-id> --job-id <job-id> --actor <actor>
```

Parser/handler contract：

- `--batch-size` becomes optional/default `None`；
- no exact ids and no explicit batch dispatches legacy global `batch_size=100`；
- explicit `--batch-size N` preserves existing global behavior/validation；
- `--lease-id` and `--job-id` must appear together；
- exact pair is mutually exclusive with explicit `--batch-size`；
- partial/mixed/invalid arguments fail before core invocation and DB mutation；
- output remains one `{"result": ...}` JSON object on success；core `ValueError` contract yields
  existing CLI nonzero error behavior。

## 5. P1.2 claim-time reap policy

Extend Coordinate `runtime.claim_job()` and `runtime_lease.claim_leased_job()`：

```python
reap_mode: str = "global"
reap_reason: str | None = None
```

Contract：

- only exact `global|none`；default `global` preserves every existing caller；
- `global` rejects any non-`None` reason；
- `none` requires nonblank、stripped-stable、<=512、control-char-free reason；
- invalid/partial combination fails before transaction/global reap/select/CAS/event；
- `global` executes current `_reap_due_leases_in_transaction()` and preserves error behavior；
- `none` does not call any global due selector/reaper and proceeds directly to deterministic claim；
- every successful typed `job.claimed` payload includes exact keys
  `reap_mode` and `reap_reason`（JSON null for global，canonical string for none）；
- queue-empty/blocked claim creates no claim event；future P2 controller ledger records argv/result。
- `none` is valid only for a typed managed agent with an exact executor binding；an untyped/legacy
  agent using `none` fails before job/event mutation。Untyped default/global behavior remains exact
  backward compatible and does not gain a new implicit reap。

CLI：

```text
coordinate runtime job claim \
  --agent-id <id> \
  [--reap-mode {global,none}] \
  [--reap-reason <bounded-reason>]
```

CLI default remains global。`none` normal and `--recoverable` paths use the same policy validation；
recovery evidence remains independently required and cannot substitute for reap reason。

Required sentinel proof：place at least one unrelated due typed lease/job in the same DB。Normal and
recoverable `none` claim must leave its lease/job/events exact unchanged while claiming only the target。
Default/explicit global regression tests must demonstrate current reap behavior remains available。

## 6. P1.3 transactional agent deactivate

Add runtime API and CLI：

```text
coordinate runtime agent deactivate \
  --agent-id <id> --host-id <host> \
  --reason <bounded-reason> --actor <actor> [--dry-run]
```

API suggested name `deactivate_agent()`。Within one `BEGIN IMMEDIATE` transaction it must：

1. re-read exact agent；unknown -> nonzero；
2. require exact host match；
3. require `client_type == "agentd"`；bridge/non-agentd -> nonzero；
4. validate online state is a known `online|offline` value；
5. query exact agent active leases；
6. query assigned jobs with `pending`、`running`、or `timed_out AND recoverable=1`；
7. if any blocker exists, rollback/commit-no-change and return bounded JSON blocker result with
   `deactivated=false` and handler exit nonzero；
8. `--dry-run` performs all identity/blocker checks and returns projected JSON with zero update/event；
9. success updates only exact agent `online_state=offline`/`updated_at` and appends one audited
   `agent.deactivated` event with agent、host、actor、reason、previous state、deactivated_at；
10. transaction commits atomically；event failure rolls back agent update。

Idempotency/lifecycle：

- retry while already offline returns stable offline JSON and the original event evidence without a
  second update/event；
- an offline row without a matching prior `agent.deactivated` audit event is not silently blessed as
  a successful retry；return `offline_without_deactivation_audit` nonzero with zero mutation；
- first deactivation event key is bound to agent、host and the online epoch (`last_seen_at` or an
  equally stable pre-update value), so a later same-host heartbeat can reactivate and a later legitimate
  deactivation creates a new audit event rather than conflicting with history；
- same-host heartbeat after offline remains supported；P9-3C1 cleanup treats unexpected post-cleanup
  reactivation as an incident；
- different-host heartbeat remains fail closed。

### Claim/deactivate fence

Fix the measured pretransaction-online race：typed claim must re-read exact agent online + host **inside
the same `BEGIN IMMEDIATE` transaction before any reap/select/CAS**。Direct `claim_leased_job()` callers
must receive equivalent protection。

- claim transaction wins -> active lease/running job blocks deactivate；
- deactivate transaction wins -> claim sees offline inside its transaction and performs zero reap/job/
  lease/event mutation；
- offline agent cannot typed-claim even if a pending audit row exists。

Use two file-backed connections and deterministic barriers/hooks to test both interleavings；a purely
sequential test is insufficient for the measured race。

## 7. CLI golden compatibility

Update `tests/fixtures/cli_contract.json` through the established deterministic generator for only：

- new `runtime agent deactivate` command/handler；
- new claim reap flags；
- new exact reap flags/help。

`tests/test_cli_contract.py` must：

- add handler/path expectations for deactivate；
- add parser/help assertions for valid/default/invalid combinations；
- add a P1 delta rewind that strips only these P1 additions from candidate generated contract and exact
  matches base fixture SHA-256
  `13cb4f3b748fdf7dc1d91dfbb27d9a214d23dfff1112d253d0e01aa0c701ad3d` and bytes；
- preserve all historical baseline SHA constants and rewinds；do not “fix” old baselines by replacing
  expected hashes with candidate output。

Base has eight known historical CLI rewind failures。Candidate must keep the same exact failure names
and no new failure；P1 delta-specific tests must pass。The unrelated issue-handler AST baseline failure also remains unchanged。

## 8. Required dynamic test matrix

At minimum：

1. exact reap success with a second due sentinel unchanged；
2. exact not-found/job-mismatch/not-active/not-due/corrupt-snapshot/job-state/attempt/agent/CAS/event
   failures all zero mutation；
3. exact renew/report race both winner orderings；
4. global reap default/explicit batch compatibility；partial/mixed exact CLI args zero core calls；
5. claim `global|none` validation before transaction；
6. normal and recoverable `none` claims preserve unrelated due sentinel rows/events；
7. default global claim regression and `job.claimed` payload policy evidence；
8. deactivate success/dry-run/exact retry/reactivate/deactivate-next-epoch；
9. deactivate unknown/host mismatch/bridge/bad reason/actor/state all zero mutation；
10. each active-lease/pending/running/recoverable-timeout blocker and multiple blockers；
11. deactivate event failure rolls back agent；
12. deterministic claim-wins and deactivate-wins concurrency with two connections；
13. offline typed claim zero mutation；
14. CLI handler delegation/JSON/exit contract and golden P1 delta proof。

Do not weaken existing tests、replace real DB behavior with mocks where state/race proof is required、or
assert only SQL call strings。

## 9. Verification and failure baseline

Worker/bootstrap must run：

```bash
.venv/bin/python -m py_compile \
  src/coordinate/runtime_lease.py src/coordinate/runtime.py \
  src/coordinate/execution_cli.py \
  tests/test_runtime_lease.py tests/test_runtime.py \
  tests/test_execution_cli.py tests/test_cli_contract.py
.venv/bin/python -m pytest -q \
  tests/test_runtime_lease.py tests/test_runtime.py \
  tests/test_execution_cli.py tests/test_cli_contract.py
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
git diff --check
```

Base focused：`214 passed, 37 subtests, 8 known failures`。Base full：
`2461 passed, 517 subtests, 9 known failures`。Candidate acceptance requires：

- all new/P1 tests pass；
- no new failed test；
- exact known failure-name set unchanged；
- historical failure actual/expected hashes not silently normalized to new candidate；
- full pass/subtest counts do not regress after accounting for added tests；
- exact eight-file allowlist and one candidate commit。

## 10. Review, deploy and next gate

Sequence：

1. independent non-Codex exact-plan review；
2. resolve every P0/P1 finding and bind approved plan SHA；
3. generate exact worker bootstrap；
4. fresh independent bootstrap review；
5. non-Codex coding worker in isolated Coordinate worktree；
6. Codex adversarial result review and fresh independent exact-revision result review；
7. fast-forward merge/push；
8. deploy Coordinate under the installed P0 production lock with explicit `--no-restart`；
9. only read-only help/version/hash/integrity/FK/zero-residue/lock/status smoke；do not invoke reap or
   deactivate in production；
10. durable dogfood/progress/roadmap projection。

P2 bootstrap remains blocked until P1 exact source、deployed hashes and read-only smoke close。

P9_3C1_P1_PLAN_READY_FOR_INDEPENDENT_REVIEW
