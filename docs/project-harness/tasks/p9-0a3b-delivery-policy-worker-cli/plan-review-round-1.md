# P9-0A3b Plan Review — Round 1

## Gate verdict

**Approved for worker bootstrap.** The independent reviewer approved exact plan SHA
`5a9438c345a67a4fb7d73ce4e7cade6f951f9b8da5bf46567b4270adaa153a2f` with no
must-fix findings.

## Reviewer identity

- Provider/model: `kimi-code/kimi-for-coding-highspeed`.
- OMP session: `019f56ee-5849-7000-a189-8bedf549a52b`.
- JSONL:
  `/Users/yinxin/.omp/agent/sessions/-projects-multinexus/2026-07-12T15-24-48-585Z_019f56ee-5849-7000-a189-8bedf549a52b.jsonl`.
- Role: independent read-only plan reviewer.
- Provider transition: none; Kimi remained available, so GLM fallback was not used.

## Independently verified evidence

- Coordinate start: `533ffcb1be17c6a26e8d5acf31e9c3c05da1ef63`.
- Root `cli.py`: 1,590 lines.
- Contract: 21 top-level / 75 leaves / 99 nodes.
- Fixture SHA:
  `fbdb5064f1d4870e5ee3ae68628c7cd8be618c37d085530f03336899a82e949c`.
- Scope: ten leaves; 114 AST FunctionDef-span/nonblank handler lines = delivery 56
  + policy 44 + worker 14.
- Registration: one contiguous delivery -> policy -> worker seam after job and before
  runtime.
- Focused baseline: 382 tests passed.
- Full baseline: 1,467 tests passed.
- Root must retain `BusError`, `PolicyError`, `json`, `sys`, `_conn`, `_print_json`,
  and `row_to_dict`.
- Five-layer rewind and P9-0A3a canonical AST projection strategy are sufficient and
  do not require repository history.
- All DB/send/pump/recover/platform/worker-loop effects are patchable at the actual
  `coordinate.delivery_cli` seams.
- The `5eed424d...` concurrent-pump race remains an explicit non-goal for this
  behavior-preserving extraction.

## Nonblocking notes carried into worker authorization

1. Treat 114 as AST FunctionDef-span/nonblank handler lines, not the 136-line physical
   block including inter-function blank separators.
2. Give `delivery_cli` a docstring that explicitly names delivery/policy/worker scope.
3. Root import checks must exempt retained `BusError` and `PolicyError`.
4. Mock `run_delivery_worker` completely; never rely on an unbounded loop or live DB.
5. Reuse the accepted canonical AST projection semantics, not `ast.unparse`, and keep
   the new ten constants independently attributable to start `533ffcb`.

## Operator decision

The exact plan is sufficiently bounded, testable, and aligned with the P9-0A roadmap.
Coordinate may record approval for this SHA and generate a fresh worker bootstrap.
Approval does not authorize P9-0A4, P9-0A5, Slice 4, the pump-race fix, or P9-1+.
