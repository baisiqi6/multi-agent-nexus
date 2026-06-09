# Phase 7.1 Review Feedback

Reviewer: `codex-operator`
Date: 2026-06-08
Decision: changes required / blocked

## Summary

The current branch has useful pieces (`AgentRequest`, `AgentResponse`, `AgentDaemon`, KOOK mention routing), but it does not yet meet the Phase 7.1 architecture acceptance criteria.

The target topology is:

```text
Discord bridge ┐
KOOK bridge    ├── coordinate ── standalone mac-codex agentd
               │             └── standalone mac-claude agentd
```

The current implementation is closer to:

```text
Discord bridge ── embedded AgentDaemon ── adapter
KOOK bridge    ── embedded AgentDaemon ── adapter
```

That can still create two adapter/agentd instances for the same agent identity when Discord and KOOK are both enabled.

## Blocking Findings

### 1. Bridges embed agentd instead of sharing one standalone agentd

- `DiscordClient` starts `AgentDaemon(self.agent_config)` in bridge mode.
- `KookBridge` also starts `AgentDaemon(self.config)` in bridge mode.
- If both bridges are configured for the same agent, both bridge processes can create their own adapter and session store.

Required change:

- Add a standalone agentd runner process for one agent identity.
- In bridge mode, Discord and KOOK bridges must not instantiate `AgentDaemon` or call `make_adapter()`.
- Bridges must submit normalized requests to coordinate.
- The standalone agentd must register/heartbeat, claim jobs, execute the adapter, and report results through coordinate.

The first implementation can use the coordinate runtime CLI shim instead of HTTP, but the business flow must be:

```text
bridge -> coordinate runtime request submit -> coordinate job -> agentd claim/report -> coordinate delivery metadata
```

Useful coordinate commands currently available:

```bash
skills/coordinate-operator/scripts/mac.sh runtime agent register --agent-id <agent> --host-id <host> --client-type agentd
skills/coordinate-operator/scripts/mac.sh runtime request submit <workspace> --target-agent <agent> --prompt <text> --origin-json <json> --reply-json <json>
skills/coordinate-operator/scripts/mac.sh runtime job claim --agent-id <agent>
skills/coordinate-operator/scripts/mac.sh runtime job report <job-id> --agent-id <agent> --status done --result-json <json>
```

### 2. KOOK bridge import/startup path is not installable

`import multinexus.kook.bot` fails in the current environment because `khl` is missing from `requirements.txt`.

Required change:

- Either add the KOOK dependency to install requirements, or make KOOK bridge import optional with a clear runtime error when the dependency is absent.
- Add coverage for the chosen behavior. Mention parsing tests are not enough; review needs at least import/startup configuration coverage.

### 3. Tests do not prove the N+M process invariant

Current tests show protocol round trips and local agentd HTTP behavior, but they do not prove that Discord and KOOK share the same agentd.

Required test coverage:

- Bridge mode does not call `make_adapter()` or instantiate `AgentDaemon` in either Discord or KOOK bridge.
- A standalone agentd can claim one coordinate job and report a result.
- The same agent identity is represented by one standalone agentd process boundary, not one embedded daemon per IM bridge.
- KOOK bridge import/startup behavior is covered.

## Closeout Requirements

Before requesting review again:

1. Update the implementation to satisfy the `bridge -> coordinate -> standalone agentd` flow.
2. Re-run the multinexus test suite.
3. Re-run `scripts/harness/harnessctl validate`.
4. Send a structured `[agent-report]` block with `action=done`.
5. Run `assignment closeout discord-nexus --task-id phase-7.1-single-host-n-plus-m-runtime --reviewer codex`.

