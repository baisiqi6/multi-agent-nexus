> **Historical record.** Current source of truth: `docs/project-harness/progress.md` and `docs/project-harness/scope.md`. This file is preserved as part of the dogfood development audit chain.

# Phase 5.4 Workspace Doctor And Full Harness Init

## 背景

Phase 4 和 Phase 5.1-5.3 已经把 `multinexus` 接入 coordinator，并实际跑通了：

- coordinator 创建 task、记录 plan approval、生成 worker bootstrap。
- coordinator bot 通过 Discord 定向 handoff 给 managed agent。
- `multinexus` managed agent 自动 accept，并按 task-scoped bootstrap 执行。
- worker 通过 `[agent-report]` 回报 progress/blocker/done。
- coordinator 将事件同步回 harness state。

现在的问题是，新 workspace 接入这条链路仍然依赖人工判断和手工复制文件。之前 `multinexus` 接入时就出现过：

- workspace 指向了普通 docs 目录，而不是有效 harness root。
- 缺少 `harnessctl` 时 audit/state 的提示不够直观。
- minimal file-backed harness 能临时恢复状态，但不能完整支持 mutation lifecycle。
- `scripts/harness/` runtime 需要从 skill 模板手工复制。

本 phase 要把这部分 onboarding 和诊断能力做成 coordinator 的一等能力。

## 目标

让 operator 能用 coordinator 明确判断一个 workspace 的 harness 能力，并能一键初始化完整 harness runtime，而不是靠人工拼接文件。

## 实施范围

### multi-agent-coordinator

新增或增强以下能力：

1. Workspace doctor 输出增强

   `workspace doctor <workspace_id>` 或现有等价命令应清楚显示：

   - workspace path 是否存在。
   - harness root 是否存在。
   - `harnessctl` 是否配置、存在、可执行。
   - `harness-config.json`、`mvp-checklist.json`、`events.jsonl`、`harness-state.json`、`progress.md` 是否存在。
   - checklist/state 是否能通过 harness validator。
   - mutation lifecycle 是否可用，也就是是否能通过 harnessctl 执行 state/validate/doctor，并且 coordinator HarnessAdapter 能读写。
   - default bus / destination 是否配置；未配置时应明确说明只是影响 visible delivery，不影响 file-backed state。

2. Full harness init

   增加一个显式初始化命令，例如：

   ```bash
   PYTHONPATH=src python3 -m multi_agent_coordinator \
     --db data/coordinator.sqlite3 \
     workspace init-harness <workspace_id> \
     --mode full
   ```

   行为要求：

   - 使用已知 `long-running-project-harness` skill/template 作为来源，实例化 `scripts/harness/` runtime。
   - 创建或补齐 `docs/project-harness/` 下的协议文件：
     - `harness-config.json`
     - `mvp-checklist.json`
     - `events.jsonl`
     - `progress.md`
     - `scope.md`
     - `architecture.md`
     - `domain-model.md`
     - `runbook.md`
   - 如果文件已存在，默认不覆盖；输出 `created`、`existing`、`skipped`、`warnings` 摘要。
   - 支持 dry-run，便于 operator 先看会写什么。
   - 初始化后可以自动更新 workspace 的 `harnessctl_path`，但必须在输出中明确说明。

3. 保留 minimal fallback

   现有 minimal file-backed harness 逻辑不删除。它适合作为救援路径，但 doctor 输出必须区分：

   - `minimal_file_backed`: 只能读静态状态或有限同步。
   - `full_harness_runtime`: 支持 assignment accept / handoff / closeout / mark-done 等 mutation lifecycle。

4. 测试

   新增测试覆盖：

   - missing harness root。
   - missing harnessctl。
   - harnessctl 不可执行。
   - checklist invalid。
   - healthy full harness。
   - init-harness dry-run 不写文件。
   - init-harness full 创建缺失文件且不覆盖已有文件。
   - init-harness 后 workspace 配置能指向正确 `harnessctl_path`。

### multinexus

只做文档和 dogfood 更新：

- 在 `docs/project-harness/runbook.md` 增加新 workspace 接入推荐顺序。
- 在 `docs/project-harness/progress.md` 记录本 phase dogfood 结果。
- 不改 `multinexus/` runtime 代码，除非 dogfood 发现必须阻塞修复的问题。

## 非目标

- 不静默重写已有 harness state。
- 不把 validation failure 包装成成功。
- 不强制非 Discord workspace 配置 Discord bus/destination。
- 不实现 systemd / Windows 部署。
- 不实现 long-running job worker。
- 不改变 task/handoff/agent-report 协议。

## 安全边界

- 不读取、不打印 `.env`、`agents.toml`、token、webhook URL。
- 初始化命令默认不覆盖已有文件。
- 如果模板来源不存在或不可信，应 fail closed，并输出 operator 可执行的下一步。
- 所有路径必须限制在目标 workspace root 内，不能把 harness 文件写到 workspace 外。

## 验证计划

在 `multi-agent-coordinator`：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```

手动验证：

```bash
skills/coordinate-operator/scripts/mac.sh workspace doctor multinexus
skills/coordinate-operator/scripts/mac.sh workspace init-harness multinexus --mode full --dry-run
```

在 `multinexus`：

```bash
scripts/harness/harnessctl validate
.venv/bin/python -m unittest discover tests
```

## 验收标准

- Doctor 能明确区分 missing/minimal/full harness 状态。
- Full init 可以从缺失状态创建完整 harness runtime，并且默认不覆盖已有文件。
- 对已接入的 `multinexus` 运行 dry-run 不会产生破坏性变更。
- coordinator 和 multinexus 相关测试通过。
- runbook 写清楚新 workspace 的推荐 onboarding 顺序。

## 建议 worker

优先交给 `mac-claude` 或 `mac-opencode`。该任务主要是 coordinator CLI、template copy、安全路径和测试，适合让 worker 实现后由 Codex 做协议/安全边界 review。
