# P9-2A Executor Identity Registry — Independent Plan Review Round 2

## Review identity

- Provider / model: `kimi-code/kimi-for-coding-highspeed`
- JSONL session id: `019f5a13-d353-7000-802e-caf3d34d0e62`
- Reviewer role: independent plan reviewer only; no implementation, file mutation,
  deployment, production DB access, or lifecycle action.
- Review date: 2026-07-13

## Reviewed artifact

- Plan: `docs/project-harness/tasks/p9-2a-executor-identity-registry/plan.md`
- Exact SHA-256:
  `0f3fa12469b1a5587c94e386c0da13e32111383ccdc640c227e7564ba7f0ec45`
- Superseding plan-ready event: `3dc704af-f627-4953-a5bc-5721f67ca3cf`
- Superseded plan-ready event: `a73556cf-5960-4542-b1c8-73bc771ed109`
- Round-2 review-requested event: `ff6b03ed-f211-41f2-ad61-64c013cbdb8e`
- Plan-approved event: `6db26c20-496a-4353-bed3-31bd6b61a432`

## Verdict

`approve`

The reviewer confirmed that both Round-1 must-fix findings are closed and that the
plan is sufficiently bounded and explicit to generate the worker bootstrap.

## Accepted reasoning

- The P9-2A identity/authority package is cleanly separated from P9-2B selection,
  P9-3 leases/capacity, and P9-4 heartbeat/JSONL semantics.
- Schema v12 remains an additive minimum: catalog source, logical definitions, and
  concrete instance bindings, with no alteration to existing jobs/agents/profiles.
- Both canonical hashes derive from the same TOML authority. Executor keys are
  excluded from existing roster bytes, and Coordinate reads/canonicalizes that TOML
  directly instead of accepting a MultiNexus-generated JSON projection.
- Managed P9-2A binding authority is implementable: `runner_profile_id == agent_id`,
  adapter equals `AgentConfig.adapter`, and provider is a bounded non-executable audit
  label.
- Typed submit/replay/claim semantics remain fail-closed while legacy exact targets
  are visibly untyped and excluded from future automatic routing.
- The tests and rollout cover atomic/zero-mutation failures, exact canonical bytes,
  multi-source ownership, deploy parity, a real typed job, delivery, tamper rejection,
  rollback, doctor, and receipt closeout.

## Non-blocking recommendations and architect disposition

1. The byte-identical executor fixture and pinned SHA are already mandatory in both
   repositories; keep them in the worker bootstrap.
2. The unchanged-roster-hash probe is already required; keep an explicit before/after
   assertion.
3. Add negative parsing cases for path separators, shell metacharacters, and
   command-like provider/adapter labels.
4. Require a bounded machine-readable claim mismatch error distinct from queue-empty.
5. Implement the in-flight typed-job guard inside the catalog sync transaction using
   an immediate write lock, not as a racy deploy-only preflight.

Current `register_agent()` already creates the same-id runner profile required by the
P9-2A rule; catalog sync must still reject a missing profile. The exact representation
of P9-2B's routing-request marker remains intentionally deferred to the independently
reviewed P9-2B plan.

## Implementation gate

Approved plan revision for worker-bootstrap generation:

```text
0f3fa12469b1a5587c94e386c0da13e32111383ccdc640c227e7564ba7f0ec45
```

---

[agent-report]
action=review.plan
verdict=approve
plan_sha256=0f3fa12469b1a5587c94e386c0da13e32111383ccdc640c227e7564ba7f0ec45
session=019f5a13-d353-7000-802e-caf3d34d0e62
must_fix=0
recommended=5
open_questions=2
