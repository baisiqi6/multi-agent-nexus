# Progress Archiving Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `coordinate task archive` command that moves closed phase artifacts from `docs/project-harness/tasks/<phase-id>/` to `docs/project-harness/archive/<phase-id>/` while leaving a stable stub pointer behind.

**Architecture:** Introduce a small `coordinate/archive.py` module that knows how to resolve source/archive/stub paths, copy files, write an `INDEX.md` with YAML front-matter, and rewrite `current/` packet links. The CLI delegates to this module after verifying the task mirror phase is `closed` or `done`. Harness compatibility is added so archived task stubs resolve their plan from `archive/` — the scripts that actually hardcode `tasks/<id>/plan.md` are `harnessctl` (bash ~line 269), `build_harness_state.py`, `workflow_transition.py` (NOT `validate_checklist.py`, which only validates JSON schema).

**Tech Stack:** Python 3.12+, `pathlib`, `shutil`, `pytest`.（`INDEX.md` 的 YAML front-matter 手写标量字段——coordinate 的 `pyproject.toml` 依赖里只有 `python-dotenv`，没有 PyYAML，不为此引入新依赖。）

## Global Constraints

- Archive SHALL use copy + stub, not move.
- Stub links SHALL use relative paths (`../../archive/<phase-id>/`).
- Archive trigger condition SHALL be task mirror phase == `closed` or `done`.
- `INDEX.md` SHALL be Markdown with YAML front-matter and include `original_path`, `archive_path`, `workspace_id`, `task_id`, `closeout_event_id`, `closed_at`, `commit_sha`.
- The command SHALL be idempotent.
- Archive copies every file in the task dir faithfully (no extension filter); only gitignored runtime byproducts (`:memory:*`, logs, local DB shards) are skipped with a logged note. Spec `task-archive:preserves file content` is the source of truth — the earlier "Only text/Markdown/JSON" draft was rejected as self-contradictory (mac-codex round-2 review).
- All state changes through CLI; never direct DB or JSON edits.
- TDD: write the failing test first, then the minimal implementation.

---

### Task 1: Add archive path model and closed-phase gate

**Files:**
- Create: `coordinate/src/coordinate/archive.py`
- Test: `coordinate/tests/test_archive.py`

**Interfaces:**
- Produces: `ArchivePaths(source_dir, archive_dir, stub_path, current_dir)` dataclass
- Produces: `resolve_archive_paths(harness_root: str, task_id: str) -> ArchivePaths`
- Produces: `require_closed_phase(conn, workspace_id, task_id) -> sqlite3.Row`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import pytest
from coordinate.archive import ArchiveError, resolve_archive_paths, require_closed_phase
from coordinate.db import initialize, upsert_workspace, upsert_task_mirror


def test_resolve_archive_paths():
    paths = resolve_archive_paths("/tmp/harness", "phase-8.4.2")
    assert str(paths.source_dir).endswith("tasks/phase-8.4.2")
    assert str(paths.archive_dir).endswith("archive/phase-8.4.2")
    assert str(paths.stub_path).endswith("tasks/phase-8.4.2/README.md")
    assert str(paths.current_dir).endswith("current")


def test_require_closed_phase_accepts_done():
    with tempfile.TemporaryDirectory() as tmp:
        conn = initialize(":memory:")
        upsert_workspace(conn, workspace_id="demo", name="Demo", path=tmp, harness_root=tmp)
        upsert_task_mirror(conn, workspace_id="demo", task_id="phase-8.4.2", phase="done", owner="op", branch=None, pr=None, payload={})
        row = require_closed_phase(conn, "demo", "phase-8.4.2")
        assert row["phase"] == "done"


def test_require_closed_phase_rejects_running():
    with tempfile.TemporaryDirectory() as tmp:
        conn = initialize(":memory:")
        upsert_workspace(conn, workspace_id="demo", name="Demo", path=tmp, harness_root=tmp)
        upsert_task_mirror(conn, workspace_id="demo", task_id="phase-8.8", phase="running", owner="op", branch=None, pr=None, payload={})
        with pytest.raises(ArchiveError, match="phase running"):
            require_closed_phase(conn, "demo", "phase-8.8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest coordinate/tests/test_archive.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coordinate.archive'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Progress archiving helpers."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


class ArchiveError(ValueError):
    pass


@dataclass(frozen=True)
class ArchivePaths:
    source_dir: Path
    archive_dir: Path
    stub_path: Path
    current_dir: Path


def resolve_archive_paths(harness_root: str, task_id: str) -> ArchivePaths:
    root = Path(harness_root)
    return ArchivePaths(
        source_dir=root / "tasks" / task_id,
        archive_dir=root / "archive" / task_id,
        stub_path=root / "tasks" / task_id / "README.md",
        current_dir=root / "current",
    )


def require_closed_phase(conn: sqlite3.Connection, workspace_id: str, task_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM tasks WHERE workspace_id = ? AND task_id = ?",
        (workspace_id, task_id),
    ).fetchone()
    if row is None:
        raise ArchiveError(f"task not found: {task_id}")
    if row["phase"] not in {"closed", "done"}:
        raise ArchiveError(f"task {task_id} phase is {row['phase']}; only closed/done can be archived")
    return row
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest coordinate/tests/test_archive.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add coordinate/src/coordinate/archive.py coordinate/tests/test_archive.py
git commit -m "feat(archive): add path resolution and closed-phase gate"
```

---

### Task 2: Copy task directory and write archive INDEX.md

**Files:**
- Modify: `coordinate/src/coordinate/archive.py`
- Test: `coordinate/tests/test_archive.py`

**Interfaces:**
- Consumes: `ArchivePaths` from Task 1
- Produces: `copy_task_directory(source_dir: Path, archive_dir: Path) -> None`
- Produces: `write_archive_index(archive_dir: Path, original_path: Path, workspace_id: str, task_id: str, closeout_event_id: str, closed_at: str, commit_sha: str) -> None`

- [ ] **Step 1: Write the failing test**

```python
from coordinate.archive import copy_task_directory, write_archive_index


def test_copy_task_directory_preserves_content(tmp_path):
    source = tmp_path / "tasks" / "phase-8.4.2"
    source.mkdir(parents=True)
    (source / "plan.md").write_text("# Plan\n")
    nested = source / "deep"
    nested.mkdir()
    (nested / "note.md").write_text("note")

    archive = tmp_path / "archive" / "phase-8.4.2"
    copy_task_directory(source, archive)

    assert (archive / "plan.md").read_text() == "# Plan\n"
    assert (archive / "deep" / "note.md").read_text() == "note"


def test_write_archive_index(tmp_path):
    archive_dir = tmp_path / "archive" / "phase-8.4.2"
    archive_dir.mkdir(parents=True)
    write_archive_index(
        archive_dir=archive_dir,
        original_path=tmp_path / "tasks" / "phase-8.4.2",
        workspace_id="demo",
        task_id="phase-8.4.2",
        closeout_event_id="evt-1",
        closed_at="2026-06-25T10:00:00Z",
        commit_sha="abc123",
    )
    index = (archive_dir / "INDEX.md").read_text()
    assert "original_path:" in index
    assert "workspace_id: demo" in index
    assert "task_id: phase-8.4.2" in index
    assert "closeout_event_id: evt-1" in index
    assert "commit_sha: abc123" in index
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with `ImportError: cannot import name 'copy_task_directory'`

- [ ] **Step 3: Write minimal implementation**

```python
import logging
import shutil


def copy_task_directory(source_dir: Path, archive_dir: Path) -> None:
    # 正常态由 archive_task 顶层 guard（stub+archive 都在则跳过）挡住；
    # 走到这里且 archive 已存在 = 部分态异常，fail loud 不静默覆盖（spec: archive 不变）。
    if archive_dir.exists():
        raise ArchiveError(f"archive already exists: {archive_dir}")
    # Copy every tracked artifact; skip gitignored runtime byproducts
    # (:memory:* SQLite shards, logs, __pycache__) per spec — log skipped names.
    _RUNTIME_IGNORE = {":memory:", ":memory:-shm", ":memory:-wal"}
    def _ignore_runtime(_dir, names):
        skipped = [n for n in names if n in _RUNTIME_IGNORE or n == "__pycache__" or n.endswith(".pyc") or n.endswith(".log")]
        if skipped:
            logging.warning("archive: skipping runtime byproducts in %s: %s", _dir, skipped)
        return skipped
    shutil.copytree(source_dir, archive_dir, ignore=_ignore_runtime)


def write_archive_index(
    archive_dir: Path,
    original_path: Path,
    workspace_id: str,
    task_id: str,
    closeout_event_id: str,
    closed_at: str,
    commit_sha: str,
) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    # 字段都是标量，手写 front-matter（不引 PyYAML）。spec 允许 "key-value list parseable by simple regex"。
    fields = [
        ("original_path", str(original_path)),
        ("archive_path", str(archive_dir)),
        ("workspace_id", workspace_id),
        ("task_id", task_id),
        ("closeout_event_id", closeout_event_id),
        ("closed_at", closed_at),
        ("commit_sha", commit_sha),
    ]
    lines = ["---"]
    for key, value in fields:
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append(f"# Archived Task: {task_id}")
    lines.append("")
    lines.append("This task has been archived. See [INDEX.md](INDEX.md) for provenance.")
    (archive_dir / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add coordinate/src/coordinate/archive.py coordinate/tests/test_archive.py
git commit -m "feat(archive): copy task directory and write archive index"
```

---

### Task 3: Write stub README.md and rewrite current/ links

**Files:**
- Modify: `coordinate/src/coordinate/archive.py`
- Test: `coordinate/tests/test_archive.py`

**Interfaces:**
- Produces: `write_stub(stub_path: Path, archive_dir: Path, closeout_event_id: str, closed_at: str) -> None`
- Produces: `update_current_links(current_dir: Path, task_id: str, archive_dir: Path) -> list[Path]`

- [ ] **Step 1: Write the failing test**

```python
from coordinate.archive import write_stub, update_current_links


def test_write_stub(tmp_path):
    stub_path = tmp_path / "tasks" / "phase-8.4.2" / "README.md"
    archive_dir = tmp_path / "archive" / "phase-8.4.2"
    write_stub(stub_path, archive_dir, "evt-1", "2026-06-25T10:00:00Z")
    text = stub_path.read_text()
    assert "Archived" in text
    assert "archive/phase-8.4.2" in text
    assert "evt-1" in text
    assert "2026-06-25T10:00:00Z" in text
    assert "../../archive/phase-8.4.2" in text


def test_update_current_links(tmp_path):
    current_dir = tmp_path / "current"
    current_dir.mkdir()
    packet = current_dir / "closeout-packet.md"
    packet.write_text("See [plan](tasks/phase-8.4.2/plan.md).\n")
    archive_dir = tmp_path / "archive" / "phase-8.4.2"
    changed = update_current_links(current_dir, "phase-8.4.2", archive_dir)
    assert changed == [packet]
    text = packet.read_text()
    assert "archive/phase-8.4.2/plan.md" in text
    assert "tasks/phase-8.4.2/plan.md" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

```python
import os
import re


def write_stub(stub_path: Path, archive_dir: Path, closeout_event_id: str, closed_at: str) -> None:
    stub_path.parent.mkdir(parents=True, exist_ok=True)
    relative = os.path.relpath(archive_dir, stub_path.parent)
    content = f"""# Archived Task

This phase has been archived. See the full artifacts at [{archive_dir.name}]({relative}/).

- **Closeout event**: `{closeout_event_id}`
- **Archived at**: `{closed_at}`
- **Archive path**: `{relative}/`
"""
    stub_path.write_text(content, encoding="utf-8")


def update_current_links(current_dir: Path, task_id: str, archive_dir: Path) -> list[Path]:
    changed: list[Path] = []
    if not current_dir.exists():
        return changed
    # Match `tasks/<task_id>/<rest>` and rewrite to `archive/<task_id>/<rest>`.
    # The task_id MUST be carried into the replacement — earlier draft used
    # `archive/\1` which dropped task_id (tasks/<id>/plan.md → archive/plan.md).
    pattern = re.compile(r"tasks/" + re.escape(task_id) + r"/([^\s\)\"\]]*)")
    replacement = f"archive/{task_id}/\\1"
    for path in current_dir.glob("*.md"):
        original = path.read_text(encoding="utf-8")
        updated = pattern.sub(replacement, original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(path)
    return changed
```

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add coordinate/src/coordinate/archive.py coordinate/tests/test_archive.py
git commit -m "feat(archive): write stub and rewrite current links"
```

---

### Task 4: Integrate `coordinate task archive` CLI command

**Files:**
- Modify: `coordinate/src/coordinate/cli.py`
- Modify: `coordinate/src/coordinate/archive.py`
- Test: `coordinate/tests/test_cli_archive.py`

**Interfaces:**
- Consumes: `ArchivePaths`, `require_closed_phase`, `copy_task_directory`, `write_archive_index`, `write_stub`, `update_current_links`
- Produces: `handle_task_archive(args: argparse.Namespace) -> int`
- Produces: `archive_task(conn, workspace_id, task_id, *, actor, dry_run) -> ArchiveResult`

- [ ] **Step 1: Write the failing test**

```python
from coordinate.archive import ArchiveError, archive_task
from coordinate.db import initialize, upsert_task_mirror, upsert_workspace
import pytest


def _setup(tmp_path, task_id, phase):
    conn = initialize(":memory:")
    harness_root = tmp_path / "harness"
    tasks_dir = harness_root / "tasks" / task_id
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "plan.md").write_text("# Plan\n")
    upsert_workspace(
        conn, workspace_id="demo", name="Demo",
        path=str(tmp_path), harness_root=str(harness_root),
    )
    upsert_task_mirror(
        conn, workspace_id="demo", task_id=task_id, phase=phase,
        owner="op", branch=None, pr=None, payload={},
    )
    return conn, harness_root, tasks_dir


# Tests target archive_task (core logic). The CLI handler in cli.py is a thin
# wrapper around it; verify the CLI entry separately after Step 3 via
# `coordinate task archive demo --task-id phase-x --dry-run`.
def test_archive_task_closed_phase_copies_and_stubs(tmp_path):
    conn, harness_root, tasks_dir = _setup(tmp_path, "phase-8.4.2", "done")
    result = archive_task(conn, "demo", "phase-8.4.2")
    assert result.archived is True
    archive_dir = harness_root / "archive" / "phase-8.4.2"
    assert (archive_dir / "plan.md").read_text() == "# Plan\n"
    assert (archive_dir / "INDEX.md").exists()
    # original plan.md removed from tasks/; only stub README.md remains
    assert not (tasks_dir / "plan.md").exists()
    assert (tasks_dir / "README.md").exists()


def test_archive_task_running_phase_rejected(tmp_path):
    conn, harness_root, tasks_dir = _setup(tmp_path, "phase-8.8", "running")
    with pytest.raises(ArchiveError, match="running"):
        archive_task(conn, "demo", "phase-8.8")
    assert not (harness_root / "archive" / "phase-8.8").exists()
    assert (tasks_dir / "plan.md").exists()  # original untouched
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL with `SystemExit` / unknown command

- [ ] **Step 3: Write minimal implementation**

In `coordinate/src/coordinate/cli.py`（cli.py 所有 handler 用 `with _conn(args) as conn:` 模式，**没有 `_db`**）：

- Import（加到顶部 archive 相关 import）：

```python
from .archive import ArchiveError, archive_task
```

- 在 `task_subcommands`（cli.py:306 `task = subcommands.add_parser("task")` 之下）加 `archive` 子命令：

```python
task_archive = task_subcommands.add_parser("archive", help="Archive a closed phase's artifacts")
task_archive.add_argument("workspace_id")
task_archive.add_argument("--task-id", required=True)
task_archive.add_argument("--actor", default="operator")
task_archive.add_argument("--dry-run", action="store_true")
task_archive.set_defaults(handler=handle_task_archive)
```

- 实现 `handle_task_archive`（用 `_conn` context manager + 捕获 `ArchiveError` 返回非零，对齐 `handle_task_create` / `handle_task_handoff` 范式）：

```python
def handle_task_archive(args: argparse.Namespace) -> int:
    try:
        with _conn(args) as conn:
            result = archive_task(
                conn, args.workspace_id, args.task_id,
                actor=args.actor, dry_run=args.dry_run,
            )
    except ArchiveError as exc:
        print(f"archive failed: {exc}", file=sys.stderr)
        return 1
    _print_json({
        "archived": result.archived,
        "archive_dir": str(result.archive_dir),
        "stub_path": str(result.stub_path),
        "current_links_updated": [str(p) for p in result.current_links_updated],
    })
    return 0
```

In `coordinate/src/coordinate/archive.py`，Task 4 新增 import（加在文件顶部已有的 `import shutil` 等之后）：

```python
import subprocess
from .db import get_workspace
```

然后新增 `ArchiveResult` 与 `archive_task`：

```python
@dataclass(frozen=True)
class ArchiveResult:
    archived: bool
    archive_dir: Path
    stub_path: Path
    current_links_updated: list[Path]


def archive_task(
    conn: sqlite3.Connection,
    workspace_id: str,
    task_id: str,
    *,
    actor: str = "operator",
    dry_run: bool = False,
) -> ArchiveResult:
    workspace = get_workspace(conn, workspace_id)
    if workspace is None:
        raise ArchiveError(f"unknown workspace: {workspace_id}")
    task = require_closed_phase(conn, workspace_id, task_id)
    paths = resolve_archive_paths(workspace.harness_root, task_id)

    if paths.stub_path.exists() and paths.archive_dir.exists():
        return ArchiveResult(
            archived=False,
            archive_dir=paths.archive_dir,
            stub_path=paths.stub_path,
            current_links_updated=[],
        )

    if dry_run:
        return ArchiveResult(
            archived=False,
            archive_dir=paths.archive_dir,
            stub_path=paths.stub_path,
            current_links_updated=list((paths.current_dir).glob("*.md")),
        )

    closeout_event_id, closed_at = _find_closeout_event_id(conn, workspace_id, task_id)
    commit_sha = _current_commit_sha(workspace.path)

    copy_task_directory(paths.source_dir, paths.archive_dir)
    write_archive_index(
        archive_dir=paths.archive_dir,
        original_path=paths.source_dir,
        workspace_id=workspace_id,
        task_id=task_id,
        closeout_event_id=closeout_event_id,
        closed_at=closed_at,
        commit_sha=commit_sha,
    )

    # Replace original task directory contents with the stub. The full copy
    # already lives in archive_dir; tasks/<id>/ keeps only README.md so old
    # links resolve via the stub pointer (design decision 1).
    for child in paths.source_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    write_stub(paths.stub_path, paths.archive_dir, closeout_event_id, task["updated_at"])

    updated = update_current_links(paths.current_dir, task_id, paths.archive_dir)
    return ArchiveResult(archived=True, archive_dir=paths.archive_dir, stub_path=paths.stub_path, current_links_updated=updated)


def _find_closeout_event_id(conn, workspace_id, task_id):
    """Return (event_id, created_at) for the latest closeout/done event.

    closed_at 取 event 的 created_at（真正关闭时刻），不用 tasks.updated_at
    （后者会被后续任意 upsert 漂移，不是关闭时间）。fallback ("unknown", "")。
    """
    row = conn.execute(
        "SELECT id, created_at FROM events WHERE workspace_id = ? AND task_id = ? AND event_type IN (?, ?) ORDER BY created_at DESC LIMIT 1",
        (workspace_id, task_id, "closeout.requested", "task.done"),
    ).fetchone()
    if row is None:
        return "unknown", ""
    return row["id"], row["created_at"]


def _current_commit_sha(repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"
```

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add coordinate/src/coordinate/archive.py coordinate/src/coordinate/cli.py coordinate/tests/test_cli_archive.py
git commit -m "feat(cli): add coordinate task archive command"
```

---

### Task 5: Make harnessctl accept archived task stubs

**Correction from mac-codex round-2 review:** earlier draft assumed `validate_checklist.py` checks `plan.md` existence and would reject a stubbed task dir. That premise is **false** — `validate_checklist.py` only validates the checklist JSON schema (`Path(args.checklist)`, no filesystem check of `tasks/<id>/plan.md`). The scripts that actually hardcode `tasks/<id>/plan.md` are:
- `harnessctl:269` — `if [ -f "$HARNESS_ROOT/tasks/$DOING_ID/plan.md" ]` (bash existence check)
- `workflow_transition.py:111` — artifacts plan path default
- `build_harness_state.py:128` — plan_path default
- `activate_item.py:126`, `sync_current_from_item.py:118` — doc/comment references

So Task 5 targets **`harnessctl` (bash) + `build_harness_state.py` + `workflow_transition.py`**, not `validate_checklist.py`.

**Out of scope (mac-codex round-4 review):** the packet generators also read `tasks/<id>/plan.md` — `prepare_review_packet.py:41`, `prepare_closeout_packet.py:55`, `prepare_handoff_packet.py:40`, `sync_current_from_item.py:136`. These run when a task is being reviewed/closed-out/handed-off — i.e. **before** it's archived (archive only happens at `phase=closed/done`, after closeout). So by the time a task dir is stubbed, these packet readers are no longer invoked for it. Reading a stub post-archive is undefined-but-harmless (they'd render the stub text, not crash). We **do not** add resolver logic to them — that would inflate scope for a path that isn't exercised post-archive. If a future workflow reviews an already-archived task, revisit.

**Files:**
- Modify: `multinexus/scripts/harness/harnessctl` (the `tasks/$ID/plan.md` existence check at ~line 269)
- Modify: `multinexus/scripts/harness/build_harness_state.py` (plan_path default at line 128)
- Modify: `multinexus/scripts/harness/workflow_transition.py` (artifacts plan default at line 111)
- Test: `multinexus` harnessctl/build_harness_state tests, or a new `tests/test_archive_stub_harness.py`

**Interfaces:**
- Consumes: existence of `tasks/<phase-id>/README.md` stub with archive pointer + `archive/<phase-id>/INDEX.md`

- [ ] **Step 1: Write the failing test**

Create a minimal harness root with:
- `mvp-checklist.json` containing a done item `phase-8.4.2`
- `tasks/phase-8.4.2/README.md` stub (containing "Archived Task" + `archive/phase-8.4.2` pointer), NO `plan.md`
- `archive/phase-8.4.2/INDEX.md` + `archive/phase-8.4.2/plan.md`

Then exercise the **plan-path resolvers** (not `validate` — validate_checklist only checks JSON schema):
- `python3 scripts/harness/build_harness_state.py` (reads checklist, resolves plan_path per item) → assert the built `harness-state.json` for `phase-8.4.2` has `plan_path` pointing at `archive/phase-8.4.2/plan.md`, not the stubbed `tasks/phase-8.4.2/plan.md`.
- `bash scripts/harness/harnessctl status <item>` (or whichever subcommand hits the ~line 269 plan.md check) → assert it does NOT report a missing plan.

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL — `build_harness_state` defaults plan_path to `tasks/<id>/plan.md` (line 128) which no longer exists; harnessctl:269 flags missing plan.

- [ ] **Step 3: Write minimal implementation**

For each hardcoded `tasks/<id>/plan.md` path, add a fallback: if the direct path doesn't exist but `tasks/<id>/README.md` is an archive stub, resolve the plan from `archive/<id>/plan.md` (read the stub's archive pointer). Concretely:
- `harnessctl` (bash, ~line 269): `if [ -f ".../tasks/$ID/plan.md" ]; then ...; elif grep -q "Archived Task" ".../tasks/$ID/README.md" 2>/dev/null; then PLAN="archive/$ID/plan.md"; ...`
- `build_harness_state.py:128` + `workflow_transition.py:111`: Python helper `_resolve_plan_path(item_id)` that checks stub → archive before defaulting.

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS — harness resolves archived task's plan without error.

- [ ] **Step 5: Commit**

```bash
git add scripts/harness/harnessctl scripts/harness/build_harness_state.py scripts/harness/workflow_transition.py  # multinexus repo
git commit -m "feat(harness): accept archived task stubs (resolve plan from archive/)"
```

---

### Task 6: Documentation and dogfood

**Files:**
- Modify: `coordinate/docs/runbook.md`
- Modify: `coordinate/CLAUDE.md`
- Modify: `multinexus/CLAUDE.md`

- [ ] **Step 1: Add archive command usage to runbook**

Add section under task management:

```markdown
## Archiving a closed phase

Once a phase is `closed` or `done`, archive its artifacts to keep `docs/project-harness/tasks/` clean:

```bash
coordinate task archive <workspace-id> --task-id <phase-id>
```

This copies `tasks/<phase-id>/` to `archive/<phase-id>/`, writes `INDEX.md` with provenance, and leaves a stub `README.md` in the original location.

Use `--dry-run` to preview changes without modifying files.
```

- [ ] **Step 2: Mention archive in CLAUDE.md architecture guidelines**

In `coordinate/CLAUDE.md` Section 2.7 (Host-aware) or add a note: archive is a host-aware file operation that runs on the local dev harness root, not on `/opt` server copies.

- [ ] **Step 3: Dogfood on a real closed phase**

Pick a real closed phase in `multinexus/docs/project-harness/` (e.g. `phase-8.4.4-host-aware-mark-done` if closed). Run:

```bash
coordinate task archive <workspace> --task-id phase-8.4.4-host-aware-mark-done
```

Verify:
- `archive/phase-8.4.4-host-aware-mark-done/` contains all original files + `INDEX.md`.
- `tasks/phase-8.4.4-host-aware-mark-done/README.md` links to archive.
- `build_harness_state.py` resolves the archived task's plan_path to `archive/<id>/plan.md`; `harnessctl:269` check accepts the stub (no missing-plan error).
- `current/` packet links updated.

- [ ] **Step 4: Commit**

```bash
git add coordinate/docs/runbook.md coordinate/CLAUDE.md multinexus/CLAUDE.md
git commit -m "docs: archive command usage and dogfood notes"
```

---

## Spec Coverage Check

| Spec Requirement | Implementing Task |
|---|---|
| Archive command migrates closed phase artifacts | Task 4 |
| Archive refuses non-closed phases | Task 1 + Task 4 |
| Archive is idempotent | Task 4 |
| Archive preserves file content | Task 2 |
| Active directory keeps stable pointer | Task 3 |
| Archive index is machine-readable | Task 2 |
| Pointer uses relative paths | Task 3 |

## Placeholder Scan

No TBD/TODO/"implement later" placeholders. Every step includes concrete file paths, code, or exact commands.

## Type Consistency

- `ArchivePaths` fields are `Path`.
- `ArchiveResult` fields are `Path` and `list[Path]`.
- `require_closed_phase` returns `sqlite3.Row`.
- `archive_task` accepts `workspace_id: str`, `task_id: str`, `actor: str`, `dry_run: bool`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-25-progress-archiving.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - Use superpowers:subagent-driven-development to dispatch a fresh subagent per task, with two-stage review after each.
2. **Inline Execution** - Execute tasks in this session using superpowers:executing-plans.

Which approach?
