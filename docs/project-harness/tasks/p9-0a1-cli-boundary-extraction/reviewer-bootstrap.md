# Reviewer Bootstrap: p9-0a1-cli-boundary-extraction

## Session Startup

### Step 1: Locate the plan document (read-only, in your local repo)

This is a **plan review** — you evaluate the plan/spec, not code. There is no implementation yet, so no task worktree or branch to guard. In your local checkout of the workspace repo, read:

```bash
# primary entry (relative — works on any host's checkout):
cat openspec/changes/p9-0a1-cli-boundary-extraction/proposal.md
# also review: design.md, specs/*/spec.md, tasks.md in that dir,
# and any docs/superpowers/plans/*-p9-0a1-cli-boundary-extraction*.md implementation plan
```

Control-plane recorded the plan at `docs/project-harness/tasks/p9-0a1-cli-boundary-extraction/plan.md` (server path, for reference only — read your LOCAL repo, not the server path). Do NOT switch branches, create worktrees, or modify any file — plan review is strictly read-only.

### Step 2: Read project boundaries (read-only, relative paths)

- `docs/project-harness/scope.md` — goals, non-goals, constraints
- `docs/project-harness/architecture.md` — module boundaries
- `docs/project-harness/domain-model.md` — core entities

## Review Assignment

- **Task**: p9-0a1-cli-boundary-extraction
- **Title**: P9-0A1 CLI Contract And Support Seam
- **Source Plan**: openspec/changes/p9-0a1-cli-boundary-extraction/proposal.md (relative; server copy: docs/project-harness/tasks/p9-0a1-cli-boundary-extraction/plan.md)
- **Role**: reviewer (plan review — read-only, you do NOT own this task, do NOT mutate code or branches)

## Acceptance Criteria

No acceptance criteria recorded. See source plan.

## Review Focus (plan review)

Evaluate the plan document itself:
- Plan completeness: are edge cases and error paths covered?
- Architecture alignment: does the plan respect scope/architecture boundaries?
- Test baseline: are acceptance criteria testable?
- Non-goals: does the plan avoid out-of-scope creep?
- Risk assessment: are there unaddressed failure modes?

## Review Output Format

Your response MUST include exactly one machine-readable block:

```text
[agent-report]
decision=approve
workspace_id=discord-nexus
task_id=p9-0a1-cli-boundary-extraction
summary="Approved. <optional notes>"
```

OR

```text
[agent-report]
decision=reject
workspace_id=discord-nexus
task_id=p9-0a1-cli-boundary-extraction
reason="<specific issue requiring revision>"
summary="Rejected. <brief explanation>"
```

The `[agent-report]` marker must start at the beginning of its own line.

## Constraints

- Review only — do NOT modify code, commit, or push
- Do NOT run `assignment accept` — you do not own this task
- No merge or deploy without explicit operator approval
- Your review is the gate: approve only when requirements are met
