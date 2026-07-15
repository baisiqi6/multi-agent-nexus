# P9-3C0 Package 3 Plan Review — Round 1

## Verdict

`REQUEST_CHANGES`

Reviewed revision:
`2e91e6cef4f3ec58d98bb77dc7d2e7188b1612c6`.

Reviewer session:
`83d9041f-9740-4eee-97b9-2abe07cc7b0b`.

Provider evidence from the native JSONL stream:

- Claude Code outer model: `claude-sonnet-4-6`;
- provider-native model: `kimi-for-coding`;
- tools restricted to `Read` and `Bash` (plus configured read-only MCP surface);
- repository remained clean; no tracked/untracked repository file was created by the
  reviewer.

Stream:
`/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3c0-fixture-package3-plan-review-round1-claude-kimi/reviewer-stream.jsonl`.

The reviewer independently confirmed the exact revision/parent, documentation-only
diff, both expected SHA-256 values, current Coordinate dependency, TTL/renew
constants, recovery CAS, stale-attempt authority, capacity guards, and forward/cleanup
catalog feasibility.

## Blocking findings accepted for revision

1. Add a wrapper path/inode/hash/owner/mode authority record and revalidate it before
   every Coordinate invocation; define root controller versus non-root unit ownership
   explicitly.
2. Replace literal systemd input/output comparison with property-specific systemd 255
   semantic normalization, while retaining both static verify and post-start gates.
3. Anchor hold timing to the exact monotonic value used by
   `ClaudeAdapter._run` for its first-byte clock. Cgroup observation remains identity
   evidence only.
4. Add canonical launch regression tests for the `agentd --log-level` default and
   production argv that omit the new flag.
5. Enumerate isolated global-quiescence queries and exact expected row sets.
6. Require zero active fixture lease immediately before every cleanup catalog sync.
7. Capture the initial lease deadline before renewal and count two strictly later
   deadlines.
8. Delete the unsupported `systemd-run --dry-run` path rather than supplementing it.
9. Copy the exact three production service names into the execution plan.
10. Correct the cgroup process model: agentd main, one fixture adapter child, optional
    one `/bin/sleep` descendant, and bounded Coordinate CLI children—not “every child
    is the fixture executable.”
11. Define before/after DB/event immutability proof for stale-N rejection.
12. Define interrupted/frozen cleanup as independently callable exact-ledger recovery,
    not a rerun of the complete verifier.
13. Restrict runbook edits to the Package 3 section.
14. Explicitly prove the minimal environment and provider/proxy credential removal;
    do not rely on `filtered_env` alone.

## Reviewer findings refined rather than copied literally

Two Round 1 premises require correction in the revised plan:

- Coordinate has no “mark runtime agent offline” transition. A persisted
  `online_state=online` row is registration/heartbeat residue, not process liveness and
  is not consulted by claim authority. Recovery must instead prove exact prior
  unit/cgroup absence, exact host-id consistency, expired/reaped job state, and N+1
  attempt state. Requiring an impossible offline row would make the plan non-executable
  without adding unrelated Coordinate scope.
- A root-owned wrapper cannot be mode `0700` and still execute inside a non-root
  `User=` unit. The revised plan uses root-owned, exact-unit-group `0750`, records
  inode/hash, and keeps the isolated DB/work/context paths owned by the non-root unit
  user. This is stricter against replacement than a unit-user-owned `0700` wrapper.

The Round 1 wrapper containment concern was already partially addressed by the
state-root section, but the inode/hash/ownership and privilege split were not explicit;
the revision must make all of them normative.

## Gate status

No worker bootstrap or implementation is authorized. The detailed plan must be
revised, committed, and sent to a fresh exact-revision Round 2 reviewer.
