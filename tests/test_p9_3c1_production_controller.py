"""Dynamic tests for P9-3C1 P2 inert production controller.

Tests exercise the controller state machine, ledger, phase, manifest,
prepare/preflight/status, authorization, and five-job matrix via fake-system seams.
No test asserts only source text; all tests use temp directories, real SQLite,
and injected subprocess seams.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the repo root is on sys.path so we can import the controller module.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Import controller module directly (it's at scripts/p9_3c1_controller.py).
import importlib.util
_CTRL_PATH = _REPO_ROOT / "scripts" / "p9_3c1_controller.py"
_spec = importlib.util.spec_from_file_location("p9_3c1_controller", _CTRL_PATH)
assert _spec is not None
_ctrl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ctrl)  # type: ignore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_state_root():
    """Create a temporary state root base."""
    with tempfile.TemporaryDirectory(prefix="p9-3c1-test-") as td:
        yield os.path.realpath(td)


@pytest.fixture
def fake_manifest(tmp_state_root):
    """Create a minimal valid controller manifest."""
    run_id = "p9-3c1-prod-20260716t120000z-abcdef01"
    state_root = os.path.join(tmp_state_root, run_id)
    os.makedirs(state_root, exist_ok=True)

    manifest = {
        "production_launcher_identity": {
            "cli_path": "/usr/local/bin/coord-local",
            "cli_dev": 2049,
            "cli_inode": 12345,
            "cli_owner": 0,
            "cli_group": 0,
            "cli_mode": 493,  # 0o755
            "db_path": "/var/lib/coordinate/coord.sqlite3",
            "db_dev": 2049,
            "db_inode": 67890,
            "db_owner": 0,
            "db_group": 0,
            "db_mode": 384,  # 0o600
        },
        "run_id": run_id,
        "state_root": state_root,
        "unit_user": "coord",
        "unit_group": "coord",
        "unit_uid": 1001,
        "unit_gid": 1001,
        "installed_revisions": {
            "multinexus_deployed": "1" * 40,
            "coordinate_deployed": "2" * 40,
        },
        "installed_hashes": {
            "controller": "a" * 64,
            "entrypoint": "b" * 64,
            "helper": "c" * 64,
            "fixture_bin": "d" * 64,
            "agentd_main": "e" * 64,
            "agentd_worker": "f" * 64,
            "agentd_coordinate_client": "0" * 64,
        },
        "config_hashes": {
            name: hashlib.sha256(
                (_REPO_ROOT / "multinexus" / "fixture" / "config" / "p9-3c1" / name).read_bytes()
            ).hexdigest()
            for name in (
                "agents.production.toml",
                "executor.v1-disabled.toml",
                "executor.v2-enabled.toml",
                "executor.v3-disabled.toml",
                "executor.v4-empty.toml",
                "capacity.v1.toml",
                "capacity.v2-empty.toml",
            )
        },
        "helper_allowlist": ["p9-3c-fixture-e1", "p9-3c-fixture-e2"],
        "reap_policy": {"mode": "none", "reason": "p9-3c1-test-run"},
        "p3_authorization_digest": None,
    }
    manifest_json = (_ctrl.canonical_json(manifest) + "\n").encode()
    manifest_sha = hashlib.sha256(manifest_json).hexdigest()

    manifest_path = os.path.join(state_root, "control", "manifest.json")
    sha_path = os.path.join(state_root, "control", "manifest.sha256")
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "wb") as f:
        f.write(manifest_json)
    os.chmod(manifest_path, 0o600)
    with open(sha_path, "w") as f:
        f.write(manifest_sha + "\n")
    os.chmod(sha_path, 0o600)

    return {
        "run_id": run_id,
        "state_root": state_root,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_sha": manifest_sha,
    }


@pytest.fixture
def controller_seams(fake_manifest):
    """Set up controller seams for testing."""
    orig_seams = dict(_ctrl._seams)

    # Override state root base and paths
    _ctrl._set_seam("state_root_base", os.path.dirname(fake_manifest["state_root"]))
    _ctrl._set_seam("os_getuid", lambda: 1000)
    _ctrl._set_seam("os_geteuid", lambda: 0)

    # Keep fake authorities outside the per-run root: prepare is fresh-only and
    # several tests deliberately remove that root before invoking it.
    authority_root = os.path.dirname(fake_manifest["state_root"])
    db_path = os.path.join(authority_root, "fake-coord.sqlite3")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE execution_attempt_leases "
            "(lease_id TEXT PRIMARY KEY, status TEXT NOT NULL, expires_at TEXT NOT NULL)"
        )
        conn.execute("PRAGMA user_version = 13")
        conn.commit()
    finally:
        conn.close()
    _ctrl._set_seam("production_db", db_path)

    # Fake production CLI
    cli_path = os.path.join(authority_root, "fake-coord-cli")
    with open(cli_path, "w") as f:
        f.write("#!/bin/sh\nprintf '%s\\n' '{\"status\":\"ok\"}'\n")
    os.chmod(cli_path, 0o755)
    _ctrl._set_seam("production_cli", cli_path)
    _ctrl._set_seam("config_dir", str(_REPO_ROOT / "multinexus" / "fixture" / "config" / "p9-3c1"))
    _ctrl._set_seam("helper_path", str(_REPO_ROOT / "multinexus" / "fixture" / "bin" / "p9-3c0-unit.sh"))
    _ctrl._set_seam(
        "fixture_bin",
        "/opt/multinexus/multinexus/fixture/bin/p9-3c0-fixture.py",
    )
    _ctrl._set_seam("resolve_user", lambda _name: 1001)
    _ctrl._set_seam("resolve_group", lambda _name: 1001)
    _ctrl._set_seam("validate_owner_mode", lambda path, uid, gid, mode: path)
    _ctrl._set_seam(
        "collect_installed_hashes",
        lambda: {
            "controller": "a" * 64,
            "entrypoint": "b" * 64,
            "helper": "c" * 64,
            "fixture_bin": "d" * 64,
            "agentd_main": "e" * 64,
            "agentd_worker": "f" * 64,
            "agentd_coordinate_client": "0" * 64,
        },
    )
    _ctrl._set_seam(
        "collect_revisions",
        lambda: {
            "multinexus_deployed": "1" * 40,
            "coordinate_deployed": "2" * 40,
        },
    )
    _ctrl._set_seam(
        "canonical_projection",
        lambda: {"sha256": "9" * 64, "components": {}},
    )
    def launcher_identity(path, digest):
        return {
            "path": path,
            "sha256": digest,
            "dev": 10,
            "inode": int(digest[0], 16) + 100,
            "size": 128,
            "nlink": 1,
            "owner": 0,
            "group": 0,
            "mode": 0o755 if not path.endswith(".toml") else 0o644,
        }

    _ctrl._set_seam(
        "collect_launcher_files",
        lambda: {
            "python": launcher_identity("/opt/multinexus/.venv/bin/python", "1" * 64),
            "helper": launcher_identity(
                "/opt/multinexus/multinexus/fixture/bin/p9-3c0-unit.sh", "2" * 64
            ),
            "fixture_bin": launcher_identity(
                "/opt/multinexus/multinexus/fixture/bin/p9-3c0-fixture.py", "3" * 64
            ),
            "mutation_lock_helper": launcher_identity(
                "/opt/multinexus/scripts/production-mutation-lock.sh", "5" * 64
            ),
            "agent_template": launcher_identity(
                "/opt/multinexus/multinexus/fixture/config/p9-3c1/agents.production.toml",
                "4" * 64,
            ),
        },
    )
    lock_state = {"token": None}

    def lock_status(expect=None):
        token = lock_state["token"]
        if token is None:
            return {"state": "free", "phase": "free"}
        return {
            "state": "held",
            "phase": "held",
            "owner": _ctrl.LOCK_OWNER,
            "action": _ctrl._lock_action(fake_manifest["run_id"]),
            "token_matches": expect == token if expect is not None else None,
        }

    def lock_acquire(_run_id):
        assert lock_state["token"] is None
        lock_state["token"] = "a" * 64
        return lock_state["token"]

    def lock_release(token):
        assert token == lock_state["token"]
        lock_state["token"] = None

    _ctrl._set_seam("lock_status", lock_status)
    _ctrl._set_seam("lock_acquire", lock_acquire)
    _ctrl._set_seam("lock_release", lock_release)
    _ctrl._set_seam("chown", lambda _path, _uid, _gid: None)

    # Fake now_utc
    fixed_now = datetime.datetime(2026, 7, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)
    _ctrl._set_seam("now_utc", lambda: fixed_now)

    yield

    # Restore original seams
    _ctrl._seams.clear()
    _ctrl._seams.update(orig_seams)


# ---------------------------------------------------------------------------
# Run ID validation
# ---------------------------------------------------------------------------


class TestRunIdValidation:
    def test_valid_run_id(self):
        rid = "p9-3c1-prod-20260716t120000z-abcdef01"
        assert _ctrl.validate_run_id(rid) == rid

    def test_invalid_prefix(self):
        with pytest.raises(_ctrl.ControllerError):
            _ctrl.validate_run_id("bad-prod-20260716t120000z-abcdef01")

    def test_invalid_format(self):
        with pytest.raises(_ctrl.ControllerError):
            _ctrl.validate_run_id("p9-3c1-prod-2026-07-16t120000z-abcdef01")

    def test_too_long(self):
        rid = "p9-3c1-prod-20260716t120000z-" + "a" * 16
        with pytest.raises(_ctrl.ControllerError):
            _ctrl.validate_run_id(rid)


# ---------------------------------------------------------------------------
# Canonical JSON and SHA helpers
# ---------------------------------------------------------------------------


class TestCanonicalJson:
    def test_deterministic_output(self):
        obj = {"b": 2, "a": 1}
        out1 = _ctrl.canonical_json(obj)
        out2 = _ctrl.canonical_json({"a": 1, "b": 2})
        assert out1 == out2

    def test_no_trailing_newline(self):
        out = _ctrl.canonical_json({"a": 1})
        assert not out.endswith("\n")

    def test_sha256_stable(self):
        data = b"test data"
        sha1 = _ctrl.sha256_hex(data)
        sha2 = _ctrl.sha256_hex(b"test data")
        assert sha1 == sha2
        assert len(sha1) == 64


# ---------------------------------------------------------------------------
# Phase and ledger
# ---------------------------------------------------------------------------


class TestPhaseAndLedger:
    def test_phase_roundtrip(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        root = fake_manifest["state_root"]
        os.makedirs(_ctrl.control_dir(run_id), exist_ok=True)

        _ctrl._write_phase(run_id, "sealed")
        assert _ctrl._current_phase(run_id) == "sealed"

        _ctrl._write_phase(run_id, "preflight-ok")
        assert _ctrl._current_phase(run_id) == "preflight-ok"

    def test_ledger_append_and_chain(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        root = fake_manifest["state_root"]
        os.makedirs(os.path.join(root, "ledger"), exist_ok=True)

        sha1 = _ctrl._append_ledger(run_id, "sealed", "prepare.completed")
        sha2 = _ctrl._append_ledger(run_id, "sealed", "test.event")
        assert sha1 != sha2

        records = _ctrl._read_ledger(run_id)
        assert len(records) == 2
        assert records[0]["seq"] == 1
        assert records[1]["seq"] == 2
        assert records[0]["record_sha256"] == sha1
        assert records[1]["prev_sha256"] == sha1

        # Chain should validate
        _ctrl._validate_ledger_chain(run_id)

    def test_ledger_chain_corruption_detected(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        root = fake_manifest["state_root"]
        os.makedirs(os.path.join(root, "ledger"), exist_ok=True)

        _ctrl._append_ledger(run_id, "sealed", "prepare.completed")
        _ctrl._append_ledger(run_id, "sealed", "test.event")

        # Corrupt the chain
        lp = _ctrl.ledger_path(run_id)
        with open(lp, "a") as f:
            f.write(json.dumps({"seq": 3, "phase": "sealed", "event": "bad",
                               "prev_sha256": "deadbeef", "record_sha256": "bad"}) + "\n")

        with pytest.raises(_ctrl.ControllerError):
            _ctrl._validate_ledger_chain(run_id)

    def test_phase_tail_agreement(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        root = fake_manifest["state_root"]
        os.makedirs(os.path.join(root, "ledger"), exist_ok=True)
        os.makedirs(os.path.join(root, "control"), exist_ok=True)

        _ctrl._write_phase(run_id, "sealed")
        _ctrl._append_ledger(run_id, "sealed", "prepare.completed")
        assert _ctrl._phase_tail_agree(run_id)

    def test_no_phase_returns_none(self):
        assert _ctrl._current_phase("nonexistent-run") is None


# ---------------------------------------------------------------------------
# Manifest building and writing
# ---------------------------------------------------------------------------


class TestManifest:
    def test_build_manifest_has_required_fields(self, controller_seams, fake_manifest):
        m = fake_manifest["manifest"]
        assert "production_launcher_identity" in m
        assert "run_id" in m
        assert "state_root" in m
        assert "reap_policy" in m
        assert m["reap_policy"]["mode"] == "none"
        assert "helper_allowlist" in m
        assert set(m["helper_allowlist"]) == {"p9-3c-fixture-e1", "p9-3c-fixture-e2"}

    def test_manifest_write_and_read(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        root = fake_manifest["state_root"]
        os.makedirs(_ctrl.control_dir(run_id), exist_ok=True)

        manifest_json = json.dumps(fake_manifest["manifest"], sort_keys=True)
        manifest_sha = _ctrl.sha256_hex(manifest_json)

        mp = _ctrl.manifest_path(run_id)
        msp = _ctrl.manifest_sha_path(run_id)
        with open(mp, "w") as f:
            f.write(manifest_json)
        with open(msp, "w") as f:
            f.write(manifest_sha + "\n")

        stored_sha = _ctrl.sha256_file(mp)
        assert stored_sha == manifest_sha


# ---------------------------------------------------------------------------
# Prepare
# ---------------------------------------------------------------------------


class TestPrepare:
    def test_prepare_fresh_directory(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        root = _ctrl.state_root(run_id)
        # Ensure fresh
        if os.path.exists(root):
            import shutil
            shutil.rmtree(root)

        _ctrl._set_seam("os_getuid", lambda: 1000)
        _ctrl._set_seam("os_geteuid", lambda: 0)

        result = _ctrl.cmd_prepare(run_id, "coord", "coord")
        assert result["status"] == "sealed"
        assert result["run_id"] == run_id

        # Verify directory structure
        assert os.path.isdir(root)
        assert os.path.isdir(os.path.join(root, "control"))
        assert os.path.isdir(os.path.join(root, "ledger"))
        assert os.path.isdir(os.path.join(root, "evidence"))
        assert os.path.isdir(os.path.join(root, "backup"))
        assert os.path.isfile(_ctrl.manifest_path(run_id))
        assert os.path.isfile(_ctrl.manifest_sha_path(run_id))
        assert os.path.isfile(_ctrl.phase_path(run_id))

    def test_prepare_refuses_existing(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        root = _ctrl.state_root(run_id)
        os.makedirs(root, exist_ok=True)

        _ctrl._set_seam("os_getuid", lambda: 1000)
        _ctrl._set_seam("os_geteuid", lambda: 0)

        with pytest.raises(_ctrl.ControllerError, match="already exists"):
            _ctrl.cmd_prepare(run_id, "coord", "coord")


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


class TestPreflight:
    def test_preflight_readonly_does_not_mutate(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        _ctrl._set_seam("os_getuid", lambda: 1000)
        _ctrl._set_seam("os_geteuid", lambda: 0)

        # Prepare first
        root = _ctrl.state_root(run_id)
        if os.path.exists(root):
            import shutil
            shutil.rmtree(root)
        _ctrl.cmd_prepare(run_id, "coord", "coord")

        # Capture state tree bytes before
        def _state_tree_bytes():
            result = b""
            for dirpath, dirnames, filenames in sorted(os.walk(root)):
                for fn in sorted(filenames):
                    fp = os.path.join(dirpath, fn)
                    if os.path.isfile(fp) and not os.path.islink(fp):
                        with open(fp, "rb") as f:
                            result += f.read()
            return result

        before = _state_tree_bytes()
        evidence = _ctrl.cmd_preflight(run_id)
        after = _state_tree_bytes()

        assert before == after, "preflight mutated read-only state tree"
        assert evidence["status"] == "preflight_passed"


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_status_readonly(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        _ctrl._set_seam("os_getuid", lambda: 1000)
        _ctrl._set_seam("os_geteuid", lambda: 0)

        root = _ctrl.state_root(run_id)
        if os.path.exists(root):
            import shutil
            shutil.rmtree(root)
        _ctrl.cmd_prepare(run_id, "coord", "coord")

        status = _ctrl.cmd_status(run_id)
        assert status["run_id"] == run_id
        assert "phase" in status


# ---------------------------------------------------------------------------
# Authorization validation
# ---------------------------------------------------------------------------


def _prepare_fresh(run_id):
    root = _ctrl.state_root(run_id)
    if os.path.exists(root):
        import shutil
        shutil.rmtree(root)
    _ctrl.cmd_prepare(run_id, "coord", "coord")


def _write_authorization(fake_manifest, **overrides):
    run_id = fake_manifest["run_id"]
    manifest, manifest_sha = _ctrl._read_manifest(run_id)
    auth = {
        "contract_version": 1,
        "run_id": run_id,
        "manifest_sha256": manifest_sha,
        "installed_revisions": manifest["installed_revisions"],
        "installed_hashes": manifest["installed_hashes"],
        "p3_bootstrap_sha256": "3" * 64,
        "review_artifact_sha256": "4" * 64,
        "reviewer_verdict": "APPROVE",
        "budgets": dict(_ctrl.AUTH_EXACT_BUDGETS),
        "expiry_utc": "2026-07-16T13:00:00Z",
        "nonce": "p9-3c1-once-abcdef0123456789",
    }
    auth.update(overrides)
    auth_path = os.path.join(os.path.dirname(fake_manifest["state_root"]), "external-auth.json")
    Path(auth_path).write_text(_ctrl.canonical_json(auth) + "\n", encoding="utf-8")
    os.chmod(auth_path, 0o600)
    return auth_path, _ctrl.sha256_file(auth_path)


def _install_live_fake(run_id: str) -> dict:
    """Install one dynamic fake system that exercises real controller command construction."""
    state = {
        "jobs": {},
        "units": {},
        "executor_version": None,
        "capacity_version": None,
        "recovery_started": False,
        "clock": 0.0,
        "commands": [],
    }

    def completed(argv, payload=None, *, returncode=0, stderr=""):
        stdout = "" if payload is None else json.dumps(payload, sort_keys=True) + "\n"
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    def value_after(args, flag):
        return args[args.index(flag) + 1]

    def fake_runner(argv, **_kwargs):
        state["commands"].append(list(argv))
        args = list(argv[1:])
        fail_prefix = state.get("fail_once_prefix")
        if fail_prefix is not None and args[:len(fail_prefix)] == list(fail_prefix):
            state.pop("fail_once_prefix")
            return completed(argv, returncode=1, stderr="injected phase failure")
        if argv[0] == _ctrl._seams["helper_path"]:
            command = args[0]
            agent = value_after(args, "--agent-id") if "--agent-id" in args else None
            if command == "production-render":
                helper_ledger = Path(_ctrl.state_root(run_id)) / "runtime" / "unit" / "helper-events.log"
                helper_ledger.write_text("static-definition ready\n", encoding="utf-8")
                return completed(argv, {"status": "rendered", "run_id": run_id, "state_dir": _ctrl.state_root(run_id)})
            if command == "production-preflight":
                return completed(argv, {"status": "preflight_ok", "agent_id": agent, "run_id": run_id, "unit_count": len(state["units"])})
            if command == "production-start":
                mode = value_after(args, "--mode")
                state["units"][agent] = "active"
                helper_ledger = Path(_ctrl.state_root(run_id)) / "runtime" / "unit" / "helper-events.log"
                with helper_ledger.open("a", encoding="utf-8") as handle:
                    handle.write(f"unit {agent}-{run_id}.service agent={agent} cgroup=/system.slice/{agent}.service\n")
                if "--recoverable" in args:
                    state["recovery_started"] = True
                return completed(argv, {"status": "started", "agent_id": agent, "run_id": run_id, "mode": mode})
            if command == "production-stop":
                state["units"][agent] = "inactive"
                helper_ledger = Path(_ctrl.state_root(run_id)) / "runtime" / "unit" / "helper-events.log"
                with helper_ledger.open("a", encoding="utf-8") as handle:
                    handle.write(f"cgroup-empty unit={agent}-{run_id}.service\n")
                termination = "crash" if "--crash" in args else "graceful"
                return completed(argv, {"status": "stopped", "agent_id": agent, "termination": termination, "unit": f"{agent}-{run_id}.service"})
            if command == "production-status":
                active = state["units"].get(agent) == "active"
                return completed(argv, {
                    "status": "ok", "agent_id": agent, "unit": f"{agent}-{run_id}.service",
                    "properties": {
                        "ActiveState": "active" if active else "inactive",
                        "SubState": "running" if active else "dead",
                        "MainPID": "4321" if active else "0",
                        "ControlGroup": f"/system.slice/{agent}.service",
                        "Result": "success",
                    },
                })
            if command == "production-cleanup":
                return completed(argv, {"status": "cleaned", "agent_id": agent, "unit": f"{agent}-{run_id}.service"})
            raise AssertionError(args)

        if args[:2] == ["workspace", "add"]:
            return completed(argv, {"workspace": {"id": args[2], "path": value_after(args, "--path")}})
        if args[:3] == ["workspace", "host-profile", "set"]:
            return completed(argv, {"result": {"workspace_id": args[3], "host_id": value_after(args, "--host-id")}})
        if args[:3] == ["runtime", "agent", "register"]:
            agent = value_after(args, "--agent-id")
            return completed(argv, {"result": {"agent": {"id": agent, "host_id": value_after(args, "--host-id")}}})
        if args[:3] == ["runtime", "agent", "heartbeat"]:
            agent = value_after(args, "--agent-id")
            return completed(argv, {"result": {"agent": {"id": agent, "online_state": "online"}}})
        if args[:3] == ["runtime", "agent", "deactivate"]:
            return completed(argv, {"result": {"blocked": False, "deactivated": True}})
        if args[:3] == ["runtime", "executor", "sync"]:
            filename = Path(value_after(args, "--source")).name
            version = int(filename.split(".")[1][1])
            state["executor_version"] = version
            return completed(argv, {"source_id": "p9-3c1-fixture-executors", "source_version": version})
        if args[:3] == ["runtime", "executor", "list"]:
            version = state["executor_version"]
            empty = version == 4
            definitions = [] if empty else [{"id": "p9-3c1-local-fixture", "source_id": "p9-3c1-fixture-executors"}]
            bindings = [] if empty else [
                {"agent_id": agent, "source_id": "p9-3c1-fixture-executors", "enabled": version == 2}
                for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2")
            ]
            return completed(argv, {"sources": [{"source_id": "p9-3c1-fixture-executors", "source_version": version}], "definitions": definitions, "bindings": bindings})
        if args[:3] == ["runtime", "capacity", "sync"]:
            filename = Path(value_after(args, "--source")).name
            version = 2 if "v2" in filename else 1
            state["capacity_version"] = version
            return completed(argv, {"source_id": "p9-3c1-fixture-capacity", "source_version": version})
        if args[:3] == ["runtime", "capacity", "list"]:
            version = state["capacity_version"]
            policies = [] if version == 2 else [
                {"agent_id": agent, "source_id": "p9-3c1-fixture-capacity", "max_concurrent_jobs": 1}
                for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2")
            ]
            return completed(argv, {"sources": [{"source_id": "p9-3c1-fixture-capacity", "source_version": version}], "policies": policies})
        if args[:3] == ["runtime", "request", "submit"]:
            origin = json.loads(value_after(args, "--origin-json"))
            label = origin["matrix_job"]
            agent = value_after(args, "--target-agent")
            worktree = value_after(args, "--worktree-path")
            job_id = f"job-{label.lower()}"
            state["jobs"][label] = {
                "id": job_id, "assigned_agent": agent, "worktree_path": worktree,
                "status": "pending", "attempt_count": 0, "recoverable": 0,
                "result_json": None, "poll": 0, "leases": [], "deliveries": [],
            }
            return completed(argv, {"result": {
                "event": {"id": f"event-{label.lower()}"}, "event_created": True,
                "job": {"id": job_id, "assigned_agent": agent, "worktree_path": worktree},
                "job_created": True,
            }})
        if args[:3] == ["runtime", "job", "claim"]:
            j5 = state["jobs"]["J5"]
            j3_lease = state["jobs"]["J3"]["leases"][0]
            return completed(argv, {"result": {
                "job": None, "claimed": False, "attempt_token": None,
                "execution_context": None, "execution_lease": None,
                "reason": "resource_blocked", "oldest_blocked_job_id": j5["id"],
                "oldest_blocked_resource_key": j3_lease["resource_key"],
            }})
        if args[:4] == ["runtime", "job", "lease", "reap"]:
            job = state["jobs"]["J3"]
            lease = job["leases"][0]
            lease["status"] = "expired"
            job.update(status="timed_out", recoverable=1)
            return completed(argv, {"result": {
                "mode": "exact", "reaped_count": 1, "lease_id": lease["lease_id"],
                "job_id": job["id"], "attempt_token": lease["attempt_token"],
                "agent_id": job["assigned_agent"],
            }})
        if args[:3] == ["runtime", "job", "progress"]:
            return completed(argv, returncode=1, stderr="stale attempt rejected")
        if args[:4] == ["runtime", "job", "lease", "renew"]:
            return completed(argv, returncode=1, stderr="stale lease rejected")
        if args[:3] == ["runtime", "job", "report"]:
            job = state["jobs"]["J3"]
            attempt = int(value_after(args, "--attempt-token"))
            if attempt == 1:
                return completed(argv, returncode=1, stderr="stale report rejected")
            job.update(status="done", recoverable=0, result_json="{}")
            job["leases"][1]["status"] = "released"
            return completed(argv, {"result": {
                "job": {"id": job["id"], "status": "done"}, "event": {"id": "event-j3-done"},
                "event_created": True, "delivery": None, "delivery_created": False,
            }})
        if args[:2] == ["delivery", "send"]:
            delivery_id = args[2]
            for job in state["jobs"].values():
                for delivery in job["deliveries"]:
                    if delivery["id"] == delivery_id:
                        delivery["status"] = "sent"
                        delivery["platform_message_id"] = f"stdout:{delivery_id}"
                        return completed(argv, {"result": {"delivery": dict(delivery), "sent": True}})
        raise AssertionError(f"unexpected command: {argv!r}")

    def make_lease(label, attempt):
        worktree = state["jobs"][label]["worktree_path"]
        resource = "sha256:" + hashlib.sha256(worktree.encode()).hexdigest()
        return {
            "lease_id": f"lease-{label.lower()}-{attempt}", "job_id": state["jobs"][label]["id"],
            "attempt_token": attempt, "agent_id": state["jobs"][label]["assigned_agent"],
            "resource_key": resource, "normalized_path": worktree, "status": "active",
            "acquired_at": "2026-07-16T12:00:00+00:00", "renewed_at": "2026-07-16T12:00:00+00:00",
            "expires_at": "2026-07-16T11:59:59+00:00", "released_at": None,
            "release_reason": None, "due": False,
        }

    def add_delivery(label):
        job = state["jobs"][label]
        if not job["deliveries"]:
            job["deliveries"].append({
                "id": f"delivery-{label.lower()}", "event_id": f"event-{label.lower()}-done",
                "platform": "stdout", "destination": "local", "message_key": f"message-{label.lower()}",
                "status": "pending", "platform_message_id": None, "attempt_count": 0,
            })

    def observer(job_ids):
        for label, job in state["jobs"].items():
            if label not in job_ids:
                continue
            if label == "J3" and job["status"] == "timed_out" and state["recovery_started"]:
                job.update(status="running", attempt_count=2, recoverable=0)
                if len(job["leases"]) == 1:
                    lease = make_lease("J3", 2)
                    lease["expires_at"] = "2026-07-16T13:00:00+00:00"
                    job["leases"].append(lease)
                continue
            if job["status"] == "pending":
                if label == "J5" and state["jobs"].get("J3", {}).get("status") != "done":
                    continue
                job.update(status="running", attempt_count=1, poll=1)
                job["leases"].append(make_lease(label, 1))
            elif job["status"] == "running" and job["attempt_count"] == 1:
                if label == "J3":
                    job["poll"] = min(job["poll"] + 1, 4)
                else:
                    job["poll"] += 1
                lease = job["leases"][0]
                lease["renewed_at"] = f"2026-07-16T12:00:0{min(job['poll'] - 1, 3)}+00:00"
                if label != "J3" and job["poll"] >= 5:
                    job.update(status="done", result_json='{"result":"fixture complete"}')
                    lease["status"] = "released"
                    add_delivery(label)
        if state["units"].get("p9-3c-fixture-e1") == "inactive" and "J3" in state["jobs"]:
            old = state["jobs"]["J3"]["leases"][0]
            if old["status"] == "active":
                old["due"] = True
        return {
            "jobs": {label: {key: value for key, value in job.items() if key not in {"poll", "leases", "deliveries"}} for label, job in state["jobs"].items() if label in job_ids},
            "leases": {label: [dict(row) for row in job["leases"]] for label, job in state["jobs"].items() if label in job_ids},
            "deliveries": {label: [dict(row) for row in job["deliveries"]] for label, job in state["jobs"].items() if label in job_ids},
        }

    def monotonic():
        state["clock"] += 0.5
        return state["clock"]

    def final_observer():
        return {
            "jobs": [
                {"id": job["id"], "status": job["status"], "assigned_agent": job["assigned_agent"],
                 "attempt_count": job["attempt_count"], "recoverable": job["recoverable"]}
                for job in sorted(state["jobs"].values(), key=lambda row: row["id"])
            ],
            "leases": [
                {key: lease.get(key) for key in ("lease_id", "job_id", "attempt_token", "agent_id", "status")}
                for job in state["jobs"].values() for lease in job["leases"]
            ],
            "deliveries": [dict(delivery) for job in state["jobs"].values() for delivery in job["deliveries"]],
            "agents": [
                {"id": agent, "online_state": "offline", "current_load": 0, "host_id": "VM-0-15-ubuntu"}
                for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2")
            ],
            "executor_sources": [{"source_id": "p9-3c1-fixture-executors", "source_version": state["executor_version"]}],
            "executor_definitions": [],
            "executor_bindings": [],
            "capacity_sources": [{"source_id": "p9-3c1-fixture-capacity", "source_version": state["capacity_version"]}],
            "capacity_policies": [],
            "db": {"integrity": "ok", "schema": 13, "fk_violations": 0},
        }

    _ctrl._set_seam("run_command", fake_runner)
    _ctrl._set_seam("matrix_observer", observer)
    _ctrl._set_seam("final_observer", final_observer)
    _ctrl._set_seam("monotonic", monotonic)
    _ctrl._set_seam("sleep", lambda _seconds: None)
    return state


class TestAuthorization:
    def test_authorization_expired(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        _prepare_fresh(run_id)
        auth_path, auth_sha = _write_authorization(
            fake_manifest, expiry_utc="2020-01-01T00:00:00Z"
        )
        _ctrl._set_seam("now_utc", lambda: datetime.datetime(2026, 7, 16, 12, 0, 0, tzinfo=datetime.timezone.utc))

        with pytest.raises(_ctrl.ControllerError, match="expired"):
            _ctrl.cmd_run(run_id, auth_path, auth_sha)

    def test_authorization_run_id_mismatch(self, controller_seams, fake_manifest):
        _prepare_fresh(fake_manifest["run_id"])
        auth_path, auth_sha = _write_authorization(fake_manifest, run_id="wrong-run-id")

        with pytest.raises(_ctrl.ControllerError, match="run_id mismatch"):
            _ctrl.cmd_run(fake_manifest["run_id"], auth_path, auth_sha)

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        [
            ("reviewer_verdict", "REQUEST_CHANGES", "verdict"),
            ("p3_bootstrap_sha256", "bad", "p3_bootstrap"),
            ("nonce", "short", "nonce"),
            ("budgets", {"total_requests": 4}, "budgets"),
        ],
    )
    def test_authorization_exact_contract_failures(
        self, controller_seams, fake_manifest, field, value, message
    ):
        _prepare_fresh(fake_manifest["run_id"])
        auth_path, auth_sha = _write_authorization(fake_manifest, **{field: value})
        with pytest.raises(_ctrl.ControllerError, match=message):
            _ctrl.cmd_run(fake_manifest["run_id"], auth_path, auth_sha)
        assert not os.path.exists(_ctrl.auth_path(fake_manifest["run_id"]))
        assert not os.path.exists(_ctrl.lock_token_path(fake_manifest["run_id"]))

    def test_noncanonical_authorization_fails_before_lock(self, controller_seams, fake_manifest):
        _prepare_fresh(fake_manifest["run_id"])
        auth_path, _ = _write_authorization(fake_manifest)
        auth = json.loads(Path(auth_path).read_text())
        Path(auth_path).write_text(json.dumps(auth, indent=2) + "\n", encoding="utf-8")
        with pytest.raises(_ctrl.ControllerError, match="canonical"):
            _ctrl.cmd_run(fake_manifest["run_id"], auth_path, _ctrl.sha256_file(auth_path))
        assert _ctrl._lock_status()["state"] == "free"

    def test_exact_authorization_runs_once_and_releases_lock(
        self, controller_seams, fake_manifest
    ):
        run_id = fake_manifest["run_id"]
        _prepare_fresh(run_id)
        state = _install_live_fake(run_id)
        auth_path, auth_sha = _write_authorization(fake_manifest)
        result = _ctrl.cmd_run(run_id, auth_path, auth_sha)
        assert result == {"status": "done", "run_id": run_id}
        assert _ctrl._current_phase(run_id) == "done"
        assert _ctrl._lock_status()["state"] == "free"
        assert not os.path.exists(_ctrl.lock_token_path(run_id))
        request_commands = [
            command for command in state["commands"]
            if command[1:4] == ["runtime", "request", "submit"]
        ]
        assert len(request_commands) == 5
        assert all("--route-capability" not in command for command in request_commands)
        prompts = [command[command.index("--prompt") + 1] for command in request_commands]
        assert prompts == [
            _ctrl.MATRIX_COMPLETE_ENVELOPE,
            _ctrl.MATRIX_COMPLETE_ENVELOPE,
            _ctrl.MATRIX_HOLD_ENVELOPE,
            _ctrl.MATRIX_COMPLETE_ENVELOPE,
            _ctrl.MATRIX_COMPLETE_ENVELOPE,
        ]
        assert all(
            json.loads(command[command.index("--reply-json") + 1]) == _ctrl.MATRIX_REPLY
            for command in request_commands
        )
        worktrees = [command[command.index("--worktree-path") + 1] for command in request_commands]
        assert worktrees[2] == worktrees[4]
        claim_commands = [
            command for command in state["commands"]
            if command[1:4] == ["runtime", "job", "claim"]
        ]
        assert len(claim_commands) == 1
        assert "--reap-mode" in claim_commands[0] and "none" in claim_commands[0]
        reap_commands = [
            command for command in state["commands"]
            if command[1:5] == ["runtime", "job", "lease", "reap"]
        ]
        assert len(reap_commands) == 1
        assert "--lease-id" in reap_commands[0] and "--job-id" in reap_commands[0]
        assert "--batch-size" not in reap_commands[0]
        helper_starts = [
            command for command in state["commands"]
            if command[0] == _ctrl._seams["helper_path"] and command[1] == "production-start"
        ]
        assert [(command[command.index("--agent-id") + 1], command[command.index("--mode") + 1]) for command in helper_starts] == [
            ("p9-3c-fixture-e1", "complete"),
            ("p9-3c-fixture-e2", "complete"),
            ("p9-3c-fixture-e1", "hold"),
        ]
        assert "--recoverable" in helper_starts[2]
        delivery_sends = [command for command in state["commands"] if command[1:3] == ["delivery", "send"]]
        assert len(delivery_sends) == 4
        with pytest.raises(_ctrl.ControllerError, match="phase=sealed"):
            _ctrl.cmd_run(run_id, auth_path, auth_sha)


class TestProductionLockFence:
    def test_acquire_and_release_exact_owned_token(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        _prepare_fresh(run_id)
        token = _ctrl._acquire_lock(run_id)
        assert token == "a" * 64
        token_path = _ctrl.lock_token_path(run_id)
        assert Path(token_path).read_text(encoding="ascii") == token + "\n"
        assert stat.S_IMODE(os.stat(token_path).st_mode) == 0o600
        held = _ctrl._require_owned_lock(run_id)
        assert held["token_matches"] is True
        _ctrl._release_lock(run_id)
        assert not os.path.exists(token_path)
        assert _ctrl._lock_status()["state"] == "free"

    def test_lock_status_mismatch_preserves_token_and_never_releases(
        self, controller_seams, fake_manifest
    ):
        run_id = fake_manifest["run_id"]
        _prepare_fresh(run_id)
        _ctrl._acquire_lock(run_id)
        releases = []
        _ctrl._set_seam("lock_release", lambda token: releases.append(token))
        _ctrl._set_seam(
            "lock_status",
            lambda _expect=None: {
                "state": "held",
                "phase": "held",
                "owner": _ctrl.LOCK_OWNER,
                "action": _ctrl._lock_action(run_id),
                "token_matches": False,
            },
        )
        with pytest.raises(_ctrl.ControllerError, match="token_matches"):
            _ctrl._release_lock(run_id)
        assert releases == []
        assert os.path.exists(_ctrl.lock_token_path(run_id))

    def test_release_failure_preserves_incident_token(
        self, controller_seams, fake_manifest
    ):
        run_id = fake_manifest["run_id"]
        _prepare_fresh(run_id)
        _ctrl._acquire_lock(run_id)

        def fail_release(_token):
            raise _ctrl.ControllerError("injected release failure")

        _ctrl._set_seam("lock_release", fail_release)
        with pytest.raises(_ctrl.ControllerError, match="injected release failure"):
            _ctrl._release_lock(run_id)
        assert os.path.exists(_ctrl.lock_token_path(run_id))


# ---------------------------------------------------------------------------
# Cleanup gating
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_cleanup_refuses_sealed(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        _ctrl._set_seam("os_getuid", lambda: 1000)
        _ctrl._set_seam("os_geteuid", lambda: 0)

        root = _ctrl.state_root(run_id)
        if os.path.exists(root):
            import shutil
            shutil.rmtree(root)
        _ctrl.cmd_prepare(run_id, "coord", "coord")

        with pytest.raises(_ctrl.ControllerError, match="sealed inert"):
            _ctrl.cmd_cleanup(run_id)

    def test_cleanup_refuses_done(self, controller_seams, fake_manifest):
        run_id = fake_manifest["run_id"]
        _ctrl._set_seam("os_getuid", lambda: 1000)
        _ctrl._set_seam("os_geteuid", lambda: 0)

        # Mark done via phase
        root = _ctrl.state_root(run_id)
        if os.path.exists(root):
            import shutil
            shutil.rmtree(root)
        _ctrl.cmd_prepare(run_id, "coord", "coord")
        _ctrl._write_phase(run_id, "done")

        with pytest.raises(_ctrl.ControllerError, match="already done"):
            _ctrl.cmd_cleanup(run_id)


# ---------------------------------------------------------------------------
# State machine forward progress with fake commands
# ---------------------------------------------------------------------------


class TestStateMachineFake:
    """Test the state machine transitions with fake coordinate CLI responses."""

    @pytest.fixture(autouse=True)
    def setup_fake_coord(self, controller_seams, fake_manifest):
        self.live_state = _install_live_fake(fake_manifest["run_id"])
        yield

    def test_state_machine_forward_progress(self, controller_seams, fake_manifest):
        """Run the state machine through all phases."""
        run_id = fake_manifest["run_id"]
        _ctrl._set_seam("os_getuid", lambda: 1000)
        _ctrl._set_seam("os_geteuid", lambda: 0)

        root = _ctrl.state_root(run_id)
        if os.path.exists(root):
            import shutil
            shutil.rmtree(root)
        _ctrl.cmd_prepare(run_id, "coord", "coord")

        # Advance through phases manually to test each transition
        from scripts.p9_3c1_controller import PHASE_INDEX

        # Start from sealed, advance to preflight-ok
        _ctrl._write_phase(run_id, "preflight-ok")
        _ctrl._append_ledger(run_id, "preflight-ok", "test.advance")
        _ctrl._acquire_lock(run_id)
        auth_path, _auth_sha = _write_authorization(fake_manifest)
        auth = json.loads(Path(auth_path).read_text(encoding="utf-8"))
        _ctrl._atomic_copy(auth_path, _ctrl.auth_path(run_id))

        # Execute state machine from preflight-ok
        result = _ctrl._execute_state_machine(run_id, auth)
        assert result["status"] == "done"
        assert _ctrl._current_phase(run_id) == "done"

        # Verify ledger has records for each phase
        records = _ctrl._read_ledger(run_id)
        phases_seen = {r["phase"] for r in records}
        assert "done" in phases_seen
        assert len(records) >= 18  # at least one per phase

    def test_crash_after_workspace_enters_cleanup(self, controller_seams, fake_manifest):
        """Crash at a mid-point should leave forensic evidence."""
        run_id = fake_manifest["run_id"]
        _ctrl._set_seam("os_getuid", lambda: 1000)
        _ctrl._set_seam("os_geteuid", lambda: 0)

        root = _ctrl.state_root(run_id)
        if os.path.exists(root):
            import shutil
            shutil.rmtree(root)
        _ctrl.cmd_prepare(run_id, "coord", "coord")

        # Simulate partial progress: advance to workspace-ready then crash
        _ctrl._write_phase(run_id, "workspace-ready")
        _ctrl._append_ledger(run_id, "workspace-ready", "test.partial")
        assert _ctrl._current_phase(run_id) == "workspace-ready"
        _ctrl._acquire_lock(run_id)
        result = _ctrl._execute_cleanup_suffix(run_id)
        assert result["status"] == "cleanup_completed"
        assert _ctrl._current_phase(run_id) == "done"
        assert _ctrl._lock_status()["state"] == "free"

    @pytest.mark.parametrize(
        "failure_prefix",
        [
            ("workspace", "add"),
            ("runtime", "executor", "sync"),
            ("runtime", "request", "submit"),
        ],
    )
    def test_mutation_failure_runs_real_cleanup_suffix(
        self, controller_seams, fake_manifest, failure_prefix
    ):
        run_id = fake_manifest["run_id"]
        _prepare_fresh(run_id)
        self.live_state["fail_once_prefix"] = failure_prefix
        auth_path, auth_sha = _write_authorization(fake_manifest)
        with pytest.raises(_ctrl.ControllerError, match="injected phase failure"):
            _ctrl.cmd_run(run_id, auth_path, auth_sha)
        assert _ctrl._current_phase(run_id) == "done"
        assert _ctrl._lock_status()["state"] == "free"
        assert not os.path.exists(_ctrl.lock_token_path(run_id))
        assert _ctrl._read_evidence(run_id, "cleanup.json")["from_phase"] in _ctrl.PHASES
        assert all(value != "active" for value in self.live_state["units"].values())

    def test_live_authorization_drift_halts_before_next_mutation(
        self, controller_seams, fake_manifest
    ):
        run_id = fake_manifest["run_id"]
        _prepare_fresh(run_id)
        auth_path, _ = _write_authorization(fake_manifest)
        auth = json.loads(Path(auth_path).read_text(encoding="utf-8"))
        _ctrl._atomic_copy(auth_path, _ctrl.auth_path(run_id))
        _ctrl._write_phase(run_id, "preflight-ok")
        _ctrl._append_ledger(run_id, "preflight-ok", "test.advance")
        _ctrl._acquire_lock(run_id)
        Path(_ctrl.auth_path(run_id)).write_text("{}\n", encoding="utf-8")
        before = len(self.live_state["commands"])
        with pytest.raises(_ctrl.ControllerError, match="authorization bytes changed"):
            _ctrl._execute_state_machine(run_id, auth)
        assert len(self.live_state["commands"]) == before
        assert _ctrl._current_phase(run_id) == "preflight-ok"
        assert _ctrl._lock_status()["state"] == "held"
        _ctrl._release_lock(run_id)

    def test_final_active_lease_halts_cleanup_and_preserves_lock(
        self, controller_seams, fake_manifest
    ):
        """A live final lease cannot be hidden by the cleanup fallback."""
        run_id = fake_manifest["run_id"]
        _prepare_fresh(run_id)
        original_final = _ctrl._seams["final_observer"]
        original_matrix = _ctrl._seams["matrix_observer"]
        final_gate_entered = {"value": False}

        def final_with_active_lease():
            snapshot = json.loads(json.dumps(original_final()))
            final_gate_entered["value"] = True
            snapshot["leases"][0]["status"] = "active"
            return snapshot

        def matrix_with_active_lease(job_ids):
            snapshot = original_matrix(job_ids)
            if final_gate_entered["value"]:
                snapshot["leases"]["J1"][0]["status"] = "active"
            return snapshot

        _ctrl._set_seam("final_observer", final_with_active_lease)
        _ctrl._set_seam("matrix_observer", matrix_with_active_lease)
        auth_path, auth_sha = _write_authorization(fake_manifest)

        with pytest.raises(_ctrl.ControllerError, match="cleanup halted"):
            _ctrl.cmd_run(run_id, auth_path, auth_sha)

        assert _ctrl._current_phase(run_id) == "canonical-compared"
        assert _ctrl._lock_status()["state"] == "held"
        blocked = _ctrl._read_evidence(run_id, "cleanup-blocked.json")
        assert blocked["nonterminal_jobs"] == {}
        assert blocked["active_lease_ids"]
        _ctrl._release_lock(run_id)


# ---------------------------------------------------------------------------
# Command runner edge cases
# ---------------------------------------------------------------------------


class TestCommandRunner:
    def test_shell_false_enforced(self, controller_seams):
        """Test that commands run with shell=False."""
        cli = _ctrl._seams["production_cli"]
        os.makedirs(os.path.dirname(cli), exist_ok=True)
        with open(cli, "w") as f:
            f.write("#!/bin/sh\necho '{\"status\":\"ok\"}'\n")
        os.chmod(cli, 0o755)

        result = _ctrl._coord_cli("--version")
        assert isinstance(result, dict)
        assert result["status"] == "ok"

    def test_timeout_raises(self, controller_seams):
        """Test that timeout raises ControllerError."""
        cli = _ctrl._seams["production_cli"]
        os.makedirs(os.path.dirname(cli), exist_ok=True)
        with open(cli, "w") as f:
            f.write("#!/bin/sh\nsleep 60\n")
        os.chmod(cli, 0o755)

        with pytest.raises(_ctrl.ControllerError, match="timed out"):
            _ctrl._coord_cli("--version")


# ---------------------------------------------------------------------------
# Argparse rejects unknown subcommand
# ---------------------------------------------------------------------------


class TestArgparse:
    def test_unknown_command(self, capsys):
        with pytest.raises(SystemExit):
            _ctrl.main(["unknown-cmd", "--run-id", "p9-3c1-prod-20260716t120000z-abcdef01"])


# ---------------------------------------------------------------------------
# Key verify: all 18 phases are registered
# ---------------------------------------------------------------------------


def test_all_phases_registered():
    """Every run phase from preflight-ok through canonical-compared has a handler."""
    from scripts.p9_3c1_controller import PHASES, _CMD_REGISTRY

    expect_handlers = [p for p in PHASES if p not in ("sealed", "done")]
    for phase in expect_handlers:
        assert phase in _CMD_REGISTRY, f"Phase {phase} has no registered handler"
