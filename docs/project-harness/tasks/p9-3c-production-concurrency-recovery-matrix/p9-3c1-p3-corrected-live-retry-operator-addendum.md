# P9-3C1 P3 Corrected Live Retry — Operator Addendum

状态：`DRAFT_FOR_INDEPENDENT_REVIEW_ALL_NEW_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Purpose and authority boundary

This addendum binds the already-approved P3 live matrix operator bootstrap to the reviewed lock-helper path
correction and to a completely fresh retry identity。It does not replace or weaken the original plan/
bootstrap；it adds exact correction evidence、failed-root preservation and launch-time revision rules。

Until a fresh independent review approves this file，no docs alignment deploy、prepare、auth install、`run`
or cleanup is authorized。P0 `recover` remains forbidden throughout this retry。

## 2. Required authority chain

Read these files completely before action：

1. `p9-3c1-p3-live-matrix-plan.md`；
2. `p9-3c1-p3-live-matrix-operator-bootstrap.md`；
3. `p9-3c1-p3-lock-helper-path-correction-measurement.md`；
4. `p9-3c1-p3-lock-helper-path-correction-plan.md`；
5. `p9-3c1-p3-lock-helper-path-correction-plan-review.md`；
6. `p9-3c1-p3-lock-helper-path-correction-bootstrap-review.md`；
7. `p9-3c1-p3-lock-helper-path-correction-result-review.md`；
8. this addendum and its future independent review。

Fixed reviewed identities：

- correction implementation：`ec772f2a0ed2a7d585bad41683f3fe7e34b63e36`；
- current correction docs/deployed revision：`b61e7bf426e04b13dd5ed04d84278171d35eb9d9`；
- Coordinate deployed：`a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`；
- corrected installed helper SHA：
  `201af82e40c29e1f676a92ff2de0e5cdd1bb8dff23c6ac739fcaaebe54b03c92`；
- controller SHA：`31ca28804c2a5d9252002124c324acb7353a2431af6da82e37e3b9c3ffcecf82`；
- P0 installed helper SHA：`7dd71c31595c7135a8a75ef3d8e459788682f6a30272ea5bdeb66bb7c2a2ebd4`；
- original P3 operator bootstrap SHA：
  `541142443dbdf02d4f4304bc658e0b390fff9d81d2f4dcc4f252655f19844552`；
- correction result-review doc SHA：
  `aab1abc1bc59d39d26e2777453eb2350869f5aad5b55847675f2bd5d593d5864`；
- correction reviewer JSONL SHA：
  `aeb838092c6a519f160cfeb889bc89a2ad2b432750c95047ca1e051661702cbb`。

At launch，operator must set `MERGED_RETRY_SHA` to the exact docs-only `main == origin/main` commit that
contains this addendum and its independent review。Require：

```bash
git diff --quiet b61e7bf426e04b13dd5ed04d84278171d35eb9d9..$MERGED_RETRY_SHA \
  -- multinexus scripts tests config agents.toml
```

Only reviewed docs may differ after `b61e7bf...`。If any runtime/test/config surface differs，stop and create
a new implementation package。

## 3. Immutable retained production evidence

Never reuse、repair、rename、cleanup or delete：

```text
p9-3c1-prod-20260716t062904z-90d00e16  # symlink-authority forensic root
p9-3c1-prod-20260716t064920z-c2bee4d4  # dual-clock forensic root
p9-3c1-prod-20260716t071325z-06f98f25  # successful P2 inert sealed root
p9-3c1-prod-20260716t083723z-1faf2606  # P3 cleanup-completed path-drift failure
```

The last root must remain `phase=done`、13 ledger records、tail `cleanup.completed`、lock free、token absent，
with its root-owned live auth、remote auth、backup、ledger、evidence and reviewers preserved。Its nonce、auth、
manifest、basis reviewer and final auth reviewer are consumed evidence and cannot authorize the retry。

## 4. Pre-alignment gate and docs-only alignment

Before the alignment deploy require：

- local/current/origin at `MERGED_RETRY_SHA`；tracked status clean；ignored runtime `agents.toml` exact
  approved SHA `08d834c06b67493dc07d8e9faec5809bf48f23e64572491aceb7ff438cf52ebe`；
- current deployed revision `b61e7bf...`，corrected helper/controller/P0 hashes exact；
- lock `free/free` and lock path absent；
- Coordinate/bridge active/running with PID/NRestarts `836234/0` and `1276892/0`；
- DB `ok/13/0`，zero nonterminal/recoverable job and active/due lease；
- failed-run dormant state：E1/E2 offline，zero P9 job/lease/definition/binding/policy，workspace/profile plus
  executor v4/capacity v2 source retained；
- all exact failed-run units not found/inactive and no P9 process/cgroup。

Run the canonical MultiNexus deploy from a clean worktree at `MERGED_RETRY_SHA` with `--no-restart` only。
Require registry/executor/capacity zero delta、bounded `server smoke OK`、PID/NRestarts unchanged、DB/lock/
failed-root state unchanged。Installed runtime hashes must remain the fixed values in section 2 while
`VERSION_DEPLOYED` becomes `MERGED_RETRY_SHA`。

Do not use `--allow-dirty`、`--no-smoke` or service restart。

## 5. Fresh retry identity and prepare-only gate

Only after alignment passes，create exactly one fresh：

```text
RUN_ID=p9-3c1-prod-<UTC-lowercase-tz>-<MERGED_RETRY_SHA8>
STATE_ROOT=/var/tmp/multinexus-p9-3c1/$RUN_ID
AUTH_REMOTE=/var/tmp/multinexus-p9-3c1-authorizations/$RUN_ID.json
```

Require root and auth path absent。Call only：

```text
sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh prepare \
  --run-id $RUN_ID --unit-user coord --unit-group coord
```

Then execute the original bootstrap section 9 double `preflight/status/tree` packet。Both rounds must be
byte-identical by category；phase sealed；one `prepare.completed` ledger record；lock free；token/live auth
absent；DB `ok/13/0`；zero new P9 namespace/unit/process state；canonical projection、revisions、installed
hashes and corrected shell literal exact。

Any drift consumes/abandons the fresh root。Do not repair、retry or cleanup it。

## 6. Fresh two-review authorization chain

Use the original bootstrap sections 10-15 with these additions：

- basis live-preflight reviewer must be a fresh non-Codex session and must verify the corrected installed
  shell SHA/literal plus all sealed packet/live state；
- none of the failed run reviewers or auth bytes may be reused；
- create a fresh random nonce and canonical auth bound to fresh run/manifest、current deployed revision、
  current installed hashes、original P3 bootstrap SHA and new basis JSONL SHA；
- final exact-auth review must be a second fresh session；its native JSONL SHA is closeout evidence，not an
  auth field；
- authorization expiry is creation + 60 minutes；at least 50 minutes must remain both before exact root-owned
  install and immediately before `run`；
- install with `O_EXCL|O_NOFOLLOW` to a previously absent root-owned `0600` path；never overwrite。

The review verdict opens only the next named gate。No review retroactively authorizes deploy、run、cleanup or
recover。

## 7. One-shot run and monitoring

After the complete last pre-run gate，run exactly one foreground controller with SSH keepalives and no kill
timeout：

```text
sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh run \
  --run-id $RUN_ID --authorization-file $AUTH_REMOTE --authorization-sha256 $AUTH_SHA
```

Do not launch a second controller。Every 30-60 seconds，use only original bootstrap section 17 read-only
status/lock/systemd/bounded DB probes。Never read prompt/result/env、lock token、live auth bytes or credentials。

P0 recover remains forbidden because its unit-prefix probe residual is not corrected here。If the controller
returns nonzero：

- phase done + lock free => preserve and classify cleanup-completed failure；no more cleanup；
- held lock、cleanup-blocked or uncertain process authority => stop automation and obtain a new incident
  review；no manual release、second controller、speculative cleanup or recover；
- canonical/user drift、DB failure、accepted stale mutation、duplicate resource lease、provider/external send
  => immediate halt and forensic preservation。

## 8. Success and closeout gate

Success is the original bootstrap section 18 exact gate：`status=done`、valid ledger/authorization、lock free、
five terminal jobs、J3 N/N+1 and stale-N rejection exact、four local stdout deliveries and no J3 delivery、
zero active/executable state、dormant audit retained、canonical projection/PIDs unchanged、DB `ok/13/0`、
budgets `5/2/0/0`。

After terminal success，launch a fresh independent post-run live reviewer。Only its `APPROVE` permits P3
dogfood/closeout、progress、roadmap and Phase 9 status updates。Do not delete any retry or failed-run evidence。

P9_3C1_P3_CORRECTED_LIVE_RETRY_ADDENDUM_READY_FOR_INDEPENDENT_REVIEW_ALL_NEW_MUTATION_BLOCKED
