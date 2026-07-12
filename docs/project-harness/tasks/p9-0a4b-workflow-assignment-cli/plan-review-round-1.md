# P9-0A4b Plan Review — Round 1

## Decision

**REJECT** exact plan SHA-256
`f331e84dc4520d89605f9640ff49b8a8635c71e341034a93330b4151429817d9`.

## Reviewer identity

- Reviewer/model: `kimi-code/kimi-for-coding-highspeed` through Oh-My-Pi.
- OMP session: `019f572b-5869-7000-9063-ff9af65eea79`.
- Provider JSONL:
  `/Users/yinxin/.omp/agent/sessions/-projects-multinexus/2026-07-12T16-31-26-313Z_019f572b-5869-7000-9063-ff9af65eea79.jsonl`.
- Provider transition: none; Kimi remained available and GLM fallback was not used.
- Review was read-only. Two initial test commands used the wrong working directory;
  the reviewer corrected them and completed focused 472 and full 1,523 verification.

## Verified facts

The reviewer confirmed HEAD `4526d09`, root 730 lines, fixture `a7c6e955...`, 21/75/99,
12 handlers / 254 lines, all three parser seam measurements, 8 workflow plus 6
completion assignment leaves, focused/full baselines, the need for three static
registrars, and acyclic `cli -> workflow -> completion` direction.

## Must-fix

`tests/test_completion_cli.py::CompletionCLIOwnershipTests::test_root_retains_legacy_mark_done_and_workflow_handlers`
currently requires `handle_assignment_mark_done`, `handle_assignment_request`, and
`handle_assignment_closeout` to remain literal `FunctionDef` nodes in `cli.py`.
P9-0A4b intentionally moves them and preserves root aliases, so the approved
implementation would fail that existing boundary test.

Round-1 allowed paths omitted `tests/test_completion_cli.py`. The plan must authorize a
narrow boundary-test update from root-definition assertions to root compatibility
alias/owner assertions, while continuing to forbid any `completion_cli.py` or receipt
semantic change.

## Machine-readable result

```text
[agent-report]
decision=reject
workspace_id=discord-nexus
task_id=p9-0a4b-workflow-assignment-cli
reason="Allowed paths omit the existing P9-0A4a boundary test that must change from root FunctionDef assertions to root alias/ownership assertions."
summary="Source facts and architecture pass; revise only the boundary-test authorization before implementation."
```
