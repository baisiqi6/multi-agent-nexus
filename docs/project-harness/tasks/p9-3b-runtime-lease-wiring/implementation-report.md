# P9-3B Implementation Report

## Status

Implementation, local review, production maintenance, and deployment smoke are
complete. The host-aware completion receipt and durable closeout remain pending.

Coordinate implementation is committed and deployed at `3eaa7bf`. MultiNexus
implementation commit `0348c8b` is integrated and deployed through main merge
`6bc1adf`.

## Implemented contract

- Coordinate now issues and validates a strict version-1 execution lease envelope,
  atomically couples claim/capacity/resource authority, renews by exact identity,
  fences progress and terminal reports, and reaps expiry as the sole expiry
  authority.
- MultiNexus parses the same closed schema, verifies all claim/context/binding/
  resource identities before provider execution, runs a dedicated monotonic renewal
  supervisor, and suppresses stale progress/result reporting after authority loss.
- Recovery claiming now requires explicit normalized reason plus proof that the prior
  process stopped. Diagnostics retain bounded blocker fields without logging provider
  payloads or secrets.
- Ten positive/adversarial fixtures are byte-identical across the repositories.
- Every adapter constructible by `make_adapter()` uses an owned process group for
  provider execution: Claude, Codex call/resume, OpenCode, OMP, Hermes, Jarvis SSH,
  and Jarvis local.
- `jarvis-local` moved from `asyncio.to_thread()` to an owned local Python child. A
  cancelled coroutine can now terminate and join the provider tree rather than leave
  an in-process brain thread editing after lease loss.

## Worker and reviewer boundary

Coding slices were delegated to non-Codex workers. The final adapter slices used
Claude Code `--model sonnet`; provider-native stream JSONL identified the actual
assistant model as `kimi-for-coding`.

The Codex reviewer retained acceptance authority and made bounded corrections where
worker output was incomplete or unsafe, including:

- restoring spawn pipes/kwargs in OpenCode;
- completing Codex recovery wiring and tests after a thinking-only worker run;
- rejecting swallowed Jarvis cleanup failures;
- restoring `jarvis-local` `brain_fail` compatibility;
- adding the configured `jarvis-local` provider to the cancellation scope;
- normalizing transient macOS process-group probe denial without treating denial as
  proof that a group disappeared.

## Verification

### Coordinate

- Focused P9-3B suites: 151 passed, 23 subtests passed.
- Full authoritative gate:
  `PYTHONPATH=src /Users/yinxin/projects/coordinate/.venv/bin/python -m pytest -q`
  produced 2396 passed and 493 subtests passed.
- Nine failures are the exact reviewed historical argparse/AST baseline: eight CLI
  contract rewind hashes and one issue-handler AST hash. They were not rebaselined.
- Changed-file Ruff, compile, `git diff --check`, harness validate, and harness doctor
  passed; doctor retained only historical optional misses.

### MultiNexus

- Full suite: 650 passed, 2 skipped.
- Adapter/process-group focused suites: 83 tests passed after adding the macOS probe
  regression; the real POSIX tree tests were also repeated five times successfully.
- POSIX proof covers SIGTERM, SIGKILL escalation, descendant removal, leader join,
  cancellation during cleanup, and transient `PermissionError` probing.
- Windows unit contract covers `taskkill /PID <pid> /T /F`, bounded failure, and join.
  Real Windows tree smoke remains a Windows-host deployment check and is not claimed
  from macOS.
- Changed-file Ruff, compileall, shell syntax, `git diff --check`, and harness validate
  passed.
- `verify_execution_lease_fixture_parity.py --ref 3eaa7bf` reports all ten fixtures
  byte-identical.
- Full-repository Ruff still reports historical errors in unrelated files; the active
  main checkout reports an even larger historical set. No unrelated lint cleanup was
  mixed into P9-3B.

## Explicit boundaries

- Registry entry `openclaw` is not constructible by the local generic adapter factory;
  it is not falsely listed as a locally cancellation-tested adapter.
- The local Python 3.14 virtualenv still has two KOOK import failures caused by missing
  `pkg_resources`; the authoritative Python 3.12 full suite passes with two accepted
  skips.
- Production deployment and restart evidence is recorded in `deployment-dogfood.md`.
  No production execution lease or P9-3C concurrency/crash smoke is claimed.
