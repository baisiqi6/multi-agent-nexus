# S3-C3 Execution Report: Attempt 1

## Verdict

- Overall: `BLOCKED_FAIL_CLOSED`
- Local regression: PASS
- Fast-forward push: PASS
- Remote preflight and DB backup: PASS with CLI/schema dogfood findings
- Exact deployment: FAIL during Coordinate dependency installation
- Rollback: old Coordinate code/version restored; DB integrity PASS
- Control-plane PASS: NO
- Worker-execution PASS: PARTIAL (worker active and bounded, then interrupted by Operator)
- Receipt matrix: NOT STARTED

No sidecar workspace/task was created and no receipt event was issued.

## Identities

- Approved plan hash: `871664176c514bec`
- Coordinate target/pushed SHA: `e0cc1561cd20b0f22389234aefe92d01273860e4`
- MultiNexus target/pushed SHA: `82c5613f9d8fcb25c5ca936a24c61536e567df50`
- Previous Coordinate deployed SHA: `b93ab46b88f0628de2ede03dc58a8a02a4bbefe1`
- Previous MultiNexus deployed SHA: `24022a408d45ec8ff4501172af3f942e092067f9`
- OMP JSONL:
  `/Users/yinxin/.omp/agent/sessions/-projects-multinexus/2026-07-12T05-48-56-868Z_019f54df-20a4-7000-abb4-d8e3a2490a59.jsonl`
- OMP session: `019f54df-20a4-7000-abb4-d8e3a2490a59`

## Completed evidence

- Coordinate focused: 342 passed.
- Coordinate full: 1,347 passed.
- Coordinate checklist: 0 warnings.
- MultiNexus: 350 passed, 2 skipped, 6 subtests passed.
- MultiNexus checklist: validation PASS with six recorded warnings.
- Both detached release worktrees were clean at the exact approved SHAs.
- Both upstreams were behind only and accepted normal fast-forward pushes.
- Production DB preflight integrity: `ok`.
- Backup: `/var/lib/coordinate/coord-backup-20260712T055517Z.db`, owner
  `coord:coord`, mode 0600, integrity `ok`, SHA-256
  `72e490d6e95570b505a6dc3d835257443fefa16430393a1ef8a771e8fba96467`.
- Preflight collision count for `s3c3-smoke-*`: zero.

## Failure and rollback

The deployment script synchronized new Coordinate source to `/opt/coordinate`, then
failed before install completion, version write, or restart. Its hard-coded local
proxy `127.0.0.1:7890` accepted CONNECT but every upstream TLS handshake failed. Pip
could not obtain the isolated build dependency `setuptools>=68` and exited nonzero.
MultiNexus deployment never started.

The Operator interrupted further worker diagnosis because proxy repair was outside the
approved smoke runbook. A clean worktree at the previous Coordinate SHA was deployed
with `--skip-install` solely as rollback; dependency manifests were unchanged and the
existing venv was the previous runtime. Verification after rollback:

- `/opt/coordinate/VERSION_DEPLOYED` is `b93ab46b...`;
- `/opt/multinexus/VERSION_DEPLOYED` remains `24022a40...`;
- new-only `completion.py` is absent from `/opt/coordinate`;
- production DB integrity remains `ok`.

The rollback restart exposed an external availability blocker: Mihomo reports active
and listens on 7890/9090, but its automatic group reports zero alive upstream nodes.
Coordinate cannot establish a new Discord connection and is in systemd activation /
restart cycling. Restarting Mihomo once did not recover an upstream. No further proxy
mutation, alternate tunnel, subscription edit, deploy retry, or sidecar work occurred.

## Dogfood evidence

### Semi-dogfood paths

- Plan approval, worker bootstrap, event identity, and task artifacts used Coordinate
  and the canonical harness.
- The actual non-Codex worker ran from the generated task bootstrap and was supervised
  using provider-native JSONL plus process, Git, remote, and artifact evidence.
- Push, deployment, backup, and rollback used the real production scripts and host.

### Direct operational fallbacks

- The worker was invoked directly through local OMP rather than targeted Discord
  handoff because this workspace still lacks a usable host execution profile for the
  local non-Codex agent. This remains semi-dogfood, not full dogfood.
- Remote preflight used direct SSH and SQLite read-only queries. The first documented
  query assumptions were wrong (`workspace list --workspace-id`, `task_mirrors`, and
  old column names), requiring live schema discovery. This exposes stale runbook/query
  contracts.
- The deploy script synchronizes source before dependency installation succeeds, so a
  network failure leaves disk code newer than `VERSION_DEPLOYED` and the running
  process. This is a non-transactional deployment gap.
- The deploy script hard-codes a single proxy and has no pre-sync dependency/network
  gate or offline/no-build-isolation install strategy. External proxy failure therefore
  blocks deploy and can also prevent a restarted Discord daemon from recovering.

### Required backlog routing

1. MultiNexus deployment hardening: preflight proxy/package availability before source
   sync; stage/install/verify first; atomically switch code/version; preserve an
   explicit rollback snapshot.
2. Deployment dependency strategy: support a reviewed wheel/cache or safe reuse path
   when manifests are unchanged, without normalizing `--skip-install` for new deploys.
3. Operator smoke/runbook: derive read-only queries from current CLI/schema and treat
   old deployed command absence as expected upgrade evidence, not an ambiguous gate.
4. Full dogfood: add a valid host execution profile so a non-Codex worker can be
   targeted through Coordinate/Discord rather than launched directly.

## Resume condition

Do not retry S3-C3 deployment until the server has at least one healthy Mihomo upstream,
Discord and PyPI proxy probes pass, and the old Coordinate service remains active
without increasing restart count across two observation intervals. Then re-run the
approved preflight/backup identity checks and start a fresh execution attempt.
