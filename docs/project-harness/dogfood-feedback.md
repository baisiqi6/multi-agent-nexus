# Dogfood Feedback

本文件记录真实使用 coordinator + multinexus 多 agent 协作时暴露的 UX、协议和运行体验问题。

记录原则：

- 保留原始问题，不只记录最终修复。
- 标注状态：`fixed`、`mitigated`、`open`、`deferred`。
- 能顺手修的小问题可以直接修，但仍要留下问题和修复记录。
- 默认将 Claude 作为 coding worker，Codex 优先用于 review/operator；只有明确需要 Codex worker 时再派给 Codex。

## 2026-06-01

### 1. Codex worker 额度限制导致任务中断

- 状态：mitigated
- 原始现象：Phase 5.3 派给 `mac-codex` 后，Codex CLI 返回 usage limit，需要等到 23:27 后再试。
- 影响：任务不是因为代码或 coordinator 协议失败，而是 worker 额度不可用；如果继续默认派 Codex，会浪费调度时间。
- 临时处理：将 Phase 5.3 reroute 给 `mac-claude`，任务完成。
- 后续规则：默认 coding worker 使用 Claude；Codex 主要承担 review/operator。
- 待修方向：coordinator 的 worker selection 可以支持 agent availability / quota 状态，避免把任务派给当前不可用的 agent。

### 2. 历史 lifecycle 事件被新协议补发到 Discord

- 状态：fixed
- 原始现象：Phase 5.3 dogfood 时，`policy pump-events` 因 message key 变化，为历史 Phase 5.1 lifecycle 事件补发了一条新的 Discord 消息。
- 影响：不会再触发 worker 执行，但会造成频道噪声，并让人误以为旧任务刚刚发生。
- 修复：Phase 8 preflight cleanup 在 `coordinate` 中让 live 平台的 broad `policy pump-events` fail closed；需要 `--task-id` / `--event-type` 过滤，或显式 `--allow-backfill`。
- 验证：`coordinate` 新增 policy tests 覆盖 `--limit 1` 单独使用不再被接受为 live “latest event” 投递；`policy create-deliveries <event-id>` 保持单事件投递路径。

### 3. Managed agent 缺少稳定的中途进展通道

- 状态：open
- 原始现象：Phase 5.4 dogfood 中，`mac-claude` 成功 auto-accept 并执行任务，但在长时间运行期间 Discord/Coordinator 只看到 accept，没有看到阶段性 progress。
- 影响：人类观察者很难判断 worker 是在正常执行、卡住、还是忘记汇报；群聊看起来仍像 coordinator 单向广播。
- 当前处理：已记录到 `multi-agent-coordinator/docs/operator-needs-backlog.md`。
- 待修方向：
  - 增加明确的 `agent report` / `assignment progress` CLI。
  - worker bootstrap 中给出可执行的中途汇报命令，而不是只提示最终回复里写 `[agent-report]`。
  - daemon 将 progress report 渲染成 Discord 可见消息。

### 4. Agent 最终 report 可能被 message.edit 吃掉

- 状态：fixed
- 原始现象：如果 agent 的最终回复通过编辑 placeholder 发送，外部 watcher 只监听 `MESSAGE_CREATE` 时看不到 `[agent-report]`。
- 影响：worker 明明回复了 done/progress，但 coordinator 可能 ingest 不到。
- 修复：`multinexus` 将 `[agent-report]` 行拆出来，用独立 `channel.send()` 发送，避免只出现在 edited message 中。
- 验证：Phase 5.4 中 `mac-claude` 的 `action=done` 已被 coordinator ingest。

### 5. Workspace doctor 可能把 validation failure 包装成绿色状态

- 状态：fixed
- 原始现象：Phase 5.4 review 时发现 `workspace doctor` 先根据文件和 harnessctl 可执行性判断 `full_harness_runtime`，CLI 退出码只看 mode；如果 `harnessctl validate` 失败，仍可能退出 0。
- 影响：新项目接入时会把无效 harness 误判为健康，后续 assignment mutation 才失败。
- 修复：`workspace doctor` 现在在 `harnessctl validate` 或 `harnessctl doctor` 失败时返回非 0。
- 验证：新增测试覆盖 validate failure；coordinator 665 tests OK。

### 6. Discord 可见消息仍偏原始文本

- 状态：fixed
- 原始现象：coordinator 的 handoff、state、lifecycle、review summary 仍以大段纯文本为主。结构化字段存在，但没有充分利用 Discord embeds/cards/fields。
- 影响：群聊可读性差，人工扫描成本高；状态、owner、branch、风险、下一步等信息没有视觉层级。
- 修复：Phase 5.5 已在 `coordinate` 增加 Discord rendering 层，支持把 plan / state / handoff / lifecycle / review 等 delivery payload 渲染为 Discord embeds，同时保留 `[handoff]` / `[lifecycle]` 协议正文。
- 验证：`coordinate` 的 `discord_rendering.py` 与 `tests/test_discord_rendering.py` 覆盖卡片渲染；`multinexus` 文档已声明 Discord 卡片只是展示层，协议仍以 content 为准。
- 设计原则：
  - `[handoff]` 和 `[lifecycle]` 这类需要触发 bot 的协议行仍保留纯文本正文，避免破坏触发规则。
  - 状态、review、done、progress、doctor 这类面向人看的消息用 embeds fields 展示。
  - 长文本放摘要 + 链接/文件路径，不直接刷屏。
  - Discord 没有真正表格，优先用 embed fields、bullet list、code block 小表格。

### 7. Handoff packet 中部分字段不够可读

- 状态：open
- 原始现象：reroute 时生成的 `current/handoff-packet.md` 中 `Current Handoff` 出现 `{'from': None, 'to': None, 'reason': None}` 这类原始 dict 表达。
- 影响：不影响运行，但 review/审计文档可读性差。
- 待修方向：harness packet 生成器应把空 handoff 渲染为 `None` 或更友好的字段列表。

## 2026-06-08

### 8. Phase 7 计划文件存在但 checklist 缺项

- 状态：fixed
- 原始现象：Phase 7.1 已通过 Discord 派给 `mac-claude`，计划和 worker bootstrap 文件存在，但 `mvp-checklist.json` 没有 `phase-7.1-single-host-n-plus-m-runtime` item。
- 影响：operator review 时 `assignment blocker` 失败，coordinate 只能记录 `harness.mutation_failed`，无法把真实审核结论写入任务状态。
- 当前处理：已补 `phase-7-n-plus-m-runtime`、`phase-7.1-single-host-n-plus-m-runtime`、`phase-7.2-multi-host-agent-runtime` 三个 checklist item，并重新写入 Phase 7.1 blocker。
- 修复：Phase 8 preflight cleanup 在 `coordinate.task handoff` 写入 `worker.handoff.prepared` 事件前读取 workspace harness，要求 `harness-state.json` 与 `mvp-checklist.json` 都能观察到目标 task；缺失时拒绝生成 handoff。
- 验证：`coordinate` 新增 handoff tests 覆盖 checklist 缺项、harness state 缺失、成功路径不回退。

### 9. Phase 7.1 实现报告与验收口径不一致

- 状态：mitigated
- 原始现象：worker 报告“系统中只有一个 agentd 进程 per agent identity”，但代码实际在 Discord/KOOK bridge 内部各自启动 embedded `AgentDaemon`。
- 影响：如果同一 agent 同时接 Discord 和 KOOK，仍可能出现两个 adapter/agentd 实例，未真正从 `n*m` 收敛到 `n+m`。
- 当前处理：Phase 7.1.1 / 7.2 A0 已把 Discord bridge 与 coordinate 迁到腾讯云，Mac / Windows agentd 通过 coordinate runtime claim/report 复用同一 agentd 进程；Discord 侧不再是 `n*m`。
- 剩余：KOOK bridge 尚未启用，真正多 IM 平台同时接入同一 agentd 的验收仍 deferred 到后续阶段。
- 待修方向：review checklist 继续强制对照运行拓扑；KOOK 启用时必须验证同一 agent 不再启动第二个 adapter 常驻实例。

### 10. Auto accept report can hide missing execution report

- 状态：fixed
- 原始现象：Phase 7.1 Round 3 中，Discord 可见消息包含自动 `action=accept` 后接自然语言完成说明，但 coordinate 没有收到 `done`/`closeout`/progress completion event。
- 影响：operator 能在 Discord 看到 worker 完成说明，但 coordinate 任务状态仍停留在 running/accept，review 入口断开。
- 当前处理：MultiNexus runtime fallback 改成只把 `done`/`blocker`/`progress` 算作执行结果 report；单独的 `accept` 不再阻止 fallback 发送 progress report。
- 待修方向：worker 仍必须显式输出 `[agent-report] action=done ...` 或运行 `assignment closeout`；系统不会从纯自然语言推断完成。

## 2026-06-17

### 11. A0 多主机 handoff bootstrap 使用服务器部署路径

- 状态：fixed
- 原始现象：Phase 8 preflight cleanup 通过真实 Discord / coordinate / bridge / agentd 链路派给 `mac-claude`。第一次失败是服务器 bridge 私有 `agents.toml` 仍指向 Mac 本机路径，导致 bridge 读不到 bootstrap；修正服务器 `coordinator_db_path=/var/lib/coordinate/coord.sqlite3` 与 `coordinator_workspace_path=/opt/multinexus` 后，第二次 handoff 能读到 bootstrap。
- 新问题：bootstrap 内容仍把 worker 执行目录写成服务器部署副本 `/opt/multinexus`，但真实 worker 跑在 Mac agentd，源码工作区是 `/Users/yinxin/projects/multinexus`。worker 正确报告 blocker，没有切分支或写错 DB。
- 影响：A0 形态下“bridge/coordinate 在服务器，agentd 在宿主机”已经跑通普通消息，但 worker handoff 还缺少 host-aware execution profile；不能把 `/opt/multinexus` 部署副本当作开发 source of truth。
- 修复：`coordinate` 增加 `workspace_host_profiles` 与 `workspace host-profile` CLI，`task handoff` 根据目标 agent 的 `host_id` 渲染 worker bootstrap；`multinexus` bridge 使用 `assignment accept` 返回的 `bootstrap_text`，不再从服务器 `/opt/multinexus` 读取 worker 执行提示。
- 验证：真实 Discord handoff 给 `win-claude`，bootstrap / handoff 均使用 `C:\Users\ADMIN\projects\multinexus`，没有把 `/opt/multinexus` 当 worker 执行目录；job `request:651a60b4-327b-4aa7-95c6-b53e8bba7856` done，review approved 后 mark-done。

### 12. Mac Claude agentd 运行环境缺少 Claude API proxy

- 状态：open
- 原始现象：host-profile smoke 派给 `mac-claude` 后，handoff path 已经正确使用 `/Users/yinxin/projects/multinexus`，但 adapter 执行失败：`Claude error: API Error: Unable to connect to API (ConnectionRefused)`。
- 诊断：Mac shell 环境有 `ANTHROPIC_BASE_URL=http://127.0.0.1:15721` 与 `ANTHROPIC_AUTH_TOKEN=PROXY_MANAGED`，但 15721 没有 listener；`claude -p "Reply with exactly: ok"` 本地 45 秒超时。当前失败是 Mac Claude CLI / 本地代理环境问题，不是 handoff/bootstrap 路径问题。
- 影响：Mac worker handoff 可以 accept/claim，但实际 Claude 执行不可靠；会干扰后续用 `mac-claude` 做 coding worker 的 dogfood。
- 待修方向：统一 Mac agentd launchd 环境中的 Claude proxy 配置，并加一个启动前/健康检查：Claude CLI 可用、proxy listener 存在、短 prompt 能在超时内返回。

### 13. Job response_text 内的 `[agent-report] done` 没被摄取

- 状态：open
- 原始现象：`win-claude` smoke 的最终 `response_text` 末尾包含标准 `[agent-report] action=done ...` block，但 coordinate 事件里只出现 bridge 兜底 `progress.reported`：`adapter completed without a structured agent-report; operator should inspect the visible response`。
- 影响：worker 的自然语言结果与 done block 已经回到 job result/Discord 可见层，但 lifecycle 没自动进入 done，需要 operator 手动 `review-result` + `mark-done` 收尾。
- 当前处理：operator 已核对 job result，走 `assignment review-result` approved，再走 `assignment mark-done`，任务最终 closed。
- 待修方向：bridge 在收到 agentd job `response_text` 后，应复用 agent-report parser 处理其中的结构化 block，或将拆出的 `[agent-report]` 独立发为 Discord message create，避免只写入 result text 后被 fallback 覆盖。

### 14. win-opencode 在 NSSM / LocalSystem 下仍不稳定

- 状态：mitigated
- 原始现象：Windows `win-opencode` agentd 可以 claim job，但 OpenCode adapter 在 NSSM LocalSystem 服务环境下经常只收到 `step_start` 后 EOF，没有 `text` event。早期表现为 `response_text="(no response)"` 且 job 被错误标为 `done`，Discord 侧看起来像 worker 成功但没有内容。
- 已修复：
  - `filtered_env()` 不再在 Windows 子进程环境注入 POSIX 风格 `PWD`。
  - OpenCode adapter 对空 text 做有限重试，重试后仍无 text 时返回 `OpenCode returned no text ...`。
  - Agentd worker 将该错误前缀标为失败，使 job 变为 `failed`，不再假成功。
  - Windows `coord-ssh-win.py` 支持显式 `COORD_SSH_TARGET` / identity / known_hosts，并避免 OpenSSH stdin pipe 卡死。
  - Windows 服务态私钥改用 `C:\ProgramData\ssh\coord\id_ed25519_coord_win_v2`，ACL 只给 `SYSTEM` / `Administrators`，解决 NSSM service 读取私钥的权限问题。
- 验证：Windows `win-opencode` NSSM 服务恢复 claim/report；5 个 pending smoke job 最终 2 done、3 failed，失败均为 `OpenCode returned no text (events=step_start)`，没有 `(no response)` 假成功或永久 pending。
- 剩余问题：OpenCode 在前台 ADMIN 环境下稳定，但 NSSM LocalSystem 仍有高比例空 text。当前只能视为 degraded worker，不应作为默认 coding worker。
- 待修方向：给 `win-opencode` 改成真实 ADMIN 用户上下文的长期运行方式（NSSM ObjectName 需要用户密码，或设计可自动重启的 Scheduled Task / per-user runner），再做 10 次以上真实 job smoke；通过前不要把 `win-opencode` 放入默认 worker selection。

### 15. 服务器部署副本容易与开发 checkout 漂移

- 状态：fixed
- 原始现象：腾讯云 `/opt/multinexus` / `/opt/coordinate` 是运行副本，不是开发 source of truth；手工 rsync / hotfix 后容易忘记服务器当前跑的是哪个 commit。Phase 8 dogfood 中已多次遇到服务器副本落后本地分支的问题。
- 影响：operator 调试时可能以为“代码已修”，但远端 bridge / coordinate 仍在跑旧版本；worker bootstrap、agent-report、proxy、Windows wrapper 等问题会反复出现。
- 修复：增加 `scripts/deploy-server.sh` 与 `scripts/server-smoke.sh` 的手动一键部署/状态检查流程，并在 `/opt/{coordinate,multinexus}/VERSION_DEPLOYED` 写入 component、branch、commit、deployed_at、deployed_by。
- 验证：`scripts/deploy-server.sh status` 通过；`scripts/deploy-server.sh multinexus --skip-install` 已把服务器 `/opt/multinexus` 同步到 `f465a1f`，`server smoke OK`。
- 设计边界：这不是完整 GitHub Actions 自动发布；当前仍是 operator 手动触发的受控部署。后续 CI/CD 应调用同一套脚本，而不是发明第二套生产发布路径。

### 16. Issue scan 不能假设服务器有 GitHub 开发工具

- 状态：fixed
- 原始现象：Phase 8.1 首版 `coordinate issue scan` 把 `gh issue list` 与 SQLite event append 放在同一个进程里。A0 架构确认腾讯云是 runtime-only 后，不能要求服务器安装 `gh`、`git` 或保存 GitHub token。
- 影响：如果直接通过 `coord-ssh issue scan` 跑首版命令，会把 `gh` 依赖转移到服务器，扩大攻击面并破坏 runtime-only 边界。
- 修复：`coordinate issue scan` 增加 `--event-cli-path`；Mac / Windows coding host 本地运行 `gh issue list`，再通过远端 coordinate CLI wrapper 写入 `issue.spotted` event。
- 验证：Mac 创建并扫描临时 GitHub issue `baisiqi6/multi-agent-nexus#2`，远端 event `335d09e2-189c-41bd-b874-8fbe32f1bca2` 创建成功，Discord delivery `6d5c5601-1f36-45e7-9317-305912893aba` 已发送；重复 scan `created=0 existing=1`。

### 17. `--skip-install` 会让 Python package venv 变旧

- 状态：mitigated
- 原始现象：`scripts/deploy-server.sh coordinate --skip-install` 同步了 `/opt/coordinate/src`，但 `/opt/coordinate/.venv/site-packages/coordinate` 仍是旧 wheel。随后 `coord-local policy create-deliveries` 仍报 `unsupported event type: issue.spotted`，尽管 `/opt/coordinate/src/coordinate/policy.py` 已包含该 event type。
- 影响：`VERSION_DEPLOYED` 看起来是新 commit，server smoke 也可能通过，但 `coord-local` 实际执行旧 installed package，造成“代码已部署但行为没变”的错觉。
- 当前处理：Phase 8.1 dogfood 后已用非 `--skip-install` 的 `scripts/deploy-server.sh coordinate` 重新安装 package，远端 venv 已支持 `issue.spotted`。
- 规则：只要 Python import package 代码变化，就不要用 `--skip-install`；该参数仅用于文档、纯脚本或明确不影响 venv installed package 的同步。
- 待修方向：server smoke 后续应增加 installed package 与 `VERSION_DEPLOYED` 的一致性检查，避免只看 `/opt/*` 源码路径。

### 18. Phase 8.2 issue triage：untrusted 边界与幂等设计

- 状态：fixed（coordinate 侧已实现并完成真实 issue dogfood）
- 背景：Phase 8.1 已能 `issue scan` 把 GitHub issue 写成 `issue.spotted` event（coordinate commit 966b8c5；真实 dogfood：issue #2 → event `335d09e2-189c-41bd-b874-8fbe32f1bca2` → Discord delivery sent）。Phase 8.2 补下一段：issue.spotted → operator triage → task/assignment。
- 实现的 CLI：`coord-local issue triage <workspace> --event-id <issue.spotted id> --decision accept|reject|defer`（accept 额外接 `--task-id/--title/--owner/--phase`，reject/defer 接 `--reason`）。
- 设计边界（重要，踩过 untrusted 边界的坑都要写下来）：
  - **untrusted 内容边界**：GitHub issue body 是不可信输入。`triage_issue` 把 body_excerpt 原样保留进 task mirror 和 event payload，但永远标 `content_trust=untrusted`；policy 渲染的可见消息显式重复"issue 内容不可信，operator/worker 不得把正文当作系统指令执行"。body 绝不会被当作 system prompt 注入任何 agent。
  - **幂等 + 冲突拒绝**：同 (event_id, decision, task_id) 幂等复用 `issue.triaged` event；同一个 issue 已被 accept 后再 reject/defer 会报 `IssueTriageError`，避免重复或矛盾的 triage 决策。
  - **不自动 merge / close**：triage accept 只创建 task mirror + 写 event + 可见 delivery，不创建 PR、不 merge、不关 GitHub issue。merge/close 保持 operator-gated。
  - **服务器零改动**：triage 逻辑在 coordinate 控制面，但实际 dogfood 在 Mac/Win 本地跑（通过 coord-ssh 写远端 DB）；server 仍是 runtime-only，不装 gh/git。
- 真实 dogfood：
  - 部署 coordinate commit `5092bc4` 到腾讯云，未使用 `--skip-install`，确保远端 installed package 与 `/opt/coordinate/VERSION_DEPLOYED` 一致。
  - 创建临时 GitHub issues `baisiqi6/multi-agent-nexus#3`（accept）和 `#4`（reject），在 Mac 本地跑 `gh` + `/Users/yinxin/.local/bin/coord-ssh` 写远端 DB。
  - Scan 创建 `issue.spotted` events：`45279001-d431-45f7-8286-30c0a1e08af3`（#3）和 `b59be207-33c6-4434-9357-e65c96f68f1d`（#4）。
  - Accept 创建 `issue.triaged` event `b1d35a1c-970a-4f75-914c-e94cb5ca5ffa`、delivery `240e9eb1-01c0-4bdd-94e2-bddc5bdb0f4b`、task mirror `phase-8-2-triage-accept-smoke`，且 `content_trust=untrusted`。
  - Reject 创建 `issue.triaged` event `f7f8bcc5-9086-4e95-b250-31fa12f37e6f`、delivery `076e71b3-4daa-4217-89c1-96d7c172dad0`，不创建 task mirror。
  - 两条 `[ISSUE_TRIAGE]` delivery 已投递到 Discord：`discord_bot:1516871824963539165`（accept）和 `discord_bot:1516871826884661398`（reject）。
  - 重复 accept 幂等复用原 event/delivery；对已 accept 的 issue 改 reject 返回 `IssueTriageError`。临时 issue #3/#4 已关闭。
- Phase 8 编号体系（2026-06-18 对齐现实进度）：8.1 issue intake（done）/ 8.2 issue triage（done，本条）/ 8.3 accepted-issue materialization + handoff readiness / 8.4 PR-CI-review automation / 8.5 operator bot。
- 8.2 边界（review 收口）：accept 只创建 DB task mirror（`tasks` 表），不写 harness `mvp-checklist.json`，不保证 `task handoff`（`handoff.py` preflight 要 checklist 含该 task）。把 accepted issue 落成 harness task/checklist/plan-ready 是 8.3。
- content_trust follow-up：triage 层强制 `content_trust="untrusted"`，不再读 spotted payload 的自声明（防 payload 篡改声明 `trusted` 绕过 untrusted 边界）。
- dogfood 命令修正：`coord-local task list` 不存在（task CLI 只有 `create`/`handoff`）；验证 task mirror 改用 `coord-local event list <workspace>` 看 `issue.triaged` event，或直接读 triage CLI 的 JSON 输出里的 `task` 字段。
- 待修方向：Phase 8.3 把 accepted issue mirror materialize 到 harness checklist/task state，使其可被 `task handoff`；Phase 8.5 再做 operator bot 自动消费 `issue.spotted` 并产出 triage 决策。

### 19. Phase 8.3 accepted-issue materialization：把 issue accept 落成 harness task

- 状态：implemented + host-aware path added；pending A0 dogfood。同机（coding host = coordinate host）下 `issue materialize` 可用；A0 runtime-only server 不能直接 coord-ssh 跑 `materialize`（/opt guard 拒），必须走 `materialize-files`（coding host）+ commit/push + deploy + `materialize-record`（coord-ssh）。
- Host-aware rework（A0-safe，review follow-up）：单 `materialize` 命令拒绝 workspace.path/harness_root 在 `/opt/` 的 runtime copy（除非 `--allow-runtime-copy`），错误信息指向 host-aware flow。拆成 `issue materialize-files`（coding host 写 mvp-checklist.json，不碰 DB）+ `issue materialize-record`（coord-ssh 写 plan.ready/issue.materialized/task mirror/delivery，不碰 harness 文件，所以对 /opt workspace 安全）。renderer P2 修：兼容 `payload.number` 或 `payload.issue_number`，Discord 卡片不再显示 `repo#?`。`test_issues.py` 46 OK，`test_handoff.py` 46 OK，coordinate 全量 803 OK。
- 背景：Phase 8.2 accept 只建 DB task mirror，不进 harness `mvp-checklist.json`，所以 `task handoff` 过不了 `_require_harness_task` preflight（dogfood-feedback #18 收口边界）。
- 实现：`coord-local issue materialize <workspace> --event-id <issue.triaged id> --plan-doc <workspace-relative plan path>`。
- 设计边界：
  - **复用 create_plan_task**：materialize 调 `onboarding.create_plan_task`（写 `plan.ready` + sync `mvp-checklist.json` + upsert task mirror），不手写 checklist JSON mutation。
  - **operator 必须提供 plan**：`--plan-doc` 必须指向真实文件；refuse 从 untrusted issue body 自动生成 plan/prompt。
  - **content_trust 强制 untrusted**：materialize 层不读 spotted/triaged payload 的自声明。
  - **fail closed**：reject/defer 的 issue.triaged 不能 materialize；非 issue.triaged event 不能 materialize；plan_doc 缺/不存在报错。
  - **幂等 + 冲突**：同 (triage_event_id, task_id, plan_doc) 复用；不同 task_id/plan_doc 报 `IssueTriageError`。
  - **不自动 approve / handoff / close issue**：materialize 只解 checklist gate；plan gate 仍需 operator 手动 `plan approve --scope "implementation plan"`；merge/close 保持 human-gated。
- 验证：`tests/test_issues.py::IssueMaterializeTests` 12 cases + `tests/test_handoff.py::IssueMaterializeHandoffTests` 3 cases（`_require_harness_task` 前 fail / 后 pass；materialize + plan approve → `prepare_handoff` 成功）。coordinate 793 OK，multinexus 314 OK (2 skipped)。
- 后续 dogfood 步骤：临时 issue → `issue scan --event-cli-path` → `issue triage accept` →（operator 写 plan 文件）→ `issue materialize --plan-doc ...` → `plan approve --scope "implementation plan"` → `task handoff`。
- 待修方向：Phase 8.5 operator bot 自动 triage；Phase 8.4 PR/CI/review automation。

## 2026-06-18

### 20. Phase 8.3.1 harness 源真理边界：internal repo vs external sidecar vs `/opt`

- 状态：documented + tested。把 Phase 8.3 host-aware materialize（#19）的边界固化成文档 + 测试，不动 runtime 代码。
- 规则（写入 multinexus `scope.md` Boundaries + coordinate `docs/runbook.md`）：
  - **internal/managed repo**（如 multinexus）：harness 在 repo 内，随 repo commit；`workspace.path` 是 `workspace.harness_root` 的父目录；`init-harness --mode full` 要求 `harness_root ⊆ workspace.path`（`onboarding.full_init` 拒绝 out-of-tree）。
  - **external/upstream repo**（如 opencode）：harness 放 **checkout 外的 sidecar `harness_root`**，保证 upstream PR 不带我们的 harness 文件；不在那跑 `init-harness --mode full`，只用 host-aware flow。
  - **`/opt/*` 是 deploy artifact**（tar+ssh，无 git history，下次 deploy 覆盖），不是开发 source。`materialize`/`materialize-files` 拒 `/opt/` 路径（除非 `--allow-runtime-copy`）。
  - `workspace.path` 与 `workspace.harness_root` 是有意分离的概念（同树 or 分离树）。
- 证据：
  - 新测试 `coordinate/tests/test_issues.py::IssueMaterializeHostAwareTests::test_files_supports_sidecar_harness_root` 证明 `materialize-files` 把 checklist 写到 checkout **外**的 sidecar `harness_root`，且 checkout 保持无 harness 文件。
  - worker bootstrap（`coordinate/src/coordinate/handoff.py`）已把 `execution_workspace_path`（cd/git）与 `execution_harness`（harness root）作为分离值渲染并按 host profile 重映射 —— 即 #11/#14/#15 的 A0 修复，8.3.1 只是固化。
- 验证：coordinate 全量 805 OK；multinexus 无源码改动故无需跑测试；两 repo `git diff --check` 干净。
- 待修方向：无。文档 + 跨 repo 测试 only，无 deploy / 无服务变更。

### 21. Handoff follow-up：worker 首次回复可能只完成 start/progress

- 状态：open
- 原始现象：`phase-8.3.1-harness-source-boundary` 通过 coordinate -> Discord -> `mac-claude` handoff 后，第一次 agentd job 只发了"已接收/准备做"的 start/progress 文本，没有执行实现、提交或 closeout；同时 `[agent-report] action=progress` 被放在 fenced code block 内，coordinate 未按结构化 report 摄取，只生成 fallback progress。
- 临时处理：operator 通过 `runtime request submit` 用同一个 `session_scope_id=task:discord-nexus:phase-8.3.1-harness-source-boundary` 发 follow-up，明确要求"不要再发 start，继续执行实际任务"，agentd 成功 resume 旧 Claude session，随后完成 commit/push/closeout；codex review approved 并 mark-done。
- 影响：handoff 链路可恢复，但首次 worker job 可能消耗一次交互而没有实际推进；如果 operator 不盯状态，会误以为 worker 正在执行，或者只收到 fallback progress。
- 待修方向：
  - worker bootstrap / handoff accepted prompt 应区分"visible start update"和"actual implementation"，避免 adapter 调用在 start 后停止。
  - `[agent-report]` 示例不要放在 fenced code block，或者 report parser 应明确忽略 fenced 示例但能捕获真实未 fenced block。
  - 可考虑给 `action=progress` 加 `next_requires_followup=false/true` 或 agentd 侧检测"只 start 无文件变更/无 closeout"的长任务风险。

### 22. Phase 8.3.2 A0 重试：provider 529 后执行失败，assignment 仍保持 running

- 状态：open（重试策略缺口；失败可见性正常）
- 原始现象：`phase-8.3.2-a0-materialization-dogfood` 首次 handoff 被 `mac-claude` accept（event `e5800e0c-9d8f-44e4-a7f0-8ca8f14ed755`，2026-06-18 05:02:11Z），但 worker 执行时遇到 Claude API `529 Overloaded`，未产出实现、提交或 closeout。coordinate 正确记录了 `job.failed`，Discord 也生成了 fallback blocker；但 harness assignment 仍保持 accepted/running，没有自动 retry 或回退到可重新调度状态。
- 影响：失败本身可见，但任务生命周期不会自行恢复；operator 必须看到 blocker 后主动重试。与 #21 同属"accepted != executed"风险，区别是本次 adapter 明确失败，而不是只返回 start/progress。
- 当前处理：operator 直接重试 worker 执行，明确说明"上次 529 未开始实施，不要再 accept"。重试在同一执行内完成进度记录 → 测试 → commit/push → closeout；未再次 `assignment accept`（该命令对同 task+owner 幂等，accept 已记录）。
- 待修方向：
  - 对 provider 限流（529 / overloaded / 短时超时）增加有上限、带退避的自动 retry；超过上限后继续保留当前可见 blocker 行为。
  - 明确失败后的 assignment 状态：保持 running 等待 operator retry，或转为 blocked/retryable，避免 DB job 已 failed 而 harness 仍像在执行。
  - worker bootstrap 可固化重试指引：若 session 仍 live 且 task 已 `accepted`/`running`，直接 resume 执行，不要重新 accept。
  - 可给任务加一个"accepted 后 N 分钟无成功执行/closeout 即标 stale"的看护。

## 2026-06-22

### 23. Phase 8.4 真实 PR replay：同仓 `gh pr list --head owner:branch` 返回空

- 状态：fixed, reviewer pending。
- 原始现象：fresh host 首次通过远端 preflight 创建
  `multi-agent-coordinator#1` 并写入远端 mirror；第二个 fresh host 收到
  `mode=link_existing`，但 read-only discovery 返回 `discover_missing_pr`。
- 根因：`gh pr create --head` 接受 `owner:branch`，而真实
  `gh pr list --head` 对同仓 PR 需要 bare branch。单测 fake runner 没断言 argv
  的 `--head` 值，因此 Round 1-7 和 correctness review 都没发现。
- 安全结果：第二次没有调用 create，远端原 PR/mirror 未被覆盖；只追加了可见
  `publish.blocked` 事件。
- 修复：`discover_open_pr_for_head` 校验 owner 等于 repo owner 后，把 CLI
  filter 规范化为 bare branch；增加 argv-shape 测试，并用真实 GitHub read-only
  discovery 验证 URL/head SHA/base。
- 衍生修复：已有 PR 的同 task/repo/branch 允许 commit 前进，但只能走
  `link_existing`，由 GitHub 验证新 head SHA 和同一 PR URL 后，remote sink 才更新
  `publish_metadata.reported_commit`。repo/branch/PR 改绑仍 fail closed。

### 24. coordinate 部署尝试删除服务器 `.coordinator/logs`

- 状态：fixed, deploy replay pending。
- 原始现象：部署成功，但 rsync 输出
  `cannot delete non-empty directory: .coordinator`。该目录是服务器本地运行日志，
  不属于源码部署产物。
- 修复：coordinate staging tar 与远端 rsync 都显式排除 `.coordinator`，与
  `.venv`、data、logs、`VERSION_DEPLOYED` 的 server-local 保留策略一致。

## 后续建议排期

1. Phase 5.5: Discord Message Rendering
2. Maintenance: pump-events 历史 delivery 过滤
3. Maintenance: agent progress CLI / worker 中途汇报通道
4. Maintenance: handoff/closeout packet 可读性修复
5. Maintenance: response_text 中的 `[agent-report]` 摄取修复
6. Maintenance: Mac Claude CLI proxy / agentd launchd 健康检查
7. Maintenance: win-opencode per-user runner / service account stabilization
8. Phase 8: GitHub PR / CI / review automation loop
