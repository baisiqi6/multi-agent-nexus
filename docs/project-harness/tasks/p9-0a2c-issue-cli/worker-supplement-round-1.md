# P9-0A2c Worker Supplement — Round 1

This supplement overrides generic/stale instructions in `worker-bootstrap.md`.

## Exact execution identity

- Implementation repo/worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a2c-kimi`
- Required branch: `agents/mac-omp/p9-0a2c-issue-cli`
- Required start: `38da30f8bb508638e0cc30c301968153a420bdb7`
- Control/source-plan repo: `/Users/yinxin/projects/multinexus`
- Exact plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a2c-issue-cli/plan.md`
- Exact plan SHA-256:
  `d5ff4620afc7799bcc050c960bd1491f82a136ec829431f92d04e021bb88d444`
- Approved review:
  `docs/project-harness/tasks/p9-0a2c-issue-cli/plan-review-round-1.md`
- Logical assignment session: `p9-0a2c-kimi-20260712T1109Z`

`/opt/multinexus`, `feature/multi-bot`, and `~/projects/coordinate` in the generic
bootstrap are not implementation authority. Do not switch to them or edit MultiNexus.

## Exact allowed paths

- `src/coordinate/cli.py`
- `src/coordinate/issue_cli.py` (new)
- `tests/test_cli_contract.py`
- `tests/fixtures/cli_contract.json`
- `tests/test_issue_cli.py` (new)
- `tests/test_cli.py` only if a narrow compatibility assertion demonstrably cannot
  live in `test_issue_cli.py`

Do not modify `issues.py`, another production/test module, packaging, schema, docs,
harness state, `.qoder/`, or generated local noise. Stop if another path is required.

## Required implementation

1. Verify exact cwd/branch/start and clean worktree, plan SHA, focused 265 and full
   1,411 preflight tests before editing.
2. Add static `coordinate.issue_cli` with one `register_issue_commands(subcommands)`
   registrar and move exactly five handlers mechanically.
3. Keep direct root handler aliases, exact issue position after merge/before job, and
   remove only issue-only root service imports.
4. Preserve `--event-cli-path` bypass of `_conn`, combined materialize semantics,
   files-only filesystem + `/opt` guard, and record-only DB/event behavior.
5. Extend contract proof in three layers:
   - C rewind -> `adddac8bd623b20a1f8b0f931e0ae83a45148315652c220d6f70c276f0f7cc74`;
   - C+B -> `652a77d5ee7ab2239b7e2a406560ae21ada4d93b7f7c076fa7c65d6e0aa3f048`;
   - C+B+A2a -> `83c4c1819ddaed6c823c2a38fb1410a69d4b0a767c8d8cf046cb1bd3ce64ff94`.
   Reject missing/unapproved owners and non-handler drift; never self-bless a fixture.
6. Add boundary/delegation tests. Patch the actually called `coordinate.issue_cli._conn`
   or issue service symbol and assert calls; never let a mock silently fall through to
   live SQLite/GitHub/SSH.
7. Compare all five new handler AST bodies to exact start `38da30f` and record evidence.

## Required validation

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_issue_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_cli tests.test_planning_cli tests.test_issues
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
git diff --check
```

Record exact before/new fixture SHA, all three rewind hashes, 21/75/99, focused/full
counts, alias identities, import orders, event-CLI no-local-DB proof, split boundaries,
AST equality, and changed paths.

## Authority boundaries

- Do not run assignment/lifecycle, Discord delivery, deploy, restart, SSH, push, merge,
  PR, live GitHub, or live DB commands.
- Do not edit MultiNexus plan/progress/checklist/bootstrap artifacts.
- Do not self-approve or request closeout. Commit one local implementation only after
  validation, then report to Codex.
- Kimi is preferred. If quota/auth/provider fails, stop with evidence; Operator may
  resume with GLM. Do not silently change model.
