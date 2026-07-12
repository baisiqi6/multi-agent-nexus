# Slice 4D Plan Review — Round 1

## Decision

**CHANGES_REQUESTED** for exact plan SHA-256
`dbe4d029b5bb0272a0002a494fb24b9bb8dcf7e31247841c7059bfb9087f8a1a`.

The independent reviewer verified the plan bytes and Coordinate start, accepted the
overall read-only authority architecture, and rejected seven P1 ambiguities that affect
deterministic implementation and acceptance. No implementation or worker bootstrap is
authorized from this round.

Coordinate recorded `plan.rejected` as
`46172b33-ca4d-4e22-ae6b-29f899261399`.

## Reviewer evidence

- Reviewer/provider: `kimi-code/kimi-for-coding-highspeed` through Oh-My-Pi.
- OMP session: `019f5871-29c3-7000-aa85-9e33cace2fb9`.
- Provider JSONL:
  `/Users/yinxin/.omp/agent/sessions/-projects-multinexus/2026-07-12T22-27-19-107Z_019f5871-29c3-7000-aa85-9e33cace2fb9.jsonl`.
- Provider transition: none; Kimi remained available and GLM fallback was not used.
- Review request: `c699acfe-489c-4573-aa75-33d66178f4be`.
- Verified Coordinate start:
  `a21d946e4d6be78f3f481d38eb2571229a4d3a9f`.
- Review was read-only. The known unrelated Coordinate `.qoder/` remained untracked.

## Accepted architecture

- one read-only projection diagnostic surface is appropriate;
- the S4-C2 `mark-done-preflight` stale-authorized behavior is real;
- projection diagnosis must preserve S4-B registry, S4-C operation, mirror, and receipt
  authorities rather than create a repair authority;
- additive doctor integration and fail-closed receipt derivation are appropriate.

## Required revision and resolution

1. Define the exact deterministic finding ordering key.
2. Close the severity enum to `error | warning | info`.
3. Define receipt supersession by distinct receipt, same workspace/task, and later
   valid `completion.consumed` rowid; a later authorization alone is insufficient.
4. Extend no-write evidence to the complete harness manifest/bytes and prohibit the
   projection collector from invoking `harnessctl` or subprocess operations.
5. Enumerate reusable split-operation validators/builders and permit only focused
   read-only wrappers around existing private verification logic.
6. Clarify that retained expired override is informational, while inclusion in
   compatibility `agents_json` is the separate stale-projection error.
7. Define file-pending repairability per operation and require every record-half input;
   envelope-only evidence normally remains non-repairable.

The reviewer stated that `task.create` does not consume owner/branch/actor/destination.
Current `apply_task_create_record` does consume owner, branch, actor, target, and
payload (but not destination). The resolution therefore keeps the valid concern—never
guess record-only inputs—while correcting the operation-specific argument list from
the live implementation.

Optional advice was also incorporated: reuse existing receipt payload-key lookup
semantics and explicitly define `receipt_terminal` as an informational finding.

The corrected plan requires a new exact hash, fresh `plan.ready`, and a second
independent review before implementation.
