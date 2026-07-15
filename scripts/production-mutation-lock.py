#!/usr/bin/env python3
"""Root-owned shared production mutation lock helper.

Production constants (LOCK_DIR, OWNER_PATH, HELPER_PATH, AUDIT_PATH) are fixed.
Tests must import ProductionMutationLock and override its paths/probes via
constructor kwargs; CLI always uses the production constants.

CLI contracts:

* ``acquire`` writes the **raw 64-char lowercase hex token + a single newline**
  to stdout on success. stderr stays empty; no JSON envelope. This makes the
  success token trivially machine-parseable without depending on a JSON
  parser in shell callers (the deploy script reads it directly).
* ``status``, ``release`` and ``recover`` emit a single canonical JSON object
  on stdout. stderr is reserved for failures and never carries a raw token.
* All commands are read-only when they do not need to mutate; ``status`` is
  always read-only.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CONTRACT_VERSION = 1
LOCK_DIR = "/run/lock/coordinate-production-mutation.lock"
OWNER_PATH = "/run/lock/coordinate-production-mutation.lock/owner.json"
HELPER_PATH = "/usr/local/sbin/coordinate-production-mutation-lock"
AUDIT_PATH = "/var/log/coordinate-production-mutation-lock-recovery.jsonl"

_ALLOWED_RE = re.compile(r"^[A-Za-z0-9_:-]{1,128}$")
_TOKEN_RE = re.compile(r"^[0-9a-f]{64}$")


class LockError(Exception):
    """Bounded lock operation error with structured detail."""

    def __init__(self, *, state: str, detail: dict[str, Any], exit_code: int = 1):
        self.state = state
        self.detail = detail
        self.exit_code = exit_code
        super().__init__(state)


@dataclass
class _ProbeResult:
    ok: bool
    reason: str


# ── default probes (testable via injection) ────────────────────────────────


def _probe_systemd_default() -> _ProbeResult:
    try:
        result = subprocess.run(
            [
                "systemctl", "list-units",
                "--type=service",
                "--state=running,reloading,activating,deactivating",
                "--no-pager", "--no-legend",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        # systemctl missing on the host: cannot prove no active p9-3c1 unit.
        return _ProbeResult(
            ok=False,
            reason="systemctl unavailable: cannot prove no p9-3c1 units",
        )
    except Exception as exc:
        return _ProbeResult(ok=False, reason=f"systemd probe unavailable: {exc}")
    rc = result.returncode
    if rc != 0:
        return _ProbeResult(
            ok=False, reason=f"systemctl exited {rc}: {result.stderr.strip()}"
        )
    for line in result.stdout.splitlines():
        name = line.split()[0] if line.split() else ""
        if name.startswith("p9-3c1-"):
            return _ProbeResult(ok=False, reason=f"active p9-3c1 unit: {name}")
    return _ProbeResult(ok=True, reason="no active p9-3c1 units")


def _probe_processes_default() -> _ProbeResult:
    try:
        result = subprocess.run(
            ["pgrep", "-f", "p9-3c1"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        # Missing pgrep is indistinguishable from "could not prove no live
        # process". Fail closed: an absent probe cannot authorize a recover.
        return _ProbeResult(
            ok=False,
            reason="pgrep unavailable: cannot prove no p9-3c1 processes",
        )
    except Exception as exc:
        return _ProbeResult(ok=False, reason=f"process probe unavailable: {exc}")
    rc = result.returncode
    # pgrep returns 1 when no process matched (the desired "ok" case).
    # Any other non-zero exit is treated as probe failure so recover cannot
    # authorize on uncertain ground.
    if rc not in (0, 1):
        return _ProbeResult(
            ok=False, reason=f"pgrep exited {rc}: {result.stderr.strip()}"
        )
    if rc == 1:
        return _ProbeResult(ok=True, reason="no running p9-3c1 processes")
    pids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if pids:
        return _ProbeResult(ok=False, reason=f"running p9-3c1 processes: {pids}")
    return _ProbeResult(ok=True, reason="no running p9-3c1 processes")


# ── core lock class ─────────────────────────────────────────────────────────


class ProductionMutationLock:
    """Core lock logic.

    All filesystem paths and probes are constructor kwargs so tests can inject
    temporary roots. CLI always uses production defaults.
    """

    def __init__(
        self,
        *,
        lock_dir: str = LOCK_DIR,
        owner_path: str = OWNER_PATH,
        helper_path: str = HELPER_PATH,
        audit_path: str = AUDIT_PATH,
    ) -> None:
        self.lock_dir = Path(lock_dir)
        self.owner_path = Path(owner_path)
        self.helper_path = Path(helper_path)
        self.audit_path = Path(audit_path)

        self._is_root: Callable[[], bool] = lambda: os.geteuid() == 0
        self._now_utc: Callable[[], str] = lambda: (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        # Filesystem operations (injectable for fsync-failure tests).
        self._mkdir = os.mkdir
        self._lstat = os.lstat
        self._open = os.open
        self._unlink = os.unlink
        self._rmdir = os.rmdir
        self._chmod = os.chmod
        self._chown = os.chown
        self._fchmod = os.fchmod
        self._fchown = os.fchown
        self._fsync = os.fsync
        self._fstat = os.fstat
        self._replace = os.replace
        self._symlink = os.symlink
        self._readlink = os.readlink
        self._listdir = os.listdir
        # Test-only failure injection.
        self._inject_fsync_failure: str | None = None
        self._inject_dir_fsync_failure: bool = False
        self._inject_chown_failure: bool = False
        self._inject_audit_fsync_failure: bool = False
        self._probe_systemd: Callable[[], _ProbeResult] = _probe_systemd_default
        self._probe_processes: Callable[[], _ProbeResult] = _probe_processes_default

    # ── input validation ────────────────────────────────────────────────

    def _validate_id(self, value: Any, name: str) -> str:
        if not isinstance(value, str):
            raise LockError(
                state="invalid_input",
                detail={"field": name, "reason": f"{name} must be a string"},
                exit_code=2,
            )
        if not _ALLOWED_RE.fullmatch(value):
            raise LockError(
                state="invalid_input",
                detail={"field": name, "reason": f"{name} contains invalid characters"},
                exit_code=2,
            )
        return value

    def _validate_positive_int_pid(self, value: Any, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise LockError(
                state="invalid_input",
                detail={"field": name, "reason": f"{name} must be an integer, not bool"},
                exit_code=2,
            )
        if value <= 0:
            raise LockError(
                state="invalid_input",
                detail={"field": name, "reason": f"{name} must be positive"},
                exit_code=2,
            )
        return value

    def _validate_token_shape(self, token: Any) -> str:
        if not isinstance(token, str):
            raise LockError(
                state="invalid_input",
                detail={"reason": "token must be a string"},
                exit_code=2,
            )
        if not _TOKEN_RE.fullmatch(token):
            raise LockError(
                state="invalid_input",
                detail={"reason": "token must be 64-char lowercase hex"},
                exit_code=2,
            )
        return token

    # ── helpers ─────────────────────────────────────────────────────────

    def _token_hex(self) -> str:
        return secrets.token_hex(32)

    def _token_digest(self, token: str) -> str:
        return "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _token_prefix(self, token: str) -> str:
        return token[:16] + "..."

    def _canonical_meta(self, meta: dict[str, Any]) -> bytes:
        return json.dumps(
            meta, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    def _isfile(self, st: os.stat_result) -> bool:
        return stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode)

    def _isdir(self, st: os.stat_result) -> bool:
        return stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode)

    # ── owner.json write (atomic) ────────────────────────────────────────

    def _write_owner(self, meta: dict[str, Any], *, fsync: bool = True) -> None:
        data = self._canonical_meta(meta)
        parent = self.owner_path.parent
        tmp_path = parent / f".owner.json.tmp.{os.getpid()}.{int(time.monotonic() * 1e9)}"
        try:
            fd = self._open(
                str(tmp_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(fd, "wb", closefd=True) as f:
                self._fchmod(f.fileno(), 0o600)
                self._fchown(f.fileno(), 0, 0)
                f.write(data)
                if fsync:
                    if self._inject_fsync_failure == "file":
                        raise OSError(errno.EIO, "injected fsync failure")
                    self._fsync(f.fileno())
            self._replace(str(tmp_path), str(self.owner_path))
            if fsync:
                if self._inject_dir_fsync_failure:
                    raise OSError(errno.EIO, "injected dir fsync failure")
                dir_fd = self._open(
                    str(parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                )
                try:
                    self._fsync(dir_fd)
                finally:
                    os.close(dir_fd)
        except Exception:
            try:
                self._unlink(str(tmp_path))
            except OSError:
                pass
            raise

    # ── owner.json read (TOCTOU-safe) ───────────────────────────────────

    def _read_owner(self) -> dict[str, Any]:
        """Read owner.json without following symlinks and validate the fd.

        The path is opened with ``O_RDONLY|O_NOFOLLOW``; if the file is a
        symlink the open itself returns ELOOP. After open we re-stat the fd
        (so an inode swap after the directory ``lstat`` cannot slip in) and
        enforce regular file / single-link / root / 0600 / root-only ownership
        before reading. All authority checks raise ``ValueError`` so the
        caller surfaces them as ``invalid``.
        """
        path = str(self.owner_path)
        try:
            fd = self._open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError as exc:
            raise ValueError(f"owner.json open failed: {exc}") from exc
        try:
            st = self._fstat(fd)
        except OSError:
            os.close(fd)
            raise
        if not self._isfile(st):
            os.close(fd)
            raise ValueError("owner.json is not a regular file")
        if st.st_uid != 0 or st.st_gid != 0:
            os.close(fd)
            raise ValueError("owner.json has non-root ownership")
        if stat.S_IMODE(st.st_mode) != 0o600:
            os.close(fd)
            raise ValueError("owner.json mode is not 0600")
        if st.st_nlink != 1:
            os.close(fd)
            raise ValueError("owner.json link count is not 1")
        try:
            chunks: list[bytes] = []
            remaining = st.st_size
            while remaining:
                chunk = os.read(fd, min(remaining, 65536))
                if not chunk:
                    raise ValueError("owner.json short read")
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
        finally:
            os.close(fd)
        meta = json.loads(data.decode("utf-8"))
        if not isinstance(meta, dict):
            raise ValueError("owner.json is not a JSON object")
        return meta

    # ── authority validation ─────────────────────────────────────────────

    def _check_authority(self) -> dict[str, Any]:
        """Validate lock directory + owner.json authority.

        Returns meta on success.  Raises LockError with state=invalid otherwise.
        Zero mutation.  Uses the injected _is_root() probe consistently —
        never os.geteuid() directly — so tests can verify root/nonroot paths.
        """

        # ── lock directory ──
        try:
            dir_st = self._lstat(str(self.lock_dir))
        except FileNotFoundError:
            raise LockError(
                state="absent",
                detail={"reason": "lock directory does not exist"},
                exit_code=1,
            )
        if stat.S_ISLNK(dir_st.st_mode):
            raise LockError(
                state="invalid",
                detail={"reason": "lock directory is a symlink"},
                exit_code=3,
            )
        if not stat.S_ISDIR(dir_st.st_mode):
            raise LockError(
                state="invalid",
                detail={"reason": "lock path is not a directory"},
                exit_code=3,
            )
        if dir_st.st_uid != 0 or dir_st.st_gid != 0:
            raise LockError(
                state="invalid",
                detail={"reason": "lock directory has non-root ownership"},
                exit_code=3,
            )
        if stat.S_IMODE(dir_st.st_mode) != 0o700:
            raise LockError(
                state="invalid",
                detail={"reason": "lock directory mode is not 0700"},
                exit_code=3,
            )
        # Minimum link count for a directory with one entry: '.' + 'owner.json' = 2
        if dir_st.st_nlink < 2:
            raise LockError(
                state="invalid",
                detail={"reason": "lock directory link count is too low"},
                exit_code=3,
            )

        # ── owner.json ──
        try:
            owner_st = self._lstat(str(self.owner_path))
        except FileNotFoundError:
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json is missing"},
                exit_code=3,
            )
        if stat.S_ISLNK(owner_st.st_mode):
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json is a symlink"},
                exit_code=3,
            )
        if not stat.S_ISREG(owner_st.st_mode):
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json is not a regular file"},
                exit_code=3,
            )
        if owner_st.st_uid != 0 or owner_st.st_gid != 0:
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json has non-root ownership"},
                exit_code=3,
            )
        if stat.S_IMODE(owner_st.st_mode) != 0o600:
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json mode is not 0600"},
                exit_code=3,
            )
        if owner_st.st_nlink != 1:
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json link count is not 1"},
                exit_code=3,
            )

        # ── strict single-entry directory ──
        entries = self._listdir(str(self.lock_dir))
        if set(entries) != {"owner.json"}:
            raise LockError(
                state="invalid",
                detail={"reason": "lock directory contains unexpected entries"},
                exit_code=3,
            )

        # ── metadata parse & validation (TOCTOU-safe read) ──
        try:
            meta = self._read_owner()
        except Exception as exc:
            raise LockError(
                state="invalid",
                detail={"reason": f"owner.json is unreadable: {exc}"},
                exit_code=3,
            )

        required = {
            "contract_version", "token", "owner", "action",
            "owner_host", "owner_pid", "started_at", "phase",
        }
        if set(meta.keys()) != required:
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json keys mismatch"},
                exit_code=3,
            )
        if meta.get("contract_version") != CONTRACT_VERSION:
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json contract_version mismatch"},
                exit_code=3,
            )
        if meta.get("phase") != "held":
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json phase is not held"},
                exit_code=3,
            )

        token = meta.get("token", "")
        if not _TOKEN_RE.fullmatch(token):
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json token is not 64-char lowercase hex"},
                exit_code=3,
            )

        try:
            datetime.strptime(meta.get("started_at", ""), "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            raise LockError(
                state="invalid",
                detail={"reason": "owner.json started_at is not canonical UTC"},
                exit_code=3,
            )

        try:
            self._validate_positive_int_pid(meta.get("owner_pid"), "owner_pid")
        except LockError as exc:
            raise LockError(
                state="invalid",
                detail={"reason": f"owner_pid invalid: {exc.detail['reason']}"},
                exit_code=3,
            )

        for key in ("owner", "action", "owner_host"):
            try:
                self._validate_id(meta.get(key, ""), key)
            except LockError as exc:
                raise LockError(
                    state="invalid",
                    detail={"reason": f"{key} invalid: {exc.detail['reason']}"},
                    exit_code=3,
                )
        return meta

    def _redact_meta(self, meta: dict[str, Any]) -> dict[str, Any]:
        return {
            "contract_version": meta.get("contract_version"),
            "owner": meta.get("owner"),
            "action": meta.get("action"),
            "owner_host": meta.get("owner_host"),
            "owner_pid": meta.get("owner_pid"),
            "started_at": meta.get("started_at"),
            "phase": meta.get("phase"),
            "token_digest": self._token_digest(meta.get("token", "")),
            "token_prefix": self._token_prefix(meta.get("token", "")),
        }

    # ── acquire ──────────────────────────────────────────────────────────

    def acquire(
        self,
        *,
        owner: str,
        action: str,
        owner_host: str,
        owner_pid: int,
    ) -> dict[str, Any]:
        # Fail closed: non-root cannot acquire.
        if not self._is_root():
            raise LockError(
                state="blocked",
                detail={"reason": "must be root to acquire"},
                exit_code=4,
            )
        owner = self._validate_id(owner, "owner")
        action = self._validate_id(action, "action")
        owner_host = self._validate_id(owner_host, "owner_host")
        owner_pid = self._validate_positive_int_pid(owner_pid, "owner_pid")

        # Atomic mkdir wins the lock.
        try:
            self._mkdir(str(self.lock_dir), 0o700)
        except FileExistsError:
            # Lock directory exists — validate authority.
            try:
                meta = self._check_authority()
            except LockError as exc:
                if exc.state == "invalid":
                    raise  # invalid authority — do not repair
                # absent state shouldn't happen here, but pass through
                raise
            # Valid lock held — blocked.
            raise LockError(
                state="blocked",
                detail=self._redact_meta(meta),
                exit_code=5,
            )
        except OSError as exc:
            raise LockError(
                state="invalid",
                detail={"reason": f"mkdir failed: {exc}"},
                exit_code=3,
            )

        # Ensure root ownership on the freshly created directory.
        # Fail closed: if chown fails (injected or real), clean up and bail.
        try:
            if self._inject_chown_failure:
                raise PermissionError("injected chown failure")
            self._chown(str(self.lock_dir), 0, 0)
            self._chmod(str(self.lock_dir), 0o700)
        except (PermissionError, OSError) as exc:
            # Clean up partial authority we just created.
            try:
                self._rmdir(str(self.lock_dir))
            except OSError:
                pass
            raise LockError(
                state="invalid",
                detail={"reason": f"chown failed on lock directory: {exc}"},
                exit_code=3,
            )

        token = self._token_hex()
        meta = {
            "contract_version": CONTRACT_VERSION,
            "token": token,
            "owner": owner,
            "action": action,
            "owner_host": owner_host,
            "owner_pid": owner_pid,
            "started_at": self._now_utc(),
            "phase": "held",
        }
        try:
            self._write_owner(meta)
        except Exception as exc:
            # Clean up partial authority: only if we can prove it's empty/partial.
            try:
                if self.lock_dir.exists():
                    entries = self._listdir(str(self.lock_dir))
                    if set(entries) <= {"owner.json"}:
                        try:
                            self._unlink(str(self.owner_path))
                        except FileNotFoundError:
                            pass
                        self._rmdir(str(self.lock_dir))
            except OSError:
                pass
            raise LockError(
                state="invalid",
                detail={"reason": f"metadata write failed: {exc}"},
                exit_code=3,
            )
        return {"state": "acquired", "token": token, "started_at": meta["started_at"]}

    # ── status (read-only) ───────────────────────────────────────────────

    def status(self, *, expect_token: str | None = None) -> dict[str, Any]:
        if expect_token is not None:
            self._validate_token_shape(expect_token)
        try:
            meta = self._check_authority()
        except LockError as exc:
            if exc.state == "invalid":
                raise
            # absent → free
            return {"state": "free", "phase": "free"}

        result: dict[str, Any] = {"state": "held", "phase": "held"}
        result.update(self._redact_meta(meta))
        if expect_token is not None:
            result["token_matches"] = hmac.compare_digest(meta["token"], expect_token)
        return result

    # ── release ──────────────────────────────────────────────────────────

    def release(
        self, *, token: str, allow_already_free: bool = False
    ) -> dict[str, Any]:
        if not self._is_root():
            raise LockError(
                state="blocked",
                detail={"reason": "must be root to release"},
                exit_code=4,
            )
        self._validate_token_shape(token)

        try:
            meta = self._check_authority()
        except LockError as exc:
            if exc.state == "invalid":
                raise
            # absent → only succeed with explicit idempotency flag
            if allow_already_free:
                return {"state": "already_free", "phase": "free"}
            raise LockError(
                state="mismatch",
                detail={
                    "reason": "lock is free; cannot release without --allow-already-free"
                },
                exit_code=6,
            )

        if not hmac.compare_digest(meta["token"], token):
            raise LockError(
                state="mismatch",
                detail={"reason": "token mismatch"},
                exit_code=6,
            )

        try:
            self._unlink(str(self.owner_path))
            self._rmdir(str(self.lock_dir))
        except FileNotFoundError:
            if allow_already_free:
                return {"state": "already_free", "phase": "free"}
            raise LockError(
                state="mismatch",
                detail={"reason": "lock disappeared during release"},
                exit_code=6,
            )
        except OSError as exc:
            raise LockError(
                state="invalid",
                detail={"reason": f"release failed: {exc}"},
                exit_code=3,
            )
        return {"state": "released", "phase": "free"}

    # ── recover (incident-only) ──────────────────────────────────────────

    def recover(
        self,
        *,
        token: str,
        operator: str,
        reason: str,
        confirm_owner_stopped: bool = False,
    ) -> dict[str, Any]:
        if not self._is_root():
            raise LockError(
                state="blocked",
                detail={"reason": "must be root to recover"},
                exit_code=4,
            )
        self._validate_token_shape(token)
        operator = self._validate_id(operator, "operator")
        reason = self._validate_id(reason, "reason")
        if not confirm_owner_stopped:
            raise LockError(
                state="blocked",
                detail={"reason": "recover requires --confirm-owner-stopped"},
                exit_code=4,
            )

        meta = self._check_authority()
        if not hmac.compare_digest(meta["token"], token):
            raise LockError(
                state="mismatch",
                detail={"reason": "token mismatch"},
                exit_code=6,
            )

        # Run probes before any mutation.
        probe_results: dict[str, Any] = {}
        systemd_probe = self._probe_systemd()
        probe_results["systemd"] = {"ok": systemd_probe.ok, "reason": systemd_probe.reason}
        if not systemd_probe.ok:
            raise LockError(
                state="blocked",
                detail={"reason": f"systemd probe failed: {systemd_probe.reason}"},
                exit_code=4,
            )
        process_probe = self._probe_processes()
        probe_results["processes"] = {"ok": process_probe.ok, "reason": process_probe.reason}
        if not process_probe.ok:
            raise LockError(
                state="blocked",
                detail={"reason": f"process probe failed: {process_probe.reason}"},
                exit_code=4,
            )

        # Write audit entry before release.
        audit_entry = {
            "recovered_at": self._now_utc(),
            "operator": operator,
            "reason": reason,
            "lock_owner": meta.get("owner"),
            "lock_action": meta.get("action"),
            "lock_owner_host": meta.get("owner_host"),
            "lock_owner_pid": meta.get("owner_pid"),
            "lock_started_at": meta.get("started_at"),
            "lock_token_digest": self._token_digest(meta["token"]),
            "lock_token_prefix": self._token_prefix(meta["token"]),
        }
        try:
            self._audit_append(audit_entry)
        except OSError as exc:
            raise LockError(
                state="blocked",
                detail={"reason": f"audit append failed: {exc}"},
                exit_code=4,
            )

        # Only release after durable audit.
        try:
            self._unlink(str(self.owner_path))
            self._rmdir(str(self.lock_dir))
        except OSError as exc:
            raise LockError(
                state="invalid",
                detail={"reason": f"recover release failed: {exc}"},
                exit_code=3,
            )
        return {
            "state": "recovered",
            "phase": "free",
            "receipt_digest": self._token_digest(
                json.dumps(audit_entry, sort_keys=True)
            ),
        }

    def _audit_append(self, entry: dict[str, Any]) -> None:
        line = (
            json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        )
        parent = self.audit_path.parent
        try:
            parent_st = self._lstat(str(parent))
        except OSError as exc:
            raise OSError(errno.EIO, f"audit parent unavailable: {exc}") from exc
        if (
            not self._isdir(parent_st)
            or parent_st.st_uid != 0
            or parent_st.st_gid != 0
        ):
            raise OSError(errno.EPERM, "audit parent must be a root-owned directory")

        fd = self._open(
            str(self.audit_path),
            os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW,
            0o600,
        )
        try:
            audit_st = self._fstat(fd)
            if (
                not self._isfile(audit_st)
                or audit_st.st_uid != 0
                or audit_st.st_gid != 0
                or stat.S_IMODE(audit_st.st_mode) != 0o600
                or audit_st.st_nlink != 1
            ):
                raise OSError(
                    errno.EPERM,
                    "audit file must be a root-owned 0600 single-link regular file",
                )
            payload = memoryview(line.encode("utf-8"))
            while payload:
                written = os.write(fd, payload)
                if written <= 0:
                    raise OSError(errno.EIO, "short audit write")
                payload = payload[written:]
            # Durability: fsync the audit file, then fsync the parent directory
            # so the new append survives a host crash. Any failure must abort
            # the recover before the lock is touched.
            if self._inject_audit_fsync_failure:
                raise OSError(errno.EIO, "injected audit fsync failure")
            self._fsync(fd)
        finally:
            os.close(fd)

        # Parent directory fsync so the append is durable. Best effort if the
        # parent directory is not writable; failure here is the same class of
        # error as audit append failure and aborts the recover.
        try:
            dir_fd = self._open(
                str(parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
            try:
                self._fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError as exc:
            raise OSError(errno.EIO, f"audit parent fsync failed: {exc}") from exc


# ── CLI ────────────────────────────────────────────────────────────────────


def _json_out(obj: dict[str, Any]) -> None:
    print(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _err_out(obj: dict[str, Any]) -> None:
    # Defense in depth: strip any field that looks like a raw token (64
    # lowercase hex) from the error stream so an errant code path can never
    # leak the active lock token via stderr.
    def _scrub(value: Any) -> Any:
        if isinstance(value, str):
            return _TOKEN_RE.sub("<redacted:64hex>", value)
        if isinstance(value, dict):
            return {k: _scrub(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_scrub(v) for v in value]
        return value
    print(
        json.dumps(_scrub(obj), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        file=sys.stderr,
    )


def _emit_acquire_token(token: str) -> None:
    """Write the raw token + a single trailing newline to stdout.

    No JSON envelope, no other characters. This is the canonical success
    channel for ``acquire`` so shell callers can read it with a single
    ``read`` and never accidentally serialize/parse a JSON object.
    """
    sys.stdout.write(token + "\n")
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    # Restrict every filesystem object this helper may create. This is
    # process-local, so status remains filesystem read-only.
    os.umask(0o077)
    parser = argparse.ArgumentParser(prog="coordinate-production-mutation-lock")
    subparsers = parser.add_subparsers(dest="command", required=True)

    acquire_parser = subparsers.add_parser("acquire")
    acquire_parser.add_argument("--owner", required=True)
    acquire_parser.add_argument("--action", required=True)
    acquire_parser.add_argument("--owner-host", required=True)
    acquire_parser.add_argument("--owner-pid", required=True, type=int)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--expect-token", default=None)

    release_parser = subparsers.add_parser("release")
    release_parser.add_argument("--token", required=True)
    release_parser.add_argument("--allow-already-free", action="store_true")

    recover_parser = subparsers.add_parser("recover")
    recover_parser.add_argument("--token", required=True)
    recover_parser.add_argument("--operator", required=True)
    recover_parser.add_argument("--reason", required=True)
    recover_parser.add_argument("--confirm-owner-stopped", action="store_true")
    args = parser.parse_args(argv)
    lock = ProductionMutationLock()
    try:
        if args.command == "acquire":
            result = lock.acquire(
                owner=args.owner,
                action=args.action,
                owner_host=args.owner_host,
                owner_pid=args.owner_pid,
            )
            token = result.get("token", "")
            if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token):
                # Defensive: if the core ever produced a malformed token,
                # refuse to write it as the raw stream.
                raise LockError(
                    state="invalid",
                    detail={"reason": "internal token shape violation"},
                    exit_code=3,
                )
            _emit_acquire_token(token)
            return 0
        if args.command == "status":
            result = lock.status(expect_token=args.expect_token)
            _json_out(result)
            return 0
        if args.command == "release":
            result = lock.release(
                token=args.token, allow_already_free=args.allow_already_free
            )
            _json_out(result)
            return 0
        if args.command == "recover":
            result = lock.recover(
                token=args.token,
                operator=args.operator,
                reason=args.reason,
                confirm_owner_stopped=args.confirm_owner_stopped,
            )
            _json_out(result)
            return 0
    except LockError as exc:
        # error detail must never carry a raw 64-hex token. _err_out scrubs,
        # but we additionally drop any "token" key explicitly here.
        detail = {k: v for k, v in exc.detail.items() if k != "token"}
        _err_out({"state": exc.state, **detail})
        return exc.exit_code
    return 1


if __name__ == "__main__":
    sys.exit(main())
