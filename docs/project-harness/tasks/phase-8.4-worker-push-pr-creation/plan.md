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
3. **Publish flow** — add `coordinate.prs.publish_pr` (the host-side
   orchestrator: validates, fetches remote ref via `gh api`,
   discovers existing PR via `gh pr list`, then either links or
   creates via `gh pr create`). All `gh` calls go through an injected
   runner. The CLI exposes `coordinate pr publish <workspace>` for the
   host and `coordinate pr publish-record <workspace> --result-json <json>`
   plus `coordinate pr publish-preflight <workspace> --repo ...
   --branch ... --commit ... --task-id ...` as a record-only /
   read-only sink for the remote DB. The remote sink recomputes
   `event_type` / `idempotency_key` / event payload from the host's
   minimal facts (it never trusts the host envelope for those); it
   writes the event + mirror upsert inside a single SAVEPOINT so a
   partial failure leaves no half-state; it re-validates the mirror
   so a replay repairs missing mirror rows.
4. **Three new visible events** — `pr.created`, `push.required`,
   `publish.blocked`. `pr.linked` already exists. All four get policy text,
   Discord embed colour, message_key uniqueness, and tests.
5. **CLI surface** — `coordinate pr publish <workspace>` on the host
   (default: runs `publish_pr` locally); `--event-cli-path` forwards
   the host's PublishResult JSON to a remote `pr publish-record`
   invocation; `--preflight-event-cli-path` runs a remote
   `pr publish-preflight` BEFORE any `gh` call so a remote mirror
   conflict short-circuits the host without writing to GitHub.
   `--event-cli-path` mirrors the Phase 8.1 `issue scan` pattern and is
   the only host/server split plumbing.
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

### G. A0 host/server split (record-only remote sink)

Two distinct CLI subcommands implement the split. Neither ever shells
out to `gh` from the server.

- `coordinate pr publish <workspace> ...` runs on the Mac/Windows
  coding host. Default mode (no `--event-cli-path`) executes
  `publish_pr` against the host's local DB, which is the only path
  allowed to call `gh api` / `gh pr list` / `gh pr create`.
- With `--event-cli-path`, the host first runs `publish_pr` locally
  and then forwards the resulting `PublishResult.to_dict()` JSON to a
  remote `coordinate pr publish-record <workspace> --result-json ...`
  invocation.
- `coordinate pr publish-record` is a record-only sink. It runs on
  Tencent Cloud `/opt/coordinate` (or any other DB-bearing host). It
  re-validates the host's claim against the local task mirror, appends
  the event using the host-supplied `idempotency_key`, and on
  `action in {created, linked}` upserts the local task mirror with
  the resolved PR URL. It never invokes `gh`.

The `merge gate` reads whichever DB the operator / CI is configured
to read. In A0 the merge gate runs on the server, so the remote
record-only sink is what makes `tasks.pr` visible to it.

`head_owner` must equal the repo owner — fork workflow is out of
scope, and a mismatched `head_owner` would create a PR pointing at a
different fork that `fetch_remote_ref` cannot see. Mismatches
fail-closed as `publish.blocked (head_owner_mismatch)`.

`.py` event_cli paths are auto-prepended with `sys.executable` so the
Windows coding host (`coord-ssh-win.py`) spawns correctly without
hardcoding `python` in worker scripts.

## Boundary Review

The plan answers six boundary questions before any code is written:

1. **Where does `gh` execute?**
   - Only on the Mac/Windows coding host that runs `coordinate pr publish`
     **without** `--event-cli-path` (or with `--event-cli-path` whose
     remote coord CLI is itself a host wrapper — never `/opt/coordinate`).
     All `gh api`, `gh pr list`, `gh pr create` calls happen in
     `coordinate.prs.publish_pr` on that host.
   - Tencent Cloud `/opt/coordinate` never calls `gh`. The
     `coordinate pr publish` CLI in the server runtime must not be
     invoked with `gh`-relevant parameters; if it is, the gh runner
     surfaces `gh_missing` and `publish.blocked (gh_missing)` is
     recorded. The server copy of `coordinate` is a pure event sink.

2. **How is the result written back idempotently to the remote DB?**
   - The host runs `coordinate pr publish` locally. After
     `publish_pr` produces a result, if the operator passes
     `--event-cli-path PATH`, the CLI forwards the host's full
     `PublishResult.to_dict()` JSON to a remote
     `coordinate pr publish-record <workspace> --result-json <json>`
     invocation.
   - The remote sink is `record_publish_result(conn, workspace_id,
     result)`. It is **deliberately paranoid**: it does not trust the
     host's `event_type` / `idempotency_key` / event payload. It
     recomputes the canonical `event_type` from the action
     (`created`→`pr.created`, `linked`→`pr.linked`,
     `push_required`→`push.required`, `blocked`→`publish.blocked`),
     the `idempotency_key` from `(workspace_id, task_id, event_type,
     repo, branch, commit, extra)`, and the event payload from the
     action + minimal facts.
   - `event append` and (on success) `upsert_task_mirror` run inside
     a single SAVEPOINT so a partial failure rolls back both writes.
     On replay, even if `event_created=False`, the sink re-upserts
     the mirror from the host's facts if the row is missing (so a
     transient half-completion can be repaired by a retry).
   - The remote side never sees another `pr publish` invocation
     (no nested publish) and never invokes `gh`.

3. **Does the host ever create a PR whose record the remote will refuse?**
   - No. When `--preflight-event-cli-path PATH` is set, the host runs
     a remote `coordinate pr publish-preflight <workspace> --repo ...
     --branch ... --commit ... --task-id ...` BEFORE any `gh` call.
     The remote preflight is a read-only check; if the remote
     returns `ok=false` (mirror_conflict / unknown_workspace /
     invalid_result), the host short-circuits with
     `publish.blocked` and exits 1 without invoking `gh`. This is
     what guarantees "no GitHub write happens before the remote
     state has been re-validated".
   - The publish idempotency key is derived from
     `(workspace_id, task_id, event_type, repo, branch, commit, extra)`,
     so re-running after a transient write failure produces
     `event_created=False` and does not duplicate events. Replays
     also re-upsert the remote mirror from the host's facts so a
     partial half-completion can be repaired.

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
