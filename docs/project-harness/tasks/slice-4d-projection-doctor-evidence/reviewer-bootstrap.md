# Reviewer Bootstrap: slice-4d-projection-doctor-evidence

## Session startup

This is an independent **plan review**, not implementation. Work strictly read-only
in the local MultiNexus checkout. Do not create or switch branches/worktrees and do
not modify, commit, push, deploy, or invoke lifecycle transitions.

Read the canonical plan and project boundaries:

```bash
cat docs/project-harness/tasks/slice-4d-projection-doctor-evidence/plan.md
cat docs/project-harness/scope.md
cat docs/project-harness/architecture.md
cat docs/project-harness/domain-model.md
```

You may inspect the current Coordinate implementation and tests read-only at
`/Users/yinxin/projects/coordinate` to verify that the proposed boundaries and test
matrix match reality.

## Review identity

- Workspace: `discord-nexus`
- Task: `slice-4d-projection-doctor-evidence`
- Role: independent non-Codex plan reviewer
- Plan commit: `892dd78e714041e8d9546d1b9c42c8066d02e254`
- Exact plan SHA-256:
  `dbe4d029b5bb0272a0002a494fb24b9bb8dcf7e31247841c7059bfb9087f8a1a`
- Coordinate implementation start: `a21d946e4d6be78f3f481d38eb2571229a4d3a9f`
- Review request event: `c699acfe-489c-4573-aa75-33d66178f4be`

Before reviewing, independently compute the plan SHA-256. Reject the review as stale
if it differs from the exact value above.

## Required red-team focus

Evaluate whether the plan is complete, internally consistent, testable, and aligned
with the existing architecture. In particular, challenge:

1. whether one read-only collector can inspect registry, split-operation, mirror, and
   receipt authorities without importing mutation owners or creating another source
   of truth;
2. whether every finding has an unambiguous severity, authority, evidence shape,
   deterministic ordering, and safe `repairable`/`next_action` behavior;
3. whether file-pending, orphan, unsupported, drifted, conflicting, and event-mismatch
   split-operation states are distinguished without guessing missing intent;
4. whether mirror ordering by `events.rowid` correctly accepts later legitimate
   lifecycle events and detects regression or cross-task/workspace linkage;
5. whether receipt derivation and `mark-done-preflight` precedence
   `consumed > applied > claimed > authorized` cover duplicates, partial chains,
   conflicts, expiry, supersession, and unknown states while remaining fail-closed;
6. whether registry unreadability is kept separate from proven mismatch, overrides
   are evaluated at the correct time, and `agents_json` stays only a compatibility
   projection;
7. whether adding projection errors to `workspace doctor` exit behavior is compatible
   and whether `--no-projections` could accidentally bypass a release/deploy gate;
8. whether the no-write proof is strong enough for SQLite and all relevant files,
   including failure paths and dogfood; and
9. whether scope, allowed modules, acceptance cases, rollout, rollback, and production
   evidence are precise enough for a coding worker without architectural invention.

Do not approve merely because the plan is detailed. Reject for any P0/P1 ambiguity
that could change authority, mutation behavior, compatibility, or acceptance. Clearly
separate must-fix findings from optional improvements.

## Output format

Return a concise review followed by exactly one machine-readable block beginning at
the start of its own line:

```text
[agent-report]
decision=approve
workspace_id=discord-nexus
task_id=slice-4d-projection-doctor-evidence
summary="Approved exact plan SHA dbe4d029...; <brief residual notes>"
```

or:

```text
[agent-report]
decision=reject
workspace_id=discord-nexus
task_id=slice-4d-projection-doctor-evidence
reason="<specific must-fix issue(s)>"
summary="Rejected exact plan SHA dbe4d029...; <brief explanation>"
```

## Constraints

- Read-only plan review only; do not edit any file.
- Do not run `assignment accept` or any task/plan lifecycle mutation.
- Do not implement code or generate a worker commit.
- Do not push, deploy, use SSH, or access production state.
- Cite exact plan sections and current-code locations for every must-fix finding.
