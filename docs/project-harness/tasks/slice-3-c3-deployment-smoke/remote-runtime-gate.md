# S3-C3 Remote and Runtime Authorization Gate

## Approved plan identity

- Task: `slice-3-c3-deployment-smoke`
- Plan hash: `871664176c514bec`
- `plan.ready`: `dc9d6e33-9223-44f0-962f-4252c458cc3e`
- `plan.approved`: `44a11ddc-ae45-46a5-8a1e-2b8d6f895ec8`
- Review artifact:
  `docs/project-harness/tasks/slice-3-c3-deployment-smoke/plan-review-round-2.md`
- Coordinate release SHA: `e0cc1561cd20b0f22389234aefe92d01273860e4`
- MultiNexus release SHA: `82c5613f9d8fcb25c5ca936a24c61536e567df50`

Any plan, SHA, upstream, deploy-script, server-topology, or command-surface drift
invalidates this gate and returns the package to planning/review.

## Authorization requested as one bounded gate

Authorization permits the Operator to dispatch a non-Codex worker and supervise it
for these actions only:

1. normal fast-forward pushes of the two exact approved `main` histories, if still
   ahead of their configured upstreams;
2. SSH through the configured alias/wrapper for read-only preflight;
3. a mode-0600 timestamped backup of the production Coordinate SQLite DB;
4. deployment of the two exact SHAs using the reviewed deployment script, including
   dependency installation, service restarts, and generic server smoke;
5. creation and mutation of one uniquely prefixed S3-C3 sidecar workspace and its four
   smoke tasks in the production Coordinate DB and dedicated smoke root;
6. execution of the approved happy/replay/expiry/fingerprint-drift/interrupted-recovery
   receipt matrix through the real `coord-ssh` boundary;
7. bounded, redacted evidence reads from versions, service status, journals, sidecar
   files, and namespaced DB events; and
8. code rollback to the recorded previous deployed SHAs only if an approved failure
   condition requires it.

## Not authorized by this gate

- force push, merge, rebase, amend, history rewrite, or branch deletion;
- `--allow-dirty`, deletion or modification of Coordinate `.qoder/`;
- direct edits to JSON, JSONL, SQLite rows, canonical `discord-nexus` tasks, or the
  canonical MultiNexus harness for negative probes;
- real Discord/KOOK delivery or unrelated worker execution;
- secret/private-key output;
- deletion of sidecar evidence or DB rows;
- DB restore, data repair flags, destructive cleanup, or production migration; or
- S3-C3/Slice 3 mark-done and S3-C4 closeout.

## Fail-closed rule

The worker must stop before the next mutation when any approved identity, preflight,
backup, service, command surface, fingerprint, isolation, or acceptance check fails.
It may collect bounded evidence but may not improvise repair. Codex remains the result
reviewer and records control-plane PASS separately from worker-execution PASS.
