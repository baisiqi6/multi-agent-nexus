# Phase 8.4: Worker Push And PR Creation

> Source plan for task `phase-8.4-worker-push-pr-creation`.
> Authority: `docs/project-harness/tasks/phase-8-github-automation-loop/plan.md` (Phase 8.4 section).
> This document is the only operator-authored implementation instruction for the worker.

## Goal

Close the GitHub automation loop from worker completion to a real PR without
assuming the Tencent Cloud coordinate server owns a local checkout of the
worker branch.

```text
worker host commit
  → worker host push
  → structured completion report carries repo/branch/commit/remote/validation/pushed
  → GitHub-capable host verifies remote ref SHA via `gh api`
  → existing open PR: link
  → no PR: create then record/link
  → coordinate events + Discord visible result
  → existing CI / review / merge gate continues unchanged
```

Success criterion is **not** "coordinate server has the worker branch locally"
but "based solely on the GitHub remote ref and the worker's reported commit,
coordinate can create or link a PR safely and idempotently".

## In Scope

1. **Worker completion metadata** — extend `daemon.AgentReport` and the
   `agent.reported` event payload to persist `repo`, `branch`, `commit`,
   `remote`, `pushed`, `validation`. Old reports carrying only `summary` /
   `reason` keep working.
2. **Remote branch SHA verification** — add `coordinate.github.fetch_remote_ref`
   using `gh api repos/<owner>/<repo>/git/ref/heads/<branch>`. All calls go
   through an injected runner (testable, never shells out implicitly).
3. **Create-or-link PR publish flow** — add `coordinate.prs.publish_pr`
   (server path: idempotency only, no `gh`) and `coordinate.prs.publish_pr_via_gh`
   (host path: owns `gh pr create` + `gh api`). No new GitHub SDK abstraction.
4. **Three new visible events** — `pr.created`, `push.required`,
   `publish.blocked`. `pr.linked` already exists. All four get policy text,
   Discord embed colour, message_key uniqueness, and tests.
5. **CLI surface** — add `coordinate pr publish <workspace> --task-id ...
   --repo ... --head <owner>:<branch> --base ... --title ... --body ...
   --commit <sha> --pushed true|false --actor ... [--event-cli-path PATH]`
   plus an explicit `[GH-PUBLISH]` host-side wrapper. `--event-cli-path`
   mirrors the Phase 8.1 issue-scan pattern and is the only host/server
   split plumbing we add.
6. **Documentation sync** — `coordinate/README.md`, `docs/runbook.md`,
   `docs/progress.md`, the operator command reference and GitHub integration
   reference, plus `multinexus/docs/agent-report-protocol.md` for the new
   report fields. Multinexus `progress.md` records the closeout; no
   `dogfood-feedback.md` update unless a real dogfood surfaces new findings.

## Out Of Scope

- Not rewriting `ci check`, `review check`, `merge gate`.
- Not implementing `gh pr merge`. Not auto-merging anything.
- Not auto-closing GitHub issues.
- Not implementing the Phase 8.5 driver/timer/systemd unit.
- Not running the Phase 8.6 full real issue → PR smoke unless operator
  explicitly authorizes it later.
- Not adding fork / third-party upstream workflow.
- Not pushing the worker branch from the coordinate server.
- Not requiring a target-repo checkout on the coordinate server.
- Not adding GitHub Actions workflows or branch protection — neither repo
  has `.github/workflows` today; not 8.4 work.
- Not editing real `.env`, tokens, SSH config, `agents.toml`, systemd,
  launchd, NSSM, mihomo.
- Not deploying.
- Not merging or force-pushing the long-lived Phase 8 branch.

## Acceptance Mapping

### A. Already-pushed branch, no local checkout on the executing host

- Input: `repo + branch + commit + pushed=true`.
- Executing host does not need the target repo on disk.
- `fetch_remote_ref` returns a SHA equal to the reported commit → create or
  link PR.

### B. Idempotent create-or-link

- First run with no open PR: exactly one `gh pr create` call, exactly one
  `pr.created` event, exactly one task mirror update.
- Second identical run: discovers the existing PR via `gh pr list`, writes a
  `pr.linked` event (or reuses `pr.created` idempotency), does **not** call
  `gh pr create` again.

### C. Worker has not pushed

- `pushed=false` or remote ref explicitly absent.
- Writes `push.required`. Visible message names the expected owner/host.
- Never calls `gh pr create`.

### D. SHA mismatch

- Remote ref SHA ≠ worker report commit.
- Writes `publish.blocked` with both reported and remote SHAs in payload.
- Never creates or links a PR.

### E. Visible events

- `pr.created`, `pr.linked`, `push.required`, `publish.blocked` all have
  stable text + Discord embed colour + render-mapping tests.
- Reruns do not produce duplicate deliveries or events (idempotency keys are
  unique per (workspace, task, repo, branch, commit, action)).

### F. Existing gates unchanged

- `pr link`, `ci check`, `review check`, `merge gate` keep their existing
  test suites green.
- `merge gate` still returns `human_gate_required=true`; still never merges.

### G. A0 host/server split

- `gh api`, `gh pr list`, `gh pr create` are only invoked from the
  Mac/Windows coding host wrapper (`publish_pr_via_gh` or the host CLI).
- The Tencent Cloud coordinate server is never asked to have `gh` or a
  GitHub token. Server `publish_pr` is record-only / idempotency-only and
  refuses to invoke `gh`.
- A failed `gh` call and a failed remote-CLI record write are reported
  separately; neither returns a fake success.

## Boundary Review

The plan answers six boundary questions before any code is written:

1. **Where does `gh` execute?**
   - Only on Mac/Windows coding hosts, through the host-side wrapper
     `coordinate pr publish ... --event-cli-path /Users/yinxin/.local/bin/coord-ssh`
     (Mac) or `python scripts/coord-ssh-win.py ...` (Windows).
   - Tencent Cloud coordinate never calls `gh`. The server path
     `publish_pr` is record-only: it appends a `pr.linked` /
     `pr.created` event directly to the local DB. It must refuse if asked
     to verify a SHA or run `gh`.

2. **How is the result written back idempotently to the remote DB?**
   - The host CLI invokes `coord-ssh event append <event-type> --workspace-id
     ... --task-id ... --idempotency-key ... --payload-json ...`. The
     event-appender reuses the existing `db.append_event` contract, which
     treats `idempotency_key` collisions as `created=False` rather than
     errors. The event_appender (existing) is reused without modification.

3. **PR is created on GitHub but event record write fails — how does a rerun
   recover without creating a duplicate PR?**
   - Before any `gh pr create`, the host CLI calls `gh pr list --head
     <branch> --state open`. If an open PR already exists for that head, it
     short-circuits to `pr.linked` instead. Even if a transient write failed,
     the next rerun will see the same existing PR and never re-create.
   - The publish idempotency key is derived from
     `(workspace_id, task_id, repo, branch, commit, "publish")`, so re-running
     without an open PR still produces `created=False` and does not duplicate
     events.

4. **Where does `base` come from, and how do we avoid the cross-repo trap
   where one workspace carries many target repos?**
   - The publish CLI requires an explicit `--base` (the GitHub target branch,
     usually the repo default `main`). The workspace's `base_branch` is
     recorded in `branch.allocated` events as audit metadata but is **not**
     used as `--base`. Resolved `base` is written into the event payload so
     later readers see exactly which base was used.
   - If `--base` is omitted, the CLI errors with a clear "must specify
     `--base` explicitly to avoid cross-repo confusion" message.

5. **Which worker fields are audit information vs security gate inputs?**
   - Audit only (recorded, never parsed as shell): `remote`, `validation`,
     `summary`, `reason`, free text.
   - Security gate inputs (parsed, validated, fail-closed on mismatch):
     `repo` (must match `[a-z0-9._-]+/[a-z0-9._-]+`),
     `branch` (must match `^refs/heads/`-safe pattern), `commit`
     (must be 40 lowercase hex), `pushed` (strict `true`/`false`).
   - `pushed=true` with a remote ref that does not exist is **not** accepted
     as "fine, just link" — it stays `publish.blocked` because a missing ref
     contradicts the report.

6. **What is the relationship between `pr.created` and `pr.linked`?**
   - `pr.created` is written when *this run* created the PR on GitHub. Its
     idempotency key includes the PR URL, so a second call with the same
     input never writes a second `pr.created`.
   - `pr.linked` is written when an existing PR was discovered and bound to
     the task, or when an explicit `pr link` operation succeeded. It is also
     reused when a subsequent run discovers the same PR that an earlier
     `pr.created` produced.
   - Both events update the task mirror with the PR URL. The merge gate
     keys off the task mirror's `pr` column, not the event type.

## Steps

1. Branch + worktree (already done — see session bootstrap).
2. Read source files listed in the implementation handoff Step 4.
3. Implement coordinate changes in this order (each step has tests):
   1. `coordinate.github.fetch_remote_ref` + tests.
   2. `coordinate.prs.publish_pr` (server record-only) + tests.
   3. `coordinate.prs.publish_pr_via_gh` (host GH orchestrator) + tests.
   4. CLI surface (`coordinate pr publish`) + handler + tests.
   5. `policy.SUPPORTED_EVENT_TYPES` + text renderers + Discord styling +
      tests.
   6. `daemon.AgentReport` field extension + payload persistence + tests
      (backward-compatible with old reports).
   7. Documentation sync.
4. Validation:
   - targeted suite `test_prs test_cli test_daemon test_policy
     test_discord_rendering test_ci test_reviews`.
   - full suite `unittest discover -s tests -p 'test_*.py'`.
   - `scripts/harness/harnessctl validate`.
   - `git diff --check`.
5. Read-only GitHub smoke (no writes):
   - `gh api repos/<owner>/multi-agent-coordinator/git/ref/heads/<branch> --jq .object.sha`
   - `gh api repos/<owner>/multi-agent-nexus/git/ref/heads/<branch> --jq .object.sha`
   - `gh pr list --repo ... --head <branch> --state all`
6. Commit + push both task branches. No deploy. No merge.
7. Closeout report as described in the implementation handoff.

## Verification

- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'` passes.
- `scripts/harness/harnessctl validate` passes.
- `git diff --check` is clean on both repos.
- Multinexus full suite `python -m unittest discover -s tests` passes
  (no multinexus runtime change is expected).
- Targeted GitHub read-only smoke matches the SHA expected from the worker
  report.

## Exit Criteria

- All Acceptance Mapping items pass.
- All Out Of Scope items remain untouched.
- Branch pushed on both repos; commit SHAs recorded in the closeout report.
- No real GitHub write operation was performed (read-only smoke only).
- Harness state preflight repair recorded in `multinexus/progress.md`.
- Final visible message ends with the unfenced, parseable `[agent-report]
  action=done ...` line described in the handoff.
