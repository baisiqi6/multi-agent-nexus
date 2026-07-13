# P9-3A Plan Approval

- Current approved plan SHA-256:
  `d75486b42e8d3315bda488db1129e02c03c0a2c152c04a60cccce917a385d99e`
- Material amendment: internal capacity-only snapshot capture/restore for exact
  first-rollout prior-absence rollback.
- Independent amendment reviewer: GLM 5.2 reviewer-only session
  `019f5cc0-83ff-7000-9d97-1a76b7f0e509`.
- Round 4 verdict: `APPROVED`; blocking findings none; refinement conditions are
  recorded in `plan-review-round4.md` and must be present in the new worker bootstrap.
- Superseded implementation plan SHA-256:
  `77f467f1d9555552b236f0958d0f08fd267f3cb8193ab83541580de8f0ab7c0f`.
- Current `plan.ready`: `9a63f3ee-9135-4e12-8157-851a7fd99f4f`
- Round 4 review request: `a0d46094-9c94-4d8e-903a-69d411919476`
- Original implementation reviewer: ordinary `kimi-code/kimi-for-coding`, session
  `019f5c4d-8aa6-7000-a928-b262cb779e0b`.
- Canonical Coordinate `plan.approved`: `246da1d6-473a-4093-86f1-f468a5d6d160`
- Superseded old-SHA `plan.ready`: `80b2c163-8108-407a-ac52-294ac80fffe3`
- Superseded old-SHA `plan.approved`: `c9c338b3-2947-4936-8a4f-b9e4143b89d3`
- Superseded old-SHA worker handoff: `c5aa80a4-d920-4315-a74e-b83c3ec868a7`
- Correction Round 2 bootstrap:
  `worker-bootstrap-result-review-round2.md`
- Current correction worker handoff: `5a326e5e-0062-44c9-a0c6-4c3225e47da4`

Only this exact plan revision authorizes the coding-worker bootstrap. Any plan text
change invalidates this approval, handoff, and bootstrap.

The generic bootstrap text embedded in the Coordinate handoff event is retained as
dogfood evidence but is overridden by `worker-bootstrap.md` where it conflicts: the
generated text points at the shared main checkout/legacy base branch and asks the worker
to deploy, while this package uses two isolated worktrees and reserves deployment,
production DB, lifecycle review, receipt, and closeout for Codex operator/reviewer.
