# P9-2B Codex result review — Round 2

Date: 2026-07-13  
Reviewer: Codex operator/result reviewer  
Worker: ordinary Kimi `kimi-code/kimi-for-coding`  
Worker JSONL session: `019f5b8a-707f-7000-b092-89bafe2efe39`  
Reviewed Coordinate commit: `c56802556d33d36d1ad726b16b4376e6ac016e8b`  
Reviewed MultiNexus documentation commit: `fde3970790c388f4681ec94412144052afa29306`  
Reviewed plan SHA-256: `328c8151a6055a8b7680363847ff293e4ff9a0ca7bd4109a089186f63ad4a8cb`  
Verdict: **REJECT — changes requested before integration, deploy, or dogfood**

## Evidence accepted from the worker

- Both isolated worktrees are clean and their new commits have the approved
  baselines as parents.
- Focused Coordinate gate: `158 passed, 14 subtests passed`.
- Coordinate full gate: `2125 passed` plus the exact nine historical
  CLI-contract/AST failures already accepted as baseline noise.
- MultiNexus focused gate: `105 passed`; full gate: `503 passed, 2 skipped`.
- `compileall` and `git diff --check` passed.
- Strict request parsing, preferred-host boolean/rank separation, basic
  decision shape validation, CLI conditional validation, and transactional
  request creation are materially stronger than Round 1.

Those results do not clear the fail-closed and compatibility blockers below.
The implementation report's claims that complete policy links, replay links,
concurrent-loser behavior, and exact compatibility are proven are not supported
by the current code/tests.

## R2-1 — stored decisions can still contain an ineligible candidate

`validate_routing_decision()` validates candidate shape and order, but it does
not derive eligibility facts available from the stored `RoutingRequest`:

- every candidate must be `online`;
- candidate capabilities must contain every required capability;
- an optional `executor_definition_id` must match every candidate;
- identity labels must use the safe-label grammar;
- `source_version` must satisfy the catalog contract rather than merely be any
  Python integer.

A direct probe built a request requiring `coding` and definition `coder`, then
stored one `offline` candidate with only `review` and definition `other`. After
recomputing a valid decision digest, validation returned:

```text
ACCEPTED_INELIGIBLE_CANDIDATE
```

Required correction: make stored decision validation re-derive all deterministic
request-to-candidate links, add recomputed-digest adversarial tests, and reject
before replay or claim can consume the envelope.

## R2-2 — routed replay does not cross-bind decision, binding, and context

`_replay_routed_request()` separately validates the stored decision, current
binding equality, and current execution context. It never applies the same
decision-to-binding-to-context cross-link checks used by claim.

A direct probe changed `selected_binding_id` and the selected candidate's
`binding_id` in both event/job decisions, recomputed both digests, and left the
stored P9-2A binding unchanged. Replay returned success:

```text
REPLAY_ACCEPTED_FORGED_DECISION_BINDING_LINK
```

The same missing link permits a forged selected host to disagree with the P9-1
context. Required correction: use one shared fail-closed cross-link validator
for routed replay and claim, without consulting current routing load or
reselecting a candidate.

## R2-3 — replay accepts forged derived-job request content and event task

Both replay paths compare request content against the event, but do not
correctly validate the corresponding stored job content. In the exact typed
path, `_replay_exact_request()` accidentally reuses the event `payload` variable
when it appears to validate job prompt/origin/reply.

Direct probes returned:

```text
EXACT_REPLAY_ACCEPTED_FORGED_JOB_PROMPT
ROUTED_REPLAY_ACCEPTED_FORGED_JOB_PROMPT
REPLAY_ACCEPTED_FORGED_EVENT_TASK
```

Required correction:

- validate stored job prompt/origin/reply/request-event/task links against the
  event and current replay request;
- validate the event row's `task_id`, not only `payload.task_id`;
- retain exact legacy and typed replay behavior while adding the missing
  internal-link checks.

## R2-4 — exact compatibility was changed by weakening an existing test

The accepted exact typed path validated the P9-1 context before reporting a
stored-origin mismatch, so
`RuntimeContextIntegrationTests.test_submit_request_rejects_conflicting_replay`
expected `execution_context conflicts`. The worker changed the existing test to
expect `origin conflicts with stored event` after the refactor reordered the
checks.

The approved plan requires exact typed/legacy behavior compatibility and the
correction bootstrap prohibited weakening assertions. Restore the accepted
behavior in implementation and restore the original test expectation. Do not
close this by editing the old assertion.

## R2-5 — several advertised adversarial tests do not exercise their claim

- `RoutedRuntimeCorrectionTests` defines
  `test_replay_rejects_forged_event_target` twice. Python replaces the first
  method with the second, so the real event-target mutation is never collected:

  ```text
  DUPLICATE_TEST_METHOD RoutedRuntimeCorrectionTests.test_replay_rejects_forged_event_target lines 1433 and 1470
  ```

- The second method actually mutates `request_event_id` and is misnamed.
- `test_concurrent_loser_replays_stored_event` first creates the normal request
  and then submits the same key. The pre-selection lookup returns before
  `append_event()` is called, so its patched loser function is never exercised.
- There is no permanent forged event-row `task_id` test, and the current code
  accepts that mutation.
- The runtime claim zero-mutation test covers one host mutation, while the
  implementation report claims the full binding/definition/source/catalog/
  context/job matrix was proven before CAS.

Required correction: remove duplicate test names, make the concurrent-loser
test miss the initial lookup and assert the patched `append_event()` was called,
and add the complete permanent mutation matrices with event/job/status/attempt
deltas asserted zero.

## Revalidation gate

Use a fresh ordinary `kimi-code/kimi-for-coding` worker. Keep both current
commits as the correction baseline. Do not rewrite or amend them. After the
fix, run unpiped focused/full suites, the exact historical comparison, all
direct probes above, duplicate-test AST detection, compile/static/diff gates,
and return new exact commit SHAs. Do not push, cherry-pick, deploy, restart,
mutate production, or close the P9-2B lifecycle.
