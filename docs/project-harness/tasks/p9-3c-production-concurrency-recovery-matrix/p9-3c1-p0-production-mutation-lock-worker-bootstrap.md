# P9-3C1 P0 Shared Production Mutation Lock — Worker Bootstrap

> **状态：draft；必须先经独立 exact-SHA bootstrap review。** 本文件现在只授权 review，
> 不授权 coding、commit、push、merge、deploy、SSH、production mutation、service restart、
> DB/catalog/job/lease/fixture 操作。独立 reviewer 返回 `APPROVE` 后，才授权下面严格限定的
> MultiNexus 本地实现与一个 local commit；其他操作仍然禁止。

日期：2026-07-15 Asia/Shanghai

## 1. Authorization chain

- Approved measurement SHA-256：
  `cd57fcdbb1a3ec9a3f9478f95f068d2378653c233646f14a5167253405fb9214`。
- Approved P9-3C1 detailed plan SHA-256：
  `b9a4fc51aa56a8656b6bda4b4aff5f784171855da928baa7c83c3b540696f190`。
- Independent plan review：`p9-3c1-production-plan-review-round2.md`。
- Plan verdict：`APPROVE`，且只授权生成本 P0 bootstrap。
- MultiNexus implementation base：
  `d09e0f8fba0f6d189934173027ca5a756e5f36ce`。
- Coordinate dependency（只读，不修改）：
  `9804bbd74c4b826d0620c5939b00e01be9c1120d`。

本 bootstrap 不得自我授权。任何内容修改都会改变 SHA-256，并使旧 bootstrap review 失效。

## 2. Worker、model 与 evidence

Primary route：

- Outer worker：Claude Code，固定 `--model sonnet`，禁止 Opus；
- intended provider-native model：`kimi-for-coding`；
- worker 开始前必须从 assistant JSONL event 确认
  `message.model = kimi-for-coding`；UI label、CLI 参数或 system init model 都不是证明。

Quota-only fallback route：若 primary route 在任何 repo write 前返回 explicit quota/auth
failure（例如 Kimi billing-cycle `403`），operator 保存原始失败 JSONL 后，可以按下面顺序启动
新的独立 session；不得在同一 session silent model switch：

1. OMP `minimax-code-cn/MiniMax-M3`，native JSONL 必须同时证明
   `provider=minimax-code-cn`、`model=MiniMax-M3`；
2. OMP `deepseek/deepseek-v4-pro`，只在 MiniMax unavailable/limited 时使用，native JSONL 必须
   同时证明 `provider=deepseek`、`model=deepseek-v4-pro`。

Fallback 只改变 coding worker route，不改变 exact scope、allowlist、tests、commit 或 hard gates；
不能把较弱模型的报告当作降低 reviewer bar 的理由。若 primary failure 发生在 repo write 后，或
actual route 不在上面 exact allowlist，立即停止并由 Codex 做 dirty-state audit，不得继续写。

保存每次尝试的完整 stream JSONL、session id、outer route 与 actual provider model。Codex 是
architect/operator/final reviewer；worker 不自行扩大 scope 或批准结果。

## 3. Exact repo / branch / worktree

- Repository：`/Users/yinxin/projects/multinexus`。
- Base branch：`main`。
- Exact base SHA：`d09e0f8fba0f6d189934173027ca5a756e5f36ce`。
- Required worker branch：
  `agents/fallback/p9-3c1-production-mutation-lock`。Branch 只表达本次使用 approved quota
  fallback，不绑定某个 fallback model；actual MiniMax/DeepSeek route 必须由 native JSONL 与
  completion receipt 精确记录，不得伪装为 Kimi 或另一个 model。
- Required isolated worktree：
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-production-mutation-lock`。

Operator 在 bootstrap approval 后从 exact base 创建 worktree/branch。Worker 开始时必须
核验 `HEAD`、branch、worktree path 与 clean status；任何不一致都停止。不得在 main checkout
实现，不得读取或修改任何 `.qoder/`、credential、runtime `agents.toml` secret、production
DB 或用户未跟踪文件。

## 4. P0 goal and non-goals

目标是在 production host 建立一个 server-owned、atomic、token-fenced mutation lock，供：

- `scripts/deploy-server.sh coordinate|multinexus|all`；
- 后续 P9-3C1 controller（P2 实现，本包不实现）

共同使用。它必须让 concurrent deploy/matrix task lines fail closed，并覆盖 deploy 的完整
mutation window，包括 first staging/copy、snapshot/sync、install、version write、restart、
smoke、rollback 与 cleanup。

P0 不实现：

- Coordinate exact reap、claim reap policy 或 agent deactivate（P1）；
- P9-3C1 controller/config/unit/catalog/job/lease/fixture（P2/P3）；
- schema/migration/DB changes；
- provider/Discord/KOOK behavior；
- production activation、live lock recovery 或 deploy execution。

## 5. Exact changed-file allowlist

Worker 只允许修改以下四个文件：

1. `scripts/production-mutation-lock.py`（new，mode `0755`）；
2. `scripts/deploy-server.sh`；
3. `tests/test_production_mutation_lock.py`（new）；
4. `tests/test_deploy_contract.py`。

不得修改 project-harness docs、planning files、Coordinate repo、requirements、packaging、
systemd units、runtime config、registry authority、snapshot helper 或其他 tests。若实现需要第
五个文件，停止并返回 bootstrap deviation；不得 silent widen。

## 6. Lock authority and filesystem contract

### 6.1 Fixed production paths

- Lock directory：`/run/lock/coordinate-production-mutation.lock`。
- Metadata：`/run/lock/coordinate-production-mutation.lock/owner.json`。
- Installed helper：`/usr/local/sbin/coordinate-production-mutation-lock`。
- Recovery audit：`/var/log/coordinate-production-mutation-lock-recovery.jsonl`。

CLI production paths必须是 code constants；不得提供普通 CLI flag/env 让 caller 重定向
lock/audit path。Tests 通过 importable core functions 与 injected temp paths/system probes，
不能依赖修改 production constants 或 root filesystem。

### 6.2 Root and inode authority

- `acquire/release/recover` 要求 effective uid `0`；非 root 在任何 filesystem mutation 前
  fail closed。
- Lock directory 必须由 root 创建、owner/group `0:0`、mode `0700`、非 symlink、link count
  与类型符合 ordinary directory contract。
- `owner.json` 必须 root-owned、mode `0600`、ordinary file、非 symlink、single link；使用
  `O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW`（platform support fail closed），写后 `fsync` file 与
  parent directory。
- Helper 设置 restrictive umask；不得 follow symlink、替换未知 inode、递归删除或使用
  `rm -rf`。
- Existing file/symlink/directory authority mismatch 一律返回 bounded invalid/blocked result，
  zero mutation。

### 6.3 Metadata and token

`owner.json` 使用 canonical compact JSON，exact keys：

```text
contract_version
token
owner
action
owner_host
owner_pid
started_at
phase
```

- `contract_version=1`，`phase=held`。
- Token 使用 `secrets.token_hex(32)`，只允许 64-char lowercase hex。
- `owner/action/owner_host` 与 recover reason 都必须 type-safe、strip-stable、bounded、无
  control chars；`owner_pid` 必须 positive integer-not-bool。
- Timestamp 是 UTC `Z` canonical form。
- `acquire` 的 stdout 是单个 canonical machine-readable JSON object；token 只在 successful
  acquire result 中返回。不得把 token 写入普通 info/error log。
- `status` 默认只返回 token digest/prefix，不回显 raw token；可用 exact
  `--expect-token <token>` 做 read-only ownership validation，但 response 只返回
  `token_matches=true|false`。

### 6.4 Acquire semantics

- `acquire --owner ... --action ... --owner-host ... --owner-pid ...` 使用 atomic final-path
  `mkdir` 获得唯一 authority。
- 已存在 valid lock 返回 `state=blocked` 与 redacted owner/action/start/phase；不得更新
  timestamp/metadata，不得 steal。
- 已存在 invalid authority 返回 `state=invalid` nonzero；不得 repair/delete。
- Metadata creation/write/fsync failure 只能清理由本次 invocation 创建且仍可证明拥有的空/
  partial authority；若 identity 无法证明则保留 loud invalid lock，不猜测成功。
- 两个 concurrent acquire 必须 exactly one success、one blocked；不能 last-writer-wins。

### 6.5 Status semantics

- `status` strictly read-only，可由 `deploy-server.sh status` 通过 `sudo` 调用。
- Absent 返回 `state=free, phase=free`；valid 返回 redacted owner/action/start/phase；invalid
  返回 nonzero structured result。
- Status 不创建 helper、lock、metadata、audit log，不 chmod/chown，不刷新时间，不释放锁。
- `--expect-token` mismatch 也是 read-only，不能改变 exit 前后 stat/content。

### 6.6 Release semantics

- `release --token <exact-token>` 必须重新 `lstat` directory/file、重读并 canonical validate
  metadata、constant-time compare token，然后只 unlink exact `owner.json` 并 `rmdir` exact
  lock directory。
- Unknown/malformed/mismatch token、inode/metadata drift、extra directory entry 或 authority
  mismatch 全部 nonzero、zero mutation；不得根据 owner/action/age 释放。
- Successful retry after lock absent 返回 stable `already_free` only when caller明确传
  `--allow-already-free`；deploy normal path不使用该 flag掩盖 duplicate release。

### 6.7 Explicit recover semantics

`recover` 是 incident-only，不由 deploy 自动调用：

```text
coordinate-production-mutation-lock recover \
  --token <exact-stale-token> \
  --operator <bounded-id> \
  --reason <bounded-reason> \
  --confirm-owner-stopped
```

- 不提供 age-based recovery/timeout/force/steal。
- 必须 exact token、explicit confirmation、valid reason/operator；缺一 zero mutation。
- Helper 必须通过 injectable exact probes 证明无 active/activating/deactivating
  `p9-3c1-*` systemd unit，且无 matching P9-3C1 controller/process；probe unavailable/error
  fail closed。
- Recovery audit 使用 root-owned mode `0600` append-only JSONL；记录 lock metadata digest、
  operator、reason、recovered_at，不记录 raw token。Audit append/fsync 失败不得释放锁。
- 只有 audit durable 后才能 exact release。Recovery output 返回 receipt digest；不得删除或
  改写历史 audit。

P0 tests只在 temp paths/fake probes 中验证 recover；worker 不得在 server/live lock 上运行。

## 7. Deploy integration contract

### 7.1 One invocation, one token

- `coordinate`、`multinexus`、`all` 每次 script invocation 最多一次 acquire、一次 release。
- `all` 必须同一 token 覆盖 Coordinate + MultiNexus + final smoke，不能 component 间释放。
- Local-only repo/authority validation 可在 acquire 前运行；第一个 remote filesystem/catalog/
  service mutation 必须发生在 lock acquired + helper installed/validated 之后。
- `--allow-dirty` 不绕过 lock。`--skip-install`、`--no-restart`、`--no-smoke` 仍持锁；只有
  component `status` 是 read-only/no-acquire。

### 7.2 First-install bootstrap without an unlocked copy window

不能假设 installed helper 已存在。每次 mutation deploy 使用当前 reviewed local
`scripts/production-mutation-lock.py` source，经 SSH stdin 直接执行：

```text
sudo python3 - acquire ...
```

该 streaming execution 在 server filesystem 的唯一 mutation 是 helper 自己的 atomic lock
acquire；不得先把 helper 或 repo 写到 `/tmp`/`/opt`/`/usr/local`。

Acquire 成功后，在同 token 下：

1. 将 exact local helper bytes 写入 root-owned same-directory temp file；
2. `fsync`、chmod/chown `0755 root:root`；
3. atomic replace `/usr/local/sbin/coordinate-production-mutation-lock`；
4. 比较 local/installed SHA-256；
5. 通过 installed helper `status --expect-token` 验证它读到同一 token/metadata。

任一步失败都不得开始 staging/copy。Release primary path使用已验证 installed helper；如果
install/validation 失败，可只使用同一次 reviewed streamed helper bytes + exact token 做
bounded release fallback，并必须输出 loud fallback marker。不得因 installed helper missing
而留下 silent unlocked deployment，也不得在未持锁时 install helper。

### 7.3 Mutation window and ordering

Lock 必须早于：

- `sync_to_remote_staging` 的 remote `rm/mkdir/tar extract`；
- source/config backup、capacity snapshot；
- `/opt/coordinate` 或 `/opt/multinexus` rsync/copy/chown；
- venv/pip install；
- registry/executor/capacity sync；
- `VERSION_DEPLOYED` write；
- systemd daemon-reload/restart；
- any rollback/restore/cleanup mutation。

Release 必须晚于 successful final smoke；若 `--no-smoke`，晚于最后一个 requested mutation。
Failure path 必须先完成 existing bounded rollback/artifact cleanup，再尝试 exact release。
Release failure使整个 deploy nonzero并保留 lock，不能把 deploy 标记成功。

### 7.4 Trap ownership

当前 `deploy_multinexus_cleanup_trap`/`clear_deploy_cleanup_trap` 会 install/clear the process
`EXIT` trap。Worker 必须重构为一个 top-level trap authority：

- one EXIT/signal coordinator owns trap installation；
- MultiNexus artifact cleanup 只清理自己的 state，不得 `trap - EXIT` 清掉 mutation-lock
  cleanup；
- normal success显式 checked cleanup/smoke/release后清空 state；
- known failure保留原始 nonzero，执行 bounded artifact cleanup/rollback，再 exact release；
- release/cleanup failure不能被原始错误吞掉，输出 distinct stage并保持 nonzero；
- SIGINT/SIGTERM/early shell error不得 silent release wrong token；SIGKILL/host disconnect
  可能留下 stale lock，必须由 status/recover incident path处理，不能 age-steal。

### 7.5 Read-only status

`scripts/deploy-server.sh status`：

- 不执行 streamed acquire/install/release；
- 调 installed helper `status`（helper absent 只报告 `lock_helper=absent`，不安装，并在完成
  read-only smoke 后返回 nonzero）；
- 再运行现有 `server-smoke.sh`；
- 返回 lock state/phase 与 smoke result；invalid lock/helper error使 status nonzero。

## 8. Required helper tests

`tests/test_production_mutation_lock.py` 至少证明：

1. successful acquire metadata exact keys/content/modes/ownership and canonical JSON；
2. concurrent acquire exactly one winner；blocked acquire preserves bytes/stat；
3. status free/held/invalid and `--expect-token` read-only behavior；raw token redaction；
4. symlink、regular-file-at-lock-path、metadata symlink/hardlink、wrong mode/uid/gid、extra
   entry 全部 fail closed；
5. input types/bounds/control chars/bool-as-int/token shape fail before mutation；
6. release exact success；mismatch/malformed/metadata drift zero mutation；duplicate release
   only accepted with explicit idempotency flag；
7. nonroot acquire/release/recover zero mutation；
8. injected metadata open/write/fsync failure obeys own-partial-authority cleanup rule；
9. recover refuses absent confirmation、bad reason/operator、token mismatch、live unit/process、
   probe error；all preserve lock/audit；
10. successful recover writes one durable redacted audit receipt then releases exact lock；audit
    failure retains lock；
11. no command performs age-based steal or recursive deletion；
12. CLI stdout/stderr/exit codes are bounded deterministic JSON contracts and never log raw token
    outside successful acquire stdout。

Tests must not require real root/systemd/`/run`/`/var/log` and must not weaken production CLI path
constants。

## 9. Required deploy-contract tests

Extend the current fake SSH/root harness without contacting a real host。至少证明：

1. First deploy with installed helper absent：stream acquire precedes any remote staging/copy，
   helper installs `0755 root:root`，hash/status token verification passes，then deploy proceeds。
2. Existing helper path still acquires before replacing/verifying helper；replacement cannot create
   an unlocked window。
3. Successful `coordinate` and `multinexus` ordering：acquire -> install/verify -> first mutation ->
   version/restart -> optional smoke -> release。
4. `all` has exactly one acquire/token/release across both components and final smoke。
5. `--skip-install --no-restart --no-smoke` still acquires and releases around mutations。
6. `status` performs helper status + smoke only；no acquire/install/release/staging/catalog/version/
   restart mutation。
7. Existing valid lock contention stops before staging、snapshot、copy、sync、version、restart；
   owner metadata unchanged。
8. Invalid lock authority stops before all deploy mutations and is not repaired。
9. Injected staging/copy、snapshot、source mutation、sync/verifier、version、restart 或 smoke
   failure leaves nonzero；representative pre/post-mutation failures prove release happens only after
   required rollback/artifact cleanup。
10. Existing MultiNexus cleanup trap cannot clear the global lock trap；checked cleanup failure、
    EXIT、SIGINT、SIGTERM preserve correct token/stage behavior。
11. Installed-helper validation/release failure is loud nonzero；token mismatch never removes lock；
    streamed exact-source release fallback is only used before installed-helper validation。
12. Two concurrent fake deploys：one holds lock，second exits blocked before first remote mutation；
    first eventually completes/releases。
13. All existing 20 deploy-contract tests retain their intent and pass；registry/capacity snapshot/
    rollback/version/restart assertions不得放松。

Fake SSH rewrite must map `/run/lock`、`/usr/local/sbin`、`/var/log` into `FAKE_SSH_ROOT` and
model stdin-streamed Python/helper installation faithfully；不得 special-case tests into green。

## 10. Verification commands

Use existing environments only；不得 install/upgrade dependency。

Baseline at exact base：

- `tests/test_deploy_contract.py`：20 tests collected；
- full MultiNexus：880 tests collected（accepted baseline previously
  `878 passed, 2 skipped`）。

Run from the isolated worker worktree：

```bash
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q \
  tests/test_production_mutation_lock.py tests/test_deploy_contract.py
/Users/yinxin/projects/multinexus/.venv/bin/python -m pytest -q
/Users/yinxin/projects/multinexus/.venv/bin/python -m compileall \
  scripts/production-mutation-lock.py tests/test_production_mutation_lock.py \
  tests/test_deploy_contract.py
bash -n scripts/deploy-server.sh
git diff --check
git diff --name-only d09e0f8fba0f6d189934173027ca5a756e5f36ce...HEAD
git status --short
```

Focused/full tests要报告 exact passed/skipped/failed count 与 duration。测试不能 SSH real host，
不能读取 production DB，不能创建 `/run/lock`/`/usr/local/sbin`/`/var/log` real artifacts。

## 11. Worker completion contract

所有 tests 通过后，worker 可以在 required branch 创建 exactly one local commit。不得 push、
merge、deploy、SSH、restart、production smoke 或运行 helper against live paths。

Completion report 必须包含：

- commit SHA、parent SHA、branch、worktree；
- exact changed-file list、file modes、diff stat；
- helper acquire/status/release/recover semantics summary；
- first-install streamed-acquire、single-token `all`、top-level trap refactor summary；
- helper/deploy required matrix逐项 evidence；
- focused/full/compileall/bash-n/diff-check exact results；
- residual risks/deviations；
- 每次 route attempt 的 session id、JSONL path、outer route 与 provider-native model
  evidence，包括 primary quota failure 与实际完成实现的 fallback route。

Codex 将独立检查 diff、运行 adversarial tests 与 full suite。Worker commit/green tests 不授权
push、merge、deploy 或 P1/P2/P3。

## 12. Fail-closed stop conditions

立即停止且不 commit，如果：

- base/branch/worktree evidence 不匹配，或 model evidence 不符合第 2 节 exact primary/fallback
  policy；
- 需要修改 allowlist 外文件；
- helper 需要第三方 dependency、schema/DB、daemon 或 network service；
- first remote copy/staging 可以发生在 acquire/helper validation 前；
- `all` 使用多 token 或 component 间释放；
- `status`、blocked/invalid acquire、token mismatch 会产生 mutation；
- release/recover follow symlink、recursive delete、age-steal 或不检查 exact token；
- existing cleanup trap 能清掉 lock trap；
- failure/rollback/smoke 完成前 lock 已释放；
- tests 需要 real SSH/root/systemd/production paths；
- existing deploy rollback/capacity witness tests 被删除、放松或改成只检查日志；
- full suite regression 需要扩大 scope 才能解释。

P9_3C1_P0_MUTATION_LOCK_BOOTSTRAP_PENDING_INDEPENDENT_REVIEW
