# P9-3C0 Package 3 nested run lock 偏差计划

状态：`PLAN_REVIEW_APPROVED`

## 1. 触发证据

fresh isolated sidecar run `p9-3c0-pkg3-20260715l` 的业务与数据门全部完成：
base、crash stop、first reap、recovery proof、stale rejection、second reap、production
compare、cleanup 均到达 `phase=done`，isolated/production residue 正确，进程 exit 0。

但 stdout/stderr 在 second reap 后出现：

```text
flock: 9: Bad file descriptor
```

代码路径确认：

1. `_p9c0_controller_verify` 以 `_p9c0_with_run_lock` 在 FD 9 持有 primary run lock；
2. `_p9c0_verify_recovery_start` 调用 `_p9c0_prepare_recovery_namespace`；
3. recovery prepare 再次调用 `_p9c0_with_run_lock`，仍执行 `exec 9>>...`；
4. nested lock 覆盖 outer FD 9，nested return 时 `exec 9>&-`；
5. outer unlock 随后对已关闭 FD 9 调用 `flock -u 9`，产生 warning；更严重的是
   primary lock 在 verify 后半程已提前释放。

因此 run `l` 的数据结果可以作为功能证据，但 lock gate 不合格，P9-3C0 不能收口。

## 2. 最小修复

1. `_p9c0_with_run_lock` 使用显式、有限的 nesting depth：
   - depth 0 使用 FD 9；
   - depth 1 使用 FD 8；
   - depth >=2 fail closed。
2. 每一层必须按自身 FD 完成 open → exclusive lock → callback → unlock → close，
   并在正常/非零 callback return 后恢复 previous depth。
3. 不使用 Bash 4 dynamic-FD 语法，保持 macOS Bash 3.2 测试兼容。
4. 不移除 recovery namespace lock，不提前释放 primary lock，不把 flock error 静默
   redirect，不把 unlock failure 改成成功。
5. 不改变 lock file path/authority、recovery/shared DB、job/lease、systemd、snapshot、
   cleanup 或 P9-3C1。

## 3. 回归门

- behavioral nested-lock test 证明顺序严格为 acquire 9 → acquire 8 → release 8 →
  release 9；inner critical section 同时看到 FD 9/8 有效；nested return 后 outer FD 9
  仍有效且 FD 8 已关闭；最终两者均关闭；
- third-level nesting 必须 fail closed；
- callback 非零 return 仍必须按层 unlock/close 并返回原非零（unlock failure 优先使
  结果失败）；
- recovery namespace existing tests 与 verify phase tests 全通过；
- Package 3 focused、adjacent、full pytest、`bash -n`、`compileall`、diff-check PASS；
- 独立 result review `APPROVE`。

## 4. 部署与最终重跑

- merge/push 后仅 `scripts/deploy-server.sh multinexus --no-restart`；
- canonical PID/NRestarts 不变；
- 保留 runs `a` 至 `l`，fresh run 使用
  `p9-3c0-pkg3-20260715m`；
- run `m` 必须 exit 0 且 stderr 无 `flock` warning，完整 production compare/cleanup
  后才允许 Package 3 closeout；
- dogfood 文档必须如实记录此前误用 deploy restart、runs a-m 的每轮原因，以及
  nested lock 发现；P9-3C1 仍未授权。
