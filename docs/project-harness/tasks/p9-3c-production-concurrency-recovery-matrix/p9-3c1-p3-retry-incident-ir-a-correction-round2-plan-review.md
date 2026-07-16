# P9-3C1 P3 Retry Incident Package IR-A — Replacement Correction Round 2 Plan Review

状态：`APPROVED_LOCAL_BOOTSTRAP_AUTHORING_ALLOWED_IMPLEMENTATION_BLOCKED`

日期：2026-07-17 Asia/Shanghai

## 1. Review authority

- Reviewed plan：`p9-3c1-p3-retry-incident-ir-a-correction-round2-plan.md` at main
  `b9d7286adc58a1b06abe3081a15d4c96626fb94b`。
- Reviewer provider/model：`xfyun/xopglm52`。
- Native JSONL：
  `/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-retry-incident-ir-a-correction-r2-plan-review-glm52/2026-07-16T17-49-57-999Z_019f6c0c-ad6f-7000-a943-9ace826939fc.jsonl`。
- JSONL SHA-256：`bcbb1fcd9917183a18e8de43902f57bd98432bc4bfd74a08288afc8a62da615d`。
- Exact protocol verdict：`VERDICT: APPROVE / P0_P1: NONE`。

## 2. Accepted plan findings

The reviewer confirmed：

- fixed `2147483647` Linux PID value bound does not conflict with decimal parsing、`1 MiB` output budget or
  `131072` count cap and avoids mutable host `pid_max` authority；
- only exact `ESRCH` after `/proc ENOENT|ESRCH` passes；kill success、`EPERM`、other `OSError`、
  `OverflowError` and `ValueError` remain blocked with bounded reason；
- the embedded-NUL design can reach real `os.open` only after a test-owned `0700` parent is presented as
  root:root authority；
- `os.read` injection is the correct direct seam for short/growth rows and avoids the rejected `O_RDONLY`
  write/truncate bypass；
- fresh exact base、two-path allowlist、test-first evidence、single commit、dual result review and production
  freeze are complete。

## 3. Residual P2

The reviewer noted that a defense-in-depth catch for non-`OSError` exceptions from an injected
`read_cmdline` seam could be considered later。The production `_default_read_cmdline` path does not create the
reproduced failure and the Round 2 result-review authority is specifically the `kill_0` overflow escape；this P2
does not expand the approved runtime correction。

## 4. Gate

Codex may author the exact Round 2 worker bootstrap。Implementation remains blocked until a separate independent
bootstrap review returns `APPROVE / P0_P1: NONE`。No candidate merge、deploy、P0 recover/release、cleanup、resume、
service or DB mutation is authorized。

P9_3C1_P3_RETRY_INCIDENT_IR_A_CORRECTION_ROUND2_PLAN_APPROVED_LOCAL_BOOTSTRAP_AUTHORING_ALLOWED_IMPLEMENTATION_BLOCKED
