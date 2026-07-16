# P9-3C1 P3 Retry Incident — Measurement

状态：`MEASURED_CLEANUP_BLOCKED_ALL_MUTATION_FORBIDDEN`

日期：2026-07-16 Asia/Shanghai

## 1. Exact authority and attempt boundary

- Deployed/main/origin revision：`dde26886cfbd2ba223896db3687d8bd624a11553`。
- Coordinate revision：`a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。
- Run：`p9-3c1-prod-20260716t140135z-dde26886`。
- Controller SHA：`31ca28804c2a5d9252002124c324acb7353a2431af6da82e37e3b9c3ffcecf82`。
- Exactly one reviewed foreground `run` invocation occurred。No second controller、manual cleanup、release or
  recover was attempted。
- Observed controller stderr：
  `catalog version downgrade for 'p9-3c1-fixture-executors': 3 < 4`。

The local operator wrapper used Bash-only `PIPESTATUS[0]` from zsh after the remote command returned；the
wrapper therefore failed to create an authoritative `run.exit` artifact。`run.stdout` is empty because the
controller diagnostic was stderr。This recording defect did not cause or repeat the remote run。

## 2. Immutable evidence

Exact evidence directory：
`/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-operator-p9-3c1-prod-20260716t140135z-dde26886`。

- operator observation SHA：`7083ab87a8e328cfaa32e4d622832bbc4528a33e2151ccaa79c5178f920653b4`；
- 30-second observation SHA：`a9d2c23a7711f31b87989370566e03e9e561f43cb957f76355dcfbec4b482c22`；
- failure status SHA：`39ee0e0054baa994b99a64eaa5ba6c3cb6742631772fd88a1c8260b4cba7cf28`；
- failure lock SHA：`ddea706770f9109626eb2dd68e13fc985c88213186672dd7c79641aa39bceb2c`；
- failure DB SHA：`43ae530b5b8b1bf27022687b4c944f75651272d8740447b871b7e7da9c5524bc`；
- failure units SHA：`a29984b14ac7677ef229403b437ba65ad7d8c56c2f94983da92c2e385c0afdce`；
- failure services SHA：`444c843b1388fd3a822c6e719ff72b567e7306768b61284ebd17d43f1e245f78`；
- failure packet-list SHA：`1ff3749e6434019df6152adf07c6600925a72e3f645ca54cdf65eeef7ae279bc`。

Fresh KAT incident reviewer：

- model：`kat-coder/kat-coder-pro-v2.5`；
- native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-dde26886-cleanup-blocked-incident-review-kat-coder-pro-v2.5/2026-07-16T14-25-32-187Z_019f6b51-841a-7000-ab81-b836e1b6980e.jsonl`；
- JSONL SHA：`6c2564c6e1fc279570161b94327b683473bdac1a2d405aef08d755d1e1e94fb6`；
- classification first line：`INCIDENT_CONFIRMED`。

The reviewer confirmed the incident and downgrade chain。Codex rejects three non-authoritative reviewer
recommendations：P0 recover alone is insufficient because the state-root token remains；measurement/review
and worker/result review cannot be combined；the suggested `PIPESTATUS` fallback is not actually portable。

## 3. Stable live state

Immediate and greater-than-30-second read-only snapshots agree：

- phase `agents-online`；ledger records `8`；tail `cleanup.initiated`；
- global production lock held by owner PID `2668003`，while `/proc/2668003` and controller process are absent；
- standard state-root lock token file present；
- fresh E1/E2 units not-found/inactive/MainPID 0；
- E1/E2 registry rows online with current load 0；
- zero P9 jobs、leases、executor definitions/bindings and capacity policies；
- executor source is empty v4；capacity source is empty v2；
- workspace/profile point to the current incident run；
- DB integrity ok、schema 13、zero FK violations；
- Coordinate and bridge remain active/running at PID/NRestarts `836234/0` and `1276892/0`。

This is `cleanup-blocked + stale-owner held lock`。It is not cleanup-completed and cannot be retried。

## 4. Exact code-path cause

The retained audit source already has executor version 4。The fixed protocol is not retry-safe：

1. `_phase_executor_v1_disabled()` attempts fixed executor v1 after phase `agents-online`；Coordinate rejects
   the downgrade `1 < 4`；
2. `_execute_state_machine()` enters its failure cleanup because baseline was captured；
3. `_execute_cleanup_suffix()` appends `cleanup.initiated` and then attempts fixed executor v3；Coordinate
   rejects `3 < 4`；
4. the cleanup exception masks the original `1 < 4` failure and occurs before agent deactivation、
   `cleanup.completed`、phase `done` and `_release_lock()`。

The same structural bug exists for every future attempt after terminal executor v4/capacity v2：fixed
v1-v4 and v1-v2 cannot be replayed against retained monotonic source authority。

## 5. Recovery authority gap

The installed P0 helper's systemd probe accepts only unit names beginning `p9-3c1-`，while real fixture
units begin `p9-3c-fixture-`。Current P0 recover is therefore forbidden。

Even after a separately proven P0 recovery releases the global lock，the current state-root token remains。
Existing `cmd_cleanup()` calls `_acquire_lock()`，which refuses any existing token path。A safe recovery
therefore needs all of：

1. corrected unit/process probes and durable P0 recovery receipt；
2. a reviewed way to acquire a new global lock while validating and retiring the stale state-root token；
3. idempotent cleanup from already-terminal empty executor v4/capacity v2；
4. exact incident authorization binding phase/tail/ledger/token digest/recovery receipt/deployed bytes；
5. terminal independent review。

Normal deploy cannot install these fixes while the global lock is held。A reviewed source-streamed recovery
sidecar must first release only the stale global lock，after exact no-unit/no-process/DB/phase proof。No
unreviewed manual `rm`、release or server edit is an acceptable substitute。

## 6. Required architectural separation

Two implementation packages are required：

- **IR package**：P0 probe correction、incident-authorized stale-token re-acquisition、legacy terminal-state
  cleanup idempotence and shell-explicit operator receipt capture；
- **EP package**：fresh-run monotonic catalog epoch protocol，rendered run-scoped config authority，manifest/
  preflight/readback/cleanup/success/test updates。

Combining IR and EP would make emergency cleanup depend on a larger forward-protocol refactor。They remain
separate so production can first reach a reviewed terminal incident state，then adopt repeatable epochs。

P9_3C1_P3_RETRY_INCIDENT_MEASURED_CLEANUP_BLOCKED_ALL_MUTATION_FORBIDDEN
