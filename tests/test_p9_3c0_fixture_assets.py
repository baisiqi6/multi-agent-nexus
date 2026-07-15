"""Tests for P9-3C0 Package 2 zero-provider fixture assets."""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import stat
import time
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path

from multinexus.config import _load_toml_agent
from multinexus.executor_capacity_authority import (
    CapacityCatalog,
    load_capacity_authority,
)
from multinexus.registry_authority import (
    AuthorityError,
    ExecutorDefinition,
    ExecutorInstanceBinding,
    canonical_executor_catalog_hash,
    canonical_hash,
    load_authority,
)


FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "multinexus" / "fixture"
FIXTURE_BIN = FIXTURE_ROOT / "bin" / "p9-3c0-fixture.py"
UNIT_HELPER = FIXTURE_ROOT / "bin" / "p9-3c0-unit.sh"
CONFIG_DIR = FIXTURE_ROOT / "config"
REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_AUTHORITY = REPO_ROOT / "config" / "agent-registry.toml"


RUNBOOK = FIXTURE_ROOT / "docs" / "runbook.md"

MOCK_UNIT_USER = "testuser"
MOCK_UNIT_GROUP = "testgroup"
MOCK_UNIT_ID = "1001"
MOCK_WRAPPER_SHA = "abc123def456abc123def456abc123def456abc123def456abc123def456abcd"
MOCK_DEFINITION_SHA = "def456abc123def456abc123def456abc123def456abc123def456abc123abcd"


def _prepare_helper_manifest(state_root: Path, run_id: str, wrapper: Path) -> None:
    state_dir = state_root / run_id
    state_dir.mkdir(parents=True, exist_ok=True)
    state_dir.chmod(0o750)
    for name in ("lock", "ledger", "context"):
        directory = state_dir / name
        directory.mkdir(exist_ok=True)
        directory.chmod(0o700)
    for name in ("controller.lock", "unit-helper.lock"):
        lock_file = state_dir / "lock" / name
        lock_file.touch()
        lock_file.chmod(0o600)
    ledger = state_dir / "ledger" / "events.jsonl"
    ledger.touch()
    ledger.chmod(0o600)
    record = (
        f"wrapper_raw={wrapper}"
        f"\twrapper_dev_inode_size_nlink_uid_gid_mode="
        f"0:0:256:1:0:{MOCK_UNIT_ID}:750"
        f"\twrapper_sha256={MOCK_WRAPPER_SHA}\n"
    )
    manifest = state_dir / "wrapper.manifest"
    manifest.write_text(record, encoding="utf-8")
    manifest.chmod(0o640)


def _helper_mock_prelude() -> str:
    """Source-safe authority seams for local/macOS fixture helper tests."""
    return f'''
source "{UNIT_HELPER}"
_p9c0_identity_lookup_user() {{ echo {MOCK_UNIT_ID}; }}
_p9c0_identity_lookup_group() {{ echo {MOCK_UNIT_ID}; }}
_p9c0_stat_file() {{
    case "$1" in
        */wrapper.manifest) echo "0:0:128:1:0:{MOCK_UNIT_ID}:640" ;;
        */systemd.verify.service) echo "0:0:0:1:0:0:600" ;;
        */controller.lock|*/unit-helper.lock) echo "0:0:0:1:0:0:600" ;;
        *) echo "0:0:256:1:0:{MOCK_UNIT_ID}:750" ;;
    esac
}}
_p9c0_sha256_file() {{
    case "$1" in
        */systemd.verify.service) echo "{MOCK_DEFINITION_SHA}" ;;
        *) echo "{MOCK_WRAPPER_SHA}" ;;
    esac
}}
_p9c0_systemd_analyze() {{ return 0; }}
_p9c0_set_owner_group_mode() {{ chmod "$4" "$1"; }}
_p9c0_lock_file_authority() {{ return 0; }}
'''


def _run_sourced_helper(argv: list[str], *, extra_funcs: str = ""):
    command = " ".join(shlex.quote(str(value)) for value in argv)
    script = f"{_helper_mock_prelude()}\n{extra_funcs}\nmain {command}\n"
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True
    )


def _run_fixture_process(argv, stdin):
    """Run the fixture executable in-process with virtual hooks.

    Mirrors main() but injects fake sleep/emit/descendant/signal-wait so tests
    never wait 75 real seconds. Validation errors are formatted like main().
    """
    import importlib.util
    import io

    spec = importlib.util.spec_from_file_location("fixture", FIXTURE_BIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    stdout = io.StringIO()
    stderr = io.StringIO()
    sleeps = []
    emitted = []

    def fake_sleep(seconds):
        sleeps.append(seconds)

    def fake_emit(event):
        emitted.append(event)

    def fake_descendant():
        return 12345

    def fake_wait(_deadline_func):
        pass

    old_stdin = sys.stdin
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdin = io.StringIO(stdin)
    sys.stdout = stdout
    sys.stderr = stderr
    try:
        try:
            module.validate_argv([str(FIXTURE_BIN), *argv])
        except module.FixtureError as exc:
            print(f"fixture argv error: {exc}", file=sys.stderr)
            return subprocess.CompletedProcess(
                args=[str(FIXTURE_BIN), *argv],
                returncode=1,
                stdout=stdout.getvalue(),
                stderr=stderr.getvalue(),
            )
        try:
            envelope = module.parse_envelope(stdin)
        except module.FixtureError as exc:
            print(f"fixture envelope error: {exc}", file=sys.stderr)
            return subprocess.CompletedProcess(
                args=[str(FIXTURE_BIN), *argv],
                returncode=1,
                stdout=stdout.getvalue(),
                stderr=stderr.getvalue(),
            )
        code = module.run_fixture(
            envelope,
            sleep_fn=fake_sleep,
            emit_fn=fake_emit,
            descendant_fn=fake_descendant,
            signal_wait_fn=fake_wait,
        )
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    out_lines = "\n".join(json.dumps(e, separators=(",", ":")) for e in emitted)
    return subprocess.CompletedProcess(
        args=[str(FIXTURE_BIN), *argv],
        returncode=code,
        stdout=out_lines,
        stderr=stderr.getvalue(),
    )


class FixtureExecutableArgvTests(unittest.TestCase):
    def _run(self, argv, stdin=""):
        return _run_fixture_process(argv, stdin)

    def _valid_envelope(self, mode="complete", spawn_descendant=False):
        return json.dumps({
            "contract_version": 1,
            "mode": mode,
            "quiet_seconds": 75,
            "spawn_descendant": spawn_descendant,
        })

    def test_exact_argv_accepts_reordering(self):
        for argv in (
            ["-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages"],
            ["--output-format", "stream-json", "-p", "--include-partial-messages", "--verbose"],
            ["--include-partial-messages", "-p", "--verbose", "--output-format", "stream-json"],
        ):
            with self.subTest(argv=argv):
                result = self._run(argv, self._valid_envelope())
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), json.dumps({
                    "is_error": False,
                    "result": "fixture complete",
                    "subtype": "success",
                    "type": "result",
                }, separators=(",", ":")))

    def test_missing_option_rejected(self):
        result = self._run(["-p", "--verbose", "--output-format", "stream-json"], self._valid_envelope())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required option", result.stderr)

    def test_duplicate_option_rejected(self):
        result = self._run(["-p", "-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages"], self._valid_envelope())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate", result.stderr)

    def test_unknown_option_rejected(self):
        result = self._run(["-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages", "--extra"], self._valid_envelope())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown option", result.stderr)

    def test_positional_rejected(self):
        result = self._run(["-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages", "oops"], self._valid_envelope())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("positional", result.stderr)

    def test_model_option_rejected(self):
        result = self._run(["-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages", "--model", "x"], self._valid_envelope())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden option", result.stderr)

    def test_resume_option_rejected(self):
        result = self._run(["-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages", "--resume", "x"], self._valid_envelope())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden option", result.stderr)

    def test_dangerous_permission_option_rejected(self):
        result = self._run(["-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages", "--dangerously-skip-permissions"], self._valid_envelope())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden option", result.stderr)

    def test_wrong_output_format_rejected(self):
        result = self._run(["-p", "--verbose", "--output-format", "json", "--include-partial-messages"], self._valid_envelope())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stream-json", result.stderr)


_VALID_ENVELOPE_ARGV = ["-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages"]


class FixtureExecutableEnvelopeTests(unittest.TestCase):
    def _run(self, stdin):
        return _run_fixture_process(_VALID_ENVELOPE_ARGV, stdin)

    def test_valid_envelope_ok(self):
        stdin = json.dumps({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": False,
        })
        result = self._run(stdin)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_key_rejected(self):
        stdin = json.dumps({"contract_version": 1, "mode": "complete", "quiet_seconds": 75})
        result = self._run(stdin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incorrect key set", result.stderr)

    def test_extra_key_rejected(self):
        stdin = json.dumps({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": False,
            "extra": 1,
        })
        result = self._run(stdin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incorrect key set", result.stderr)

    def test_contract_version_bool_rejected(self):
        stdin = json.dumps({
            "contract_version": True,
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": False,
        })
        result = self._run(stdin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract_version", result.stderr)

    def test_contract_version_string_rejected(self):
        stdin = json.dumps({
            "contract_version": "1",
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": False,
        })
        result = self._run(stdin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract_version", result.stderr)

    def test_quiet_seconds_not_75_rejected(self):
        stdin = json.dumps({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 74,
            "spawn_descendant": False,
        })
        result = self._run(stdin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("quiet_seconds", result.stderr)

    def test_quiet_seconds_float_rejected(self):
        stdin = json.dumps({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 75.0,
            "spawn_descendant": False,
        })
        result = self._run(stdin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("quiet_seconds", result.stderr)

    def test_spawn_descendant_non_bool_rejected(self):
        stdin = json.dumps({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": "false",
        })
        result = self._run(stdin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("spawn_descendant", result.stderr)

    def test_spawn_descendant_true_requires_hold(self):
        stdin = json.dumps({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": True,
        })
        result = self._run(stdin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("spawn_descendant=true", result.stderr)

    def test_trailing_document_rejected(self):
        stdin = json.dumps({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": False,
        }) + "\n{}"
        result = self._run(stdin)
        self.assertNotEqual(result.returncode, 0)

    def test_extra_whitespace_around_json_ok(self):
        stdin = "  " + json.dumps({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": False,
        }) + "\n\n"
        result = self._run(stdin)
        self.assertEqual(result.returncode, 0, result.stderr)


class FixtureExecutableVirtualTests(unittest.TestCase):
    def _load_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("fixture", FIXTURE_BIN)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_complete_emits_after_virtual_sleep_and_zero_before(self):
        module = self._load_module()
        sleeps = []
        emitted = []

        def fake_sleep(seconds):
            sleeps.append(seconds)

        def fake_emit(event):
            emitted.append(event)

        code = module.run_fixture({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": False,
        }, sleep_fn=fake_sleep, emit_fn=fake_emit)

        self.assertEqual(code, 0)
        self.assertEqual(sleeps, [75])
        self.assertEqual(emitted, [{
            "is_error": False,
            "result": "fixture complete",
            "subtype": "success",
            "type": "result",
        }])

    def test_hold_silent_and_waits_for_signal(self):
        module = self._load_module()
        emitted = []
        waits = []

        def fake_emit(event):
            emitted.append(event)

        def fake_wait(deadline_func):
            waits.append(deadline_func())

        code = module.run_fixture({
            "contract_version": 1,
            "mode": "hold",
            "quiet_seconds": 75,
            "spawn_descendant": False,
        }, emit_fn=fake_emit, signal_wait_fn=fake_wait)

        self.assertEqual(code, 0)
        self.assertEqual(emitted, [])
        self.assertEqual(waits, [float("inf")])

    def test_hold_descendant_started_with_fixed_argv(self):
        module = self._load_module()
        descendant_calls = []

        def fake_descendant():
            descendant_calls.append("spawned")
            return 12345

        def fake_wait(_deadline_func):
            pass

        code = module.run_fixture({
            "contract_version": 1,
            "mode": "hold",
            "quiet_seconds": 75,
            "spawn_descendant": True,
        }, descendant_fn=fake_descendant, signal_wait_fn=fake_wait)

        self.assertEqual(code, 0)
        self.assertEqual(descendant_calls, ["spawned"])

    def test_main_passes_real_sleep_to_run_fixture(self):
        """Production entrypoint must bind real time.sleep and real hooks."""
        module = self._load_module()
        captured = {}

        def spy_run_fixture(envelope, **kwargs):
            captured.update(kwargs)
            return 0

        module.run_fixture = spy_run_fixture
        import io

        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps({
            "contract_version": 1,
            "mode": "complete",
            "quiet_seconds": 75,
            "spawn_descendant": False,
        }))
        try:
            code = module.main([
                str(FIXTURE_BIN),
                "-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages",
            ])
        finally:
            sys.stdin = old_stdin

        self.assertEqual(code, 0)
        self.assertIs(captured.get("sleep_fn"), time.sleep)
        self.assertIs(captured.get("descendant_fn"), module._start_descendant)
        self.assertIs(captured.get("signal_wait_fn"), module._wait_for_signal)

    def test_terminate_descendant_reaps_with_wnohang_loop(self):
        """SIGTERM must be followed by a bounded WNOHANG reap loop."""
        module = self._load_module()

        class FakeTime:
            def __init__(self):
                self.t = 0.0
                self.sleeps = []

            def monotonic(self):
                self.t += 0.1
                return self.t

            def sleep(self, seconds):
                self.sleeps.append(seconds)

        fake_time = FakeTime()
        waitpid_calls = []
        kill_calls = []

        def fake_kill(pid, sig):
            kill_calls.append((pid, sig))

        def fake_waitpid(pid, options):
            waitpid_calls.append((pid, options))
            if len(waitpid_calls) < 3:
                return (0, 0)
            return (pid, 0)

        old_time = module.time
        old_os_kill = module.os.kill
        old_os_waitpid = module.os.waitpid
        module.time = fake_time
        module.os.kill = fake_kill
        module.os.waitpid = fake_waitpid
        try:
            module._terminate_descendant(42)
        finally:
            module.time = old_time
            module.os.kill = old_os_kill
            module.os.waitpid = old_os_waitpid

        self.assertEqual(kill_calls, [(42, signal.SIGTERM)])
        self.assertGreaterEqual(len(waitpid_calls), 3)
        self.assertTrue(all(options == os.WNOHANG for _, options in waitpid_calls))
        self.assertEqual(waitpid_calls[-1][0], 42)

    def test_no_network_or_credential_imports(self):
        source = FIXTURE_BIN.read_text(encoding="utf-8")
        forbidden = [
            "import socket", "import urllib", "import http", "import requests",
            "import shutil", "import subprocess", "configparser", "tomllib",
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source, f"fixture may not use {token!r}")
        # No environment credential reads.
        self.assertNotIn("os.environ", source)
        self.assertNotIn("getenv", source)
        # No arbitrary file IO beyond required stdin/descendant spawn.
        self.assertNotIn("open(", source)
        self.assertNotIn(".write(", source)
        # No provider binary reference.
        self.assertNotIn('"claude"', source)
        self.assertNotIn("claude_bin", source)


class FixtureExecutableSignalTests(unittest.TestCase):
    def test_fixture_bin_is_executable(self):
        mode = FIXTURE_BIN.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)


class AgentConfigRenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="p9c0-render-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.state_root = self.tmp / "state"
        self.state_root.mkdir()
        self.fixture_bin = self.tmp / "fixture.py"
        self.fixture_bin.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        self.fixture_bin.chmod(0o755)
        self.wrapper = self.state_root / "coord-local"
        self.wrapper.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
        self.wrapper.chmod(0o755)
        self.coord_db = self.state_root / "db" / "coord.sqlite3"
        self.coord_db.parent.mkdir()
        self.work_dir = self.state_root / "work"
        self.work_dir.mkdir()
        _prepare_helper_manifest(self.state_root, "test-run", self.wrapper)

    def _run_render(self, *extra_args):
        return _run_sourced_helper(
            ["render",
             "--state-root", str(self.state_root),
             "--run-id", "test-run",
             "--fixture-bin", str(self.fixture_bin),
             "--wrapper", str(self.wrapper),
             "--coord-db", str(self.coord_db),
             "--work-dir", str(self.work_dir),
             "--python", sys.executable,
             "--repo-root", str(REPO_ROOT),
             "--user", MOCK_UNIT_USER,
             "--group", MOCK_UNIT_GROUP,
             *extra_args]
        )

    def test_render_creates_config_and_loads_both_agents(self):
        result = self._run_render()
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = self.state_root / "test-run" / "agents.rendered.toml"
        self.assertTrue(rendered.exists())
        self.assertEqual(oct(rendered.stat().st_mode)[-3:], "640")

        for agent_id in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
            with self.subTest(agent_id=agent_id):
                cfg = _load_toml_agent(rendered, agent_id, require_token=False)
                self.assertEqual(cfg.claude_bin, str(self.fixture_bin))
                self.assertEqual(cfg.timeout, 240)
                self.assertEqual(cfg.first_byte_timeout, 90)
                self.assertEqual(cfg.activity_timeout, 90)
                self.assertEqual(cfg.system_prompt, "")
                self.assertEqual(cfg.adapter, "claude")
                self.assertTrue(cfg.agentd_mode)

        data = tomllib.loads(rendered.read_text(encoding="utf-8"))
        e1_ctx = data["defaults"]["context_db_path"]
        e2_ctx = data["agents"][1]["context_db_path"]
        self.assertNotEqual(e1_ctx, e2_ctx)

    def test_render_rejects_leftover_placeholder(self):
        # Create a deliberately broken template directory with a duplicated marker.
        broken_repo = self.tmp / "broken-repo"
        broken_config = broken_repo / "multinexus" / "fixture" / "config"
        broken_config.mkdir(parents=True)
        shutil.copy(FIXTURE_ROOT / "config" / "agents.fixture.toml", broken_config / "agents.fixture.toml")
        # Append an extra occurrence of one placeholder so replace_once fails.
        (broken_config / "agents.fixture.toml").write_text(
            (broken_config / "agents.fixture.toml").read_text(encoding="utf-8")
            + '\nextra = "__P9C0_COORDINATOR_CLI__"\n',
            encoding="utf-8",
        )
        result = self._run_render("--repo-root", str(broken_repo))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("marker", result.stderr.lower())

    def test_render_rejects_production_coord_db(self):
        result = self._run_render("--coord-db", "/var/lib/coordinate/coord.sqlite3")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("production", result.stderr)

    def test_render_preserves_controller_ownership_matrix(self):
        # The Package 3 controller owns directory modes; helper render preserves them.
        self.state_root.chmod(0o755)
        result = self._run_render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(oct(self.state_root.stat().st_mode)[-3:], "755")
        run_dir = self.state_root / "test-run"
        self.assertEqual(oct(run_dir.stat().st_mode)[-3:], "750")
        self.assertEqual(oct((run_dir / "lock").stat().st_mode)[-3:], "700")
        self.assertEqual(oct((run_dir / "lock" / "unit-helper.lock").stat().st_mode)[-3:], "600")
        self.assertEqual(oct((run_dir / "agents.rendered.toml").stat().st_mode)[-3:], "640")
        self.assertEqual(oct((run_dir / "values.rendered").stat().st_mode)[-3:], "600")
        self.assertEqual(oct((run_dir / "ledger").stat().st_mode)[-3:], "700")
        self.assertEqual(oct((run_dir / "ledger" / "events.jsonl").stat().st_mode)[-3:], "600")

    def test_render_rejects_missing_template(self):
        empty_repo = self.tmp / "empty-repo"
        empty_repo.mkdir()
        result = self._run_render("--repo-root", str(empty_repo))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing fixture template", result.stderr)

    def test_render_rejects_missing_fixture_bin_at_equality_gate(self):
        missing_bin = self.tmp / "does-not-exist.py"
        result = self._run_render("--fixture-bin", str(missing_bin))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mismatch", result.stderr.lower())

    def test_render_rejects_production_wrapper(self):
        result = self._run_render("--wrapper", "/usr/local/bin/coord-local")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("production", result.stderr)

    def test_render_rejects_symlink_to_production_wrapper_target(self):
        # Create a symlink whose target resolves to the production wrapper path.
        # The target need not exist; resolution still follows the symlink.
        link = self.tmp / "coord-local-link"
        link.symlink_to("/usr/local/bin/coord-local")
        result = self._run_render("--wrapper", str(link))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("production", result.stderr)

    def test_render_rejects_non_absolute_paths(self):
        result = self._run_render("--fixture-bin", "fixture.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("absolute", result.stderr)

    def test_render_rejects_coord_db_outside_state_root(self):
        outside_db = self.tmp / "outside.sqlite3"
        result = self._run_render("--coord-db", str(outside_db))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("under state-root", result.stderr)


class AuthorityTests(unittest.TestCase):
    def test_all_executor_versions_parse(self):
        versions = {
            1: (CONFIG_DIR / "executor.fixture.v1-disabled.toml"),
            2: (CONFIG_DIR / "executor.fixture.v2-enabled.toml"),
            3: (CONFIG_DIR / "executor.fixture.v3-disabled.toml"),
            4: (CONFIG_DIR / "executor.fixture.v4-empty.toml"),
        }
        hashes = set()
        for version, path in versions.items():
            auth = load_authority(path)
            self.assertEqual(auth.source_id, "p9-3c0-fixture-executors")
            self.assertEqual(auth.source_version, version)
            if version == 4:
                self.assertEqual(auth.executor_definitions, [])
                self.assertEqual(auth.executor_bindings, [])
            else:
                self.assertEqual(len(auth.executor_definitions), 1)
                self.assertEqual(auth.executor_definitions[0].id, "p9-3c-local-fixture")
                self.assertEqual(auth.executor_definitions[0].provider, "local-fixture")
                self.assertEqual(auth.executor_definitions[0].adapter, "claude")
                self.assertEqual(list(auth.executor_definitions[0].capabilities), ["coding"])
                self.assertEqual(len(auth.executor_bindings), 2)
                enabled = {b.agent_id: b.enabled for b in auth.executor_bindings}
                if version == 2:
                    self.assertTrue(enabled.get("p9-3c-fixture-e1"))
                    self.assertTrue(enabled.get("p9-3c-fixture-e2"))
                else:
                    self.assertFalse(enabled.get("p9-3c-fixture-e1"))
                    self.assertFalse(enabled.get("p9-3c-fixture-e2"))
            hashes.add(auth.executor_catalog_hash)
        self.assertEqual(len(hashes), 4)

    def test_synthetic_discord_ids_exact_and_unique(self):
        auth = load_authority(CONFIG_DIR / "executor.fixture.v2-enabled.toml")
        by_id = {e.id: e for e in auth.entries}
        self.assertEqual(by_id["p9-3c-fixture-e1"].discord_user_id, "1")
        self.assertEqual(by_id["p9-3c-fixture-e2"].discord_user_id, "2")
        self.assertNotEqual(
            by_id["p9-3c-fixture-e1"].discord_user_id,
            by_id["p9-3c-fixture-e2"].discord_user_id,
        )

    def test_fixture_ids_absent_from_canonical_authority(self):
        text = CANONICAL_AUTHORITY.read_text(encoding="utf-8")
        self.assertNotIn("p9-3c-fixture-e1", text)
        self.assertNotIn("p9-3c-fixture-e2", text)

    def test_synthetic_ids_do_not_collide_with_canonical(self):
        canonical = load_authority(CANONICAL_AUTHORITY)
        canonical_ids = {e.discord_user_id for e in canonical.entries}
        self.assertNotIn("1", canonical_ids)
        self.assertNotIn("2", canonical_ids)

    def test_executor_catalog_hash_matches_computed(self):
        auth = load_authority(CONFIG_DIR / "executor.fixture.v2-enabled.toml")
        computed = canonical_executor_catalog_hash(
            auth.source_id,
            auth.source_version,
            auth.executor_definitions,
            auth.executor_bindings,
        )
        self.assertEqual(auth.executor_catalog_hash, computed)

    def test_roster_hash_excludes_executor_bindings(self):
        v1 = load_authority(CONFIG_DIR / "executor.fixture.v1-disabled.toml")
        v2 = load_authority(CONFIG_DIR / "executor.fixture.v2-enabled.toml")
        self.assertEqual(v1.source_hash, v2.source_hash)

    def test_capacity_versions_parse_and_distinct(self):
        v1 = load_capacity_authority(CONFIG_DIR / "capacity.fixture.v1.toml")
        v2 = load_capacity_authority(CONFIG_DIR / "capacity.fixture.v2-empty.toml")
        self.assertEqual(v1.source_id, "p9-3c0-fixture-capacity")
        self.assertEqual(v1.source_version, 1)
        self.assertEqual(len(v1.policies), 2)
        self.assertEqual(
            {p.agent_id: p.max_concurrent_jobs for p in v1.policies},
            {"p9-3c-fixture-e1": 1, "p9-3c-fixture-e2": 1},
        )
        self.assertEqual(v2.source_id, "p9-3c0-fixture-capacity")
        self.assertEqual(v2.source_version, 2)
        self.assertEqual(len(v2.policies), 0)
        self.assertNotEqual(v1.catalog_hash, v2.catalog_hash)

    def test_staging_order_hashes(self):
        order = [
            CONFIG_DIR / "executor.fixture.v1-disabled.toml",
            CONFIG_DIR / "capacity.fixture.v1.toml",
            CONFIG_DIR / "executor.fixture.v2-enabled.toml",
            CONFIG_DIR / "executor.fixture.v3-disabled.toml",
            CONFIG_DIR / "capacity.fixture.v2-empty.toml",
            CONFIG_DIR / "executor.fixture.v4-empty.toml",
        ]
        hashes = []
        for path in order:
            if "capacity" in path.name:
                cat = load_capacity_authority(path)
                hashes.append((path.name, cat.catalog_hash))
            else:
                auth = load_authority(path)
                hashes.append((path.name, auth.executor_catalog_hash))
        seen = set()
        for name, h in hashes:
            self.assertNotIn(h, seen, f"duplicate hash for {name}")
            seen.add(h)


class UnitHelperStaticTests(unittest.TestCase):
    def test_bash_syntax_ok(self):
        result = subprocess.run(
            ["bash", "-n", str(UNIT_HELPER)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_eval_or_test_mode(self):
        source = UNIT_HELPER.read_text(encoding="utf-8")
        self.assertNotIn("eval ", source)
        self.assertNotIn("P9C0_TEST_MODE", source)
        self.assertNotIn("pkill", source)
        self.assertNotIn("killall", source)

    def test_runbook_has_package3_operator_and_resume_contract(self):
        source = RUNBOOK.read_text(encoding="utf-8")
        section2 = source.split("## 2. Package 3 isolated sidecar operator contract")[1].split("## 3.")[0]
        self.assertNotIn("@<file>", section2)
        self.assertIn("p9-3c0-local-verify.sh prepare", section2)
        self.assertIn("p9-3c0-local-verify.sh verify", section2)
        self.assertIn("p9-3c0-cleanup.sh cleanup", section2)
        self.assertIn("<run-id>-r2", section2)
        self.assertIn("executor v1 disabled -> capacity v1 -> executor v2 enabled", section2)
        self.assertIn("executor v3 disabled -> capacity v2 empty -> executor v4 empty", section2)
        self.assertIn("Re-run the same `verify` command after interruption", section2)
        self.assertNotIn("UNAUTHORIZED until approved", source)

    def test_sourcing_does_not_run_main(self):
        result = subprocess.run(
            ["bash", "-c", f'source "{UNIT_HELPER}" && type _p9c0_cmd_render >/dev/null && echo sourced'],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sourced", result.stdout)


class UnitHelperFunctionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="p9c0-helper-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.state_root = self.tmp / "state"
        self.state_root.mkdir()
        self.fixture_bin = self.tmp / "fixture.py"
        self.fixture_bin.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        self.fixture_bin.chmod(0o755)
        self.wrapper = self.state_root / "coord-local"
        self.wrapper.write_text("#!/bin/sh\necho test-wrapper\n", encoding="utf-8")
        self.wrapper.chmod(0o755)
        self.coord_db = self.state_root / "db" / "coord.sqlite3"
        self.coord_db.parent.mkdir()
        self.work_dir = self.state_root / "work"
        self.work_dir.mkdir()
        self.repo_root = REPO_ROOT

        _prepare_helper_manifest(self.state_root, "test-run", self.wrapper)

        self._render()

    def _render(self):
        result = _run_sourced_helper(
            ["render",
             "--state-root", str(self.state_root),
             "--run-id", "test-run",
             "--fixture-bin", str(self.fixture_bin),
             "--wrapper", str(self.wrapper),
             "--coord-db", str(self.coord_db),
             "--work-dir", str(self.work_dir),
             "--python", sys.executable,
             "--repo-root", str(self.repo_root),
             "--user", MOCK_UNIT_USER,
             "--group", MOCK_UNIT_GROUP]
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def _source_with_mocks(self, extra_funcs=""):
        return f"{_helper_mock_prelude()}\n{extra_funcs}\n"

    def test_run_id_grammar_rejected(self):
        for bad in ("", "Upper", "under_score", "a--b", "a b", "1234567890123456789012345678901234567890123456789012345678901234567890"):
            with self.subTest(run_id=bad):
                result = _run_sourced_helper(
                    ["render",
                     "--state-root", str(self.state_root),
                     "--run-id", bad,
                     "--fixture-bin", str(self.fixture_bin),
                     "--wrapper", str(self.wrapper),
                     "--coord-db", str(self.coord_db),
                     "--work-dir", str(self.work_dir),
                     "--python", sys.executable,
                     "--repo-root", str(self.repo_root),
                     "--user", MOCK_UNIT_USER,
                     "--group", MOCK_UNIT_GROUP]
                )
                self.assertNotEqual(result.returncode, 0, result.stderr)

    def test_start_mock_records_systemd_argv_and_properties(self):
        calls = self.tmp / "systemd_calls.txt"
        properties = self.tmp / "properties.txt"
        script = self._source_with_mocks(f"""
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            MainPID) echo 1234 ;;
            ControlGroup) echo /system.slice/p9-3c-fixture-e1-test-run.service ;;
            ActiveState) echo active ;;
            Result) echo success ;;
            User) echo testuser ;;
            Group) echo testgroup ;;
            WorkingDirectory) echo {self.work_dir} ;;
            RuntimeMaxUSec) echo 300000000 ;;
            TimeoutStopUSec) echo 30000000 ;;
            KillMode) echo control-group ;;
            IPAddressDeny) echo any ;;
            RestrictAddressFamilies) echo AF_UNIX ;;
            NoNewPrivileges) echo yes ;;
            PrivateTmp) echo yes ;;
            ProtectSystem) echo strict ;;
            ProtectHome) echo yes ;;
            BindPaths) echo {self.state_root}:{self.state_root}:rbind ;;
            ReadWritePaths) echo {self.state_root} ;;
            UnsetEnvironment) echo "${{P9C0_UNSET_ENVIRONMENT_NAMES//,/ }}" ;;
            UMask) echo 0077 ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{
    printf '%s\\n' "$*" >> "{calls}"
}}
_p9c0_real_date_ms() {{ echo 80000; }}
_p9c0_cmd_start --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --mode hold --user testuser --group testgroup
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls_text = calls.read_text(encoding="utf-8")
        self.assertIn("--unit=p9-3c-fixture-e1-test-run.service", calls_text)
        self.assertIn("--property=RuntimeMaxSec=300", calls_text)
        self.assertIn("--property=IPAddressDeny=any", calls_text)
        self.assertIn("--property=RestrictAddressFamilies=AF_UNIX", calls_text)
        self.assertIn(f"--property=BindPaths={self.state_root}", calls_text)
        self.assertIn("env -i", calls_text)
        self.assertIn(f"env -i -C {self.repo_root}", calls_text)
        self.assertIn("--property=UnsetEnvironment=", calls_text)
        self.assertNotIn("UnsetEnvironment=*", calls_text)
        self.assertIn("-m multinexus.agentd", calls_text)
        self.assertIn("--config", calls_text)
        self.assertIn("--agent p9-3c-fixture-e1", calls_text)
        self.assertNotIn("--recoverable", calls_text)

    def test_start_post_mismatch_triggers_stop(self):
        calls = self.tmp / "systemd_calls.txt"
        cgroup_procs = self.tmp / "cgroup_post_mismatch.procs"
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
: > "$cgroup_procs"
_p9c0_real_cgroup_procs_path() {{ printf '%s\\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            MainPID) echo 1234 ;;
            ControlGroup) echo /system.slice/p9-3c-fixture-e1-test-run.service ;;
            ActiveState) echo inactive ;;
            Result) echo success ;;
            User) echo wronguser ;;
            Group) echo testgroup ;;
            WorkingDirectory) echo {self.work_dir} ;;
            RuntimeMaxUSec) echo 300000000 ;;
            TimeoutStopUSec) echo 30000000 ;;
            KillMode) echo control-group ;;
            IPAddressDeny) echo any ;;
            RestrictAddressFamilies) echo AF_UNIX ;;
            NoNewPrivileges) echo yes ;;
            PrivateTmp) echo yes ;;
            ProtectSystem) echo strict ;;
            ProtectHome) echo yes ;;
            BindPaths) echo {self.state_root}:{self.state_root}:rbind ;;
            ReadWritePaths) echo {self.state_root} ;;
            UMask) echo 0077 ;;
            *) echo "" ;;
        esac
    fi
    return 0
}}
_p9c0_real_run_systemd_run() {{
    printf '%s\\n' "$*" >> "{calls}"
}}
_p9c0_real_date_ms() {{ echo 80000; }}
_p9c0_cmd_start --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --mode hold --user testuser --group testgroup
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stderr)
        calls_text = calls.read_text(encoding="utf-8")
        self.assertIn("stop p9-3c-fixture-e1-test-run.service", calls_text)
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("post-start-mismatch", ledger)
        self.assertIn("post-start-cleanup", ledger)

    def _seed_unit_line(self, agent_id="p9-3c-fixture-e1", mode="hold", cgroup=None):
        unit = f"{agent_id}-test-run.service"
        if cgroup is None:
            cgroup = f"/system.slice/{unit}"
        ledger = self.state_root / "test-run" / "ledger" / "events.jsonl"
        ledger.write_text(
            ledger.read_text(encoding="utf-8")
            + f"unit {unit} agent={agent_id} mode={mode} start_ms=80000 main_pid=1234 cgroup={cgroup} state=active result=success\n",
            encoding="utf-8",
        )
        return unit, cgroup

    def test_crash_stop_kills_exact_unit_before_stop_and_records_mode(self):
        self.setUp()
        unit, _ = self._seed_unit_line()
        calls = self.tmp / "systemd_crash_calls.txt"
        stopped = self.tmp / "stopped"
        cgroup_procs = self.tmp / "cgroup_crash.procs"
        cgroup_procs.write_text("", encoding="utf-8")
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
stopped="{stopped}"
_p9c0_real_cgroup_procs_path() {{ printf '%s\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\n' "$*" >> "{calls}"
    if [[ $1 == kill ]]; then return 0; fi
    if [[ $1 == stop ]]; then : > "$stopped"; return 0; fi
    if [[ $1 == show && $3 == ActiveState ]]; then
        [[ -f "$stopped" ]] && echo inactive || echo active
    fi
}}
_p9c0_real_date_ms() {{ echo 160000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run \
    --agent-id p9-3c-fixture-e1 --crash \
    --fixture-start-monotonic-ms 80000 --evidence-run-id test-run
""")
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = calls.read_text(encoding="utf-8").splitlines()
        kill = f"kill --kill-whom=all --signal=SIGKILL {unit}"
        stop = f"stop {unit}"
        self.assertIn(kill, lines)
        self.assertIn(stop, lines)
        self.assertLess(lines.index(kill), lines.index(stop))
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn(
            "termination=crash kill_signal=SIGKILL kill_result=ok", ledger
        )

    def test_crash_stop_active_kill_failure_cleans_then_fails_closed(self):
        self.setUp()
        unit, _ = self._seed_unit_line()
        calls = self.tmp / "systemd_crash_failure_calls.txt"
        stopped = self.tmp / "stopped"
        cgroup_procs = self.tmp / "cgroup_crash_failure.procs"
        cgroup_procs.write_text("", encoding="utf-8")
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
stopped="{stopped}"
_p9c0_real_cgroup_procs_path() {{ printf '%s\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\n' "$*" >> "{calls}"
    if [[ $1 == kill ]]; then return 9; fi
    if [[ $1 == stop ]]; then : > "$stopped"; return 0; fi
    if [[ $1 == show && $3 == ActiveState ]]; then
        [[ -f "$stopped" ]] && echo inactive || echo active
    fi
}}
_p9c0_real_date_ms() {{ echo 160000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run \
    --agent-id p9-3c-fixture-e1 --crash \
    --fixture-start-monotonic-ms 80000 --evidence-run-id test-run
""")
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"stop {unit}", calls.read_text(encoding="utf-8"))
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("cgroup-empty", ledger)
        self.assertIn(
            "termination=crash kill_signal=SIGKILL kill_result=failed", ledger
        )

    def test_crash_stop_inactive_kill_nonzero_is_not_needed(self):
        self.setUp()
        self._seed_unit_line()
        calls = self.tmp / "systemd_crash_inactive_calls.txt"
        cgroup_procs = self.tmp / "cgroup_crash_inactive.procs"
        cgroup_procs.write_text("", encoding="utf-8")
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
_p9c0_real_cgroup_procs_path() {{ printf '%s\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\n' "$*" >> "{calls}"
    if [[ $1 == kill ]]; then return 5; fi
    if [[ $1 == show && $3 == ActiveState ]]; then echo inactive; fi
    return 0
}}
_p9c0_real_date_ms() {{ echo 160000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run \
    --agent-id p9-3c-fixture-e1 --crash \
    --fixture-start-monotonic-ms 80000 --evidence-run-id test-run
""")
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("kill_result=not-needed", ledger)

    def test_graceful_stop_never_calls_systemctl_kill(self):
        self.setUp()
        self._seed_unit_line()
        calls = self.tmp / "systemd_graceful_calls.txt"
        cgroup_procs = self.tmp / "cgroup_graceful.procs"
        cgroup_procs.write_text("", encoding="utf-8")
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
_p9c0_real_cgroup_procs_path() {{ printf '%s\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\n' "$*" >> "{calls}"
    if [[ $1 == show && $3 == ActiveState ]]; then echo inactive; fi
    return 0
}}
_p9c0_real_date_ms() {{ echo 160000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run \
    --agent-id p9-3c-fixture-e1 \
    --fixture-start-monotonic-ms 80000 --evidence-run-id test-run
""")
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("kill ", calls.read_text(encoding="utf-8"))
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn(
            "termination=graceful kill_signal=none kill_result=not-requested", ledger
        )

    def test_stop_timing_accepted_boundaries(self):
        for elapsed in (75000, 80000, 84999):
            with self.subTest(elapsed=elapsed):
                self.setUp()
                self._seed_unit_line()
                calls = self.tmp / f"systemd_calls_{elapsed}.txt"
                cgroup_procs = self.tmp / f"cgroup_{elapsed}.procs"
                start_ms = 80000
                requested_ms = start_ms + elapsed
                script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
: > "$cgroup_procs"
_p9c0_real_cgroup_procs_path() {{ printf '%s\\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo inactive ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo {requested_ms}; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms {start_ms} --evidence-run-id test-run
""")
                result = subprocess.run(
                    ["bash", "-c", script],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
                self.assertIn("cgroup-empty", ledger)
                self.assertIn("stop unit=", ledger)

    def test_stop_timing_rejected_and_still_cleans(self):
        for label, start_ms, requested_ms in (
            ("late", 0, 85000),
            ("early", 80000, 70000),
            ("future", 90000, 80000),
            ("non-decimal", "abc", 85000),
        ):
            with self.subTest(label=label):
                self.setUp()
                self._seed_unit_line()
                calls = self.tmp / f"systemd_calls_fail_{label}.txt"
                cgroup_procs = self.tmp / f"cgroup_fail_{label}.procs"
                script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
: > "$cgroup_procs"
_p9c0_real_cgroup_procs_path() {{ printf '%s\\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo inactive ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo {requested_ms}; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms {start_ms} --evidence-run-id test-run
""")
                result = subprocess.run(
                    ["bash", "-c", script],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0, result.stderr)
                calls_text = calls.read_text(encoding="utf-8")
                self.assertIn("stop p9-3c-fixture-e1-test-run.service", calls_text)
                ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
                self.assertIn("cgroup-empty", ledger)
                self.assertIn("stop unit=", ledger)

    def test_stop_mismatched_run_id_rejected(self):
        self.setUp()
        self._seed_unit_line()
        calls = self.tmp / "systemd_calls_mismatch.txt"
        cgroup_procs = self.tmp / "cgroup_mismatch.procs"
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
: > "$cgroup_procs"
_p9c0_real_cgroup_procs_path() {{ printf '%s\\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo inactive ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo 85000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms 0 --evidence-run-id other-run
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("run-id-mismatch", (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8"))

    def test_stop_uses_recorded_cgroup_when_post_stop_control_group_empty(self):
        self.setUp()
        unit, cgroup = self._seed_unit_line()
        calls = self.tmp / "systemd_calls_recorded_cgroup.txt"
        cgroup_procs = self.tmp / "cgroup_recorded.procs"
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
: > "$cgroup_procs"
_p9c0_real_cgroup_procs_path() {{ printf '%s\\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo inactive ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo 80000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms 0 --evidence-run-id test-run
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("cgroup-empty", ledger)
        self.assertIn(f"cgroup={cgroup}", ledger)

    def test_stop_fails_closed_when_recorded_cgroup_has_processes(self):
        self.setUp()
        unit, cgroup = self._seed_unit_line()
        calls = self.tmp / "systemd_calls_nonempty_cgroup.txt"
        cgroup_procs = self.tmp / "cgroup_nonempty.procs"
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
printf '1234\\n' > "$cgroup_procs"
_p9c0_real_cgroup_procs_path() {{ printf '%s\\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo inactive ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo 80000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms 0 --evidence-run-id test-run
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stderr)
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("cgroup-not-empty", ledger)
        self.assertNotIn("cgroup-empty", ledger)

    def test_stop_fails_closed_when_cgroup_procs_is_unreadable(self):
        self.setUp()
        unit, cgroup = self._seed_unit_line()
        calls = self.tmp / "systemd_calls_unreadable_cgroup.txt"
        # Simulate an existing but unreadable cgroup.procs by pointing at a directory.
        cgroup_procs = self.tmp / "cgroup_unreadable.d"
        cgroup_procs.mkdir()
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
_p9c0_real_cgroup_procs_path() {{ printf '%s\\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo inactive ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo 80000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms 0 --evidence-run-id test-run
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stderr)
        calls_text = calls.read_text(encoding="utf-8")
        self.assertIn("stop p9-3c-fixture-e1-test-run.service", calls_text)
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("cgroup-proof-read-failed", ledger)
        self.assertNotIn("cgroup-empty", ledger)

    def test_stop_fails_closed_when_cgroup_procs_read_fails_after_precheck(self):
        """Readable regular file passes -f/-r, but the actual read seam fails."""
        self.setUp()
        unit, cgroup = self._seed_unit_line()
        calls = self.tmp / "systemd_calls_read_fail.txt"
        cgroup_procs = self.tmp / "cgroup_read_fail.procs"
        # Regular file that exists and is readable (pre-check succeeds).
        cgroup_procs.write_text("", encoding="utf-8")
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
_p9c0_real_cgroup_procs_path() {{ printf '%s\\n' "$cgroup_procs"; }}
_p9c0_real_read_cgroup_procs() {{ return 1; }}
_p9c0_real_sleep() {{ :; }}
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo inactive ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo 80000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms 0 --evidence-run-id test-run
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stderr)
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("cgroup-proof-read-failed", ledger)
        self.assertNotIn("cgroup-empty", ledger)
        self.assertNotIn("cgroup-not-empty", ledger)

    def test_stop_fails_closed_when_unit_never_becomes_inactive(self):
        self.setUp()
        unit, cgroup = self._seed_unit_line()
        calls = self.tmp / "systemd_calls_active.txt"
        cgroup_procs = self.tmp / "cgroup_active.procs"
        sleeps = self.tmp / "sleeps.txt"
        script = self._source_with_mocks(f"""
cgroup_procs="{cgroup_procs}"
: > "$cgroup_procs"
_p9c0_real_cgroup_procs_path() {{ printf '%s\\n' "$cgroup_procs"; }}
_p9c0_real_sleep() {{ printf '%s\\n' "$1" >> "{sleeps}"; }}
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo active ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo 80000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms 0 --evidence-run-id test-run
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stderr)
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("stop-inactive-timeout", ledger)
        self.assertNotIn("cgroup-empty", ledger)
        self.assertGreaterEqual(sleeps.read_text(encoding="utf-8").strip().count("\n") + 1, 1)

    def test_stop_fails_closed_when_recorded_cgroup_malformed(self):
        self.setUp()
        # Seed a unit line with a cgroup that could escape /sys/fs/cgroup.
        ledger = self.state_root / "test-run" / "ledger" / "events.jsonl"
        ledger.write_text(
            ledger.read_text(encoding="utf-8")
            + "unit p9-3c-fixture-e1-test-run.service agent=p9-3c-fixture-e1 mode=hold start_ms=80000 main_pid=1234 cgroup=/system.slice/../../etc/passwd state=active result=success\n",
            encoding="utf-8",
        )
        calls = self.tmp / "systemd_calls_malformed_cgroup.txt"
        script = self._source_with_mocks(f"""
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo inactive ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo 80000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms 0 --evidence-run-id test-run
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stderr)
        calls_text = calls.read_text(encoding="utf-8")
        self.assertIn("stop p9-3c-fixture-e1-test-run.service", calls_text)
        ledger_text = ledger.read_text(encoding="utf-8")
        self.assertIn("cgroup-proof-invalid", ledger_text)
        self.assertNotIn("cgroup-empty", ledger_text)

    def test_stop_fails_closed_when_recorded_cgroup_missing(self):
        self.setUp()
        ledger = self.state_root / "test-run" / "ledger" / "events.jsonl"
        ledger.write_text(
            ledger.read_text(encoding="utf-8")
            + "unit p9-3c-fixture-e1-test-run.service agent=p9-3c-fixture-e1 mode=hold start_ms=80000 main_pid=1234 state=active result=success\n",
            encoding="utf-8",
        )
        calls = self.tmp / "systemd_calls_missing_cgroup.txt"
        script = self._source_with_mocks(f"""
_p9c0_real_systemctl() {{
    printf '%s\\n' "$*" >> "{calls}"
    if [[ $1 == show ]]; then
        case $3 in
            ActiveState) echo inactive ;;
            ControlGroup) echo "" ;;
            *) echo "" ;;
        esac
    fi
}}
_p9c0_real_run_systemd_run() {{ true; }}
_p9c0_real_date_ms() {{ echo 80000; }}
_p9c0_cmd_stop --state-root {self.state_root} --run-id test-run --agent-id p9-3c-fixture-e1 --fixture-start-monotonic-ms 0 --evidence-run-id test-run
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stderr)
        calls_text = calls.read_text(encoding="utf-8")
        self.assertIn("stop p9-3c-fixture-e1-test-run.service", calls_text)
        ledger = (self.state_root / "test-run" / "ledger" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("stop unit=", ledger)
        self.assertNotIn("cgroup-empty", ledger)

        self.setUp()
        ledger = self.state_root / "test-run" / "ledger" / "events.jsonl"
        ledger.write_text(
            "unit p9-3c-fixture-e1-test-run.service agent=p9-3c-fixture-e1\n",
            encoding="utf-8",
        )
        result = _run_sourced_helper(
            ["cleanup",
             "--state-root", str(self.state_root),
             "--run-id", "test-run",
             "--agent-id", "p9-3c-fixture-e1"]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cgroup proof missing", result.stderr)

    def test_require_ledger_unit_uses_exact_identity(self):
        # A ledger record whose unit name differs only by replacing .service with
        # a different character must not satisfy the exact unit identity check.
        self.setUp()
        ledger = self.state_root / "test-run" / "ledger" / "events.jsonl"
        ledger.write_text(
            ledger.read_text(encoding="utf-8")
            + "unit p9-3c-fixture-e1-test-runXservice agent=p9-3c-fixture-e1 mode=hold\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["bash", str(UNIT_HELPER), "status",
             "--state-root", str(self.state_root),
             "--run-id", "test-run",
             "--agent-id", "p9-3c-fixture-e1"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unit not in ledger", result.stderr)

    def test_recorded_cgroup_rejects_near_unit_identity(self):
        # A ledger line that would match via regex wildcard must not be selected
        # for cgroup extraction.
        self.setUp()
        ledger = self.state_root / "test-run" / "ledger" / "events.jsonl"
        ledger.write_text(
            "unit p9-3c-fixture-e1-test-runXservice agent=p9-3c-fixture-e1 mode=hold start_ms=0 main_pid=0 cgroup=/system.slice/other.service state=active result=success\n",
            encoding="utf-8",
        )
        script = self._source_with_mocks(f"""
P9C0_STATE_ROOT={self.state_root}
P9C0_RUN_ID=test-run
output=$(_p9c0_recorded_cgroup_for_unit p9-3c-fixture-e1-test-run.service 2>&1) || true
echo "$output"
""")
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertIn("unit not in ledger", result.stdout + result.stderr)
        self.assertNotIn("/system.slice/other.service", result.stdout + result.stderr)

    def test_cleanup_deletes_only_ledger_files(self):
        self.setUp()
        ledger = self.state_root / "test-run" / "ledger" / "events.jsonl"
        ledger.write_text(
            ledger.read_text(encoding="utf-8")
            + "unit p9-3c-fixture-e1-test-run.service agent=p9-3c-fixture-e1\n"
            + "cgroup-empty unit=p9-3c-fixture-e1-test-run.service\n",
            encoding="utf-8",
        )
        script = self._source_with_mocks(f'''
_p9c0_cmd_cleanup --state-root "{self.state_root}" --run-id test-run --agent-id p9-3c-fixture-e1
''')
        result = subprocess.run(
            ["bash", "-c", script], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(ledger.exists())

    def test_with_lock_serializes_two_contenders(self):
        log = self.tmp / "lock_order.log"
        lock_dir = self.tmp / "run-lock-test" / "lock"
        lock_dir.mkdir(parents=True, exist_ok=True)
        (lock_dir / "unit-helper.lock").touch()
        script = self._source_with_mocks(f"""
_p9c0_real_sleep() {{ sleep "$1"; }}
holder() {{
    echo holder-enter >> "{log}"
    _p9c0_sleep 0.2
    echo holder-exit >> "{log}"
}}
contender() {{
    echo contender-enter >> "{log}"
}}
_p9c0_with_lock "{self.tmp}" "run-lock-test" holder &
pid=$!
wait $pid
_p9c0_with_lock "{self.tmp}" "run-lock-test" contender
""")
        subprocess.run(["bash", "-c", script], timeout=5, check=True)
        lines = log.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(lines, ["holder-enter", "holder-exit", "contender-enter"])

    def test_with_lock_blocks_second_contender_until_first_releases(self):
        marker = self.tmp / "holder.marker"
        lock_dir = self.tmp / "run-block-test" / "lock"
        lock_dir.mkdir(parents=True, exist_ok=True)
        (lock_dir / "unit-helper.lock").touch()
        holder_script = self._source_with_mocks(f"""
_p9c0_real_sleep() {{ sleep "$1"; }}
holder() {{
    touch "{marker}"
    _p9c0_sleep 1
}}
_p9c0_with_lock "{self.tmp}" "run-block-test" holder
""")
        contender_script = self._source_with_mocks(f"""
contender() {{ echo ok; }}
_p9c0_with_lock "{self.tmp}" "run-block-test" contender
""")
        holder = subprocess.Popen(
            ["bash", "-c", holder_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 2
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(marker.exists(), "holder did not acquire lock")
        try:
            subprocess.run(
                ["bash", "-c", contender_script],
                timeout=0.3,
                check=True,
            )
            self.fail("contender should have blocked on the held lock")
        except subprocess.TimeoutExpired:
            pass
        holder.wait(timeout=5)

    def test_render_holds_exclusive_lock(self):
        record = self.tmp / "lock_calls.txt"
        run_id = "lock-render-run"
        _prepare_helper_manifest(self.state_root, run_id, self.wrapper)
        script = f"""{_helper_mock_prelude()}
_p9c0_real_flock() {{ printf '%s\\n' "$*" >> "{record}"; }}
_p9c0_cmd_render \
  --state-root {self.state_root} \
  --run-id {run_id} \
  --fixture-bin {self.fixture_bin} \
  --wrapper {self.wrapper} \
  --coord-db {self.coord_db} \
  --work-dir {self.work_dir} \
  --python {sys.executable} \
  --repo-root {self.repo_root} \
  --user {MOCK_UNIT_USER} \
  --group {MOCK_UNIT_GROUP}
"""
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(record.exists())
        self.assertIn("-x 9", record.read_text(encoding="utf-8"))
        lock_file = self.state_root / run_id / "lock" / "unit-helper.lock"
        self.assertTrue(lock_file.exists())
        self.assertEqual(oct(lock_file.stat().st_mode)[-3:], "600")
        self.assertEqual(oct((self.state_root / run_id).stat().st_mode)[-3:], "750")


class DeploymentStaticTests(unittest.TestCase):
    def test_fixture_files_in_expected_source_location(self):
        self.assertTrue(FIXTURE_ROOT.exists())
        self.assertTrue((FIXTURE_ROOT / "bin" / "p9-3c0-fixture.py").exists())
        self.assertTrue((FIXTURE_ROOT / "bin" / "p9-3c0-unit.sh").exists())

    def test_fixture_bin_mode_is_executable(self):
        bin_mode = (FIXTURE_ROOT / "bin" / "p9-3c0-fixture.py").stat().st_mode
        self.assertTrue(bin_mode & stat.S_IXUSR)
        self.assertTrue(bin_mode & stat.S_IXGRP)
        self.assertTrue(bin_mode & stat.S_IXOTH)

    def test_fixture_helper_mode_is_executable(self):
        bin_mode = (FIXTURE_ROOT / "bin" / "p9-3c0-unit.sh").stat().st_mode
        self.assertTrue(bin_mode & stat.S_IXUSR)
        self.assertTrue(bin_mode & stat.S_IXGRP)
        self.assertTrue(bin_mode & stat.S_IXOTH)

    def test_config_modes_are_not_executable(self):
        for path in CONFIG_DIR.iterdir():
            mode = path.stat().st_mode
            self.assertFalse(mode & stat.S_IXUSR, f"{path} must not be executable")


if __name__ == "__main__":
    unittest.main()
