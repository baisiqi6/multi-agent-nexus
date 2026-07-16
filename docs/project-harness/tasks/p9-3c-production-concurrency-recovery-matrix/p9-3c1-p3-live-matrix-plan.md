# P9-3C1 P3 Live Production Matrix — Detailed Plan

状态：`DETAILED_PLAN_READY_FOR_INDEPENDENT_REVIEW_LIVE_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Outcome and hard boundary

Run exactly one authorized five-job/two-unit P9-3C1 matrix against the real schema-13 production DB，
then leave zero fixture executable state and exact dormant audit history。P3 proves production coexistence、
capacity/resource exclusion、lease recovery、stale-attempt fencing、bounded local delivery and cleanup。

This plan does **not** itself authorize：

- revision-alignment deploy or fresh `prepare`；
- authorization source creation/install；
- controller `run` or `cleanup`；
- manual Coordinate mutation、direct SQLite write、service restart、provider/network/external delivery；
- reuse or mutation of a P2/failed run root。

Each mutation gate below opens only after the preceding exact artifact and independent review is durable。

## 2. Fixed inputs

- Plan base：MultiNexus `33773c16fe7a12174b55e8e1731dbb2705e9e56b`。
- Runtime implementation：`17d0bcc1d0aeb56a821b88f096379e6dcb547fc9`。
- Current deployed runtime revision：`06f98f25f3ef5f51b6bc191c66fbe041c0e006a6`。
- Coordinate deployed：`a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。
- Controller entrypoint：`/opt/multinexus/scripts/p9-3c1-production-verify.sh`。
- Production DB/CLI：`/var/lib/coordinate/coord.sqlite3`、`/usr/local/bin/coord-local`。
- Host/unit user/group：`VM-0-15-ubuntu`、`coord`、`coord`。

All existing P2/failed state roots are read-only forensic/audit inputs。P3 creates a fresh id only after
revision alignment：`p9-3c1-prod-YYYYMMDDtHHMMSSz-<deployed-sha8>`。

## 3. Deliverables and review sequence

1. this fresh measurement and detailed plan；
2. independent plan review，with all findings dispositioned；
3. exact P3 operator bootstrap and independent bootstrap review；
4. merge/push docs-only package to `main`；
5. reviewed no-restart revision-alignment deploy and fresh sealed run；
6. basis live-preflight reviewer native JSONL；
7. canonical authorization proposal and fresh exact-auth reviewer native JSONL；
8. root-owned remote authorization source with exact reviewed hash；
9. one Codex-operated controller run plus native terminal/ledger monitoring；
10. independent post-run live review、deployment dogfood/closeout、progress/roadmap/Phase 9 sync。

There is no Coding worker in the expected P3 path because no code change is planned。Codex remains
architect/operator/final reviewer；non-Codex agents are independent plan/bootstrap/live/auth/result
reviewers。If implementation changes become necessary，KAT-Coder-Pro V2.5 is the first Coding worker
candidate，with verified native JSONL；fallback follows the user-approved provider order。

## 4. Plan and bootstrap gate

Independent plan reviewer must verify：

- P2 is truly closed and P3 does not inherit its run id/manifest/auth；
- no code change is hidden in the docs package；
- revision alignment、review circularity split、authorization TTL and mutation boundaries are exact；
- success residue and every failure branch match implemented controller behavior；
- `run` is one-shot and `cleanup` is never used speculatively；
- paid provider/network/external delivery budget is zero。

After plan approval，generate an operator bootstrap containing exact SHA、paths、allowed commands、forbidden
commands、pre/post queries、polling cadence、stop conditions and incident routes。A fresh independent
bootstrap reviewer must return `APPROVE` before merge/push or production action。

## 5. Revision-alignment deploy gate

After reviewed plan/bootstrap artifacts are merged and pushed：

1. fetch `origin/main` and prove local/main/origin exact and tracked-clean；
2. capture lock、DB health/nonterminal/lease/fixture counts、canonical PID/NRestarts and current VERSION；
3. run exact `scripts/deploy-server.sh multinexus --host kook-hermes-admin --multinexus-src <clean
   reviewed-worktree> --no-restart`；
4. require canonical roster/executor/capacity parity zero delta；
5. require installed runtime hashes still equal reviewed `17d0bcc` bytes，while `VERSION_DEPLOYED` equals
   the merged P3 docs revision；
6. require lock free、PID/NRestarts unchanged、DB `ok/13/0`、zero nonterminal/active lease/fixture state；
7. if default smoke sees a transient gateway breaker，retain the failure and require a later exact ready
   boundary plus bounded `server smoke OK`；never hide or misattribute it。

No service restart、`--allow-dirty`、`--no-smoke`、catalog delta、fixture activation or P3 run is allowed。

## 6. Fresh prepare and immutable pre-live packet

Only after revision alignment passes：

1. create one fresh run id with deployed SHA8；
2. call only `prepare --unit-user coord --unit-group coord`；
3. run two `preflight/status` read-only rounds；
4. document the exact canonical full-tree bytes+metadata formula and prove one unchanged hash；
5. verify root/mode matrix、manifest/ledger/phase、backup、authorization/token absence；
6. reprove lock free、canonical projection、installed hashes/revisions、DB `ok/13/0`、zero fixture
   workspace/agent/catalog/job/lease/unit/process and canonical PID/NRestarts；
7. freeze the packet：run id、manifest SHA、installed revisions/hashes、plan SHA、bootstrap SHA、preflight
   stdout SHA、status stdout SHA、tree SHA、production baseline and allowed budgets。

Any failure creates/retains a non-runnable forensic root according to controller behavior。Do not reuse、
repair or cleanup it；correct the cause through a new reviewed revision and later fresh run。

## 7. Two-review authorization chain

### 7.1 Basis live-preflight review

A fresh non-Codex reviewer receives the immutable pre-live packet、exact committed plan/bootstrap、runtime
code/tests and read-only SSH authority。It must independently rerun `preflight/status` and inspect
VERSION/hash/stat、lock、DB、services、units/processes and namespace absence。It must not create files or
perform any mutation。

The provider-native JSONL is the basis artifact。Only a final `APPROVE` session with verified
provider/model is valid。Compute its exact JSONL SHA-256 after the session ends；that digest becomes
authorization `review_artifact_sha256`。

### 7.2 Canonical authorization proposal

Build exact canonical UTF-8 JSON with one trailing newline and **exactly**：

```json
{
  "budgets": {
    "external_delivery": 0,
    "max_active_units": 2,
    "provider_network": 0,
    "total_requests": 5
  },
  "contract_version": 1,
  "expiry_utc": "<canonical UTC Z, creation plus 60 minutes>",
  "installed_hashes": {
    "<installed-artifact-name>": "<exact-sha256>"
  },
  "installed_revisions": {
    "coordinate_deployed": "<exact-40-char-sha>",
    "multinexus_deployed": "<exact-40-char-sha>"
  },
  "manifest_sha256": "<fresh manifest SHA>",
  "nonce": "p9-3c1-p3-<UTC>-<random-hex>",
  "p3_bootstrap_sha256": "<exact committed bootstrap file SHA>",
  "review_artifact_sha256": "<basis reviewer native JSONL SHA>",
  "reviewer_verdict": "APPROVE",
  "run_id": "<fresh P3 run id>"
}
```

The illustrated object entries must be replaced by the complete exact manifest objects；no placeholder
key/value may remain，and no extra top-level key、comment、secret、credential or prompt text is allowed。
Canonical serialization must use the controller's exact key ordering/separators rather than relying on
the display indentation above。Compute exact auth SHA。

### 7.3 Final exact-auth review and install

A second fresh reviewer inspects the final bytes/hash、basis JSONL、manifest/bootstrap and expiry window，
then returns `APPROVE` or `REQUEST_CHANGES`。This second reviewer SHA is closeout evidence and is not
self-inserted into the controller authorization。

Only after approval：

- create remote directory `/var/tmp/multinexus-p9-3c1-authorizations` as `root:root 0700`；
- install the reviewed source as `<run-id>.json`，ordinary single-link `root:root 0600`；
- verify remote SHA/stat/bytes equal the reviewed local proposal；
- recheck lock free、phase sealed、live authorization/token absent and at least 50 minutes remain；
- if any mismatch or less than 50 minutes remains，do not edit/reuse the artifact；create a new nonce/file
  and repeat final auth review。

## 8. Maintenance window and last pre-run gate

Immediately before `run`：

- source/origin/deployed/install/manifest/bootstrap/auth exact；
- basis/final reviewer verdicts `APPROVE` and native JSONL preserved；
- lock free and lock path absent；
- DB integrity/schema/FK `ok/13/0`；pending/running/recoverable timed-out `0`；active/due leases `0`；
- zero P9-3C1 workspace/agent/catalog/job/unit/process；
- canonical projection equals manifest；
- Coordinate/bridge PIDs and NRestarts equal sealed values；both active/running；
- no deploy/other production mutation task is active；
- authorization has at least 50 minutes remaining；operator wall deadline is 30 minutes；
- no user prompt/result/environment/token/credential fields will be printed or queried。

Any drift invalidates the authorization/run root。Do not “fix then continue”；retain evidence and return to
fresh prepare/review as required。

## 9. One-shot run and observation

The only live activation command is：

```text
sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh run \
  --run-id <fresh-id> \
  --authorization-file /var/tmp/multinexus-p9-3c1-authorizations/<fresh-id>.json \
  --authorization-sha256 <exact-sha>
```

Run it in one persistent operator terminal。Do not launch a second controller。The command may remain quiet
until terminal JSON；quiet stdout is not a hang signal。

Every 30-60 seconds，use separate read-only probes only：

- controller phase and validated ledger tail/count；
- P0 lock owner/action/token-match status without printing the token；
- exact P9-3C1 unit ActiveState/MainPID/NRestarts/cgroup；
- namespaced job statuses、attempt numbers and lease ids/status/due flag；
- exact source versions、binding/policy activation and agent online state；
- canonical service PID/NRestarts and DB integrity；
- provider/network/external-delivery counters remain zero。

Do not print prompt/result/env，do not infer correctness from activity，and do not mutate via monitoring。

## 10. Expected matrix authority

- exactly five jobs：J1/J2/J3/J4/J5；
- J1/J2 complete sequentially on E1/W1，each with at least two renewals；
- J3 holds E1/W1 while J4 runs on E2/W2；distinct resource keys overlap active；
- J5 exact E2 claim reports `resource_blocked` by J3/W1，without a lease；
- E1 exact crash stop，old J3 lease becomes due and exact `(lease_id,job_id)` reap expires attempt N；
- recovery E1 unit uses `hold`、claims attempt N+1 with same resource/new lease；
- stale N progress/report/renew all reject and leave exact authority unchanged；
- current N+1 empty report completes J3 without delivery；
- J5 then completes；J1/J2/J4/J5 each have one exact stdout delivery sent；
- maximum active unit identities E1/E2，total requests 5，provider/network/external delivery 0。

## 11. Success final gate

Controller must return `status=done` and release its exact P0 token。Then independently prove：

- phase `done`，ledger chain/tail exact，authorization copy present/root 0600，token absent，lock free；
- five namespaced jobs terminal `done`；J3 attempts N/N+1 and stale rejection evidence exact；
- zero active lease and zero pending/running/recoverable fixture job；
- exactly four sent stdout deliveries and no J3 delivery；zero pending/failed fixture delivery；
- E1/E2 agents offline、runner profiles dormant；workspace/host profile and terminal audit rows retained；
- executor source v4 and capacity source v2 retained empty；zero definition/binding/policy executable state；
- zero fixture unit/process/cgroup/runaway descendant；
- canonical projection equals fresh baseline；DB `ok/13/0`；
- canonical PIDs/NRestarts unchanged；no restart/provider/network/external send；
- fresh backup/evidence/ledger files and remote auth source preserved，no cleanup of audit roots。

Do not demand zero P9 rows；the accepted postcondition is zero executable state plus namespaced dormant
history。

## 12. Failure and incident matrix

### Before lock acquisition

- invalid/expired auth、hash/revision drift、live-auth already present：no DB mutation；retain root/artifact。
- lock race after live auth copy：run root is consumed and must be abandoned。Do not retry same nonce/root；
  wait for the other owner to finish，then create a fresh run/review/auth chain。

### Lock held before first production mutation

Controller should write `preactivation-failed` and release its own exact token。Verify zero namespace
mutation。If process/token authority is uncertain，do not unlock manually；use P0 reviewed status/recover only
after no P9-3C1 unit/process and operator-reason evidence。

### `baseline-captured+`

Controller attempts fixed cleanup under the same token。After nonzero exit：

1. read `status` only if it can validate without changing state；
2. inspect phase/ledger/cleanup evidence、lock owner、exact units and namespaced DB state；
3. if phase is `done` and lock free，classify as cleanup-completed failure and review evidence；
4. if lock remains held、cleanup-blocked exists or authority is uncertain，stop automation and enter
   incident review；do not start `cleanup` or a second controller blindly；
5. P0 recover requires its own exact no-unit/no-process proof and operator reason；after any reviewed
   release，controller `cleanup` may be considered only by a new incident authorization，never inferred
   from this plan。`cmd_cleanup` does not validate an external authorization artifact itself，so this is
   an explicit procedural hard gate rather than a controller-enforced auth check；
6. any real user job/canonical drift/DB integrity failure/stale mutation accepted/duplicate resource lease
   is an immediate halt with forensic preservation and human escalation。

No direct SQLite repair、global reap、age-based unlock、whole-DB restore、service restart or ad-hoc cancel
is authorized。Whole-DB restore remains a separate last-resort incident plan with no intervening-write proof。

## 13. Post-run independent review and closeout

A fresh non-Codex reviewer reads exact run root、ledger/evidence、installed revisions/hashes、read-only DB、
units/processes、lock and canonical services。APPROVE is required before P9-3C1/P9-3 stage closeout。

Then materialize durable deployment dogfood/closeout、review JSONL handles and SHAs、progress、dogfood
feedback、roadmap and Phase 9 status。Commit/push docs only after live state is terminal and reviewed。
Do not redeploy closeout-only docs unless a later package requires revision alignment。

## 14. Acceptance and next boundary

P3 closes only when one fresh exact-revision run satisfies sections 10-13 with independent live approval。
Approval of this **plan** authorizes only creation of the P3 operator bootstrap after independent plan
review。It does not authorize deploy、prepare、authorization install、`run` or `cleanup`。

P9_3C1_P3_DETAILED_PLAN_READY_FOR_INDEPENDENT_REVIEW_LIVE_MUTATION_BLOCKED
