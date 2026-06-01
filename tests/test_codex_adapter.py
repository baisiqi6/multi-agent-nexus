import tempfile
import unittest
from pathlib import Path

from discord_nexus.adapters.codex import CodexAdapter
from discord_nexus.config import _load_toml_agent
from discord_nexus.models import AgentConfig


class TestCodexAdapterPermissions(unittest.TestCase):
    def test_build_cmd_uses_bypass_flag_when_enabled(self):
        config = AgentConfig(
            id="mac-codex",
            token="token",
            adapter="codex",
            codex_bin="codex",
            codex_sandbox="danger-full-access",
            codex_dangerously_bypass_approvals_and_sandbox=True,
            work_dir="/tmp",
        )
        adapter = CodexAdapter(config)

        cmd = adapter._build_cmd(model=None)

        self.assertIn("--dangerously-bypass-approvals-and-sandbox", cmd)
        self.assertNotIn("--sandbox", cmd)

    def test_build_cmd_uses_sandbox_when_bypass_disabled(self):
        config = AgentConfig(
            id="mac-codex",
            token="token",
            adapter="codex",
            codex_bin="codex",
            codex_sandbox="danger-full-access",
            work_dir="/tmp",
        )
        adapter = CodexAdapter(config)

        cmd = adapter._build_cmd(model=None)

        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", cmd)
        self.assertIn("--sandbox", cmd)
        self.assertIn("danger-full-access", cmd)

    def test_config_loads_codex_bypass_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "agents.toml"
            path.write_text(
                """
[[agents]]
id = "mac-codex"
token = "token"
adapter = "codex"
codex_dangerously_bypass_approvals_and_sandbox = true
""",
                encoding="utf-8",
            )

            config = _load_toml_agent(path, "mac-codex")

        self.assertTrue(config.codex_dangerously_bypass_approvals_and_sandbox)


class TestCodexResumePermissions(unittest.TestCase):
    def test_resume_uses_bypass_flag_when_enabled(self):
        config = AgentConfig(
            id="mac-codex",
            token="token",
            adapter="codex",
            codex_bin="codex",
            codex_sandbox="danger-full-access",
            codex_dangerously_bypass_approvals_and_sandbox=True,
            work_dir="/tmp",
        )
        adapter = CodexAdapter(config)
        cmd: list[str] = []

        adapter._append_permission_flags(cmd, for_resume=True)

        self.assertIn("--dangerously-bypass-approvals-and-sandbox", cmd)
        self.assertNotIn("sandbox_permissions=[\"danger-full-access\"]", cmd)

    def test_resume_uses_sandbox_config_when_bypass_disabled(self):
        config = AgentConfig(
            id="mac-codex",
            token="token",
            adapter="codex",
            codex_bin="codex",
            codex_sandbox="danger-full-access",
            work_dir="/tmp",
        )
        adapter = CodexAdapter(config)
        cmd: list[str] = []

        adapter._append_permission_flags(cmd, for_resume=True)

        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", cmd)
        self.assertIn("-c", cmd)
        self.assertIn("sandbox_permissions=[\"danger-full-access\"]", cmd)
