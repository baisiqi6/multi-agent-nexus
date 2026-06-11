"""Tests for Windows coord SSH wrapper quoting and agentd Windows compat."""

import shlex
import sys

import pytest


class TestCoordSshWinQuoting:
    """Verify shlex.quote produces POSIX-shell-safe strings for coord-local args."""

    def test_simple_args(self):
        quoted = [shlex.quote(a) for a in ["runtime", "job", "claim", "--agent-id", "win-claude"]]
        cmd = "/usr/local/bin/coord-local " + " ".join(quoted)
        assert cmd == "/usr/local/bin/coord-local runtime job claim --agent-id win-claude"

    def test_json_with_spaces_and_quotes(self):
        json_val = '{"text": "hello world", "key": "it\'s done"}'
        quoted = shlex.quote(json_val)
        assert quoted != json_val
        assert "'" in quoted

    def test_roundtrip_via_shlex_split(self):
        args = [
            "runtime", "job", "report", "job-123",
            "--agent-id", "win-claude",
            "--status", "done",
            "--result-json", '{"response_text": "ok", "duration_ms": 500}',
            "--actor", "test actor with space",
        ]
        quoted = [shlex.quote(a) for a in args]
        remote_cmd = "dummy " + " ".join(quoted)
        roundtrip = shlex.split(remote_cmd)[1:]
        assert roundtrip == args

    def test_arg_with_spaces(self):
        assert shlex.quote("test actor with space") == "'test actor with space'"

    def test_empty_string(self):
        assert shlex.quote("") == "''"


class TestAgentdWindowsSignalGuard:
    """Verify __main__.py doesn't call add_signal_handler on win32."""

    def test_platform_guard_present(self):
        with open("multinexus/agentd/__main__.py", encoding="utf-8") as f:
            source = f.read()
        assert 'sys.platform != "win32"' in source
        assert "add_signal_handler" in source
        assert "import sys" in source

    def test_add_signal_handler_under_guard(self):
        with open("multinexus/agentd/__main__.py", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if "loop.add_signal_handler" in line:
                above = "".join(lines[max(0, i - 5):i])
                assert "sys.platform" in above, f"add_signal_handler at line {i+1} not guarded"
