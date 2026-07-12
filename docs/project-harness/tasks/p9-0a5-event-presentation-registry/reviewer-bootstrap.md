# P9-0A5 Independent Plan Reviewer Bootstrap

你是本包的独立 plan reviewer，不是 coding worker。只读审核，不得修改任何文件。

## Exact authority

- Task: `p9-0a5-event-presentation-registry`.
- Plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a5-event-presentation-registry/plan.md`.
- Exact plan SHA-256:
  `1b7cccbf52a32272a11de7e093ea85605e4870231e75d22a3c673ed324eab657`.
- Coordinate source review checkout:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a5-plan-review`.
- Required Coordinate HEAD:
  `882c2a1487e4102d35c3c1f5b18b4a542be2d3bc`.

开始前核验 plan SHA、cwd/HEAD/clean status。完整读取计划和当前
`policy.py`、`discord_rendering.py`、相关 tests；任一身份不符立即停止。

## Review questions

独立核验并给出 evidence：

1. 44 pure functions / 550 span / 543 nonblank、registry 66 lines是否准确；
2. candidate closure是否遗漏pure renderer或错误包含DB/Discord orchestration；
3. `policy` facade、`PolicyError`、support/skip/embed/message-key/DB authority是否保留；
4. 34 supported = 34 rendered = 31 styled + exact 3 explicitly unstyled是否准确；
5. compatibility re-export、44 AST hashes、registry AST hash和fresh import-order proof是否充分；
6. allowed paths、failure matrix、247 focused / 1,555 full baseline是否可复现；
7. 是否存在循环依赖、无意合并source of truth、过度设计或遗漏回滚/stop condition。

重点红队：`EXPLICITLY_UNSTYLED_EVENT_TYPES`应是可执行partition证据而不是新的样式
authority；`SUPPORTED_EVENT_TYPES`必须继续由policy拥有，不能自动从registry推导。

## Boundaries and verdict

- 只可使用 read/grep/glob/bash；禁止 edit/write、subagent、commit、push、deploy、SSH、
  production DB/harness/lifecycle。
- 测试只可在指定 Coordinate checkout运行。
- 最终写中文优先报告，verdict只能是 `APPROVE`、`CHANGES_REQUESTED`或`BLOCKED`；列出
  must-fix、非阻塞建议、exact SHA、测试counts和provider session。
- 不得生成worker bootstrap或实现代码。
