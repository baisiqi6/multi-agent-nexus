# Slice 4D Result Review — Round 1

## Decision

**CHANGES_REQUESTED** for worker commit
`210e5f4c76c231bee3de029d0a6412248fd9ba4f`.

The implementation is not authorized for merge, push, deploy, dogfood, closeout, or
mark-done. The worker produced useful scaffolding and kept the full suite at the same
nine historical Python 3.12 failures, but the focused tests do not cover several
required authority conflicts and two independently reproduced runtime cases are wrong.

## Worker evidence

- Provider/model: `kimi-code/kimi-for-coding-highspeed` through Oh-My-Pi.
- Session: `019f587a-6ae5-7000-a3ff-a56fa541b367`.
- Provider JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-s4d-kimi/2026-07-12T22-37-25-605Z_019f587a-6ae5-7000-a3ff-a56fa541b367.jsonl`.
- Provider transition: none; Kimi remained available and GLM fallback was not used.
- Worker focused result: 25 passed.
- Worker full result: 1,761 passed / 435 subtests; the same nine historical failures.
- Commit is local to the worker branch and has not been pushed or deployed.

## Must-fix findings

### R1-1 — Unsupported contract versions are silently accepted (P1)

`projection_doctor.py:707-723` emits `operation_contract_unsupported` only for an
unknown operation kind. A ledger row with `contract_version=99` and a supported
`task.create` kind proceeds as if v1 were supported.

Independent reproduction against the worker commit produced:

```text
unsupported_contract_findings=
  ['operation_record_event_missing', 'operation_task_mirror_missing']
```

No `operation_contract_unsupported` finding was emitted. Both ledger rows and
file-pending envelopes must reject every contract version other than the explicit v1
contract before deeper interpretation.

### R1-2 — Receipt fingerprint conflicts are not diagnosed (P1)

`projection_doctor.py:1212-1271` compares status order and optional
workspace/task/actor values but never links claim `before_fingerprint` /
`expected_after_fingerprint` to apply `after_fingerprint`, receipt authorization
intent, or terminal evidence. Its conflict message claims fingerprint coverage that the
implementation does not perform.

Independent reproduction used a valid authorized -> claimed -> applied chain with
`expected_after_fingerprint='b'*64` and `after_fingerprint='c'*64` and produced:

```text
fingerprint_conflict_findings=[]
```

The shared preflight derivation has the same omission. Require all fields that each
transition owns, compare immutable linkage, and fail closed on missing or conflicting
links. Duplicate transitions, including duplicate `consumed`, must be conflicts.

### R1-3 — Consumed receipts regress to expired in preflight (P1)

`completion_cli.py:480-505` applies authorization expiry to every derived status. A
fully valid consumed chain with an old authorization therefore returns exit 1 /
`reason=expired` instead of the authoritative terminal state.

Independent CLI reproduction produced:

```text
consumed_expired_preflight_rc=1
consumed_expired_preflight={
  'ok': False,
  'reason': 'expired',
  'workspace_id': 'demo',
  'task_id': 'task-c',
  'expires_at': '2020-01-01T00:01:00Z'
}
```

Expiry may invalidate an unused `authorized` receipt, but it may not erase a later
claimed/applied/consumed authoritative state. A valid consumed result must return
`status=consumed` and terminal evidence.

### R1-4 — Envelope drift is collapsed into orphan evidence (P1)

`split_operations.load_deployed_envelope_readonly()` delegates to the record-path
loader using the expected operation id and returns `item=None` for all
`SplitOperationError`s. `projection_doctor.py:725-746` consequently classifies an
existing target whose envelope binds a different operation as
`operation_ledger_orphaned`, bypassing the planned `operation_envelope_drift` finding.

Read the checklist item independently of expected operation identity, then distinguish
missing item/envelope from present-but-drifted identity/shape/fingerprints.

### R1-5 — Record-event and task-mirror intent comparison is incomplete (P1)

- `projection_doctor.py:916-934` checks only event workspace/task/type and nested
  `operation_id`; it does not compare the operation kind, source/target, contract
  version, fingerprints, or immutable record payload required by C1/C2.
- `projection_doctor.py:1014-1052` checks only mirror `split_operation.operation_id`;
  it does not compare the immutable operation metadata/payload required by the plan.

Add exact C1 and C2 mismatch tests for every immutable field. Preserve the distinct
`operation_record_event_mismatch` and `operation_task_mirror_metadata_drift` kinds.

### R1-6 — Historical completion proof and allowed-path boundary were overwritten (P1)

The approved worker surface did not include `src/coordinate/cli.py`. The worker changed
that facade, renamed the compatibility export from `_lookup_receipt_for_preflight` to
`_derive_receipt_state`, and rewrote the P9-0A4a canonical AST constants in
`tests/test_completion_cli.py:34-48` to post-change values.

Restore `src/coordinate/cli.py` to its start bytes and preserve
`_lookup_receipt_for_preflight` as the root/completion compatibility identity. Keep all
historical P9 constants unchanged. Express the legitimate S4-D semantic change through
a self-contained current-vs-rewound delta proof; do not replace historical evidence
with freshly generated post-change hashes.

### R1-7 — Read-only proof and acceptance coverage are incomplete (P1)

The only no-write test snapshots DB counters and harness bytes on a successful C1
fixture. It does not prove:

- failure-path no-write behavior;
- registry source bytes outside the harness root;
- `events.jsonl`, sidecars, and relative manifest stability when failures occur;
- absence of `subprocess`, `harnessctl`, `refresh_state`, and mutation-helper calls;
- C2 clean/drift/event/mirror behavior;
- unsupported versions, complete event/mirror intent, fingerprint linkage, expiry, or
  duplicate receipt transitions.

Add direct denial mocks plus before/after DB, registry source, complete harness manifest,
and path-set evidence on success and injected failure cases.

### R1-8 — Finding identities misuse `task_id` for non-task scopes (P1)

Registry agent names and source ids are written into the optional `task_id` field to
make finding ids unique. This creates false task identity in a machine-readable report.
Keep `task_id` null outside task scope and use a deterministic finding-id discriminator
or scope evidence for agent/source-specific findings.

## Additional required checks

- Verify production-like C1 and C2 fixtures, including later legitimate lifecycle
  events, are clean except planned warning/info findings.
- Explicitly test the currently deployed S4-D task whose plan bytes changed after its
  original C1 `task.create` record. The doctor must report true envelope/plan drift
  honestly; do not whitelist this task or hide it with `--no-projections`.
- Keep `--no-projections` absent from every acceptance, dogfood, deploy, and release
  command.
- Keep the same nine historical full-suite failures and make all new S4-D tests pass.

## Correction boundary

Correction remains under the exact approved plan hash and worker branch. It may modify
only the already-approved production/test paths, must restore `cli.py`, must not update
historical proof constants, and must not push, deploy, access production, or invoke
lifecycle transitions. A second Codex result review is required.
