# Reviewer Bootstrap: slice-4b2-deployed-agent-registry-authority

## Session Startup

### Step 1: Locate the plan document (read-only, in your local repo)

This is a **plan review** — you evaluate the plan/spec, not code. There is no implementation yet, so no task worktree or branch to guard. In your local checkout of the workspace repo, read:

```bash
# primary and canonical entry (relative — works on any host's checkout):
cat docs/project-harness/tasks/slice-4b2-deployed-agent-registry-authority/plan.md
```

Control-plane recorded the plan at `docs/project-harness/tasks/slice-4b2-deployed-agent-registry-authority/plan.md` (server path, for reference only — read your LOCAL repo, not the server path). Do NOT switch branches, create worktrees, or modify any file — plan review is strictly read-only.

### Step 2: Read project boundaries (read-only, relative paths)

- `docs/project-harness/scope.md` — goals, non-goals, constraints
- `docs/project-harness/architecture.md` — module boundaries
- `docs/project-harness/domain-model.md` — core entities

## Review Assignment

- **Task**: slice-4b2-deployed-agent-registry-authority
- **Title**: Slice 4B2 Deployed Agent Registry Authority
- **Source Plan**: `docs/project-harness/tasks/slice-4b2-deployed-agent-registry-authority/plan.md`
- **Role**: reviewer (plan review — read-only, you do NOT own this task, do NOT mutate code or branches)

## Acceptance Criteria

Use the complete `Tests and acceptance` section of the source plan. In particular,
red-team the claim that a tracked secret-free authority plus parity-gated private
runtime configurations leaves only one canonical roster, the failure ordering around
committed sync versus version/restart failures, and whether the isolated sidecar is a
credible same-process removal/reload proof.

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
task_id=slice-4b2-deployed-agent-registry-authority
summary="Approved. <optional notes>"
```

OR

```text
[agent-report]
decision=reject
workspace_id=discord-nexus
task_id=slice-4b2-deployed-agent-registry-authority
reason="<specific issue requiring revision>"
summary="Rejected. <brief explanation>"
```

The `[agent-report]` marker must start at the beginning of its own line.

## Constraints

- Review only — do NOT modify code, commit, or push
- Do NOT run `assignment accept` — you do not own this task
- No merge or deploy without explicit operator approval
- Your review is the gate: approve only when requirements are met
