# P9-3C0 Snapshot/Restore Compatibility — MultiNexus C2 Worker Bootstrap

> **Worker bootstrap pending independent approval.** This document does not authorize
> coding until an independent reviewer approves this exact revision. It never
> authorizes production fixture activation or live-production restore.

## 1. Exact bases and dependencies

- MultiNexus implementation base:
  `f7bab06bd2606395407675b22f81fa6284d59cf7`.
- Coordinate C1 dependency:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.
- Coordinate C1 is already reviewed, merged, pushed, deployed, and accepted through
  inert v2 capture/readback only.
- Approved parent plan:
  `p9-3c0-snapshot-compatibility-plan.md`.
- C1 result and production evidence:
  - `p9-3c0-snapshot-compatibility-coordinate-c1-result-review.md`;
  - `p9-3c0-snapshot-compatibility-coordinate-c1-deployment-dogfood.md`.

The worker must use a new isolated MultiNexus worktree and branch created from the
exact base above. Recommended branch:
`agents/mac-claude/p9-3c0-snapshot-compatibility-multinexus-c2`.

## 2. Model-routing and evidence contract

- Use Claude Code as the outer agent with `sonnet`, never `opus`.
- The intended worker provider is Kimi. Provider-native JSONL must show
  `message.model = kimi-for-coding`; the outer result metadata must show the Claude
  `sonnet` model separately.
- Do not infer the provider from UI labels or prompt text. If provider-native evidence
  does not show Kimi, stop and report the actual route before coding.
- Persist the JSONL stream path and session id in the completion report.

## 3. Exact scope and allowlist

The only implementation file allowed to change is:

- `tests/test_deploy_contract.py`.

Do not modify:

- `scripts/deploy-server.sh`;
- `scripts/capacity_snapshot_helper.py`;
- `scripts/agent_registry_deploy_verify.py`;
- runtime packages under `multinexus/`;
- registry authority/runtime config;
- Coordinate code or tests;
- any project-harness plan or review document.

C2 is deploy-contract coverage. The reviewed C1 interface remains
`capture_capacity_snapshot(conn, target_source_id, output_path)` and
`restore_capacity_snapshot(conn, target_source_id, snapshot_path)`, so no production
script change is expected.

## 4. Current gap

`tests/test_deploy_contract.py` currently embeds `_FAKE_EXECUTOR_CAPACITY` with
`SNAPSHOT_CONTRACT_VERSION = 1`. It captures only the target source, restores without
canonical/digest/version/witness checks, and cannot represent a valid second source.
The real deploy script already invokes the right target-scoped helper and owns the
right cleanup/rollback lifecycle; its contract tests are stale relative to C1.

The worker must update only the fake Coordinate contract and test fixtures so the real
`scripts/deploy-server.sh` is exercised against v2 multi-source behavior.

## 5. Minimal fake v2 contract

Keep the fake self-contained. Do not import from a developer Coordinate checkout and
do not duplicate the entire production implementation. Implement the smallest strict
contract needed to model C1 at the deploy boundary.

The fake must provide:

1. `SNAPSHOT_CONTRACT_VERSION = 2`.
2. Canonical JSON bytes using `ensure_ascii=False`, sorted keys, and compact
   separators.
3. A digest-bound envelope with exact top-level keys `snapshot` and
   `snapshot_sha256`.
4. v2 inner keys:
   `contract_version`, `target_source_id`, `captured_state`, and `preserved_state`.
5. Deterministic source ordering by `source_id` and policy ordering by `agent_id`.
6. Full-projection checks sufficient for deploy-contract fidelity:
   - every policy has a matching source;
   - source version/hash agree with its policies;
   - policy id recomputes correctly from the existing capacity-policy id contract;
   - every policy agent has a typed executor binding;
   - every enabled typed binding is covered by the union of all policies;
   - duplicate agent ownership is rejected;
   - active leases on any source block restore.
7. v2 capture writes only target state into `captured_state` and every non-target row
   into `preserved_state` as a witness.
8. Restore validates canonical bytes, digest, exact version-dependent key shape, target
   id, full current projection, v1 multi-source gate, witness equality, and proposed
   union before target deletion.
9. Restore deletes/reinserts only the target source and never writes witness rows.
10. Every restore exception rolls back. Capture failure removes any final-looking
    snapshot output.

Keep injection-only behavior explicit and isolated from the default v2 path. A test
may request a handcrafted/downgraded v1 envelope, but default capture must always be
v2.

## 6. Fixture helpers

Add focused helpers inside `DeployContractTests` rather than repeating raw SQL in each
test.

Required helper semantics:

- Seed one internally valid non-target fixture executor source, definition, agent,
  runner profile, enabled binding, capacity source, and capacity policy.
- Use an id namespace such as `p9-3c0-fixture-capacity`; never reuse the canonical
  `multinexus.discord` or `multinexus.discord.capacity` ids.
- Recompute the fixture `capacity_policy_id` whenever version, hash, or capacity is
  changed.
- Extend full DB snapshots so target and non-target capacity rows are compared by all
  persisted fields in deterministic order.
- Provide a fault injection that changes a non-target policy after capture while
  keeping the projection internally valid, for example changing
  `max_concurrent_jobs` and recomputing its policy id.
- Provide a separate injection that emits a valid v1 target-only snapshot to simulate
  a stale/downgraded artifact. This is test-only; do not make v1 the default writer.

## 7. Historical prior-absence fixture correction

Do not weaken or reorder full-projection validation to keep the historical
`test_prior_absence_first_rollout_verifier_failure_restores_no_capacity` fixture green.

Under C1 union coverage, an empty capacity projection is valid only when no typed
binding is enabled. Correct the old authority used by this test so its canonical
binding is explicitly disabled. The new authority may re-enable the binding when it
also introduces the capacity policy. Rollback must first restore the old disabled
executor binding, then restore the prior-absence capacity snapshot.

This is a fixture correction, not a production behavior change.

## 8. Required deploy-contract matrix

Add or strengthen tests with these exact semantics:

### A. Capture failure is cleanup-only

Strengthen the existing post-write capture-failure test:

- exit nonzero at `snapshot-capture`;
- SSH log contains no `restore-capacity-snapshot` invocation;
- no version write or service restart;
- snapshot, authority backup, and staging residue are all absent.

### B. Successful deploy with a second source

- Seed canonical plus fixture executor/capacity projections before deploy.
- Run the real deploy script with no fault injection.
- Assert success, version write, and expected restart.
- Assert canonical sync is accepted.
- Assert every fixture source/policy field is exact/value-identical before and after.
- Assert no deployment residue.

### C. Rollback preserves a second source

- Seed both sources and capture the complete pre-state.
- Mutate the local canonical authority so a successful canonical sync would differ.
- Inject a post-capture failure that reaches rollback.
- Assert target canonical rows return exactly to pre-state.
- Assert fixture rows are exact/value-identical before and after.
- Assert no version write/restart and no residue.

### D. Witness drift is a loud recovery failure

- Seed both sources.
- After capture, mutate only the fixture policy into another internally valid state.
- Trigger rollback without corrupting the canonical/current projection.
- Restore must reject witness mismatch before target deletion.
- Deploy must emit `restore-capacity-snapshot` and `recovery-failure`, return nonzero,
  and never write version/restart.
- Assert target capacity rows were not mutated by restore and the deliberate fixture
  drift remains visible for incident diagnosis.
- Assert the EXIT-trap artifact cleanup behavior explicitly; do not silently ignore
  residue.

### E. v1 downgrade fails closed on a multi-source DB

- Seed both sources.
- Inject a valid canonical v1 target-only snapshot artifact.
- Trigger rollback.
- Restore must reject the artifact because the current DB is multi-source.
- Assert loud nonzero `recovery-failure`, no target deletion, no version/restart, and
  explicit residue cleanup behavior.

## 9. Regression requirements

- Preserve every existing deploy-contract scenario and its intent.
- Update v1-specific comments and fixture names where they now refer to capacity source
  version rather than snapshot contract version.
- Do not relax current assertions for authority restoration, roster/executor recovery,
  cleanup ordering, same-SHA path isolation, or restart/version gating.
- Do not assert raw SQLite file bytes. Compare deterministic tuples for all persisted
  fields of every rollback-affected projection.
- Error-string assertions must identify the stage boundary but must not overfit a full
  traceback.

## 10. Verification commands

Use the existing MultiNexus environment. Do not install or upgrade dependencies.

Baseline at exact base:

- focused collection: `15 tests`;
- full collection: `660 tests`;
- full baseline: green with `2 skipped`.

Run at worker HEAD:

```bash
.venv/bin/python -m pytest tests/test_deploy_contract.py -v
.venv/bin/python -m pytest
.venv/bin/python -m compileall tests/test_deploy_contract.py
git diff --check
git diff --name-only f7bab06bd2606395407675b22f81fa6284d59cf7...HEAD
```

The worker must report exact focused/full counts, durations, skips/failures, and confirm
that the changed-file allowlist is exactly one file.

## 11. Completion contract

The worker must produce exactly one local commit and report:

- exact commit SHA;
- exact changed-file list and diff stat;
- architecture summary of the fake v2 boundary;
- each required matrix case and its observed result;
- focused and full-suite results;
- `compileall` and `git diff --check` results;
- residual risks;
- Claude session id, JSONL path, outer `sonnet` model, and provider-native
  `kimi-for-coding` evidence.

Do not push, merge, deploy, SSH, change production DB, create fixtures outside the test
temp directory, or edit project-harness docs. Codex review and a separate independent
exact-revision result review are required before merge or deploy.

## 12. Stop conditions

Stop and report instead of widening scope if:

- `deploy-server.sh` or helper interfaces appear to require a runtime change;
- a second file must change;
- a witness row is written during restore;
- capture failure invokes restore;
- witness drift or v1 downgrade is accepted;
- any existing deploy-contract scenario loses coverage;
- any test touches a real SSH host, production path, or developer Coordinate checkout;
- provider-native JSONL does not confirm `kimi-for-coding`.

`P9_3C0_SNAPSHOT_COMPATIBILITY_C2_BOOTSTRAP_PENDING_INDEPENDENT_REVIEW`
