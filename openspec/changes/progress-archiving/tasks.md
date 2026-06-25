## 1. Model & Path Discovery

- [ ] 1.1 Add `ArchivePaths` dataclass and resolver in `coordinate/src/coordinate/archive.py` to compute source, archive, and stub paths from workspace `harness_root` + `task_id`.
- [ ] 1.2 Add helper `_is_closed_phase(conn, workspace_id, task_id)` that reads task mirror phase and returns True only for `closed` or `done`.
- [ ] 1.3 Add helper `_read_closeout_event_id(conn, workspace_id, task_id)` to find the latest `closeout.requested` or `task.done` event id for `INDEX.md`.

## 2. Archive Core

- [ ] 2.1 Implement `copy_task_directory(source_dir, archive_dir)` that recursively copies files and preserves content (no transformation).
- [ ] 2.2 Implement `write_archive_index(archive_dir, original_path, workspace_id, task_id, closeout_event_id, closed_at, commit_sha)` using YAML front-matter.
- [ ] 2.3 Implement `write_stub(task_dir, archive_relative_path, closeout_event_id, closed_at)` to replace task directory contents with `README.md`.
- [ ] 2.4 Implement `update_current_links(harness_root, task_id, archive_relative_path)` to rewrite `current/*.md` relative links from `tasks/<task_id>/` to `archive/<task_id>/`.

## 3. CLI Integration

- [ ] 3.1 Add `coordinate task archive <workspace-id> --task-id <task-id>` CLI command in `coordinate/src/coordinate/cli.py`（coordinate 是单文件 CLI，`task` subparser 在这里，新增 `archive` 子命令）。
- [ ] 3.2 Gate the command on closed/done phase; return clear error and exit code 1 for non-closed tasks.
- [ ] 3.3 Make the command idempotent: if archive directory + stub already exist, succeed without modification.
- [ ] 3.4 Add `--dry-run` flag that prints source → archive mapping and link rewrites without touching filesystem.

## 4. Harness Validation Compatibility

- [ ] 4.1 Make `harnessctl` (bash, ~line 269 `tasks/$ID/plan.md` check) + `build_harness_state.py:128` + `workflow_transition.py:111` accept a `tasks/<task-id>/README.md` archive stub: if the direct `plan.md` is absent but the stub points to `archive/<task-id>/`, resolve the plan from the archive. (Note: `validate_checklist.py` only validates checklist JSON schema — it does NOT check `plan.md`, so it needs no change. mac-codex round-2 review caught the false premise.)
- [ ] 4.2 Test the plan-path resolver (harnessctl line 269 + build_harness_state): a `done`/`closed` task with only an archive stub resolves its plan from `archive/<id>/plan.md`; a non-closed task whose dir is stubbed (anomalous) is flagged. (Note: `validate_checklist.py` validates checklist JSON schema only — it does NOT inspect `tasks/<id>/plan.md`, so "validate fails on stub" is not a meaningful test; target the plan-path resolvers instead.)

## 5. Tests

- [ ] 5.1 Unit test `copy_task_directory` preserves file content and handles nested files.
- [ ] 5.2 Unit test `write_archive_index` produces valid YAML front-matter with required fields.
- [ ] 5.3 Unit test `_is_closed_phase` returns correct boolean for `running`, `awaiting_operator`, `done`, `closed`.
- [ ] 5.4 Integration test CLI archive command: closed phase → archive + stub + current link update.
- [ ] 5.5 Integration test CLI archive command: running phase → rejected, no files changed.
- [ ] 5.6 Integration test idempotent re-archive.
- [ ] 5.7 Test harnessctl validate with archived task stub passes; non-closed stub fails.

## 6. Documentation & Dogfood

- [ ] 6.1 Add `coordinate task archive` usage to `coordinate/docs/runbook.md`.
- [ ] 6.2 Update `multinexus/CLAUDE.md` or `coordinate/CLAUDE.md` 提及 archive 命令作为 host-aware 文件操作示例。
- [ ] 6.3 Dogfood：归档一个真实已关闭 phase（例如 phase-8.4.4 或 8.6），验证 stub 链接可点击、INDEX 字段完整、validate 通过。
