# P9-3C0 Fixture Assessment Bootstrap

Role: planning/measurement worker only  
Authorization: `plan-approval.md`  
Approved plan SHA-256:
`6321e77be6cfd50c82d9c7f995691fb523196c1b3ce238c501eadb4c385f6652`

## Goal

Determine, without production mutation, whether Coordinate/MultiNexus already expose a
safe zero-paid-provider fixture for the five P9-3C0 gates:

1. quiet long-running execution with no provider output;
2. strict typed context/binding/routing/worktree lease;
3. two distinct capacity-1 executor instances;
4. exact child process handle/status/stop with awaited tree cleanup;
5. scoped queue isolation and intake freeze for the fixture executors.

## Read/write boundary

Read both repositories, local tests, CLI help, deploy scripts, runner/agent registries,
and the current P9-3C docs. Production access, if needed, is read-only and limited to
identifiers/status/counts/schema/service metadata; never print payload, prompt, result
text, environment, credentials, or user messages.

The assessment worker may create only:

- `p9-3c0-fixture-measurement.md`;
- `p9-3c0-fixture-plan.md` if implementation or configuration work is required.

Do not modify code, tests, registries, capacity policy, checklist, roadmap, progress,
or lifecycle state. Do not commit/push/deploy/restart, create jobs/leases, run reap, or
invoke a provider.

## Required answers

- Can an existing `generic_subprocess`, adapter fixture, or sidecar path enter the same
  managed MultiNexus worker/renewal/cancellation path without a paid provider?
- Can two fixture executor bindings be created without weakening the canonical
  production catalog or changing real executor capacity?
- Which current API produces the strict context/binding/route/resource authority? If
  plain `job create` is insufficient, cite the exact failure boundary.
- Which exact PID/process-group handle can the Operator stop, and how is termination
  verified without `pkill` or guessed PID?
- How can fixture executor intake be frozen while leaving real executors and user
  traffic untouched?
- Is a code change required? If yes, define the smallest separately reviewable
  implementation package, tests, deploy boundary, rollback, and why a local sidecar is
  insufficient.

## Completion gate

Return `existing_fixture_verified` only with exact files/symbols/commands and focused
local/sidecar evidence. Otherwise return `implementation_plan_required` and a detailed
plan. Either outcome goes to a new independent exact-revision review before any coding
or production bootstrap is generated.
