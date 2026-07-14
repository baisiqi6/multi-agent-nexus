# P9-3C0 Fixture Plan Review — Round 1

Reviewer: Codex architect/reviewer  
Verdict: **CHANGES_REQUESTED**  
Reviewed measurement SHA-256:
`3e07a9ca03f12351f6e27488827ee7d25e52a36d22db751122155a641ae5c2a2`  
Reviewed plan SHA-256:
`7c5ae032ccff0837252cfc3169caac9f371045141c70a13c1e779498aa62e62a`

The assessment conclusion `implementation_plan_required` is correct, but the plan is
not implementation-safe yet. This review authorizes documentation correction only; it
does not authorize code, tests, catalog mutation, jobs/leases, deployment, restart, or
production fixture activation.

## Required corrections

### P1-1 — Candidate Coordinate paths and schema work are invented

The repository uses `src/coordinate/executor_capacity.py`,
`src/coordinate/execution_cli.py`, `tests/test_executor_capacity.py`, and
`tests/test_execution_cli.py`. There is no proposed `coordinate/model.py`,
`coordinate/cli/capacity.py`, or `tests/unit/executor_capacity_test.py` path, and the
existing `executor_capacity_policies.source_id` already expresses ownership. Do not add
an `owner_source_id` column without evidence. Scope Package 1 to the existing module and
tests; add doctor/projection work only if a concrete existing check is extended.

### P1-2 — Capacity activation/cleanup order is unsafe and internally inconsistent

With union coverage, an enabled fixture binding cannot exist without a policy, while a
fixture policy should not be accepted for an arbitrary unknown id. Use forward-only
staging through the existing executor binding `enabled` field:

1. register runtime agents/runner profiles;
2. sync fixture executor source v1 with E1/E2 bindings `enabled=false`;
3. sync fixture capacity source v1 with E1/E2 policies; permit policies for existing
   disabled typed bindings, but reject policy ids with no typed binding;
4. verify policy ownership/coverage;
5. sync fixture executor source v2 with E1/E2 `enabled=true`.

Cleanup must reverse this safely after all fixture jobs are terminal:

1. executor source v3 disables E1/E2;
2. capacity source v2 is empty;
3. executor source v4 is empty.

Each version/hash mutation must be forward-only, transactionally fail-closed, and
guarded against in-flight typed jobs/active leases. The current plan removes capacity
before disabling enabled bindings, which would violate its own union invariant.

### P1-3 — Quiet-row JSONL would emit progress and use the wrong timeout

An early Claude `system/init` event makes `ClaudeAdapter` emit session progress and
switch from `first_byte_timeout` to `activity_timeout`, invalidating the no-output/no-
progress quiet row. The fixture must produce **zero stdout/stderr** during the 75-second
window and only emit a final `type=result` afterward. Set total and first-byte timeouts
above the bounded quiet duration; do not emit an init event before the evidence window.
The 75 seconds derives from the current 30-second renew interval and proves renewals at
approximately 30 and 60 seconds.

### P1-4 — Fixture CLI modes and crash model do not match the real adapter path

`ClaudeAdapter` passes its fixed Claude CLI arguments to the executable; it cannot append
the plan's custom `--mode` flags through `claude_bin`. Make the fixture accept/validate
the actual Claude arguments and read a strict, bounded fixture control envelope from
stdin, for example `contract_version`, `mode`, and `quiet_seconds`. The external crash
row must stop the exact transient agentd systemd unit; an adapter child calling
`os._exit(1)` leaves agentd alive and normally produces a failed report, so it is not
evidence for unreported lease expiry/recovery. Use bounded `complete` and `hold`
behaviors; an optional descendant is only for cgroup cleanup proof.

### P1-5 — Authority TOML field names are wrong

Use the actual parsers:

- executor: `[registry] id/version`, `[[executor_definitions]]
  id/provider/adapter/capabilities`, and `[[agents]]
  id/executor_definition_id/runner_profile_id/enabled`;
- capacity: `[capacity_registry] id/version` and `[[executor_capacities]]
  agent_id/max_concurrent_jobs`.

One definition such as `p9-3c-local-fixture` with `provider="local-fixture"`,
`adapter="claude"`, and sorted capabilities may bind both E1/E2. Do not invent
`executor_id`, `capacity`, `capacity_policies`, or `max_concurrent` fields.

### P1-6 — Local verification changes lease timing and conflates child failure with crash

Do not say “调低 lease timeout” as production/sidecar evidence. The accepted lease
contract currently carries TTL 120 seconds and renew interval 30 seconds. Quiet renewal
uses the returned envelope. Expiry/reap/recovery must stop the exact agentd transient
unit, await its cgroup cleanup, wait past the recorded `expires_at`, invoke explicit
global reap only under global quiescence, then start an exact recovery unit with
`--recoverable --recovery-reason ... --prior-process-stopped`. Stale attempt N checks
use the old lease/token only after N+1 is established.

### P1-7 — Queue freeze and zero-network evidence are procedural, not fail-closed

State why fixture intake is isolated: fixture ids are absent from the canonical Discord
roster/routed catalog and requests are accepted only through the operator helper's exact
`--target-agent` path. The helper must use an exclusive run lock/ledger and refuse
unknown fixture ids. For provider isolation, launch transient units with a minimal
environment, explicit credential unsets, and a verified systemd network sandbox (for
example `IPAddressDeny=any`/restricted address families if supported by preflight).
Packet capture may be supplementary, not the primary gate.

### P1-8 — P9-3C0 and P9-3C1 authorization boundaries are mixed

After a separately approved implementation, P9-3C0 may run local/isolated sidecar jobs
and leases to close the fixture itself. Production catalog activation and the production
concurrency/recovery matrix remain P9-3C1 and require the existing exact-revision gate.
Do not say P9-3C0 closeout itself activates production fixture sources. Inert deployment
may be separately approved, with no fixture units/sources/jobs active by default.

### P1-9 — Implementation must be split by repository and reviewed sequentially

Generate separate worker bootstraps/branches for:

1. Coordinate capacity-source decoupling;
2. MultiNexus fixture assets/operator helper after Coordinate result acceptance;
3. local/isolated fixture verification and closeout.

Each package receives worker implementation, Codex result review, focused/full tests,
and its own deploy gate. Do not give one worker simultaneous mutation authority over
both repositories.

### P1-10 — Runtime agent residue decision must be explicit and consistent

There is no supported unregister CLI. For this scope, accept uniquely namespaced dormant
fixture agent/runner rows as non-active audit/config residue after bindings and policies
are removed, and verify they cannot claim typed work. A future unregister feature is a
separate roadmap item; direct SQLite deletion remains forbidden. Do not claim “no
fixture runtime agent registered” after a completed activation/cleanup cycle.

## Acceptance for Round 2

Round 2 may approve only an exact revision whose measurement and plan:

- retain `implementation_plan_required`;
- use real files, symbols, schemas, CLI semantics, lease timings, and systemd handle;
- specify the disabled-binding activation/cleanup sequence;
- produce zero output/progress during the quiet evidence window;
- split Coordinate, MultiNexus, and verification into sequential bootstraps;
- preserve the P9-3C1 production authorization boundary.

## Reviewer normalization after worker correction

After the bounded Kimi correction, the Codex reviewer made only documentation-level
normalizations required by the findings above: removed nonexistent/optional Coordinate
paths, changed union validation to a pre-write proposed-state check, fixed the exact
executor/capacity source version sequence, made capacity cleanup depend on disabled
bindings rather than already-removed bindings, converted descendant behavior to an
optional control-envelope flag, and required `claude_bin` placeholders to be rendered
to an absolute path. These edits still authorize no implementation or runtime action.
