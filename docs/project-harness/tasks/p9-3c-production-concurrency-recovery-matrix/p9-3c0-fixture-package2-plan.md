# P9-3C0 Package 2 — Zero-Provider Fixture Assets Detailed Plan

> **Plan only.** This document does not authorize implementation, unit launch,
> catalog sync, job/lease creation, SSH, deployment, service restart, or production
> fixture activation. A fresh independent review of this exact plan revision is
> required before a worker bootstrap may be generated.

## 1. Exact planning base and closed dependencies

- MultiNexus planning base:
  `ba6bb122eef17910a463be259142c6c0b82020e4`.
- Coordinate multi-source capacity and snapshot dependency:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.
- Reviewed MultiNexus C2 candidate:
  `952522dcaf4e27aa920045129e41830c42f15009`.
- Deployed MultiNexus C2 merge:
  `c5cf5f27a9aafbce828e1ff028c7c7e53d186907`.
- Parent fixture plan:
  `p9-3c0-fixture-plan.md`, whose Round 3 verdict authorized Package 2 only after
  Package 1 closed.

C1 and C2 are now reviewed, merged, pushed, deployed, and accepted. Production still
has one canonical capacity source, eight canonical policies, zero active leases, zero
pending/running jobs, and no fixture catalog or unit. Package 2 must not change that
state.

## 2. Refreshed current facts

At the exact planning base:

- no `multinexus/fixture/` tree exists;
- `ClaudeAdapter._build_cmd` invokes `claude_bin` with exactly
  `-p --verbose --output-format stream-json --include-partial-messages` when no model,
  resume id, or dangerous-permission flag is configured;
- `ClaudeAdapter._run` writes the full prompt to stdin, waits for line-delimited JSON,
  treats the first stdout byte as activity, and accepts a `type=result` event;
- `agentd` loads a separate TOML with `require_token=False` and requires
  `--config` plus exact `--agent`;
- current config fields are `timeout`, `first_byte_timeout`, and
  `activity_timeout`; no `total_timeout` field exists;
- executor and capacity authority parsers already accept standalone secret-free TOML
  sources and compute canonical hashes;
- deploy copies the repository tree but does not activate files under a fixture
  directory unless an operator explicitly invokes them.

Refreshed baseline evidence:

- fixture-adjacent focused suite:
  `89 passed, 20 subtests passed`;
- full suite:
  `663 passed, 2 skipped, 55 subtests passed` from `665 collected`;
- local `main` matched `origin/main` and was clean when measured; production reported
  the separately recorded deployed C2 revision and healthy inert state.

## 3. Package objective and non-objectives

Package 2 adds reviewed, secret-free assets that can later support Package 3's
isolated sidecar proof. It must provide:

1. a local executable that behaves like the smallest valid Claude stream-json child
   while using no provider and producing no output for the bounded quiet window;
2. two fixture-only agent configs with explicit timeout budgets;
3. immutable forward/cleanup executor and capacity authority fixtures;
4. an exact systemd transient-unit lifecycle helper with an exclusive ledger and
   fail-closed sandbox checks;
5. an operator runbook that distinguishes inert deployment, isolated Package 3 use,
   and the still-blocked P9-3C1 production activation path;
6. local tests that do not contact a provider, network, real systemd manager, SSH host,
   or production DB.

Package 2 does **not**:

- add a new adapter kind;
- modify `ClaudeAdapter`, `agentd`, Coordinate, deploy scripts, canonical
  `agents.toml`, or `config/agent-registry.toml`;
- register a runtime agent or runner profile;
- sync executor/capacity catalogs;
- start a transient unit;
- submit, claim, renew, reap, recover, or report a job/lease;
- prove the real 75-second renewal row; that is Package 3;
- authorize any production fixture use; that is P9-3C1.

## 4. Exact repository/deployment location

The approved source location is `multinexus/fixture/`. Therefore the deployed inert
asset location is exactly:

`/opt/multinexus/multinexus/fixture/`

The older parent plan's shorthand `/opt/multinexus/fixture/` must not be used. Tests,
config rendering, the helper, and the runbook must agree on the exact source and
deployed paths above.

## 5. Exact worker allowlist

The implementation worker may add only these files:

- `multinexus/fixture/bin/p9-3c0-fixture.py`;
- `multinexus/fixture/bin/p9-3c0-unit.sh`;
- `multinexus/fixture/config/agents.fixture.toml`;
- `multinexus/fixture/config/executor.fixture.v1-disabled.toml`;
- `multinexus/fixture/config/executor.fixture.v2-enabled.toml`;
- `multinexus/fixture/config/executor.fixture.v3-disabled.toml`;
- `multinexus/fixture/config/executor.fixture.v4-empty.toml`;
- `multinexus/fixture/config/capacity.fixture.v1.toml`;
- `multinexus/fixture/config/capacity.fixture.v2-empty.toml`;
- `multinexus/fixture/docs/runbook.md`;
- `tests/test_p9_3c0_fixture_assets.py`.

The two files under `bin/` must be executable in Git. No existing file may change.
The versioned immutable authority files replace unsafe operator-time editing of one
mutable template while preserving the parent plan's exact forward and cleanup order.

If implementation requires an existing runtime file, deploy script, extra helper,
canonical authority, or second test file to change, the worker must stop and request a
new plan review.

## 6. Fixture executable contract

### 6.1 CLI allowlist

`p9-3c0-fixture.py` must accept the exact ClaudeAdapter no-model/no-resume argv set:

```text
-p --verbose --output-format stream-json --include-partial-messages
```

Equivalent ordering of those option pairs may be accepted, but every required option
must appear exactly once. Unknown flags, positional text, duplicate flags, another
output format, `--model`, `--resume`, and dangerous-permission flags fail before stdin
execution. The script must not expose a custom `--mode` option.

### 6.2 Strict stdin envelope

The entire stdin text must be one JSON object with exact keys:

```json
{
  "contract_version": 1,
  "mode": "complete",
  "quiet_seconds": 75,
  "spawn_descendant": false
}
```

Rules:

- exact key set; no missing or extra keys;
- `contract_version` exact integer `1`, not bool/float/string;
- `mode` exactly `complete` or `hold`;
- `quiet_seconds` exact integer `75`, with no default or alternative production
  duration;
- `spawn_descendant` exact bool;
- `spawn_descendant=true` is valid only with `mode=hold`;
- leading/trailing whitespace around the JSON document may be accepted, but trailing
  documents or non-JSON text fail closed.

Invalid CLI or stdin exits nonzero and may write one bounded diagnostic to stderr.
No child/descendant may start before both CLI and stdin validation succeed.

### 6.3 Quiet/result behavior

- From successful validation until the 75-second boundary: zero stdout, zero stderr,
  and therefore zero adapter progress event.
- `complete`: after the boundary, emit exactly one compact JSON line with
  `type=result`, `subtype=success`, `is_error=false`, and
  `result="fixture complete"`; then exit `0` without another line.
- `hold`: remain silent after the boundary until the exact transient unit is stopped.
  It must not invent a provider session id or terminal result.
- `hold` is deliberately short-lived: Package 3 must command the exact-unit stop at
  a target elapsed time of 80 seconds after its recorded fixture-start boundary,
  accept timing evidence only while `75 <= elapsed < 85`, and always remain below the
  adapter's absolute `first_byte_timeout=90`. The five-second evidence margin is for
  scheduling jitter and bounded shutdown initiation, not extra hold time.
- A stop initiated at or after 85 seconds is an evidence failure. The helper must
  still stop and prove cleanup of the exact unit/cgroup before returning nonzero; it
  must never preserve a process merely because the timing row is already invalid.
- `spawn_descendant=true`: start one bounded, silent descendant owned by the same unit
  cgroup, solely for Package 3's cgroup cleanup proof. The fixture must never daemonize,
  escape the cgroup, or create a second session manager.
- SIGTERM/SIGINT handling must remain silent and permit bounded unit shutdown.

The implementation must expose pure parsing/decision functions that the test can load
from the script path and exercise with an injected sleep/emitter. There must be no
production environment variable or hidden CLI flag that shortens 75 seconds. The
real-time 75-second zero-output and lease-renewal proof remains Package 3.

### 6.4 Zero-provider and secret boundary

The executable may use only standard-library process/time/JSON primitives. It must not
import network clients, open sockets, read environment credentials, read home/config
files, or invoke Claude/provider binaries. It reads only argv/stdin and, for the
optional hold descendant, starts a fixed local sleep command without shell expansion.

## 7. Secret-free agent config

`agents.fixture.toml` contains only fixture defaults and exactly two agents:

- `p9-3c-fixture-e1`;
- `p9-3c-fixture-e2`.

Required values:

- `agentd_mode=true`;
- `adapter="claude"`;
- `timeout=240`;
- `first_byte_timeout=90`;
- `activity_timeout=90`;
- empty `system_prompt`;
- no `model`, resume id, dangerous-permission setting, token, token_env, Discord id,
  channel, webhook, provider key, or provider URL;
- run-specific absolute placeholders for `claude_bin`, `work_dir`,
  `coordinator_cli_path`, `coordinator_db_path`, and `context_db_path`.

The committed template is not directly launchable. `p9-3c0-unit.sh render` must replace
each exact placeholder once, refuse leftovers/duplicates, write a run-specific file
with mode `0600`, then parse it using the existing MultiNexus config loader with
`require_token=False`. It must independently assert that both resolved `claude_bin`
values equal the expected absolute fixture executable path; this prevents
`_first_existing_command` from silently falling back to a real `claude` binary.

The two context DB paths must be separate or agent-qualified so E1 and E2 do not share
session state.

## 8. Immutable executor/capacity authorities

All sources are separate from `multinexus.discord` and
`multinexus.discord.capacity`.

### 8.1 Executor source

- source id: `p9-3c0-fixture-executors`;
- one definition: `p9-3c-local-fixture`;
- `provider="local-fixture"`;
- `adapter="claude"`;
- sorted capabilities containing the exact capability used by Package 3;
- E1/E2 `runner_profile_id` exactly equals each agent id.

Immutable states:

- v1: E1/E2 bindings exist with `enabled=false`;
- v2: the same definition/bindings with `enabled=true`;
- v3: the same bindings return to `enabled=false`;
- v4: the source is empty.

Each version must parse through `load_authority`, have a distinct canonical hash, and
contain no real or canonical roster/Discord identities or canonical agent ids. The
shared parser nevertheless requires a quoted positive decimal `discord_user_id` for
each managed entry. Therefore every non-empty executor version must use these exact
synthetic parser-only placeholders:

- E1: `discord_user_id="1"`;
- E2: `discord_user_id="2"`.

These values are deliberately too short to be real Discord snowflakes. They are not
an official Discord-reserved namespace, convey no routing identity, and must never be
passed to `workspace agent sync`, a roster verifier, or any deploy-time roster path.
Tests must prove the two values are exact and unique, are absent from the current
canonical `config/agent-registry.toml`, and cannot collide with any canonical
`discord_user_id`. Fixture executor files are valid only as inputs to
`coordinate runtime executor sync --source` in the separately authorized Package 3
isolated workflow.

### 8.2 Capacity source

- source id: `p9-3c0-fixture-capacity`;
- v1: E1/E2 each have `max_concurrent_jobs=1`;
- v2: empty policy list.

Each version must parse through `load_capacity_authority` and have a distinct canonical
hash. Tests must prove the forward sequence is executor v1 disabled -> capacity v1 ->
executor v2 enabled, and cleanup is executor v3 disabled -> capacity v2 empty ->
executor v4 empty. The assets themselves do not execute those transitions.

## 9. Exact transient-unit helper

`p9-3c0-unit.sh` is an operator lifecycle helper, not a catalog or job orchestrator.
It supports explicit subcommands only:

- `render`;
- `preflight`;
- `start`;
- `status`;
- `stop`;
- `cleanup`.

Its functions must be sourceable without executing `main`, using the ordinary
`BASH_SOURCE[0] == "$0"` guard. Unit tests may replace individual shell functions after
sourcing to capture command argv and simulate results; the executable entrypoint must
contain no test-mode environment switch, backend override, or production bypass.

### 9.1 Identity and ledger

- agent allowlist is exactly E1/E2;
- run id must match a bounded lowercase alphanumeric/hyphen grammar;
- exact unit names are
  `p9-3c-fixture-e1-<run>.service` and
  `p9-3c-fixture-e2-<run>.service`;
- every mutating subcommand holds one exclusive `flock` under an explicit state root;
- the state root, lock, rendered config, and JSON/line ledger are mode `0700`/`0600`;
- ledger binds run id, agent id, exact unit, config path, Coordinate wrapper path,
  isolated DB path, work dir, unit start time, Package 3's recorded fixture-start
  boundary when present, requested stop time, actual stop-command time, timing verdict,
  and observed cgroup;
- status/stop/cleanup derive the exact unit only from this ledger and reject any
  caller-supplied mismatch;
- no `pkill`, wildcard unit pattern, guessed PID, process-name match, or unbounded
  `rm -rf` is allowed.

### 9.2 Isolated-only Package 2 boundary

The helper must fail closed if:

- Coordinate DB resolves to `/var/lib/coordinate/coord.sqlite3`;
- Coordinate wrapper resolves to `/usr/local/bin/coord-local`;
- work/state/context paths escape the explicit isolated root;
- config/fixture executable paths are not absolute reviewed paths;
- fixture ids appear in canonical `config/agent-registry.toml`;
- an unrelated unit already occupies the exact unit name;
- more than two units would exist in the run ledger.

Package 2 therefore cannot activate production even after the assets are deployed.
P9-3C1 must independently review any future production-capable authorization path;
there is no magic environment variable or bypass token in Package 2.

### 9.3 Preflight and sandbox

Before start, verify:

- Linux/systemd manager and required commands exist;
- rendered config resolves exact E1/E2 values and timeout budgets;
- control envelope used by the later request is exactly quiet 75;
- isolated Coordinate wrapper passes a read-only health/list call;
- no active/running fixture job or lease is declared in the supplied isolated
  evidence; Package 3 owns creation of that evidence;
- exact fixture namespace is quiescent;
- required unit properties are accepted; unsupported properties fail closed before an
  agentd unit is considered usable.

Mandatory unit properties:

- explicit `User`/`Group`;
- exact `WorkingDirectory`;
- `RuntimeMaxSec=300`, derived from `timeout=240` plus a bounded 60-second shutdown
  and cleanup ceiling; it is a last-resort unit safety ceiling and never a valid
  `hold` success window;
- `TimeoutStopSec` bounded;
- `KillMode=control-group`;
- `IPAddressDeny=any`;
- `RestrictAddressFamilies=AF_UNIX`;
- `NoNewPrivileges=yes`;
- `PrivateTmp=yes`;
- restrictive filesystem/home protection with only the isolated root writable;
- `UMask=0077`;
- minimal `env -i` environment with explicit unsets/absence of common Anthropic,
  OpenAI, Discord, KOOK, AWS, Azure, Google, Moonshot/Kimi, GLM, DeepSeek, and Minimax
  credential variables.

If the systemd manager cannot enforce the network properties, the helper refuses to
start after appending a bounded failure record to the run ledger; packet capture is
not a substitute.

### 9.4 Start/status/stop/cleanup

- `start` launches exactly
  `python -m multinexus.agentd --config <rendered> --agent <exact-id>` inside the exact
  unit. It never adds `--recoverable` in Package 2.
- After start, inspect the exact unit properties and persist `MainPID`, `ControlGroup`,
  state, and result. A mismatch triggers exact stop and returns nonzero.
- `status` uses `systemctl show <exact-unit>` with bounded property names only.
- For a Package 3 `hold` row, its controller supplies the recorded fixture-start
  boundary to the exact-unit stop operation. The helper validates a monotonic elapsed
  duration, records both requested and actual stop-command time, and accepts the
  timing row only for `75 <= elapsed < 85`. The operator target is 80 seconds. Package
  3 must derive the boundary from its isolated request/worker evidence and bind it to
  the same run id; Package 2 does not submit or observe the request itself.
- `stop` freezes only the fixture ledger intake marker, stops the exact unit, waits
  boundedly for inactive, then proves the recorded cgroup's `cgroup.procs` is empty or
  the cgroup no longer exists. Missing, mismatched, non-monotonic, or late hold timing
  evidence makes the command nonzero only after this cleanup proof.
- `cleanup` is allowed only after the stop proof; it removes only ledger-listed
  run-specific files and keeps an append-only bounded evidence record.

Package 3, not this helper, will submit requests, drain jobs, invoke global reap, or
start a reviewed recovery unit.

## 10. Runbook contract

The runbook must contain three visually separate tracks:

1. **Package 2 inert verification/deployment** — parse files, run tests, deploy assets,
   verify no fixture DB/unit/job/lease/catalog state changed.
2. **Package 3 isolated sidecar preview** — exact commands with placeholders for an
   isolated DB/wrapper/root, immutable forward/cleanup catalog ordering, exact request
   envelope, unit lifecycle, and evidence paths. It must show the 80-second target,
   the accepted `75 <= elapsed < 85` interval, the absolute 90-second first-byte
   timeout, and cleanup-before-failure behavior. Mark every command unauthorized until
   the Package 3 bootstrap is approved.
3. **P9-3C1 production activation outline** — list prerequisites and explicitly state
   that Package 2's helper rejects the production DB/wrapper. Do not provide a bypass.

The runbook must use real current CLI names:

- `coordinate runner add`;
- `coordinate runtime agent register`;
- `coordinate runtime executor sync --source`;
- `coordinate runtime capacity sync --source`;
- `coordinate runtime request submit --target-agent`.

It must not recommend direct SQLite writes/deletes, mutable TOML edits between stages,
`pkill`, wildcard units, or canonical authority changes.

## 11. Test matrix

All Package 2 tests are local and isolated.

### Executable tests

- exact Claude argv accepted; missing/duplicate/unknown/model/resume/dangerous args
  rejected;
- exact envelope accepted; missing/extra keys and bool/float/string boundary values
  rejected;
- `complete` calls the injected sleeper for exactly 75, emits one compact result, and
  exits 0;
- `hold` remains silent and responds to an exact termination path;
- descendant option is hold-only and uses a fixed no-shell command;
- no output occurs before the injected 75-second boundary;
- source/static check has no network/provider/config/credential access path.

### Config/authority tests

- rendered config loads with `require_token=False` and exact timeout/bin/path values;
- raw/unrendered or partially rendered config is rejected by the helper;
- no token, provider key, URL, Discord/KOOK identity, canonical id, or canonical
  authority mutation appears, except the exact parser-only synthetic values `"1"`
  and `"2"` in non-empty fixture executor authorities;
- synthetic ids are exact/unique, absent from canonical authority, do not collide with
  current canonical Discord ids, and the fixture executor sources are never routed to
  roster/workspace sync;
- every immutable authority parses, hashes deterministically, has exact ids/versions,
  and encodes the reviewed staging order;
- both capacity policies equal one and ownership sets are disjoint from canonical ids.

### Helper tests

- `bash -n` and shell static checks;
- path/run-id/agent/unit/ledger allowlists fail closed;
- canonical production DB/wrapper rejection;
- exclusive lock and maximum-two-unit budget;
- a sourced-function harness replaces external-command functions in the test shell and
  proves exact systemd arguments, mandatory sandbox properties, post-start mismatch
  cleanup, exact status/stop, bounded inactive wait, and cgroup empty proof without
  calling a real manager;
- hold timing accepts the 80-second target and boundary values inside
  `75 <= elapsed < 85`, rejects missing/mismatched/non-monotonic or `>=85` evidence,
  and still performs exact-unit/cgroup cleanup before returning failure;
- unsupported network property records bounded ledger evidence and refuses start;
- cleanup cannot run before stop/cgroup proof and cannot delete outside the ledger;
- no test invokes the real systemd manager, SSH, production DB, or network.

### Repository/deployment invariants

- changed-file set equals the exact allowlist;
- canonical `agents.toml`, `agents.toml.example`, `config/agent-registry.toml`, deploy
  scripts, runtime packages, and Coordinate are byte-unchanged;
- inert deploy-contract coverage or static deployment assertion proves the new assets
  are copied but never invoked automatically.

## 12. Verification commands and expected baselines

Use the existing environment; install/upgrade is forbidden.

```bash
.venv/bin/python -m pytest tests/test_p9_3c0_fixture_assets.py -v
.venv/bin/python -m pytest \
  tests/test_p9_3c0_fixture_assets.py \
  tests/test_claude_adapter.py \
  tests/test_executor_capacity_authority.py \
  tests/test_registry_authority.py \
  tests/test_deploy_contract.py \
  tests/test_smoke_contract.py -v
.venv/bin/python -m pytest
.venv/bin/python -m compileall multinexus/fixture tests/test_p9_3c0_fixture_assets.py
bash -n multinexus/fixture/bin/p9-3c0-unit.sh
git diff --check
```

Baseline before the new test exists is focused `89 passed, 20 subtests passed` and
full `663 passed, 2 skipped, 55 subtests passed`. The worker must report new exact
counts and durations rather than copying these baselines.

## 13. Worker and review workflow

After this plan receives independent approval:

1. Codex writes an exact worker bootstrap bound to the approved plan SHA and current
   implementation base.
2. A second independent reviewer approves that bootstrap.
3. A fresh Claude Code worker uses outer `sonnet`, never Opus. Provider-native JSONL
   must show `message.model=kimi-for-coding` unless the operator records an authorized
   fallback.
4. The worker implements in a new isolated worktree, one commit, exact allowlist, no
   push/merge/deploy.
5. Codex verifies JSONL activity, working tree, index/HEAD blobs, tests, and commit
   object separately.
6. A fresh exact-revision result reviewer must approve before merge/push.
7. Only then may Codex perform an inert deployment and prove no fixture activation.

## 14. Stop conditions

Stop rather than widen scope if:

- a real adapter/runtime/deploy/Coordinate change appears necessary;
- the helper cannot remain isolated-only without a production bypass;
- a fixture id must enter canonical authority;
- a raw template can silently resolve to real `claude`;
- exact CLI/stdin compatibility requires provider output or credentials;
- network sandbox is optional or downgraded;
- systemd lifecycle uses a pattern/PID guess instead of ledger-bound exact identity;
- test acceleration introduces a production duration override;
- immutable staging authorities cannot encode the full v1/v2/v3/v4 and v1/v2 order;
- any test reaches real systemd, SSH, network, or production DB;
- provider-native JSONL does not prove the authorized worker route.

`P9_3C0_FIXTURE_PACKAGE2_PLAN_PENDING_INDEPENDENT_REVIEW`
