# P9-0A2a Coding Worker Supplement — Round 1

This supplement overrides conflicting generic workspace, branch, deployment,
cross-repository, progress-document, or closeout instructions in `worker-bootstrap.md`.

## Authoritative execution identity

- Role: coding worker only. Codex remains architect, operator, and result reviewer.
- Coordinate worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a2a-kimi`
- Required branch: `agents/mac-omp/p9-0a2a-workspace-state-reconcile-cli`
- Required start SHA:
  `947368a4c278aa847b40eea20a7088c5cb28446f`
- Canonical plan (read-only, outside the coding worktree):
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a2a-workspace-state-reconcile-cli/plan.md`
- Approved plan SHA-256:
  `24197103213a6644125f1c6a6528f5b74ce0f1ba594eefa5567e41d8ba0f3598`
- Plan-review artifact (read-only):
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a2a-workspace-state-reconcile-cli/plan-review-round-1.md`
- Coordinate plan-approved event:
  `fd5d063e-7be0-444e-9f6c-4c86e345b925`
- Coordinate worker-handoff event:
  `4bedc79a-7858-4ba9-ad7c-f8d28e2755cd`
- Logical assignment session: `p9-0a2a-kimi-20260712T1008Z`

The primary implementation repository is Coordinate, not MultiNexus. Do not edit the
canonical MultiNexus checkout, its harness, or its generated bootstrap. The Operator
owns assignment lifecycle, delivery, result review, integration, push, and closeout.

## Exact task

Implement the approved plan mechanically:

1. add `src/coordinate/workspace_cli.py` with
   `register_workspace_commands(...)`, `register_reconcile_command(...)`, and exactly
   the 11 approved handlers;
2. keep `coordinate.cli` as the static facade/composition root and direct compatibility
   owner aliases;
3. preserve top-level ordering and all parser/action/help/output/error/DB behavior;
4. change the contract only at the exact 11 leaf `defaults.handler` values;
5. add the structural and boundary tests required by the plan; and
6. remove only imports proven unused after the mechanical move.

Move `HarnessAdapter` to the new owner while keeping `HarnessError` in the root facade,
because `main()` still catches it. Do not use a private `argparse` type annotation if it
creates compatibility or lint friction; an unannotated parameter or stable public
annotation is acceptable without changing behavior.

## Hard scope

Allowed production paths:

- `src/coordinate/cli.py`
- `src/coordinate/workspace_cli.py`

Allowed test/contract paths:

- `tests/test_cli_contract.py` only if needed for the exact structural delta verifier
- `tests/fixtures/cli_contract.json`
- `tests/test_workspace_cli.py`
- `tests/test_cli.py` only for an otherwise impossible narrow compatibility assertion

If another path appears necessary, stop and report a blocker. Do not modify docs,
packaging, schema, services, harness files, `.qoder/`, configuration, or secrets.

## Required protocol

Before edits, verify `pwd`, branch, start SHA, clean worktree, plan hash, 231 focused
tests, and 1,366 full tests. Use `PYTHONDONTWRITEBYTECODE=1` for tests.

After implementation run, at minimum:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_workspace_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_agent_registry tests.test_doctor tests.test_reconcile
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Also prove the exact structural contract delta, 21/75/99 counts, root alias identities,
clean import orders, no `workspace_cli -> cli` backedge, no stale root handler bodies,
and exact changed paths. The contract verifier must compare old/new structures and
allow only the 11 explicit path-to-handler mappings; fixture regeneration alone is not
evidence.

Create one local commit after all validation. Do not amend, push, merge, deploy, restart,
SSH, invoke another agent, touch live DB/delivery/runtime state, call harness lifecycle,
or request/perform closeout. Return the commit SHA, test results, contract evidence,
remaining risks, exact files, and exactly one terminal `[agent-report]` block with
`action=done` or `action=blocker`.
