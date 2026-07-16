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

# ── systemd unit identity (Section 4) ──────────────────────────────────

_UNIT_RE = re.compile(
    r"^p9-3c-fixture-e[12]-p9-3c1-prod-[0-9]{8}t[0-9]{6}z-[a-f0-9]{8}\.service$"
)

# ── process identity (Section 5) ───────────────────────────────────────

_CONTROLLER_ARGV0 = "/usr/bin/python3.12"
_CONTROLLER_ARGV1 = "/opt/multinexus/scripts/p9_3c1_controller.py"
_FIXTURE_ARGV0 = "/usr/bin/python3.12"
_FIXTURE_MODULE = "multinexus.agentd"
_FIXTURE_IDS = frozenset({"p9-3c-fixture-e1", "p9-3c-fixture-e2"})
_MAX_PID_STDOUT = 1 * 1024 * 1024  # 1 MiB
_MAX_PID_COUNT = 131072
_MAX_CMDLINE_READ = 64 * 1024 + 1  # 64 KiB + 1
_MAX_SYSTEMD_STDOUT = 1 * 1024 * 1024  # 1 MiB
_MAX_PID_VALUE = 2147483647  # fixed reviewed signed 32-bit PID value bound



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
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return _ProbeResult(
            ok=False,
            reason="systemctl unavailable: cannot prove no p9-3c1 units",
        )
    except Exception:
        return _ProbeResult(ok=False, reason="systemd probe unavailable")
    rc = result.returncode
    if rc != 0:
        return _ProbeResult(
            ok=False, reason="systemctl exited non-zero"
        )
    if result.stderr:
        return _ProbeResult(
            ok=False, reason="systemd probe returned non-empty stderr"
        )
    stdout_bytes = result.stdout.encode("utf-8", errors="replace")
    if len(stdout_bytes) > _MAX_SYSTEMD_STDOUT:
        return _ProbeResult(
            ok=False,
            reason="systemd probe: oversized stdout",
        )
    for line in result.stdout.splitlines():
        if not line.strip():
            return _ProbeResult(
                ok=False, reason="systemd output contains blank or whitespace-only row"
            )
        columns = line.split()
        if len(columns) < 4:
            return _ProbeResult(
                ok=False, reason="systemd output row has fewer than four columns"
            )
        name = columns[0]
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
            return _ProbeResult(
                ok=False, reason="systemd output row unit name contains control character"
            )
        if not name.endswith(".service"):
            return _ProbeResult(
                ok=False, reason="systemd output row is not a .service unit"
            )
        if _UNIT_RE.match(name):
            return _ProbeResult(ok=False, reason="active p9-3c1 unit")
    return _ProbeResult(ok=True, reason="no active p9-3c1 units")



# ── default PID enumeration (Section 5.1) ──────────────────────────────


def _default_enumerate_pids() -> list[int]:
    result = subprocess.run(
        ["ps", "-e", "-o", "pid="],
        shell=False,
        timeout=10,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise OSError(errno.EIO, "ps exited non-zero")
    if result.stderr:
        raise OSError(errno.EIO, "ps returned non-empty stderr")
    stdout_bytes = result.stdout.encode("utf-8", errors="replace")
    if len(stdout_bytes) > _MAX_PID_STDOUT:
        raise OSError(errno.EIO, "ps output exceeds 1 MiB")
    pids: list[int] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not re.fullmatch(r"[0-9]+", stripped):
            raise OSError(errno.EIO, "malformed PID")
        try:
            pid = int(stripped)
        except ValueError:
            raise OSError(errno.EIO, "malformed PID")
        if pid <= 0 or pid > _MAX_PID_VALUE:
            raise OSError(errno.EIO, "PID out of range")
        pids.append(pid)
    if len(pids) > _MAX_PID_COUNT:
        raise OSError(errno.EIO, "PID count exceeds limit")
    if len(set(pids)) != len(pids):
        raise OSError(errno.EIO, "duplicate PIDs in ps output")
    return pids


def _default_read_cmdline(pid: int) -> bytes:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read(_MAX_CMDLINE_READ)
    except OSError:
        raise


def _probe_processes_default(
    *,
    enumerate_pids: Callable[[], list[int]] = _default_enumerate_pids,
    read_cmdline: Callable[[int], bytes] = _default_read_cmdline,
    kill_0: Callable[[int, int], None] = os.kill,
    self_pid: Callable[[], int] = os.getpid,
) -> _ProbeResult:
    """Bounded exact-argv process probe (Section 5).

    Enumerates PIDs via ``enumerate_pids``, reads ``/proc/<pid>/cmdline``
    via ``read_cmdline``, and identifies controller/fixture processes by
    exact argv identity.  Malformed candidates fail closed.
    """
    try:
        pids = enumerate_pids()
    except Exception:
        return _ProbeResult(
            ok=False,
            reason="PID enumeration failed",
        )
    my_pid = self_pid()
    blocked: list[int] = []
    for pid in pids:
        if pid == my_pid:
            continue
        try:
            raw = read_cmdline(pid)
        except OSError as exc:
            eno = getattr(exc, "errno", 0)
            if eno in (errno.ENOENT, errno.ESRCH):
                # PID may have disappeared — confirm via kill(pid, 0)
                try:
                    kill_0(pid, 0)
                except OSError as exc2:
                    if getattr(exc2, "errno", 0) == errno.ESRCH:
                        continue  # confirmed exited
                    return _ProbeResult(
                        ok=False,
                        reason=(
                            f"PID {pid} disappeared from /proc but "
                            "kill(0) did not confirm exit"
                        ),
                    )
                except (OverflowError, ValueError):
                    return _ProbeResult(
                        ok=False,
                        reason=(
                            f"PID {pid} disappeared from /proc but "
                            "kill(0) did not confirm exit"
                        ),
                    )
                # kill succeeded or EPERM — PID is present/uncertain
                return _ProbeResult(
                    ok=False,
                    reason=(
                        f"PID {pid} /proc read returned error but "
                        "kill(0) did not confirm exit"
                    ),
                )
            # Permission, I/O, or other error — fail closed
            return _ProbeResult(
                ok=False,
                reason=f"PID {pid} cmdline read failed",
            )
        if len(raw) >= _MAX_CMDLINE_READ:
            return _ProbeResult(
                ok=False,
                reason=f"PID {pid} cmdline too long",
            )
        # Empty cmdline → kernel thread — ignore
        if not raw or raw == b"\x00":
            continue
        # Parse NUL-delimited argv
        if b"\x00\x00" in raw:
            return _ProbeResult(
                ok=False,
                reason=f"PID {pid} cmdline contains empty interior argv",
            )
        try:
            raw_str = raw.decode("utf-8")
        except UnicodeDecodeError:
            return _ProbeResult(
                ok=False,
                reason=f"PID {pid} cmdline is not valid UTF-8",
            )
        # Every non-kernel-thread authority must end with NUL
        if not raw.endswith(b"\x00"):
            return _ProbeResult(
                ok=False,
                reason=f"PID {pid} cmdline does not end with NUL",
            )
        # Strip trailing NUL for split
        raw_str = raw_str[:-1]
        argv = raw_str.split("\x00")
        # Leading or interior empty argv is malformed
        if "" in argv:
            return _ProbeResult(
                ok=False,
                reason=f"PID {pid} cmdline contains empty argv",
            )
        if _classify_argv(argv) is not None:
            blocked.append(pid)
    if blocked:
        return _ProbeResult(
            ok=False,
            reason=f"running p9-3c1 processes: {blocked}",
        )
    return _ProbeResult(ok=True, reason="no running p9-3c1 processes")


def _classify_argv(argv: list[str]) -> str | None:
    """Return a classification label if argv is a blocked identity.

    Returns ``"controller"``, ``"fixture-e1"``, ``"fixture-e2"`` for
    exact matches, or ``None`` for non-matching argv.  Malformed
    candidates that contain the module plus a fixture id without the
    exact expected structure fall through to the final check.
    """
    if len(argv) < 2:
        return None
    # ── controller identity (Section 5.2 item 1) ──
    if (
        argv[0] == _CONTROLLER_ARGV0
        and len(argv) >= 2
        and argv[1] == _CONTROLLER_ARGV1
    ):
        return "controller"
    # ── fixture identity pre-check ──
    if (
        argv[0] == _FIXTURE_ARGV0
        and len(argv) >= 3
        and argv[1:3] == ["-m", _FIXTURE_MODULE]
    ):
        # Look for exactly one ``--agent <id>`` pair with a fixture id
        agent_id: str | None = None
        agent_count = 0
        i = 3
        while i < len(argv):
            if argv[i] == "--agent" and i + 1 < len(argv):
                agent_id = argv[i + 1]
                agent_count += 1
                i += 2
            else:
                i += 1
        if agent_count == 1 and agent_id is not None and agent_id in _FIXTURE_IDS:
            return "fixture-" + agent_id.removeprefix("p9-3c-").replace("-", "")
        # Malformed: module present with a fixture id but wrong --agent structure
        if agent_id in _FIXTURE_IDS:
            return "malformed-fixture"
        has_fixture_in_argv = any(
            fid in argv for fid in _FIXTURE_IDS
        )
        if has_fixture_in_argv:
            return "malformed-fixture"
    return None


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
        # Process probe sub-seams (Section 5 injectable).
        self._enumerate_pids: Callable[[], list[int]] = _default_enumerate_pids
        self._read_proc_cmdline: Callable[[int], bytes] = _default_read_cmdline
        self._kill_0: Callable[[int, int], None] = os.kill
        # Rebind default process probe to capture injectable sub-seams.
        self._probe_processes = self._run_probe_processes

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


    def _run_probe_processes(self) -> _ProbeResult:
        """Run process probe with current injectable sub-seams."""
        return _probe_processes_default(
            enumerate_pids=self._enumerate_pids,
            read_cmdline=self._read_proc_cmdline,
            kill_0=self._kill_0,
        )

    # ── token file validation (Section 6) ────────────────────────────────

    def _read_token_file(self, path_str: str) -> str:
        """Validate and read a token from a recover-only token file.

        Returns the validated 64-char lowercase hex token.  Every error
        (path, stat, open, read, decode, content) is converted into a
        bounded redacted ``LockError`` before recovery can begin.  The
        raw token never enters argv/stdout/stderr/error detail/audit.
        """
        # ── path validation ──
        if not path_str or not os.path.isabs(path_str):
            raise LockError(
                state="blocked",
                detail={"reason": "token-file must be a non-blank absolute path"},
                exit_code=4,
            )
        token_path = Path(path_str)
        parent = str(token_path.parent)
        # ── parent lstat ──
        try:
            parent_st = self._lstat(parent)
        except (OSError, ValueError) as exc:
            raise LockError(
                state="blocked",
                detail={"reason": "token-file parent lstat failed"},
                exit_code=4,
            )
        if stat.S_ISLNK(parent_st.st_mode):
            raise LockError(
                state="blocked",
                detail={"reason": "token-file parent is a symlink"},
                exit_code=4,
            )
        if not self._isdir(parent_st):
            raise LockError(
                state="blocked",
                detail={"reason": "token-file parent is not a directory"},
                exit_code=4,
            )
        if parent_st.st_uid != 0 or parent_st.st_gid != 0:
            raise LockError(
                state="blocked",
                detail={"reason": "token-file parent must be root:root"},
                exit_code=4,
            )
        if stat.S_IMODE(parent_st.st_mode) != 0o700:
            raise LockError(
                state="blocked",
                detail={"reason": "token-file parent mode must be 0700"},
                exit_code=4,
            )
        # ── open file ──
        try:
            fd = self._open(path_str, os.O_RDONLY | os.O_NOFOLLOW)
        except (OSError, ValueError):
            raise LockError(
                state="blocked",
                detail={"reason": "token-file open failed"},
                exit_code=4,
            )
        try:
            # ── first fstat ──
            try:
                st1 = self._fstat(fd)
            except (OSError, ValueError):
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file fstat failed"},
                    exit_code=4,
                )
            if not self._isfile(st1):
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file is not a regular file"},
                    exit_code=4,
                )
            if st1.st_uid != 0 or st1.st_gid != 0:
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file must be root:root"},
                    exit_code=4,
                )
            if stat.S_IMODE(st1.st_mode) != 0o600:
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file mode must be 0600"},
                    exit_code=4,
                )
            if st1.st_nlink != 1:
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file link count must be 1"},
                    exit_code=4,
                )
            size = st1.st_size
            if size not in (64, 65):
                raise LockError(
                    state="blocked",
                    detail={"reason": f"token-file size {size} not in (64, 65)"},
                    exit_code=4,
                )
            # ── read (exact size + 1-byte growth probe) ──
            try:
                raw = os.read(fd, size + 1)
            except (OSError, ValueError):
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file read failed"},
                    exit_code=4,
                )
            # ── growth probe: check if file grew ──
            if len(raw) != size:
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file size changed between stat and read"},
                    exit_code=4,
                )
            # ── second fstat (TOCTOU guard) ──
            try:
                st2 = self._fstat(fd)
            except (OSError, ValueError):
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file second fstat failed"},
                    exit_code=4,
                )
            if (
                st2.st_ino != st1.st_ino
                or st2.st_dev != st1.st_dev
                or st2.st_size != st1.st_size
                or st2.st_uid != st1.st_uid
                or st2.st_gid != st1.st_gid
                or st2.st_mode != st1.st_mode
                or st2.st_nlink != st1.st_nlink
                or st2.st_mtime_ns != st1.st_mtime_ns
                or st2.st_ctime_ns != st1.st_ctime_ns
            ):
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file changed between stat calls"},
                    exit_code=4,
                )
            # ── decode content ──
            content = raw
            if content.endswith(b"\n"):
                content = content[:-1]
            try:
                text = content.decode("ascii")
            except UnicodeDecodeError:
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file content is not ASCII"},
                    exit_code=4,
                )
            if "\n" in text or "\r" in text:
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file contains embedded newline/CR"},
                    exit_code=4,
                )
            if not _TOKEN_RE.fullmatch(text):
                raise LockError(
                    state="blocked",
                    detail={"reason": "token-file content is not 64-char lowercase hex"},
                    exit_code=4,
                )
            return text
        finally:
            os.close(fd)
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
    token_group = recover_parser.add_mutually_exclusive_group(required=True)
    token_group.add_argument("--token", default=None)
    token_group.add_argument("--token-file", default=None)
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
        elif args.command == "recover":
            if args.token_file is not None:
                token = lock._read_token_file(args.token_file)
            else:
                token = args.token
            result = lock.recover(
                token=token,
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
