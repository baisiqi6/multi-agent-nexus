# P9-2A Executor Identity Registry — Independent Plan Review Round 1

## Review identity

- Primary reviewer attempt: `zhipu-coding-plan/glm-5.2`
- Primary JSONL session: `019f5a09-51f2-7000-a546-ed3e96722ae7`
- Primary outcome: timed out at the configured 300-second bound without a structured
  verdict; no approval authority was inferred from partial reasoning.
- Authorized fallback reviewer: `kimi-code/kimi-for-coding-highspeed`
- Fallback JSONL session: `019f5a0e-578b-7000-a35f-fcdd2fc0c016`
- Reviewer role: independent plan reviewer only; no file mutation, implementation,
  deployment, production DB access, or lifecycle action.
- Review date: 2026-07-13

## Reviewed artifact

- Plan: `docs/project-harness/tasks/p9-2a-executor-identity-registry/plan.md`
- Round-1 SHA-256:
  `f651648f07493b3915ba19ff83e8d435b39cf7fdbf4fb2c551de2b7f685092d6`
- Plan-ready event: `a73556cf-5960-4542-b1c8-73bc771ed109`
- Plan-review-requested event: `e4ada241-8ad7-44de-a68b-6f452cacfecb`
- Plan-rejected event: `4c51f27c-7554-4515-b02a-17805bfbcc66`
- Split operation: `62175918-ce07-4da5-8bf4-03b9784fb64e`

## Verdict

`changes_requested`

The P9-2A/P9-2B split, additive schema, exact-target binding snapshot, fail-closed
claim semantics, deploy/dogfood matrix, and exclusion of leases/heartbeat were judged
sound. Two findings blocked direct worker-bootstrap generation.

## Must-fix findings

1. Current MultiNexus `AgentConfig` has `id` and `adapter`, but no independent
   `runner_profile_id` or `provider`. The plan required agentd to validate fields for
   which it had no local authority while also saying private `agents.toml` would not
   gain required fields. The plan must define the P9-2A runner-profile rule, adapter
   comparison, and whether provider is executable or informational.
2. `runtime executor sync --source-json` diverged from existing
   `workspace agent sync --source <toml>`. Without an exact intermediate projection
   contract, MultiNexus would become a second catalog serializer and introduce a new
   source-to-DB drift surface. Coordinate should read the same TOML directly or the
   plan must fully specify and verify the intermediate bytes.

## Non-blocking recommendations adopted into the revision

- Specify exact catalog canonical JSON bytes and SHA-256 inputs.
- Define multi-source ownership and preservation behavior.
- Add indexes for foreign-key lookup paths.
- Preserve existing roster projection bytes when executor keys are added.
- Fail catalog mutation with zero DB change while typed jobs for the source are
  pending/claimed; document drain behavior.
- Require P9-2B to use an explicit routing request marker rather than treating every
  null binding as legacy.

## Revision disposition

Round 1 is rejected and cannot authorize implementation. The architect accepted both
must-fix findings and all listed safety clarifications. A new exact SHA and an
independent Round-2 verdict are required before plan approval or worker bootstrap.

---

[agent-report]
action=review.plan
verdict=changes_requested
plan_sha256=f651648f07493b3915ba19ff83e8d435b39cf7fdbf4fb2c551de2b7f685092d6
session=019f5a0e-578b-7000-a35f-fcdd2fc0c016
must_fix=2
recommended=7
