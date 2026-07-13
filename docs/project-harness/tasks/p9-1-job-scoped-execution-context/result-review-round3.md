# P9-1 Codex result review — Round 3

Date: 2026-07-13  
Reviewer: Codex operator/reviewer  
Correction worker: Kimi `kimi-code/kimi-for-coding-highspeed`  
Correction JSONL session: `019f59d3-3363-7000-8e18-914aba5f4b76`  
Verdict: **REJECT — one narrow handoff-authority correction required**

## Independently reproduced passing evidence

- Coordinate focused P9-1 suites: `318 passed`.
- Coordinate full suite: `1942 passed, 449 subtests passed`, plus exactly the nine
  historical CLI/AST failures.
- MultiNexus focused suites: `155 passed, 2 skipped`.
- MultiNexus full suite: `448 passed, 2 skipped, 26 subtests passed`.
- Both repositories pass `compileall` and `git diff --check`.
- Both fixture files remain byte-identical at
  `975be64ca2cba84530cf969038cce4c5fb74df0b5f33aed86df9352ec9d12786`.
- Adversarial probes now reject unsafe relative host profiles, pre-upgrade jobs with
  missing task mirrors without mutation, and mismatched claim workspace/agent/attempt
  envelopes.

## Must-fix findings

### R3-1 — prepared handoff loses the authoritative host profile

`prepare_handoff()` now stores
`_materialize_handoff_profile(workspace, execution_profile)` directly as
`payload.execution_profile`. That helper returns only `workspace_path` and
`harness_root`.

Before P9-1, a targeted handoff stored the complete
`WorkspaceHostProfile.to_dict()` value, including `workspace_id`, `host_id`,
`harnessctl_path`, `coordinator_cli_path`, `coordinator_db_path`, `shell`, and
`metadata`. Untargeted handoffs stored `execution_profile=null`. The new behavior
drops those fields and changes the null compatibility contract. The loss propagates
through `latest_prepared_handoff_bootstrap()` and `assignment accept` output.

This contradicts the approved requirement that `worker.handoff.prepared` remain the
authoritative execution profile.

Required correction:

- Preserve the complete existing profile object and its untargeted `null` semantics.
- For a targeted profile, copy `execution_profile.to_dict()` and materialize only the
  canonical `workspace_path`/`harness_root` values into that copy.
- Use a separate two-field rendering context when no host profile exists; do not
  rewrite the durable compatibility field to a synthetic profile.
- Add regression tests for preserved host/CLI/DB/shell/metadata fields and the
  untargeted `null` case, while retaining the harness fallback test.

### R3-2 — MultiNexus accepts a partial v1 handoff block

`parse_coordinator_handoff()` accepts `context_version=1` with a valid
`workspace_path` but no `harness_root`. The producer now guarantees a materialized
harness path, and Round 2 explicitly required rejection of malformed/partial v1
blocks. Accepting the partial block weakens the producer/consumer contract.

Required correction:

- A v1 handoff must contain both non-empty, host-absolute `workspace_path` and
  `harness_root`; reject a missing or invalid value.
- Make `_has_v1_handoff_authority()` reflect the same complete requirement.
- Add parser tests for missing workspace, missing harness, relative workspace,
  relative harness, and a valid quoted Windows/POSIX block.

### R3-3 — managed handoff authority check is defined but not enforced

`CoordinatorHandoffMixin._has_v1_handoff_authority()` is unused. In `agentd_mode`, a
legacy/partial handoff can reach `execute_assignment_accept()` before any v1 authority
check and can proceed when assignment-accept returns bootstrap text. The review path
also proceeds without requiring v1 authority. This violates the approved fail-closed
managed-mode boundary and can mutate assignment state before rejecting malformed
authority.

Required correction:

- In `agentd_mode`, reject a missing/incomplete v1 handoff before assignment accept,
  bootstrap reads, agentd submission, or provider invocation.
- Emit exactly one bounded blocker report and return handled; legacy non-agentd mode
  remains compatible.
- Add worker and reviewer integration tests proving no assignment accept, SQLite
  fallback/bootstrap read, agentd submission, or provider invocation occurs for a
  legacy/partial managed handoff.

Update `progress.md` to describe Round 3 accurately. Rerun the targeted/full/static/
fixture gates and stop for Codex Round 4. Do not commit, push, deploy, mutate lifecycle,
write a receipt, or touch production.
