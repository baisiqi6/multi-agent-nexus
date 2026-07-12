# P9-0A1 Plan Reviewer Supplement

This task-scoped supplement corrects generic fields in the generated
`reviewer-bootstrap.md`. The generated artifact remains unchanged as control-plane
evidence; this supplement is authoritative where they conflict.

## Canonical review input

- Plan:
  `docs/project-harness/tasks/p9-0a1-cli-boundary-extraction/plan.md`
- Full SHA-256:
  `44caed57423bba8bb6cfc83b5a0b8db9703cb9e3e7570e320b109cd816976a11`
- Coordinate `plan.ready` event:
  `3d61dc7b-d9bd-48ea-8278-4f3a00693d0d`
- Short `plan_content_hash`: `44caed57423bba8b`
- Review request event: `f1362ce5-b5ba-473e-be24-88c690d1b12e`
- Reviewer bootstrap event: `1722f392-4801-4965-9e3f-86880a096c3e`

There is no OpenSpec proposal for this package. Do not read or require
`openspec/changes/...`. The canonical plan above contains the acceptance matrix,
validation, worker boundaries, dependency gate, and non-goals.

## Read-only evidence roots

- Planning/harness repository: `/Users/yinxin/projects/multinexus`
- Implementation target repository: `/Users/yinxin/projects/coordinate`
- Coordinate snapshot: `8fadd687d68032cf656291e6bf537ec481fb3e25`
- Preserve unrelated Coordinate `.qoder/`; do not modify any file or branch.

Review the plan against current Coordinate `cli.py`, `pr_cli.py`, current CLI-facing
tests, `pyproject.toml`, and the Phase 9 overview. Read-only Git commands and focused
test discovery are allowed; do not run any command that creates delivery, runtime, or
harness lifecycle state.

## Required review questions

1. Is one worker session a safe size for the six explicit CLI modules plus compatibility
   tests, or must the plan be split further?
2. Are the proposed module groupings cohesive and do they preserve `coordinate.cli:main`,
   `build_parser()`, current PR injection seams, all 71 leaf commands, flags, output,
   stderr, and exit codes?
3. Are the allowed files and stop conditions narrow enough to prevent business-logic,
   schema, lifecycle, delivery, or Phase 9 feature changes?
4. Does the acceptance/validation matrix catch parser, handler, import-cycle, injection,
   and live-side-effect regressions?
5. Is the dependency rule unambiguous: plan review may finish now, but worker bootstrap
   remains forbidden until Slice 4 acceptance plus refreshed drift review?

Return `approve`, `changes_requested`, or `blocked`, with must-fix findings separated
from optional observations. Include exactly one `[agent-report]` block for workspace
`discord-nexus` and task `p9-0a1-cli-boundary-extraction`. Review only; do not edit,
commit, push, merge, deploy, create deliveries, or call lifecycle commands.
