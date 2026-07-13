# P9-2B Result Review — Round 6

Status: `approved_for_integration`

## Reviewed authority

- Approved plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`
- Final Coordinate worker HEAD: `41b2769f159a5717bb0cb081a791ac515e339e14`
- Final MultiNexus worker/report HEAD: `9ae9999dfc1ff873b21bb02717c7a62a446d142d`
- Worker model: ordinary `kimi-code/kimi-for-coding` (no highspeed)
- Provider session id: `019f5c0d-9fb9-7000-a7fe-926c6ab190cc`
- Provider JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-p9-2b-kimi/2026-07-13T15-17-04-569Z_019f5c0d-9fb9-7000-a7fe-926c6ab190cc.jsonl`

## Verdict

The final P9-2B implementation is approved for integration. The Round 5 shared
capability-item length gap is closed, and the follow-up tests isolate that gate rather
than relying on an unrelated required-capability failure. No unresolved P9-2B
correctness blocker remains in the reviewed worktree range.

This verdict authorizes integration and the already-approved deploy/dogfood gate. It
does not itself claim production deployment or lifecycle completion; those require
post-integration evidence and a terminal receipt.

## Independent Codex evidence

- Focused Coordinate gate: `189 passed in 0.95s`.
- Coordinate full suite: `2156 passed` plus exactly the same nine accepted historical
  CLI-contract/AST failures; no additional failure appeared.
- MultiNexus full suite: `503 passed, 2 skipped, 1 warning`.
- Both worktrees are clean.
- Both committed P9-2B ranges pass `git diff --check` with empty output.
- Both repositories pass `compileall`.
- Inline AST inspection reports no duplicate P9-2B test methods.

Independent digest-recomputed probes returned:

```text
PROBE_OVERLONG_STORED_REQUEST_REJECTED required_capabilities exceeds maximum item length: 64
PROBE_OVERLONG_ELIGIBLE_CANDIDATE_REJECTED candidate capabilities exceeds maximum item length: 64
```

Earlier Round 5 probes also independently proved:

- 32 capabilities accepted; 33 and 5000 rejected;
- forged selected candidate capabilities reject against the stored binding;
- routed replay rejection leaves event count/payload and job payload/status/attempt
  count unchanged.

## Final contract review

- Coordinate remains the sole owner of routing requests, candidate resolution,
  deterministic selection, immutable replay validation, and redacted claim evidence.
- MultiNexus contains no routing-policy source change and remains a worker transport /
  execution boundary.
- Candidate eligibility is derived from typed P9-2A bindings, workspace authority,
  agentd online state, host and runner profiles, requested capabilities, and optional
  definition filtering.
- Ordering is deterministic from preferred-host rank, Coordinate-owned live job load,
  definition id, and agent id. No P9-3 capacity or P9-4 freshness semantics were
  smuggled into this slice.
- Caller and stored capability envelopes share P9-2A authorities
  `MAX_CAPABILITIES = 32` and `MAX_CAPABILITY_LEN = 64`.
- Routed replay validates the immutable event/job/request/decision/binding/context
  links without recomputing current routing load or silently rerouting.
- Claim validates routing evidence before CAS and adds only redacted routing ids and
  selection kind to `job.claimed`.

## Accepted historical baseline noise

The nine Coordinate full-suite failures are unchanged historical CLI fixture/AST
proof failures outside P9-2B:

- eight `tests/test_cli_contract.py` rewind-fixture hash failures;
- one `tests/test_issue_cli.py` `handle_issue_scan` AST hash failure.

They remain visible and must not be described as a green full suite. P9-2B acceptance
is based on exact failure-set equality plus green focused and independent adversarial
gates.

## Next gate

Integrate the complete Coordinate P9-2B commit range and the MultiNexus review/report
range onto their current `main` branches without overwriting unrelated local state.
Then rerun main-checkout gates, push and verify `HEAD == @{u}`, back up production
state, deploy producer-first, execute a real routed non-Codex worker dogfood, inspect
provider JSONL/process/artifacts, and write the terminal receipt before closing P9-2B.
