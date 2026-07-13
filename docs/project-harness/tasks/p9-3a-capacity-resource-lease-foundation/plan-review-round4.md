# P9-3A Plan Review — Round 4

Verdict: APPROVED

Reviewed plan SHA-256:
`d75486b42e8d3315bda488db1129e02c03c0a2c152c04a60cccce917a385d99e`

- Reviewer: fresh GLM 5.2 reviewer-only session through Oh-My-Pi
- Model: `zhipu-coding-plan/glm-5.2`
- Session: `019f5cc0-83ff-7000-9d97-1a76b7f0e509`
- JSONL:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/sessions/p9-3a-plan-review-glm-round4/2026-07-13T18-32-28-415Z_019f5cc0-83ff-7000-9d97-1a76b7f0e509.jsonl`
- SHA verification: exact match, 23,543 bytes.

## Blocking findings

None.

## Reviewer disposition

The amendment is a rollback artifact, not a second capacity authority. It gives the
first rollout a real prior-absence restoration path: capture `source=null`, allow the
new sync to create the projection, and on a later verifier failure remove that exact
target projection inside one `BEGIN IMMEDIATE` transaction before the deploy can be
accepted.

The reviewer confirmed that the plan requires strict canonical bytes and digest,
source/policy validation, mode-0600 secret-free storage, active-lease rejection, no
public restore CLI, no roster/executor/job/event/lease mutation, three-way restored
parity, and a P9-3B re-design before capacity becomes claim authority.

## Refinement conditions carried into worker bootstrap

1. Define the exact snapshot v1 canonical object and add deterministic bytes/digest
   fixture tests.
2. Fault injection must assert restored roster, executor, and capacity projections,
   not capacity alone.
3. The prior-absence object must still carry an explicit target source id; restore may
   delete only that expected target projection and must reject unexpected extra or
   mismatched sources. This is the stricter fail-closed interpretation of the
   reviewer's absence-case observation.
4. Do not add a public `runtime capacity restore` command.
5. A restore hard failure remains loud and nonzero, with no version/restart/smoke; it
   must never be suppressed or described as successful restoration.

## Statement of independence

The reviewer did not modify files, Git state, harness state, or production state and
did not implement code. Only Codex's result gate may authorize deployment.
