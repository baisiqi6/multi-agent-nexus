"""Handoff protocol handler: auto-accept coordinator handoffs at the runtime layer.

Intercepts [handoff] messages from the coordinator bot, executes assignment accept
with fixed parameters, reads the bootstrap file, and injects it into the agent prompt.
Only assignment.accept is automated — mark-done, blocker, merge etc. must go through
normal adapter/LLM flow.
"""

from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoordinatorHandoff:
    workspace_id: str
    task_id: str
    bootstrap_path: str
    action: str


_HANDOFF_PREFIX_RE = re.compile(r"\[handoff\]\s*<@!?(\d+)>", re.IGNORECASE)
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_ALLOWED_ACTIONS = frozenset({"assignment.accept"})
_REPORT_ACTIONS = frozenset({"accept", "blocker", "done"})


def parse_coordinator_handoff(
    content: str,
    *,
    my_discord_user_id: int,
) -> CoordinatorHandoff | None:
    """Parse a structured [handoff] message from the coordinator bot.

    Returns None if the message doesn't match the expected format or
    the action isn't in the allowed whitelist.
    """
    prefix = _HANDOFF_PREFIX_RE.search(content)
    if prefix is None:
        return None
    if int(prefix.group(1)) != my_discord_user_id:
        return None

    fields = _parse_key_values(content[prefix.end():])
    workspace_id = fields.get("workspace_id")
    task_id = fields.get("task_id")
    action = (fields.get("action") or "").lower()
    bootstrap_path = fields.get("bootstrap") or ""
    if not workspace_id or not task_id or not action:
        return None
    if not _SAFE_ID_RE.match(workspace_id) or not _SAFE_ID_RE.match(task_id):
        return None
    if action not in _ALLOWED_ACTIONS:
        log.info("Handoff action %r not in allowed list, skipping", action)
        return None

    return CoordinatorHandoff(
        workspace_id=workspace_id,
        task_id=task_id,
        bootstrap_path=bootstrap_path or "",
        action=action,
    )


def _parse_key_values(text: str) -> dict[str, str]:
    try:
        parts = shlex.split(text)
    except ValueError:
        return {}
    fields: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        normalized = key.strip().lower().replace("-", "_")
        if normalized:
            fields[normalized] = value.strip()
    return fields


def execute_assignment_accept(
    *,
    cli_path: str,
    db_path: str,
    workspace_id: str,
    task_id: str,
    agent_name: str,
) -> tuple[bool, str]:
    """Run coordinator assignment accept with fixed parameters.

    Returns (success, output_or_error).
    """
    session_id = f"auto-{agent_name}-{int(time.time())}"

    cmd = [
        cli_path,
        "assignment", "accept", workspace_id,
        "--task-id", task_id,
        "--owner", agent_name,
        "--session", session_id,
    ]

    if not cli_path:
        return False, "coordinator_cli_path is not configured"
    if not db_path:
        return False, "coordinator_db_path is not configured"

    env = os.environ.copy()
    env["MAC_DB"] = db_path
    coordinator_repo = _infer_coordinator_repo(cli_path)
    if coordinator_repo:
        env["MAC_REPO"] = str(coordinator_repo)

    log.info("Executing: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "assignment accept timed out (30s)"
    except Exception as exc:
        return False, str(exc)


def _infer_coordinator_repo(cli_path: str) -> Path | None:
    """Find the coordinator repo root that owns the configured CLI wrapper."""
    try:
        path = Path(cli_path).expanduser().resolve()
    except OSError:
        return None
    candidates = [path.parent, *path.parents]
    for candidate in candidates:
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src" / "multi_agent_coordinator").is_dir()
        ):
            return candidate
    return None


def _is_allowed_bootstrap_path(relative_path: Path) -> bool:
    parts = relative_path.parts
    if len(parts) >= 5 and parts[:3] == ("docs", "project-harness", "tasks"):
        return relative_path.name == "worker-bootstrap.md"
    return parts == ("docs", "project-harness", "current", "worker-bootstrap.md")


def read_bootstrap(workspace_path: str, bootstrap_relative_path: str) -> str | None:
    """Read the bootstrap file from the workspace."""
    if not bootstrap_relative_path:
        return None
    if os.path.isabs(bootstrap_relative_path):
        log.warning("Rejecting absolute bootstrap path: %s", bootstrap_relative_path)
        return None

    try:
        workspace_root = Path(workspace_path).expanduser().resolve()
        full_path = (workspace_root / bootstrap_relative_path).resolve()
        relative_path = full_path.relative_to(workspace_root)
    except (OSError, ValueError) as exc:
        log.warning("Rejecting bootstrap path %s: %s", bootstrap_relative_path, exc)
        return None

    if not _is_allowed_bootstrap_path(relative_path):
        log.warning("Rejecting non-bootstrap path: %s", relative_path)
        return None

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, PermissionError) as exc:
        log.warning("Cannot read bootstrap %s: %s", full_path, exc)
        return None


def build_agent_report(
    action: str,
    handoff: CoordinatorHandoff,
    *,
    summary: str | None = None,
    reason: str | None = None,
) -> str:
    """Build a structured report that coordinator daemon can ingest."""
    normalized = action.lower()
    if normalized not in _REPORT_ACTIONS:
        raise ValueError(f"unsupported agent report action: {action}")
    fields = [
        "[agent-report]",
        f"action={normalized}",
        f"workspace_id={shlex.quote(handoff.workspace_id)}",
        f"task_id={shlex.quote(handoff.task_id)}",
    ]
    if summary:
        fields.append(f"summary={shlex.quote(summary)}")
    if reason:
        fields.append(f"reason={shlex.quote(reason)}")
    return " ".join(fields)


def build_handoff_prompt(
    handoff: CoordinatorHandoff,
    bootstrap_content: str | None,
    *,
    agent_name: str | None = None,
    accept_output: str | None = None,
) -> str:
    """Build the agent prompt for a coordinator handoff."""
    parts = [
        "[Coordinator Handoff Accepted]\n",
        f"Task: {handoff.task_id}",
        f"Workspace: {handoff.workspace_id}",
    ]

    if agent_name:
        parts.extend(
            [
                "\nAssignment state:",
                (
                    "- The discord-nexus runtime has already completed "
                    f"`assignment accept` for this task as `{agent_name}`."
                ),
                (
                    "- Do NOT run `assignment accept` again. The active lease "
                    "is already held by this agent."
                ),
                (
                    "- Use coordinator CLI only for later lifecycle updates, "
                    "such as branch, PR, CI, blocker, closeout, or mark-done."
                ),
            ]
        )
        if accept_output:
            sanitized_output = " ".join(accept_output.split())
            parts.append(f"- Accept result: {sanitized_output[:500]}")

    if bootstrap_content:
        parts.append("\nYour bootstrap instructions:\n")
        parts.append(bootstrap_content)
    else:
        parts.append("\nBootstrap file not found. Check with operator.")

    return "\n".join(parts)
