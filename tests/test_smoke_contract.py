"""Contract tests for scripts/server-smoke.sh registry checks.

These tests are intentionally standalone: they do not import Coordinate modules
or rely on a sibling Coordinate worktree.  The DB is populated with the minimal
v12 schema/rows the smoke verifier inspects, and a tiny fake `coordinate.db`
stub satisfies the verify helper's single Coordinate import.
"""

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
from datetime import datetime, timezone
from pathlib import Path

from multinexus.registry_authority import load_authority


_FAKE_COORDINATE_DB = '''\
import sqlite3

def resolve_effective_agents(conn, workspace_id, now_utc=None):
    rows = conn.execute(
        """SELECT agent_name, discord_user_id, display_name, agent_type
           FROM workspace_agent_registry_entries
           WHERE workspace_id = ? AND entry_kind = 'authoritative'
           ORDER BY agent_name""",
        (workspace_id,),
    ).fetchall()
    return {
        row["agent_name"]: {
            "discord_user_id": row["discord_user_id"],
            "display_name": row["display_name"],
            "agent_type": row["agent_type"],
        }
        for row in rows
    }
'''


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
            version = 2

            [[executor_definitions]]
            id = "claude-code"
            provider = "anthropic-claude"
            adapter = "claude"
            capabilities = ["coding", "review"]

            [[agents]]
            id = "mac-claude"
            display_name = "Mac Claude"
            discord_user_id = "1507329791982833775"
            executor_definition_id = "claude-code"
            runner_profile_id = "mac-claude"

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
            adapter = "claude"
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

        # Fake coordinate venv wrapper that execs the current interpreter.
        coord_venv = self.fake_root / "opt" / "coordinate" / ".venv"
        coord_venv.mkdir(parents=True)
        (coord_venv / "bin").mkdir()
        wrapper = coord_venv / "bin" / "python"
        wrapper.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            f"fake_pkg = {str(self.tmp / 'fake-coordinate')!r}\n"
            "pp = os.environ.get('PYTHONPATH', '')\n"
            "os.environ['PYTHONPATH'] = fake_pkg + (os.pathsep + pp if pp else '')\n"
            "os.execv(sys.executable, [sys.executable] + sys.argv[1:])\n",
            encoding="utf-8",
        )
        _make_executable(wrapper)

        # Minimal fake coordinate package for the verify helper.
        fake_pkg = self.tmp / "fake-coordinate" / "coordinate"
        fake_pkg.mkdir(parents=True)
        (fake_pkg / "__init__.py").write_text("", encoding="utf-8")
        (fake_pkg / "db.py").write_text(_FAKE_COORDINATE_DB, encoding="utf-8")

        # Copy the verify helper and authority loader into the fake source tree.
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
            "FAKE_COORD_LOCAL_BIN": str(self.bin_dir / "coord-local"),
        }

    def _sync_db(self):
        authority = load_authority(self.authority_path)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        now = datetime.now(timezone.utc).isoformat()
        conn.executescript(
            """
            PRAGMA user_version = 12;

            CREATE TABLE IF NOT EXISTS workspaces (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              path TEXT NOT NULL,
              harness_root TEXT NOT NULL,
              agent_registry_revision INTEGER NOT NULL DEFAULT 0,
              agents_json TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workspace_agent_registry_sources (
              workspace_id TEXT PRIMARY KEY,
              source_id TEXT NOT NULL,
              source_version INTEGER NOT NULL,
              source_hash TEXT NOT NULL,
              source_path TEXT,
              synced_by TEXT,
              synced_at TEXT NOT NULL,
              FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS workspace_agent_registry_entries (
              workspace_id TEXT NOT NULL,
              agent_name TEXT NOT NULL,
              entry_kind TEXT NOT NULL CHECK(entry_kind IN ('authoritative', 'override', 'legacy')),
              discord_user_id TEXT NOT NULL,
              display_name TEXT NOT NULL,
              agent_type TEXT NOT NULL,
              expires_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY (workspace_id, agent_name, entry_kind),
              FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS agents (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              role TEXT,
              capabilities_json TEXT NOT NULL,
              online_state TEXT NOT NULL,
              current_load INTEGER NOT NULL DEFAULT 0,
              host_id TEXT,
              client_type TEXT,
              last_seen_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runner_profiles (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              runner_type TEXT NOT NULL,
              command TEXT NOT NULL,
              working_directory_strategy TEXT NOT NULL,
              supports_stream_attach INTEGER NOT NULL DEFAULT 0,
              env_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS executor_catalog_sources (
              source_id TEXT PRIMARY KEY,
              source_version INTEGER NOT NULL,
              catalog_hash TEXT NOT NULL,
              source_path TEXT,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS executor_definitions (
              id TEXT PRIMARY KEY,
              source_id TEXT NOT NULL,
              provider TEXT NOT NULL,
              adapter TEXT NOT NULL,
              capabilities_json TEXT NOT NULL,
              metadata_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(source_id) REFERENCES executor_catalog_sources(source_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS executor_instance_bindings (
              agent_id TEXT PRIMARY KEY,
              source_id TEXT NOT NULL,
              executor_definition_id TEXT NOT NULL,
              runner_profile_id TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(source_id) REFERENCES executor_catalog_sources(source_id) ON DELETE CASCADE,
              FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE,
              FOREIGN KEY(executor_definition_id) REFERENCES executor_definitions(id) ON DELETE CASCADE,
              FOREIGN KEY(runner_profile_id) REFERENCES runner_profiles(id) ON DELETE CASCADE
            );
            """
        )

        authority_json = {
            e.id: {
                "discord_user_id": e.discord_user_id,
                "display_name": e.display_name,
                "agent_type": e.agent_type,
            }
            for e in authority.entries
        }
        conn.execute(
            "INSERT INTO workspaces (id, name, path, harness_root, agent_registry_revision, agents_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("discord-nexus", "discord-nexus", "/x", "docs", 1, json.dumps(authority_json), now, now),
        )
        conn.execute(
            "INSERT INTO workspace_agent_registry_sources "
            "(workspace_id, source_id, source_version, source_hash, source_path, synced_by, synced_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("discord-nexus", authority.source_id, authority.source_version, authority.source_hash, str(self.authority_path), "test", now),
        )
        for e in authority.entries:
            conn.execute(
                "INSERT INTO workspace_agent_registry_entries "
                "(workspace_id, agent_name, entry_kind, discord_user_id, display_name, agent_type, created_at, updated_at) "
                "VALUES (?, ?, 'authoritative', ?, ?, ?, ?, ?)",
                ("discord-nexus", e.id, e.discord_user_id, e.display_name, e.agent_type, now, now),
            )
            conn.execute(
                "INSERT INTO agents (id, name, role, capabilities_json, online_state, current_load, created_at, updated_at) "
                "VALUES (?, ?, 'agent', '[]', 'offline', 0, ?, ?)",
                (e.id, e.display_name, now, now),
            )
            conn.execute(
                "INSERT INTO runner_profiles (id, name, runner_type, command, working_directory_strategy, supports_stream_attach, env_json, created_at, updated_at) "
                "VALUES (?, ?, 'agent', 'agent', 'current_dir', 0, '{}', ?, ?)",
                (e.id, e.id, now, now),
            )

        conn.execute(
            "INSERT INTO executor_catalog_sources (source_id, source_version, catalog_hash, source_path, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (authority.source_id, authority.source_version, authority.executor_catalog_hash, str(self.authority_path), now),
        )
        for d in authority.executor_definitions:
            conn.execute(
                "INSERT INTO executor_definitions (id, source_id, provider, adapter, capabilities_json, metadata_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, '{}', ?, ?)",
                (d.id, authority.source_id, d.provider, d.adapter, json.dumps(list(d.capabilities)), now, now),
            )
        for b in authority.executor_bindings:
            conn.execute(
                "INSERT INTO executor_instance_bindings (agent_id, source_id, executor_definition_id, runner_profile_id, enabled, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (b.agent_id, authority.source_id, b.executor_definition_id, b.runner_profile_id, int(b.enabled), now, now),
            )
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
        conn = sqlite3.connect(str(self.db_path))
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
        conn = sqlite3.connect(str(self.db_path))
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
