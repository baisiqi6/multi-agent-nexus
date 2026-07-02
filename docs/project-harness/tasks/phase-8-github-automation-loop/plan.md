# Phase 8: GitHub Automation Loop

## Purpose

Build the first practical "loop engineering" path for our own repositories:

```text
GitHub issue
  -> coordinate detects candidate
  -> operator triages
  -> worker agent fixes on its own host/worktree
  -> worker/host pushes branch
  -> coordinate links or creates PR
  -> human reviews and merges
```

This phase is intentionally scoped to repositories we control. Fork-based work on third-party repositories is a later phase after this path is stable.

## Inputs

- Draft plan: `/Users/yinxin/.claude/plans/frolicking-popping-llama.md`.
- Current runtime shape: Phase 7.2 A0, with coordinate and the Discord bridge on Tencent Cloud; Mac and Windows agentd processes remain on their host machines.
- Current test baseline before this plan: coordinate `743/743 OK`; multinexus `302/302 OK (2 skipped)`.
- Current control-plane rule: coordinate is the runtime source of truth, but operator/worker agents make judgment calls.

## Non-Goals

- No automatic merge. Human review and merge remain the gate.
- No third-party fork workflow in this phase.
- No autonomous issue interpretation inside coordinate. GitHub issue text is untrusted input.
- No assumption that the Tencent Cloud coordinate service owns every worker branch object locally.
- No tracked real `agents.toml` changes. Real agent config stays host-local; only examples/docs may be tracked.

## Architecture Decisions

### 1. Coordinate Stays Deterministic

Coordinate may scan GitHub, write events, create task mirrors, request handoffs, check branch/PR/CI state, and create PRs from already-pushed branches.

Coordinate must not decide whether an issue is worth doing or which worker should own it. That is operator work.

### 2. Push Authority Belongs To The Worktree Owner

In Phase 7.2 A0, coordinate runs on Tencent Cloud while agent worktrees live on Mac/Windows hosts. A branch created by a worker may not exist in the server-side repository clone.

Therefore MVP publish flow is:

```text
worker host commits
worker host pushes branch
worker reports branch + commit + remote
coordinate verifies remote branch SHA
coordinate creates or links PR
```

Coordinate can later support a colocated-runner mode where it performs `git push` itself, but that is not the default Phase 8 path.

### 3. Issue Text Is Untrusted

Every prompt and bootstrap generated from a GitHub issue must wrap issue title/body/comments as untrusted source material. The worker must not follow issue-injected instructions to reveal secrets, alter deployment credentials, bypass review gates, or ignore project instructions.

### 4. One Issue Produces One Candidate Event

Issue scan idempotency is issue-based, not date-based:

```text
idempotency_key = <workspace_id>:github_issue:<repo>:<number>:<updated_at>
```

This allows a materially updated issue to be surfaced again without re-spamming unchanged issues every scan.

### 5. Server Timers Use systemd

Phase 7.2 moved coordinate and bridge to Tencent Cloud. Central pollers and drivers for this phase should be systemd services/timers on Tencent Cloud, not launchd. Mac/Windows startup systems are only for host-local agentd processes.

## Phase 8.1: GitHub Issue Intake

### Goal

Scan configured GitHub repositories for actionable candidate issues and write normalized `issue.spotted` events into coordinate.

### Coordinate Changes

- Add `src/coordinate/issues.py`.
- Add a GitHub query helper using `gh issue list` with injected `run=` for tests.
- Add CLI:

```text
coordinate issue scan <workspace_id> --repo <owner/name> [--label bug] [--limit 50]
```

- Each event payload must include:
  - `repo`
  - `number`
  - `url`
  - `title`
  - `labels`
  - `author`
  - `state`
  - `updated_at`
  - optional short `body_excerpt`
- Add policy rendering for `issue.spotted` as a visible `[ISSUE]` message.
- Add Discord rendering style for `issue.spotted`.

### Acceptance

- Fake `gh issue list` tests pass.
- Unchanged issue scans are idempotent.
- Updated issues can emit a new event.
- Policy rendering never treats issue body as trusted instructions.

## Phase 8.2: Operator Runtime And Triage Handoff

### Goal

Make issue candidates reach an operator agent as structured triage work.

### Multinexus Changes

- Add `mac-operator` to `agents.toml.example` only.
- Real `agents.toml` remains local-only on the host that runs the operator agentd.
- Add launchd template for a Mac operator agentd only if the operator will run on Mac.
- Do not require a separate Discord bridge. The existing remote Discord bridge routes to the operator agentd through coordinate.

### Coordinate Changes

- Add an issue-to-triage command:

```text
coordinate issue triage-create <workspace_id> --repo <owner/name> --number <n> --operator mac-operator
```

- Create or update a coordinate task mirror:

```text
task_id = triage-gh-issue-<number>
```

- Generate a worker bootstrap or equivalent task packet for the operator that contains:
  - issue metadata
  - links to source docs
  - explicit untrusted-input warning
  - expected operator outputs: ignore, needs-human, assign-to-worker

### Acceptance

- A spotted issue can become exactly one triage task.
- Duplicate triage-create is idempotent.
- Operator handoff uses the existing coordinate handoff/report protocol.
- No raw issue body is inserted as trusted system instructions.

## Phase 8.3: Worker Assignment

### Goal

Let the operator turn an accepted issue into a concrete implementation task for a coding worker.

### Coordinate Changes

- Add a command or structured report parser for triage decisions:

```text
coordinate issue triage-report <workspace_id> --issue <repo>#<number> --decision assign --worker <agent_id> --task-id <task_id>
```

- Decisions:
  - `ignore`
  - `needs-human`
  - `assign`
- For `assign`, create an implementation task and hand it off to the chosen worker.
- The worker bootstrap must include:
  - issue URL and summary
  - repository path
  - target branch naming convention
  - validation expectations
  - security warning about untrusted issue content

### Acceptance

- Operator can assign a candidate issue to a worker.
- The implementation task has a stable task id and source issue reference.
- Worker bootstrap is generated as a file artifact and referenced by the handoff.
- The Discord handoff message remains a pointer; the bootstrap file remains the source of truth for worker instructions.

## Phase 8.4: Worker Push And PR Creation

### Goal

Close the loop from worker completion to GitHub PR without assuming the coordinate server owns the worker branch locally.

### Required Worker Report Fields

When a worker finishes a GitHub issue task, its closeout/report must include:

- `branch`
- `commit`
- `remote`
- `repo`
- validation summary
- whether the branch has been pushed

### Coordinate Changes

- Add `src/coordinate/prs.py` support for explicit PR creation from a remote branch:

```text
gh pr create --repo <owner/name> --head <owner>:<branch> --base <base> --title <title> --body <body>
```

- Before PR creation, verify remote branch state:

```text
gh api repos/<owner>/<repo>/git/ref/heads/<branch>
```

- If the remote branch SHA does not match the worker-reported commit, block and emit `publish.blocked`.
- If the branch is not pushed, emit `push.required` and hand the task back to the owning worker/host.
- If an open PR already exists for the branch, link it instead of creating a duplicate.

### Acceptance

- PR creation works for an already-pushed worker branch without a local coordinate branch checkout.
- Duplicate PR creation is idempotent.
- Mismatched branch/commit is blocked.
- `pr.created`, `pr.linked`, `push.required`, and `publish.blocked` events render clearly in Discord.

## Phase 8.5: GitHub Driver Loop

### Goal

Automate the mechanical polling and publish checks while keeping judgment and merge gates human/agent-driven.

### Deployment Shape

Tencent Cloud:

```text
coordinate.service
multinexus-discord-bridge.service
coordinate-github-driver.service
coordinate-github-driver.timer
```

Mac/Windows:

```text
agentd processes only
```

### Driver Responsibilities

- Run issue scan for configured own repositories.
- Create triage tasks for new candidate issues.
- Poll task closeout state.
- Verify pushed worker branches.
- Create/link PRs.
- Poll CI/review status using existing coordinate checks.
- Emit events; do not merge.

### Acceptance

- Driver can be run manually first.
- systemd timer can run it repeatedly without duplicate events.
- Driver logs include enough context to debug issue number, task id, branch, PR URL, and event id.

## Phase 8.6: Own-Repo MVP End-To-End Smoke

### Scenario

Use a low-risk issue in `multi-agent-nexus` or `multi-agent-coordinator`.

### Smoke Steps

1. Create or label a test GitHub issue.
2. Run issue scan.
3. Confirm `issue.spotted` event and Discord `[ISSUE]` rendering.
4. Create triage task and hand off to `mac-operator`.
5. Operator assigns to one worker.
6. Worker creates branch and commit.
7. Worker pushes branch from its host.
8. Coordinate verifies branch SHA.
9. Coordinate creates or links PR.
10. CI/review polling works.
11. Human merges or closes manually.

### Acceptance

- The full loop reaches an open PR without manual branch/PR creation.
- Every state transition is visible in coordinate events.
- Discord remains a notification/control surface, not the source of truth.
- Human merge gate remains intact.

## Later: Phase 8.x Fork Workflow

After own-repo MVP:

- Add fork remote management.
- Add branch naming for external repos.
- Add upstream sync checks.
- Add fork permission and token isolation.
- Add PR creation into third-party upstreams.

## Validation Matrix

### Coordinate

- Unit tests for issue scan, idempotency, triage creation, PR creation/linking, branch SHA verification, and driver loop.
- Existing coordinate full suite must remain green.

### Multinexus

- Unit tests for operator config loading if templates or route logic change.
- Existing multinexus full suite must remain green.

### Runtime

- Manual smoke against a test issue.
- Confirm Tencent Cloud systemd driver logs.
- Confirm Mac/Windows agentd are not required to expose inbound network ports.

## Open Questions

- Which label should opt issues into the MVP loop: `bug`, `loop-candidate`, or a dedicated private label?
- Should `mac-operator` run on Mac first, or should an operator agentd eventually run on the server?
- Should PR creation live under `coordinate pr create` only, or should a higher-level `coordinate publish` command own the whole branch verification and PR creation flow?
- How much issue body/comment content should be copied into the worker bootstrap versus summarized by the operator?
