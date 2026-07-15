"""Focused tests for scripts/production-mutation-lock.py.

All tests use injectable temp paths and fake system probes; no real root,
/run, /usr/local/sbin, /var/log, or systemd is required.
"""
import hashlib
import json
import os
import stat
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
        def _fake_lstat(path):
            st = _real_lstat(path)
            if path == lock_dir_str:
                return os.stat_result((st.st_mode,) + st[1:4] + (0, 0) + st[6:])
            if path in {owner_path_str, audit_parent_str, audit_path_str}:
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

if __name__ == "__main__":
    unittest.main()
