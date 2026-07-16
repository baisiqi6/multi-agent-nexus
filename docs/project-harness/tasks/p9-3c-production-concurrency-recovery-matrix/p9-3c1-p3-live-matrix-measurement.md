# P9-3C1 P3 Live Matrix — Fresh Measurement

状态：`MEASURED_DETAILED_PLAN_REQUIRED_LIVE_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

本文件只记录 source、installed runtime 与 production state 的只读事实。它不授权 deploy、fresh
`prepare`、authorization file creation/install、controller `run/cleanup`、catalog sync、fixture
agent/unit/job/lease/delivery mutation或 service restart。

## 1. Exact source and deployed authority

- MultiNexus local `main` / `origin/main`：
  `33773c16fe7a12174b55e8e1731dbb2705e9e56b`。
- MultiNexus deployed：
  `06f98f25f3ef5f51b6bc191c66fbe041c0e006a6`。
- Runtime implementation：
  `17d0bcc1d0aeb56a821b88f096379e6dcb547fc9`；`06f98f2` includes its correction docs，
  while `33773c1` adds only P2 dogfood/closeout/roadmap docs。
- Coordinate deployed：
  `a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。
- Production host/DB/CLI：`VM-0-15-ubuntu`、`/var/lib/coordinate/coord.sqlite3`、
  `/usr/local/bin/coord-local`。

P3 fresh prepare must not seal the current source/origin/deployed split，even though runtime bytes are
unchanged。After P3 plan/bootstrap review artifacts are merged，one exact `multinexus --no-restart`
zero-delta alignment deploy is required before the P3 run id exists。

## 2. P2 closed runtime authority

P2 closed at source `33773c1` with runtime installed from `06f98f2`：

- local full gate `1032 passed, 2 skipped, 81 subtests passed`；
- controller `47 passed`；
- installed source hashes、system Python and P0 lock helper exact；
- fresh inert run `p9-3c1-prod-20260716t071325z-06f98f25` passed two read-only
  `preflight/status` rounds；
- full tree bytes+metadata hash stayed
  `4dca4e1d2f3908ee4d6effdd7f5cfafcc2951dd854c0993198d74286b061c207`；
- independent live reviewer corrected its failure-run label、reproduced the exact tree hash and returned
  `APPROVE — P2 close；P3 run/cleanup unauthorized`。

P3 must use a new run id and new prepare。The P2 successful sealed root is immutable audit evidence，not
a resumable production activation root。

## 3. Fresh production baseline

Read-only probe on 2026-07-16：

- P0 mutation lock：`state=free, phase=free`；lock path absent；
- `coordinate.service`：active/running，PID/NRestarts `836234/0`；
- `multinexus-discord-bridge.service`：active/running，PID/NRestarts `1276892/0`；
- DB integrity/schema/FK：`ok / 13 / 0`；
- job history：`done=151`、`failed=20`；pending/running `0`；recoverable timed-out `0`；
- active leases `0`；due active leases `0`；
- P9-3C1 workspace/host profile/agents/jobs/executor source/capacity source均为 `0`；
- P9-3C1 loaded/transient units为 `0`。

Canonical executor/capacity/roster state remains the ordinary production projection。P2 canonical
projection SHA was
`a84c040bd7fb9bde7f970c950ce4469e3edd1c2d7e0db2182fb0636593fd00cb`；P3 fresh prepare must
recapture rather than inherit it。

## 4. Retained run roots

Production currently retains exactly：

```text
p9-3c1-prod-20260716t062904z-90d00e16  # symlink authority prepare-failed forensic root
p9-3c1-prod-20260716t064920z-c2bee4d4  # dual-clock sealed forensic root
p9-3c1-prod-20260716t071325z-06f98f25  # successful P2 inert sealed evidence
```

The earlier argv failure `p9-3c1-prod-20260716t061838z-37721127` has no root because wrapper
validation failed before controller state creation。P3 must not delete、reuse、rename、repair or cleanup
any retained root。

## 5. P3 capability already implemented

Installed controller already contains the reviewed P3-only surfaces：

- canonical external authorization validation and one-time live copy；
- P0 lock acquire/ownership/release；
- exact 18-phase forward machine；
- five-request/two-unit/zero-network budgets；
- P9-3C1 workspace/agent/executor/capacity activation；
- J1/J2 sequential capacity，J3/J4 overlap，J5 resource blocker；
- exact J3 crash、expiry、scoped reap、N+1 recovery and stale-N rejection；
- exact stdout delivery send/readback；
- fixed cleanup suffix、empty v4/v2 catalogs、offline agents、canonical compare and final DB/unit gates。

P3 is therefore an operations/authorization package，not a new coding package by default。Any code or
test change discovered during plan/live review invalidates this route and sends the task back through a
new implementation/result-review/P2-style deploy gate。

## 6. Authorization circularity measurement

The controller requires authorization field `review_artifact_sha256`，but an exact final authorization
review cannot self-reference its own output SHA。P3 must split review authority：

1. **basis live-preflight review**：approves exact committed bootstrap、fresh manifest、installed/live
   authority and proposed authorization fields except its own digest；its provider-native JSONL SHA is
   inserted as `review_artifact_sha256`；
2. **final authorization review**：a fresh read-only session reviews the exact final canonical auth bytes
   and SHA，including the basis JSONL digest。Its own SHA is closeout evidence，not a field inside the
   authorization。

This removes the circular dependency without weakening the controller schema or inventing a second
lifecycle authority。

## 7. Operational hazards the plan must close

- `cmd_run` copies authorization before lock acquisition；a concurrent lock winner can leave a sealed
  root with consumed live authorization。That run must be abandoned，not retried。
- Controller stdout is intentionally quiet until terminal result；liveness must be observed through
  ledger tail、phase、P0 lock、exact unit state and namespaced DB rows，not file-change guesses。
- A handled failure at `baseline-captured+` attempts fixed cleanup under the existing token。If cleanup
  blocks or authority becomes uncertain，do not issue speculative mutation or second controller；retain
  lock/evidence and enter the reviewed incident branch。
- Authorization expiry is rechecked before every forward phase。TTL、latest start and wall deadline must
  cover four 75-second complete envelopes、expiry/recovery and cleanup without creating an open-ended
  mutation window。
- Discord gateway reconnects are an environmental signal。P3 zero-provider local fixture work does not
  need Discord delivery，but canonical service identity and bounded ready/smoke state still remain gates。

P9_3C1_P3_FRESH_MEASUREMENT_COMPLETE_LIVE_MUTATION_BLOCKED
