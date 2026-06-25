## Context

`docs/project-harness/` 是 MultiNexus 项目的 active workspace。每个 phase 在 `tasks/<phase-id>/` 下保存 plan.md、worker-bootstrap.md、测试基线等文件。Phase 8 系列密集交付后，`tasks/` 下积累了大量已关闭 phase 的完整目录，而 `current/` 里仍残留指向旧路径的 closeout/blocker packet。Operator 和 worker 在定位当前任务时面临噪音。

现有工具链：
- `coordinate task create` / `task handoff` / `assignment mark-done` 管理 task mirror 和 harness checklist。
- `scripts/harness/validate_checklist.py`（经 `harnessctl validate` 调用）只校验 `mvp-checklist.json` 的 JSON schema，**不检查 `tasks/<id>/plan.md` 是否存在**。真正硬编码 `tasks/<id>/plan.md` 路径的是 `harnessctl:269`（bash 存在检查）、`build_harness_state.py:128`、`workflow_transition.py:111`（plan_path 默认），以及 `prepare_review_packet.py` / `prepare_closeout_packet.py` / `prepare_handoff_packet.py` / `sync_current_from_item.py`（packet 生成时读 plan）。
- 没有"归档已完成 phase 产物"的约定或命令。

## Goals / Non-Goals

**Goals:**
- 建立轻量、可测试、可自动触发的 progress 归档机制。
- 让 `docs/project-harness/tasks/` 只保留活跃或未关闭 phase。
- 归档后的 phase 仍可通过稳定指针从原路径找到。
- 先落地显式 `coordinate task archive` 命令（Phase 1）。`mark-done --archive` 自动触发是 Phase 2，不在本次 scope（见 decision 5）。

**Non-Goals:**
- 不引入外部存储（S3、数据库 archive 表）或压缩格式；archive 仍是 Git 管理的 Markdown 文件。
- 不自动归档非 phase 产物（如 `docs/architecture.md` 等常青文档）。
- 本次不实现通用“任意目录归档”框架；只针对 `docs/project-harness/tasks/<phase-id>/`。
- 不删除 Git 历史；archive 保留完整文件副本以便 `git log --follow` 继续工作。

## Decisions

### 1. copy 到 archive + 原位留 stub，而非 git mv
- **行为**：把 `tasks/<id>/` 完整复制到 `archive/<id>/`，然后删除 `tasks/<id>/` 下的原文件、只留一个 `README.md` stub 指向 archive。即”原目录内容被 stub 替换”，不是原文件保留在原处。
- **Rationale**：要在原路径留一个可解析的 stub 指针（旧链接不 404、operator muscle memory 不破）。`git mv` 会清空原目录、不留 stub，做不到这点。
- **Trade-off（诚实）**：git 视角下 `tasks/<id>/plan.md` 是 delete、`archive/<id>/plan.md` 是 add（不是 rename），所以 `git log --follow tasks/<id>/plan.md` 会断。代价可接受——历史通过 archive 副本 + `INDEX.md` 的 `commit_sha` 追溯。
- **Alternative**：`git mv` 整目录移动。Rejected：原路径无 stub，旧链接 404。

### 2. stub 用相对路径，不用绝对路径
- **Rationale**: 仓库可能在 Mac/Win/Server 之间 clone 或 tar 部署，绝对路径会失效。
- **Trade-off**: 相对路径从 `tasks/<phase-id>/README.md` 到 `archive/<phase-id>/` 需要 `../../archive/...`，可读性稍差，但稳定。

### 3. archive 触发条件以 task mirror phase == closed/done 为准，不重新解析 checklist
- **Rationale**: task mirror 是 coordinate DB 中的 lifecycle 真相；checklist 可能因 host-aware drift 落后（见 operator-needs-backlog A1/A2）。用 mirror 状态做 gate 更可靠。
- **Trade-off**: 若 checklist 尚未 mark-done 但 mirror 已 closed，archive 仍会执行。这被认为是可接受的，因为 archive 是文件整理，不是 lifecycle 状态变更。

### 4. `INDEX.md` 采用 Markdown + YAML front-matter（手写标量，不引 PyYAML）
- **Rationale**: 人可读、机器可解析，且与现有 `docs/` 风格一致。简单 regex 或 front-matter parser 都能读取。
- **Decision**: coordinate 的 `pyproject.toml` 依赖只有 `python-dotenv`，**没有 PyYAML**。INDEX 字段都是标量（路径/字符串），手写 `key: value` 行即可，不为此引入新依赖。spec 也允许 "key-value list parseable by simple regex"。
- **Trade-off**: 手写 front-matter 要保证值里没有破坏 YAML 解析的字符（冒号在值中间无碍，只有 `key:` 后的冒号有语义）；字段都是受控标量，风险低。

### 5. 本次只做显式 `coordinate task archive`，自动触发（`--archive`）是 Phase 2
- **Rationale**: 归档是不可逆的文件系统布局变更（虽然副本保留），先让 operator 显式运行、观察几轮，再决定是否接 closeout 自动触发（Phase 2）。降低误归档运行中 phase 的风险，也让本次变更 scope 收敛（mac-codex round-3 review 指出原"先显式后自动"措辞与 Migration Plan 矛盾）。

## Risks / Trade-offs

- **[Risk] archive 后外部脚本仍读旧 plan.md 路径** → Mitigation: stub README 顶部明确说明已归档并提供链接；同时加入废弃警告，给下游 1–2 个 release 的迁移期。
- **[Risk] 重复 archive 产生冲突** → Mitigation: idempotency 检查——若 archive 目录已存在且 stub 已存在，命令直接成功；若部分存在（只有 archive 没有 stub 或反之），报错并列出差异，不自动修复。
- **[Risk] `current/` packet 指向已归档 task 目录** → Mitigation: archive 命令扫描 `current/` 下所有 `.md`，把指向 `tasks/<phase-id>/` 的相对链接更新为 `archive/<phase-id>/`。
- **[Risk] 大文件/二进制文件进入 archive 增加 repo 体积** → Mitigation: archive 是 task 目录的 faithful copy（spec `task-archive:preserves file content`）——原则上 task 目录里本就不该有大二进制产物（它们该在 gitignored runtime 目录）。gitignored runtime byproducts（`:memory:*`、log、`__pycache__`）由 `copy_task_directory` 的 ignore 过滤跳过。不按扩展名挑文件（之前的"只归档 Markdown/JSON/文本"措辞已废弃，和 spec 矛盾）。
- **[Risk] host-aware 路径不一致（本地 vs /opt）** → Mitigation: archive 命令只操作当前运行该命令的 workspace path；生产环境中由 operator 在本地 dev 机运行，云端 `/opt` 作为部署副本不直接执行 archive。

## Migration Plan

1. **Phase 1（本变更）**: 新增 `coordinate task archive` 命令 + harness plan-path resolver 兼容 stub（`harnessctl:269` + `build_harness_state.py:128` + `workflow_transition.py:111`，**非** validate_checklist.py）+ 单测。
2. **Phase 2（后续可选）**: 在 `assignment mark-done` 增加 `--archive` 标志，允许 closeout 成功后自动归档。
3. **Phase 3（后续可选）**: 对 Phase 8 已关闭 task 批量运行一次 `task archive`，清理活跃目录。
4. **Rollback**: 若 archive 有误，可手动把 `archive/<phase-id>/` 内容复制回 `tasks/<phase-id>/`，删除 stub，恢复 `current/` 链接。注意：archive 命令**会删除 `tasks/<id>/` 原文件、只留 stub**（见 decision 1），但完整副本在 `archive/<id>/`，所以回滚 = 把 archive 副本复制回 tasks/ + 删 stub。不是"只 copy 不删"。

## Open Questions

- 是否需要把 archive 路径也写进 `mvp-checklist.json` 的 task metadata？当前 spec 未要求，待 dogfood 后评估。
- 是否需要在 stub README 中嵌入 `git log --oneline -5` 以便快速查看该 phase 的最近提交？可作为后续增强。
- 多 workspace（mac-smoke 与 multinexus）archive 路径是否统一？待 operator-needs-backlog B1 尘埃落定后再决定。
