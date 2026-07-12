"""Contract tests for scripts/server-smoke.sh registry checks."""

import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from coordinate.db import connect, initialize, upsert_workspace, sync_workspace_agents
from coordinate.schema import migrate

from multinexus.registry_authority import AgentEntry, canonical_hash

COORDINATE_VENV = Path("/Users/yinxin/projects/coordinate/.venv")


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class SmokeContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="smoke-contract-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

        self.fake_root = self.tmp / "fake-root"
        self.fake_root.mkdir()
        self.ssh_log = self.tmp / "ssh.log"

        self.bin_dir = self.tmp / "bin"
        self.bin_dir.mkdir()

        self._write_fake_ssh()
        self._write_fake_systemctl()
        self._write_fake_coord_local()
        self._write_fake_curl()

        self.repo_root = Path(__file__).parent.parent
        self.smoke_script = self.repo_root / "scripts" / "server-smoke.sh"

        # Build authority and a matching runtime config.
        self.authority_path = self.tmp / "agent-registry.toml"
        self.authority_path.write_text(
            textwrap.dedent("""\
            [registry]
            id = "multinexus.discord"
            version = 1

            [[agents]]
            id = "mac-claude"
            display_name = "Mac Claude"
            discord_user_id = "1507329791982833775"

            [[external_agents]]
            id = "server-hermes"
            display_name = "Hermes"
            discord_user_id = "1505562531706568928"
            """),
            encoding="utf-8",
        )

        self.runtime_path = self.tmp / "agents.toml"
        self.runtime_path.write_text(
            textwrap.dedent("""\
            [[agents]]
            id = "mac-claude"
            display_name = "Mac Claude"
            discord_user_id = "1507329791982833775"
            token_env = "SECRET"

            [[external_agents]]
            id = "server-hermes"
            display_name = "Hermes"
            discord_user_id = "1505562531706568928"
            """),
            encoding="utf-8",
        )

        remote_opt = self.fake_root / "opt" / "multinexus"
        remote_opt.mkdir(parents=True)
        (remote_opt / "config").mkdir()
        shutil.copy(self.authority_path, remote_opt / "config" / "agent-registry.toml")
        shutil.copy(self.runtime_path, remote_opt / "agents.toml")

        # Fake coordinate venv wrapper.
        coord_venv = self.fake_root / "opt" / "coordinate" / ".venv"
        coord_venv.mkdir(parents=True)
        (coord_venv / "bin").mkdir()
        wrapper = coord_venv / "bin" / "python"
        wrapper.write_text(
            f"#!/bin/sh\nexec {COORDINATE_VENV / 'bin' / 'python'} \"$@\"\n",
            encoding="utf-8",
        )
        _make_executable(wrapper)

        # Copy the verify helper into the fake source tree.
        (remote_opt / "scripts").mkdir(parents=True, exist_ok=True)
        (remote_opt / "multinexus").mkdir(parents=True, exist_ok=True)
        shutil.copy(
            self.repo_root / "scripts" / "agent_registry_deploy_verify.py",
            remote_opt / "scripts" / "agent_registry_deploy_verify.py",
        )
        shutil.copy(
            self.repo_root / "multinexus" / "registry_authority.py",
            remote_opt / "multinexus" / "registry_authority.py",
        )

        self.db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        self.db_path.parent.mkdir(parents=True)
        self._sync_db()

        # VERSION_DEPLOYED files required by existing smoke checks.
        for component in ("coordinate", "multinexus"):
            version_file = self.fake_root / "opt" / component / "VERSION_DEPLOYED"
            version_file.parent.mkdir(parents=True, exist_ok=True)
            version_file.write_text("component=test\ncommit=abc\n", encoding="utf-8")

        self._env = {
            "PATH": f"{self.bin_dir}:{os.environ.get('PATH', '')}",
            "DEPLOY_HOST": "fake-host",
            "FAKE_SSH_LOG": str(self.ssh_log),
            "FAKE_SSH_ROOT": str(self.fake_root),
            "FAKE_COORDINATE_VENV": str(COORDINATE_VENV),
            "FAKE_COORD_LOCAL_BIN": str(self.bin_dir / "coord-local"),
        }

    def _sync_db(self):
        conn = initialize(str(self.db_path))
        upsert_workspace(conn, workspace_id="discord-nexus", name="discord-nexus", path="/x", harness_root="docs")
        entries = [
            AgentEntry("mac-claude", "Mac Claude", "1507329791982833775", "managed"),
            AgentEntry("server-hermes", "Hermes", "1505562531706568928", "external"),
        ]
        sync_workspace_agents(
            conn,
            workspace_id="discord-nexus",
            source_id="multinexus.discord",
            source_version=1,
            source_hash=canonical_hash(entries),
            source_path=str(self.authority_path),
            entries=[e.to_canonical_dict() for e in entries],
            replace=True,
            synced_by="test",
        )
        # Empty agents table for the runtime DB agents query.
        conn.execute("CREATE TABLE IF NOT EXISTS agents (id TEXT, online_state TEXT, host_id TEXT, last_seen_at TEXT)")
        conn.commit()
        conn.close()

    def _write_fake_ssh(self):
        script = self.bin_dir / "ssh"
        script.write_text(
            textwrap.dedent(f"""\
            #!{sys.executable}
            import os, sys, subprocess, tempfile, textwrap

            log_path = os.environ["FAKE_SSH_LOG"]
            root = os.environ["FAKE_SSH_ROOT"]
            coord_venv = os.environ.get("FAKE_COORDINATE_VENV", "")

            host = sys.argv[1]
            cmd = sys.argv[2] if len(sys.argv) > 2 else ""

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{{host}}: {{cmd}}\\n")

            def rewrite(s):
                s = s.replace("/opt/multinexus", os.path.join(root, "opt/multinexus"))
                s = s.replace("/opt/coordinate", os.path.join(root, "opt/coordinate"))
                s = s.replace("/var/lib/coordinate", os.path.join(root, "var/lib/coordinate"))
                s = s.replace("/usr/local/bin/coord-local", os.environ.get("FAKE_COORD_LOCAL_BIN", ""))
                s = s.replace("sudo -u coord env ", "env ")
                s = s.replace("sudo ", "")
                return s

            rewritten = rewrite(cmd)

            if "bash -s" in rewritten:
                script_text = sys.stdin.read()
                rewritten_script = rewrite(script_text)
                # Preserve leading VAR=value assignments (e.g. SMOKE_SINCE='...').
                env_prefix = ""
                body = rewritten
                if " bash -s" in rewritten:
                    env_prefix, body = rewritten.rsplit(" bash -s", 1)
                with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tf:
                    tf.write(rewritten_script)
                    tf_path = tf.name
                try:
                    cmd = ["bash", tf_path]
                    if env_prefix.strip():
                        import shlex
                        cmd = ["env"] + shlex.split(env_prefix) + cmd
                    sys.exit(subprocess.run(cmd, stdin=subprocess.DEVNULL).returncode)
                finally:
                    os.unlink(tf_path)

            sys.exit(subprocess.run(rewritten, shell=True, stdin=sys.stdin).returncode)
            """),
            encoding="utf-8",
        )
        _make_executable(script)

    def _write_fake_systemctl(self):
        script = self.bin_dir / "systemctl"
        script.write_text(
            textwrap.dedent("""\
            #!/bin/sh
            if [ "$1" = "is-active" ]; then
              echo "active"
              exit 0
            fi
            exit 0
            """),
            encoding="utf-8",
        )
        _make_executable(script)

    def _write_fake_coord_local(self):
        script = self.bin_dir / "coord-local"
        script.write_text(
            textwrap.dedent("""\
            #!/bin/sh
            if [ "$1" = "--version" ]; then
              echo "coord-local test"
              exit 0
            fi
            if [ "$1" = "workspace" ] && [ "$2" = "list" ]; then
              echo '{"workspaces": []}'
              exit 0
            fi
            echo "fake coord-local: unexpected $*" >&2
            exit 1
            """),
            encoding="utf-8",
        )
        _make_executable(script)

    def _write_fake_curl(self):
        script = self.bin_dir / "curl"
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        _make_executable(script)

    def _run_smoke(self) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.update(self._env)
        return subprocess.run(
            ["bash", str(self.smoke_script), "--host", "fake-host"],
            capture_output=True,
            text=True,
            env=env,
        )

    def test_smoke_passes_when_registry_matches_authority(self):
        result = self._run_smoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("registry authority", result.stdout)
        self.assertIn("server smoke OK", result.stdout)

    def test_smoke_fails_when_active_override_shadows_authority(self):
        conn = connect(str(self.db_path))
        now = "2099-01-01T00:00:00Z"
        conn.execute(
            """
            INSERT INTO workspace_agent_registry_entries
            (workspace_id, agent_name, entry_kind, discord_user_id, display_name, agent_type, created_at, updated_at)
            VALUES (?, ?, 'override', ?, ?, ?, ?, ?)
            """,
            ("discord-nexus", "mac-claude", "999999999999999999", "X", "managed", now, now),
        )
        conn.commit()
        conn.close()

        result = self._run_smoke()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("registry authority smoke failed", result.stderr)

    def test_smoke_fails_when_legacy_entries_remain(self):
        conn = connect(str(self.db_path))
        now = "2099-01-01T00:00:00Z"
        conn.execute(
            """
            INSERT INTO workspace_agent_registry_entries
            (workspace_id, agent_name, entry_kind, discord_user_id, display_name, agent_type, created_at, updated_at)
            VALUES (?, ?, 'legacy', ?, ?, ?, ?, ?)
            """,
            ("discord-nexus", "old-bot", "111111111111111111", "Old", "managed", now, now),
        )
        conn.commit()
        conn.close()

        result = self._run_smoke()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("registry authority smoke failed", result.stderr)

    def test_smoke_below_v10_fails_without_migrating_database(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA user_version = 9")
        conn.commit()
        conn.close()

        result = self._run_smoke()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("registry authority smoke failed", result.stderr)

        conn = sqlite3.connect(self.db_path)
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(version, 9, "read-only smoke must not migrate production DB")

    def test_smoke_fails_when_registry_revision_is_zero(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE workspaces SET agent_registry_revision = 0 WHERE id = ?",
            ("discord-nexus",),
        )
        conn.commit()
        conn.close()

        result = self._run_smoke()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("registry authority smoke failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
