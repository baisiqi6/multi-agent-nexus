# Result Review Round 2: slice-3-c3-deployment-smoke

## Verdict

- Decision: `approve`
- Reviewer: `codex-operator`
- Review date: 2026-07-12
- Corrected evidence commit: `4b87855`
- Approved runtime: Coordinate `e0cc1561cd20b0f22389234aefe92d01273860e4`
  and MultiNexus `82c5613f9d8fcb25c5ca936a24c61536e567df50`
- Approved plan SHA-256:
  `871664176c514bec7b9c32c8045d5368ff382e35d44ccff4eefc2b3d54e64ecb`

Both round-1 must-fix findings are resolved. The report now cites the fresh final
attempt-2 authorization pair (`ccdd2948-...` / `fb247f22-...`) and labels the older
pair as historical gate evidence. It also records the stale interrupted-recovery task
projection as an unresolved reconciliation risk instead of predicting that a daemon
pump will repair it.

## Independent acceptance evidence

- Exact approved SHAs are deployed in both `VERSION_DEPLOYED` files.
- Coordinate and MultiNexus services remained active with `NRestarts=0` across two
  observations.
- Discord and PyPI proxy probes returned HTTP 200; production DB integrity returned
  `ok`; independent `server-smoke.sh --host kook-hermes-admin --since '5 min ago'`
  returned `server smoke OK`.
- Canonical `discord-nexus` stayed at 29 tasks and 851 events. All fixture activity is
  isolated to the retained sidecar, which has 6 namespaced tasks and 89 events.
- Happy, replay, expiry, fingerprint-drift, and interrupted-recovery receipt cases meet
  the exact plan criteria. Event counts confirm one terminal pair where required and no
  forbidden terminal mutation in negative cases.
- Provider JSONL proves the non-Codex worker advanced through the runbook, produced the
  execution report, exited normally, and later applied only the two requested report
  corrections. Runtime correctness was established independently rather than inferred
  from worker activity.

## Accepted residual risks and routing

- The interrupted-recovery `tasks` projection remains stale despite a correct terminal
  event pair. Route this to reconciliation/projection hardening; do not silently repair
  or erase the retained fixture before S3-C4 records the evidence.
- Two failed fingerprint-drift fixture attempts consumed receipts because the harness
  CLI contract was unclear. Their preserved evidence is accepted and already routed to
  the Phase 9 0A CLI-boundary backlog.
- The first deployment attempt exposed non-atomic source sync and proxy-health gaps;
  the successful second attempt does not erase those dogfood findings.

S3-C3 result review is approved. This approval does not itself delete the sidecar or
perform package `mark-done`; durable package closeout and Slice 3 roll-up belong to the
separate S3-C4 package.
