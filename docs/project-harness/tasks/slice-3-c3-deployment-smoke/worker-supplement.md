# S3-C3 Execution Worker Supplement

This supplement is authoritative when the generated bootstrap is generic or stale.

## Authorization now in force

The user explicitly authorized normal fast-forward push, SSH, production preflight and
DB backup, exact deployment, dependency installation, service restart, production DB
reads/writes required by the isolated smoke, and creation/retention of the namespaced
sidecar. Do not stop merely because `worker-bootstrap.md` repeats the earlier gate.

The authorization is bounded by restored byte-identical approved plan hash
`871664176c514bec`, fresh `plan.ready` event
`ccdd2948-5f3d-4b16-b089-c4de7caac054`, and fresh `plan.approved` event
`fb247f22-417f-47ad-babb-87589ee5ed66`. No force push, direct JSON/SQLite edit, DB restore, repair
flag, canonical `discord-nexus` negative probe, evidence deletion, or destructive
cleanup is authorized.

Attempt 1 is recorded in `execution-report.md`. The old code/version was restored.
A user-supplied Mihomo config then passed server validation; Discord and PyPI proxy
probes passed, and Coordinate/bridge stayed active with zero restarts across two
observation windows. Attempt 2 must use the original normal full-install path: do not
pass `--skip-install`, `--no-smoke`, `--no-restart`, or `--allow-dirty`.

## Worker identity and role

- Runtime: non-Codex Oh-My-Pi worker.
- Worker executes the runbook and writes evidence; it does not approve results or mark
  the package done.
- Codex is Operator and result reviewer.
- Do not send real Discord/KOOK messages for this package.

## Required start

1. Read `plan.md`, `plan-review-round-2.md`, and `remote-runtime-gate.md`.
2. Confirm plan SHA-256 is
   `871664176c514bec7b9c32c8045d5368ff382e35d44ccff4eefc2b3d54e64ecb`.
3. Confirm Coordinate HEAD `e0cc1561cd20b0f22389234aefe92d01273860e4` and
   MultiNexus HEAD `82c5613f9d8fcb25c5ca936a24c61536e567df50`.
4. Treat the dirty MultiNexus harness plan/checklist artifacts and Coordinate `.qoder/`
   as Operator-owned state. Do not modify, clean, stage, or commit them.
5. Create separate clean detached release worktrees for both approved SHAs and pass
   both explicitly to `deploy-server.sh`. Do not deploy either development checkout.

## Evidence and stop behavior

- Write attempt-2 evidence to
  `docs/project-harness/tasks/slice-3-c3-deployment-smoke/execution-report-attempt-2.md`;
  do not overwrite attempt-1 evidence.
- Include exact commands by class, exit status, timestamps, previous/new deployed
  SHAs, backup handle and mode, sidecar paths/IDs, receipt IDs/events/fingerprints,
  service results, canonical drift audit, and JSONL session handle.
- Add a `Dogfood evidence` section that classifies every major step as full dogfood,
  semi-dogfood, or direct operational fallback. For each fallback, record why the
  normal Coordinate/Discord/harness route was not used, what product gap it exposes,
  and the recommended backlog/package destination. Do not claim full dogfood merely
  because Coordinate commands were used for part of the path.
- Correlate dogfood evidence across the provider JSONL, Coordinate events, deployed
  service state, sidecar harness artifacts, and independent verification. A visible
  message is not proof of execution, and worker activity is not proof of correctness.
- Do not include secrets, tokens, private-key paths, raw DB content, or private
  reasoning.
- On the first fail-closed condition, stop further mutation, collect bounded evidence,
  report the blocker, and do not improvise repair or rollback. Code rollback is allowed
  only when the approved failure matrix explicitly calls for it.
- Do not request package closeout and do not run package `mark-done`; Codex performs
  independent result review first.
