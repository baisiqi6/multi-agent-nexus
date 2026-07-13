#!/usr/bin/env python3
"""Read-after-write registry verification for MultiNexus deployment.

Uses the deployed Coordinate venv to open the production DB and independently
verify committed source metadata, authoritative rows, compatibility projection,
and effective resolver output against the deployed authority.

This script imports Coordinate; the parity verifier module does not.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from coordinate.db import resolve_effective_agents

# MultiNexus authority loader is safe to import (no Coordinate dependency).
from multinexus.registry_authority import load_authority


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_db(db_path: str) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def _get_source_row(conn: sqlite3.Connection, workspace_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT source_id, source_version, source_hash FROM workspace_agent_registry_sources WHERE workspace_id = ?",
        (workspace_id,),
    ).fetchone()
    return dict(row) if row else None


def _get_revision(conn: sqlite3.Connection, workspace_id: str) -> int:
    row = conn.execute(
        "SELECT agent_registry_revision FROM workspaces WHERE id = ?",
        (workspace_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"workspace not found: {workspace_id}")
    return row["agent_registry_revision"]


def _get_entry_summary(conn: sqlite3.Connection, workspace_id: str) -> dict[str, int]:
    rows = conn.execute(
        "SELECT entry_kind, COUNT(*) AS n FROM workspace_agent_registry_entries WHERE workspace_id = ? GROUP BY entry_kind",
        (workspace_id,),
    ).fetchall()
    return {row["entry_kind"]: row["n"] for row in rows}


def _get_agents_json(conn: sqlite3.Connection, workspace_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT agents_json FROM workspaces WHERE id = ?",
        (workspace_id,),
    ).fetchone()
    value = row["agents_json"] if row else None
    if not value:
        return None
    return json.loads(value)


def verify(conn: sqlite3.Connection, workspace_id: str, authority_path: str, *, strict_effective: bool) -> dict[str, Any]:
    authority = load_authority(authority_path)
    authority_entries_by_id = {e.id: e for e in authority.entries}
    authority_json = {
        e.id: {
            "discord_user_id": e.discord_user_id,
            "display_name": e.display_name,
            "agent_type": e.agent_type,
        }
        for e in authority.entries
    }

    errors: list[str] = []
    diagnostics: dict[str, Any] = {}

    # Schema version
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    diagnostics["schema_version"] = user_version
    if user_version < 12:
        return {
            "ok": False,
            "workspace_id": workspace_id,
            "source_id": authority.source_id,
            "source_version": authority.source_version,
            "source_hash": authority.source_hash,
            "executor_catalog_hash": authority.executor_catalog_hash,
            "revision": None,
            "errors": [f"schema version {user_version} is below v12"],
            "diagnostics": diagnostics,
        }

    # Source row
    source_row = _get_source_row(conn, workspace_id)
    diagnostics["source_row"] = source_row
    if source_row is None:
        errors.append("no source row found")
    else:
        if source_row["source_id"] != authority.source_id:
            errors.append("source_id mismatch")
        if source_row["source_version"] != authority.source_version:
            errors.append("source_version mismatch")
        if source_row["source_hash"] != authority.source_hash:
            errors.append("source_hash mismatch")

    # Workspace revision
    try:
        revision = _get_revision(conn, workspace_id)
        diagnostics["revision"] = revision
        if not isinstance(revision, int) or revision < 1:
            errors.append(f"invalid registry revision: {revision!r}")
    except ValueError as exc:
        errors.append(str(exc))
        revision = None

    # Entry kind summary
    summary = _get_entry_summary(conn, workspace_id)
    diagnostics["entry_summary"] = summary
    authoritative_count = summary.get("authoritative", 0)
    legacy_count = summary.get("legacy", 0)
    override_count = summary.get("override", 0)

    if authoritative_count != len(authority.entries):
        errors.append(
            f"authoritative entry count mismatch: {authoritative_count} vs authority {len(authority.entries)}"
        )
    if legacy_count != 0:
        errors.append(f"legacy entries remain: {legacy_count}")

    # Active overrides
    now = _utc_now()
    active_overrides = conn.execute(
        """
        SELECT agent_name FROM workspace_agent_registry_entries
        WHERE workspace_id = ? AND entry_kind = 'override'
          AND (expires_at IS NULL OR expires_at > ?)
        ORDER BY agent_name
        """,
        (workspace_id, now),
    ).fetchall()
    diagnostics["active_overrides"] = [row["agent_name"] for row in active_overrides]

    # Compatibility projection (workspaces.agents_json)
    agents_json = _get_agents_json(conn, workspace_id)
    diagnostics["agents_json_count"] = len(agents_json) if agents_json is not None else None
    if agents_json != authority_json:
        errors.append("compatibility agents_json does not match authority")

    # Effective resolver output
    try:
        effective = resolve_effective_agents(conn, workspace_id, now_utc=now)
    except ValueError as exc:
        errors.append(f"effective resolver error: {exc}")
        effective = None

    diagnostics["effective_count"] = len(effective) if effective is not None else None
    if effective is not None:
        if active_overrides and strict_effective:
            errors.append(
                f"active overrides present; strict effective parity failed: {[row['agent_name'] for row in active_overrides]}"
            )
        elif not active_overrides and effective != authority_json:
            errors.append("effective resolver output does not match authority")

    # Authoritative row canonical parity
    if source_row and source_row["source_hash"] == authority.source_hash and authoritative_count == len(authority.entries):
        rows = conn.execute(
            """
            SELECT agent_name, discord_user_id, display_name, agent_type
            FROM workspace_agent_registry_entries
            WHERE workspace_id = ? AND entry_kind = 'authoritative'
            ORDER BY agent_name
            """,
            (workspace_id,),
        ).fetchall()
        db_json = {
            row["agent_name"]: {
                "discord_user_id": row["discord_user_id"],
                "display_name": row["display_name"],
                "agent_type": row["agent_type"],
            }
            for row in rows
        }
        if db_json != authority_json:
            errors.append("authoritative row fields do not match authority")

    # Executor catalog source parity
    executor_source_row = conn.execute(
        "SELECT source_id, source_version, catalog_hash FROM executor_catalog_sources WHERE source_id = ?",
        (authority.source_id,),
    ).fetchone()
    diagnostics["executor_source_row"] = dict(executor_source_row) if executor_source_row else None
    if executor_source_row is None:
        errors.append("no executor catalog source row found")
    else:
        if executor_source_row["source_id"] != authority.source_id:
            errors.append("executor catalog source_id mismatch")
        if executor_source_row["source_version"] != authority.source_version:
            errors.append("executor catalog source_version mismatch")
        if executor_source_row["catalog_hash"] != authority.executor_catalog_hash:
            errors.append("executor catalog hash mismatch")

    # Executor definitions parity
    db_definitions = conn.execute(
        "SELECT id, provider, adapter, capabilities_json FROM executor_definitions WHERE source_id = ? ORDER BY id",
        (authority.source_id,),
    ).fetchall()
    diagnostics["executor_definition_count"] = len(db_definitions)
    if len(db_definitions) != len(authority.executor_definitions):
        errors.append(
            f"executor definition count mismatch: {len(db_definitions)} vs authority {len(authority.executor_definitions)}"
        )
    else:
        auth_defs_by_id = {d.id: d for d in authority.executor_definitions}
        for row in db_definitions:
            auth_def = auth_defs_by_id.get(row["id"])
            if auth_def is None:
                errors.append(f"unexpected executor definition in DB: {row['id']!r}")
                continue
            if row["provider"] != auth_def.provider:
                errors.append(f"executor definition {row['id']!r} provider mismatch")
            if row["adapter"] != auth_def.adapter:
                errors.append(f"executor definition {row['id']!r} adapter mismatch")
            if json.loads(row["capabilities_json"]) != list(auth_def.capabilities):
                errors.append(f"executor definition {row['id']!r} capabilities mismatch")

    # Executor instance bindings parity
    db_bindings = conn.execute(
        "SELECT agent_id, executor_definition_id, runner_profile_id, enabled "
        "FROM executor_instance_bindings WHERE source_id = ? ORDER BY agent_id",
        (authority.source_id,),
    ).fetchall()
    diagnostics["executor_binding_count"] = len(db_bindings)
    if len(db_bindings) != len(authority.executor_bindings):
        errors.append(
            f"executor binding count mismatch: {len(db_bindings)} vs authority {len(authority.executor_bindings)}"
        )
    else:
        auth_bindings_by_agent = {b.agent_id: b for b in authority.executor_bindings}
        for row in db_bindings:
            auth_binding = auth_bindings_by_agent.get(row["agent_id"])
            if auth_binding is None:
                errors.append(f"unexpected executor binding in DB: {row['agent_id']!r}")
                continue
            if row["executor_definition_id"] != auth_binding.executor_definition_id:
                errors.append(f"executor binding {row['agent_id']!r} definition mismatch")
            if row["runner_profile_id"] != auth_binding.runner_profile_id:
                errors.append(f"executor binding {row['agent_id']!r} runner_profile mismatch")
            if bool(row["enabled"]) != auth_binding.enabled:
                errors.append(f"executor binding {row['agent_id']!r} enabled mismatch")

    return {
        "ok": not errors,
        "workspace_id": workspace_id,
        "source_id": authority.source_id,
        "source_version": authority.source_version,
        "source_hash": authority.source_hash,
        "executor_catalog_hash": authority.executor_catalog_hash,
        "revision": revision,
        "errors": errors,
        "diagnostics": diagnostics,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Coordinate DB registry against authority")
    parser.add_argument("--db", required=True, help="Path to coordinate SQLite DB")
    parser.add_argument("--workspace-id", required=True, default="discord-nexus")
    parser.add_argument("--authority", required=True, help="Path to agent-registry.toml")
    parser.add_argument(
        "--strict-effective",
        action="store_true",
        help="Fail if active overrides shadow the authority",
    )
    args = parser.parse_args(argv)

    conn = _load_db(args.db)
    try:
        result = verify(
            conn,
            workspace_id=args.workspace_id,
            authority_path=args.authority,
            strict_effective=args.strict_effective,
        )
    finally:
        conn.close()

    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
