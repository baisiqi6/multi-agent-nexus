# P9-2A Codex result review

Date: 2026-07-13  
Reviewer: Codex operator/reviewer  
Worker: Kimi `kimi-code/kimi-for-coding-highspeed` through Oh-My-Pi  
Worker sessions: `019f5a18-f9ea-7000-b08a-82b48b3b1622` (timed out after
substantial implementation) and `019f5a36-19f8-7000-89c5-30b548fb102a`
(portable correction, verification, and commits)  
Verdict: **APPROVE after reviewer corrections**

## Accepted result

- The source-controlled `agent-registry.toml` remains the single authority and now
  has independent roster and executor-catalog projections with byte-identical
  cross-repository fixtures.
- Coordinate schema v12 durably stores source-owned executor definitions and concrete
  instance bindings. Sync is serialized with `BEGIN IMMEDIATE`, preserves unrelated
  sources, rejects ownership takeover and in-flight typed-job changes, and exposes
  redacted inspection commands.
- Exact typed submission snapshots one immutable binding before durable request/job
  writes. Replay does not upgrade it, claim validates it before CAS/attempt mutation,
  and `job.claimed` records redacted identity evidence.
- MultiNexus independently parses the optional v1 binding, verifies instance/profile/
  local adapter identity before provider invocation, accepts only the documented
  legacy null path, and reports redacted binding evidence.
- Deployment validates the authority locally, syncs both projections through
  Coordinate, then verifies catalog/source/binding parity before version write or
  restart.

## Worker commits

- Coordinate implementation: `2a3a81927e545b7b4ad32508d12922bd83e67e3f`.
- MultiNexus implementation: `4a3852000cc38591c310752b36323adeb52f1a73`.

## Codex must-fix findings and corrections

Five acceptance gaps were reproduced and corrected:

1. The v11-to-v12 migration used a bare `executescript()`. An injected index failure
   left `executor_catalog_sources` behind while `user_version` remained 11. The v12
   DDL, indexes, version change, and commit now run in one explicit transaction and a
   regression test proves zero partial v12 objects after failure.
2. Sync delta receipts compared only definition capabilities and compared binding
   dictionaries with asymmetric keys. Provider/adapter changes could be reported as
   unchanged while unchanged bindings were reported as updated. Both projections now
   compare their complete canonical dictionaries.
3. Catalog sync checked only whether agent/profile ids existed. The approved
   non-agentd-instance gate now requires both `agents.client_type == "agentd"` and
   `runner_profiles.runner_type == "agentd"`, with zero-mutation tests.
4. `enabled` accepted arbitrary integers and malformed binding field errors could grow
   with attacker-controlled key count. Both authority parsers now require a TOML
   boolean, reject executor-only flags on external agents, and emit bounded structural
   errors. Coordinate also requires the exact lowercase binding-id digest shape.
5. The first real deployment preflight found the canonical `pad-jarvis` definition
   declared adapter `jarvis`, while the private runtime and active local-brain adapter
   use `jarvis-local`. Local authority/runtime parity stopped the deployment before any
   remote write, version update, or restart. The source authority now records the
   existing concrete adapter id `jarvis-local`, as required by the approved plan.

Reviewer correction commits:

- Coordinate: `44635726f579022004c9b10dd1225a196dd90eef`.
- MultiNexus: `b192b2748f784219ba0725979015770f51d71ecc`.
- MultiNexus deployment-gate correction:
  `39390592b45fb32e5ccf667de5f16eef4f6840e3`.

## Independent verification

- Approved plan SHA-256:
  `0f3fa12469b1a5587c94e386c0da13e32111383ccdc640c227e7564ba7f0ec45`.
- Cross-repository fixture SHA-256 values are identical:
  `c0ae603aa78aee57f6b3cd85ffcf7043c8158ee0ce402ad8d799b3c650f3b614`
  (`executor_binding_v1.json`) and
  `8d7632488bea64fe5b5145110004c07b016af92e446b1e54c7f234f9823216bc`
  (`executor_catalog_v1.json`).
- Coordinate focused executor suite after review: `43 passed, 12 subtests passed`.
- Coordinate full suite after review: `1989 passed, 461 subtests passed` plus exactly
  the same nine historical CLI/AST failures reproduced independently at clean baseline
  `b732159c4a1bbced39dc6ab9cde8841e7959a8cb`.
- MultiNexus full suite after review: `492 passed, 2 skipped, 31 subtests passed`.
- Post-gate local authority/runtime parity passes with roster hash
  `95bdad3b3d1f0526873e4acd8156ba296d6aa153fb11d5c9e6ddc4482212213b`
  and executor catalog hash
  `f4cdf79897755c173e97ddae1dfd88047436039f3447d4d6257105715ba5551d`;
  the focused deployment/authority suite reports `70 passed, 25 subtests passed`,
  and the full suite remains `492 passed, 2 skipped, 31 subtests passed`.
- `compileall` and `git diff --check` pass in both worktrees.
- MultiNexus P9-2A domain/runtime tests contain no sibling Coordinate import, hardcoded
  P9-2A worktree path, managed SQLite access, provider command execution, routing, or
  lease behavior.

No must-fix finding remains. P9-2A is re-approved for fast-forward integration, ordered
backup/deployment, real typed-job and tamper dogfood, durable receipt, and lifecycle
closeout.
