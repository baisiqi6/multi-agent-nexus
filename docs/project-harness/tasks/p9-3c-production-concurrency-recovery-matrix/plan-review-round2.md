# P9-3C Independent Plan Review — Round 2

Reviewer route: Claude Code Sonnet -> `kimi-for-coding`  
Session: `p9-3c-plan-review-kimi-round2`  
Date: 2026-07-14  
Verdict: **approve with a planning-only authorization boundary**

- Plan SHA-256:
  `6321e77be6cfd50c82d9c7f995691fb523196c1b3ce238c501eadb4c385f6652`.
- Measurement SHA-256:
  `177f0225fa2c0ecbe398231dbc33e9055a20ca97a91c5d2e30dac5a942a7bc96`.
- Provider-native stream result: success; actual assistant model
  `kimi-for-coding`; five turns; three repository reads and no mutation.

## Round-1 disposition

- **P0 whole-DB restore:** closed. Section 9 orders exact process cleanup,
  supported API cleanup, code/service rollback, and forensic stop/copy before a
  last-resort restore. Restore requires a fresh backup, human incident gate, proof
  of no intervening writes, and a documented recovery decision.
- **P1 impossible Row B:** closed. E1/W1 plus E2/W2 first proves concurrency; J2
  then releases E2 capacity while E1/W1 remains active; only then does E2/W1 prove
  cross-executor `resource_blocked`.
- **P1 fixture/scope contradiction:** closed. P9-3C0 owns local/sidecar fixture
  assessment and any separately reviewed implementation; P9-3C1 production remains
  blocked until the exact fixture contract closes.
- **P1 manual renewal false pass:** closed. Row C forbids manual renew and requires
  at least two automatic lease timestamp advances with no progress/output.
- **P1 restart/crash conflation:** closed. G0 is zero-active restart/integrity; G1 is
  separately gated by a measured downtime/transport/TTL contract and does not use
  `NRestarts` as proof of manual restart.
- **P1 recovery target ambiguity:** closed. D/E/F is one chained Jc scenario with
  queue freeze and returned-job-id equality before N+1 proceeds.
- **P1 invented evidence/reaper:** closed. `capacity show` is policy-only; usage and
  resources use bounded read-only lease queries; global reap is explicit and never
  represented as test-id scoped.
- **P1 inconsistent ledger/acceptance:** closed. The budget is eight jobs, G0 creates
  none, job/lease ids are treated as Coordinate-generated, and A-G core semantics are
  mandatory while Windows/Pad variants remain optional.

Remaining must-fix findings: none.  
Remaining should-fix findings: none.

## Authorization boundary

This approval authorizes only the exact revision above as the P9-3C0 measurement and
detailed-planning entry. It does **not** authorize:

- P9-3C0 code/helper implementation;
- checklist registration as a coding-ready production task;
- a production/coding worker bootstrap;
- any paid provider call, job/lease mutation, capacity sync, service restart, deploy,
  or P9-3C1 production matrix row.

P9-3C0 must first identify or plan the exact fixture contract. If implementation is
required, it receives its own detailed implementation plan, independent exact-revision
review, and worker bootstrap. After the fixture closes, `measurement.md` and `plan.md`
must be revised with real fixture identities and independently reviewed again before
P9-3C1 authorization.

## Reviewer-route note

The preferred exact `zhipu-coding-plan/glm-5.2` reviewer route was attempted first but
produced no file read or verdict inside the bounded observation window, so it was
stopped and is not counted as approval. The independent Kimi reviewer completed the
bounded Round-2 disposition above.
