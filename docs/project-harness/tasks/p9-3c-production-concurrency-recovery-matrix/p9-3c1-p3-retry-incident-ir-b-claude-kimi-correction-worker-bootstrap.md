# P9-3C1 P3 Retry Incident IR-B — Claude-hosted Kimi Correction Worker Bootstrap

状态：`DRAFT_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Role and replacement boundary

You are the replacement non-Codex Coding worker，invoked through Claude Code's local `sonnet` slot，which the
operator has configured for Kimi-for-coding。Invoke exactly `claude --model sonnet`；never use `opus`。Codex
remains architect/operator/test-gate reviewer/result reviewer。

This bootstrap supplements，but does not weaken：

- approved IR-B detailed plan and plan review；
- approved original IR-B worker bootstrap and bootstrap review；
- rejected KAT attempt review。

Read all five completely。The KAT branch/JSONL is negative evidence only：do not read its uncommitted source/test
diff，copy helper names，apply patches or reuse its worktree。

No SSH/network、production/state-root/token/auth/DB/service access、P0 recover/release、cleanup/resume invocation、
deploy、push/merge、sessions read or subagents。The worker may write only its Claude native stream JSON output to
the operator-supplied session path；it must never open that path。

## 2. Fresh base and allowlist

The operator supplies exact `WORKER_BASE` after this correction bootstrap and its review are pushed。Require：

```bash
test "$(git rev-parse HEAD)" = "$WORKER_BASE"
test "$(git rev-parse origin/main)" = "$WORKER_BASE"
test -z "$(git status --short)"
git diff --quiet 6ba82a90d3cf0390eba97c472d8eff62261a9d90.."$WORKER_BASE" -- \
  scripts multinexus tests config agents.toml
```

Expected fresh assignment：

- worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p3-retry-incident-ir-b-claude-kimi-r1`；
- branch：`agents/claude-kimi/p9-3c1-p3-retry-incident-ir-b-r1`；
- parent：exact launch-time `WORKER_BASE`。

Only：

- `scripts/p9_3c1_controller.py`；
- `tests/test_p9_3c1_production_controller.py`；
- `tests/test_deploy_contract.py` only for one dynamic installed-controller invariant if genuinely needed。

No shell/helper/config/deploy/Coordinate/schema/docs/session change。

## 3. Mandatory two-gate test-first protocol

Do not edit runtime during either test gate。The operator launches/resumes the same Claude session in three named
turns。Each tests-only turn stops without a commit after reporting exact failures。

### Gate T1 — four core behavioral tests only

Edit only `tests/test_p9_3c1_production_controller.py`。Add final-behavior tests for：

1. parser and dispatch accept exact `resume-cleanup` args；
2. terminal cleanup skips all three catalog sync calls；
3. `_acquire_global_lock(run_id)` acquires a valid new token while the stale standard token remains byte-identical；
4. a narrow transaction primitive executes stale→archive and temp→standard itself，then an injected cleanup
   failure preserves archived old token、new standard token、held global lock and zero release。

Run only those tests against unchanged runtime。Every selected failure must be due to missing/wrong runtime
behavior。If any stops at fixture/path/owner/lock/ledger/catalog/SQL error，fix the **test only** and rerun。Stop
and output `T1_READY_FOR_CODEX_REVIEW`；do not edit runtime。

#### Required T1 fixture discipline

- use only valid lowercase hex tokens/SHA values (`a` through `f` and digits)；
- use `_prepare_fresh()`，then real adjacent `_transition_to()` calls through `agents-online`，then
  `_append_ledger(..., "machine.failure")` and `_append_ledger(..., "cleanup.initiated")`，and assert exact
  eight-record valid chain/tail before the behavior under test；
- for terminal-sync proof，use `_install_live_fake()`，set its terminal versions，call ordinary `_acquire_lock()`，
  monkeypatch module `_sync_executor/_sync_capacity` directly，and inject a future classifier seam returning
  `TERMINAL_SKIP` with `raising=False`。Current runtime must reach the sync calls and fail only because the list is
  non-empty；
- global-acquire seam must be stateful：free before acquire，held with exact owner/action/token match afterward；
- transaction test must not pre-create archive/new standard。The primitive under test performs both renames。

No `assert not hasattr`、expected parser `SystemExit`、placeholder/no-op test、source-text assertion or test-only
constant qualifies。

### Gate T2 — complete reviewed matrix，still tests only

Only after Codex sends exact `T1_APPROVED_CONTINUE_TESTS_ONLY`，add all remaining dynamic tests from plan §12 and
original bootstrap §12：

- fd root authority/canonical receipt/stale token and sealed-TOML stable identity；
- exact 18-key contract/type/digest/canonical/expiry/nonce/manifest/live-auth/revision/hash/ledger/receipt/copy/
  replay/file+dir-fsync failures；
- full positive lower Cartesian catalog matrix、terminal skip and every malformed/duplicate/bool/path/hash/row/
  policy/partial/higher rejection；
- all fifteen pre-acquire fields，including bounded unit/process argv cases；
- acquire race/unknown authority；every archive/temp/write/chown/chmod/fsync/rename/reproof/rollback boundary；
- every post-install auth/catalog/helper/agent/DB/evidence/phase/release failure；
- ordinary acquire/run/cleanup/state-machine and parser compatibility；raw-token non-disclosure。

Positive catalog snapshots must be generated from the exact manifest-bound sealed TOML semantic authority；never
invent placeholder hash/path/definition/policy ids。Use an explicit catalog snapshot seam for impossible
duplicate/malformed rows。External auth/receipt/token fixtures use fd-valid paths and controller owner-mode seams。

Run the new test selection on unchanged runtime。Missing-function failures are acceptable only after Codex has
read the fixture and confirmed the assertion would pass on a correct implementation。Fix every fixture-first
failure。Stop with `T2_READY_FOR_CODEX_REVIEW` and no runtime edit/commit。

### Gate I — implementation

Only after Codex sends exact `T2_APPROVED_IMPLEMENT` may runtime be edited。Implement the complete reviewed plan，
make T1/T2 and all existing tests pass，then create one final commit。

## 4. Runtime requirements after T2 approval

Implement the original approved bootstrap exactly，including：

- fd-stable root authority readers and fixed receipt/auth/temp/archive paths；
- separate 18-key resume contract，bare versus prefixed digest validators and `hmac.compare_digest`；
- one-shot fixed `O_EXCL|O_NOFOLLOW` auth copy，never deleted/repaired，guarded before every mutation；
- sealed-TOML stable fd reads，manifest byte hashes，derived semantic catalog hashes/policy ids；
- exact `LOWER_MONOTONIC`/`TERMINAL_SKIP` classifier before mutation；
- fresh fifteen-field pre-acquire proof；
- bounded unit/process probes with exact NUL argv classification；
- `_acquire_global_lock()` split while ordinary `_acquire_lock()` behavior remains；
- explicit new-lock/stale-archive transaction with safe pre-install rollback and no post-install release；
- no duplicate incident `cleanup.initiated` and a live fixed-auth guard before every suffix mutation；
- exact parser/dispatch and unchanged thin shell。

Do not weaken runtime to satisfy a fixture。If an approved test conflicts with the plan，stop and report the exact
conflict rather than broadening authority。

## 5. Gates and commit

Canonical Python：`/Users/yinxin/projects/multinexus/.venv/bin/python`。

After implementation：

```bash
/Users/yinxin/projects/multinexus/.venv/bin/python -m py_compile \
  scripts/p9_3c1_controller.py tests/test_p9_3c1_production_controller.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q \
  tests/test_p9_3c1_production_controller.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q tests/test_deploy_contract.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q
bash -n scripts/p9-3c1-production-verify.sh
git diff --check
git diff --name-only "$WORKER_BASE" --
git diff -- scripts/p9-3c1-production-verify.sh scripts/production-mutation-lock.py
```

Full-suite timeout at least 20 minutes；timeout is not PASS。Last diff must be empty and all paths allowlisted。

Create exactly one commit with parent `WORKER_BASE` and subject：

```text
fix(p9-3c1): add reviewed incident cleanup resume
```

Do not amend、push、merge、deploy or touch production。Final report includes native model evidence、base/commit/
parent/subject/paths/diffstat，T1/T2 exact negative evidence，all final gate counts and transaction/catalog
semantics。Worker completion is not acceptance。

P9_3C1_P3_RETRY_INCIDENT_IR_B_CLAUDE_KIMI_CORRECTION_BOOTSTRAP_DRAFT_FOR_INDEPENDENT_REVIEW_LOCAL_IMPLEMENTATION_BLOCKED
