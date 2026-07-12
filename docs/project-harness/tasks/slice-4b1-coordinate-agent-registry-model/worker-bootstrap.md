# Worker Bootstrap: Slice 4B1 Coordinate Agent Registry Model

你是本包唯一 coding worker。严格执行已通过两轮独立审核的计划，不扩展到
MultiNexus roster 部署、doctor/repair 或 Phase 9 executor selection。

## Exact identity

- Task: `slice-4b1-coordinate-agent-registry-model`.
- Worker worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-s4b1-kimi`.
- Branch: `agents/mac-omp/slice-4b1-coordinate-agent-registry-model`.
- Required start HEAD:
  `5986cc38d8fa7a46c1cdd1dcb195fcc7043314d9`.
- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/slice-4b1-coordinate-agent-registry-model/plan.md`.
- Approved plan SHA-256:
  `f23210ee9986e4e8d737a43d3abe155f900a59aec7fde117e1bb5b7e63f97fb8`.
- Coordinate plan approval event:
  `1569fb46-ab07-4d6e-a0de-a5171cccee59`.
- Read `plan-review-round-1.md` and `plan-review-round-2.md` completely before editing.

开始前核验 `pwd`、branch、HEAD、clean status 和 plan SHA。任一不符立即停止并报告，
不要用 `switch`、`reset`、`rebase`、`cherry-pick` 修复，也不要改共享 checkout。

## Authorized implementation

1. 将 SQLite schema 从 v9 升到 v10，新增 source、normalized entries 和 registry
   revision；v9 `agents_json` 必须先完整验证再原子 backfill 为 `legacy`，失败不得推进
   `user_version` 或留下部分 legacy rows，v10 reopen 必须幂等。
2. TOML 增加 `[registry]` source id/version 解析，并严格按计划定义的 normalized JSON
   list、UTF-8 和 SHA-256 算法生成 canonical roster hash；不得哈希 raw bytes、secret、
   path 或未知字段。
3. 实现 source version/hash conflict、rollback、takeover 拒绝规则；authoritative sync
   必须要求现有 `--replace`，替换 authoritative/legacy、保留 override，并在同一事务中
   更新 source/revision/compatibility projection/audit event。
4. `workspace agent add` 改为带 actor、非空 reason、可选严格 UTC expiry 的 override
   upsert；新增显式 `remove-override`，只删除 override。两者必须原子更新 revision、
   projection 和 audit event。
5. effective resolver 顺序必须是 active override > authoritative > pre-sync legacy；
   expired override 保留审计但不授权；不同名字的重复 effective Discord id 必须在提交前
   拒绝。
6. daemon 在每一条 inbound channel message 的 `is_agent` 分类前执行一次完整、当前时钟的
   effective registry refresh。migration/resolution 失败必须 fail closed，不能沿用旧 cache；
   expiry 不依赖 revision 变化或 restart。
7. `agents_json` 只作为事务内生成的 compatibility projection，新的 resolver/daemon
   不得把它重新当作 authority。
8. 更新 CLI fixture，并用永久 delta/rewind proof 证明仅移除 `remove-override` leaf、归一化
   add 的三个新 options 后，恢复旧 fixture SHA
   `43e181046d3baa174199e3c02bcbc1ab1fedf83177d5c3725516a839bbb1f9e1`。

实现时特别检查 migration transaction boundary、malformed/duplicate JSON、same-name
shadowing、duplicate effective ids、expiry 边界 `expires_at <= now`、跨 workspace 隔离，
以及 audit append 失败时的完整 rollback。测试使用可控时钟，不得 `sleep`。

## Allowed paths only

Production:

- `src/coordinate/schema.py`;
- `src/coordinate/db.py`;
- `src/coordinate/agent_registry.py`;
- `src/coordinate/workspace_cli.py`;
- `src/coordinate/daemon.py`.

Tests/fixture:

- `tests/test_agent_registry.py`;
- `tests/test_db.py`;
- `tests/test_workspace_cli.py`;
- `tests/test_daemon.py`;
- `tests/test_cli.py`;
- `tests/test_cli_contract.py`;
- `tests/fixtures/cli_contract.json`.

禁止修改其他 Coordinate path、任何 MultiNexus path、真实 DB/config、policy/handoff、
deploy 脚本或 harness 文件。若实现确实需要超范围，停止并报告 blocker，不要自行改 plan。

## Validation

必须使用 `/opt/homebrew/bin/python3.14`：

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_agent_registry.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_db.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_workspace_cli.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_daemon.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_cli_contract.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests -p 'test_cli.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.14 \
  -m unittest discover -s tests
```

Baseline 是 focused 291、full 1574；新增测试后不得低于 baseline。报告每个 suite 的实际
count、old/new fixture SHA、rewind proof、migration/atomicity/daemon refresh 证据和 exact
changed paths。

## Provider and completion protocol

- Primary provider: `kimi-code/kimi-for-coding-highspeed`.
- Kimi 若发生 quota、auth 或 provider failure，保留原 session JSONL 并停止；只有 Operator
  可基于该证据启动 GLM fallback。不得自行换模型或把失败 session 伪装成完成。
- 不得调用 subagent。
- 全部通过后只创建一个 local commit。
- 禁止 push、merge、deploy、restart、SSH、真实 lifecycle、MultiNexus 修改或 mark-done。
- 最终中文优先报告 commit、changed paths、测试证据、未决风险；Codex 将独立审查结果。
