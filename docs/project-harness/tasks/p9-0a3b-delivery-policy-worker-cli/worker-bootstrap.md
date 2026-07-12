# P9-0A3b Worker Bootstrap

This source-controlled bootstrap supersedes the generic text emitted by
`worker.handoff.prepared` event `ab671233-1fe2-40e7-817b-6850e53124c2` wherever
paths or permissions differ.

## Authority

- Task: `p9-0a3b-delivery-policy-worker-cli`.
- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a3b-delivery-policy-worker-cli/plan.md`.
- Required plan SHA-256:
  `5a9438c345a67a4fb7d73ce4e7cade6f951f9b8da5bf46567b4270adaa153a2f`.
- Plan review:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a3b-delivery-policy-worker-cli/plan-review-round-1.md`.
- Plan approval event: `c4d46ce9-a968-4152-b430-d66942097c57`.
- Coordinate start: `533ffcb1be17c6a26e8d5acf31e9c3c05da1ef63`.
- Worker checkout:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a3b-kimi`.
- Required branch: `agents/mac-omp/p9-0a3b-delivery-policy-worker-cli`.

The implementation repository is Coordinate, not MultiNexus. Edit only the isolated
Coordinate checkout above; never edit either canonical checkout under
`/Users/yinxin/projects`.

## Startup gate

Before editing, verify:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
shasum -a 256 /Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a3b-delivery-policy-worker-cli/plan.md
```

Stop and report a blocker if checkout, branch, start commit, or plan SHA differs. Read
the full approved plan and review artifact before implementation.

## Authorized implementation

Perform only P9-0A3b:

- add `src/coordinate/delivery_cli.py` with a docstring naming delivery/policy/worker,
  one `register_delivery_commands`, and exactly ten moved handlers;
- replace only the contiguous root delivery/policy/worker parser block between job and
  runtime;
- retain direct root aliases to all moved handlers;
- retain root `BusError`, `PolicyError`, `json`, `sys`, `_conn`, `_print_json`, and
  `row_to_dict` while removing only proven delivery-only service imports;
- preserve exact JSON, stderr, DB, send/pump/recover, policy, and worker-loop behavior;
- update the five-layer contract proof and approved fixture/tests.

Treat 114 as AST FunctionDef-span/nonblank handler lines (delivery 56 + policy 44 +
worker 14), not the 136-line physical block including blank separators.

Allowed paths are exactly those in the approved plan. Do not implement the
`5eed424d...` pump-race fix, P9-0A4, P9-0A5, Slice 4, or P9-1+.

## Proof and isolation requirements

- New handler constants must be generated once from start `533ffcb` using the accepted
  canonical AST projection: retain node type, non-empty fields, scalar values, context
  nodes, and list order; drop only `None`/empty list/tuple fields.
- Permanent tests must not use `git show`, repository history, whole-FunctionDef
  `ast.dump`, or `ast.unparse`.
- Root import checks must explicitly exempt retained `BusError` and `PolicyError`.
- Patch the actually invoked `coordinate.delivery_cli._conn` and service names.
- Mock `send_delivery`, `pump_deliveries`, `recover_sending_deliveries`, policy calls,
  and `run_delivery_worker` completely. Assert `sys.stderr` forwarding and
  `once -> max_iterations=1`; never open production DB, use a platform adapter, recover
  a live row, or enter a real worker loop.

## Verification

Run `git diff --check`, the new boundary/contract tests, the 382-test focused baseline,
the five-layer rewind proof, and the 1,467-test full baseline. Counts may increase but
must not drop. Record 21/75/99, old/new fixture SHA, five rewind hashes, ten canonical
AST hashes, import/order/error/output/isolation evidence, and exact commands.

Commit only task changes on the worker branch with a descriptive commit. Do not amend,
push, merge, deploy, restart, SSH, send/pump/recover live deliveries, mutate lifecycle,
modify MultiNexus harness files, or call coordinator transitions.

## Report

Return commit SHA, changed files, exact test commands/counts, contract/fixture/rewind/
AST evidence, assumptions and remaining risk, followed by exactly one block:

```text
[agent-report]
action=done
workspace_id=discord-nexus
task_id=p9-0a3b-delivery-policy-worker-cli
summary="Implemented P9-0A3b on <commit>; tests: <counts>; risks: <none-or-list>"
```

If blocked, do not improvise outside the plan. Report the exact blocker and stop.
