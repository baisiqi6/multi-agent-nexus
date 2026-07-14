# P9-3B Coding Worker Bootstrap

Role: Coding worker  
Harness: Claude Code  
Requested model mode: `sonnet` (the configured Kimi backend; do not select `opus`)  
Task: `p9-3b-runtime-lease-wiring`

## Authority

- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-3b-runtime-lease-wiring/plan.md`
- Exact approved plan SHA-256:
  `5c04d3bd8d297da1565d67a4aa41b679559481a3bed75ede287dd941f75b1378`
- Independent review:
  `plan-review-round1.md` and `plan-review-round2.md`
- Coordinate start:
  `af8461efdf6beb7c47560fe3d17b30f2ac6696ba`
- MultiNexus start: the canonical commit containing this bootstrap; verify it equals
  the supplied worktree HEAD before editing.
- Production task-create event:
  `b9fd30af-4942-4e63-b8d8-5f35fb60e2e8`
- Split operation:
  `039bdcda-de94-4bbd-9f26-13f39b2d33bf` (`record_applied`)

## Isolated worktrees

- Coordinate:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-3b-claude`
- MultiNexus:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3b-claude`

Do not edit the main checkouts. Do not change or delete the unrelated
`/Users/yinxin/projects/coordinate/.qoder/` directory.

## Hard boundaries

- Implement only the approved P9-3B digest. Do not implement P9-4 provider JSONL/
  process observation or the P9-3C production concurrency/crash matrix.
- No direct Coordinate DB writes from MultiNexus.
- No direct edit of `mvp-checklist.json`, lifecycle JSON, or SQLite.
- No push, PR, merge, production deploy, SSH, service restart, production DB access,
  assignment transition, review approval, receipt, or mark-done action.
- Do not claim completion merely because focused tests pass. Report exact tests,
  remaining failures, commits, and residual risks to Codex for independent review.
- Preserve the exact historical Coordinate full-suite baseline unless a changed
  contract test is intentionally updated by this package.

## Required implementation

Read the complete approved plan and both reviews before editing. Implement all plan
sections, including these review-critical requirements:

1. Reap is the only expiry authority. Remove reserve's lease-only inline expiry.
   Claim runs bounded global reap before selection; the production timer path uses the
   same authority. Lease expiry and exact running-job timeout/recoverable CAS are one
   transaction.
2. Atomic claim means execution-context backfill, job CAS, lease reserve,
   `job.claimed`, and final response are all-or-nothing under one `BEGIN IMMEDIATE`.
3. Managed-attempt detection is `EXISTS` any lease row for
   `(job_id, attempt_token)`. It gates normal report, progress, and
   `_accept_late_result`; a managed attempt never falls back to attempt-token-only.
4. Remove/transaction-gate the current commits in `claim_job`,
   `_apply_terminal_job_update`, `record_job_progress`, and `_accept_late_result`.
   Nested events/deliveries use `commit=False`.
5. Produce a strict versioned lease envelope including Coordinate `server_now`,
   TTL, renewal interval, immutable resource/capacity evidence, and exact tuple.
   Coordinate owns the canonical fixture; MultiNexus verifies its mirror bytes/SHA.
6. MultiNexus validates lease identity before context. If no lease tuple is trusted,
   invoke no provider and perform no untrusted mutation. If lease is trusted but
   context/payload/binding fails, report exact managed failure and release atomically.
7. A dedicated renewal supervisor is independent of provider progress/JSONL. Use
   `server_now + expires_at` to set a monotonic deadline with the approved safety
   margin. Ordinary renewals update the lease row without event spam.
8. On lease loss, cancel, terminate, and join the owned provider subprocess/process
   group. Prove this for every configured generic adapter; worktree mutation by an
   orphan is not acceptable.
9. Managed terminal report atomically changes job state, releases the exact lease,
   appends all terminal/agent/review/release events, and creates delivery.
10. Queue order is `created_at, id`, capacity stops selection, resource-blocked jobs
    may be skipped within the fixed 256 scan bound, and bounded no-claim reasons/
    doctor visibility are exact and tested.
11. Managed recovery remains Operator-only and requires audited reason plus explicit
    prior-process-stopped confirmation. An expired N late result is rejected before
    and after N+1 reclaim.
12. Use schema v13. Add explicit 30-second SQLite `busy_timeout`; do not enable WAL.

For the independent review's non-blocking clarification: claim-path reap remains
commit-free inside claim's caller-owned transaction; timer-path reap owns its bounded
transaction(s).

## Expected code boundaries

Prefer the approved focused boundaries:

- Coordinate lease primitives remain reusable, strict, and commit-free.
- Add one focused runtime-lease orchestration/contract module; keep public runtime
  entry points in `runtime.py`.
- Extend static CLI registration only; do not introduce plugin discovery or DI.
- Add a strict MultiNexus `execution_lease` parser beside existing context/binding
  consumers and a small worker lease supervisor.
- Touch provider adapters only where real cancellation tests prove termination/join is
  required.
- Production reaper unit/timer and deploy/smoke verification belong to the existing
  explicit deployment surfaces; do not create another deployment system.

## Required tests and evidence

At minimum run and report:

- Coordinate focused runtime/lease/resource/capacity/CLI/DB tests, including real
  two-connection capacity/resource races and failure injection at all former commit
  boundaries.
- MultiNexus focused agentd/context/binding/lease-contract/adapter cancellation/
  deploy/smoke tests.
- Both full suites.
- Cross-repository raw fixture equality and canonical SHA.
- `git diff --check`, Python compilation, and shell syntax checks.

Do not weaken assertions, remove negative cases, enlarge allow-lists generically, or
mark historical failures as accepted without showing their exact names and proving
they match the pre-task baseline.

## Worker completion report

Return one concise report containing:

- Coordinate and MultiNexus commit SHAs;
- files changed grouped by repository;
- architecture/transaction summary;
- exact focused/full/static commands and outcomes;
- cross-repo fixture SHA evidence;
- known residual risks and anything not implemented;
- explicit statement that no production/operator lifecycle actions were taken.

Codex remains architect, code/result reviewer, integration owner, production operator,
and closeout authority.
