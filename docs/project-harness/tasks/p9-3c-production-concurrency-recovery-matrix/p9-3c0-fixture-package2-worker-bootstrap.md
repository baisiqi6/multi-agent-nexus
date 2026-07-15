# P9-3C0 Package 2 — Zero-Provider Fixture Assets Worker Bootstrap

> **Bootstrap pending independent approval.** This document does not authorize coding
> until a fresh reviewer approves this exact bootstrap revision. It never authorizes
> real systemd execution, catalog sync, job/lease creation, SSH, production access, or
> fixture activation.

## 1. Exact bases and reviewed dependencies

- MultiNexus implementation base:
  `7e887cbc24a7e38f268e6eb8ba656ac69c11905d`.
- Approved Package 2 plan:
  `p9-3c0-fixture-package2-plan.md`.
- Approved plan SHA-256:
  `282f2c92d09325486245d021349c0689bb92fa05e62a43a3a4e803d27ccf3d93`.
- Round 2 plan approval:
  `p9-3c0-fixture-package2-plan-review-round2.md` with token
  `APPROVED_FOR_P9_3C0_FIXTURE_PACKAGE2_BOOTSTRAP_AUTHORING`.
- Closed Coordinate dependency:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.
- Closed MultiNexus C2 deployment dependency:
  `c5cf5f27a9aafbce828e1ff028c7c7e53d186907`.

The worker must create a new isolated worktree and branch from the exact implementation
base. Recommended branch:
`agents/mac-claude/p9-3c0-fixture-package2`.

## 2. Worker route and evidence

- Use Claude Code as the outer agent with `sonnet`; never use Opus.
- The provider must be Kimi. Provider-native JSONL must contain
  `message.model = kimi-for-coding`; the outer init/result metadata must separately
  show the Claude sonnet route.
- Do not accept a UI label or prompt claim as model evidence.
- Persist the exact Claude session id and JSONL path in the completion report.
- JSONL proves activity/model/tool calls, not committed state. The worker must also
  report `git status --porcelain=v2`, `git diff`, `git diff --cached`, `git show HEAD`,
  and the final commit object.

## 3. Exact changed-file allowlist

The worker may add only these eleven files:

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

Both `bin` files must have Git mode `100755`; every other file must be `100644`. No
existing file may change. Do not modify plans, reviews, deploy scripts, canonical
config, adapters, agentd, Coordinate, or another test file.

## 4. Fixture executable implementation contract

Implement `p9-3c0-fixture.py` using only the Python standard library.

### CLI and input

- Accept exactly one occurrence of each Claude no-model/no-resume option:
  `-p`, `--verbose`, `--output-format stream-json`, and
  `--include-partial-messages`.
- Option-pair ordering may differ; unknown/duplicate/missing options, positionals,
  `--model`, `--resume`, and dangerous-permission options fail before stdin work.
- Read all stdin once and require one JSON object with the exact key set:
  `contract_version`, `mode`, `quiet_seconds`, `spawn_descendant`.
- Require integer-not-bool `contract_version=1`, mode `complete|hold`,
  integer-not-bool `quiet_seconds=75`, and a real bool `spawn_descendant`.
- Permit descendants only for `mode=hold`. Reject trailing documents and extra keys.

### Runtime behavior

- Validation failure may emit one bounded stderr line and exits nonzero without
  sleeping or spawning.
- After successful validation, emit no stdout/stderr before 75 seconds.
- `complete` sleeps exactly 75 seconds, writes exactly one compact line with
  `{"is_error":false,"result":"fixture complete","subtype":"success","type":"result"}`
  using deterministic compact JSON, then exits `0`.
- `hold` remains silent until SIGTERM/SIGINT and never emits a result/session id.
- With `spawn_descendant=true`, start exactly one fixed argv descendant such as
  `['/bin/sleep', '300']`, no shell, no daemonization, and terminate/reap it during
  signal cleanup. It remains in the transient unit cgroup.
- Signal handling stays silent and bounded.
- No socket/network client, credential/environment read, home/config read, provider
  binary, shell, dynamic command, or file mutation is permitted.

Expose importable pure functions for argv validation, envelope parsing, and execution
decision. The execution function must accept injected sleep/emitter/descendant hooks so
tests use a virtual clock; production entrypoint must always use the real 75 seconds
and expose no duration override.

## 5. Secret-free agent config

`agents.fixture.toml` must contain `[defaults]` and exactly two `[[agents]]` entries:
`p9-3c-fixture-e1` and `p9-3c-fixture-e2`.

Exact common values:

- `agentd_mode = true`;
- `adapter = "claude"`;
- `timeout = 240`;
- `first_byte_timeout = 90`;
- `activity_timeout = 90`;
- `system_prompt = ""`;
- no token/token_env/model/resume/dangerous-permission/provider/Discord/KOOK fields.

Use each of these unique committed placeholders exactly once:

- `__P9C0_COORDINATOR_CLI__`;
- `__P9C0_COORDINATOR_DB__`;
- `__P9C0_WORK_DIR__`;
- `__P9C0_E1_CONTEXT_DB__`;
- `__P9C0_E2_CONTEXT_DB__`;
- `__P9C0_E1_CLAUDE_BIN__`;
- `__P9C0_E2_CLAUDE_BIN__`.

The rendered E1/E2 context DBs must be distinct. `render` replaces every placeholder
once, refuses missing/duplicate/leftover markers, writes mode `0600`, and calls the
existing config loader with `require_token=False` for both agents. It must then assert
that both resolved `claude_bin` values are the same expected absolute fixture
executable, so `_first_existing_command` cannot fall back to real Claude.

## 6. Immutable executor authorities

Every non-empty executor file must use:

- `[registry].id = "p9-3c0-fixture-executors"`;
- one `[[executor_definitions]]` with id `p9-3c-local-fixture`,
  `provider="local-fixture"`, `adapter="claude"`, and
  `capabilities=["coding"]`;
- managed E1/E2 entries with display names `P9-3C Fixture E1/E2`, exact
  `executor_definition_id="p9-3c-local-fixture"`, and
  `runner_profile_id` equal to each agent id;
- E1 parser-only `discord_user_id="1"` and E2 parser-only
  `discord_user_id="2"`.

Exact versions/states:

- `v1-disabled`: `[registry].version=1`, both bindings `enabled=false`;
- `v2-enabled`: `[registry].version=2`, both bindings `enabled=true`;
- `v3-disabled`: `[registry].version=3`, both bindings `enabled=false`;
- `v4-empty`: `[registry].version=4`, no definitions, agents, or bindings.

All parse through `load_authority`, have pairwise-distinct canonical executor catalog
hashes, and remain immutable. Values `"1"`/`"2"` are schema placeholders, not routing
identities. The runbook must forbid these files as inputs to `workspace agent sync`,
roster verification, or deploy-time roster projection. They are only future isolated
inputs to `coordinate runtime executor sync --source` after Package 3 approval.

## 7. Immutable capacity authorities

- `capacity.fixture.v1.toml`: `[capacity_registry].id` equals
  `p9-3c0-fixture-capacity`, version `1`, and E1/E2 each have
  `max_concurrent_jobs=1`.
- `capacity.fixture.v2-empty.toml`: same id, version `2`, no policies.
- Both parse through `load_capacity_authority` and have distinct hashes.

The documented future staging order is exactly:

1. executor v1 disabled;
2. capacity v1;
3. executor v2 enabled;
4. executor v3 disabled;
5. capacity v2 empty;
6. executor v4 empty.

Package 2 code/tests parse and assert this order but never execute it.

## 8. Exact helper CLI and ledger contract

Implement `p9-3c0-unit.sh` as a Bash helper with sourceable functions and an ordinary
`[[ ${BASH_SOURCE[0]} == "$0" ]]` main guard. No test flag, backend override, environment
bypass, or eval is allowed.

The only subcommands are `render`, `preflight`, `start`, `status`, `stop`, and
`cleanup`. Common identity flags are:

- `--state-root <absolute-isolated-root>`;
- `--run-id <lowercase-alnum-and-hyphen>`;
- `--agent-id p9-3c-fixture-e1|p9-3c-fixture-e2` where applicable.

`render` additionally accepts reviewed absolute values for fixture executable,
Coordinate wrapper, Coordinate DB, work directory, Python executable, and repo root.
It creates one run directory below state root, records all values, and renders one
run-specific config. Work/state/context/Coordinate DB paths must resolve inside the
isolated root. Fixture/Python/repo/wrapper paths must be absolute and match the values
subsequent operations read from the ledger.

`start` additionally requires `--mode complete|hold`, `--user`, and `--group`. It
records the declared mode. `status`, `stop`, and `cleanup` accept no caller-supplied
unit or PID; they derive exact identity from the ledger.

For a hold row, `stop` additionally requires
`--fixture-start-monotonic-ms <unsigned-decimal>` and
`--evidence-run-id <same-run-id>`. Read the current monotonic clock from a replaceable
shell function, validate start <= now, compute integer elapsed milliseconds, and
record start/requested-stop/actual-stop/elapsed/verdict. The accepted interval is
`75000 <= elapsed < 85000`; operator target is `80000`. Missing, mismatched,
non-decimal, future, or late evidence is a failed timing row. Regardless of timing
verdict, exact unit stop, bounded inactive wait, and cgroup cleanup proof run first;
only then may `stop` return nonzero.

The boundary is opaque Package 3 evidence. This helper must not claim it observed the
request. Package 3 must later prove the boundary is anchored at or before
`ClaudeAdapter._run`'s first-byte clock and bound the offset; this bootstrap does not
authorize that execution.

Every mutating operation holds one exclusive `flock`. State directories are `0700`;
ledger/config/evidence files are `0600`. The append-only bounded ledger binds run,
agent, exact unit, paths, unit start, mode, MainPID, ControlGroup, timing evidence,
sandbox verdict, stop verdict, and cleanup verdict. Maximum two units per run. Never
use wildcard units, `pkill`, guessed PID, process-name matching, `eval`, or unbounded
`rm -rf`.

## 9. Isolation, systemd, and cleanup

Fail before usable start when any condition is false:

- Linux/systemd and required commands are available;
- Coordinate DB is not `/var/lib/coordinate/coord.sqlite3`;
- wrapper is not `/usr/local/bin/coord-local`;
- fixture ids are absent from canonical `config/agent-registry.toml`;
- rendered config paths/timeouts/binaries are exact;
- isolated read-only Coordinate health/list evidence is clean;
- namespace/unit is quiescent and no unrelated unit occupies it;
- mandatory sandbox properties are accepted.

Mandatory transient-unit properties are exact User/Group/WorkingDirectory,
`RuntimeMaxSec=300`, bounded `TimeoutStopSec`, `KillMode=control-group`,
`IPAddressDeny=any`, `RestrictAddressFamilies=AF_UNIX`, `NoNewPrivileges=yes`,
`PrivateTmp=yes`, `ProtectSystem=strict`, restrictive home protection,
`ReadWritePaths=<isolated-root>`, and `UMask=0077`. Use `env -i` with only a minimal
explicit environment; no Anthropic/OpenAI/Discord/KOOK/AWS/Azure/Google/Kimi/GLM/
DeepSeek/Minimax credential variables may survive.

`RuntimeMaxSec=300` is `timeout=240` plus a 60-second shutdown/cleanup ceiling, never a
valid hold duration. Unsupported network isolation appends bounded failure evidence
and refuses start; no downgrade or packet-capture substitute.

Start exactly one `python -m multinexus.agentd --config <rendered> --agent <id>` in the
exact unit, without `--recoverable`. Post-start property mismatch triggers exact stop
and nonzero. Stop uses only the ledger unit, waits boundedly for inactive, and proves
the recorded cgroup is absent or has empty `cgroup.procs`. Cleanup requires that proof,
deletes only ledger-listed run files, and preserves bounded evidence.

## 10. Runbook requirements

The runbook has three separated tracks:

1. Package 2 local/inert deployment verification only.
2. Unauthorized-until-approved Package 3 isolated preview with immutable sync order,
   target request, 75/80/85/90 timing boundaries, exact unit lifecycle, evidence, and
   cleanup.
3. P9-3C1 production outline that explicitly says the helper rejects the production
   DB/wrapper and provides no bypass.

Use current CLI spelling: `coordinate runner add`,
`coordinate runtime agent register`, `coordinate runtime executor sync --source`,
`coordinate runtime capacity sync --source`, and
`coordinate runtime request submit --target-agent`. Never recommend direct SQLite
writes/deletes, mutable authority editing, roster sync of fixture executor files,
wildcards, or canonical authority mutation.

## 11. Required tests

`tests/test_p9_3c0_fixture_assets.py` must cover the full plan matrix without real
sleep, systemd, SSH, network, production paths, or provider calls.

At minimum prove:

- exact fixture argv/input types/key set and all fail-closed cases;
- virtual complete/hold/signal/descendant behavior and zero pre-boundary output;
- static absence of network/provider/credential/config access in the executable;
- render refuses raw/partial/duplicate placeholders and loads both agents with exact
  path/timeout/context isolation and no real Claude fallback;
- every authority parses, hashes distinctly, has exact ids/versions/states/order;
- synthetic ids are exact/unique, absent/non-colliding with canonical authority, and
  runbook/helper never routes fixture executor files to workspace/roster sync;
- helper grammar/path/production DB/wrapper/lock/two-unit gates;
- sourced-function tests capture exact systemd argv/properties/env, post-start cleanup,
  status, exact stop, inactive wait, and cgroup proof;
- hold timing accepts `75000`, target `80000`, and `84999`, rejects missing/mismatch/
  future/non-decimal/`85000+`, and still performs cleanup before failure;
- network-property failure records ledger evidence and refuses start;
- cleanup cannot precede cgroup proof or escape ledger paths;
- deployment static contract copies `multinexus/fixture/` to
  `/opt/multinexus/multinexus/fixture/` but invokes nothing automatically;
- canonical configs, deploy scripts, runtime packages, and Coordinate remain unchanged.

## 12. Verification and baseline

Use the existing environment only; do not install or upgrade dependencies.

Baseline at the exact implementation base:

- fixture-adjacent focused suite: `89 passed, 20 subtests passed`;
- full suite: `663 passed, 2 skipped, 55 subtests passed` from `665 collected`.

Run and report:

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
git diff --name-status 7e887cbc24a7e38f268e6eb8ba656ac69c11905d...HEAD
git status --porcelain=v2
```

## 13. Completion and stop contract

Produce exactly one local commit and report its SHA, exact file modes/list/stat,
focused/full counts and durations, compile/bash/diff results, architecture summary,
residual risks, session id, JSONL path, outer sonnet, and provider-native Kimi evidence.

Do not push, merge, deploy, SSH, run systemd, sync catalogs, create jobs/leases, access
production, or edit harness docs. Stop instead of widening scope if any existing file
or twelfth file must change, a real 75-second/systemd/network/provider path is needed,
the helper needs a production bypass, or provider JSONL is not Kimi.

After worker completion, Codex must independently verify JSONL, working tree/index/HEAD
blobs, commit ancestry, file modes, tests, and exact changed-file set. A fresh
exact-revision result reviewer is required before merge or inert deployment.

`P9_3C0_FIXTURE_PACKAGE2_BOOTSTRAP_PENDING_INDEPENDENT_REVIEW`
