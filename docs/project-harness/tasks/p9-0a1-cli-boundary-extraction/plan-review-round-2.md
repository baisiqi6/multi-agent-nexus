# P9-0A1 Plan Review — Round 2

- Reviewer: Kimi Code Highspeed through Oh-My-Pi
- Provider/model: `kimi-code/kimi-for-coding-highspeed`
- OMP session: `019f558a-42ec-7000-af9b-aeb45fd49a27`
- JSONL: `/Users/yinxin/.omp/agent/sessions/-projects-multinexus/2026-07-12T08-55-52-300Z_019f558a-42ec-7000-af9b-aeb45fd49a27.jsonl`
- Reviewed plan SHA-256:
  `167ef44cfc48db5b74a99db811a9e8847e2740c07fee4fbe9c2d2bf869c95a8a`
- Verdict: `changes_requested`

## Review result

The roadmap order and package boundary are coherent: P9-0A1 captures the CLI contract
and extracts only the shared root support seam before Slice 4. It does not authorize a
domain registrar move. The proposed `cli_support` dependency direction, compatibility
aliases, allowed paths, authority separation, and safe test boundary are otherwise
sound.

The reviewer identified three must-fix issues:

1. The current parser has 21 top-level commands, not the 22 stated in the plan. The 75
   leaf count is correct.
2. The root `--db` default contains the checkout-specific absolute
   `DEFAULT_DB_PATH`. The contract design must specify a semantic deterministic token
   while separately asserting the exact current `DEFAULT_DB_PATH` relationship.
3. `argparse.format_help()` wrapping depends on terminal width for many parser nodes.
   Contract generation must pin `COLUMNS` before formatting help.

Optional advice:

- encode action classes by stable class name and callable handlers by stable qualified
  name, never object repr;
- state explicitly that `pr_cli.py` retains its existing private helper copies in this
  package because it is outside the approved path set.

## Codex independent reproduction

Codex independently inspected current Coordinate `e0cc1561`:

- 21 ordered top-level commands and 75 leaves;
- `--db` default resolves to the local Coordinate checkout's
  `data/coordinator.sqlite3`;
- 66 parser nodes produced different help text at `COLUMNS=80` versus `COLUMNS=120`;
- no reviewer file mutation occurred; the worktree remained limited to
  operator-generated harness/review artifacts.

## Reviewer report

```text
[agent-report]
decision=reject
workspace_id=discord-nexus
task_id=p9-0a1-cli-boundary-extraction
reviewed_plan_sha256=167ef44cfc48db5b74a99db811a9e8847e2740c07fee4fbe9c2d2bf869c95a8a
reason="Actual parser has 21 top-level commands, not 22; contract fixture must explicitly normalize the host-dependent --db default path and terminal width for deterministic format_help() output."
summary="Rejected. Roadmap boundary, cli_support acyclic seam, allowed paths, and test evidence are sound, but three determinism/acceptance gaps in the contract fixture must be fixed before approval."
```

This verdict does not authorize implementation. A material plan revision requires a new
hash, fresh `plan.ready`, and independent re-review.
