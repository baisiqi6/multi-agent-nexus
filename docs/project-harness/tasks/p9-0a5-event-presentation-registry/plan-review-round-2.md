# P9-0A5 Independent Plan Review — Round 2

## Verdict

`APPROVE`

- Approved plan SHA-256:
  `f8507735838a22b3d7c69982f9fed9493e09caf4ab1b8b709f4085d12fc3c1c2`.
- Reviewed Coordinate start:
  `882c2a1487e4102d35c3c1f5b18b4a542be2d3bc`.
- Provider/model: `kimi-code/kimi-for-coding-highspeed` through Oh-My-Pi.
- Provider session: `019f5756-1931-7000-8b91-1c65ca183565`.
- Provider JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-p9-0a5-plan-review/2026-07-12T17-18-08-177Z_019f5756-1931-7000-8b91-1c65ca183565.jsonl`.

The reviewer remained read-only. The detached review checkout was clean before and
after the review.

## Evidence independently reproduced

- The plan hash and Coordinate start identity matched the reviewer bootstrap.
- The proposed closure is exactly 44 top-level pure functions, 550 source-span lines
  and 543 nonblank lines.
- `_EVENT_BASE_PAYLOAD_RENDERERS` is one 66-line `AnnAssign` with 34 keys.
- `SUPPORTED_EVENT_TYPES` has 34 keys and equals the registry key set.
- Discord styling has 31 keys; the exact explicitly unstyled partition is
  `issue.materialized`, `issue.triaged`, and `review.rejected`.
- The 44-function closure contains no delivery, DB, policy-facade, or Discord-rendering
  orchestration. Those authorities remain in `policy.py`.
- The approved portable witness uses recursive `ast.iter_fields` projection, retains
  node types, non-empty fields, scalar values, contexts and list order, and does not
  traverse `_attributes` such as line/column positions. It serializes sorted-key
  compact JSON and hashes UTF-8 bytes with SHA-256.
- Permanent witness generation may not use whole-node `ast.dump`, `ast.unparse`, git
  history, or post-move expected-value regeneration.
- Allowed paths, object-identity re-exports, cold import-order checks, exact
  `PolicyError` fallback, rollback, stop conditions and provider fallback boundaries
  are sufficient for a movement-only package.

## Baseline qualification

The reviewer reproduced 151 policy, 40 Discord-rendering and 24 delivery-CLI tests as
passing. On the host's current Python 3.12 interpreter, discovery counted the expected
1,555 tests but retained eight pre-existing failures: seven CLI-contract fixture
differences caused by interpreter-specific argparse formatting and one historical
issue-CLI AST witness mismatch. These failures are outside P9-0A5 and are not treated
as green. Implementation acceptance therefore requires:

1. the package-focused 247-test baseline must not drop;
2. the full suite must not add a failure relative to the reviewed start under the same
   interpreter/environment; and
3. Codex must repeat the suite in the project's known-good isolated interpreter when
   available.

## Non-blocking implementation precision

The worker bootstrap must name `ast.iter_fields` explicitly and must state that
`_attributes` are excluded. This clarifies the already-approved plan without changing
its algorithm or authority.
