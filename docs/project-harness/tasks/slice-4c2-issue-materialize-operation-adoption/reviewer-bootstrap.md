# Reviewer Bootstrap: slice-4c2-issue-materialize-operation-adoption

## Session startup

This is a strictly read-only implementation-plan review. Do not modify files, switch
branches, create a worktree, implement code, commit, push, deploy or accept task
ownership.

Read the exact local plan first:

```bash
cat docs/project-harness/tasks/slice-4c2-issue-materialize-operation-adoption/plan.md
```

Then inspect only the current code needed to verify the plan's factual claims:

```bash
git -C /Users/yinxin/projects/coordinate rev-parse HEAD
sed -n '520,1085p' /Users/yinxin/projects/coordinate/src/coordinate/issues.py
sed -n '1,340p' /Users/yinxin/projects/coordinate/src/coordinate/issue_cli.py
rg -n 'def create_delivery|def create_delivery_for_event' \
  /Users/yinxin/projects/coordinate/src/coordinate/{db.py,policy.py}
```

## Assignment

- Task: `slice-4c2-issue-materialize-operation-adoption`
- Role: independent plan reviewer
- Plan SHA-256:
  `7ed001a5f200109016d79298a5cd5dc86fe995d2964559808e6178db01be7dda`
- Required Coordinate start: `1cbb547d7966c83c198125370f46bddc2d8640c9`
- Required MultiNexus plan commit: `7753c707e70bad9da1088eda2be35a729fdffb52`
- C2 task-create operation: `66616b54-2502-4981-922f-8d18e86e70c5`
- Workspace: `discord-nexus`

## Red-team focus

Review the plan, not code. Request changes for any P0/P1 gap, especially:

- a forked C2 schema/fingerprint/envelope rather than neutral C1 reuse;
- trusting the file host instead of the accepted server triage event;
- inability to preserve the pre-materialize task mirror on rollback;
- plan-ready/materialized/delivery effects outside one transaction;
- ambiguous ledger `record_event_id` or final task `last_event_id` authority;
- retry that repairs a pre-existing event/delivery or resets a sent delivery;
- missing exact persisted-intent checks when platform/destination is absent or changes;
- delivery commit seams that accidentally change existing callers;
- CLI fixture updates that rewrite historical P9/S4-B/C1 baselines;
- tests that cannot deterministically inject every failure step; or
- expansion into issue triage, pump leases, S4-D repair or Phase 9 isolation.

Approve only if the plan is implementable, testable, and makes C2 a true second consumer
of the C1 contract without weakening C1/mark-done/combined materialize behavior.

## Output

Return concise findings ordered P0/P1/P2 and exactly one final block:

```text
[agent-report]
decision=approve
workspace_id=discord-nexus
task_id=slice-4c2-issue-materialize-operation-adoption
summary="Approved. No P0/P1 findings."
```

or:

```text
[agent-report]
decision=reject
workspace_id=discord-nexus
task_id=slice-4c2-issue-materialize-operation-adoption
reason="<specific blocking issue>"
summary="Rejected. <brief explanation>"
```
