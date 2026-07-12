# P9-0A1 Plan Review — Round 3

- Reviewer: fresh Kimi Code Highspeed session through Oh-My-Pi
- Provider/model: `kimi-code/kimi-for-coding-highspeed`
- OMP session: `019f5590-f3d4-7000-8a77-e1a801138cac`
- JSONL: `/Users/yinxin/.omp/agent/sessions/-projects-multinexus/2026-07-12T09-03-10-804Z_019f5590-f3d4-7000-8a77-e1a801138cac.jsonl`
- Reviewed plan SHA-256:
  `fed690eacb2fc99eba07899a803633a44f0dd3090422db6d71e8c777bfbca61e`
- Verdict: `changes_requested`

## Review result

Round 2 corrections were accepted in substance: the reviewer independently reproduced
21 ordered top-level commands and 75 leaves, accepted the semantic
`<DEFAULT_DB_PATH>` design, the fixed help width/locale, stable action/callable identity,
the acyclic support seam, the narrow allowed paths, and the no-live-side-effect role
gates.

One remaining must-fix was found. `build_parser()` reads
`MULTI_AGENT_COORDINATOR_DB`; merely setting `COLUMNS`, `LANG`, and `LC_ALL` does not
prevent a caller environment from overriding `--db`. Both clean contract-generation
subprocesses must explicitly omit that variable and build the parser directly, so the
fixture cannot inherit or leak a host-specific DB path.

Optional advice:

- pin deterministic JSON serialization bytes;
- cover help for every intermediate parser node, not only root/top-level/leaves;
- normalize custom callable `type` values by stable qualified name;
- keep reviewer and worker as separate agent sessions/roles even when the same provider
  family is used.

## Codex independent reproduction

Codex ran `build_parser()` with
`MULTI_AGENT_COORDINATOR_DB=/tmp/p9-reviewer-env.sqlite3` and observed that the root
`--db` default became that exact inherited path. The must-fix is valid. Current source
has no other `os.environ` read inside `build_parser()`; `.env` loading occurs in `main()`
before `build_parser()`, so contract generation must call `build_parser()` directly and
must not invoke `main()`.

## Reviewer report

```text
[agent-report]
decision=reject
workspace_id=discord-nexus
task_id=p9-0a1-cli-boundary-extraction
reviewed_plan_sha256=fed690eacb2fc99eba07899a803633a44f0dd3090422db6d71e8c777bfbca61e
reason="Contract-generation subprocesses must sanitize MULTI_AGENT_COORDINATOR_DB (and any env var that can override the --db default) in addition to setting COLUMNS/LANG/LC_ALL; otherwise the parser default can diverge from str(DEFAULT_DB_PATH) and leak a host-specific DB path into the fixture."
summary="Rejected. Plan hash, 21/75 command structure, DEFAULT_DB_PATH semantic normalization, action/callable identity rules, acyclic cli_support seam, and narrow scope/gates are sound; the only remaining must-fix is explicit environment sanitization for the contract-generation subprocess."
```

This verdict does not authorize implementation. A materially revised plan requires a
new hash, fresh `plan.ready`, and independent re-review.
