# S3-C3 Plan Reviewer Supplement

The generated reviewer bootstrap contains a known generic OpenSpec-path fallback and
does not carry the canonical acceptance matrix. For this review, this supplement is
authoritative over those generic fields.

## Exact review target

- Plan: `docs/project-harness/tasks/slice-3-c3-deployment-smoke/plan.md`
- Coordinate `plan.ready` event: `0ec4187e-4099-4a42-98e6-5cd0546a02c8`
- Short content hash: `9ed248670686be65`
- Full SHA-256:
  `9ed248670686be65d7f70def40669e0b2299dd3b2ffe7374bb76f628e39df59f`

Do not look for `openspec/changes/...`; it is not the source plan. Review the exact
file above together with `scope.md`, `architecture.md`, `domain-model.md`, the Slice 3
overview, deployment runbook, and the current Coordinate receipt CLI/code/tests.

## Review boundary

- Read-only. Do not edit files, create worktrees, commit, push, use SSH/`coord-ssh`,
  deploy, restart services, access the production DB, or send real messages.
- You may use read-only local shell commands to verify Git identities, command help,
  scripts, tests, and plan consistency.
- Judge whether the sidecar workspace genuinely proves the local/cloud receipt split
  without contaminating canonical project state.
- Check exactness of the push/deploy gate, clean-release-worktree design, backup and
  rollback rules, happy/replay/expiry/fingerprint-drift/interrupted-recovery cases,
  and separate control-plane versus worker-execution verdicts.
- Reject if fixture setup cannot be performed through existing public coordinator and
  harness operations without direct JSON/SQLite edits, or if any required transition,
  synchronization, fingerprint, cleanup, or rollback step is underspecified.
- Reject any hidden reliance on `--allow-dirty`, repair flags, canonical
  `discord-nexus` negative probes, secret disclosure, worker self-approval, or an
  unreviewed destructive cleanup.

Return a concise evidence-backed review followed by exactly one `[agent-report]`
block with `decision=approve` or `decision=reject`, workspace
`discord-nexus`, and task `slice-3-c3-deployment-smoke`.
