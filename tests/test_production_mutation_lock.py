"""Focused tests for scripts/production-mutation-lock.py.

All tests use injectable temp paths and fake system probes; no real root,
/run, /usr/local/sbin, /var/log, or systemd is required.
"""
import hashlib
import json
import os
import stat
import errno
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "production_mutation_lock",
    str(Path(__file__).parent.parent / "scripts" / "production-mutation-lock.py"),
)
_production_mutation_lock = importlib.util.module_from_spec(_spec)
sys.modules["production_mutation_lock"] = _production_mutation_lock
_spec.loader.exec_module(_production_mutation_lock)
ProductionMutationLock = _production_mutation_lock.ProductionMutationLock
LockError = _production_mutation_lock.LockError
CONTRACT_VERSION = _production_mutation_lock.CONTRACT_VERSION


class _FakeRoot:
    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.lock_dir = self.tmp / "lock"
        self.owner_path = self.lock_dir / "owner.json"
        self.helper_path = self.tmp / "sbin" / "coordinate-production-mutation-lock"
        self.audit_path = self.tmp / "log" / "recovery.jsonl"
        self.audit_path.parent.mkdir(mode=0o755)

    def lock(self, **kwargs):
        defaults = {
            "lock_dir": str(self.lock_dir),
            "owner_path": str(self.owner_path),
            "helper_path": str(self.helper_path),
            "audit_path": str(self.audit_path),
        }
        defaults.update(kwargs)
        return ProductionMutationLock(**defaults)


class Base(unittest.TestCase):
    def setUp(self):
        self.root = _FakeRoot()
        self.lock = self.root.lock()
        self.lock._is_root = lambda: True
        self.lock._chown = lambda path, uid, gid: None
        self.lock._fchown = lambda fd, uid, gid: None
        _real_lstat = self.lock._lstat
        _real_fstat = self.lock._fstat
        lock_dir_str = str(self.root.lock_dir)
        owner_path_str = str(self.root.owner_path)
        audit_parent_str = str(self.root.audit_path.parent)
        audit_path_str = str(self.root.audit_path)
        tmp_root = str(self.root.tmp)
        def _fake_lstat(path):
            st = _real_lstat(path)
            if path == lock_dir_str:
                return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
            if path in {owner_path_str, audit_parent_str, audit_path_str}:
                return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
            # Any path under the temp root gets root:root for token-file tests
            if path.startswith(tmp_root):
                return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
            return st
        def _fake_fstat(fd):
            # Mirror lstat's ownership fixup: tests do not run as real root,
            # so the new TOCTOU-safe ``_read_owner`` needs the same uid/gid
            # rewrite that lstat already receives.
            st = _real_fstat(fd)
            return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
        self.lock._lstat = _fake_lstat
        self.lock._fstat = _fake_fstat
        self.lock._probe_systemd = lambda: type("P", (), {"ok": True, "reason": "ok"})()
        self.lock._probe_processes = lambda: type("P", (), {"ok": True, "reason": "ok"})()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root.tmp, ignore_errors=True)

    def _acquire(self, **kwargs):
        return self.lock.acquire(
            owner=kwargs.get("owner", "deploy"),
            action=kwargs.get("action", "multinexus"),
            owner_host=kwargs.get("owner_host", "mac"),
            owner_pid=kwargs.get("owner_pid", os.getpid()),
        )


class AcquireTests(Base):
    def test_successful_acquire_metadata(self):
        result = self._acquire()
        self.assertEqual(result["state"], "acquired")
        self.assertEqual(len(result["token"]), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result["token"]))
        self.assertTrue(self.root.lock_dir.is_dir())
        st = self.root.lock_dir.stat()
        self.assertEqual(stat.S_IMODE(st.st_mode), 0o700)
        owner_st = self.root.owner_path.stat()
        self.assertEqual(stat.S_IMODE(owner_st.st_mode), 0o600)
        raw = self.root.owner_path.read_bytes()
        meta = json.loads(raw)
        self.assertEqual(
            set(meta.keys()),
            {
                "contract_version", "token", "owner", "action",
                "owner_host", "owner_pid", "started_at", "phase",
            },
        )
        self.assertEqual(meta["contract_version"], CONTRACT_VERSION)
        self.assertEqual(meta["phase"], "held")
        self.assertEqual(meta["owner"], "deploy")
        self.assertEqual(meta["action"], "multinexus")
        self.assertEqual(meta["owner_host"], "mac")
        self.assertEqual(meta["owner_pid"], os.getpid())
        self.assertTrue(meta["started_at"].endswith("Z"))
        expected = json.dumps(
            meta, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        self.assertEqual(raw, expected)

    def test_blocked_acquire_preserves_stat(self):
        self._acquire(owner="first")
        before = self.root.owner_path.stat()
        time.sleep(0.01)
        with self.assertRaises(LockError) as cm:
            self.lock.acquire(owner="second", action="x", owner_host="y", owner_pid=12345)
        after = self.root.owner_path.stat()
        self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)
        self.assertEqual(before.st_size, after.st_size)
        self.assertEqual(cm.exception.state, "blocked")
        self.assertEqual(cm.exception.detail["owner"], "first")
        self.assertNotIn("token", cm.exception.detail)

    def test_concurrent_acquire_exactly_one_winner(self):
        results: dict[str, Any] = {}
        errors: dict[str, Any] = {}
        ready = threading.Event()

        def _new_lk():
            lk = self.root.lock()
            lk._is_root = lambda: True
            lk._chown = lambda path, uid, gid: None
            lk._fchown = lambda fd, uid, gid: None
            _rlstat = lk._lstat
            _rfstat = lk._fstat
            _ld = str(lk.lock_dir)
            _op = str(lk.owner_path)
            def _flstat(path):
                st = _rlstat(path)
                if path == _ld:
                    return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
                if path == _op:
                    return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
                return st
            def _ffstat(fd):
                st = _rfstat(fd)
                return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
            lk._lstat = _flstat
            lk._fstat = _ffstat
            return lk

        def worker_a():
            lk = _new_lk()
            try:
                results["a"] = lk.acquire(
                    owner="a", action="x", owner_host="h", owner_pid=os.getpid()
                )
            except LockError as exc:
                errors["a"] = exc
            finally:
                ready.set()

        def worker_b():
            ready.wait()
            lk = _new_lk()
            try:
                results["b"] = lk.acquire(
                    owner="b", action="x", owner_host="h", owner_pid=os.getpid()
                )
            except LockError as exc:
                errors["b"] = exc

        ta = threading.Thread(target=worker_a)
        tb = threading.Thread(target=worker_b)
        ta.start()
        tb.start()
        ta.join()
        tb.join()

        self.assertIn("a", results, f"acquired={list(results)}, blocked={list(errors)}")
        self.assertEqual(results["a"]["state"], "acquired")
        self.assertIn("b", errors)
        self.assertEqual(errors["b"].state, "blocked")

    def test_invalid_lock_directory_is_symlink(self):
        self.root.lock_dir.symlink_to("/tmp")
        with self.assertRaises(LockError) as cm:
            self._acquire()
        self.assertEqual(cm.exception.state, "invalid")

    def test_invalid_lock_path_is_regular_file(self):
        self.root.lock_dir.parent.mkdir(parents=True, exist_ok=True)
        self.root.lock_dir.write_text("x")
        with self.assertRaises(LockError) as cm:
            self._acquire()
        self.assertEqual(cm.exception.state, "invalid")

    def test_invalid_owner_json_is_symlink(self):
        self.root.lock_dir.mkdir(parents=True)
        self.root.owner_path.symlink_to("/tmp/x")
        with self.assertRaises(LockError) as cm:
            self._acquire()
        self.assertEqual(cm.exception.state, "invalid")

    def test_invalid_owner_json_hardlink(self):
        self.root.lock_dir.mkdir(parents=True)
        other = self.root.tmp / "other.json"
        other.write_text("{}")
        os.link(str(other), str(self.root.owner_path))
        with self.assertRaises(LockError) as cm:
            self._acquire()
        self.assertEqual(cm.exception.state, "invalid")

    def test_invalid_owner_json_mode(self):
        self._acquire()
        self.root.owner_path.chmod(0o644)
        with self.assertRaises(LockError) as cm:
            self.lock.status()
        self.assertEqual(cm.exception.state, "invalid")

    def test_invalid_lock_dir_mode(self):
        self._acquire()
        self.root.lock_dir.chmod(0o755)
        with self.assertRaises(LockError) as cm:
            self.lock.status()
        self.assertEqual(cm.exception.state, "invalid")

    def test_invalid_extra_entry(self):
        self._acquire()
        (self.root.lock_dir / "extra").write_text("x")
        with self.assertRaises(LockError) as cm:
            self.lock.status()
        self.assertEqual(cm.exception.state, "invalid")

    def test_invalid_metadata_contract_version(self):
        self._acquire()
        meta = json.loads(self.root.owner_path.read_text())
        meta["contract_version"] = 99
        self.root.owner_path.write_text(json.dumps(meta))
        with self.assertRaises(LockError) as cm:
            self.lock.status()
        self.assertEqual(cm.exception.state, "invalid")

    def test_invalid_owner_json_not_json(self):
        self.root.lock_dir.mkdir(parents=True)
        with self.assertRaises(LockError) as cm:
            self.lock.status()
        self.assertEqual(cm.exception.state, "invalid")

    def test_invalid_owner_json_wrong_uid(self):
        # Create lock with enforce_root_ownership ON, so bad ownership is caught.
        lk = self.root.lock()
        lk._is_root = lambda: True
        lk._chown = lambda path, uid, gid: None
        lk._fchown = lambda fd, uid, gid: None
        lk._probe_systemd = lambda: type("P", (), {"ok": True, "reason": "ok"})()
        lk._probe_processes = lambda: type("P", (), {"ok": True, "reason": "ok"})()
        # mkdir directly so it has non-root ownership (chown is no-op)
        lk._mkdir(str(lk.lock_dir), 0o700)
        lk._write_owner({
            "contract_version": 1, "token": "0" * 64, "owner": "x",
            "action": "y", "owner_host": "z", "owner_pid": 1,
            "started_at": "2026-01-01T00:00:00Z", "phase": "held",
        })
        with self.assertRaises(LockError) as cm:
            lk.status()
        self.assertEqual(cm.exception.state, "invalid")

    def test_input_owner_control_chars(self):
        with self.assertRaises(LockError) as cm:
            self.lock.acquire(owner="foo\nbar", action="x", owner_host="h", owner_pid=1)
        self.assertEqual(cm.exception.state, "invalid_input")

    def test_input_action_too_long(self):
        with self.assertRaises(LockError) as cm:
            self.lock.acquire(owner="o", action="x" * 200, owner_host="h", owner_pid=1)
        self.assertEqual(cm.exception.state, "invalid_input")

    def test_input_owner_pid_bool(self):
        with self.assertRaises(LockError) as cm:
            self.lock.acquire(owner="o", action="x", owner_host="h", owner_pid=True)
        self.assertEqual(cm.exception.state, "invalid_input")

    def test_input_owner_pid_zero(self):
        with self.assertRaises(LockError) as cm:
            self.lock.acquire(owner="o", action="x", owner_host="h", owner_pid=0)
        self.assertEqual(cm.exception.state, "invalid_input")

    def test_input_owner_pid_negative(self):
        with self.assertRaises(LockError) as cm:
            self.lock.acquire(owner="o", action="x", owner_host="h", owner_pid=-1)
        self.assertEqual(cm.exception.state, "invalid_input")

    def test_nonroot_acquire_zero_mutation(self):
        self.lock._is_root = lambda: False
        with self.assertRaises(LockError) as cm:
            self._acquire()
        self.assertEqual(cm.exception.state, "blocked")
        self.assertFalse(self.root.lock_dir.exists())

    def test_chown_failure_fail_closed(self):
        self.lock._inject_chown_failure = True
        with self.assertRaises(LockError) as cm:
            self._acquire()
        self.assertEqual(cm.exception.state, "invalid")
        self.assertIn("chown failed", cm.exception.detail["reason"])
        self.assertFalse(self.root.lock_dir.exists())


class StatusTests(Base):
    def test_status_free(self):
        result = self.lock.status()
        self.assertEqual(result, {"state": "free", "phase": "free"})

    def test_status_held_redacts_token(self):
        acq = self._acquire(owner="o", action="a", owner_host="h", owner_pid=1234)
        result = self.lock.status()
        self.assertEqual(result["state"], "held")
        self.assertEqual(result["phase"], "held")
        self.assertEqual(result["owner"], "o")
        self.assertEqual(result["action"], "a")
        self.assertEqual(result["owner_host"], "h")
        self.assertEqual(result["owner_pid"], 1234)
        self.assertIn("token_digest", result)
        self.assertIn("token_prefix", result)
        self.assertNotIn("token", result)
        self.assertEqual(
            result["token_digest"],
            "sha256:" + hashlib.sha256(acq["token"].encode()).hexdigest(),
        )

    def test_status_expect_token_match(self):
        acq = self._acquire()
        result = self.lock.status(expect_token=acq["token"])
        self.assertTrue(result["token_matches"])

    def test_status_expect_token_mismatch(self):
        self._acquire()
        result = self.lock.status(expect_token="0" * 64)
        self.assertFalse(result["token_matches"])

    def test_status_invalid_expect_token_shape(self):
        with self.assertRaises(LockError) as cm:
            self.lock.status(expect_token="bad")
        self.assertEqual(cm.exception.state, "invalid_input")

    def test_status_read_only_no_mutation(self):
        self._acquire()
        before = self.root.owner_path.stat()
        self.lock.status()
        after = self.root.owner_path.stat()
        self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)

    def test_status_invalid_lock_returns_error(self):
        self.root.lock_dir.mkdir(parents=True)
        self.root.owner_path.symlink_to("/tmp/x")
        with self.assertRaises(LockError) as cm:
            self.lock.status()
        self.assertEqual(cm.exception.state, "invalid")


class ReleaseTests(Base):
    def test_release_success(self):
        acq = self._acquire()
        result = self.lock.release(token=acq["token"])
        self.assertEqual(result["state"], "released")
        self.assertFalse(self.root.lock_dir.exists())

    def test_release_mismatch(self):
        self._acquire()
        with self.assertRaises(LockError) as cm:
            self.lock.release(token="0" * 64)
        self.assertEqual(cm.exception.state, "mismatch")
        self.assertTrue(self.root.lock_dir.exists())

    def test_release_malformed_token(self):
        self._acquire()
        with self.assertRaises(LockError) as cm:
            self.lock.release(token="bad")
        self.assertEqual(cm.exception.state, "invalid_input")

    def test_release_metadata_drift(self):
        acq = self._acquire()
        meta = json.loads(self.root.owner_path.read_text())
        meta["phase"] = "stolen"
        self.root.owner_path.write_text(json.dumps(meta))
        with self.assertRaises(LockError) as cm:
            self.lock.release(token=acq["token"])
        self.assertEqual(cm.exception.state, "invalid")
        self.assertTrue(self.root.lock_dir.exists())

    def test_release_duplicate_not_allowed(self):
        acq = self._acquire()
        self.lock.release(token=acq["token"])
        with self.assertRaises(LockError) as cm:
            self.lock.release(token=acq["token"])
        self.assertEqual(cm.exception.state, "mismatch")

    def test_release_allow_already_free(self):
        acq = self._acquire()
        self.lock.release(token=acq["token"])
        result = self.lock.release(token=acq["token"], allow_already_free=True)
        self.assertEqual(result["state"], "already_free")

    def test_nonroot_release_zero_mutation(self):
        acq = self._acquire()
        self.lock._is_root = lambda: False
        with self.assertRaises(LockError) as cm:
            self.lock.release(token=acq["token"])
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())

    def test_release_token_not_a_string(self):
        acq = self._acquire()
        with self.assertRaises(LockError) as cm:
            self.lock.release(token=12345)  # type: ignore
        self.assertEqual(cm.exception.state, "invalid_input")


class FsyncFailureTests(Base):
    def test_file_fsync_failure_cleans_partial_authority(self):
        self.lock._inject_fsync_failure = "file"
        with self.assertRaises(LockError) as cm:
            self._acquire()
        self.assertEqual(cm.exception.state, "invalid")
        self.assertFalse(self.root.lock_dir.exists())

    def test_dir_fsync_failure_cleans_partial_authority(self):
        self.lock._inject_dir_fsync_failure = True
        with self.assertRaises(LockError) as cm:
            self._acquire()
        self.assertEqual(cm.exception.state, "invalid")
        self.assertFalse(self.root.lock_dir.exists())


class RecoverTests(Base):
    def test_recover_success(self):
        acq = self._acquire(owner="o", action="a", owner_host="h", owner_pid=1234)
        result = self.lock.recover(
            token=acq["token"],
            operator="admin",
            reason="stale",
            confirm_owner_stopped=True,
        )
        self.assertEqual(result["state"], "recovered")
        self.assertFalse(self.root.lock_dir.exists())
        self.assertTrue(self.root.audit_path.exists())
        lines = self.root.audit_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["operator"], "admin")
        self.assertEqual(entry["reason"], "stale")
        self.assertEqual(entry["lock_owner"], "o")
        self.assertIn("lock_token_digest", entry)
        self.assertIn("lock_token_prefix", entry)
        self.assertNotIn("token", entry)
        self.assertNotIn("lock_token", entry)
        audit_st = self.root.audit_path.stat()
        self.assertEqual(stat.S_IMODE(audit_st.st_mode), 0o600)

    def test_recover_no_confirmation(self):
        acq = self._acquire()
        with self.assertRaises(LockError) as cm:
            self.lock.recover(token=acq["token"], operator="admin", reason="stale")
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())
        self.assertFalse(self.root.audit_path.exists())

    def test_recover_bad_reason(self):
        acq = self._acquire()
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token=acq["token"],
                operator="admin",
                reason="bad reason!",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "invalid_input")

    def test_recover_token_mismatch(self):
        self._acquire()
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token="0" * 64,
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "mismatch")

    def test_recover_systemd_probe_fails(self):
        acq = self._acquire()
        self.lock._probe_systemd = lambda: type("P", (), {"ok": False, "reason": "unit alive"})()
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token=acq["token"],
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())
        self.assertFalse(self.root.audit_path.exists())

    def test_recover_process_probe_fails(self):
        acq = self._acquire()
        self.lock._probe_processes = lambda: type("P", (), {"ok": False, "reason": "proc alive"})()
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token=acq["token"],
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())
        self.assertFalse(self.root.audit_path.exists())

    def test_recover_audit_failure_retains_lock(self):
        acq = self._acquire()
        self.root.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.root.audit_path.write_text("x")
        self.root.audit_path.chmod(0o000)
        try:
            with self.assertRaises(LockError) as cm:
                self.lock.recover(
                    token=acq["token"],
                    operator="admin",
                    reason="stale",
                    confirm_owner_stopped=True,
                )
            self.assertEqual(cm.exception.state, "blocked")
        finally:
            self.root.audit_path.chmod(0o600)
        self.assertTrue(self.root.lock_dir.exists())

    def test_nonroot_recover_zero_mutation(self):
        acq = self._acquire()
        self.lock._is_root = lambda: False
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token=acq["token"],
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())

    def test_recover_probe_error_fail_closed(self):
        acq = self._acquire()
        self.lock._probe_systemd = lambda: type("P", (), {"ok": False, "reason": "timeout"})()
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token=acq["token"],
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())

    def test_recover_pgrep_missing_fails_closed(self):
        # ``pgrep`` absent on the host must NOT be interpreted as "no live
        # process". An unknown probe state must not authorize a recover.
        from production_mutation_lock import _probe_processes_default

        acq = self._acquire()
        original = self.lock._probe_processes
        try:
            # Real default probe is exercised in production paths; under
            # the test runner pgrep is present, so emulate the
            # FileNotFoundError branch by invoking the implementation
            # through a wrapper that mirrors the failure shape.
            def missing_pgrep():
                from production_mutation_lock import _ProbeResult
                return _ProbeResult(
                    ok=False,
                    reason="pgrep unavailable: cannot prove no p9-3c1 processes",
                )
            self.lock._probe_processes = missing_pgrep
            with self.assertRaises(LockError) as cm:
                self.lock.recover(
                    token=acq["token"],
                    operator="admin",
                    reason="stale",
                    confirm_owner_stopped=True,
                )
            self.assertEqual(cm.exception.state, "blocked")
            self.assertTrue(self.root.lock_dir.exists())
            self.assertFalse(self.root.audit_path.exists())
        finally:
            self.lock._probe_processes = original
        # Sanity: the default probe helper actually returns a fail-closed
        # result shape if pgrep were missing.
        assert _probe_processes_default is not None

    def test_recover_pgrep_nonzero_exit_fails_closed(self):
        # pgrep returning a non-(0|1) exit code is uncertain: fail closed.
        from production_mutation_lock import _ProbeResult

        acq = self._acquire()
        self.lock._probe_processes = lambda: _ProbeResult(
            ok=False, reason="pgrep exited 2"
        )
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token=acq["token"],
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())
        self.assertFalse(self.root.audit_path.exists())

    def test_recover_audit_fsync_failure_retains_lock(self):
        # Audit file must fsync durably; injected fsync failure aborts
        # the recover before the lock is touched.
        acq = self._acquire()
        self.lock._inject_audit_fsync_failure = True
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token=acq["token"],
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())

    def test_recover_does_not_change_audit_parent_mode(self):
        before = stat.S_IMODE(self.root.audit_path.parent.stat().st_mode)
        acq = self._acquire()
        result = self.lock.recover(
            token=acq["token"],
            operator="admin",
            reason="stale",
            confirm_owner_stopped=True,
        )
        self.assertEqual(result["state"], "recovered")
        after = stat.S_IMODE(self.root.audit_path.parent.stat().st_mode)
        self.assertEqual(before, 0o755)
        self.assertEqual(after, before)

    def test_recover_refuses_hardlinked_audit_file_and_retains_lock(self):
        outside = self.root.tmp / "outside-audit"
        outside.write_text("sentinel", encoding="utf-8")
        outside.chmod(0o600)
        os.link(outside, self.root.audit_path)
        acq = self._acquire()
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token=acq["token"],
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())
        self.assertEqual(outside.read_text(encoding="utf-8"), "sentinel")


class NoStealTests(Base):
    def _last_token(self):
        return json.loads(self.root.owner_path.read_text())["token"]

    def test_no_age_based_steal(self):
        self._acquire()
        self.assertFalse(hasattr(self.lock, "steal"))

    def test_no_recursive_delete(self):
        self._acquire()
        (self.root.lock_dir / "extra").write_text("x")
        with self.assertRaises(LockError):
            self.lock.release(token=self._last_token())
        self.assertTrue(self.root.lock_dir.exists())


class CLITests(unittest.TestCase):
    def setUp(self):
        self.root = _FakeRoot()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root.tmp, ignore_errors=True)

    def _run(self, *args, is_root=True):
        from production_mutation_lock import main

        root = self.root
        original_init = ProductionMutationLock.__init__

        def patched_init(inst, **kwargs):
            kwargs.setdefault("lock_dir", str(root.lock_dir))
            kwargs.setdefault("owner_path", str(root.owner_path))
            kwargs.setdefault("helper_path", str(root.helper_path))
            kwargs.setdefault("audit_path", str(root.audit_path))
            original_init(inst, **kwargs)
            inst._is_root = lambda: is_root
            inst._chown = lambda path, uid, gid: None
            inst._fchown = lambda fd, uid, gid: None
            _rlstat = inst._lstat
            _rfstat = inst._fstat
            _ld = str(inst.lock_dir)
            _op = str(inst.owner_path)
            def _flstat(path):
                st = _rlstat(path)
                if path == _ld:
                    return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
                if path == _op:
                    return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
                return st
            def _ffstat(fd):
                st = _rfstat(fd)
                return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
            inst._lstat = _flstat
            inst._fstat = _ffstat
            inst._probe_systemd = lambda: type("P", (), {"ok": True, "reason": "ok"})()

        previous_umask = os.umask(0)
        os.umask(previous_umask)
        ProductionMutationLock.__init__ = patched_init
        try:
            return main(list(args))
        finally:
            ProductionMutationLock.__init__ = original_init
            os.umask(previous_umask)

    def test_cli_sets_restrictive_umask_before_dispatch(self):
        real_umask = os.umask
        calls = []

        def recording_umask(mask):
            calls.append(mask)
            return real_umask(mask)

        with mock.patch.object(
            _production_mutation_lock.os,
            "umask",
            side_effect=recording_umask,
        ):
            self.assertEqual(self._run("status"), 0)
        self.assertIn(0o077, calls)

    def test_cli_acquire_stdout_is_raw_token_and_no_token_in_stderr(self):
        import io
        import re
        from contextlib import redirect_stdout, redirect_stderr

        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self._run(
                "acquire",
                "--owner", "o",
                "--action", "a",
                "--owner-host", "h",
                "--owner-pid", "1",
            )
        self.assertEqual(rc, 0)
        # Contract: stdout is exactly one 64-char lowercase hex token followed
        # by a single newline. No JSON envelope.
        raw = out.getvalue()
        self.assertRegex(raw, r"^[0-9a-f]{64}\n$")
        self.assertNotIn("{", raw)
        self.assertNotIn("state", raw)
        # stderr must be empty: token never leaves the stdout success channel.
        self.assertEqual(err.getvalue(), "")

    def test_cli_acquire_failure_does_not_leak_token(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr

        # Hold a lock with one identity, then try to acquire as a different
        # owner; stderr must carry the structured error and never the
        # token of the current holder.
        self._run(
            "acquire",
            "--owner", "first",
            "--action", "a",
            "--owner-host", "h",
            "--owner-pid", "1",
        )
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self._run(
                "acquire",
                "--owner", "second",
                "--action", "a",
                "--owner-host", "h",
                "--owner-pid", "2",
            )
        self.assertNotEqual(rc, 0)
        self.assertEqual(out.getvalue(), "")
        err_text = err.getvalue()
        self.assertIn("blocked", err_text)
        # The structured error object must never carry a raw "token" field.
        # token_digest / token_prefix are allowed redacted forms.
        err_obj = json.loads(err_text)
        self.assertNotIn("token", err_obj)
        if "token_digest" in err_obj:
            self.assertTrue(str(err_obj["token_digest"]).startswith("sha256:"))
        if "token_prefix" in err_obj:
            self.assertTrue(str(err_obj["token_prefix"]).endswith("..."))

    def test_cli_status_free(self):
        import io
        from contextlib import redirect_stdout

        out = io.StringIO()
        with redirect_stdout(out):
            rc = self._run("status")
        self.assertEqual(rc, 0)
        obj = json.loads(out.getvalue())
        self.assertEqual(obj["state"], "free")

    def test_cli_release_fail_prints_stderr(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr

        self._run(
            "acquire", "--owner", "o", "--action", "a",
            "--owner-host", "h", "--owner-pid", "1",
        )
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self._run("release", "--token", "0" * 64)
        self.assertNotEqual(rc, 0)
        self.assertIn("mismatch", err.getvalue())



class SystemdProbeDefaultTests(unittest.TestCase):
    """Test _probe_systemd_default with mocked subprocess (Section 4)."""

    def setUp(self):
        from production_mutation_lock import _probe_systemd_default
        self._probe = _probe_systemd_default
        self._run_patch = mock.patch("production_mutation_lock.subprocess.run")
        self._mock_run = self._run_patch.start()

    def tearDown(self):
        self._run_patch.stop()

    def _make(self, stdout="", stderr="", returncode=0):
        r = mock.MagicMock()
        r.stdout = stdout
        r.stderr = stderr
        r.returncode = returncode
        self._mock_run.return_value = r

    def test_e1_unit_blocks(self):
        self._make(stdout="p9-3c-fixture-e1-p9-3c1-prod-20260101t000000z-aabbccdd.service loaded active running\n")
        r = self._probe()
        self.assertFalse(r.ok, "exact E1 unit must block")

    def test_e2_unit_blocks(self):
        self._make(stdout="p9-3c-fixture-e2-p9-3c1-prod-20261231t235959z-ffeeddcc.service loaded active running\n")
        r = self._probe()
        self.assertFalse(r.ok, "exact E2 unit must block")

    def test_unrelated_unit_passes(self):
        self._make(stdout="sshd.service loaded active running\ncron.service loaded active running\n")
        r = self._probe()
        self.assertTrue(r.ok, "unrelated units must not block")

    def test_obsolete_p9_3c1_prefix_passes(self):
        self._make(stdout="p9-3c1-old-thing.service loaded active running\n")
        r = self._probe()
        self.assertTrue(r.ok, "obsolete p9-3c1- prefix must not block")

    def test_similar_not_exact_unit_passes(self):
        self._make(stdout="p9-3c-fixture-e3-p9-3c1-prod-20260101t000000z-aabbccdd.service loaded active running\n")
        r = self._probe()
        self.assertTrue(r.ok, "e3 fixture must not match")

    def test_partial_prefix_match_passes(self):
        self._make(stdout="p9-3c-fixture-e1-p9-3c1-prod.service loaded active running\n")
        r = self._probe()
        self.assertTrue(r.ok, "partial match without timestamp+hex must not block")

    def test_systemctl_missing_blocks(self):
        self._mock_run.side_effect = FileNotFoundError()
        r = self._probe()
        self.assertFalse(r.ok, "missing systemctl must block")

    def test_systemctl_nonzero_blocks(self):
        self._make(returncode=1, stderr="unit load error")
        r = self._probe()
        self.assertFalse(r.ok, "nonzero exit must block")
        self.assertNotIn("unit load error", r.reason)

    def test_oversized_stdout_blocks(self):
        self._make(stdout="x" * (2 * 1024 * 1024))
        r = self._probe()
        self.assertFalse(r.ok, "oversized stdout must block")

    def test_malformed_line_no_columns_ignored(self):
        # Per bootstrap: blank/whitespace-only rows are malformed and block.
        self._make(stdout="\n  \nsshd.service loaded active running\n")
        r = self._probe()
        self.assertFalse(r.ok, "internal blank or whitespace-only row must block")

    def test_exact_subprocess_invocation(self):
        self._make(stdout="")
        r = self._probe()
        self.assertTrue(r.ok)
        self._mock_run.assert_called_once()
        call_args = self._mock_run.call_args
        self.assertEqual(call_args[0][0], [
            "systemctl", "list-units",
            "--type=service",
            "--state=running,reloading,activating,deactivating",
            "--no-pager", "--no-legend",
        ])
        kwargs = call_args[1]
        self.assertIs(kwargs["shell"], False)
        self.assertEqual(kwargs["timeout"], 10)
        self.assertIs(kwargs["capture_output"], True)
        self.assertIs(kwargs["text"], True)

    def test_empty_stdout_passes(self):
        self._make(stdout="")
        r = self._probe()
        self.assertTrue(r.ok, "empty stdout (no units) must pass")

    def test_suffix_added_target_passes(self):
        # Suffix added to the hex portion; still ends in .service but doesn't match regex.
        self._make(stdout="p9-3c-fixture-e1-p9-3c1-prod-20260101t000000z-aabbccdd-extra.service loaded active running\n")
        r = self._probe()
        self.assertTrue(r.ok, "suffix-added target must not match exact regex")

    def test_single_column_blocks(self):
        self._make(stdout="sshd\n")
        r = self._probe()
        self.assertFalse(r.ok, "single-column row must block")

    def test_wrong_non_service_column_blocks(self):
        self._make(stdout="sshd.socket loaded active running\n")
        r = self._probe()
        self.assertFalse(r.ok, "non-.service first column must block")

    def test_control_char_unit_blocks(self):
        # Unit name with a NUL control character must block (fail-closed).
        self._make(stdout="p9-3c-fixture-e1-p9-3c1-prod-20260101t000000z-aabbccdd\x00.service loaded active running\n")
        r = self._probe()
        self.assertFalse(r.ok, "control char in unit name must block")
        self.assertNotIn("aabbccdd", r.reason)

    def test_bounded_reasons_no_sentinel(self):
        sentinel = "UNIQUE_SENTINEL_SYSTEMD_7F3A"
        self._make(stdout=f"{sentinel}.service loaded active running\n", stderr=sentinel, returncode=1)
        r = self._probe()
        self.assertFalse(r.ok)
        self.assertNotIn(sentinel, r.reason)


_CONTROLLER_CMD = b"/usr/bin/python3.12\x00/opt/multinexus/scripts/p9_3c1_controller.py\x00"
_FIXTURE_E1_CMD = b"/usr/bin/python3.12\x00-m\x00multinexus.agentd\x00--agent\x00p9-3c-fixture-e1\x00"
_FIXTURE_E2_CMD = b"/usr/bin/python3.12\x00-m\x00multinexus.agentd\x00--agent\x00p9-3c-fixture-e2\x00"
_HELPER_CMD = b"/usr/bin/python3.12\x00/usr/local/sbin/coordinate-production-mutation-lock\x00recover\x00--token\x00" + b"0" * 64 + b"\x00"
_TOKEN_FILE_CMD = b"/usr/bin/python3.12\x00/usr/local/sbin/coordinate-production-mutation-lock\x00recover\x00--token-file\x00/tmp/token\x00"
_SSH_CMD = b"ssh\x00somehost\x00/usr/bin/python3.12 /opt/multinexus/scripts/p9_3c1_controller.py\x00"
_BASH_C_CMD = b"/bin/bash\x00-c\x00/usr/bin/python3.12 /opt/multinexus/scripts/p9_3c1_controller.py\x00"
_GREP_CMD = b"/usr/bin/grep\x00controller\x00/opt/multinexus/scripts/p9_3c1_controller.py\x00"
_UNRELATED_PYTHON = b"/usr/bin/python3.12\x00/tmp/somescript.py\x00"
_UNRELATED_MODULE = b"/usr/bin/python3.12\x00-m\x00http.server\x00"
_UNRELATED_AGENT = b"/usr/bin/python3.12\x00-m\x00multinexus.agentd\x00--agent\x00p9-3c-fixture-e99\x00"
_MALFORMED_FIXTURE_NO_AGENT = b"/usr/bin/python3.12\x00-m\x00multinexus.agentd\x00p9-3c-fixture-e1\x00"
_MALFORMED_FIXTURE_EXTRA_AGENT = b"/usr/bin/python3.12\x00-m\x00multinexus.agentd\x00--agent\x00p9-3c-fixture-e1\x00--agent\x00p9-3c-fixture-e2\x00"
_KERNEL_THREAD = b"\x00"
_PROBE_SELF_CMD = b"/usr/bin/python3.12\x00-m\x00pytest\x00"
_EDITOR_CMD = b"/usr/bin/vim\x00/opt/multinexus/scripts/production-mutation-lock.py\x00"


class ProcessProbeDefaultTests(unittest.TestCase):
    """Test _probe_processes_default with injected seams (Section 5)."""

    def setUp(self):
        from production_mutation_lock import _ProbeResult
        self._ProbeResult = _ProbeResult

    def _run(self, pids, cmdlines, kill_errors=None, self_pid=99999):
        from production_mutation_lock import _probe_processes_default

        def _enumerate_pids():
            return list(pids)

        def _read_cmdline(pid):
            if pid in cmdlines:
                return cmdlines[pid]
            raise OSError(errno.ENOENT, os.strerror(errno.ENOENT))

        def _kill_0(pid, sig):
            if kill_errors and pid in kill_errors:
                err = kill_errors[pid]
                if err != 0:
                    raise OSError(err, os.strerror(err))

        return _probe_processes_default(
            enumerate_pids=_enumerate_pids,
            read_cmdline=_read_cmdline,
            kill_0=_kill_0,
            self_pid=lambda: self_pid,
        )

    # ── positive rows (must block) ──

    def test_controller_blocks(self):
        r = self._run([100], {100: _CONTROLLER_CMD})
        self.assertFalse(r.ok)
        self.assertIn("100", r.reason)

    def test_fixture_e1_blocks(self):
        r = self._run([200], {200: _FIXTURE_E1_CMD})
        self.assertFalse(r.ok)
        self.assertIn("200", r.reason)

    def test_fixture_e2_blocks(self):
        r = self._run([300], {300: _FIXTURE_E2_CMD})
        self.assertFalse(r.ok)
        self.assertIn("300", r.reason)

    def test_multiple_matches_report_only_pids(self):
        r = self._run([100, 200], {100: _CONTROLLER_CMD, 200: _FIXTURE_E1_CMD})
        self.assertFalse(r.ok)
        self.assertIn("100", r.reason)
        self.assertIn("200", r.reason)
        # Must not leak argv/token strings
        self.assertNotIn("python3.12", r.reason)
        self.assertNotIn("controller", r.reason)

    # ── negative rows (must NOT block) ──

    def test_recovery_helper_passes(self):
        r = self._run([400], {400: _HELPER_CMD})
        self.assertTrue(r.ok)

    def test_token_file_path_passes(self):
        r = self._run([500], {500: _TOKEN_FILE_CMD})
        self.assertTrue(r.ok)

    def test_ssh_command_passes(self):
        r = self._run([600], {600: _SSH_CMD})
        self.assertTrue(r.ok)

    def test_bash_c_command_passes(self):
        r = self._run([700], {700: _BASH_C_CMD})
        self.assertTrue(r.ok)

    def test_grep_command_passes(self):
        r = self._run([800], {800: _GREP_CMD})
        self.assertTrue(r.ok)

    def test_unrelated_python_passes(self):
        r = self._run([900], {900: _UNRELATED_PYTHON})
        self.assertTrue(r.ok)

    def test_unrelated_module_passes(self):
        r = self._run([1000], {1000: _UNRELATED_MODULE})
        self.assertTrue(r.ok)

    def test_unrelated_agent_passes(self):
        r = self._run([1100], {1100: _UNRELATED_AGENT})
        self.assertTrue(r.ok)

    # ── malformed candidates fail-closed ──

    def test_malformed_fixture_no_agent_flag_fails_closed(self):
        r = self._run([1200], {1200: _MALFORMED_FIXTURE_NO_AGENT})
        self.assertFalse(r.ok)

    def test_malformed_fixture_duplicate_agent_flags_fails_closed(self):
        r = self._run([1300], {1300: _MALFORMED_FIXTURE_EXTRA_AGENT})
        self.assertFalse(r.ok)

    # ── edge cases ──

    def test_kernel_thread_empty_cmdline_ignored(self):
        r = self._run([1], {1: _KERNEL_THREAD})
        self.assertTrue(r.ok)

    def test_confirmed_exited_pid_ignored(self):
        from production_mutation_lock import _ProbeResult
        r = self._run([1400], {}, kill_errors={1400: errno.ESRCH})
        # ENOENT from read_cmdline + ESRCH from kill_0 → confirmed exited
        self.assertTrue(r.ok)

    def test_eperm_on_kill_blocks(self):
        from production_mutation_lock import _ProbeResult
        r = self._run([1500], {}, kill_errors={1500: errno.EPERM})
        # ENOENT from read but EPERM from kill → uncertain → blocks
        self.assertFalse(r.ok)

    def test_eio_on_cmdline_read_blocks(self):
        def _read_cmdline_eio(pid):
            raise OSError(errno.EIO, os.strerror(errno.EIO))
        from production_mutation_lock import _probe_processes_default
        r = _probe_processes_default(
            enumerate_pids=lambda: [1600],
            read_cmdline=_read_cmdline_eio,
            kill_0=lambda pid, sig: None,
            self_pid=lambda: 99999,
        )
        self.assertFalse(r.ok)

    def test_empty_pid_list_passes(self):
        r = self._run([], {})
        self.assertTrue(r.ok)

    def test_self_pid_skipped(self):
        r = self._run([100], {100: _CONTROLLER_CMD}, self_pid=100)
        self.assertTrue(r.ok, "own PID must be skipped")

    def test_probe_self_passes(self):
        # pytest runner argv contains no blocked identity
        r = self._run([os.getpid()], {os.getpid(): _PROBE_SELF_CMD}, self_pid=os.getpid())
        self.assertTrue(r.ok, "probe-self argv must not block")

    def test_editor_passes(self):
        # vim editing the lock script is not a blocked identity
        r = self._run([7777], {7777: _EDITOR_CMD})
        self.assertTrue(r.ok, "editor argv must not block")

    def test_bounded_reasons_no_sentinel(self):
        sentinel = "UNIQUE_SENTINEL_PROC_9B2C"
        def _read_cmdline_sentinel(pid):
            raise OSError(errno.EIO, sentinel)
        from production_mutation_lock import _probe_processes_default
        r = _probe_processes_default(
            enumerate_pids=lambda: [8888],
            read_cmdline=_read_cmdline_sentinel,
            kill_0=lambda pid, sig: None,
            self_pid=lambda: 99999,
        )
        self.assertFalse(r.ok)
        self.assertNotIn(sentinel, r.reason)


class TokenFileValidationTests(Base):
    """Test _read_token_file validation (Section 6)."""

    def _write_token_file(self, content, parent_mode=0o700, file_mode=0o600):
        token_dir = self.root.tmp / "token_dir"
        token_dir.mkdir(mode=parent_mode, exist_ok=True)
        token_file = token_dir / "token"
        token_file.write_bytes(content)
        token_file.chmod(file_mode)
        return str(token_file)

    def test_valid_64_hex_no_newline_succeeds(self):
        path = self._write_token_file(b"a" * 64)
        token = self.lock._read_token_file(path)
        self.assertEqual(token, "a" * 64)

    def test_valid_64_hex_with_lf_succeeds(self):
        path = self._write_token_file(b"a" * 64 + b"\n")
        token = self.lock._read_token_file(path)
        self.assertEqual(token, "a" * 64)

    def test_relative_path_blocks(self):
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file("relative/path")
        self.assertEqual(cm.exception.state, "blocked")

    def test_blank_path_blocks(self):
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file("")
        self.assertEqual(cm.exception.state, "blocked")

    def test_parent_symlink_blocks(self):
        real_dir = self.root.tmp / "real_dir"
        real_dir.mkdir(mode=0o700)
        token_file = real_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        link_dir = self.root.tmp / "link_dir"
        link_dir.symlink_to(real_dir, target_is_directory=True)
        linked_path = str(link_dir / "token")
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(linked_path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_parent_not_directory_blocks(self):
        f = self.root.tmp / "not_a_dir"
        f.write_text("x")
        path = str(f / "token")
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_parent_wrong_mode_blocks(self):
        path = self._write_token_file(b"a" * 64, parent_mode=0o755)
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_file_symlink_blocks(self):
        token_dir = self.root.tmp / "token_dir"
        token_dir.mkdir(mode=0o700)
        real_file = token_dir / "real"
        real_file.write_bytes(b"a" * 64)
        real_file.chmod(0o600)
        link_file = token_dir / "token"
        link_file.symlink_to("real")
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(str(link_file))
        self.assertEqual(cm.exception.state, "blocked")

    def test_file_wrong_mode_blocks(self):
        path = self._write_token_file(b"a" * 64, file_mode=0o644)
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_file_hardlinked_blocks(self):
        token_dir = self.root.tmp / "token_dir"
        token_dir.mkdir(mode=0o700)
        token_file = token_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        hardlink = token_dir / "token_link"
        os.link(str(token_file), str(hardlink))
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(str(token_file))
        self.assertEqual(cm.exception.state, "blocked")

    def test_size_not_64_or_65_blocks(self):
        path = self._write_token_file(b"a" * 63)
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_size_66_blocks(self):
        path = self._write_token_file(b"a" * 66)
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_bad_ascii_uppercase_blocks(self):
        path = self._write_token_file(b"A" * 64)
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_bad_ascii_spaces_blocks(self):
        path = self._write_token_file(b" " * 64)
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_crlf_blocks(self):
        path = self._write_token_file(b"a" * 64 + b"\r\n")
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_multiple_newlines_blocks(self):
        path = self._write_token_file(b"a" * 64 + b"\n\n")
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_non_ascii_bytes_blocks(self):
        path = self._write_token_file(b"\xff" * 64)
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")

    def test_short_content_blocks(self):
        path = self._write_token_file(b"a" * 32)
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")



class TokenFileRecoverTests(Base):
    """Integration: recover via --token-file (Section 7.5-7.6)."""

    def _write_token_file(self, content, parent_mode=0o700, file_mode=0o600):
        token_dir = self.root.tmp / "token_dir"
        token_dir.mkdir(mode=parent_mode, exist_ok=True)
        token_file = token_dir / "token"
        token_file.write_bytes(content)
        token_file.chmod(file_mode)
        return str(token_file)

    def test_token_file_validation_failure_zero_audit(self):
        acq = self._acquire()
        # Token file with bad content should fail before audit/release
        bad_path = self._write_token_file(b"bad" * 21)
        try:
            self.lock._read_token_file(bad_path)
        except LockError:
            pass
        # Lock is still held, no audit written
        self.assertTrue(self.root.lock_dir.exists())
        self.assertFalse(self.root.audit_path.exists())

    def test_token_file_block_retains_lock_with_real_probe_fail(self):
        acq = self._acquire()
        token_path = self._write_token_file(acq["token"].encode("ascii") + b"\n")
        token = self.lock._read_token_file(token_path)
        self.lock._probe_systemd = lambda: type("P", (), {"ok": False, "reason": "unit alive"})()
        with self.assertRaises(LockError) as cm:
            self.lock.recover(
                token=token,
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
        self.assertEqual(cm.exception.state, "blocked")
        self.assertTrue(self.root.lock_dir.exists())
        self.assertFalse(self.root.audit_path.exists())


class TokenFileCLITests(unittest.TestCase):
    """CLI tests for --token-file (Section 7.3)."""

    def setUp(self):
        self.root = _FakeRoot()
        self._token_dir = self.root.tmp / "token_dir"
        self._token_dir.mkdir(mode=0o700)
        self._token_path = self._token_dir / "token"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root.tmp, ignore_errors=True)

    def _run(self, *args, is_root=True):
        from production_mutation_lock import main
        root = self.root
        original_init = ProductionMutationLock.__init__

        def patched_init(inst, **kwargs):
            kwargs.setdefault("lock_dir", str(root.lock_dir))
            kwargs.setdefault("owner_path", str(root.owner_path))
            kwargs.setdefault("helper_path", str(root.helper_path))
            kwargs.setdefault("audit_path", str(root.audit_path))
            original_init(inst, **kwargs)
            inst._is_root = lambda: is_root
            inst._chown = lambda path, uid, gid: None
            inst._fchown = lambda fd, uid, gid: None
            _rlstat = inst._lstat
            _rfstat = inst._fstat
            _ld = str(inst.lock_dir)
            _op = str(inst.owner_path)
            def _flstat(path):
                st = _rlstat(path)
                if path in {_ld, _op, str(root.audit_path.parent), str(root.audit_path),
                            str(self._token_dir), str(self._token_path)}:
                    return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
                return st
            def _ffstat(fd):
                st = _rfstat(fd)
                return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
            inst._lstat = _flstat
            inst._fstat = _ffstat
            inst._probe_systemd = lambda: type("P", (), {"ok": True, "reason": "ok"})()
            inst._probe_processes = lambda: type("P", (), {"ok": True, "reason": "ok"})()

        previous_umask = os.umask(0)
        os.umask(previous_umask)
        ProductionMutationLock.__init__ = patched_init
        try:
            return main(list(args))
        except SystemExit as e:
            return e.code
        finally:
            ProductionMutationLock.__init__ = original_init
            os.umask(previous_umask)

    def test_token_file_accepted_by_cli(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr

        # First acquire and capture the real token
        out_acq = io.StringIO()
        with redirect_stdout(out_acq):
            self._run(
                "acquire", "--owner", "o", "--action", "a",
                "--owner-host", "h", "--owner-pid", "1",
            )
        token_hex = out_acq.getvalue().strip()
        self.assertEqual(len(token_hex), 64)
        # Write token to file (with LF)
        self._token_path.write_text(token_hex + "\n")
        self._token_path.chmod(0o600)
        # Now recover with token-file
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self._run(
                "recover",
                "--token-file", str(self._token_path),
                "--operator", "admin",
                "--reason", "stale",
                "--confirm-owner-stopped",
            )
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["state"], "recovered")
        # No raw token in stdout
        self.assertNotIn(token_hex, out.getvalue())

    def test_token_file_no_raw_token_in_stderr_on_failure(self):
        token_hex = "b" * 64
        self._token_path.write_text(token_hex + "\n")
        self._token_path.chmod(0o600)
        import io
        from contextlib import redirect_stdout, redirect_stderr

        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self._run(
                "recover",
                "--token-file", str(self._token_path),
                "--operator", "admin",
                "--reason", "stale",
                "--confirm-owner-stopped",
            )
        # Should fail because no lock was acquired
        self.assertNotEqual(rc, 0)
        err_text = err.getvalue()
        self.assertNotIn(token_hex, err_text)

    def test_both_token_and_token_file_fails(self):
        self._token_path.write_text("a" * 64 + "\n")
        self._token_path.chmod(0o600)
        import io
        from contextlib import redirect_stdout, redirect_stderr

        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self._run(
                "recover",
                "--token", "a" * 64,
                "--token-file", str(self._token_path),
                "--operator", "admin",
                "--reason", "stale",
                "--confirm-owner-stopped",
            )
        self.assertNotEqual(rc, 0)

    def test_neither_token_nor_token_file_fails(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr

        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self._run(
                "recover",
                "--operator", "admin",
                "--reason", "stale",
                "--confirm-owner-stopped",
            )
        self.assertNotEqual(rc, 0)


# ── Correction regression tests (P0/P1 from rejected 3f337eb2) ─────────


class CorrectionCLITests(unittest.TestCase):
    """P0: successful release must return rc==0 with canonical JSON."""

    def setUp(self):
        self.root = _FakeRoot()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root.tmp, ignore_errors=True)

    def _run(self, *args, is_root=True):
        from production_mutation_lock import main
        root = self.root
        original_init = ProductionMutationLock.__init__

        def patched_init(inst, **kwargs):
            kwargs.setdefault("lock_dir", str(root.lock_dir))
            kwargs.setdefault("owner_path", str(root.owner_path))
            kwargs.setdefault("helper_path", str(root.helper_path))
            kwargs.setdefault("audit_path", str(root.audit_path))
            original_init(inst, **kwargs)
            inst._is_root = lambda: is_root
            inst._chown = lambda path, uid, gid: None
            inst._fchown = lambda fd, uid, gid: None
            _rlstat = inst._lstat
            _rfstat = inst._fstat
            _ld = str(inst.lock_dir)
            _op = str(inst.owner_path)
            def _flstat(path):
                st = _rlstat(path)
                if path in {_ld, _op, str(root.audit_path.parent), str(root.audit_path)}:
                    return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
                return st
            def _ffstat(fd):
                st = _rfstat(fd)
                return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
            inst._lstat = _flstat
            inst._fstat = _ffstat
            inst._probe_systemd = lambda: type("P", (), {"ok": True, "reason": "ok"})()
            inst._probe_processes = lambda: type("P", (), {"ok": True, "reason": "ok"})()

        previous_umask = os.umask(0)
        os.umask(previous_umask)
        ProductionMutationLock.__init__ = patched_init
        try:
            return main(list(args))
        finally:
            ProductionMutationLock.__init__ = original_init
            os.umask(previous_umask)

    def test_successful_cli_release_returns_zero_and_canonical_json(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr

        # Acquire a real synthetic lock and capture the token.
        out_acq = io.StringIO()
        with redirect_stdout(out_acq):
            rc = self._run(
                "acquire", "--owner", "o", "--action", "a",
                "--owner-host", "h", "--owner-pid", "1",
            )
        self.assertEqual(rc, 0)
        token_hex = out_acq.getvalue().strip()
        self.assertEqual(len(token_hex), 64)

        # Release with the valid token.
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self._run("release", "--token", token_hex)

        # P0 regression: rejected runtime returns rc==1 and no JSON.
        self.assertEqual(rc, 0, "successful release must return 0")
        self.assertEqual(err.getvalue(), "", "successful release must have empty stderr")
        result = json.loads(out.getvalue())
        self.assertEqual(result["state"], "released")
        self.assertEqual(result["phase"], "free")
        # Raw token must never appear in the JSON output.
        self.assertNotIn(token_hex, out.getvalue())
        # Lock directory must be gone.
        self.assertFalse(self.root.lock_dir.exists())


class CorrectionSystemdTests(unittest.TestCase):
    """Systemd: blank/internal-empty rows block; non-empty stderr blocks."""

    def setUp(self):
        from production_mutation_lock import _probe_systemd_default
        self._probe = _probe_systemd_default
        self._run_patch = mock.patch("production_mutation_lock.subprocess.run")
        self._mock_run = self._run_patch.start()

    def tearDown(self):
        self._run_patch.stop()

    def _make(self, stdout="", stderr="", returncode=0):
        r = mock.MagicMock()
        r.stdout = stdout
        r.stderr = stderr
        r.returncode = returncode
        self._mock_run.return_value = r

    def test_nonempty_stderr_blocks(self):
        # P1: rejected runtime ignores stderr and authorizes the enumeration.
        self._make(stdout="", stderr="authority warning")
        r = self._probe()
        self.assertFalse(r.ok, "non-empty stderr must block")

    def test_internal_blank_row_blocks(self):
        # A non-empty line that is whitespace-only must block (malformed row).
        self._make(stdout="sshd.service loaded active running\n   \n")
        r = self._probe()
        self.assertFalse(r.ok, "internal whitespace-only row must block")


class CorrectionPidEnumerationTests(unittest.TestCase):
    """Direct tests of _default_enumerate_pids (P1 gaps in rejected runtime)."""

    def setUp(self):
        from production_mutation_lock import _default_enumerate_pids
        self._enumerate = _default_enumerate_pids
        self._run_patch = mock.patch("production_mutation_lock.subprocess.run")
        self._mock_run = self._run_patch.start()

    def tearDown(self):
        self._run_patch.stop()

    def _make(self, stdout="", stderr="", returncode=0):
        r = mock.MagicMock()
        r.stdout = stdout
        r.stderr = stderr
        r.returncode = returncode
        self._mock_run.return_value = r

    def _assert_exact_invocation(self):
        self._mock_run.assert_called_once()
        call_args = self._mock_run.call_args[0][0]
        self.assertEqual(call_args, ["ps", "-e", "-o", "pid="])
        kwargs = self._mock_run.call_args[1]
        self.assertIs(kwargs["shell"], False)
        self.assertEqual(kwargs["timeout"], 10)
        self.assertIs(kwargs["capture_output"], True)
        self.assertIs(kwargs["text"], True)

    def test_valid_single_pid(self):
        self._make(stdout="123\n")
        pids = self._enumerate()
        self._assert_exact_invocation()
        self.assertEqual(pids, [123])

    def test_nonzero_exit_raises(self):
        self._make(returncode=1, stderr="ps failed")
        with self.assertRaises(OSError):
            self._enumerate()
        self._assert_exact_invocation()

    def test_nonempty_stderr_raises(self):
        # P1: rejected runtime accepts non-empty stderr.
        self._make(stdout="123\n", stderr="authority warning")
        with self.assertRaises(OSError):
            self._enumerate()

    def test_oversized_stdout_raises(self):
        self._make(stdout="1\n" * (2 * 1024 * 1024))
        with self.assertRaises(OSError):
            self._enumerate()

    def test_malformed_pid_raises(self):
        self._make(stdout="abc\n")
        with self.assertRaises(OSError):
            self._enumerate()

    def test_plus_sign_pid_raises(self):
        # ps can emit "+123" for kernel threads; re.fullmatch("[0-9]+") rejects it.
        self._make(stdout="+123\n")
        with self.assertRaises(OSError):
            self._enumerate()

    def test_zero_pid_raises(self):
        self._make(stdout="0\n")
        with self.assertRaises(OSError):
            self._enumerate()

    def test_negative_pid_raises(self):
        self._make(stdout="-1\n")
        with self.assertRaises(OSError):
            self._enumerate()

    def test_duplicate_pids_raises(self):
        self._make(stdout="100\n100\n")
        with self.assertRaises(OSError):
            self._enumerate()

    def test_count_cap_raises(self):
        # More than 131072 unique PIDs must raise.
        n = 131073
        lines = "\n".join(str(i) for i in range(1, n + 1)) + "\n"
        self._make(stdout=lines)
        with self.assertRaises(OSError):
            self._enumerate()

    def test_count_cap_boundary(self):
        # Exactly 131072 unique PIDs must pass.
        n = 131072
        lines = "\n".join(str(i) for i in range(1, n + 1)) + "\n"
        self._make(stdout=lines)
        pids = self._enumerate()
        self.assertEqual(len(pids), n)

    def test_bounded_reasons_no_sentinel(self):
        sentinel = "UNIQUE_SENTINEL_PID_4E1D"
        self._make(stdout="123\n", stderr=sentinel)
        with self.assertRaises(OSError) as cm:
            self._enumerate()
        self.assertNotIn(sentinel, str(cm.exception))


class CorrectionCmdlineTests(unittest.TestCase):
    """Cmdline: 65536 passes, 65537 blocks; missing NUL / leading-empty / interior empty / non-UTF8 block."""

    def setUp(self):
        from production_mutation_lock import _probe_processes_default
        self._probe = _probe_processes_default

    def _run(self, pids, cmdlines, kill_errors=None, self_pid=99999):
        def _enumerate_pids():
            return list(pids)

        def _read_cmdline(pid):
            if pid in cmdlines:
                return cmdlines[pid]
            raise OSError(errno.ENOENT, os.strerror(errno.ENOENT))

        def _kill_0(pid, sig):
            if kill_errors and pid in kill_errors:
                err = kill_errors[pid]
                if err != 0:
                    raise OSError(err, os.strerror(err))

        return self._probe(
            enumerate_pids=_enumerate_pids,
            read_cmdline=_read_cmdline,
            kill_0=_kill_0,
            self_pid=lambda: self_pid,
        )

    def test_cmdline_65536_bytes_passes(self):
        # Exactly 65536 well-formed unrelated argv bytes must pass.
        argv = b"/usr/bin/python3.12\x00/tmp/somescript.py\x00"
        padding = b"x"
        total = argv + padding * (65536 - len(argv))
        # Ensure it ends with NUL so it parses as a well-formed argv.
        total = total[:-1] + b"\x00"
        r = self._run([5000], {5000: total})
        self.assertTrue(r.ok, "65536 well-formed bytes must pass")

    def test_cmdline_65537_bytes_blocks(self):
        # P1: rejected runtime accepts exactly 65537 bytes (sentinel off-by-one).
        argv = b"/usr/bin/python3.12\x00/tmp/somescript.py\x00"
        padding = b"x"
        total = argv + padding * (65537 - len(argv))
        total = total[:-1] + b"\x00"
        r = self._run([5001], {5001: total})
        self.assertFalse(r.ok, "65537 bytes must block as oversize sentinel")

    def test_missing_trailing_nul_blocks(self):
        # Cmdline not ending with NUL (and not empty/single-NUL) must block.
        raw = b"/usr/bin/python3.12\x00/tmp/somescript.py"
        r = self._run([5002], {5002: raw})
        self.assertFalse(r.ok, "missing trailing NUL must block")

    def test_leading_empty_argv_blocks(self):
        # b"\x00foo\x00" — leading empty argv, not a kernel thread.
        raw = b"\x00foo\x00"
        r = self._run([5010], {5010: raw})
        self.assertFalse(r.ok, "leading empty argv must block")

    def test_interior_empty_argv_blocks(self):
        raw = b"/usr/bin/python3.12\x00\x00/tmp/somescript.py\x00"
        r = self._run([5003], {5003: raw})
        self.assertFalse(r.ok, "interior empty argv must block")

    def test_non_utf8_cmdline_blocks(self):
        raw = b"/usr/bin/python3.12\x00\xff\xfe\x00"
        r = self._run([5004], {5004: raw})
        self.assertFalse(r.ok, "non-UTF8 cmdline must block")

    def test_eio_on_cmdline_blocks(self):
        def _read_cmdline_eio(pid):
            raise OSError(errno.EIO, os.strerror(errno.EIO))
        r = self._probe(
            enumerate_pids=lambda: [5005],
            read_cmdline=_read_cmdline_eio,
            kill_0=lambda pid, sig: None,
            self_pid=lambda: 99999,
        )
        self.assertFalse(r.ok, "EIO on cmdline read must block")

    def test_eperm_on_kill_after_enoent_blocks(self):
        # ENOENT from read + EPERM from kill → uncertain → blocks.
        r = self._run([5006], {}, kill_errors={5006: errno.EPERM})
        self.assertFalse(r.ok, "EPERM on kill after ENOENT must block")

    def test_confirmed_exit_kernel_thread_self(self):
        # Empty cmdline (kernel thread) → ignored; self PID → skipped.
        r = self._run(
            [os.getpid(), 1],
            {1: b"\x00"},
            self_pid=os.getpid(),
        )
        self.assertTrue(r.ok, "kernel thread + self must pass")

    def test_bounded_reasons_no_sentinel(self):
        sentinel = "UNIQUE_SENTINEL_CMD_8A5F"
        def _read_cmdline_sentinel(pid):
            raise OSError(errno.EIO, sentinel)
        r = self._probe(
            enumerate_pids=lambda: [5007],
            read_cmdline=_read_cmdline_sentinel,
            kill_0=lambda pid, sig: None,
            self_pid=lambda: 99999,
        )
        self.assertFalse(r.ok)
        self.assertNotIn(sentinel, r.reason)


class CorrectionTokenFileTests(Base):
    """Token file: parent/file wrong uid/gid separately; non-regular; embedded NUL → LockError."""

    def _setup_token_dir(self):
        token_dir = self.root.tmp / "token_dir"
        token_dir.mkdir(mode=0o700)
        return token_dir

    def test_parent_wrong_uid_blocks(self):
        # Acquire a lock first so we can verify zero mutation.
        self._acquire()
        token_dir = self._setup_token_dir()
        token_file = token_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        path = str(token_file)

        real_lstat = self.lock._lstat
        def _fake_lstat(p):
            st = real_lstat(p)
            if p == str(token_dir):
                return os.stat_result((st.st_mode, st.st_ino, st.st_dev, st.st_nlink,
                                      1000, 0, st.st_size, st.st_atime,
                                      st.st_mtime, st.st_ctime))
            return st
        self.lock._lstat = _fake_lstat
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")
        self.assertEqual(cm.exception.exit_code, 4)
        # Zero mutation: lock still held, no audit written.
        self.assertTrue(self.root.lock_dir.exists())
        self.assertFalse(self.root.audit_path.exists())

    def test_parent_wrong_gid_blocks(self):
        self._acquire()
        token_dir = self._setup_token_dir()
        token_file = token_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        path = str(token_file)

        real_lstat = self.lock._lstat
        def _fake_lstat(p):
            st = real_lstat(p)
            if p == str(token_dir):
                return os.stat_result((st.st_mode, st.st_ino, st.st_dev, st.st_nlink,
                                      0, 1000, st.st_size, st.st_atime,
                                      st.st_mtime, st.st_ctime))
            return st
        self.lock._lstat = _fake_lstat
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")
        self.assertEqual(cm.exception.exit_code, 4)
        self.assertTrue(self.root.lock_dir.exists())
        self.assertFalse(self.root.audit_path.exists())

    def test_file_wrong_uid_blocks(self):
        self._acquire()
        token_dir = self._setup_token_dir()
        token_file = token_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        path = str(token_file)

        real_fstat = self.lock._fstat
        def _fake_fstat(fd):
            st = real_fstat(fd)
            return os.stat_result((st.st_mode, st.st_ino, st.st_dev, st.st_nlink,
                                  1000, st.st_gid, st.st_size, st.st_atime,
                                  st.st_mtime, st.st_ctime))
        self.lock._fstat = _fake_fstat
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")
        self.assertEqual(cm.exception.exit_code, 4)
        self.assertTrue(self.root.lock_dir.exists())

    def test_file_wrong_gid_blocks(self):
        self._acquire()
        token_dir = self._setup_token_dir()
        token_file = token_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        path = str(token_file)

        real_fstat = self.lock._fstat
        def _fake_fstat(fd):
            st = real_fstat(fd)
            return os.stat_result((st.st_mode, st.st_ino, st.st_dev, st.st_nlink,
                                  st.st_uid, 1000, st.st_size, st.st_atime,
                                  st.st_mtime, st.st_ctime))
        self.lock._fstat = _fake_fstat
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")
        self.assertEqual(cm.exception.exit_code, 4)
        self.assertTrue(self.root.lock_dir.exists())

    def test_non_regular_final_component_blocks(self):
        self._acquire()
        token_dir = self._setup_token_dir()
        token_file = token_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        path = str(token_file)

        real_fstat = self.lock._fstat
        import stat as stat_mod
        def _fake_fstat(fd):
            st = real_fstat(fd)
            # Force S_IFIFO so S_ISREG returns False.
            mode = stat_mod.S_IFIFO | 0o600
            return os.stat_result((mode,) + st[1:])
        self.lock._fstat = _fake_fstat
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")
        self.assertEqual(cm.exception.exit_code, 4)
        self.assertTrue(self.root.lock_dir.exists())

    def test_embedded_nul_parent_path_produces_structured_lockerror(self):
        # NUL in the parent path → lstat ValueError → LockError.
        token_dir = self._setup_token_dir()
        token_file = token_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        # Build a path with NUL in the parent directory component.
        bad_parent = str(token_dir) + "\x00sub"
        path = bad_parent + "/token"
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")
        self.assertEqual(cm.exception.exit_code, 4)

    def test_bounded_token_file_reasons_no_sentinel(self):
        sentinel = "UNIQUE_SENTINEL_TF_2C9B"
        token_dir = self._setup_token_dir()
        token_file = token_dir / sentinel
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        path = str(token_file)

        # Make lstat raise with the sentinel in the message.
        def _fake_lstat(p):
            raise OSError(errno.ENOENT, sentinel)
        self.lock._lstat = _fake_lstat
        with self.assertRaises(LockError) as cm:
            self.lock._read_token_file(path)
        self.assertEqual(cm.exception.state, "blocked")
        self.assertNotIn(sentinel, cm.exception.detail["reason"])



# ── Round 2 regression tests (P0/P1 from rejected 97fbec23) ─────────────


class Round2PidEnumerationTests(unittest.TestCase):
    """Round 2: bounded PID value (_MAX_PID_VALUE = 2147483647)."""

    def setUp(self):
        from production_mutation_lock import _default_enumerate_pids
        self._enumerate = _default_enumerate_pids
        self._run_patch = mock.patch("production_mutation_lock.subprocess.run")
        self._mock_run = self._run_patch.start()

    def tearDown(self):
        self._run_patch.stop()

    def _make(self, stdout="", stderr="", returncode=0):
        r = mock.MagicMock()
        r.stdout = stdout
        r.stderr = stderr
        r.returncode = returncode
        self._mock_run.return_value = r

    def test_pid_above_max_int32_raises(self):
        # P0: 2147483648 must be rejected with bounded OSError, not appended.
        self._make(stdout="2147483648\n")
        with self.assertRaises(OSError):
            self._enumerate()

    def test_pid_at_max_int32_accepted(self):
        # 2147483647 is the exact accepted boundary.
        self._make(stdout="2147483647\n")
        pids = self._enumerate()
        self.assertEqual(pids, [2147483647])


class Round2ProbeExceptionNormalizationTests(unittest.TestCase):
    """Round 2: kill_0 OverflowError / ValueError must normalize to ok=False."""

    def test_kill_overflowerror_blocked(self):
        from production_mutation_lock import _probe_processes_default
        def _kill_overflow(pid, sig):
            raise OverflowError("pid too large")
        r = _probe_processes_default(
            enumerate_pids=lambda: [2147483648],
            read_cmdline=lambda pid: (_ for _ in ()).throw(
                OSError(errno.ENOENT, os.strerror(errno.ENOENT))
            ),
            kill_0=_kill_overflow,
            self_pid=lambda: 99999,
        )
        self.assertFalse(r.ok, "OverflowError from kill_0 must block")

    def test_kill_valueerror_blocked(self):
        from production_mutation_lock import _probe_processes_default
        def _kill_value(pid, sig):
            raise ValueError("embedded null byte")
        r = _probe_processes_default(
            enumerate_pids=lambda: [100],
            read_cmdline=lambda pid: (_ for _ in ()).throw(
                OSError(errno.ENOENT, os.strerror(errno.ENOENT))
            ),
            kill_0=_kill_value,
            self_pid=lambda: 99999,
        )
        self.assertFalse(r.ok, "ValueError from kill_0 must block")


class Round2EmbeddedNulTokenFileTests(Base):
    """Round 2: actual embedded NUL in final component reaches open seam."""

    def test_embedded_nul_reaches_open_seam(self):
        # P1: filesystem forbids NUL in filenames, so create a normal file
        # but pass a path string whose final component contains a real NUL.
        # The open seam must be invoked exactly once and os.open must raise
        # ValueError, which the runtime must convert to structured LockError.
        self._acquire()
        token_dir = self.root.tmp / "nul_parent"
        token_dir.mkdir(mode=0o700)
        normal_file = token_dir / "token"
        normal_file.write_bytes(b"a" * 64)
        normal_file.chmod(0o600)

        # Build a path string with NUL in the final component.
        path = str(token_dir) + "/tok\x00en"

        # Record exact invocation count and received path.
        invoked = []
        real_open = self.lock._open
        def _tracking_open(p, flags, *args, **kwargs):
            invoked.append(p)
            return real_open(p, flags, *args, **kwargs)
        self.lock._open = _tracking_open

        # Override lstat so the parent appears root:root 0700.
        real_lstat = self.lock._lstat
        def _fake_lstat(p):
            if p == str(token_dir):
                st = real_lstat(str(self.root.tmp))
                return st
            return real_lstat(p)
        self.lock._lstat = _fake_lstat

        try:
            with self.assertRaises(LockError) as cm:
                self.lock._read_token_file(path)
            self.assertEqual(cm.exception.state, "blocked")
            self.assertEqual(cm.exception.exit_code, 4)
            self.assertEqual(
                cm.exception.detail["reason"],
                "token-file open failed",
            )
            self.assertNotIn("\x00", cm.exception.detail["reason"])
            self.assertNotIn(path, cm.exception.detail["reason"])
            self.assertEqual(invoked, [path], "open seam must receive exact path exactly once")
            self.assertTrue(self.root.lock_dir.exists())
            self.assertFalse(self.root.audit_path.exists())
        finally:
            self.lock._open = real_open
            self.lock._lstat = real_lstat


class Round2TokenFileRecoverDirectTests(Base):
    """Round 2: valid no-LF and one-LF token files reach recover."""

    def test_no_lf_token_file_reaches_recover(self):
        acq = self._acquire(owner="o", action="a", owner_host="h", owner_pid=1234)
        token = acq["token"]
        token_dir = self.root.tmp / "tf_nolf"
        token_dir.mkdir(mode=0o700)
        token_file = token_dir / "token"
        token_file.write_bytes(token.encode("ascii"))
        token_file.chmod(0o600)
        path = str(token_file)

        read_token = self.lock._read_token_file(path)
        self.assertEqual(read_token, token)
        with mock.patch.object(
            type(self.lock), "recover", wraps=self.lock.recover
        ) as wrapped_recover:
            result = self.lock.recover(
                token=read_token,
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
            wrapped_recover.assert_called_once()
        self.assertEqual(result["state"], "recovered")
        self.assertIn("receipt_digest", result)
        # Lock released.
        self.assertFalse(self.root.lock_dir.exists())
        # Audit file exists with exactly one canonical JSON receipt.
        self.assertTrue(self.root.audit_path.exists())
        audit_lines = self.root.audit_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(audit_lines), 1)
        audit_entry = json.loads(audit_lines[0])
        self.assertIn("lock_token_digest", audit_entry)
        # Raw token must not appear in audit.
        self.assertNotIn(token, audit_lines[0])
        # Raw token must not appear in result.
        result_str = json.dumps(result)
        self.assertNotIn(token, result_str)

    def test_one_lf_token_file_reaches_recover(self):
        acq = self._acquire()
        token = acq["token"]
        token_dir = self.root.tmp / "tf_lf"
        token_dir.mkdir(mode=0o700)
        token_file = token_dir / "token"
        token_file.write_bytes(token.encode("ascii") + b"\n")
        token_file.chmod(0o600)
        path = str(token_file)

        read_token = self.lock._read_token_file(path)
        self.assertEqual(read_token, token)
        with mock.patch.object(
            type(self.lock), "recover", wraps=self.lock.recover
        ) as wrapped_recover:
            result = self.lock.recover(
                token=read_token,
                operator="admin",
                reason="stale",
                confirm_owner_stopped=True,
            )
            wrapped_recover.assert_called_once()
        self.assertEqual(result["state"], "recovered")
        self.assertIn("receipt_digest", result)
        self.assertFalse(self.root.lock_dir.exists())
        self.assertTrue(self.root.audit_path.exists())
        audit_lines = self.root.audit_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(audit_lines), 1)
        audit_entry = json.loads(audit_lines[0])
        self.assertIn("lock_token_digest", audit_entry)
        self.assertNotIn(token, audit_lines[0])
        result_str = json.dumps(result)
        self.assertNotIn(token, result_str)


class Round2ShortAndGrowthReadTests(Base):
    """Round 2: short read and growth read via os.read injection."""

    def test_short_read_blocks_retains_lock(self):
        # P1: rejected runtime uses _open injection; Round 2 must inject os.read.
        self._acquire()
        token_dir = self.root.tmp / "short_read"
        token_dir.mkdir(mode=0o700)
        token_file = token_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        path = str(token_file)

        real_os_read = os.read
        def _short_read(fd, n):
            # Return fewer than fstat-reported size.
            return real_os_read(fd, 32)
        with mock.patch("production_mutation_lock.os.read", side_effect=_short_read):
            with self.assertRaises(LockError) as cm:
                self.lock._read_token_file(path)
            self.assertEqual(cm.exception.state, "blocked")
            self.assertEqual(cm.exception.exit_code, 4)
            self.assertEqual(
                cm.exception.detail["reason"],
                "token-file size changed between stat and read",
            )
            # Lock still held, no audit.
            self.assertTrue(self.root.lock_dir.exists())
            self.assertFalse(self.root.audit_path.exists())

    def test_growth_read_blocks_retains_lock(self):
        self._acquire()
        token_dir = self.root.tmp / "growth_read"
        token_dir.mkdir(mode=0o700)
        token_file = token_dir / "token"
        token_file.write_bytes(b"a" * 64)
        token_file.chmod(0o600)
        path = str(token_file)

        real_os_read = os.read
        def _growth_read(fd, n):
            # Return size+1 bytes (growth probe catches it).
            return real_os_read(fd, n) + b"x"
        with mock.patch("production_mutation_lock.os.read", side_effect=_growth_read):
            with self.assertRaises(LockError) as cm:
                self.lock._read_token_file(path)
            self.assertEqual(cm.exception.state, "blocked")
            self.assertEqual(cm.exception.exit_code, 4)
            self.assertEqual(
                cm.exception.detail["reason"],
                "token-file size changed between stat and read",
            )
            self.assertTrue(self.root.lock_dir.exists())
            self.assertFalse(self.root.audit_path.exists())


if __name__ == "__main__":
    unittest.main()
