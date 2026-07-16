# P9-3C1 P3 Live Matrix — Independent Bootstrap Review

状态：`APPROVE_ORDERED_OPERATOR_GATES_P0_RECOVER_FORBIDDEN`

日期：2026-07-16 Asia/Shanghai

## 1. Exact reviewed authority

- branch：`agents/fallback/p9-3c1-p3-live-matrix-plan`；
- reviewed HEAD：`bfe7abcc1da4cd3f5ca145aca0f27e345b25fb22`；
- bootstrap：`p9-3c1-p3-live-matrix-operator-bootstrap.md`；
- bootstrap SHA-256：
  `541142443dbdf02d4f4304bc658e0b390fff9d81d2f4dcc4f252655f19844552`；
- approved plan SHA-256：
  `7e8d8846f56d4d62870c63f30705855586adcf34caf2d593f80839952d175fe2`；
- plan-review SHA-256：
  `df73e862c580a562348260719dd1cf693183f68f472331ed8c1f5c9e3b148426`；
- measurement SHA-256：
  `7b84344dccf02d0164565f4a1bc127cb9f5860663cea697e4f64712b6639cf13`。

Any bootstrap byte change invalidates this review and requires a fresh independent session。

## 2. Reviewer identity and evidence

- route：OMP `deepseek/deepseek-v4-pro`；
- tools：`read,grep,glob,bash` only；
- session id：`019f6a03-2a76-7000-83cc-16bc784486e9`；
- native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-bootstrap-review-deepseek-v4-pro/2026-07-16T08-20-20-214Z_019f6a03-2a76-7000-83cc-16bc784486e9.jsonl`；
- completed JSONL SHA-256：
  `e8bd25cdf3630de7b1eef88b1f4e1974cdd77ca58de2450982db0f32a2d8ef86`；
- native model evidence：model-change and all assistant events report
  `deepseek/deepseek-v4-pro`；
- reviewer local gate：controller `47 passed`；
- repo write、SSH、deploy and production mutation：none。

Final machine-readable receipt：

```text
APPROVE
P0/P1/P2: none
INFO: P0 recover systemd probe prefix mismatch is accepted separate code-package debt; current P3 bootstrap does not authorize recover.
Scope: exact bootstrap SHA 541142443dbdf02d4f4304bc658e0b390fff9d81d2f4dcc4f252655f19844552 only; no merge/push/deploy/prepare/auth install/run/cleanup/recover authorization.
```

## 3. Corrected findings

### Blocking findings

`P0/P1/P2: none`。

### INFO-1 — P0 recover unit probe prefix mismatch

`scripts/production-mutation-lock.py` systemd recover probe filters unit names with
`name.startswith("p9-3c1-")`，while the shared fixture helper generates
`p9-3c-fixture-e{1,2}-<run-id>.service`。The process probe still searches `p9-3c1` in command lines，but
the unit probe is not independent defense for these exact units。

Disposition：accepted only as a **separate code-package debt** because normal P3 deploy/prepare/run and
controller cleanup suffix never call P0 `recover`。This bootstrap already forbids manual recovery and
requires a separately reviewed incident route。Current P3 must not call P0 `recover` under any condition。
Before a future runbook may rely on P0 recover for P9-3C1 units，fix/test/review/deploy the probe prefix
or provide an equivalently fail-closed exact-unit implementation through a separate package。

### Withdrawn finding — local `sha256sum`

The initial reviewer report incorrectly said section 9 depends on local macOS `sha256sum`。Both
`sha256sum` invocations are inside the remote command string passed to `ssh`；only `ssh | tee` runs
locally。Same-session correction explicitly withdrew the finding。No bootstrap change was required。

### Accepted INFO

- Remote auth install uses absolute-path `O_EXCL|O_NOFOLLOW` after validating a root:root 0700 parent；
  source SHA is verified before destination creation，then file/dir fsync and exact readback close the
  authority chain。
- Detached deploy worktree precheck is an operator gate rather than an automatic script；nonzero
  `test`/`git worktree add` stops the next step。
- `cmd_cleanup` has no external auth validator and remains behind a new procedural incident gate；it is
  not inferred from this bootstrap。

## 4. Accepted execution conclusions

Independent review and Codex disposition agree that the exact bootstrap：

- preserves user-owned `sessions/` and deploys only from a fresh detached tracked-clean worktree；
- proves no runtime/config/test byte change after `17d0bcc` before no-restart revision alignment；
- uses correct production paths、backup filename and fixture unit identities；
- keeps pre/post deploy、prepare、double read-only and tree stability gates distinct；
- uses schema-13-valid bounded read-only SQL without prompt/result/event payload/env/token/credential；
- builds the exact canonical 11-key auth with one-time basis/final review chain；
- installs remote auth fail-closed with source SHA check、destination O_EXCL and no overwrite；
- requires >=50 minutes before one-shot run，captures pipeline exit and never timeout-kills controller；
- matches five-job/two-unit success residue and all normal failure branches；
- never authorizes speculative cleanup、repair、restart、DB write、global reap or P0 recover。

## 5. Authorization boundary

This independent review is evidence，not user authorization by itself。Combined with the user's standing
goal authorization，it permits Codex to enter bootstrap section 5 and then proceed only through each
freshly satisfied sequential gate。It does not collapse later review/expiry/state checks。

P0 `recover` remains forbidden even in an incident。A held/uncertain lock enters forensic stop and a
separate code/incident package，not recovery under this bootstrap。

P9_3C1_P3_BOOTSTRAP_APPROVED_ORDERED_OPERATOR_GATES_P0_RECOVER_FORBIDDEN
