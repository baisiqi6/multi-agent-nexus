# P9-3C1 P3 Retry Incident IR-B — KAT Worker Attempt Review

状态：`REJECTED_BEFORE_IMPLEMENTATION_CANDIDATE_ALL_KAT_BYTES_FORBIDDEN`

日期：2026-07-17 Asia/Shanghai

## 1. Exact attempt authority

- Worker：OMP `kat-coder/kat-coder-pro-v2.5`。
- Exact base：`967cf043bc34efd473f9e4d9367159908bb0d86f`。
- Branch：`agents/kat/p9-3c1-p3-retry-incident-ir-b-r1`。
- Worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p3-retry-incident-ir-b-kat-r1`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-b-worker-kat-coder-pro-v2.5/2026-07-16T19-06-45-491Z_019f6c52-fb73-7000-86e8-c8075b660718.jsonl`。
- JSONL SHA：`2f2bd92da7b12dc915f264114939f293145ea51408b12649df2f9009bba093f0`。
- Final worker tree：uncommitted；77 controller insertions and 320 test insertions across the two allowlisted
  paths；no candidate commit、push、merge or production access。

## 2. Rejection findings

### P1 — test-first order was violated

The worker initially planned “controller changes，then tests” and had to be interrupted before edits。After the
first correction it wrote tests that asserted new functions/constants did **not** exist or expected the new parser
to reject `resume-cleanup`，so those tests would fail after a correct implementation。After the second correction
it still added controller constants/path helpers before a valid four-block negative run。

### P1 — negative tests repeatedly stopped at invalid fixtures

The first test set used non-hex token/SHA characters、forged catalog hashes/paths/rows、a non-authoritative ledger
shape and no-op/name-only assertions。It was discarded before execution。

The replacement run selected six tests，not four。Two consecutive terminal-catalog runs stopped before the
catalog decision：first because the standard token path was absent，then because the lock-status fixture lacked
the required owner/action/token match。Neither run proved that the old runtime emitted forbidden v3/v2/v4 syncs。
The JSONL nevertheless stated that all four core tests were “real runtime failures” and proceeded to runtime
implementation。

### P1 — the required gate remained incomplete

No valid terminal-sync negative proof existed；the post-install test had not yet proved a complete real
stale→archive/new→standard transaction；the 18-key、catalog rejection、15-field pre-acquire and failure-boundary
matrices were absent。Only the old baseline controller suite ran successfully (`47 passed`)。No focused final、
deploy-contract or full-suite acceptance run exists。

## 3. Disposition

The worktree and JSONL remain immutable evidence。No changed byte、test fixture、helper name or partial design from
this branch may be copied/applied/cherry-picked into a replacement。The branch must not be committed、amended、
merged、pushed、deployed or used as a new worker base。

The approved IR-B plan remains valid。A replacement worker must use a fresh clean worktree from current reviewed
main and a new independently reviewed correction bootstrap。Because the failure was specifically test-gate
discipline，the replacement bootstrap must split work into：tests-only checkpoint → Codex validation of exact
negative reasons → explicit implementation continuation。

No P0 recover/release、source streaming、token retirement、cleanup/resume、deploy、SSH、service/DB/catalog mutation
or other production action is authorized。

P9_3C1_P3_RETRY_INCIDENT_IR_B_KAT_WORKER_ATTEMPT_REJECTED_BEFORE_IMPLEMENTATION_CANDIDATE_ALL_KAT_BYTES_FORBIDDEN
