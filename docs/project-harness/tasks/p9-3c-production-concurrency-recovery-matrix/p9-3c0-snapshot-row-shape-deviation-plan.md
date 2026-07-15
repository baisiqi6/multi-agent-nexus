# P9-3C0 Package 3 production snapshot row-shape 偏差计划

状态：`PLAN_REVIEW_APPROVED`

## 1. 触发证据

真实 isolated sidecar run `p9-3c0-pkg3-20260715j` 已通过 base concurrency、
75 秒 quiet/renewal boundary、exact process-tree proof 与 hold attempt N crash-stop。
ledger 记录：

```text
termination=crash kill_signal=SIGKILL kill_result=ok elapsed=80037 verdict=ok
lease-active ... expires_at=2026-07-15T17:50:39Z
```

随后 hold scenario 的 production snapshot compare 返回 drift 并 fail closed。Operator
逐项复核 baseline 与当前 production state：三个 canonical service 的
`Id/LoadState/ActiveState/SubState/MainPID/NRestarts/FragmentPath/fragment_sha256`、
三个 config SHA、schema 13、FK 0、pending/running 0、active lease 0、fixture
identity 0、executor/capacity source rows均完全相同。

根因在 `scripts/p9-3c0-local-verify.sh::_p9c0_real_production_snapshot`：

```python
"executor_sources": [tuple(r) for r in conn.execute(...)],
"capacity_sources": [tuple(r) for r in conn.execute(...)],
```

capture 的 `json.dump` 把 tuple 序列化为 JSON array；compare 的 `json.loads` 将其
恢复为 Python list。因此 baseline 为 `list[list]`，当前 payload 为
`list[tuple]`，即使值完全相同，Python equality 也必然为 false。

## 2. 最小修复

1. 只把两处 row materialization 改为 `list(r)`，使 capture 与 compare 的内存
   shape 都为 `list[list]`。
2. 不改变查询、排序、字段、canonical service/config/DB gate、snapshot 文件
   schema 或 fail-closed 条件。
3. 增加真实 Python/JSON round-trip regression test：capture 后立即对未变化 state
   compare 必须成功；任一 source row 值变化仍必须失败。
4. 若现有测试 seam 难以运行完整 production snapshot，只允许抽取一个纯
   normalization helper；不得弱化 `json.loads(output) != payload` 的严格比较。

## 3. 禁止扩展

- 不接受忽略 source rows、字符串化整个 payload、sort/canonicalize 后吞掉类型或
  值漂移、删除 production compare，或 catch-all 后继续；
- 不改 Coordinate、catalog/capacity authority、lease TTL/reap、systemd stop、
  production DB、canonical services 或 P9-3C1；
- 不复用失败 run `j`，不删除 runs `a` 至 `j`。

## 4. 验证门

- focused regression 证明 unchanged round-trip PASS、row-value drift FAIL；
- Package 3 focused、adjacent、full pytest、`bash -n`、`compileall`、
  `git diff --check` 全通过；
- 独立 result review `APPROVE`；
- merge/push 后仅使用 `scripts/deploy-server.sh multinexus --no-restart`；
- 确认 canonical service PID 均不变，使用全新 run id
  `p9-3c0-pkg3-20260715k` 重跑完整 isolated sidecar；
- cleanup 与 dogfood/closeout 文档完成前，P9-3C0 不收口；P9-3C1 仍未授权。

## 5. 独立计划审核

- verdict：`APPROVE`
- reviewer：Claude Code `--model sonnet`，JSONL assistant 事件实际
  `model=kimi-for-coding`
- session：`p9-3c0-snapshot-row-shape-plan-review-claude-kimi`
- 限制：reviewer 对仓库文件的直接 `Read` 请求被权限层拒绝；审核依据本 prompt
  内完整给出的根因、最小修复、回归与部署边界完成，不记作直接文件读取。
