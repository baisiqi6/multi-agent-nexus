#!/usr/bin/env python3
"""P9-3C1 P2 Inert Production Controller.

State machine, read-only DB evidence, sealed ledger, P3 authorization fence.
Invoked only via the thin root/run-id entrypoint:
  sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh <subcommand> ...

Subcommands: prepare, preflight, status, run, cleanup.

P2 inert: only prepare/preflight/status are safe to invoke against production.
run/cleanup require a P3 authorization artifact that does not exist in P2.
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import hashlib
import hmac
import json
import os
import grp
import pwd
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants — production paths, never environment-overridden.
# ---------------------------------------------------------------------------

STATE_ROOT_BASE = "/var/tmp/multinexus-p9-3c1"
PRODUCTION_DB = "/var/lib/coordinate/coord.sqlite3"
PRODUCTION_CLI = "/usr/local/bin/coord-local"
PRODUCTION_LOCK_HELPER = "/usr/local/sbin/coordinate-production-mutation-lock"
INSTALLED_ROOT = "/opt/multinexus"
COORDINATE_ROOT = "/opt/coordinate"
EXPECTED_SCHEMA = 13
RUN_ID_REGEX = re.compile(r"^p9-3c1-prod-[0-9]{8}t[0-9]{6}z-[0-9a-f]{8}$")
RUN_ID_MAX_BYTES = 42
LOCK_OWNER = "p9-3c1-controller"
LOCK_ACTION_PREFIX = "p9-3c1-run:"
AUTH_CONTRACT_VERSION = 1
AUTH_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
AUTH_NONCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
AUTH_EXACT_KEYS = {
    "contract_version",
    "run_id",
    "manifest_sha256",
    "installed_revisions",
    "installed_hashes",
    "p3_bootstrap_sha256",
    "review_artifact_sha256",
    "reviewer_verdict",
    "budgets",
    "expiry_utc",
    "nonce",
}
AUTH_EXACT_BUDGETS = {
    "total_requests": 5,
    "max_active_units": 2,
    "provider_network": 0,
    "external_delivery": 0,
}
MATRIX_LABELS = ("J1", "J2", "J3", "J4", "J5")
MATRIX_COMPLETE_ENVELOPE = (
    '{"contract_version":1,"mode":"complete","quiet_seconds":75,'
    '"spawn_descendant":false}'
)
MATRIX_HOLD_ENVELOPE = (
    '{"contract_version":1,"mode":"hold","quiet_seconds":75,'
    '"spawn_descendant":true}'
)
MATRIX_REPLY = {"destination": "local", "platform": "stdout"}
MATRIX_WAIT_SECONDS = 240.0

# 18 exact forward phases (plan §9).
PHASES: list[str] = [
    "sealed",
    "preflight-ok",
    "lock-held",
    "baseline-captured",
    "workspace-ready",
    "agents-online",
    "executor-v1-disabled",
    "capacity-v1-active",
    "executor-v2-enabled",
    "matrix-running",
    "matrix-verified",
    "intake-frozen",
    "units-quiescent",
    "executor-v3-disabled",
    "capacity-v2-empty",
    "executor-v4-empty",
    "agents-offline",
    "canonical-compared",
    "done",
]

PHASE_INDEX: dict[str, int] = {p: i for i, p in enumerate(PHASES)}

# ---------------------------------------------------------------------------
# Seams for dependency injection in tests.
# ---------------------------------------------------------------------------

_seams: dict[str, Any] = {
    "state_root_base": STATE_ROOT_BASE,
    "production_db": PRODUCTION_DB,
    "production_cli": PRODUCTION_CLI,
    "lock_helper": PRODUCTION_LOCK_HELPER,
    "installed_root": INSTALLED_ROOT,
    "coordinate_root": COORDINATE_ROOT,
    "config_dir": os.path.join(
        INSTALLED_ROOT, "multinexus", "fixture", "config", "p9-3c1"
    ),
    "helper_path": os.path.join(
        INSTALLED_ROOT, "multinexus", "fixture", "bin", "p9-3c0-unit.sh"
    ),
    "fixture_bin": os.path.join(
        INSTALLED_ROOT, "multinexus", "fixture", "bin", "p9-3c0-fixture.py"
    ),
    "python_path": os.path.join(INSTALLED_ROOT, ".venv", "bin", "python"),
    "now_utc": lambda: datetime.datetime.now(datetime.timezone.utc),
    "os_getuid": os.getuid,
    "os_geteuid": os.geteuid,
    "run_command": None,  # set to real _run_command or test fake
    "collect_installed_hashes": None,
    "collect_revisions": None,
    "collect_launcher_files": None,
    "canonical_projection": None,
    "matrix_observer": None,
    "final_observer": None,
    "sleep": time.sleep,
    "monotonic": time.monotonic,
    "lock_status": None,
    "lock_acquire": None,
    "lock_release": None,
    "hostname": lambda: os.uname().nodename,
    "resolve_user": lambda name: pwd.getpwnam(name).pw_uid,
    "resolve_group": lambda name: grp.getgrnam(name).gr_gid,
    "validate_owner_mode": lambda path, uid, gid, mode: validate_owner_mode(path, uid, gid, mode),
    "chown": os.chown,
}


def _set_seam(key: str, value: Any) -> None:
    _seams[key] = value


# ---------------------------------------------------------------------------
# Validation primitives
# ---------------------------------------------------------------------------


def validate_run_id(run_id: str) -> str:
    """Validate run-id against the exact production regex. Returns canonical id."""
    if not isinstance(run_id, str):
        raise ControllerError(f"run_id must be str, got {type(run_id).__name__}")
    if not RUN_ID_REGEX.match(run_id):
        raise ControllerError(f"invalid run-id format: {run_id!r}")
    if len(run_id.encode("utf-8")) > RUN_ID_MAX_BYTES:
        raise ControllerError(f"run-id exceeds {RUN_ID_MAX_BYTES} bytes: {run_id!r}")
    return run_id


def validate_absolute_path(path: str, *, allow_nonexistent: bool = False) -> str:
    """Validate path is absolute, canonical, rejects symlink traversal."""
    if not isinstance(path, str):
        raise ControllerError(f"path must be str, got {type(path).__name__}")
    if not os.path.isabs(path):
        raise ControllerError(f"path must be absolute: {path!r}")
    if os.path.normpath(path) != path:
        raise ControllerError(f"path must be normalized: {path!r}")
    try:
        real = os.path.realpath(path)
    except OSError as exc:
        raise ControllerError(f"cannot resolve path {path!r}: {exc}")
    if not allow_nonexistent and not os.path.exists(real):
        raise ControllerError(f"path does not exist: {real!r}")
    # Canonical equality rejects both a final symlink and symlinked ancestors.
    if os.path.exists(path) and real != path:
        raise ControllerError(f"path traverses a symlink: {path!r} -> {real!r}")
    return real


def validate_single_link(path: str) -> str:
    """Require regular file, single hard link, no symlink."""
    canonical = validate_absolute_path(path)
    st = os.stat(canonical, follow_symlinks=False)
    if stat.S_ISLNK(st.st_mode):
        raise ControllerError(f"path is a symlink: {canonical!r}")
    if not stat.S_ISREG(st.st_mode):
        raise ControllerError(f"path is not a regular file: {canonical!r}")
    if st.st_nlink != 1:
        raise ControllerError(f"path has {st.st_nlink} links, expected 1: {canonical!r}")
    return canonical


def validate_owner_mode(path: str, expected_uid: int, expected_gid: int, expected_mode: int) -> str:
    """Validate file owner, group, and mode."""
    st = os.stat(path, follow_symlinks=False)
    if st.st_uid != expected_uid:
        raise ControllerError(
            f"{path!r}: expected uid={expected_uid}, got uid={st.st_uid}"
        )
    if st.st_gid != expected_gid:
        raise ControllerError(
            f"{path!r}: expected gid={expected_gid}, got gid={st.st_gid}"
        )
    actual_mode = stat.S_IMODE(st.st_mode)
    if actual_mode != expected_mode:
        raise ControllerError(
            f"{path!r}: expected mode {expected_mode:04o}, got {actual_mode:04o}"
        )
    return path


# ---------------------------------------------------------------------------
# Canonical JSON and SHA helpers
# ---------------------------------------------------------------------------


def canonical_json(obj: Any) -> str:
    """Serialize to canonical JSON: sorted keys, no trailing newline, compact."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_hex(data: bytes | str) -> str:
    """Return SHA-256 hex digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    """Return SHA-256 hex digest of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# State root layout
# ---------------------------------------------------------------------------


def state_root(run_id: str) -> str:
    return os.path.join(_seams["state_root_base"], run_id)


def control_dir(run_id: str) -> str:
    return os.path.join(state_root(run_id), "control")


def ledger_path(run_id: str) -> str:
    return os.path.join(state_root(run_id), "ledger", "events.jsonl")


def phase_path(run_id: str) -> str:
    return os.path.join(control_dir(run_id), "phase.json")


def manifest_path(run_id: str) -> str:
    return os.path.join(control_dir(run_id), "manifest.json")


def manifest_sha_path(run_id: str) -> str:
    return os.path.join(control_dir(run_id), "manifest.sha256")


def lock_token_path(run_id: str) -> str:
    return os.path.join(control_dir(run_id), "production-lock.token")


def auth_path(run_id: str) -> str:
    return os.path.join(control_dir(run_id), "live-authorization.json")


def evidence_dir(run_id: str) -> str:
    return os.path.join(state_root(run_id), "evidence")


def backup_path(run_id: str) -> str:
    return os.path.join(state_root(run_id), "backup", "coord.sqlite3")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ControllerError(Exception):
    """Controlled failure that halts the state machine."""


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def _compute_record_sha(seq: int, phase: str, event: str, prev_sha: str, evidence: dict[str, Any] | None) -> str:
    """Compute the SHA-256 of a ledger record (before the record_sha256 field is set)."""
    record = {
        "seq": seq,
        "timestamp_utc": _seams["now_utc"]().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "phase": phase,
        "event": event,
        "prev_sha256": prev_sha,
        "evidence": evidence or {},
    }
    return sha256_hex(canonical_json(record))


def _append_ledger(run_id: str, phase: str, event: str, evidence: dict[str, Any] | None = None) -> str:
    """Append one record to the hash-chained ledger. Returns the record SHA-256."""
    lp = ledger_path(run_id)
    parent = os.path.dirname(lp)
    os.makedirs(parent, exist_ok=True)

    # Read last record to get seq and prev_sha
    prev_sha = "0000000000000000000000000000000000000000000000000000000000000000"
    seq = 1
    if os.path.exists(lp):
        with open(lp, "r") as fh:
            lines = fh.readlines()
        if lines:
            last = json.loads(lines[-1].rstrip("\n"))
            prev_sha = last.get("record_sha256", prev_sha)
            seq = last.get("seq", 0) + 1

    record_sha = _compute_record_sha(seq, phase, event, prev_sha, evidence)
    record = {
        "seq": seq,
        "timestamp_utc": _seams["now_utc"]().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "phase": phase,
        "event": event,
        "prev_sha256": prev_sha,
        "record_sha256": record_sha,
        "evidence": evidence or {},
    }
    line = canonical_json(record) + "\n"
    fd = os.open(lp, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    # fsync parent directory
    dfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return record_sha


def _read_ledger(run_id: str) -> list[dict[str, Any]]:
    """Read all ledger records. Returns empty list if ledger doesn't exist."""
    lp = ledger_path(run_id)
    if not os.path.exists(lp):
        return []
    records: list[dict[str, Any]] = []
    with open(lp, "r") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line:
                records.append(json.loads(line))
    return records


def _validate_ledger_chain(run_id: str) -> None:
    """Validate the full hash chain. Raises ControllerError on corruption."""
    records = _read_ledger(run_id)
    prev = "0000000000000000000000000000000000000000000000000000000000000000"
    for i, rec in enumerate(records):
        if rec.get("seq") != i + 1:
            raise ControllerError(f"ledger sequence gap at record {i + 1}, got seq={rec.get('seq')}")
        if rec.get("prev_sha256") != prev:
            raise ControllerError(
                f"ledger hash chain broken at record {i + 1}: "
                f"expected prev={prev}, got prev={rec.get('prev_sha256')}"
            )
        expected_sha = _compute_record_sha(
            rec["seq"], rec["phase"], rec["event"], rec["prev_sha256"], rec.get("evidence")
        )
        if rec.get("record_sha256") != expected_sha:
            raise ControllerError(
                f"ledger record SHA mismatch at record {rec['seq']}"
            )
        prev = rec["record_sha256"]


# ---------------------------------------------------------------------------
# Phase
# ---------------------------------------------------------------------------


def _current_phase(run_id: str) -> str | None:
    """Read the current phase. Returns None if no phase file exists."""
    pp = phase_path(run_id)
    if not os.path.exists(pp):
        return None
    with open(pp, "r") as fh:
        data = json.load(fh)
    return data.get("phase")


def _write_phase(run_id: str, phase: str, force: bool = False) -> None:
    """Atomically write phase file using temp+fsync+replace+dir-fsync."""
    pp = phase_path(run_id)
    parent = os.path.dirname(pp)
    os.makedirs(parent, exist_ok=True)

    current = _current_phase(run_id)
    if current is not None and not force:
        expected_idx = PHASE_INDEX.get(current, -1)
        new_idx = PHASE_INDEX.get(phase, -1)
        if new_idx <= expected_idx:
            raise ControllerError(
                f"phase regression: {current} -> {phase}"
            )

    content = canonical_json({
        "phase": phase,
        "timestamp_utc": _seams["now_utc"]().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    }) + "\n"

    # Write to temp file in same directory, then atomic rename
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=".phase-", suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp, 0o600)
    os.replace(tmp, pp)
    # fsync parent directory
    dfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def _transition_to(run_id: str, phase: str) -> None:
    """Commit one adjacent phase transition to ledger and phase authority."""
    current = _current_phase(run_id)
    if current is None:
        raise ControllerError("cannot transition without current phase")
    current_idx = PHASE_INDEX.get(current, -1)
    target_idx = PHASE_INDEX.get(phase, -1)
    if current_idx < 0 or target_idx != current_idx + 1:
        raise ControllerError(f"non-adjacent phase transition: {current} -> {phase}")
    _append_ledger(
        run_id,
        phase,
        "phase.transition",
        {"from": current, "to": phase},
    )
    _write_phase(run_id, phase)
    if not _phase_tail_agree(run_id):
        raise ControllerError("ledger/phase tail mismatch after transition")


def _phase_tail_agree(run_id: str) -> bool:
    """Verify ledger tail and phase file agree on current phase."""
    phase = _current_phase(run_id)
    records = _read_ledger(run_id)
    if not records:
        return phase is None
    tail_phase = records[-1].get("phase")
    return tail_phase == phase


# ---------------------------------------------------------------------------
# SQLite read-only evidence
# ---------------------------------------------------------------------------


def _open_evidence_db(db_path: str) -> sqlite3.Connection:
    """Open a read-only evidence connection with write-blocking authorizer."""
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA query_only = ON")

    def _authorizer(action, arg1, arg2, dbname, source):
        # SQLITE_READ = 20, SQLITE_SELECT = 21. The evidence layer also uses
        # exactly three read-only PRAGMAs; all write-capable PRAGMAs remain denied.
        if action in (20, 21):  # SQLITE_READ, SQLITE_SELECT
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and str(arg2).lower() == "count":
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_PRAGMA and arg1 in {
            "integrity_check",
            "user_version",
            "foreign_key_check",
        } and arg2 is None:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    conn.set_authorizer(_authorizer)
    conn.row_factory = sqlite3.Row
    return conn


def _evidence_query(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute an allowlisted read-only query. Returns list of dicts."""
    # Verify not in transaction after query
    rows = conn.execute(query, params).fetchall()
    if conn.in_transaction:
        conn.rollback()
        raise ControllerError("evidence connection left in transaction")
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# DB evidence queries (allowlisted, explicit columns only)
# ---------------------------------------------------------------------------


def _db_integrity_check(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return integrity check result. Must be 'ok'."""
    rows = _evidence_query(conn, "PRAGMA integrity_check")
    result = rows[0].get("integrity_check", "") if rows else ""
    return {"integrity": result, "ok": result == "ok"}


def _db_schema_version(conn: sqlite3.Connection) -> int:
    rows = _evidence_query(conn, "PRAGMA user_version")
    return rows[0].get("user_version", -1) if rows else -1


def _db_fk_check(conn: sqlite3.Connection) -> int:
    rows = _evidence_query(conn, "PRAGMA foreign_key_check")
    return len(rows)


def _db_due_active_leases(conn: sqlite3.Connection) -> int:
    rows = _evidence_query(
        conn,
        "SELECT COUNT(*) AS cnt FROM execution_attempt_leases "
        "WHERE status = 'active' AND expires_at <= ?",
        (_seams["now_utc"]().isoformat(),),
    )
    return rows[0]["cnt"] if rows else 0


# ---------------------------------------------------------------------------
# Command runner
# ---------------------------------------------------------------------------


ALLOWED_ENV_KEYS = frozenset({"PATH", "HOME", "MAC_DB", "LANG", "LC_ALL"})


def _run_command(
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: float = 30.0,
    output_cap: int = 1_048_576,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """Run a single command with shell=False, allowlisted env, bounded timeout and output."""
    filtered_env = {
        key: value for key, value in os.environ.items() if key in ALLOWED_ENV_KEYS
    }
    if env:
        for k, v in env.items():
            if k in ALLOWED_ENV_KEYS:
                filtered_env[k] = v

    try:
        result = subprocess.run(
            argv,
            env=filtered_env,
            capture_output=capture,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        raise ControllerError(f"command timed out after {timeout}s: {argv[:4]!r}")

    if capture:
        if result.stdout and len(result.stdout.encode("utf-8")) > output_cap:
            raise ControllerError(f"command stdout exceeded {output_cap} bytes")
        if result.stderr and len(result.stderr.encode("utf-8")) > output_cap:
            raise ControllerError(f"command stderr exceeded {output_cap} bytes")

    return result


def _coord_cli(*args: str, env_extra: dict[str, str] | None = None) -> dict[str, Any]:
    """Run a Coordinate CLI command and parse its JSON output."""
    cmd = [_seams["production_cli"], *args]
    env: dict[str, str] = {}
    if env_extra:
        env.update(env_extra)
    env.setdefault("MAC_DB", _seams["production_db"])
    runner = _seams.get("run_command") or _run_command
    result = runner(cmd, env=env, timeout=30.0, output_cap=1_048_576)
    if result.returncode != 0:
        raise ControllerError(
            f"Coordinate CLI failed (exit {result.returncode}): {result.stderr[:500]!r}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ControllerError(f"Coordinate CLI returned non-JSON: {exc}")
    if not isinstance(data, dict):
        raise ControllerError("Coordinate CLI returned non-dict JSON")
    return data


def _lock_status(expect_token: str | None = None) -> dict[str, Any]:
    override = _seams.get("lock_status")
    if override is not None:
        result = override(expect_token)
        if not isinstance(result, dict):
            raise ControllerError("lock status seam returned non-dict")
        return result
    argv = [_seams["lock_helper"], "status"]
    if expect_token is not None:
        argv.extend(["--expect-token", expect_token])
    runner = _seams.get("run_command") or _run_command
    result = runner(argv, env={}, timeout=15.0, output_cap=16_384)
    if result.returncode != 0:
        raise ControllerError(
            f"production lock status failed (exit {result.returncode}): "
            f"{result.stderr[:500]!r}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ControllerError(f"production lock status returned non-JSON: {exc}")
    if not isinstance(payload, dict):
        raise ControllerError("production lock status returned non-object")
    return payload


def _require_free_lock() -> dict[str, Any]:
    status = _lock_status()
    state = status.get("state")
    phase = status.get("phase")
    if state not in {"free", "absent"} or phase != "free":
        raise ControllerError(f"production mutation lock is not free: {status!r}")
    return status


# ---------------------------------------------------------------------------
# Controller manifest
# ---------------------------------------------------------------------------


def _build_controller_manifest(
    run_id: str,
    installed_hashes: dict[str, str],
    revisions: dict[str, str],
    coord_cli_identity: dict[str, Any],
    coord_db_identity: dict[str, Any],
    helper_allowlist: list[str],
    config_hashes: dict[str, str],
    reap_policy: tuple[str, str | None],
    unit_user: str,
    unit_group: str,
    launcher_files: dict[str, dict[str, Any]],
    backup_identity: dict[str, Any],
    canonical_projection_sha256: str,
) -> dict[str, Any]:
    """Build a canonical controller manifest."""
    unit_uid = int(_seams["resolve_user"](unit_user))
    unit_gid = int(_seams["resolve_group"](unit_group))
    return {
        "production_launcher_identity": {
            "cli_path": coord_cli_identity["path"],
            "cli_dev": coord_cli_identity["dev"],
            "cli_inode": coord_cli_identity["inode"],
            "cli_owner": coord_cli_identity["owner"],
            "cli_group": coord_cli_identity["group"],
            "cli_mode": coord_cli_identity["mode"],
            "db_path": coord_db_identity["path"],
            "db_dev": coord_db_identity["dev"],
            "db_inode": coord_db_identity["inode"],
            "db_owner": coord_db_identity["owner"],
            "db_group": coord_db_identity["group"],
            "db_mode": coord_db_identity["mode"],
            "python_path": launcher_files["python"]["path"],
            "python_sha256": launcher_files["python"]["sha256"],
            "python_dev": launcher_files["python"]["dev"],
            "python_inode": launcher_files["python"]["inode"],
            "python_owner": launcher_files["python"]["owner"],
            "python_group": launcher_files["python"]["group"],
            "python_mode": launcher_files["python"]["mode"],
            "helper_path": launcher_files["helper"]["path"],
            "helper_sha256": launcher_files["helper"]["sha256"],
            "fixture_bin_path": launcher_files["fixture_bin"]["path"],
            "fixture_bin_sha256": launcher_files["fixture_bin"]["sha256"],
            "agent_template_path": launcher_files["agent_template"]["path"],
            "agent_template_sha256": launcher_files["agent_template"]["sha256"],
            "config_dir": os.path.realpath(_seams["config_dir"]),
            "lock_helper_path": os.path.realpath(_seams["lock_helper"]),
            "files": {name: dict(identity) for name, identity in launcher_files.items()},
            "cli_file": dict(coord_cli_identity),
            "db_file": dict(coord_db_identity),
        },
        "run_id": run_id,
        "state_root": state_root(run_id),
        "unit_user": unit_user,
        "unit_group": unit_group,
        "unit_uid": unit_uid,
        "unit_gid": unit_gid,
        "installed_revisions": dict(revisions),
        "installed_hashes": dict(installed_hashes),
        "config_hashes": dict(config_hashes),
        "helper_allowlist": list(helper_allowlist),
        "reap_policy": {"mode": reap_policy[0], "reason": reap_policy[1]},
        "budgets": dict(AUTH_EXACT_BUDGETS),
        "workspace_id": "p9-3c1-production",
        "host_id": "VM-0-15-ubuntu",
        "backup_identity": dict(backup_identity),
        "canonical_projection_sha256": canonical_projection_sha256,
        "prepared_at_utc": _seams["now_utc"]().isoformat().replace("+00:00", "Z"),
        "p3_authorization_digest": None,  # Absent in P2
    }


def _write_manifest(run_id: str, manifest: dict[str, Any]) -> str:
    """Write manifest.json and manifest.sha256, return SHA-256."""
    mp = manifest_path(run_id)
    msp = manifest_sha_path(run_id)
    parent = os.path.dirname(mp)
    os.makedirs(parent, exist_ok=True)

    content = canonical_json(manifest) + "\n"
    sha = sha256_hex(content)

    # Write manifest atomically
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=".manifest-", suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp, 0o600)
    os.replace(tmp, mp)

    # Write SHA
    fd2, tmp2 = tempfile.mkstemp(dir=parent, prefix=".manifest-sha-", suffix=".tmp")
    try:
        os.write(fd2, f"{sha}\n".encode("utf-8"))
        os.fsync(fd2)
    finally:
        os.close(fd2)
    os.chmod(tmp2, 0o600)
    os.replace(tmp2, msp)

    dfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return sha


# ---------------------------------------------------------------------------
# Prepare
# ---------------------------------------------------------------------------


def cmd_prepare(run_id: str, unit_user: str, unit_group: str) -> dict[str, Any]:
    """Create a fresh sealed run directory with immutable expected hashes."""
    _validate_prepare_args(run_id, unit_user, unit_group)

    root = state_root(run_id)

    # Ensure fresh — no existing path
    if os.path.exists(root):
        raise ControllerError(f"run root already exists: {root}")

    lock_before = _require_free_lock()
    hash_reader = _seams.get("collect_installed_hashes") or _collect_installed_hashes
    revision_reader = _seams.get("collect_revisions") or _collect_revisions
    installed_hashes = hash_reader()
    revisions = revision_reader()
    config_contract = _validate_config_contract(
        _seams["config_dir"], _seams["helper_path"]
    )
    installed_hashes_confirm = hash_reader()
    revisions_confirm = revision_reader()
    lock_after = _require_free_lock()
    if installed_hashes_confirm != installed_hashes:
        raise ControllerError("installed source hashes changed during prepare gate")
    if revisions_confirm != revisions:
        raise ControllerError("deployed revisions changed during prepare gate")
    if lock_after != lock_before:
        raise ControllerError("production mutation lock changed during prepare gate")

    try:
        # Create directory structure
        _create_run_dirs(run_id)

        # Collect Coordinate CLI/DB identity
        coord_cli_identity = _file_identity(_seams["production_cli"])
        coord_db_identity = _file_identity(_seams["production_db"])
        launcher_reader = _seams.get("collect_launcher_files") or _collect_launcher_files
        launcher_files = launcher_reader()

        # Open read-only DB evidence
        conn = _open_evidence_db(_seams["production_db"])
        try:
            integrity = _db_integrity_check(conn)
            schema_ver = _db_schema_version(conn)
            fk_violations = _db_fk_check(conn)
            due_leases = _db_due_active_leases(conn)
        finally:
            conn.close()

        if not integrity["ok"]:
            raise ControllerError(f"DB integrity check failed: {integrity['integrity']}")
        if schema_ver != EXPECTED_SCHEMA:
            raise ControllerError(f"DB schema {schema_ver}, expected {EXPECTED_SCHEMA}")
        if fk_violations != 0:
            raise ControllerError(f"DB has {fk_violations} FK violations")
        if due_leases != 0:
            raise ControllerError(f"DB has {due_leases} due active lease(s)")
        canonical_projection = _canonical_projection_snapshot()

        # Online read-only backup
        _create_backup(run_id)
        backup_identity = _file_identity(backup_path(run_id))
        if backup_identity["mode"] != 0o600:
            raise ControllerError("backup mode is not 0600")

        # Controller manifest
        manifest = _build_controller_manifest(
            run_id=run_id,
            installed_hashes=installed_hashes,
            revisions=revisions,
            coord_cli_identity=coord_cli_identity,
            coord_db_identity=coord_db_identity,
            helper_allowlist=config_contract["agent_ids"],
            config_hashes=config_contract["config_hashes"],
            reap_policy=("none", f"p9-3c1-{run_id}"),
            unit_user=unit_user,
            unit_group=unit_group,
            launcher_files=launcher_files,
            backup_identity=backup_identity,
            canonical_projection_sha256=canonical_projection["sha256"],
        )
        _write_manifest(run_id, manifest)

        # Baseline evidence
        baseline = {
            "db_integrity": integrity,
            "schema_version": schema_ver,
            "fk_violations": fk_violations,
            "due_active_leases": due_leases,
            "installed_hashes": installed_hashes,
            "revisions": revisions,
            "canonical_projection_sha256": canonical_projection["sha256"],
        }
        _write_evidence(run_id, "baseline.json", baseline)

        # Seal phase
        _write_phase(run_id, "sealed")
        _append_ledger(run_id, "sealed", "prepare.completed", {"manifest_sha": sha256_file(manifest_path(run_id))})

        return {"status": "sealed", "run_id": run_id, "state_root": root}

    except Exception:
        # Forensic marker on failure
        try:
            _write_forensic_failure(run_id, "prepare-failed")
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


def _read_manifest(run_id: str) -> tuple[dict[str, Any], str]:
    """Read and validate the sealed canonical manifest and detached digest."""
    manifest_file = validate_single_link(manifest_path(run_id))
    manifest_sha_file = validate_single_link(manifest_sha_path(run_id))
    expected_sha = Path(manifest_sha_file).read_text(encoding="utf-8").strip()
    if not AUTH_SHA_RE.fullmatch(expected_sha):
        raise ControllerError("manifest SHA authority is malformed")
    raw = Path(manifest_file).read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha:
        raise ControllerError(f"manifest SHA mismatch: {actual_sha} != {expected_sha}")
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ControllerError(f"manifest is not canonical JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ControllerError("manifest must be a JSON object")
    if raw != (canonical_json(manifest) + "\n").encode("utf-8"):
        raise ControllerError("manifest bytes are not canonical JSON")
    if manifest.get("run_id") != run_id or manifest.get("state_root") != state_root(run_id):
        raise ControllerError("manifest run/state authority mismatch")
    return manifest, actual_sha


def _preflight(run_id: str, *, owned_token: str | None) -> dict[str, Any]:
    """Shared read-only gate for standalone and held-lock run preflight."""
    validate_run_id(run_id)

    phase = _current_phase(run_id)
    if phase != "sealed":
        raise ControllerError(f"preflight requires phase=sealed, got {phase}")

    _validate_ledger_chain(run_id)
    if not _phase_tail_agree(run_id):
        raise ControllerError("ledger/phase tail mismatch")

    manifest, actual_sha = _read_manifest(run_id)

    if owned_token is None:
        _require_free_lock()
    else:
        _require_owned_lock(run_id, owned_token)

    hash_reader = _seams.get("collect_installed_hashes") or _collect_installed_hashes
    revision_reader = _seams.get("collect_revisions") or _collect_revisions
    if hash_reader() != manifest.get("installed_hashes"):
        raise ControllerError("installed source hash drift")
    if revision_reader() != manifest.get("installed_revisions"):
        raise ControllerError("deployed revision drift")
    launcher_reader = _seams.get("collect_launcher_files") or _collect_launcher_files
    if launcher_reader() != manifest.get("production_launcher_identity", {}).get("files"):
        raise ControllerError("production launcher file identity drift")
    launcher = manifest.get("production_launcher_identity", {})
    if _file_identity(_seams["production_cli"]) != launcher.get("cli_file"):
        raise ControllerError("Coordinate CLI identity drift")
    if _file_identity(_seams["production_db"]) != launcher.get("db_file"):
        raise ControllerError("Coordinate DB identity drift")
    config_contract = _validate_config_contract(_seams["config_dir"], _seams["helper_path"])
    if config_contract["config_hashes"] != manifest.get("config_hashes"):
        raise ControllerError("sealed config hash drift")
    if config_contract["agent_ids"] != manifest.get("helper_allowlist"):
        raise ControllerError("sealed helper allowlist drift")

    # Read-only DB evidence
    conn = _open_evidence_db(_seams["production_db"])
    try:
        integrity = _db_integrity_check(conn)
        schema_ver = _db_schema_version(conn)
        fk_violations = _db_fk_check(conn)
        due_leases = _db_due_active_leases(conn)
    finally:
        conn.close()

    if not integrity["ok"]:
        raise ControllerError(f"DB integrity lost: {integrity['integrity']}")
    if schema_ver != EXPECTED_SCHEMA:
        raise ControllerError(f"DB schema changed: {schema_ver}")
    if fk_violations != 0:
        raise ControllerError(f"DB foreign-key violations changed: {fk_violations}")
    if due_leases != 0:
        raise ControllerError(f"DB has {due_leases} due active lease(s)")
    projection = _canonical_projection_snapshot()
    if projection["sha256"] != manifest.get("canonical_projection_sha256"):
        raise ControllerError("canonical projection drift")

    # Backup evidence
    bp = backup_path(run_id)
    validate_single_link(bp)
    _seams["validate_owner_mode"](bp, 0, 0, 0o600)
    if _file_identity(bp) != manifest.get("backup_identity"):
        raise ControllerError("backup identity/hash drift")

    evidence = {
        "status": "preflight_passed",
        "run_id": run_id,
        "phase": phase,
        "manifest_sha": actual_sha,
        "db_integrity": integrity,
        "schema_version": schema_ver,
        "fk_violations": fk_violations,
        "due_active_leases": due_leases,
        "canonical_projection_sha256": projection["sha256"],
        "backup_sha": sha256_file(bp),
        "installed_hashes": manifest.get("installed_hashes", {}),
        "installed_revisions": manifest.get("installed_revisions", {}),
        "lock_mode": "owned" if owned_token is not None else "free",
    }
    return evidence


def cmd_preflight(run_id: str) -> dict[str, Any]:
    """Read-only standalone preflight; the global mutation lock must be free."""
    return _preflight(run_id, owned_token=None)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def cmd_status(run_id: str) -> dict[str, Any]:
    """Read-only status summary."""
    validate_run_id(run_id)

    phase = _current_phase(run_id)
    if phase is None:
        raise ControllerError(f"run {run_id} not prepared (no phase file)")

    _validate_ledger_chain(run_id)
    records = _read_ledger(run_id)
    if not _phase_tail_agree(run_id):
        raise ControllerError("ledger/phase tail mismatch")
    tail = records[-1] if records else None
    lock = _lock_status()

    return {
        "run_id": run_id,
        "phase": phase,
        "ledger_records": len(records),
        "tail_event": tail["event"] if tail else None,
        "tail_sha": tail["record_sha256"] if tail else None,
        "lock": lock,
        "token_file_present": os.path.exists(lock_token_path(run_id)),
    }


# ---------------------------------------------------------------------------
# Run (P3 only — gated by authorization file)
# ---------------------------------------------------------------------------


def _parse_authorization_expiry(value: Any) -> datetime.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ControllerError("authorization expiry_utc must be canonical UTC Z")
    try:
        parsed = datetime.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ControllerError("authorization expiry_utc is invalid") from exc
    if parsed.tzinfo != datetime.timezone.utc or parsed.isoformat().replace("+00:00", "Z") != value:
        raise ControllerError("authorization expiry_utc is not canonical")
    return parsed


def _validate_authorization(
    run_id: str, authorization_file: str, authorization_sha256: str
) -> dict[str, Any]:
    """Validate the external P3 artifact completely before any live mutation."""
    if not isinstance(authorization_sha256, str) or not AUTH_SHA_RE.fullmatch(
        authorization_sha256
    ):
        raise ControllerError("authorization SHA must be 64-char lowercase hex")
    auth_canonical = validate_single_link(authorization_file)
    if os.path.realpath(auth_canonical) == os.path.realpath(auth_path(run_id)):
        raise ControllerError("authorization source cannot be live-authorization destination")
    _seams["validate_owner_mode"](auth_canonical, 0, 0, 0o600)
    raw = Path(auth_canonical).read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual_sha, authorization_sha256):
        raise ControllerError(
            f"authorization SHA mismatch: {actual_sha} != {authorization_sha256}"
        )
    try:
        auth = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ControllerError(f"authorization is not JSON: {exc}") from exc
    if not isinstance(auth, dict) or set(auth) != AUTH_EXACT_KEYS:
        raise ControllerError("authorization keys mismatch")
    if raw != (canonical_json(auth) + "\n").encode("utf-8"):
        raise ControllerError("authorization bytes are not canonical JSON")
    if auth.get("contract_version") != AUTH_CONTRACT_VERSION:
        raise ControllerError("authorization contract_version mismatch")
    if auth.get("run_id") != run_id:
        raise ControllerError("authorization run_id mismatch")

    manifest, manifest_sha = _read_manifest(run_id)
    if auth.get("manifest_sha256") != manifest_sha:
        raise ControllerError("authorization manifest SHA mismatch")
    if auth.get("installed_revisions") != manifest.get("installed_revisions"):
        raise ControllerError("authorization installed revisions mismatch")
    if auth.get("installed_hashes") != manifest.get("installed_hashes"):
        raise ControllerError("authorization installed hashes mismatch")
    hash_reader = _seams.get("collect_installed_hashes") or _collect_installed_hashes
    revision_reader = _seams.get("collect_revisions") or _collect_revisions
    if auth["installed_hashes"] != hash_reader():
        raise ControllerError("authorization live installed hashes mismatch")
    if auth["installed_revisions"] != revision_reader():
        raise ControllerError("authorization live installed revisions mismatch")

    for key in ("p3_bootstrap_sha256", "review_artifact_sha256"):
        if not isinstance(auth.get(key), str) or not AUTH_SHA_RE.fullmatch(auth[key]):
            raise ControllerError(f"authorization {key} is malformed")
    if auth.get("reviewer_verdict") != "APPROVE":
        raise ControllerError("authorization reviewer verdict is not APPROVE")
    if auth.get("budgets") != AUTH_EXACT_BUDGETS:
        raise ControllerError("authorization budgets mismatch")
    nonce = auth.get("nonce")
    if not isinstance(nonce, str) or not AUTH_NONCE_RE.fullmatch(nonce):
        raise ControllerError("authorization nonce is malformed")
    if _parse_authorization_expiry(auth.get("expiry_utc")) <= _seams["now_utc"]():
        raise ControllerError("authorization expired")
    return auth


def cmd_run(run_id: str, authorization_file: str, authorization_sha256: str) -> dict[str, Any]:
    """Execute the full state machine. Requires P3 authorization artifact."""
    validate_run_id(run_id)
    if _current_phase(run_id) != "sealed":
        raise ControllerError("run requires phase=sealed")
    if os.path.lexists(auth_path(run_id)):
        raise ControllerError("live authorization already exists; nonce may have been used")
    auth = _validate_authorization(run_id, authorization_file, authorization_sha256)
    _atomic_copy(authorization_file, auth_path(run_id), mode=0o600)
    _seams["validate_owner_mode"](auth_path(run_id), 0, 0, 0o600)
    if sha256_file(auth_path(run_id)) != authorization_sha256:
        raise ControllerError("live authorization copy digest mismatch")

    token = _acquire_lock(run_id)
    try:
        _preflight(run_id, owned_token=token)
        _transition_to(run_id, "preflight-ok")
        return _execute_state_machine(run_id, auth)
    except Exception:
        current = _current_phase(run_id)
        if current in {"sealed", "preflight-ok", "lock-held"}:
            _write_evidence(
                run_id,
                "preactivation-failed.json",
                {"phase": current, "production_mutation_started": False},
            )
            _release_lock(run_id)
        raise


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def cmd_cleanup(run_id: str) -> dict[str, Any]:
    """Resume cleanup from ledgered phase. Only valid from workspace-ready+."""
    validate_run_id(run_id)

    phase = _current_phase(run_id)
    if phase is None:
        raise ControllerError(f"run {run_id} not prepared")
    if phase == "sealed":
        raise ControllerError("cannot cleanup a sealed inert run")
    if phase == "done":
        raise ControllerError("run already done; cannot cleanup")

    workspace_idx = PHASE_INDEX.get("workspace-ready", -1)
    current_idx = PHASE_INDEX.get(phase, -1)
    if current_idx < workspace_idx:
        raise ControllerError(f"cleanup requires at least workspace-ready, got {phase}")

    # Acquire lock and resume cleanup
    _acquire_lock(run_id)
    return _execute_cleanup_suffix(run_id)


def _require_live_authorization(run_id: str, expected: dict[str, Any]) -> None:
    """Revalidate the copied P3 artifact before every forward phase mutation."""
    path = validate_single_link(auth_path(run_id))
    _seams["validate_owner_mode"](path, 0, 0, 0o600)
    raw = Path(path).read_bytes()
    if raw != (canonical_json(expected) + "\n").encode("utf-8"):
        raise ControllerError("live authorization bytes changed during run")
    if expected.get("run_id") != run_id or expected.get("budgets") != AUTH_EXACT_BUDGETS:
        raise ControllerError("live authorization authority mismatch during run")
    if _parse_authorization_expiry(expected.get("expiry_utc")) <= _seams["now_utc"]():
        raise ControllerError("live authorization expired during run")


# ---------------------------------------------------------------------------
# State machine — complete bounded-sequence controller.
# ---------------------------------------------------------------------------

_CMD_REGISTRY: dict[str, Any] = {}


def _register_phase(phase: str, prev_phase: str):
    """Decorator: register a phase transition function."""
    def decorator(fn):
        if prev_phase in _CMD_REGISTRY:
            raise RuntimeError(f"duplicate phase handler: {prev_phase}")
        _CMD_REGISTRY[prev_phase] = (phase, fn)
        return fn
    return decorator


def _run_coord(*args: str) -> dict[str, Any]:
    """Run a Coordinate CLI command via _coord_cli, verify result is non-error."""
    result = _coord_cli(*args)
    if result.get("error"):
        raise ControllerError(f"Coordinate command error: {result['error']}")
    return result


def _result_object(payload: dict[str, Any], label: str) -> dict[str, Any]:
    return _require_object(payload.get("result"), label)


def _helper_cli(run_id: str, command: str, *args: str) -> dict[str, Any]:
    """Invoke one exact production helper command and require one JSON object."""
    if command not in {
        "production-render", "production-preflight", "production-start",
        "production-status", "production-stop", "production-cleanup",
    }:
        raise ControllerError(f"unapproved production helper command: {command}")
    manifest, manifest_sha = _read_manifest(run_id)
    argv = [
        _seams["helper_path"], command,
        "--state-root", state_root(run_id),
        "--run-id", run_id,
        "--controller-manifest", manifest_path(run_id),
        "--controller-manifest-sha256", manifest_sha,
    ]
    if command not in {"production-preflight", "production-status"}:
        argv.extend(["--lock-token-file", lock_token_path(run_id)])
    argv.extend(args)
    runner = _seams.get("run_command") or _run_command
    result = runner(argv, env={}, timeout=45.0, output_cap=1_048_576)
    if result.returncode != 0:
        raise ControllerError(
            f"production helper {command} failed (exit {result.returncode}): "
            f"{result.stderr[:500]!r}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ControllerError(f"production helper {command} returned non-JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ControllerError(f"production helper {command} returned non-object")
    if manifest.get("run_id") != run_id:
        raise ControllerError("controller manifest run authority changed during helper call")
    return payload


def _expect_coord_rejection(*args: str) -> str:
    """Require one Coordinate command to fail; return a bounded error digest."""
    try:
        _coord_cli(*args)
    except ControllerError as exc:
        return sha256_hex(str(exc)[:500])
    raise ControllerError(f"expected Coordinate rejection but command succeeded: {args[:4]!r}")


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ControllerError(f"Coordinate {label} is not an object")
    return value


def _config_asset(filename: str) -> str:
    allowed = {
        "executor.v1-disabled.toml",
        "executor.v2-enabled.toml",
        "executor.v3-disabled.toml",
        "executor.v4-empty.toml",
        "capacity.v1.toml",
        "capacity.v2-empty.toml",
    }
    if filename not in allowed:
        raise ControllerError(f"unapproved config asset: {filename}")
    path = os.path.join(_seams["config_dir"], filename)
    return validate_single_link(path)


def _sync_executor(filename: str, version: int, binding_enabled: bool | None) -> None:
    result = _run_coord("runtime", "executor", "sync", "--source", _config_asset(filename))
    if result.get("source_id") != "p9-3c1-fixture-executors" or result.get("source_version") != version:
        raise ControllerError("executor sync response authority mismatch")
    readback = _run_coord("runtime", "executor", "list")
    sources = readback.get("sources")
    definitions = readback.get("definitions")
    bindings = readback.get("bindings")
    if not all(isinstance(value, list) for value in (sources, definitions, bindings)):
        raise ControllerError("executor readback envelope mismatch")
    own_sources = [row for row in sources if row.get("source_id") == "p9-3c1-fixture-executors"]
    own_defs = [row for row in definitions if row.get("source_id") == "p9-3c1-fixture-executors"]
    own_bindings = [row for row in bindings if row.get("source_id") == "p9-3c1-fixture-executors"]
    if len(own_sources) != 1 or own_sources[0].get("source_version") != version:
        raise ControllerError("executor source readback mismatch")
    if version == 4:
        if own_defs or own_bindings:
            raise ControllerError("executor terminal catalog is not empty")
        return
    if len(own_defs) != 1 or own_defs[0].get("id") != "p9-3c1-local-fixture":
        raise ControllerError("executor definition readback mismatch")
    if len(own_bindings) != 2 or {
        row.get("agent_id") for row in own_bindings
    } != {"p9-3c-fixture-e1", "p9-3c-fixture-e2"}:
        raise ControllerError("executor binding readback mismatch")
    if any(bool(row.get("enabled")) is not binding_enabled for row in own_bindings):
        raise ControllerError("executor binding enabled readback mismatch")


def _sync_capacity(filename: str, version: int, active: bool) -> None:
    result = _run_coord("runtime", "capacity", "sync", "--source", _config_asset(filename))
    if result.get("source_id") != "p9-3c1-fixture-capacity" or result.get("source_version") != version:
        raise ControllerError("capacity sync response authority mismatch")
    readback = _run_coord("runtime", "capacity", "list")
    sources = readback.get("sources")
    policies = readback.get("policies")
    if not isinstance(sources, list) or not isinstance(policies, list):
        raise ControllerError("capacity readback envelope mismatch")
    own_sources = [row for row in sources if row.get("source_id") == "p9-3c1-fixture-capacity"]
    own_policies = [row for row in policies if row.get("source_id") == "p9-3c1-fixture-capacity"]
    if len(own_sources) != 1 or own_sources[0].get("source_version") != version:
        raise ControllerError("capacity source readback mismatch")
    if active:
        if len(own_policies) != 2 or any(row.get("max_concurrent_jobs") != 1 for row in own_policies):
            raise ControllerError("capacity active policy readback mismatch")
    elif own_policies:
        raise ControllerError("capacity terminal catalog is not empty")


def _execute_state_machine(run_id: str, auth: dict[str, Any]) -> dict[str, Any]:
    """Execute forward phases from current phase to done."""
    phase = _current_phase(run_id)
    if phase is None:
        raise ControllerError("no phase file")

    try:
        while phase != "done":
            entry = _CMD_REGISTRY.get(phase)
            if entry is None:
                raise ControllerError(f"unknown or terminal phase: {phase}")
            next_phase, handler = entry
            actual = _current_phase(run_id)
            if actual != phase:
                raise ControllerError(f"phase mismatch: expected {phase}, got {actual}")
            _validate_ledger_chain(run_id)
            if not _phase_tail_agree(run_id):
                raise ControllerError("ledger/phase tail mismatch before phase mutation")
            _require_owned_lock(run_id)
            _require_live_authorization(run_id, auth)
            handler(run_id, auth)
            phase = _current_phase(run_id)
            if phase is None:
                raise ControllerError("phase disappeared mid-machine")
            if phase != next_phase:
                raise ControllerError(
                    f"handler for {actual} advanced to {phase}, expected {next_phase}"
                )
    except Exception:
        current = _current_phase(run_id)
        if current not in (None, "sealed", "preflight-ok", "lock-held"):
            _append_ledger(run_id, current or "unknown", "machine.failure")
            if PHASE_INDEX.get(current or "", -1) >= PHASE_INDEX["baseline-captured"]:
                _execute_cleanup_suffix(run_id)
        raise

    return {"status": "done", "run_id": run_id}


def _execute_cleanup_suffix(run_id: str) -> dict[str, Any]:
    """Execute the fixed production cleanup suffix from authoritative phase."""
    phase = _current_phase(run_id)
    if phase is None:
        raise ControllerError("no phase file for cleanup")
    if phase in ("sealed", "preflight-ok", "lock-held"):
        raise ControllerError(f"cleanup not allowed from phase {phase!r}")
    if phase == "done":
        raise ControllerError("cleanup not allowed: run already done")

    try:
        current_idx = PHASE_INDEX[phase]
    except KeyError:
        raise ControllerError(f"unknown phase {phase!r}")

    internal_cleanup_idx = PHASE_INDEX["baseline-captured"]
    if current_idx < internal_cleanup_idx:
        raise ControllerError(f"cleanup not allowed from phase {phase!r}")

    _require_owned_lock(run_id)
    _append_ledger(run_id, phase, "cleanup.initiated", evidence={"from_phase": phase})

    helper_ledger = os.path.join(state_root(run_id), "runtime", "unit", "helper-events.log")
    recorded_agents: list[str] = []
    if os.path.exists(helper_ledger):
        validate_single_link(helper_ledger)
        raw = Path(helper_ledger).read_text(encoding="utf-8")
        for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
            unit_prefix = f"unit {agent}-{run_id}.service "
            if any(line.startswith(unit_prefix) for line in raw.splitlines()):
                recorded_agents.append(agent)
        for agent in recorded_agents:
            stopped = _helper_cli(run_id, "production-stop", "--agent-id", agent)
            if stopped.get("status") != "stopped" or stopped.get("termination") != "graceful":
                raise ControllerError(f"cleanup stop response mismatch for {agent}")
        for agent in recorded_agents:
            cleaned = _helper_cli(run_id, "production-cleanup", "--agent-id", agent)
            if cleaned.get("status") != "cleaned" or cleaned.get("agent_id") != agent:
                raise ControllerError(f"cleanup helper response mismatch for {agent}")

    submitted_jobs: dict[str, str] = {}
    for record in _read_ledger(run_id):
        event = record.get("event")
        if isinstance(event, str) and re.fullmatch(r"matrix\.j[1-5]\.submitted", event):
            label = event.split(".")[1].upper()
            job_id = (record.get("evidence") or {}).get("job_id")
            if not isinstance(job_id, str) or label in submitted_jobs:
                raise ControllerError("cleanup submitted-job ledger authority is invalid")
            submitted_jobs[label] = job_id
    if submitted_jobs:
        runtime = _matrix_snapshot(submitted_jobs)
        nonterminal = {
            label: runtime.get("jobs", {}).get(label, {}).get("status")
            for label in submitted_jobs
            if runtime.get("jobs", {}).get(label, {}).get("status") not in {"done", "failed"}
        }
        active_leases = [
            row.get("lease_id")
            for label in submitted_jobs
            for row in runtime.get("leases", {}).get(label, [])
            if row.get("status") == "active"
        ]
        if nonterminal or active_leases:
            _write_evidence(
                run_id,
                "cleanup-blocked.json",
                {"nonterminal_jobs": nonterminal, "active_lease_ids": active_leases},
            )
            raise ControllerError("cleanup halted with exact nonterminal job or active lease authority")

    # The current phase is the last committed transition; the next handler may
    # have completed its mutation before failing its readback. Cleanup therefore
    # begins one boundary earlier than the corresponding committed phase.
    if current_idx >= PHASE_INDEX["agents-online"]:
        _sync_executor("executor.v3-disabled.toml", 3, False)
        _sync_capacity("capacity.v2-empty.toml", 2, False)
        _sync_executor("executor.v4-empty.toml", 4, None)
    if current_idx >= PHASE_INDEX["workspace-ready"]:
        for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
            result = _result_object(
                _run_coord(
                    "runtime", "agent", "deactivate", "--agent-id", agent,
                    "--host-id", "VM-0-15-ubuntu", "--reason", "p9-3c1-cleanup",
                    "--actor", "p9-3c1-controller",
                ),
                "cleanup agent deactivate",
            )
            if result.get("blocked") is not False or result.get("deactivated") is not True:
                raise ControllerError(f"cleanup agent deactivate blocked for {agent}")

    projection = _canonical_projection_snapshot()
    manifest, _ = _read_manifest(run_id)
    if projection["sha256"] != manifest.get("canonical_projection_sha256"):
        raise ControllerError("cleanup canonical projection drift")
    conn = _open_evidence_db(_seams["production_db"])
    try:
        integrity = _db_integrity_check(conn)
        schema = _db_schema_version(conn)
        fk = _db_fk_check(conn)
    finally:
        conn.close()
    if not integrity["ok"] or schema != EXPECTED_SCHEMA or fk != 0:
        raise ControllerError("cleanup DB health gate failed")
    final = {
        "from_phase": phase,
        "recorded_agents": recorded_agents,
        "canonical_projection_sha256": projection["sha256"],
        "db": {"integrity": integrity["integrity"], "schema": schema, "fk_violations": fk},
    }
    _write_evidence(run_id, "cleanup.json", final)
    _append_ledger(run_id, "done", "cleanup.completed", evidence={"evidence_sha256": sha256_hex(canonical_json(final))})
    _write_phase(run_id, "done")
    _release_lock(run_id)
    return {"status": "cleanup_completed", "run_id": run_id, "from_phase": phase}


@_register_phase("lock-held", "preflight-ok")
def _phase_lock_held(run_id: str, _auth: dict[str, Any]) -> None:
    """Revalidate the once-acquired P0 token and record lock-held."""
    _require_owned_lock(run_id)
    _transition_to(run_id, "lock-held")


@_register_phase("baseline-captured", "lock-held")
def _phase_baseline_captured(run_id: str, _auth: dict[str, Any]) -> None:
    """Capture baseline evidence from read-only DB, then advance."""
    conn = _open_evidence_db(_seams["production_db"])
    try:
        integrity = _db_integrity_check(conn)
        due = _db_due_active_leases(conn)
    finally:
        conn.close()
    if not integrity["ok"]:
        raise ControllerError(f"DB integrity failed at baseline: {integrity['integrity']}")
    _write_evidence(run_id, "baseline.json", {
        "integrity": integrity,
        "due_active_leases": due,
        "captured_at": _seams["now_utc"]().isoformat(),
    })
    _transition_to(run_id, "baseline-captured")


@_register_phase("workspace-ready", "baseline-captured")
def _phase_workspace_ready(run_id: str, _auth: dict[str, Any]) -> None:
    """Create production workspace and host profile."""
    root = state_root(run_id)
    workspace_path = os.path.join(root, "runtime", "work")
    harness_root = os.path.join(root, "runtime")
    created = _run_coord(
        "workspace", "add", "p9-3c1-production", "--path", workspace_path,
        "--harness-root", harness_root, "--default-bus", "", "--default-destination", "",
    )
    workspace = _require_object(created.get("workspace"), "workspace add result")
    if workspace.get("id") != "p9-3c1-production" or workspace.get("path") != workspace_path:
        raise ControllerError("workspace add readback mismatch")
    profile_result = _run_coord(
        "workspace", "host-profile", "set", "p9-3c1-production",
        "--host-id", "VM-0-15-ubuntu", "--workspace-path", workspace_path,
        "--harness-root", harness_root, "--coordinator-cli-path", _seams["production_cli"],
        "--coordinator-db-path", _seams["production_db"],
    )
    profile = _require_object(profile_result.get("result"), "host profile result")
    if profile.get("workspace_id") != "p9-3c1-production" or profile.get("host_id") != "VM-0-15-ubuntu":
        raise ControllerError("host profile readback mismatch")
    _transition_to(run_id, "workspace-ready")


@_register_phase("agents-online", "workspace-ready")
def _phase_agents_online(run_id: str, _auth: dict[str, Any]) -> None:
    """Register and heartbeat E1 and E2 agents."""
    for agent_id in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
        registered = _run_coord(
            "runtime", "agent", "register", "--agent-id", agent_id,
            "--host-id", "VM-0-15-ubuntu", "--client-type", "agentd",
            "--capabilities-json", canonical_json({"p9-3c1-fixture": True}),
            "--actor", "p9-3c1-controller",
        )
        agent = _require_object(
            _require_object(registered.get("result"), "agent register result").get("agent"),
            "registered agent",
        )
        if agent.get("id") != agent_id or agent.get("host_id") != "VM-0-15-ubuntu":
            raise ControllerError("registered agent readback mismatch")
        heartbeat = _run_coord(
            "runtime", "agent", "heartbeat", "--agent-id", agent_id,
            "--host-id", "VM-0-15-ubuntu", "--actor", "p9-3c1-controller",
        )
        heartbeated = _require_object(
            _require_object(heartbeat.get("result"), "agent heartbeat result").get("agent"),
            "heartbeated agent",
        )
        if heartbeated.get("id") != agent_id or heartbeated.get("online_state") != "online":
            raise ControllerError("agent heartbeat readback mismatch")
    _transition_to(run_id, "agents-online")


@_register_phase("executor-v1-disabled", "agents-online")
def _phase_executor_v1_disabled(run_id: str, _auth: dict[str, Any]) -> None:
    """Sync executor v1 (disabled) and verify."""
    _sync_executor("executor.v1-disabled.toml", 1, False)
    _transition_to(run_id, "executor-v1-disabled")


@_register_phase("capacity-v1-active", "executor-v1-disabled")
def _phase_capacity_v1_active(run_id: str, _auth: dict[str, Any]) -> None:
    """Sync capacity v1 and verify."""
    _sync_capacity("capacity.v1.toml", 1, True)
    _transition_to(run_id, "capacity-v1-active")


@_register_phase("executor-v2-enabled", "capacity-v1-active")
def _phase_executor_v2_enabled(run_id: str, _auth: dict[str, Any]) -> None:
    """Sync executor v2 (enabled) and verify."""
    _sync_executor("executor.v2-enabled.toml", 2, True)
    _transition_to(run_id, "executor-v2-enabled")


@_register_phase("matrix-running", "executor-v2-enabled")
def _phase_matrix_running(run_id: str, _auth: dict[str, Any]) -> None:
    """Execute five-job matrix with lease management and renewals."""
    _run_five_job_matrix(run_id)
    _transition_to(run_id, "matrix-running")


@_register_phase("matrix-verified", "matrix-running")
def _phase_matrix_verified(run_id: str, _auth: dict[str, Any]) -> None:
    """Verify matrix results: all jobs completed, correct order, correct renewals."""
    _verify_job_matrix(run_id)
    _transition_to(run_id, "matrix-verified")


@_register_phase("intake-frozen", "matrix-verified")
def _phase_intake_frozen(run_id: str, _auth: dict[str, Any]) -> None:
    """Freeze intake: no new job claims accepted."""
    _append_ledger(run_id, "matrix-verified", "intake.frozen")
    _transition_to(run_id, "intake-frozen")


@_register_phase("units-quiescent", "intake-frozen")
def _phase_units_quiescent(run_id: str, _auth: dict[str, Any]) -> None:
    """Ensure all units are stopped/quiescent."""
    unit_evidence: dict[str, dict[str, str]] = {}
    for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
        stopped = _helper_cli(run_id, "production-stop", "--agent-id", agent)
        if stopped.get("status") != "stopped" or stopped.get("termination") != "graceful":
            raise ControllerError(f"unit stop response mismatch for {agent}")
        status = _helper_cli(run_id, "production-status", "--agent-id", agent)
        properties = _require_object(status.get("properties"), "production unit status properties")
        if properties.get("ActiveState") not in {"inactive", "failed"} or properties.get("MainPID") not in {"0", 0}:
            raise ControllerError(f"unit did not become quiescent: {agent}")
        unit_evidence[agent] = {
            "ActiveState": str(properties.get("ActiveState")),
            "MainPID": str(properties.get("MainPID")),
        }
    for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
        cleaned = _helper_cli(run_id, "production-cleanup", "--agent-id", agent)
        if cleaned.get("status") != "cleaned" or cleaned.get("agent_id") != agent:
            raise ControllerError(f"unit cleanup response mismatch for {agent}")
    unit_payload = {"agents": unit_evidence}
    _write_evidence(run_id, "units-quiescent.json", unit_payload)
    _append_ledger(
        run_id,
        "intake-frozen",
        "units.quiescent",
        evidence={"evidence_sha256": sha256_hex(canonical_json(unit_payload))},
    )
    _transition_to(run_id, "units-quiescent")


@_register_phase("executor-v3-disabled", "units-quiescent")
def _phase_executor_v3_disabled(run_id: str, _auth: dict[str, Any]) -> None:
    """Sync executor v3 (disabled) and verify."""
    _sync_executor("executor.v3-disabled.toml", 3, False)
    _transition_to(run_id, "executor-v3-disabled")


@_register_phase("capacity-v2-empty", "executor-v3-disabled")
def _phase_capacity_v2_empty(run_id: str, _auth: dict[str, Any]) -> None:
    """Sync capacity v2 (empty) and verify."""
    _sync_capacity("capacity.v2-empty.toml", 2, False)
    _transition_to(run_id, "capacity-v2-empty")


@_register_phase("executor-v4-empty", "capacity-v2-empty")
def _phase_executor_v4_empty(run_id: str, _auth: dict[str, Any]) -> None:
    """Sync executor v4 (empty) and verify."""
    _sync_executor("executor.v4-empty.toml", 4, None)
    _transition_to(run_id, "executor-v4-empty")


@_register_phase("agents-offline", "executor-v4-empty")
def _phase_agents_offline(run_id: str, _auth: dict[str, Any]) -> None:
    """Deactivate E1 and E2 agents."""
    for agent_id in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
        result = _run_coord("runtime", "agent", "deactivate", "--agent-id", agent_id,
                   "--host-id", "VM-0-15-ubuntu",
                   "--reason", "p9-3c1-run-complete", "--actor", "p9-3c1-controller")
        deactivated = _require_object(result.get("result"), "agent deactivate result")
        if deactivated.get("blocked") is not False or deactivated.get("deactivated") is not True:
            raise ControllerError("agent deactivate readback mismatch")
    _transition_to(run_id, "agents-offline")


def _canonical_projection_snapshot() -> dict[str, Any]:
    """Hash the explicit non-fixture schema-13 projection."""
    override = _seams.get("canonical_projection")
    if override is not None:
        result = override()
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("components"), dict)
            or not isinstance(result.get("sha256"), str)
            or not AUTH_SHA_RE.fullmatch(result["sha256"])
        ):
            raise ControllerError("canonical projection seam returned invalid authority")
        return result

    queries: tuple[tuple[str, str, tuple[Any, ...]], ...] = (
        ("executor_sources", "SELECT source_id, source_version, catalog_hash, source_path "
         "FROM executor_catalog_sources WHERE source_id != ? ORDER BY source_id",
         ("p9-3c1-fixture-executors",)),
        ("executor_definitions", "SELECT id, source_id, provider, adapter, capabilities_json, metadata_json "
         "FROM executor_definitions WHERE source_id != ? ORDER BY id",
         ("p9-3c1-fixture-executors",)),
        ("executor_bindings", "SELECT agent_id, source_id, executor_definition_id, runner_profile_id, enabled "
         "FROM executor_instance_bindings WHERE source_id != ? ORDER BY agent_id",
         ("p9-3c1-fixture-executors",)),
        ("capacity_sources", "SELECT source_id, source_version, catalog_hash, source_path "
         "FROM executor_capacity_sources WHERE source_id != ? ORDER BY source_id",
         ("p9-3c1-fixture-capacity",)),
        ("capacity_policies", "SELECT agent_id, source_id, source_version, catalog_hash, "
         "capacity_policy_id, max_concurrent_jobs FROM executor_capacity_policies "
         "WHERE source_id != ? ORDER BY agent_id",
         ("p9-3c1-fixture-capacity",)),
        ("roster_sources", "SELECT workspace_id, source_id, source_version, source_hash, source_path, synced_by "
         "FROM workspace_agent_registry_sources WHERE workspace_id = ? ORDER BY workspace_id",
         ("discord-nexus",)),
        ("roster_entries", "SELECT workspace_id, agent_name, entry_kind, discord_user_id, display_name, "
         "agent_type, actor, reason, expires_at FROM workspace_agent_registry_entries "
         "WHERE workspace_id = ? ORDER BY agent_name, entry_kind",
         ("discord-nexus",)),
        ("workspace", "SELECT id, name, path, harness_root, harnessctl_path, default_bus, "
         "default_destination, base_branch, branch_namespace, agent_registry_revision "
         "FROM workspaces WHERE id = ? ORDER BY id", ("discord-nexus",)),
        ("host_profiles", "SELECT workspace_id, host_id, workspace_path, harness_root, harnessctl_path, "
         "coordinator_cli_path, coordinator_db_path, shell, metadata_json "
         "FROM workspace_host_profiles WHERE workspace_id = ? ORDER BY host_id",
         ("discord-nexus",)),
    )
    conn = _open_evidence_db(_seams["production_db"])
    try:
        components = {name: _evidence_query(conn, sql, params) for name, sql, params in queries}
    finally:
        conn.close()
    return {"sha256": sha256_hex(canonical_json(components)), "components": components}


@_register_phase("canonical-compared", "agents-offline")
def _phase_canonical_compared(run_id: str, _auth: dict[str, Any]) -> None:
    """Compare canonical projection and verify it matches pre-run baseline."""
    proj = _canonical_projection_snapshot()
    manifest, _ = _read_manifest(run_id)
    baseline_hash = manifest.get("canonical_projection_sha256")
    if proj["sha256"] != baseline_hash:
        raise ControllerError(
            f"canonical projection drift: baseline={baseline_hash}, current={proj['sha256']}"
        )
    _write_evidence(run_id, "canonical.json", {
        "projection_hash": proj["sha256"],
        "compared_at": _seams["now_utc"]().isoformat(),
    })
    _append_ledger(run_id, "agents-offline", "canonical.compared",
                   evidence={"projection_hash": proj["sha256"], "drift": False})
    _transition_to(run_id, "canonical-compared")


def _final_runtime_snapshot(run_id: str) -> dict[str, Any]:
    """Read the exact terminal P9-3C1 residue and DB health."""
    override = _seams.get("final_observer")
    if override is not None:
        result = override()
        if not isinstance(result, dict):
            raise ControllerError("final observer returned non-object")
        return result
    matrix_jobs = _read_evidence(run_id, "matrix.json").get("jobs")
    if not isinstance(matrix_jobs, dict) or set(matrix_jobs) != set(MATRIX_LABELS):
        raise ControllerError("final exact matrix job authority missing")
    matrix = _matrix_snapshot(matrix_jobs)
    conn = _open_evidence_db(_seams["production_db"])
    try:
        result = {
            "jobs": [matrix["jobs"][label] for label in MATRIX_LABELS],
            "leases": [row for label in MATRIX_LABELS for row in matrix["leases"].get(label, [])],
            "deliveries": [row for label in MATRIX_LABELS for row in matrix["deliveries"].get(label, [])],
            "agents": _evidence_query(
                conn,
                "SELECT id, online_state, current_load, host_id FROM agents "
                "WHERE id IN (?, ?) ORDER BY id",
                ("p9-3c-fixture-e1", "p9-3c-fixture-e2"),
            ),
            "executor_sources": _evidence_query(
                conn,
                "SELECT source_id, source_version FROM executor_catalog_sources "
                "WHERE source_id = ? ORDER BY source_id",
                ("p9-3c1-fixture-executors",),
            ),
            "executor_definitions": _evidence_query(
                conn,
                "SELECT id, source_id FROM executor_definitions WHERE source_id = ? ORDER BY id",
                ("p9-3c1-fixture-executors",),
            ),
            "executor_bindings": _evidence_query(
                conn,
                "SELECT agent_id, source_id FROM executor_instance_bindings "
                "WHERE source_id = ? ORDER BY agent_id",
                ("p9-3c1-fixture-executors",),
            ),
            "capacity_sources": _evidence_query(
                conn,
                "SELECT source_id, source_version FROM executor_capacity_sources "
                "WHERE source_id = ? ORDER BY source_id",
                ("p9-3c1-fixture-capacity",),
            ),
            "capacity_policies": _evidence_query(
                conn,
                "SELECT agent_id, source_id FROM executor_capacity_policies "
                "WHERE source_id = ? ORDER BY agent_id",
                ("p9-3c1-fixture-capacity",),
            ),
        }
        integrity = _db_integrity_check(conn)
        result["db"] = {
            "integrity": integrity["integrity"],
            "schema": _db_schema_version(conn),
            "fk_violations": _db_fk_check(conn),
        }
    finally:
        conn.close()
    return result


@_register_phase("done", "canonical-compared")
def _phase_done(run_id: str, _auth: dict[str, Any]) -> None:
    """Finalize only after exact runtime residue and unit gates pass."""
    final = _final_runtime_snapshot(run_id)
    jobs = final.get("jobs")
    leases = final.get("leases")
    deliveries = final.get("deliveries")
    agents = final.get("agents")
    if not all(isinstance(value, list) for value in (jobs, leases, deliveries, agents)):
        raise ControllerError("final runtime evidence envelope mismatch")
    if len(jobs) != 5 or any(row.get("status") != "done" for row in jobs):
        raise ControllerError("final fixture jobs are not exactly five done rows")
    if any(row.get("status") == "active" for row in leases):
        raise ControllerError("final fixture lease residue is active")
    if len(deliveries) != 4 or any(
        row.get("platform") != "stdout"
        or row.get("destination") != "local"
        or row.get("status") != "sent"
        for row in deliveries
    ):
        raise ControllerError("final fixture delivery residue mismatch")
    if {row.get("id") for row in agents} != {"p9-3c-fixture-e1", "p9-3c-fixture-e2"} or any(
        row.get("online_state") != "offline" for row in agents
    ):
        raise ControllerError("final fixture agents are not offline")
    if final.get("executor_sources") != [
        {"source_id": "p9-3c1-fixture-executors", "source_version": 4}
    ] or final.get("executor_definitions") or final.get("executor_bindings"):
        raise ControllerError("final executor catalog is not exact empty v4")
    if final.get("capacity_sources") != [
        {"source_id": "p9-3c1-fixture-capacity", "source_version": 2}
    ] or final.get("capacity_policies"):
        raise ControllerError("final capacity catalog is not exact empty v2")
    if final.get("db") != {
        "integrity": "ok", "schema": EXPECTED_SCHEMA, "fk_violations": 0,
    }:
        raise ControllerError("final DB health mismatch")
    units = _read_evidence(run_id, "units-quiescent.json")
    expected_units = {
        "p9-3c-fixture-e1": {"ActiveState": "inactive", "MainPID": "0"},
        "p9-3c-fixture-e2": {"ActiveState": "inactive", "MainPID": "0"},
    }
    if units.get("agents") != expected_units:
        raise ControllerError("final unit quiescence evidence mismatch")
    final["completed_at"] = _seams["now_utc"]().isoformat()
    final["status"] = "done"
    _write_evidence(run_id, "final.json", final)
    _transition_to(run_id, "done")
    _release_lock(run_id)


# ---------------------------------------------------------------------------
# Five-job matrix execution
# ---------------------------------------------------------------------------


def _matrix_snapshot(job_ids: dict[str, str]) -> dict[str, Any]:
    """Return a bounded read-only snapshot for exact matrix job ids."""
    override = _seams.get("matrix_observer")
    if override is not None:
        snapshot = override(dict(job_ids))
        if not isinstance(snapshot, dict):
            raise ControllerError("matrix observer returned non-object")
        return snapshot
    if not job_ids:
        return {"jobs": {}, "leases": {}, "deliveries": {}}
    ids = list(job_ids.values())
    placeholders = ",".join("?" for _ in ids)
    conn = _open_evidence_db(_seams["production_db"])
    try:
        jobs = _evidence_query(
            conn,
            "SELECT id, assigned_agent, status, attempt_count, recoverable, "
            "worktree_path, result_json FROM jobs WHERE id IN (" + placeholders + ") ORDER BY id",
            tuple(ids),
        )
        leases = _evidence_query(
            conn,
            "SELECT lease_id, job_id, attempt_token, agent_id, resource_key, normalized_path, "
            "status, acquired_at, renewed_at, expires_at, released_at, release_reason "
            "FROM execution_attempt_leases WHERE job_id IN (" + placeholders + ") "
            "ORDER BY job_id, attempt_token",
            tuple(ids),
        )
        events = _evidence_query(
            conn,
            "SELECT id, payload_json FROM events WHERE workspace_id = ? ORDER BY created_at, id",
            ("p9-3c1-production",),
        )
        event_job: dict[str, str] = {}
        for row in events:
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise ControllerError("matrix event payload is invalid JSON") from exc
            if isinstance(payload, dict) and payload.get("job_id") in ids:
                event_job[row["id"]] = payload["job_id"]
        deliveries: list[dict[str, Any]] = []
        if event_job:
            event_ids = list(event_job)
            event_placeholders = ",".join("?" for _ in event_ids)
            deliveries = _evidence_query(
                conn,
                "SELECT id, event_id, platform, destination, message_key, status, "
                "platform_message_id, attempt_count FROM deliveries WHERE event_id IN ("
                + event_placeholders + ") ORDER BY id",
                tuple(event_ids),
            )
    finally:
        conn.close()
    labels_by_id = {job_id: label for label, job_id in job_ids.items()}
    now = _seams["now_utc"]()
    jobs_by_label = {labels_by_id[row["id"]]: row for row in jobs}
    leases_by_label: dict[str, list[dict[str, Any]]] = {label: [] for label in job_ids}
    for row in leases:
        row = dict(row)
        try:
            expires = datetime.datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ControllerError("matrix lease expiry is invalid") from exc
        row["due"] = row["status"] == "active" and expires <= now
        leases_by_label[labels_by_id[row["job_id"]]].append(row)
    deliveries_by_label: dict[str, list[dict[str, Any]]] = {label: [] for label in job_ids}
    for row in deliveries:
        label = labels_by_id[event_job[row["event_id"]]]
        deliveries_by_label[label].append(row)
    return {"jobs": jobs_by_label, "leases": leases_by_label, "deliveries": deliveries_by_label}


def _wait_matrix(
    job_ids: dict[str, str], description: str, predicate: Any, *, timeout: float = MATRIX_WAIT_SECONDS
) -> dict[str, Any]:
    start = float(_seams["monotonic"]())
    while True:
        snapshot = _matrix_snapshot(job_ids)
        if predicate(snapshot):
            return snapshot
        if float(_seams["monotonic"]()) - start >= timeout:
            raise ControllerError(f"matrix wait timed out: {description}")
        _seams["sleep"](0.5)


def _lease_for_attempt(snapshot: dict[str, Any], label: str, attempt: int) -> dict[str, Any] | None:
    rows = snapshot.get("leases", {}).get(label, [])
    matches = [row for row in rows if row.get("attempt_token") == attempt]
    if len(matches) > 1:
        raise ControllerError(f"matrix {label} has duplicate lease authority for attempt {attempt}")
    return matches[0] if matches else None


def _wait_terminal_with_renewals(
    job_ids: dict[str, str], label: str, agent_id: str
) -> tuple[dict[str, Any], list[str]]:
    renewed: list[str] = []

    def predicate(snapshot: dict[str, Any]) -> bool:
        job = snapshot.get("jobs", {}).get(label)
        if not isinstance(job, dict):
            return False
        if job.get("assigned_agent") != agent_id:
            raise ControllerError(f"matrix {label} agent authority mismatch")
        attempt = job.get("attempt_count")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            return False
        lease = _lease_for_attempt(snapshot, label, attempt)
        if lease is None:
            return False
        value = lease.get("renewed_at")
        if not isinstance(value, str):
            raise ControllerError(f"matrix {label} renewal authority missing")
        if not renewed or value != renewed[-1]:
            if renewed and value <= renewed[-1]:
                raise ControllerError(f"matrix {label} renewal time is not monotonic")
            renewed.append(value)
        if job.get("status") in {"failed", "timed_out", "cancelled"}:
            raise ControllerError(f"matrix {label} terminated as {job.get('status')}")
        return job.get("status") == "done" and lease.get("status") == "released" and len(renewed) >= 3

    snapshot = _wait_matrix(job_ids, f"{label} terminal with two renewals", predicate)
    return snapshot, renewed


def _wait_running_with_renewals(
    job_ids: dict[str, str], label: str, agent_id: str
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    renewed: list[str] = []

    def predicate(snapshot: dict[str, Any]) -> bool:
        job = snapshot.get("jobs", {}).get(label)
        if not isinstance(job, dict) or job.get("status") != "running":
            return False
        if job.get("assigned_agent") != agent_id:
            raise ControllerError(f"matrix {label} agent authority mismatch")
        lease = _lease_for_attempt(snapshot, label, job.get("attempt_count"))
        if lease is None or lease.get("status") != "active":
            return False
        value = lease.get("renewed_at")
        if not isinstance(value, str):
            raise ControllerError(f"matrix {label} renewal authority missing")
        if not renewed or value != renewed[-1]:
            if renewed and value <= renewed[-1]:
                raise ControllerError(f"matrix {label} renewal time is not monotonic")
            renewed.append(value)
        return len(renewed) >= 3

    snapshot = _wait_matrix(job_ids, f"{label} running with two renewals", predicate)
    job = snapshot["jobs"][label]
    lease = _lease_for_attempt(snapshot, label, job["attempt_count"])
    assert lease is not None
    return snapshot, lease, renewed


def _stale_authority_fingerprint(snapshot: dict[str, Any], label: str) -> dict[str, Any]:
    job = snapshot.get("jobs", {}).get(label, {})
    leases = snapshot.get("leases", {}).get(label, [])
    deliveries = snapshot.get("deliveries", {}).get(label, [])
    return {
        "job": {key: job.get(key) for key in ("id", "status", "attempt_count", "recoverable", "result_json")},
        "leases": [
            {key: row.get(key) for key in ("lease_id", "attempt_token", "agent_id", "resource_key", "status")}
            for row in leases
        ],
        "deliveries": [
            {key: row.get(key) for key in ("id", "platform", "destination", "status")}
            for row in deliveries
        ],
    }


def _run_five_job_matrix(run_id: str) -> None:
    """Drive five real requests through agentd units; controller only probes/reports exact authority."""
    workspace = "p9-3c1-production"
    e1, e2 = "p9-3c-fixture-e1", "p9-3c-fixture-e2"
    suffix = run_id[-8:]
    work1 = os.path.join(state_root(run_id), "runtime", "work", "e1")
    work2 = os.path.join(state_root(run_id), "runtime", "work", "e2")
    job_ids: dict[str, str] = {}
    renewals: dict[str, list[str]] = {}
    unit_generations: list[dict[str, str]] = []
    _append_ledger(run_id, "executor-v2-enabled", "matrix.budget.sealed", evidence=dict(AUTH_EXACT_BUDGETS))

    def helper(command: str, agent: str | None = None, *extra: str) -> dict[str, Any]:
        args: list[str] = []
        if agent is not None:
            args.extend(["--agent-id", agent])
        args.extend(extra)
        return _helper_cli(run_id, command, *args)

    def start(agent: str, mode: str, *extra: str) -> None:
        active = {row["agent"] for row in unit_generations if row.get("state") == "active"}
        if agent not in active and len(active) >= AUTH_EXACT_BUDGETS["max_active_units"]:
            raise ControllerError("matrix active-unit budget exceeded")
        result = helper("production-start", agent, "--mode", mode, *extra)
        if result.get("status") != "started" or result.get("agent_id") != agent or result.get("mode") != mode:
            raise ControllerError("production-start response mismatch")
        unit_generations.append({"agent": agent, "mode": mode, "state": "active"})

    def stop(agent: str, *, crash: bool = False) -> None:
        extra = ("--crash",) if crash else ()
        result = helper("production-stop", agent, *extra)
        expected = "crash" if crash else "graceful"
        if result.get("status") != "stopped" or result.get("termination") != expected:
            raise ControllerError("production-stop response mismatch")
        for row in reversed(unit_generations):
            if row["agent"] == agent and row["state"] == "active":
                row["state"] = "stopped"
                break

    def submit(label: str, agent: str, worktree: str, envelope: str) -> str:
        if label in job_ids or len(job_ids) >= AUTH_EXACT_BUDGETS["total_requests"]:
            raise ControllerError("matrix request budget exceeded or duplicate label")
        payload = _run_coord(
            "runtime", "request", "submit", workspace,
            "--target-agent", agent,
            "--worktree-path", worktree,
            "--prompt", envelope,
            "--origin-json", canonical_json({"contract_version": 1, "matrix_job": label, "run_id": run_id}),
            "--reply-json", canonical_json(MATRIX_REPLY),
            "--actor", "p9-3c1-controller",
            "--idempotency-key", f"p9-3c1-{suffix}-{label.lower()}",
        )
        result = _result_object(payload, "request submit result")
        job = _require_object(result.get("job"), "submitted job")
        job_id = job.get("id")
        if (
            result.get("job_created") is not True
            or result.get("event_created") is not True
            or not isinstance(job_id, str)
            or job.get("assigned_agent") != agent
            or job.get("worktree_path") != worktree
        ):
            raise ControllerError(f"matrix {label} submit readback mismatch")
        job_ids[label] = job_id
        _append_ledger(run_id, "executor-v2-enabled", f"matrix.{label.lower()}.submitted", evidence={"job_id": job_id})
        return job_id

    rendered = _helper_cli(run_id, "production-render")
    if rendered.get("status") != "rendered" or rendered.get("run_id") != run_id:
        raise ControllerError("production-render response mismatch")
    for agent in (e1, e2):
        preflight = helper("production-preflight", agent)
        if preflight.get("status") != "preflight_ok" or preflight.get("agent_id") != agent:
            raise ControllerError("production-preflight response mismatch")
    start(e1, "complete")

    submit("J1", e1, work1, MATRIX_COMPLETE_ENVELOPE)
    _, renewals["J1"] = _wait_terminal_with_renewals(job_ids, "J1", e1)
    submit("J2", e1, work1, MATRIX_COMPLETE_ENVELOPE)
    _, renewals["J2"] = _wait_terminal_with_renewals(job_ids, "J2", e1)

    submit("J3", e1, work1, MATRIX_HOLD_ENVELOPE)
    _, old_lease, renewals["J3"] = _wait_running_with_renewals(job_ids, "J3", e1)
    old_attempt = old_lease["attempt_token"]
    old_lease_id = old_lease["lease_id"]

    submit("J4", e2, work2, MATRIX_COMPLETE_ENVELOPE)
    submit("J5", e2, work1, MATRIX_COMPLETE_ENVELOPE)
    start(e2, "complete")

    def overlap(snapshot: dict[str, Any]) -> bool:
        j3 = snapshot.get("jobs", {}).get("J3", {})
        j4 = snapshot.get("jobs", {}).get("J4", {})
        l3 = _lease_for_attempt(snapshot, "J3", old_attempt)
        l4 = _lease_for_attempt(snapshot, "J4", j4.get("attempt_count", -1))
        return (
            j3.get("status") == "running" and j4.get("status") == "running"
            and l3 is not None and l3.get("status") == "active"
            and l4 is not None and l4.get("status") == "active"
            and l3.get("resource_key") != l4.get("resource_key")
        )

    overlap_snapshot = _wait_matrix(job_ids, "J3/J4 active overlap", overlap)
    _, renewals["J4"] = _wait_terminal_with_renewals(job_ids, "J4", e2)
    blocker = _result_object(
        _run_coord(
            "runtime", "job", "claim", "--agent-id", e2,
            "--reap-mode", "none", "--reap-reason", f"p9-3c1-resource-probe-{suffix}",
        ),
        "J5 resource probe",
    )
    if (
        blocker.get("claimed") is not False
        or blocker.get("reason") != "resource_blocked"
        or blocker.get("oldest_blocked_job_id") != job_ids["J5"]
        or blocker.get("oldest_blocked_resource_key") != old_lease.get("resource_key")
    ):
        raise ControllerError("J5 exact resource blocker was not proven")

    stop(e1, crash=True)

    def old_due(snapshot: dict[str, Any]) -> bool:
        lease = _lease_for_attempt(snapshot, "J3", old_attempt)
        return lease is not None and lease.get("lease_id") == old_lease_id and lease.get("due") is True

    _wait_matrix(job_ids, "J3 old lease exact expiry", old_due)
    reap = _result_object(
        _run_coord(
            "runtime", "job", "lease", "reap",
            "--lease-id", old_lease_id, "--job-id", job_ids["J3"],
            "--actor", "p9-3c1-controller",
        ),
        "exact reap result",
    )
    if (
        reap.get("mode") != "exact" or reap.get("reaped_count") != 1
        or reap.get("lease_id") != old_lease_id or reap.get("job_id") != job_ids["J3"]
        or reap.get("attempt_token") != old_attempt
    ):
        raise ControllerError("J3 exact reap response mismatch")

    def reaped(snapshot: dict[str, Any]) -> bool:
        job = snapshot.get("jobs", {}).get("J3", {})
        lease = _lease_for_attempt(snapshot, "J3", old_attempt)
        return (
            job.get("status") == "timed_out" and job.get("recoverable") in {1, True}
            and job.get("attempt_count") == old_attempt
            and lease is not None and lease.get("status") == "expired"
        )

    _wait_matrix(job_ids, "J3 exact reap readback", reaped)
    start(
        e1, "hold", "--recoverable",
        "--recovery-reason", f"p9-3c1-j3-recovery-{suffix}",
        "--prior-process-stopped",
    )

    def recovered(snapshot: dict[str, Any]) -> bool:
        job = snapshot.get("jobs", {}).get("J3", {})
        lease = _lease_for_attempt(snapshot, "J3", old_attempt + 1)
        return (
            job.get("id") == job_ids["J3"] and job.get("status") == "running"
            and job.get("attempt_count") == old_attempt + 1
            and lease is not None and lease.get("status") == "active"
            and lease.get("lease_id") != old_lease_id
            and lease.get("resource_key") == old_lease.get("resource_key")
        )

    recovery_snapshot = _wait_matrix(job_ids, "J3 N+1 recovery claim", recovered)
    new_attempt = old_attempt + 1
    new_lease = _lease_for_attempt(recovery_snapshot, "J3", new_attempt)
    assert new_lease is not None
    new_lease_id = new_lease["lease_id"]
    stale_specs = {
        "progress": (
            "runtime", "job", "progress", job_ids["J3"], "--agent-id", e1,
            "--stage", "p9-3c1-stale-probe", "--summary", "stale-attempt-probe",
            "--attempt-token", str(old_attempt), "--lease-id", old_lease_id,
            "--actor", "p9-3c1-controller",
        ),
        "report": (
            "runtime", "job", "report", job_ids["J3"], "--agent-id", e1,
            "--status", "done", "--result-json", "{}",
            "--attempt-token", str(old_attempt), "--lease-id", old_lease_id,
            "--actor", "p9-3c1-controller",
        ),
        "renew": (
            "runtime", "job", "lease", "renew", job_ids["J3"], "--agent-id", e1,
            "--attempt-token", str(old_attempt), "--lease-id", old_lease_id,
            "--actor", "p9-3c1-controller",
        ),
    }
    stale_digests: dict[str, str] = {}
    for name, args in stale_specs.items():
        before = _stale_authority_fingerprint(_matrix_snapshot(job_ids), "J3")
        stale_digests[name] = _expect_coord_rejection(*args)
        after = _stale_authority_fingerprint(_matrix_snapshot(job_ids), "J3")
        if after != before:
            raise ControllerError(f"stale {name} mutated J3 authority")

    current = _result_object(
        _run_coord(
            "runtime", "job", "report", job_ids["J3"], "--agent-id", e1,
            "--status", "done", "--result-json", "{}",
            "--attempt-token", str(new_attempt), "--lease-id", new_lease_id,
            "--actor", "p9-3c1-controller",
        ),
        "J3 current report",
    )
    if (
        _require_object(current.get("job"), "J3 reported job").get("status") != "done"
        or current.get("delivery") is not None or current.get("delivery_created") is not False
    ):
        raise ControllerError("J3 N+1 empty terminal report mismatch")

    _, renewals["J5"] = _wait_terminal_with_renewals(job_ids, "J5", e2)
    delivery_evidence: dict[str, dict[str, Any]] = {}
    snapshot = _matrix_snapshot(job_ids)
    if snapshot.get("deliveries", {}).get("J3", []):
        raise ControllerError("J3 empty recovery result created a delivery")
    for label in ("J1", "J2", "J4", "J5"):
        rows = snapshot.get("deliveries", {}).get(label, [])
        if len(rows) != 1:
            raise ControllerError(f"matrix {label} must have exactly one response delivery")
        row = rows[0]
        if row.get("platform") != "stdout" or row.get("destination") != "local" or row.get("status") != "pending":
            raise ControllerError(f"matrix {label} delivery authority mismatch")
        sent = _result_object(_run_coord("delivery", "send", row["id"]), f"{label} delivery send")
        sent_row = _require_object(sent.get("delivery"), f"{label} sent delivery")
        if sent.get("sent") is not True or sent_row.get("status") != "sent" or sent_row.get("id") != row["id"]:
            raise ControllerError(f"matrix {label} stdout delivery send failed")
        delivery_evidence[label] = {key: sent_row.get(key) for key in ("id", "platform", "destination", "status", "platform_message_id")}

    final_snapshot = _matrix_snapshot(job_ids)
    for label in MATRIX_LABELS:
        if final_snapshot.get("jobs", {}).get(label, {}).get("status") != "done":
            raise ControllerError(f"matrix {label} is not terminal done")
    evidence = {
        "budget": dict(AUTH_EXACT_BUDGETS),
        "jobs": dict(job_ids),
        "renewals": renewals,
        "overlap": {
            "j3_lease_id": old_lease_id,
            "j4_status": overlap_snapshot["jobs"]["J4"]["status"],
        },
        "blocker": {key: blocker.get(key) for key in ("claimed", "reason", "oldest_blocked_job_id", "oldest_blocked_resource_key")},
        "reap": {key: reap.get(key) for key in ("mode", "reaped_count", "lease_id", "job_id", "attempt_token")},
        "recovery": {
            "old_attempt": old_attempt,
            "old_lease_id": old_lease_id,
            "new_attempt": new_attempt,
            "new_lease_id": new_lease_id,
            "stale_rejection_digests": stale_digests,
        },
        "unit_generations": unit_generations,
        "deliveries": delivery_evidence,
    }
    _write_evidence(run_id, "matrix.json", evidence)
    _append_ledger(run_id, "executor-v2-enabled", "matrix.executed", evidence={"evidence_sha256": sha256_hex(canonical_json(evidence))})


def _verify_job_matrix(run_id: str) -> None:
    """Independently derive acceptance from sealed matrix evidence and live readback."""
    evidence = _read_evidence(run_id, "matrix.json")
    jobs = evidence.get("jobs")
    if not isinstance(jobs, dict) or tuple(jobs) != MATRIX_LABELS or len(set(jobs.values())) != 5:
        raise ControllerError("matrix evidence does not contain five unique exact jobs")
    if evidence.get("budget") != AUTH_EXACT_BUDGETS:
        raise ControllerError("matrix evidence budget mismatch")
    renewals = evidence.get("renewals")
    if not isinstance(renewals, dict) or set(renewals) != set(MATRIX_LABELS):
        raise ControllerError("matrix renewal evidence set mismatch")
    for label, values in renewals.items():
        if not isinstance(values, list) or len(values) < 3 or values != sorted(set(values)):
            raise ControllerError(f"matrix {label} did not prove two monotonic renewals")
    blocker = evidence.get("blocker", {})
    if blocker.get("claimed") is not False or blocker.get("reason") != "resource_blocked" or blocker.get("oldest_blocked_job_id") != jobs["J5"]:
        raise ControllerError("matrix blocker evidence mismatch")
    recovery = evidence.get("recovery", {})
    if (
        recovery.get("new_attempt") != recovery.get("old_attempt", 0) + 1
        or recovery.get("old_lease_id") == recovery.get("new_lease_id")
        or set(recovery.get("stale_rejection_digests", {})) != {"progress", "report", "renew"}
    ):
        raise ControllerError("matrix recovery/stale evidence mismatch")
    generations = evidence.get("unit_generations")
    if not isinstance(generations, list) or [(row.get("agent"), row.get("mode")) for row in generations] != [
        ("p9-3c-fixture-e1", "complete"),
        ("p9-3c-fixture-e2", "complete"),
        ("p9-3c-fixture-e1", "hold"),
    ]:
        raise ControllerError("matrix unit-generation evidence mismatch")
    deliveries = evidence.get("deliveries")
    if not isinstance(deliveries, dict) or set(deliveries) != {"J1", "J2", "J4", "J5"}:
        raise ControllerError("matrix delivery evidence set mismatch")
    if any(row.get("platform") != "stdout" or row.get("destination") != "local" or row.get("status") != "sent" for row in deliveries.values()):
        raise ControllerError("matrix delivery evidence mismatch")
    snapshot = _matrix_snapshot(jobs)
    if any(snapshot.get("jobs", {}).get(label, {}).get("status") != "done" for label in MATRIX_LABELS):
        raise ControllerError("matrix final job readback mismatch")
    if snapshot.get("deliveries", {}).get("J3", []):
        raise ControllerError("matrix J3 has forbidden response delivery")
    for label in ("J1", "J2", "J4", "J5"):
        rows = snapshot.get("deliveries", {}).get(label, [])
        if len(rows) != 1 or rows[0].get("status") != "sent":
            raise ControllerError(f"matrix {label} sent-delivery readback mismatch")
    digest = sha256_hex(canonical_json(evidence))
    _append_ledger(run_id, "matrix-running", "matrix.verified", evidence={"evidence_sha256": digest})

# ---------------------------------------------------------------------------
# Lock acquisition
# ---------------------------------------------------------------------------


def _lock_action(run_id: str) -> str:
    return LOCK_ACTION_PREFIX + run_id


def _parse_lock_token(raw: Any) -> str:
    if not isinstance(raw, str):
        raise ControllerError("production lock token must be text")
    token = raw.strip("\n")
    if raw not in {token, token + "\n"} or not re.fullmatch(r"[0-9a-f]{64}", token):
        raise ControllerError("production lock returned malformed token")
    return token


def _read_lock_token(run_id: str) -> str:
    path = validate_single_link(lock_token_path(run_id))
    _seams["validate_owner_mode"](path, 0, 0, 0o600)
    return _parse_lock_token(Path(path).read_text(encoding="ascii"))


def _require_owned_lock(run_id: str, token: str | None = None) -> dict[str, Any]:
    if token is None:
        token = _read_lock_token(run_id)
    else:
        token = _parse_lock_token(token)
    status = _lock_status(token)
    expected = {
        "state": "held",
        "phase": "held",
        "owner": LOCK_OWNER,
        "action": _lock_action(run_id),
        "token_matches": True,
    }
    for key, value in expected.items():
        if status.get(key) != value:
            raise ControllerError(f"production lock ownership mismatch for {key}: {status!r}")
    return status


def _call_lock_release(token: str) -> None:
    override = _seams.get("lock_release")
    if override is not None:
        override(token)
        return
    runner = _seams.get("run_command") or _run_command
    result = runner(
        [_seams["lock_helper"], "release", "--token", token],
        env={},
        timeout=15.0,
        output_cap=16_384,
    )
    if result.returncode != 0:
        raise ControllerError(
            f"production lock release failed (exit {result.returncode}): "
            f"{result.stderr[:500]!r}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ControllerError("production lock release returned non-JSON") from exc
    if payload.get("state") != "released":
        raise ControllerError(f"production lock release result mismatch: {payload!r}")


def _release_lock(run_id: str) -> None:
    """Release only the exact owned P0 token; preserve evidence on any failure."""
    token = _read_lock_token(run_id)
    _require_owned_lock(run_id, token)
    _call_lock_release(token)
    free = _lock_status()
    if free.get("state") not in {"free", "absent"} or free.get("phase") != "free":
        raise ControllerError(f"production lock did not become free: {free!r}")
    os.unlink(lock_token_path(run_id))
    dfd = os.open(os.path.dirname(lock_token_path(run_id)), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def _acquire_lock(run_id: str) -> str:
    """Acquire the installed P0 global lock and durably seal its exact token."""
    validate_run_id(run_id)
    ltp = lock_token_path(run_id)
    if os.path.lexists(ltp):
        raise ControllerError("production lock token file already exists")
    _require_free_lock()

    override = _seams.get("lock_acquire")
    if override is not None:
        token = _parse_lock_token(override(run_id))
    else:
        host = str(_seams["hostname"]())
        runner = _seams.get("run_command") or _run_command
        result = runner(
            [
                _seams["lock_helper"],
                "acquire",
                "--owner",
                LOCK_OWNER,
                "--action",
                _lock_action(run_id),
                "--owner-host",
                host,
                "--owner-pid",
                str(os.getpid()),
            ],
            env={},
            timeout=15.0,
            output_cap=16_384,
        )
        if result.returncode != 0:
            raise ControllerError(
                f"production lock acquire failed (exit {result.returncode}): "
                f"{result.stderr[:500]!r}"
            )
        token = _parse_lock_token(result.stdout)

    os.makedirs(os.path.dirname(ltp), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ltp), prefix=".token-", suffix=".tmp")
    try:
        os.write(fd, (token + "\n").encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp, 0o600)
    _seams["chown"](tmp, 0, 0)
    os.replace(tmp, ltp)
    dfd = os.open(os.path.dirname(ltp), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    _require_owned_lock(run_id, token)
    return token


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _validate_prepare_args(run_id: str, unit_user: str, unit_group: str) -> None:
    validate_run_id(run_id)
    if not isinstance(unit_user, str) or not unit_user.strip():
        raise ControllerError("unit_user must be non-blank string")
    if not isinstance(unit_group, str) or not unit_group.strip():
        raise ControllerError("unit_group must be non-blank string")


def _create_run_dirs(run_id: str) -> None:
    root = state_root(run_id)
    dirs = [
        os.path.join(root, "control"),
        os.path.join(root, "ledger"),
        os.path.join(root, "evidence"),
        os.path.join(root, "backup"),
        os.path.join(root, "runtime", "work", "e1"),
        os.path.join(root, "runtime", "work", "e2"),
        os.path.join(root, "runtime", "context"),
        os.path.join(root, "runtime", "unit"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=False)
    # Set ownership: control/ledger/backup root:root 0700
    for d in [os.path.join(root, "control"), os.path.join(root, "ledger"), os.path.join(root, "backup")]:
        os.chmod(d, 0o700)
    # runtime: would be root:coord 0750 in production


def _file_identity(path: str) -> dict[str, Any]:
    canonical = validate_single_link(path)
    st = os.stat(canonical, follow_symlinks=False)
    return {
        "path": canonical,
        "dev": st.st_dev,
        "inode": st.st_ino,
        "nlink": st.st_nlink,
        "owner": st.st_uid,
        "group": st.st_gid,
        "mode": stat.S_IMODE(st.st_mode) if stat.S_ISREG(st.st_mode) else stat.S_IMODE(st.st_mode),
        "size": st.st_size,
        "sha256": sha256_file(canonical),
    }


def _collect_installed_hashes() -> dict[str, str]:
    """Collect SHA-256 of key installed files."""
    root = _seams["installed_root"]
    paths = {
        "controller": os.path.join(root, "scripts", "p9_3c1_controller.py"),
        "entrypoint": os.path.join(root, "scripts", "p9-3c1-production-verify.sh"),
        "helper": _seams["helper_path"],
        "fixture_bin": _seams["fixture_bin"],
        "agentd_main": os.path.join(root, "multinexus", "agentd", "__main__.py"),
        "agentd_worker": os.path.join(root, "multinexus", "agentd", "worker.py"),
        "agentd_coordinate_client": os.path.join(
            root, "multinexus", "agentd", "coordinate_client.py"
        ),
    }
    hashes: dict[str, str] = {}
    for name, path in paths.items():
        canonical = validate_single_link(path)
        hashes[name] = sha256_file(canonical)
    return hashes


def _collect_launcher_files() -> dict[str, dict[str, Any]]:
    """Collect exact executable/template file identities sealed into the manifest."""
    return {
        "python": _file_identity(_seams["python_path"]),
        "helper": _file_identity(_seams["helper_path"]),
        "fixture_bin": _file_identity(_seams["fixture_bin"]),
        "mutation_lock_helper": _file_identity(_seams["lock_helper"]),
        "agent_template": _file_identity(
            os.path.join(_seams["config_dir"], "agents.production.toml")
        ),
    }


def _collect_revisions() -> dict[str, str]:
    """Read exact deployed revisions from the two VERSION_DEPLOYED authorities."""
    def read_version(path: str, component: str) -> str:
        canonical = validate_single_link(path)
        values: dict[str, str] = {}
        for line in Path(canonical).read_text(encoding="utf-8").splitlines():
            if not line or "=" not in line:
                raise ControllerError(f"invalid VERSION_DEPLOYED line: {path}")
            key, value = line.split("=", 1)
            if key in values:
                raise ControllerError(f"duplicate VERSION_DEPLOYED key {key}: {path}")
            values[key] = value
        commit = values.get("commit", "")
        if values.get("component") != component or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ControllerError(f"invalid deployed revision authority: {path}")
        return commit

    return {
        "multinexus_deployed": read_version(
            os.path.join(_seams["installed_root"], "VERSION_DEPLOYED"),
            "multinexus",
        ),
        "coordinate_deployed": read_version(
            os.path.join(_seams["coordinate_root"], "VERSION_DEPLOYED"),
            "coordinate",
        ),
    }


def _validate_config_contract(config_dir: str, helper_path: str) -> dict[str, Any]:
    """Parse the immutable P9-3C1 catalogs and cross-check their exact sets."""
    expected_agents = ("p9-3c-fixture-e1", "p9-3c-fixture-e2")
    expected_agent_set = set(expected_agents)
    executor_files = (
        ("executor.v1-disabled.toml", 1, False),
        ("executor.v2-enabled.toml", 2, True),
        ("executor.v3-disabled.toml", 3, False),
        ("executor.v4-empty.toml", 4, None),
    )
    hashes: dict[str, str] = {}
    for filename, version, enabled in executor_files:
        path = os.path.join(config_dir, filename)
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        registry = data.get("registry")
        if registry != {"id": "p9-3c1-fixture-executors", "version": version}:
            raise ControllerError(f"invalid executor source/version: {filename}")
        definitions = data.get("executor_definitions", [])
        agents = data.get("agents", [])
        if version == 4:
            if definitions or agents:
                raise ControllerError("executor v4 must be empty")
        else:
            if definitions != [{
                "id": "p9-3c1-local-fixture",
                "provider": "local-fixture",
                "adapter": "claude",
                "capabilities": ["p9-3c1-fixture"],
            }]:
                raise ControllerError(f"invalid executor definition: {filename}")
            ids = [row.get("id") for row in agents]
            if len(ids) != 2 or set(ids) != expected_agent_set:
                raise ControllerError(f"invalid executor agent set: {filename}")
            for row in agents:
                agent_id = row["id"]
                if row.get("executor_definition_id") != "p9-3c1-local-fixture":
                    raise ControllerError(f"invalid executor binding: {filename}")
                if row.get("runner_profile_id") != agent_id:
                    raise ControllerError(f"invalid runner binding: {filename}")
                if row.get("enabled") is not enabled:
                    raise ControllerError(f"invalid enabled state: {filename}")
                discord_id = row.get("discord_user_id")
                if not isinstance(discord_id, str) or not discord_id.isdigit():
                    raise ControllerError(f"invalid inert Discord id: {filename}")
        hashes[filename] = sha256_file(path)

    capacity_files = (
        ("capacity.v1.toml", 1, {agent_id: 1 for agent_id in expected_agents}),
        ("capacity.v2-empty.toml", 2, {}),
    )
    for filename, version, expected in capacity_files:
        path = os.path.join(config_dir, filename)
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        if data.get("capacity_registry") != {
            "id": "p9-3c1-fixture-capacity",
            "version": version,
        }:
            raise ControllerError(f"invalid capacity source/version: {filename}")
        rows = data.get("executor_capacities", [])
        actual = {row.get("agent_id"): row.get("max_concurrent_jobs") for row in rows}
        if len(rows) != len(actual) or actual != expected:
            raise ControllerError(f"invalid capacity policy set: {filename}")
        hashes[filename] = sha256_file(path)

    agent_path = os.path.join(config_dir, "agents.production.toml")
    raw = Path(agent_path).read_text(encoding="utf-8")
    with open(agent_path, "rb") as fh:
        agent_data = tomllib.load(fh)
    defaults = agent_data.get("defaults", {})
    agent_rows = agent_data.get("agents", [])
    ids = [row.get("id") for row in agent_rows]
    if len(ids) != 2 or set(ids) != expected_agent_set:
        raise ControllerError("invalid agent template set")
    if defaults.get("agentd_mode") is not True or defaults.get("adapter") != "claude":
        raise ControllerError("invalid agentd template mode")
    if defaults.get("claude_bin") != _seams["fixture_bin"]:
        raise ControllerError("agent template fixture binary drift")
    if defaults.get("coordinator_cli_path") != PRODUCTION_CLI:
        raise ControllerError("agent template Coordinate CLI drift")
    if defaults.get("coordinator_db_path") != PRODUCTION_DB:
        raise ControllerError("agent template Coordinate DB drift")
    if "__P9C0_" in raw:
        raise ControllerError("P9-3C0 marker in P9-3C1 template")
    markers = set(re.findall(r"__P9C1_[A-Z0-9_]+__", raw))
    if markers != {
        "__P9C1_E1_WORK_DIR__",
        "__P9C1_E2_WORK_DIR__",
        "__P9C1_E1_CONTEXT_DB__",
        "__P9C1_E2_CONTEXT_DB__",
    }:
        raise ControllerError(f"invalid P9-3C1 template markers: {sorted(markers)!r}")
    forbidden_keys = {
        "token", "token_env", "channels", "kook_poll_channel_ids", "model",
        "omp_model", "hermes_provider", "openclaw_agent_id",
    }
    if forbidden_keys.intersection(defaults) or any(
        forbidden_keys.intersection(row) for row in agent_rows
    ):
        raise ControllerError("agent template contains provider/bus/delivery authority")
    hashes["agents.production.toml"] = sha256_file(agent_path)

    helper_raw = Path(helper_path).read_text(encoding="utf-8")
    declarations = re.findall(r"P9C0_AGENT_ALLOWLIST=\(([^)]*)\)", helper_raw)
    if not declarations:
        raise ControllerError("helper agent allowlist declaration missing")
    import shlex
    for declaration in declarations:
        values = shlex.split(declaration)
        if len(values) != 2 or set(values) != expected_agent_set:
            raise ControllerError("helper agent allowlist mismatch")
    return {"agent_ids": list(expected_agents), "config_hashes": hashes}


def _collect_config_hashes() -> dict[str, str]:
    """Collect SHA-256 of P9-3C1 config files."""
    config_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "multinexus", "fixture", "config", "p9-3c1",
    )
    files = [
        "agents.production.toml",
        "executor.v1-disabled.toml",
        "executor.v2-enabled.toml",
        "executor.v3-disabled.toml",
        "executor.v4-empty.toml",
        "capacity.v1.toml",
        "capacity.v2-empty.toml",
    ]
    hashes: dict[str, str] = {}
    for f in files:
        fp = os.path.join(config_dir, f)
        if os.path.exists(fp):
            hashes[f] = sha256_file(fp)
        else:
            hashes[f] = "absent"
    return hashes


def _create_backup(run_id: str) -> None:
    """Create read-only online backup with mode 0600."""
    bp = backup_path(run_id)
    os.makedirs(os.path.dirname(bp), exist_ok=True)
    src = sqlite3.connect(f"file:{_seams['production_db']}?mode=ro", uri=True)
    dst = sqlite3.connect(bp)
    src.backup(dst)
    src.close()
    dst.close()
    os.chmod(bp, 0o600)


def _read_evidence(run_id: str, filename: str) -> dict[str, Any]:
    """Read an evidence file. Returns empty dict if not found."""
    ep = os.path.join(evidence_dir(run_id), filename)
    if not os.path.exists(ep):
        return {}
    with open(ep, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_evidence(run_id: str, filename: str, data: dict[str, Any]) -> None:
    """Atomically write an evidence file."""
    ep = os.path.join(evidence_dir(run_id), filename)
    parent = os.path.dirname(ep)
    os.makedirs(parent, exist_ok=True)
    content = canonical_json(data) + "\n"
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=".ev-", suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp, 0o600)
    os.replace(tmp, ep)


def _write_forensic_failure(run_id: str, marker: str) -> None:
    """Write a forensic failure marker."""
    fp = os.path.join(state_root(run_id), marker)
    with open(fp, "w") as fh:
        fh.write(f"{marker}\n")


def _atomic_copy(src: str, dst: str, mode: int = 0o600) -> None:
    """Atomically copy a file."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, "rb") as sfh:
        data = sfh.read()
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dst), prefix=".copy-", suffix=".tmp")
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp, mode)
    os.replace(tmp, dst)


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="P9-3C1 P2 Inert Production Controller")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--run-id", required=True)
    p_prepare.add_argument("--unit-user", required=True)
    p_prepare.add_argument("--unit-group", required=True)

    p_preflight = sub.add_parser("preflight")
    p_preflight.add_argument("--run-id", required=True)

    p_status = sub.add_parser("status")
    p_status.add_argument("--run-id", required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--run-id", required=True)
    p_run.add_argument("--authorization-file", required=True)
    p_run.add_argument("--authorization-sha256", required=True)

    p_cleanup = sub.add_parser("cleanup")
    p_cleanup.add_argument("--run-id", required=True)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if _seams["os_geteuid"]() != 0:
        print("p9_3c1_controller: must run as root", file=sys.stderr)
        sys.exit(1)

    try:
        if args.command == "prepare":
            result = cmd_prepare(args.run_id, args.unit_user, args.unit_group)
        elif args.command == "preflight":
            result = cmd_preflight(args.run_id)
        elif args.command == "status":
            result = cmd_status(args.run_id)
        elif args.command == "run":
            result = cmd_run(args.run_id, args.authorization_file, args.authorization_sha256)
        elif args.command == "cleanup":
            result = cmd_cleanup(args.run_id)
        else:
            parser.error(f"unknown command: {args.command}")
            return

        print(canonical_json(result))

    except ControllerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
