# P9-0A6 Post-Closeout Module Review — Measurement and Decision

> Provider/model: `kimi-code/kimi-for-coding-highspeed`
> Kimi JSONL session: `019f5965-5678-7000-a255-5e280348ca89`
> Worker bootstrap: `docs/project-harness/tasks/p9-0a6-post-closeout-module-review/worker-bootstrap.md`
> Approved plan: `docs/project-harness/tasks/p9-0a6-post-closeout-module-review/plan.md`
> Plan SHA-256: `825d1aec89877b7cfff1b05938dabde4968d88fd3f29b2baa22359d02d6ee792`

This document records the independent remeasurement of `completion.py`, `db.py`, and
`transitions.py` after Slice 4 closeout. The deliverable is a durable no-code-change
architecture decision with exact commands, outputs, and rubric scoring.

## 1. Baseline and authority verification

### 1.1 Coordinate baseline

```text
$ cd /Users/yinxin/projects/coordinate
$ git rev-parse HEAD
15020c2204e8e05c6304f6ed83a5fed83ad12eae
$ git rev-parse origin/main
15020c2204e8e05c6304f6ed83a5fed83ad12eae
$ git status --short
?? .qoder/
```

Coordinate `HEAD == origin/main == 15020c2` and the only dirty state is the
user-owned `.qoder/` directory, matching the approved-plan exception.

### 1.2 MultiNexus baseline

```text
$ cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-0a6-kimi
$ git rev-parse HEAD
54f7e5025b2d8e30103c9e14f4fb0e742f3a8afc
$ git merge-base --is-ancestor f2ad2042836bc8d0140de9c63f7fbe4c2694984d HEAD && echo ancestor
ancestor
$ git log --oneline f2ad2042836bc8d0140de9c63f7fbe4c2694984d..HEAD
54f7e50 docs: authorize P9-0A6 Kimi worker
```

The approved MultiNexus content baseline `f2ad204` is an ancestor of `HEAD`; the
single newer commit is the P9-0A6 worker authorization document only.

### 1.3 Plan SHA-256

```text
$ sha256sum docs/project-harness/tasks/p9-0a6-post-closeout-module-review/plan.md
825d1aec89877b7cfff1b05938dabde4968d88fd3f29b2baa22359d02d6ee792  docs/project-harness/tasks/p9-0a6-post-closeout-module-review/plan.md
```

The plan SHA-256 matches the approved revision exactly.

### 1.4 Deployment and schema identities at planning time

From Slice 4D closeout (`tasks/slice-4d-projection-doctor-evidence/closeout.md`):

- Coordinate deployed/installed: `15020c2`.
- Code schema / production DB user version: `11 / 11`.
- Production DB backup integrity: `ok`.
- Full production doctor before and after S4-D closeout: `rc=0`, `projection_ok=true`,
  `errors=0`, with only the two legitimate expired-unused receipt warnings.
- MultiNexus completion projection deployed at `9281f84` before receipt consume.
- Receipt `ee38b348-b2fb-4ad1-b9af-dc01f4d6c144` completed
  authorized/claimed/applied/task.done/consumed.
- Slice 4 stage receipt `046f5bf9-62ad-40ea-a828-c2b984531212` consumed.

## 2. Physical and AST metrics

### 2.1 Line counts

```text
$ wc -l src/coordinate/completion.py src/coordinate/db.py src/coordinate/transitions.py
  1038 src/coordinate/completion.py
  1798 src/coordinate/db.py
  1391 src/coordinate/transitions.py
  4227 total
```

### 2.2 Top-level AST counts

```text
$ python3 - <<'PY'
import ast, pathlib
for p in ['src/coordinate/completion.py','src/coordinate/db.py','src/coordinate/transitions.py']:
    tree = ast.parse(pathlib.Path(p).read_text())
    tl_funcs = [n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    classes  = [n.name for n in tree.body if isinstance(n,ast.ClassDef)]
    print(f'{p}: top-level funcs={len(tl_funcs)}, classes={len(classes)}')
PY
src/coordinate/completion.py: top-level funcs=26, classes=8
src/coordinate/db.py: top-level funcs=54, classes=6
src/coordinate/transitions.py: top-level funcs=28, classes=9
```

### 2.3 Section and function ranges

`completion.py` (1,038 lines, 26 top-level functions, 8 classes):

| Section | Range | Notes |
|---|---|---|
| Gate helpers | L51–201 | `MarkDoneGateResult`, `check_mark_done_gate`, fingerprint helpers, checklist read |
| Result dataclasses | L209–347 | `CompletionReceiptError`, `ReceiptEvidence`, `CompletionReceipt`, `CompletionClaimResult`, `CompletionApplyResult`, `CompletionConsumeResult` |
| Timestamp/event helpers | L361–425 | parsing, UTC stamp, receipt event lookup, review/forge evidence |
| prepare | L433–554 | validate gate and issue `completion.authorized` event |
| claim | L635–756 | `authorized -> claimed`; BEFORE canonical write |
| apply | L764–854 | `claimed -> applied`; AFTER canonical write |
| consume | L862–1038 | `applied -> task.done + completion.consumed`; atomic SAVEPOINT |

`db.py` (1,798 lines, 54 top-level functions, 6 classes):

| Section | Range | Notes |
|---|---|---|
| Connection lifecycle | L23–68 | connection registry, `CoordinatorConnection`, `connect`, `initialize` |
| Workspace / host / runner dataclasses | L72–188 | `Workspace`, `WorkspaceHostProfile`, `AppendEventResult`, `RunnerProfile` |
| Workspace CRUD | L202–354 | upsert/get/list workspace and host profile |
| Agent registry | L360–665 | validation, effective resolution, manual override, removal |
| Authoritative registry sync | L668–932 | `sync_workspace_agents`: version/hash conflict rules, atomic replace-sync |
| Runner profile | L935–989 | upsert/get/list |
| Job repository | L992–1168 | create/get/list/mark-started/completed/cancelled |
| Delivery repository | L1171–1339 | create/get/list/mark-sending/sent/failed plus recovery |
| Task group / decision request | L1342–1416 | lifecycle support records |
| Task mirror | L1419–1483 | `upsert_task_mirror`, `list_task_mirrors` |
| Split operation ledger | L1487–1645 | `SplitOperation`, insert/get/update/list |
| Event ledger | L1648–1798 | `append_event`, `get_event`, `list_events`, `find_events`, `latest_event` |

`transitions.py` (1,391 lines, 28 top-level functions, 9 classes):

| Section | Range | Notes |
|---|---|---|
| Reconcile hook | L28–35 | `_post_mutation_reconcile` |
| accept_task | L39–179 | assignment.accepted / mutation_failed |
| handoff_task | L183–319 | handoff.requested / mutation_failed |
| blocker_task | L323–456 | assignment.blocked / mutation_failed |
| unblock_task | L460–601 | assignment.unblocked / mutation_failed |
| closeout_task | L605–742 | closeout.requested / mutation_failed |
| review_result_task | L746–885 | review.approved/changes_requested / mutation_failed |
| mark_done_task | L896–1125 | mark-done canonical mutation + task.done / mutation_failed |
| mark_done_files | L1128–1323 | coding-host file-only half of host-aware mark-done |
| mark_done_record | L1326–1391 | server DB-only half of host-aware mark-done |

### 2.4 Slice-4 churn from `084419c` to `15020c2`

```text
$ git log 084419c..15020c2 --oneline -- src/coordinate/completion.py src/coordinate/db.py src/coordinate/transitions.py
4847798 S4-C2: adopt issue.materialize split-operation contract
f0fff49 Slice 4C1: task.create split operation contract, lock, ledger and tests
ff6b8bf fix: enforce atomic agent registry mutations
6ee743b Slice 4B1: agent registry model (v10)

$ git diff --stat 084419c 15020c2 -- src/coordinate/completion.py src/coordinate/db.py src/coordinate/transitions.py
 src/coordinate/db.py | 778 ++++++++++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 703 insertions(+), 75 deletions(-)
```

`completion.py` and `transitions.py` have zero Slice-4 churn. `db.py` has four
commits and `+703/-75`; the churn is concentrated in agent registry model/fixes
and split-operation ledger, both Phase 9 isolation inputs. The job repository
region (`create_job` through `mark_job_cancelled`) had zero changes in the
Slice-4 diff.

## 3. Import direction and cycle check

### 3.1 Direct imports inside the three modules

```text
completion.py:
  from .db import append_event, find_events, get_workspace, latest_event, row_to_dict
  from .harness import HarnessAdapter, HarnessError

db.py:
  from coordinate.schema import (...)

transitions.py:
  from .completion import (CompletionReceiptError, MarkDoneGateResult, ReceiptEvidence, ...)
  from .db import append_event, get_workspace, row_to_dict
  from .harness import HarnessAdapter, HarnessError, HarnessMutationResult
  from .reconcile import reconcile_workspace
```

### 3.2 Direct importers of each target

```text
completion: 3 importers -> cli.py, completion_cli.py, transitions.py
db:         34 importers -> assignments.py, audit.py, branches.py, bus.py, ci.py, cli.py,
            cli_support.py, completion.py, completion_cli.py, daemon.py, delivery_cli.py,
            doctor.py, execution_cli.py, handoff.py, harness.py, issues.py, jobs.py,
            onboarding.py, operator.py, plan_gate.py, planning_cli.py, policy.py, pr_cli.py,
            pr_contracts.py, pr_publishing.py, pr_recording.py, projection_doctor.py, prs.py,
            reconcile.py, reviews.py, runtime.py, split_operations.py, transitions.py,
            workspace_cli.py
transitions: 4 importers -> cli.py, completion_cli.py, daemon.py, workflow_cli.py
```

### 3.3 Cycle analysis

The dependency graph at the measured boundary is acyclic:

```text
db -> schema
completion -> db + harness
transitions -> completion + db + harness + reconcile
CLI/daemon -> transitions/completion
```

`db.py` imports neither `completion` nor `transitions`; `completion.py` imports `db`
only. Extracting `completion.py` or `transitions.py` would keep the same direction, but
extracting any repository subset from `db.py` must avoid introducing a cycle back from
the remaining modules through re-exports.

## 4. Transaction and authority boundaries

### 4.1 `completion.py` — receipt state machine

The module owns one authority boundary: the completion receipt lifecycle
`authorized -> claimed -> applied -> consumed`.

- `prepare_completion_receipt` (L433–554) reads the harness gate and writes a
  `completion.authorized` event via `append_event`.
- `claim_completion_receipt` (L635–756) validates binding/expiry and writes
  `completion.claimed` (BEFORE the canonical checklist write).
- `apply_completion_receipt` (L764–854) validates claimed state and writes
  `completion.applied` (AFTER the canonical checklist write).
- `consume_completion_receipt` (L862–1038) is intentionally atomic:

```python
conn.execute("SAVEPOINT consume_receipt")
done_result = append_event(..., event_type="task.done", commit=False)
consumed_result = append_event(..., event_type="completion.consumed", commit=False)
conn.execute("RELEASE SAVEPOINT consume_receipt")
conn.commit()
```

Splitting the consume path across modules would scatter the atomic-consume review
surface and make it harder to prove that `task.done` and `completion.consumed` are
always written together or rolled back together.

### 4.2 `db.py` — repository facade and Slice-4 transaction seams

- `append_event` (L1648–1693) is the single event-ledger write primitive. It supports
  `commit=False` and `idempotency_key` so callers can compose multi-event transactions.
- `upsert_task_mirror` (L1419–1474) mirrors harness task state into the DB with a
  stable `(workspace_id, task_id)` key.
- `sync_workspace_agents` (L668–932) uses `SAVEPOINT workspace_agent_registry_sync`,
  validates source identity/version/hash conflict rules, then atomically updates
  source metadata, authoritative/legacy entries, the workspace revision, the
  `agents_json` projection, and the audit event.
- `insert_split_operation` / `update_split_operation_event` (L1525–1607) form the
  split-operation ledger used by `task.create` and `issue.materialize`; the record
  half binds the ledger row to an `append_event` call.
- Job, task group, and decision request write helpers each call `conn.commit()`
  independently; caller orchestration (`jobs.py`, `runtime.py`, etc.) coordinates
  them at the application layer, not inside one larger DB transaction.
- `append_event` and `create_delivery` support `commit=False`, so event/delivery
  helpers can opt into caller-owned multi-event transactions where the caller
  owns the whole DB commit (for example, the atomic consume path in
  `completion.py`). These two cases should not be blurred.

### 4.3 `transitions.py` — harness mutations

Each public function follows the same shape but with operation-specific payloads:

1. Build an idempotency key specific to the operation, task, actor, and decision.
2. Call `HarnessAdapter.run_mutation(...)` with operation-specific CLI arguments.
3. On success, append one `assignment.*`, `handoff.*`, `review.*`, or `task.done`
   event; on failure, append `harness.mutation_failed`.
4. Run `_post_mutation_reconcile`.

The six mutations differ in event type, payload fields, actor defaults, and failure
evidence. A generic template would hide those operation-specific test contracts.

`mark_done_task` additionally depends on `completion.py` for
`check_mark_done_gate` and `compute_mark_done_fingerprints`, and on `db.py` for
`append_event`. `mark_done_files` and `mark_done_record` are the host-aware split
halves introduced for A0 runtime-only server safety.

## 5. Callers and test ownership

### 5.1 Test files directly covering the targets

| Target module | Test file | Collected tests |
|---|---|---|
| `completion.py` | `tests/test_completion.py` | included in 359 target-focused tests |
| `transitions.py` | `tests/test_transitions.py` | included in 359 target-focused tests |
| `db.py` | `tests/test_db.py` | included in 359 target-focused tests |
| Agent registry in `db.py` | `tests/test_agent_registry.py` | included in 359 target-focused tests |
| Split operations in `db.py` | `tests/test_split_operations.py` | included in 359 target-focused tests |

```text
$ python -m pytest tests/test_completion.py tests/test_transitions.py tests/test_db.py \
  tests/test_agent_registry.py tests/test_split_operations.py -q
359 passed, 43 subtests passed in 0.82s
```

### 5.2 CLI/daemon callers

- `cli.py` imports `completion` and `transitions` directly for the root parser.
- `completion_cli.py` imports `completion` and `transitions` (for `mark_done_files`/`mark_done_record`).
- `daemon.py` imports `transitions.mark_done_task` for the Discord bridge.
- `workflow_cli.py` imports `transitions` for assignment handlers.

No production caller imports `db.py` through a dynamic lookup; all imports are static.

## 6. Extraction candidates and rubric scoring

The plan requires all seven rubric conditions to recommend extraction:

1. one owner/authority and one dependency direction are explicit;
2. transaction boundaries do not cross the proposed seam, or the seam owns the whole transaction;
3. public identity/call-site compatibility can be preserved without circular imports;
4. permanent tests can prove movement-only behavior and cold import orders;
5. the change directly enables a named P9-1+ isolation package;
6. the benefit is more than reducing file length or duplication;
7. the target is stable enough that current Slice-4 churn will not immediately reopen the boundary.

### 6.1 Candidate A — extract the whole receipt state machine from `completion.py` intact

Candidate boundary: move `prepare_completion_receipt`, `claim_completion_receipt`,
`apply_completion_receipt`, `consume_completion_receipt`, the result/error dataclasses,
and receipt helpers together to a new module. This is an intact function/state-machine
movement, not a split of the internal consume SAVEPOINT.

| Rubric | Score | Evidence |
|---|---|---|
| 1. Owner/authority | ✓ | `completion.py` already owns the receipt lifecycle. |
| 2. Transaction boundary | ✓ | Intact movement preserves the internal `SAVEPOINT consume_receipt`; the seam still owns the whole consume transaction. |
| 3. Public identity | △ | The public home is currently `coordinate.completion`; an intact move would require re-export from `coordinate.completion` (or migration of the 3 production callers and tests) to preserve call-site compatibility. |
| 4. Tests | ✓ | `tests/test_completion.py` exists; movement-only tests could be added. |
| 5. P9-1+ consumer | ✗ | No named Phase 9 package requires the receipt state machine to move; P9-1+ cares about job context, not receipt authority. |
| 6. Benefit beyond lines | ✗ | The only benefit would be shorter `completion.py`; the authority boundary is already explicit and `completion_cli.py` already provides the transport seam. |
| 7. Stability | ✓ | Zero Slice-4 churn. |

**Verdict:** defer/retain. Without a named P9-1+ consumer, the re-export facade cost outweighs the line reduction.

### 6.2 Candidate B — extract generic harness-mutation template from `transitions.py`

| Rubric | Score | Evidence |
|---|---|---|
| 1. Owner/authority | ✗ | Six different operations (accept, handoff, blocker, unblock, closeout, review-result, mark-done) each have distinct authority semantics. |
| 2. Transaction boundary | ✗ | Each function composes a harness mutation with `append_event` and reconcile; the seam does not own the whole transaction. |
| 3. Public identity | ✓ | Re-exports are possible, but operation-specific result types are the public identity. |
| 4. Tests | ✓ | `tests/test_transitions.py` exists. |
| 5. P9-1+ consumer | ✗ | No named Phase 9 package is blocked by the current module layout. |
| 6. Benefit beyond lines | ✗ | A generic template would hide payload/event-type/idempotency differences that tests currently make explicit. |
| 7. Stability | ✓ | Zero Slice-4 churn. |

**Verdict:** defer/retain. Operation-specific authority and test contracts outweigh repetition.

### 6.3 Candidate C — extract mark-done adapters from `transitions.py`

| Rubric | Score | Evidence |
|---|---|---|
| 1. Owner/authority | △ | `mark_done_files`/`mark_done_record` are host-aware halves, but `mark_done_task` depends on `completion.py` gate/fingerprint logic. |
| 2. Transaction boundary | ✗ | `mark_done_task` composes harness mutation + `task.done` event + reconcile; splitting would leave a compatibility facade. |
| 3. Public identity | ✓ | Could be re-exported. |
| 4. Tests | ✓ | Covered by `tests/test_transitions.py` and `tests/test_completion_cli.py`. |
| 5. P9-1+ consumer | ✗ | No named Phase 9 package requires this. |
| 6. Benefit beyond lines | ✗ | Moving only adapters would be a compatibility-facade exercise without changing authority or isolation readiness. |
| 7. Stability | ✓ | Zero Slice-4 churn. |

**Verdict:** defer/retain.

### 6.4 Candidate D — extract job repository from `db.py`

Candidate boundary: move `create_job`, `get_job`, `list_jobs`, `mark_job_started`,
`mark_job_completed`, and `mark_job_cancelled` to a new `job_repository` module.

Exact Slice-4 diff check (`git diff 084419c 15020c2 -- src/coordinate/db.py`) shows
no changes inside the job function region; the `+703/-75` churn is concentrated in
agent-registry code, `create_delivery(commit=...)`, and the split-operation ledger.
Each job write helper currently calls `conn.commit()` itself, so the candidate does
not depend on being composed into larger DB transactions at this layer.

However, `create_job` depends on `get_workspace`, `get_runner_profile`,
`_absolute_path`, `_json_dumps`, and `utc_now` from the current `db.py`. If the job
functions move while `db.py` re-exports them for backward compatibility, the new
module would need to import those helpers from `db.py`, and any future repository
extracted from `db.py` that also needs them risks a cycle or a growing shared-utils
facade. Migrating every caller instead avoids the cycle but increases the change
surface beyond the candidate.

| Rubric | Score | Evidence |
|---|---|---|
| 1. Owner/authority | △ | Jobs are a clear aggregate, but `jobs.py` already orchestrates them and `runtime.py`/`execution_cli.py` are active callers; repository ownership is shared until P9-1 defines job context. |
| 2. Transaction boundary | ✓ | Each write helper (`create_job`, `mark_job_started`, `mark_job_completed`, `mark_job_cancelled`) calls `conn.commit()` itself; intact movement preserves that ownership. |
| 3. Public identity | △ | Functions could be re-exported, but `create_job` depends on `db.py` helpers; naive re-export creates a `job_repository <-> db` cycle/facade risk unless shared primitives also move or all callers migrate. |
| 4. Tests | ✓ | Existing tests cover jobs; movement-only tests could be added. |
| 5. P9-1+ consumer | △ | P9-1 job-scoped context will need a job repository, but the aggregate boundary depends on context/transaction ownership not yet defined; extracting now risks the wrong seam. |
| 6. Benefit beyond lines | △ | Would shorten `db.py`, but the real value is defining job-scoped context, which is P9-1 work. |
| 7. Stability | ✓ | The job region had zero Slice-4 churn; it is stable. |

**Verdict:** defer to P9-1. The seam is plausible but P9-1 must define the context
and helper-ownership boundary before the extraction can avoid a cycle or a large
compatibility facade.

### 6.5 Candidate E — extract delivery repository from `db.py`

| Rubric | Score | Evidence |
|---|---|---|
| 1. Owner/authority | △ | Deliveries are owned by `bus.py`/`policy.py` orchestration, not by one module. |
| 2. Transaction boundary | ✗ | `create_delivery` is called inside event-to-delivery pipelines; the seam does not own the whole transaction. |
| 3. Public identity | ✓ | Re-export possible. |
| 4. Tests | ✓ | Covered by `tests/test_db.py` and `tests/test_policy.py`. |
| 5. P9-1+ consumer | △ | P9-4 observation contract may touch deliveries, but not as the first extraction. |
| 6. Benefit beyond lines | ✗ | Would only reduce `db.py` length. |
| 7. Stability | ✗ | `db.py` churn is high. |

**Verdict:** defer to P9-4 or later.

### 6.6 Candidate F — extract event ledger from `db.py`

| Rubric | Score | Evidence |
|---|---|---|
| 1. Owner/authority | ✓ | `append_event`/`get_event`/`find_events`/`latest_event` are a coherent surface. |
| 2. Transaction boundary | △ | `append_event(commit=False)` is designed to be composed; extracting it alone does not own caller transactions. |
| 3. Public identity | △ | Could be re-exported. Exact direct usage: 19 production modules import `append_event` from `coordinate.db` (`branches.py`, `ci.py`, `pr_publishing.py`, `pr_recording.py`, `prs.py`, `reviews.py` use absolute imports; the rest use relative `.db` imports); 20 modules contain `append_event` call sites; 67 total call sites. A move would need a broad compatibility re-export or caller migration. |
| 4. Tests | ✓ | `tests/test_db.py` covers event ledger. |
| 5. P9-1+ consumer | ✗ | No named P9-1+ package is blocked by `append_event` staying in `db.py`. |
| 6. Benefit beyond lines | ✗ | The benefit is only file length; event ledger is already a clear conceptual surface. |
| 7. Stability | ✗ | `db.py` churn is high. |

**Verdict:** defer/retain.

### 6.7 Candidate G — extract agent registry repository from `db.py`

| Rubric | Score | Evidence |
|---|---|---|
| 1. Owner/authority | ✓ | `sync_workspace_agents` is the authoritative roster sync. |
| 2. Transaction boundary | ✓ | The function owns its SAVEPOINT and commits atomically. |
| 3. Public identity | ✓ | `resolve_effective_agents`, `build_agent_registry_map`, etc. could be re-exported. |
| 4. Tests | ✓ | `tests/test_agent_registry.py` covers the surface. |
| 5. P9-1+ consumer | △ | P9-2 executor identity needs registry, but the registry is versioned and replace-synced; moving it now does not unblock P9-1 job context. |
| 6. Benefit beyond lines | △ | Would separate authority surface, but Slice 4 just stabilized it. |
| 7. Stability | ✗ | Agent registry is the largest source of recent `db.py` churn (`ff6b8bf`, `6ee743b`). |

**Verdict:** defer to P9-2. Recent churn will reopen boundaries if extracted before executor identity is defined.

### 6.8 Candidate H — extract split-operation ledger from `db.py`

| Rubric | Score | Evidence |
|---|---|---|
| 1. Owner/authority | ✓ | `SplitOperation`, `insert_split_operation`, `update_split_operation_event` form one ledger surface. |
| 2. Transaction boundary | ✗ | The ledger row is inserted by `split_operations.py`; the binding event is appended by callers; the seam does not own the whole transaction. |
| 3. Public identity | ✓ | Re-export possible. |
| 4. Tests | ✓ | `tests/test_split_operations.py` covers the ledger. |
| 5. P9-1+ consumer | ✗ | Split operations are a Slice-4 partial-operation primitive, not a P9-1 isolation enabler. |
| 6. Benefit beyond lines | ✗ | Would only shorten `db.py`. |
| 7. Stability | ✗ | Split operations are the other major source of recent `db.py` churn (`4847798`, `f0fff49`). |

**Verdict:** defer/retain.

### 6.9 Rubric summary

No candidate satisfies all seven rubric conditions. The binding blockers are:

- `completion.py`: no named P9-1+ consumer and re-export facade cost (rubrics 5, 6);
  intact movement does not split the consume SAVEPOINT (rubric 2 is satisfied).
- `transitions.py`: operation-specific authority and test contracts (rubrics 1, 2, 6).
- `db.py`: undefined P9-1 aggregate boundaries, helper/cycle/facade cost, and
  repository churn from non-candidate regions (rubrics 3, 5, 7).

## 7. Dogfood projection evidence

Slice 4 closeout repeatedly showed that three authority surfaces are distinct and
currently not converged automatically:

1. **Source harness projection** (committed `mvp-checklist.json` in the development repo).
2. **Deployed harness projection** (the running `/opt/*` artifact).
3. **Control-plane event state** (Coordinate DB events such as `review.completed`).

Evidence from `docs/project-harness/dogfood-feedback.md` (2026-07-13):

- Remote lifecycle mutation was overwritten by a later canonical source deploy because
  the source checklist had not replayed the approved transition; source and deployed
  bytes were identical but both lagged the control DB event state.
- `review.phase` projection is not idempotent under replay: the first source
  `review-result approved` recorded `review.phase=running` (the pre-transition phase),
  while the deployed/control replay recorded `review.phase=review_approved`. The
  checklist fingerprint differed even though the decision and summary were the same.
  The Operator stopped before receipt issuance, replayed the transition in source,
  committed/deployed, and verified exact checklist SHA equality before the terminal
  receipt.

This is a semantic projection/ordering gap, not a Coordinate module-layout defect.
Moving `transitions.py` or `completion.py` code would not fix it; P9-0A6 must route it
to Phase 9 planning instead.

## 8. Decision

### 8.1 Proposed no-change decision

P9-0A6 does **not** extract any production code from `completion.py`, `db.py`, or
`transitions.py`. The decision is based on transaction authority, import/public
identity, test ownership, and Phase 9 readiness—not on line counts. The result is
proposed by this worker; it remains pending Codex result acceptance and Operator
receipt before it can be considered durably closed.

### 8.2 Routing to Phase 9 packages

| Candidate | Disposition | Next package / reason |
|---|---|---|
| Receipt state machine (`completion.py`) | Retain cohesive module | P9-0A already extracted `completion_cli.py` as the transport seam; no further move needed. |
| Harness mutations (`transitions.py`) | Retain cohesive module | P9-1+ will define job-scoped context and transition authority; revisit after P9-1 contract. |
| Job repository (`db.py`) | Defer | P9-1 job-scoped execution context must define transaction ownership first. |
| Delivery repository (`db.py`) | Defer | P9-4 observation contract may revisit delivery/event boundaries. |
| Event ledger (`db.py`) | Defer | Keep in repository facade until P9-1 context stabilizes. |
| Agent registry repository (`db.py`) | Defer | P9-2 executor identity/routing will define registry seam. |
| Split-operation ledger (`db.py`) | Defer | Remains a Slice-4 primitive; not a P9-1 isolation enabler. |

### 8.3 Stop-gate check

No measurement contradicts the planned no-change decision. No candidate satisfies all
seven extraction rubric conditions, so the worker does not invoke the stop gate that
would require a revised plan and new independent review before code edits.

## 9. Validation commands and results

### 9.1 Target-focused tests

```text
$ cd /Users/yinxin/projects/coordinate
$ python -m pytest tests/test_completion.py tests/test_transitions.py tests/test_db.py \
  tests/test_agent_registry.py tests/test_split_operations.py -q
359 passed, 43 subtests passed in 0.82s
```

### 9.2 MultiNexus harness validation

```text
$ cd /Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-0a6-kimi
$ bash scripts/harness/harnessctl validate
Checklist validation passed: .../mvp-checklist.json (4 warning(s)).
```

The four warnings are the known historical extended-workflow items.

### 9.3 MultiNexus harness doctor

```text
$ bash scripts/harness/harnessctl doctor
Doctor complete.
```

Only the known optional `round-2-hardening/plan.md` miss and `init.sh` optional miss
are reported; no new invalid artifacts.

### 9.4 Git checks

```text
$ git diff --check
(no output)

$ git status --short
 M docs/project-harness/dogfood-feedback.md
 M docs/project-harness/progress.md
 M docs/project-harness/roadmap.md
 M docs/project-harness/tasks/phase-9-execution-isolation/plan.md
?? docs/project-harness/tasks/p9-0a6-post-closeout-module-review/measurement.md

$ git diff --name-only
docs/project-harness/dogfood-feedback.md
docs/project-harness/progress.md
docs/project-harness/roadmap.md
docs/project-harness/tasks/phase-9-execution-isolation/plan.md
```

The union of tracked modifications and the untracked `measurement.md` is exactly the
five approved documentation paths; no Coordinate production code, MultiNexus runtime
code, or lifecycle state was modified.

## 10. Residual risks

1. **Source/deploy/control projection ordering** remains an Operator UX gap. It is
   documented in `dogfood-feedback.md` and must be addressed in Phase 9 planning, not
   by P9-0A6 code movement.
2. **`db.py` size** is real (1,798 lines), but the risk is candidate-specific:
   the job repository region had zero Slice-4 churn and is stable, yet its helper
   ownership and P9-1 context boundary are undefined, so extraction now risks a
   `db <-> job_repository` cycle or a large compatibility facade. The agent registry
   and split-operation ledger are the recently churned seams; they should not be
   extracted before P9-2/P9-1 defines their consumers.
3. **`transitions.py` repetition** is real, but a generic template would weaken the
   operation-specific test contracts that Slice 4 closeout relied on.
4. **No production code was changed** in this package; lifecycle, deployment, and
   receipt issuance remain Operator-owned gates after Codex result review.
