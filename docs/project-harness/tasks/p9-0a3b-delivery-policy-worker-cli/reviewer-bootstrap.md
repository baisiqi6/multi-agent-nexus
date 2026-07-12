# P9-0A3b Plan Reviewer Bootstrap — Round 1

This source-controlled bootstrap overrides the generic text emitted by
`worker.handoff.prepared` event `0a0f7fdd-98f5-435c-b27c-a9c5b7bb9e80` wherever
paths or permissions differ.

## Exact authority

- Review only:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a3b-delivery-policy-worker-cli/plan.md`.
- Required plan SHA-256:
  `5a9438c345a67a4fb7d73ce4e7cade6f951f9b8da5bf46567b4270adaa153a2f`.
- Plan commit: `7c3137d`.
- Coordinate read-only snapshot:
  `/Users/yinxin/projects/coordinate` at
  `533ffcb1be17c6a26e8d5acf31e9c3c05da1ef63`.
- MultiNexus review checkout: `/Users/yinxin/projects/multinexus`.

There is no `openspec/changes/p9-0a3b-delivery-policy-worker-cli`. `/opt/multinexus`
and `feature/multi-bot` are control/deploy metadata, not review checkout authority.

## Role and permissions

- Independent plan reviewer only; never act as coding worker.
- Strictly read-only: no edits, formatting, commit, push, deploy, lifecycle, worktree,
  branch switch, live DB/delivery/pump, process, GitHub, or SSH mutation.
- Read-only source/AST/hash/test commands are allowed. Run Coordinate tests only from
  `/Users/yinxin/projects/coordinate`.
- Do not approve a different plan hash, and do not infer implementation authorization.

## Required adversarial review

1. Verify current identities: Coordinate `533ffcb...`, root 1,590 lines, fixture
   `fbdb5064...`, contract 21/75/99, focused 382, and full 1,467.
2. Verify exact scope from current code: ten leaves and 114 handler lines = delivery 56
   + policy 44 + worker 14; all registration remains one contiguous range after job and
   before runtime.
3. Challenge whether one `register_delivery_commands` and one `delivery_cli` authority
   preserve public ordering without hiding an unstable service boundary.
4. Verify root must retain `BusError`, `PolicyError`, `json`, `sys`, `_conn`,
   `_print_json`, and `row_to_dict`; reject over-aggressive import cleanup.
5. Verify the five-layer rewind cannot self-bless fixture drift:
   `fbdb5064...` -> `dde4c0d7...` -> `adddac8...` -> `652a77d5...` -> `83c4c181...`.
6. Verify permanent handler proof uses the accepted canonical AST projection, not
   `git show`, repository history, whole-FunctionDef `ast.dump`, or `ast.unparse`.
7. Challenge delivery/worker isolation: mocks must prevent real DB open, send, pump,
   recover-sending, platform access, stderr side effects, or an unbounded worker loop.
8. Confirm `BusError`/`PolicyError` dispatch, exact `sys.stderr` forwarding, worker
   `once -> max_iterations=1`, and all JSON parsing paths remain testable.
9. Treat delivery `5eed424d...` as pre-existing Slice 4/P9 evidence; reject any bus,
   daemon, retry, or recovery behavior change in this structural package.
10. Reject P9-0A4/P9-0A5/Slice 4 scope creep and any path outside the approved plan.

## Required verdict

Return must-fix findings and clearly labeled nonblocking notes. End with exactly one
block:

```text
[agent-report]
decision=approve|reject
workspace_id=discord-nexus
task_id=p9-0a3b-delivery-policy-worker-cli
summary="..."
```

An approval must explicitly name the exact reviewed SHA-256 above.
