#!/usr/bin/env python3
"""P9-2A task-mirror split_operation metadata repair — production audit artifact.

Imports only Python stdlib ``sqlite3``.  Does not import Coordinate or MultiNexus
modules so that it can be reviewed, hashed, and executed as a standalone artifact
against a production SQLite database copy.

Usage::

    python repair_task_mirror_metadata.py \\
        --db /path/to/coordinate.db \\
        --workspace-id discord-nexus \\
        --task-id p9-2a-executor-identity-registry \\
        --operation-id 62175918-ce07-4da5-8bf4-03b9784fb64e

Returns a JSON object to stdout.  On any repair error prints JSON to stderr and
exits with code 2.  Payload content is **never** leaked in error output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONTRACT_VERSION = 1
VALID_OPERATION_KINDS = frozenset({"task.create", "issue.materialize"})
TARGET_KIND_CHECKLIST_TASK = "checklist_task"
ACTOR_CODEX_OPERATOR = "codex-operator"
EVENT_TYPE_PROJECTION_REPAIRED = "projection.repaired"

# uuid5 namespace — mirrors Coordinate convention (uuid.NAMESPACE_URL).
UUID5_NAMESPACE = uuid.NAMESPACE_URL

# The six metadata keys validated in the event's split_operation and
# merged into the task mirror payload.
SPLIT_OPERATION_METADATA_KEYS: tuple[str, ...] = (
    "contract_version",
    "operation_id",
    "operation_kind",
    "input_fingerprint",
    "before_fingerprint",
    "after_fingerprint",
)

_EVENT_TYPE_BY_OP_KIND: dict[str, str] = {
    "task.create": "plan.ready",
    "issue.materialize": "issue.materialized",
}

# ---------------------------------------------------------------------------
# Validation helpers (stdlib only — deliberate duplicate of Coordinate shapes)
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _validate_canonical_uuid(value: str) -> str:
    """Return a lowercase canonical UUID or raise ValueError."""
    if not isinstance(value, str):
        raise ValueError(f"must be a string, got {type(value).__name__}")
    lowered = value.lower()
    if not _UUID_RE.match(lowered):
        raise ValueError(f"not a valid lowercase RFC 4122 UUID: {value!r}")
    try:
        parsed = uuid.UUID(lowered)
    except ValueError as exc:
        raise ValueError(f"UUID parse failure: {exc}") from exc
    if lowered != str(parsed):
        raise ValueError(f"must be canonical lowercase, got {value!r}")
    return lowered


def _validate_sha256_hex(value: str) -> str:
    """Return a lowercase 64-hex SHA-256 string or raise ValueError."""
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(
            f"must be a 64-character lowercase hex string, got {value!r}"
        )
    if not _SHA256_RE.match(value):
        raise ValueError(
            f"must contain only hex digits 0-9a-f, got {value!r}"
        )
    return value


def _utc_now() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_hex(data: str) -> str:
    """Return lowercase SHA-256 hex digest of a UTF-8 string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    """Match Coordinate's canonical SQLite JSON representation."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _build_idempotency_key(
    workspace_id: str, task_id: str, operation_id: str
) -> str:
    """Deterministic idempotency key for the projection.repaired event."""
    return (
        f"{workspace_id}:{task_id}:projection.repaired"
        f":split_operation:{operation_id}"
    )


def _build_repair_event_id(idempotency_key: str) -> str:
    """Return a deterministic uuid5 event id."""
    return str(uuid.uuid5(UUID5_NAMESPACE, idempotency_key))


def _build_repair_event_payload(
    *,
    workspace_id: str,
    task_id: str,
    operation_id: str,
    contract_version: int,
    operation_kind: str,
    input_fingerprint: str,
    before_fingerprint: str,
    after_fingerprint: str,
    before_payload_sha256: str,
    after_payload_sha256: str,
    repaired_fields: list[str],
    restored_phase: str,
) -> dict[str, Any]:
    """Build the redacted audit payload: ids, fingerprints, hashes, and repaired fields."""
    return {
        "workspace_id": workspace_id,
        "task_id": task_id,
        "operation_id": operation_id,
        "contract_version": contract_version,
        "operation_kind": operation_kind,
        "input_fingerprint": input_fingerprint,
        "before_fingerprint": before_fingerprint,
        "after_fingerprint": after_fingerprint,
        "before_payload_sha256": before_payload_sha256,
        "after_payload_sha256": after_payload_sha256,
        "repaired_fields": repaired_fields,
        "restored_phase": restored_phase,
    }


def _validate_existing_repair_event(
    event: sqlite3.Row,
    *,
    repair_event_id: str,
    workspace_id: str,
    task_id: str,
    operation_id: str,
    idempotency_key: str,
    record_event_id: str,
    row: sqlite3.Row,
    current_payload_sha256: str,
    restored_phase: str,
) -> None:
    """Fail closed unless an existing event is the exact deterministic audit row."""
    expected_columns = {
        "id": repair_event_id,
        "workspace_id": workspace_id,
        "event_type": EVENT_TYPE_PROJECTION_REPAIRED,
        "actor": ACTOR_CODEX_OPERATOR,
        "target": f"task:{task_id}",
        "task_id": task_id,
        "causation_id": record_event_id,
        "idempotency_key": idempotency_key,
    }
    for column, expected in expected_columns.items():
        if event[column] != expected:
            raise RepairError(
                f"existing repair event metadata differs in {column}",
                "repair_event_metadata_conflict",
            )

    try:
        payload = json.loads(event["payload_json"])
    except (json.JSONDecodeError, TypeError) as exc:
        raise RepairError(
            f"existing repair event {event['id']!r} has invalid payload_json",
            "existing_event_payload_invalid",
        ) from exc
    expected_keys = set(
        _build_repair_event_payload(
            workspace_id=workspace_id,
            task_id=task_id,
            operation_id=operation_id,
            contract_version=row["contract_version"],
            operation_kind=row["operation_kind"],
            input_fingerprint=row["input_fingerprint"],
            before_fingerprint=row["before_fingerprint"],
            after_fingerprint=row["after_fingerprint"],
            before_payload_sha256="0" * 64,
            after_payload_sha256="0" * 64,
            repaired_fields=["phase"],
            restored_phase=restored_phase,
        )
    )
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise RepairError(
            "existing repair event payload keys differ from the audit contract",
            "repair_event_payload_conflict",
        )
    fixed = {
        "workspace_id": workspace_id,
        "task_id": task_id,
        "operation_id": operation_id,
        "contract_version": row["contract_version"],
        "operation_kind": row["operation_kind"],
        "input_fingerprint": row["input_fingerprint"],
        "before_fingerprint": row["before_fingerprint"],
        "after_fingerprint": row["after_fingerprint"],
        "restored_phase": restored_phase,
    }
    if any(payload.get(key) != value for key, value in fixed.items()):
        raise RepairError(
            "existing repair event payload does not match the immutable ledger",
            "repair_event_payload_conflict",
        )
    try:
        _validate_sha256_hex(payload.get("before_payload_sha256"))
        _validate_sha256_hex(payload.get("after_payload_sha256"))
    except ValueError as exc:
        raise RepairError(
            "existing repair event payload hashes are invalid",
            "repair_event_payload_conflict",
        ) from exc
    if payload["after_payload_sha256"] != current_payload_sha256:
        raise RepairError(
            "existing repair event after-payload hash differs from the current mirror",
            "repair_event_payload_conflict",
        )
    repaired_fields = payload.get("repaired_fields")
    if (
        not isinstance(repaired_fields, list)
        or not repaired_fields
        or repaired_fields != sorted(repaired_fields)
        or len(repaired_fields) != len(set(repaired_fields))
        or not set(repaired_fields).issubset({"phase", "split_operation"})
    ):
        raise RepairError(
            "existing repair event repaired_fields is not an exact allowed sorted list",
            "repair_event_payload_conflict",
        )


# ---------------------------------------------------------------------------
# Repair error
# ---------------------------------------------------------------------------


class RepairError(Exception):
    """A repair-preventing condition.  Never leaks payload content."""

    def __init__(self, message: str, error_type: str) -> None:
        super().__init__(message)
        self.error_type = error_type


# ---------------------------------------------------------------------------
# Core repair function
# ---------------------------------------------------------------------------


def repair_task_mirror_metadata(
    conn: sqlite3.Connection,
    *,
    workspace_id: str,
    task_id: str,
    operation_id: str,
) -> dict[str, Any]:
    """Validate the split_operations ledger and repair the task mirror.

    Opens its own ``BEGIN IMMEDIATE`` transaction; the caller must provide a
    fresh ``sqlite3.Connection``.

    Returns a dict with keys ``status``, ``workspace_id``, ``task_id``,
    ``operation_id``, ``repair_event_id``, ``before_payload_sha256``,
    ``after_payload_sha256``.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        return _repair_impl(conn, workspace_id=workspace_id, task_id=task_id, operation_id=operation_id)
    except BaseException:
        conn.rollback()
        raise


def _repair_impl(
    conn: sqlite3.Connection,
    *,
    workspace_id: str,
    task_id: str,
    operation_id: str,
) -> dict[str, Any]:
    # ---- 1. Locate and validate the split_operations ledger row ----
    rows = conn.execute(
        """SELECT operation_id, contract_version, operation_kind,
                  workspace_id, target_kind, target_id,
                  source_kind, source_id,
                  input_fingerprint, before_fingerprint, after_fingerprint,
                  status, record_event_id, created_at, updated_at
           FROM split_operations
           WHERE workspace_id = ?
             AND target_kind = ?
             AND target_id = ?
           ORDER BY rowid""",
        (workspace_id, TARGET_KIND_CHECKLIST_TASK, task_id),
    ).fetchall()

    if len(rows) == 0:
        raise RepairError(
            f"no split_operations row for workspace {workspace_id!r} "
            f"target {TARGET_KIND_CHECKLIST_TASK!r} id {task_id!r}",
            "ledger_not_found",
        )
    if len(rows) > 1:
        raise RepairError(
            f"{len(rows)} split_operations rows for workspace {workspace_id!r} "
            f"target {TARGET_KIND_CHECKLIST_TASK!r} id {task_id!r}; expected exactly 1",
            "multiple_ledger_rows",
        )

    row = rows[0]
    if row["operation_id"] != operation_id:
        raise RepairError(
            f"ledger operation_id {row['operation_id']!r} does not match "
            f"requested {operation_id!r}",
            "operation_id_mismatch",
        )

    # ---- 2. Validate ledger contract shapes ----
    if row["contract_version"] != CONTRACT_VERSION:
        raise RepairError(
            f"ledger contract_version {row['contract_version']} != {CONTRACT_VERSION}",
            "invalid_contract_version",
        )
    if row["operation_kind"] not in VALID_OPERATION_KINDS:
        raise RepairError(
            f"ledger operation_kind {row['operation_kind']!r} not in {sorted(VALID_OPERATION_KINDS)}",
            "invalid_operation_kind",
        )
    if row["status"] != "record_applied":
        raise RepairError(
            f"ledger status {row['status']!r} is not record_applied",
            "invalid_operation_status",
        )

    try:
        _validate_canonical_uuid(row["operation_id"])
    except ValueError as exc:
        raise RepairError(f"ledger operation_id invalid: {exc}", "invalid_operation_id") from exc

    for col, label in [
        ("input_fingerprint", "input_fingerprint"),
        ("before_fingerprint", "before_fingerprint"),
        ("after_fingerprint", "after_fingerprint"),
    ]:
        try:
            _validate_sha256_hex(row[col])
        except ValueError as exc:
            raise RepairError(f"ledger {label} invalid: {exc}", "invalid_fingerprint") from exc

    # ---- 3. Validate record_event_id and its payload ----
    record_event_id = row["record_event_id"]
    if not record_event_id:
        raise RepairError(
            "ledger record_event_id is null",
            "missing_record_event_id",
        )

    event_row = conn.execute(
        """SELECT id, workspace_id, event_type, task_id, payload_json
           FROM events WHERE id = ?""",
        (record_event_id,),
    ).fetchone()

    if event_row is None:
        raise RepairError(
            f"ledger record_event_id {record_event_id!r} not found in events table",
            "record_event_not_found",
        )
    if event_row["workspace_id"] != workspace_id:
        raise RepairError(
            f"event workspace_id {event_row['workspace_id']!r} != {workspace_id!r}",
            "event_workspace_mismatch",
        )
    if event_row["task_id"] != task_id:
        raise RepairError(
            f"event task_id {event_row['task_id']!r} != {task_id!r}",
            "event_task_mismatch",
        )

    expected_event_type = _EVENT_TYPE_BY_OP_KIND.get(row["operation_kind"])
    if expected_event_type is not None and event_row["event_type"] != expected_event_type:
        raise RepairError(
            f"event type {event_row['event_type']!r} != expected {expected_event_type!r} "
            f"for operation_kind {row['operation_kind']!r}",
            "event_type_mismatch",
        )

    # Validate event payload contains split_operation with matching fields
    try:
        event_payload = json.loads(event_row["payload_json"])
    except (json.JSONDecodeError, TypeError) as exc:
        raise RepairError(
            f"event {record_event_id!r} payload_json is not valid JSON: {exc}",
            "event_payload_not_json",
        ) from exc

    if not isinstance(event_payload, dict):
        raise RepairError(
            f"event {record_event_id!r} payload is not a JSON object",
            "event_payload_not_dict",
        )
    event_split_op = event_payload.get("split_operation")
    if not isinstance(event_split_op, dict):
        raise RepairError(
            f"event {record_event_id!r} payload has no split_operation dict",
            "event_missing_split_operation",
        )

    if set(event_split_op) != set(SPLIT_OPERATION_METADATA_KEYS):
        raise RepairError(
            f"event {record_event_id!r} split_operation keys do not match the v1 contract",
            "event_split_operation_key_mismatch",
        )

    # Check that the six required metadata keys match the immutable ledger.
    for key in SPLIT_OPERATION_METADATA_KEYS:
        if key not in event_split_op:
            raise RepairError(
                f"event {record_event_id!r} split_operation missing key {key!r}",
                "event_split_operation_missing_key",
            )
        if event_split_op[key] != row[key]:
            raise RepairError(
                f"event {record_event_id!r} split_operation.{key} "
                f"{event_split_op[key]!r} != ledger {row[key]!r}",
                "event_split_operation_field_mismatch",
            )
    expected_phase = event_payload.get("phase")
    if not isinstance(expected_phase, str) or not expected_phase:
        raise RepairError(
            f"event {record_event_id!r} phase is not a non-empty string",
            "event_phase_invalid",
        )

    # ---- 4. Find the task mirror ----
    task_rows = conn.execute(
        """SELECT workspace_id, task_id, phase, owner, branch, pr,
                  last_event_id, payload_json, updated_at
           FROM tasks
           WHERE workspace_id = ? AND task_id = ?""",
        (workspace_id, task_id),
    ).fetchall()

    if len(task_rows) == 0:
        raise RepairError(
            f"no task mirror for {workspace_id!r}/{task_id!r}",
            "task_not_found",
        )
    if len(task_rows) > 1:
        raise RepairError(
            f"{len(task_rows)} task mirrors for {workspace_id!r}/{task_id!r}; expected exactly 1",
            "multiple_task_mirrors",
        )

    task_row = task_rows[0]
    if task_row["phase"] != expected_phase:
        raise RepairError(
            "task phase column does not match the immutable record-event phase",
            "task_column_phase_mismatch",
        )
    try:
        task_payload = json.loads(task_row["payload_json"])
    except (json.JSONDecodeError, TypeError) as exc:
        raise RepairError(
            f"task {task_id!r} payload_json is not valid JSON: {exc}",
            "task_payload_not_json",
        ) from exc

    if not isinstance(task_payload, dict):
        raise RepairError(
            f"task {task_id!r} payload is not a JSON object",
            "task_payload_not_dict",
        )

    has_split_operation = "split_operation" in task_payload
    current_split_op = task_payload.get("split_operation")
    has_phase = "phase" in task_payload
    current_phase = task_payload.get("phase")
    before_payload_sha256 = _sha256_hex(task_row["payload_json"])

    # ---- 5. Build the expected split_operation metadata object ----
    expected_meta: dict[str, Any] = {
        "contract_version": row["contract_version"],
        "operation_id": row["operation_id"],
        "operation_kind": row["operation_kind"],
        "input_fingerprint": row["input_fingerprint"],
        "before_fingerprint": row["before_fingerprint"],
        "after_fingerprint": row["after_fingerprint"],
    }

    idempotency_key = _build_idempotency_key(workspace_id, task_id, operation_id)
    repair_event_id = _build_repair_event_id(idempotency_key)

    # ---- 6. Validate present values, then repair exactly the missing fields ----
    if has_split_operation:
        if not isinstance(current_split_op, dict):
            raise RepairError(
                f"task {task_id!r} payload split_operation is not a dict: {type(current_split_op).__name__}",
                "split_operation_not_dict",
            )
        if set(current_split_op) != set(SPLIT_OPERATION_METADATA_KEYS):
            raise RepairError(
                f"task {task_id!r} payload split_operation has unexpected keys",
                "split_operation_key_mismatch",
            )
        if current_split_op != expected_meta:
            raise RepairError(
                f"task {task_id!r} payload split_operation conflicts with the ledger",
                "split_operation_value_conflict",
            )
    if has_phase:
        if not isinstance(current_phase, str) or current_phase != expected_phase:
            raise RepairError(
                f"task {task_id!r} payload phase conflicts with the validated phase",
                "payload_phase_conflict",
            )

    repaired_fields = sorted(
        field
        for field, present in (
            ("phase", has_phase),
            ("split_operation", has_split_operation),
        )
        if not present
    )
    if repaired_fields:
        return _perform_repair(
            conn=conn,
            task_payload=task_payload,
            expected_meta=expected_meta,
            expected_phase=expected_phase,
            repaired_fields=repaired_fields,
            before_payload_sha256=before_payload_sha256,
            idempotency_key=idempotency_key,
            repair_event_id=repair_event_id,
            workspace_id=workspace_id,
            task_id=task_id,
            operation_id=operation_id,
            row=row,
        )

    # Both fields are exact: preexisting-correct or exact retry.
    # Check whether a projection.repaired event already exists
    existing_event = conn.execute(
        """SELECT id, workspace_id, event_type, actor, target, task_id,
                  causation_id, idempotency_key, payload_json
           FROM events WHERE idempotency_key = ?""",
        (idempotency_key,),
    ).fetchone()

    if existing_event is not None:
        _validate_existing_repair_event(
            existing_event,
            repair_event_id=repair_event_id,
            workspace_id=workspace_id,
            task_id=task_id,
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            record_event_id=record_event_id,
            row=row,
            current_payload_sha256=before_payload_sha256,
            restored_phase=expected_phase,
        )
        # Exact retry: return same event id, zero writes.
        conn.commit()
        return {
            "status": "already_repaired",
            "workspace_id": workspace_id,
            "task_id": task_id,
            "operation_id": operation_id,
            "repair_event_id": existing_event["id"],
            "before_payload_sha256": json.loads(existing_event["payload_json"])["before_payload_sha256"],
            "after_payload_sha256": before_payload_sha256,
        }

    # Preexisting equal fields without a projection.repaired event.
    conn.commit()
    return {
        "status": "already_repaired",
        "workspace_id": workspace_id,
        "task_id": task_id,
        "operation_id": operation_id,
        "repair_event_id": None,
        "before_payload_sha256": before_payload_sha256,
        "after_payload_sha256": before_payload_sha256,
    }


def _perform_repair(
    *,
    conn: sqlite3.Connection,
    task_payload: dict[str, Any],
    expected_meta: dict[str, Any],
    expected_phase: str,
    repaired_fields: list[str],
    before_payload_sha256: str,
    idempotency_key: str,
    repair_event_id: str,
    workspace_id: str,
    task_id: str,
    operation_id: str,
    row: sqlite3.Row,
) -> dict[str, Any]:
    """Atomically merge only missing validated fields and append its audit event."""

    repaired_payload = dict(task_payload)
    if "phase" in repaired_fields:
        repaired_payload["phase"] = expected_phase
    if "split_operation" in repaired_fields:
        repaired_payload["split_operation"] = expected_meta
    after_payload_json = _canonical_json(repaired_payload)
    after_payload_sha256 = _sha256_hex(after_payload_json)

    # Check for existing idempotency event BEFORE we write anything
    existing = conn.execute(
        """SELECT id, workspace_id, event_type, actor, target, task_id,
                  causation_id, idempotency_key, payload_json
           FROM events WHERE idempotency_key = ?""",
        (idempotency_key,),
    ).fetchone()

    if existing is not None:
        raise RepairError(
            f"repair event {existing['id']!r} exists while mirror metadata is missing",
            "repair_event_without_mirror_metadata",
        )

    # ---- Write the projection.repaired event ----
    event_payload = _build_repair_event_payload(
        workspace_id=workspace_id,
        task_id=task_id,
        operation_id=operation_id,
        contract_version=row["contract_version"],
        operation_kind=row["operation_kind"],
        input_fingerprint=row["input_fingerprint"],
        before_fingerprint=row["before_fingerprint"],
        after_fingerprint=row["after_fingerprint"],
        before_payload_sha256=before_payload_sha256,
        after_payload_sha256=after_payload_sha256,
        repaired_fields=repaired_fields,
        restored_phase=expected_phase,
    )
    now = _utc_now()

    try:
        conn.execute(
            """INSERT INTO events (id, workspace_id, event_type, actor, target,
                                  task_id, causation_id, idempotency_key,
                                  payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                repair_event_id,
                workspace_id,
                EVENT_TYPE_PROJECTION_REPAIRED,
                ACTOR_CODEX_OPERATOR,
                f"task:{task_id}",
                task_id,
                row["record_event_id"],
                idempotency_key,
                _canonical_json(event_payload),
                now,
            ),
        )
    except sqlite3.IntegrityError as exc:
        # Could be a race condition on idempotency_key UNIQUE constraint
        raise RepairError(
            f"failed to insert projection.repaired event: {exc}",
            "event_insert_integrity_error",
        ) from exc

    # ---- Update task mirror payload ----
    _update_task_payload(conn, workspace_id, task_id, after_payload_json)

    conn.commit()
    return {
        "status": "repaired",
        "workspace_id": workspace_id,
        "task_id": task_id,
        "operation_id": operation_id,
        "repair_event_id": repair_event_id,
        "before_payload_sha256": before_payload_sha256,
        "after_payload_sha256": after_payload_sha256,
    }


def _update_task_payload(
    conn: sqlite3.Connection,
    workspace_id: str,
    task_id: str,
    payload_json: str,
) -> None:
    """Update only payload_json; preserve every other task column byte-for-byte."""
    conn.execute(
        """UPDATE tasks SET payload_json = ?
           WHERE workspace_id = ? AND task_id = ?""",
        (payload_json, workspace_id, task_id),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="P9-2A task-mirror split_operation metadata repair",
    )
    parser.add_argument("--db", required=True, help="Path to Coordinate SQLite database")
    parser.add_argument("--workspace-id", required=True, help="Workspace id")
    parser.add_argument("--task-id", required=True, help="Task id")
    parser.add_argument("--operation-id", required=True, help="Split operation UUID")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        result = repair_task_mirror_metadata(
            conn,
            workspace_id=args.workspace_id,
            task_id=args.task_id,
            operation_id=args.operation_id,
        )
    except RepairError as exc:
        error_output = {
            "error": True,
            "type": exc.error_type,
            "message": str(exc),
            "workspace_id": args.workspace_id,
            "task_id": args.task_id,
            "operation_id": args.operation_id,
        }
        json.dump(error_output, sys.stderr, ensure_ascii=False, sort_keys=True)
        sys.stderr.write("\n")
        sys.stderr.flush()
        sys.exit(2)
    except Exception as exc:
        error_output = {
            "error": True,
            "type": "internal_error",
            "message": f"unexpected error: {exc}",
            "workspace_id": args.workspace_id,
            "task_id": args.task_id,
            "operation_id": args.operation_id,
        }
        json.dump(error_output, sys.stderr, ensure_ascii=False, sort_keys=True)
        sys.stderr.write("\n")
        sys.stderr.flush()
        sys.exit(2)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    _main()
