"""Tests for Windows coord SSH wrapper quoting and agentd Windows compat."""

import json
import shlex
import sys
from unittest.mock import patch

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

    def test_json_with_windows_path_and_chinese(self):
        result_json = json.dumps({
            "response_text": "你好，工作目录是 C:\\Users\\ADMIN\\projects",
            "session_id": "abc-123",
            "duration_ms": 5000,
        }, ensure_ascii=False)
        quoted = shlex.quote(result_json)
        roundtrip = shlex.split("dummy " + quoted)[1]
        parsed = json.loads(roundtrip)
        assert parsed["response_text"] == "你好，工作目录是 C:\\Users\\ADMIN\\projects"
        assert parsed["duration_ms"] == 5000


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


class TestCoordinateClientBaseCmd:
    """Verify _base_cmd expansion for .py wrapper on Windows."""

    def test_py_path_on_windows_expands_to_sys_executable(self):
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient
        with patch("multinexus.agentd.coordinate_client.sys") as mock_sys:
            mock_sys.platform = "win32"
            mock_sys.executable = "C:\\Python314\\python.exe"
            client = CoordinateRuntimeClient(
                cli_path="C:\\Users\\ADMIN\\scripts\\coord-ssh-win.py",
                db_path="",
            )
            assert client._base_cmd == ["C:\\Python314\\python.exe", "C:\\Users\\ADMIN\\scripts\\coord-ssh-win.py"]

    def test_cmd_path_on_windows_not_expanded(self):
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient
        with patch("multinexus.agentd.coordinate_client.sys") as mock_sys:
            mock_sys.platform = "win32"
            mock_sys.executable = "C:\\Python314\\python.exe"
            client = CoordinateRuntimeClient(
                cli_path="C:\\Users\\ADMIN\\scripts\\coord-ssh-win.cmd",
                db_path="",
            )
            assert client._base_cmd == ["C:\\Users\\ADMIN\\scripts\\coord-ssh-win.cmd"]

    def test_py_path_on_mac_not_expanded(self):
        from multinexus.agentd.coordinate_client import CoordinateRuntimeClient
        with patch("multinexus.agentd.coordinate_client.sys") as mock_sys:
            mock_sys.platform = "darwin"
            mock_sys.executable = "/usr/bin/python3"
            client = CoordinateRuntimeClient(
                cli_path="/usr/local/bin/coord-local",
                db_path="",
            )
            assert client._base_cmd == ["/usr/local/bin/coord-local"]


class TestCoordSshWinStdinPipe:
    """Verify coord-ssh-win.py uses stdin pipe on Windows to avoid list2cmdline mangling."""

    def test_windows_uses_stdin_pipe(self):
        with open("scripts/coord-ssh-win.py", encoding="utf-8") as f:
            source = f.read()
        assert "_run_via_stdin" in source
        assert 'sys.platform == "win32"' in source
        assert "sh" in source

    def test_json_arg_not_mangled_through_subprocess(self):
        import subprocess
        result = {"response_text": "C:\\Users\\ADMIN\\path 中文 'quoted'", "duration_ms": 500}
        json_str = json.dumps(result, ensure_ascii=False)
        proc = subprocess.run(
            [sys.executable, "scripts/coord-ssh-win.py", "--dry-run",
             "test", "--result-json", json_str],
            capture_output=True, text=True, encoding="utf-8",
        )
        output = proc.stdout.strip()
        assert "--result-json" in output
        # shlex.quote preserves the JSON structure; roundtrip should be valid
        import shlex
        tokens = shlex.split(output)
        json_arg = tokens[tokens.index("--result-json") + 1]
        parsed = json.loads(json_arg)
        assert parsed["response_text"] == "C:\\Users\\ADMIN\\path 中文 'quoted'"

