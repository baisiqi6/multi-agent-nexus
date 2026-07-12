# Detailed Execution Plan: slice-3-c3-deployment-smoke

> **Status:** revision_after_changes_requested
>
> This plan may be reviewed now. It does not authorize push, SSH, deployment,
> service restart, production-database mutation, real delivery, or smoke-fixture
> creation. Those actions require the later explicit remote/runtime gate.

## Identity and revision

- Parent stage: `slice-3-completion-closeout` / `S3-C3`
- Package id: `slice-3-c3-deployment-smoke`
- Plan author / architect: Codex Operator
- Intended plan reviewer: independent Claude Code CLI session; record the effective
  provider/model from its JSONL rather than assuming the requested alias
- Intended execution worker: Oh-My-Pi or Claude Code after approval and the explicit
  remote/runtime gate; it executes only the fixed runbook and cannot approve results
- Intended result reviewer: Codex Operator
- Plan path:
  `docs/project-harness/tasks/slice-3-c3-deployment-smoke/plan.md`
- Plan revision authority: latest Coordinate `plan.ready` event and its
  `plan_content_hash`
- Supersedes: the first registered revision

## Refreshed preflight

Snapshot refreshed locally on 2026-07-12:

- Coordinate source: `/Users/yinxin/projects/coordinate`, `main` at
  `e0cc1561cd20b0f22389234aefe92d01273860e4`, five commits ahead of
  `origin/main` (`2e8427b6325042ca81f19a631e7b9e5a184dfd21`). The only dirty path is the
  pre-existing untracked `.qoder/`, which must remain untouched.
- MultiNexus source: `/Users/yinxin/projects/multinexus`, `main` at
  `82c5613f9d8fcb25c5ca936a24c61536e567df50`, thirteen commits ahead of
  `origin/main` (`b84780d8122592b75112e3db99b334f958ae34c3`), clean before this plan draft.
- Coordinate `e0cc1561` is the independently reviewed Slice 3 integration. Main-side
  validation recorded focused 342, full 1,347, and checklist validation with zero
  warnings.
- MultiNexus `82c5613` contains the durable S3-C2 closeout record. Its local
  `discord-nexus` mirror shows S3-C1 and S3-C2 closed while the Slice 3 umbrella
  remains open.
- Deployment entrypoint: MultiNexus `scripts/deploy-server.sh`; current SHA-256
  `84c1079a6f2e1ead99ece9d6307c2dba54f5b51fa49f475ccf08e7d2e74df929`.
- Server smoke entrypoint: `scripts/server-smoke.sh`; current SHA-256
  `b17b1d9b1ac30170d7ace50d309c9e5d652cb9f815a9326da3efca82b4cd3e30`.
- The configured SSH alias and `/Users/yinxin/.local/bin/coord-ssh` wrapper exist.
  No SSH or production command was run during this plan refresh.
- Current deployed SHAs, service state, database state, free space, backup state,
  remote harness capability, and runtime agents are deliberately unverified until
  the explicit remote/runtime gate. The execution preflight must obtain them and
  fail closed before any upload or restart.

The formal deploy must not use Coordinate's dirty development checkout or
`--allow-dirty`. The Operator creates a temporary clean release worktree detached at
the approved Coordinate SHA and passes it through `--coordinate-src`. MultiNexus must
also be clean at the approved SHA. Any SHA, ancestry, tracked-content, plan, deploy
script, or server-topology drift invalidates approval and returns this plan to review.

## Problem and evidence

Slice 3 has local code and integration PASS but no evidence that the receipt protocol
works across the actual split-host topology:

```text
local file host -> coord-ssh -> deployed Coordinate DB/service
                -> deployed harness copy -> record/consume
```

Unit tests cover actor/workspace/task binding, expiry, fingerprints, ordering, replay,
and callback loss. They cannot prove the deployed CLI, service version, SSH wrapper,
permissions, or real file/control-plane split. Conversely, a generic server health
check cannot prove receipt correctness. S3-C3 must therefore preserve two separate
verdicts: `control-plane PASS` and `worker-execution PASS`.

Negative receipt probes must not corrupt the canonical `discord-nexus` checklist.
They run against a uniquely named disposable sidecar smoke workspace and task set.
The sidecar is evidence-bearing test state, not a new project source of truth.

## Goal

Deploy the exact reviewed Coordinate and MultiNexus revisions through the existing
manual deployment path, then prove the completion receipt over the real local/cloud
boundary using an isolated sidecar workspace. Exercise happy path, replay, expiry,
fingerprint drift, and interrupted recovery without mutating canonical project tasks.
Produce redacted evidence sufficient for independent result review and rollback.

## Non-goals

- No Slice 4, P9-0A, CLI extraction, policy extraction, schema redesign, or generic
  host-aware framework work.
- No direct edits to the canonical `discord-nexus` checklist for negative testing.
- No real Discord/KOOK message delivery and no worker task executed through chat.
- No use of `--allow-dirty`, no deletion of `.qoder/`, no force-push, no history
  rewrite, and no merge.
- No secret/token/private-key output in artifacts, JSONL summaries, or review reports.
- No automatic deletion of remote smoke DB rows or files; cleanup is a separately
  reviewed destructive action. The fixture remains namespaced and auditable.
- No Slice 3 durable closeout or `task.done` for the S3-C3 package itself; that belongs
  to S3-C4 after independent result approval.

## Invariants and authority boundaries

- Git owns source and release identities; only exact reviewed SHAs may be pushed and
  deployed.
- `/opt/*` is a deployment copy. `VERSION_DEPLOYED` plus Git SHA and content checks
  establish deployed code identity.
- `/var/lib/coordinate/coord.sqlite3` is the production Coordinate runtime authority;
  it must be backed up before mutation and never copied into reports.
- The canonical MultiNexus harness remains untouched by negative probes. The sidecar
  workspace owns only its disposable smoke tasks and files.
- A receipt is authorized by the cloud control plane, claimed/applied by the local
  file-side command through `coord-ssh`, and consumed only after the matching sidecar
  harness state is present on the server.
- `task.done` and `completion.consumed` must remain atomic and idempotent.
- Control-plane health does not imply an executor worked; executor/session evidence
  does not imply protocol correctness. JSONL, process state, artifacts, commands, and
  reviewer checks remain separate evidence layers.
- The execution worker may run the approved commands only after the human remote gate.
  It may stop on failure but may not improvise repair, rollback, cleanup, or scope.

## Proposed execution

### 1. Gate-time refresh and release materialization

After explicit authorization but before any remote mutation:

1. Re-read this exact approved revision and review artifact.
2. Require Coordinate `main == e0cc1561...` and MultiNexus `main == 82c5613...`, or
   invalidate the plan if they drift.
3. Run focused/full local tests and both harness validate/doctor commands; record raw
   exit status and warnings without rewriting historical warnings.
4. Create a clean detached Coordinate release worktree from the exact SHA. Confirm no
   tracked or untracked changes in that worktree. Preserve the development checkout
   and `.qoder/` untouched.
5. Verify upstream ancestry. Push only the exact approved local `main` commits with a
   normal fast-forward if the gate explicitly includes push; reject non-fast-forward,
   remote drift, hooks that change content, or a different destination.

### 2. Read-only remote preflight

Before upload/restart, capture redacted evidence for:

- SSH identity/host fingerprint continuity without printing private-key paths;
- disk space and ownership for `/opt/coordinate`, `/opt/multinexus`, and
  `/var/lib/coordinate`;
- current `VERSION_DEPLOYED` files and service active state;
- current `/usr/local/bin/coord-local --version` and receipt CLI help;
- production DB integrity check and a timestamped root-readable backup with mode 0600;
- current `discord-nexus` state/audit and runtime-agent listing;
- current sidecar workspace prefix collision check.

Any failed service, DB integrity error, insufficient disk, missing backup, unexpected
host, missing receipt CLI, workspace collision, or topology drift stops before deploy.

### 3. Exact deployment

Deploy with the existing script, using the clean Coordinate release worktree and the
approved clean MultiNexus checkout. Normal execution must install dependencies,
restart both services, and run `server-smoke.sh`; it must not pass `--allow-dirty`,
`--skip-install`, `--no-restart`, or `--no-smoke`.

After restart, require:

- both systemd units active;
- both `VERSION_DEPLOYED` commits equal the approved SHAs;
- deployed Coordinate receipt command surfaces exist;
- JSON workspace listing succeeds;
- proxy/gateway and runtime-agent checks succeed;
- bounded journal scan contains no deployment-breaker traceback or import/CLI error.

This establishes `control-plane PASS` only.

### 4. Isolated sidecar fixture provisioning and synchronization contract

Create a unique identifier such as
`s3c3-smoke-<UTC timestamp>-<short approved SHA>` after confirming no collision.
Use a local temporary directory outside both repositories and a matching server
directory under a dedicated smoke root. The pair is one isolated workspace whose
coding-host copy is local and deployed copy is remote; neither path is
`discord-nexus`.

Provisioning is explicit and is not delegated to `deploy-server.sh`:

1. Create the empty, collision-free server sidecar directory, register exactly one
   cloud workspace whose `workspace_path`, `harness_root`, and eventual
   `harnessctl_path` all point inside it, then run deployed
   `workspace init-harness --mode full --source /opt/multinexus/scripts/harness`.
   This public initializer must physically copy the approved harness scripts to
   `<server-sidecar>/scripts/harness/`; invoking scripts in `/opt/multinexus` to
   operate another root is forbidden because `project_root()` is derived from the
   script location. Verify the copied script hashes equal the approved release.
2. Create four immutable, namespaced Markdown plan stubs from the fixed smoke-plan
   template carried in the approved execution bootstrap, then use deployed
   `task create` to create the four tasks and matching DB events. Markdown fixture
   creation is allowed; direct `mvp-checklist.json`, `events.jsonl`, or SQLite writes
   are forbidden.
3. Through deployed `coord-local`, bring every task through the public lifecycle in
   this order: `assign`, `accept`, `closeout`, then `review-result approved`.
   `closeout` must precede approval so the stored review phase is
   `closeout_requested`; no `--force` or repair path is allowed.
4. Copy the complete server sidecar to the new empty local sidecar, without
   `--delete`, so the local path also physically contains `scripts/harness/`.
   Verify each local/server script hash and lifecycle fingerprint is identical. This
   is the only baseline from which receipts may be prepared.

The synchronization direction is thereafter fixed:

- server -> local is allowed only before receipt preparation to establish the
  reviewed baseline;
- local -> server after `mark-done-files` copies only the namespaced sidecar
  `docs/project-harness/mvp-checklist.json`, not a repository, DB, canonical
  workspace, or unrelated smoke root;
- every transfer records source/destination, file SHA-256 before and after, and the
  task lifecycle fingerprint;
- no synchronization uses `--delete`, and no sidecar is removed in S3-C3. The result
  artifact records a retained-fixture manifest and a separately reviewable cleanup
  command, but does not run it.

Create separate tasks for:

- `happy-replay`
- `expiry`
- `fingerprint-drift`
- `interrupted-recovery`

All workspace/task IDs, paths, events, and receipt IDs must carry the unique prefix.
If fixture setup requires direct JSON/SQLite edits, stop: the plan does not authorize
them.

### 5. Receipt matrix

Before every prepare, compute the server fingerprint through deployed code and the
local fingerprint from the local sidecar, require equality, and record both. Receipt
preparation immediately follows that comparison with no intervening fixture mutation.

1. **Happy path:** prepare a receipt on the cloud control plane; run local
   `mark-done-files` with the real `coord-ssh` wrapper; transfer only the namespaced
   sidecar checklist to the matching server sidecar and verify its SHA-256; run
   `mark-done-record`; verify ordered
   `authorized -> claimed -> applied -> task.done + consumed` and matching
   fingerprints.
2. **Replay:** repeat file and record commands with the same receipt. Require no second
   canonical mutation, no duplicate terminal event, and an idempotent success/result.
3. **Expiry:** issue a receipt with `--ttl-seconds 2`, record the local checklist hash,
   wait at most ten seconds while polling only the read-only preflight until it reports
   expiry, then run files once. Require rejection before any local file mutation, an
   unchanged checklist hash, and no claimed/applied/done event. A provider wait is not
   used for timing this case.
4. **Fingerprint drift:** issue a receipt, then use the copied local public
   `workflow_transition.py review-result ... changes_requested` command to change the
   local task from `review_approved` to `changes_requested`; do not synchronize that
   change to the server. Record the deliberately drifted checklist hash and lifecycle
   fingerprint, then attempt local `mark-done-files`. Require
   `before_fingerprint_mismatch`, no done state, and no repair path.
5. **Interrupted recovery:** execute exactly this sequence: prepare; local
   `mark-done-files` through real `coord-ssh` until claim/apply succeeds; intentionally
   leave the server sidecar unchanged; run `mark-done-record` once and require a
   deployed-state/fingerprint rejection; transfer only the namespaced sidecar
   checklist and verify its SHA-256; retry `mark-done-record`. Require one terminal
   event and one consumed receipt.

Use fresh receipt/task identities between negative cases. Never reuse a rejected or
expired receipt to repair a fixture. A later fresh receipt may close residual fixture
tasks only if that cleanup is added to the reviewed execution log and does not erase
negative evidence.

### 6. Independent result review

The execution worker returns redacted command/result evidence, deployed SHAs, backup
handle, fixture IDs, event IDs, receipt state transitions, fingerprint comparisons,
service status, test results, and a provider JSONL/session handle. Codex independently
queries the deployed versions and bounded event/task rows, checks for canonical
`discord-nexus` drift, reviews logs/artifacts, and records separate verdicts for:

- local regression;
- deployment/control plane;
- each receipt case;
- worker execution/liveness; and
- rollback readiness.

S3-C3 is not accepted if any required case is unproven, even when services are healthy.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Local or upstream SHA/plan/deploy-script drift | Stop before remote access; revise and re-review. |
| Dirty release worktree or need for `--allow-dirty` | Stop; recreate a clean worktree. Do not delete unrelated files. |
| SSH identity, disk, DB integrity, backup, or service preflight fails | Stop before upload/restart and preserve evidence. |
| Coordinate deploy succeeds but service smoke fails | Stop new fixture work; collect bounded logs and use only the approved rollback procedure. |
| MultiNexus deploy fails after Coordinate succeeds | Stop fixture work; assess component versions explicitly; do not claim control-plane PASS. |
| Provider/worker fails before mutation | Preserve clean state and retry with another approved executor after evidence review. |
| Provider fails after remote mutation | Inspect JSONL/process, deployed versions, DB events, and fixture files before any retry. |
| Receipt rejected before file write | Preserve fixture and event evidence; no repair flag or manual edit. |
| Files changed but apply acknowledgement is absent | Treat as interrupted; inspect receipt and fingerprints before idempotent retry. |
| Apply succeeds but server sidecar is stale | Record must fail closed; sync only the namespaced fixture and retry. |
| Duplicate terminal event or mismatched task/workspace/actor accepted | S3-C3 fails; stop and roll back Coordinate deployment. |
| Canonical `discord-nexus` task/harness drift appears | Stop all smoke work, preserve evidence, and escalate before repair. |

## Acceptance matrix

| Case | Expected result | Evidence |
|---|---|---|
| Release identity | Exact approved SHAs, fast-forward-only push if authorized | Git/upstream and `VERSION_DEPLOYED` |
| Control-plane smoke | Services, CLI, JSON, proxy, agents, journals healthy | `server-smoke.sh` plus bounded probes |
| Isolation | Only unique sidecar workspace/tasks change | Pre/post canonical audit and namespaced rows/files |
| Happy path | Ordered receipt lifecycle and one atomic terminal pair | Event IDs, task state, fingerprints |
| Replay | Idempotent success, no duplicate terminal event | Repeated command output and event count |
| Expiry | Two-second receipt rejected before mutation | Receipt/event state plus unchanged file hash |
| Fingerprint drift | `before_fingerprint_mismatch`, task remains nonterminal | Before/after fingerprint and events |
| Interrupted recovery | Stale record fails, synchronized retry succeeds once | First/second record outputs and terminal count |
| Worker execution | Session advances and exits with expected artifact | Redacted JSONL/process/result handle |
| Rollback readiness | Backup and previous deployed identities are known | Backup metadata and version evidence |

## Validation

- Coordinate focused: `tests.test_completion tests.test_transitions tests.test_cli`
- Coordinate full: `python3 -m unittest discover -s tests -p 'test_*.py'`
- Coordinate checklist validation: `scripts/harness/validate_checklist.py docs/mvp-checklist.json`
- MultiNexus full suite using its repository virtual environment
- MultiNexus: `bash scripts/harness/harnessctl validate` and `doctor`
- Remote: deploy script smoke plus the receipt matrix above
- Post-smoke: production DB integrity, service state, bounded journal scan, exact
  deployed versions, and canonical `discord-nexus` drift audit

Local tests are required before deployment. Remote preflight is required before upload.
All receipt cases and independent review are required before S3-C3 acceptance.

## Rollout and rollback

- Landing order: approved plan -> explicit push/deploy/runtime gate -> exact push if
  included -> read-only preflight/backup -> Coordinate + MultiNexus deploy -> generic
  smoke -> isolated receipt smoke -> independent review -> S3-C4.
- The plan introduces no schema migration. The deployed Coordinate code reads/writes
  receipt events in the existing event store.
- Before deployment, record previous `VERSION_DEPLOYED` SHAs and verify they are
  available for clean release worktrees.
- Rollback means redeploying those exact prior component SHAs through the same script,
  then rerunning server smoke. Never reset shared Git history or restore the entire DB
  merely to remove namespaced smoke evidence.
- A DB restore is permitted only for demonstrated database corruption and requires a
  separate explicit destructive authorization; normal receipt/test failure uses code
  rollback while preserving the audit ledger.

## Worker boundaries

- Allowed local paths: Operator-created clean release worktrees and a unique temporary
  sidecar fixture directory; no edits in the Coordinate development checkout.
- Allowed remote paths after gate: existing deployment paths plus one unique dedicated
  sidecar smoke root and timestamped DB backup.
- Allowed actions after gate: exact fast-forward push, preflight, deploy/restart/smoke,
  namespaced fixture operations, bounded evidence reads, and approved rollback.
- Forbidden: force push, merge/rebase/amend, `--allow-dirty`, secret reads/output,
  canonical checklist negative probes, direct JSON/SQLite edits, real chat delivery,
  unreviewed repair, fixture deletion, package mark-done, or self-approval.
- Report progress by phase with timestamp, command class, exit status, IDs, redacted
  summary, and latest JSONL event. Never report private reasoning or secret arguments.

## Plan review record

- Review artifact:
  `docs/project-harness/tasks/slice-3-c3-deployment-smoke/plan-review-round-1.md`
- Reviewer: OpenCode CLI, `zhipuai-coding-plan/glm-5.2`, session
  `ses_0ab323f77ffeqCG1qF1AekYdVS`
- Verdict: `changes_requested`
- Reviewed plan revision: `9ed248670686be65`
- Must-fix findings: sidecar script placement/provisioning, lifecycle order,
  prepare-time fingerprint alignment, valid local drift, and exact interrupted
  recovery synchronization
- Resolution revision: this material revision; pending a new `plan.ready` hash and
  independent round-2 approval

Any material edit after approval creates a new `plan.ready`, invalidates old approval
and bootstrap evidence, and requires another independent review.

## Bootstrap gate

Before approval, generate only a `review-type=plan` reviewer bootstrap. After plan
approval, do not generate an execution bootstrap until the user grants the single
push/deploy/SSH/runtime gate for the exact approved revisions and side-effect scope.
