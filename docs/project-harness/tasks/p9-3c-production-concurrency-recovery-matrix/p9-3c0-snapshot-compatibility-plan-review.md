# P9-3C0 Snapshot/Restore Compatibility Plan Review

## Review identity

- Review type: independent, read-only, exact-revision plan review
- Reviewed MultiNexus commit: `ffa78485ff5a515200b229920237cef52552abe5`
- MultiNexus base: `aec171f22180cc8b7405762ff79cf93c155cc243`
- Coordinate baseline: `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`
- Reviewer runtime: Claude Code outer `sonnet`; provider-native stream reported
  `message.model=kimi-for-coding`
- Reviewer session: `3e22fa0d-147f-4511-ab67-83ab31916965`

The reviewed commit changes exactly:

- `p9-3c0-snapshot-compatibility-measurement.md`
- `p9-3c0-snapshot-compatibility-plan.md`

The plan worktree was clean before and after review. The reviewer made no file,
commit, deployment, service, or database changes.

## Evidence checked

The reviewer read the reviewed documents and the current implementations/tests in:

- Coordinate `src/coordinate/executor_capacity.py`
- Coordinate `src/coordinate/schema.py`
- Coordinate `tests/test_executor_capacity.py`
- MultiNexus `scripts/deploy-server.sh`
- MultiNexus `scripts/capacity_snapshot_helper.py`
- MultiNexus `tests/test_deploy_contract.py`

Executed baselines:

- Coordinate capacity suite: `91 passed`
- MultiNexus deploy-contract suite: `15 passed`

The review independently confirmed the current v1 single-source rejection, the
capture-failure cleanup-only branch, later-failure restore path, hard-coded canonical
target, prior-absence behavior, capacity-table constraints, and fake deploy-contract
snapshot gap.

## Findings

### Blocking findings

No blocking findings.

### Implementation guidance carried into the bootstrap

1. Extend the existing C5-3 pre-delete validation to the full multi-source projection;
   do not present it as a new recovery rule.
2. Replace the v1 target-only equality check with Package 1 global union coverage
   across every source.
3. Mirror `_all_typed_agent_ids` semantics exactly: policies may reference enabled or
   disabled typed bindings, while every enabled typed binding must be covered.
4. The MultiNexus fake must reproduce at least v2 exact key-shape, digest,
   `preserved_state`, witness-drift, prior-absence, and zero-write rejection semantics;
   a superficial envelope-only fake is insufficient.
5. Add an explicit capture case for target absence with a non-target source that owns
   zero policies.
6. Record in the operator runbook that the prohibition on manual production restore is
   procedural; production verification for this package is capture/readback only.

### Accepted residual risks

- An active lease on any source blocks canonical rollback.
- Non-target witness drift converts normal rollback into loud recovery failure.
- A v1 artifact fails closed after second-source activation.
- Package 2/3 and P9-3C1 remain blocked by the compatibility implementation,
  independent result review, isolated restore proof, and their own activation gates.

## Verdict

`APPROVED_FOR_P9_3C0_SNAPSHOT_COMPATIBILITY_IMPLEMENTATION_BOOTSTRAP`
