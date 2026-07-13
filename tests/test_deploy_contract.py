"""Contract tests for the registry-aware deploy-server.sh flow.

These tests execute the real deploy script with fake ssh/git/tar/chown binaries
and safe fixtures.  They are standalone: no Coordinate worktree path is
hardcoded.  The fake `coord-local` writes the minimal v12 schema/rows the
read-after-write verifier inspects, and a tiny fake `coordinate.db` stub
satisfies the verify helper's single Coordinate import.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path


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

_FAKE_COORD_LOCAL = '''\
#!{sys_executable}
import os, sys, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

root = os.environ.get("FAKE_SSH_ROOT", "")
mn_path = Path(root) / "opt" / "multinexus" if root else Path(__file__).resolve().parent.parent / "multinexus"
sys.path.insert(0, str(mn_path))
from multinexus.registry_authority import load_authority

db_path = Path(root) / "var/lib/coordinate/coord.sqlite3" if root else Path("coord.sqlite3")
db_path.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
now = datetime.now(timezone.utc).isoformat()

conn.executescript("""
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
""")

args = sys.argv[1:]
if "sync" not in args:
    print("fake coord-local: only sync supported", file=sys.stderr)
    sys.exit(1)
source_path = Path(args[args.index("--source") + 1])
authority = load_authority(source_path)

if args[0] == "workspace" and args[1] == "agent":
    workspace_id = args[args.index("sync") + 1]
    authority_json = {
        e.id: {"discord_user_id": e.discord_user_id, "display_name": e.display_name, "agent_type": e.agent_type}
        for e in authority.entries
    }
    conn.execute(
        "INSERT OR REPLACE INTO workspaces (id, name, path, harness_root, agent_registry_revision, agents_json, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (workspace_id, workspace_id, "/x", "docs", authority.source_version, json.dumps(authority_json), now, now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO workspace_agent_registry_sources "
        "(workspace_id, source_id, source_version, source_hash, source_path, synced_by, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (workspace_id, authority.source_id, authority.source_version, authority.source_hash, str(source_path), "deploy", now),
    )
    conn.execute(
        "DELETE FROM workspace_agent_registry_entries WHERE workspace_id = ? AND entry_kind = 'authoritative'",
        (workspace_id,),
    )
    for e in authority.entries:
        conn.execute(
            "INSERT INTO workspace_agent_registry_entries "
            "(workspace_id, agent_name, entry_kind, discord_user_id, display_name, agent_type, created_at, updated_at) "
            "VALUES (?, ?, 'authoritative', ?, ?, ?, ?, ?)",
            (workspace_id, e.id, e.discord_user_id, e.display_name, e.agent_type, now, now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO agents (id, name, role, capabilities_json, online_state, current_load, created_at, updated_at) "
            "VALUES (?, ?, 'agent', '[]', 'offline', 0, ?, ?)",
            (e.id, e.display_name, now, now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO runner_profiles (id, name, runner_type, command, working_directory_strategy, supports_stream_attach, env_json, created_at, updated_at) "
            "VALUES (?, ?, 'agent', 'agent', 'current_dir', 0, '{}', ?, ?)",
            (e.id, e.id, now, now),
        )
elif args[0] == "runtime" and args[1] == "executor":
    conn.execute(
        "INSERT OR REPLACE INTO executor_catalog_sources (source_id, source_version, catalog_hash, source_path, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (authority.source_id, authority.source_version, authority.executor_catalog_hash, str(source_path), now),
    )
    conn.execute(
        "DELETE FROM executor_definitions WHERE source_id = ?",
        (authority.source_id,),
    )
    conn.execute(
        "DELETE FROM executor_instance_bindings WHERE source_id = ?",
        (authority.source_id,),
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
else:
    print("fake coord-local: unexpected subcommand", file=sys.stderr)
    sys.exit(1)

conn.commit()
conn.close()
'''


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class DeployContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="deploy-contract-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

        self.fake_root = self.tmp / "fake-root"
        self.fake_root.mkdir()
        self.ssh_log = self.tmp / "ssh.log"

        self.bin_dir = self.tmp / "bin"
        self.bin_dir.mkdir()

        self.git_sha = "abcd1234" * 5
        self.git_branch = "agents/mac-omp/slice-4b2-deployed-agent-registry-authority"

        self._write_fake_git()
        self._write_fake_ssh()
        self._write_fake_coord_local()
        self._write_fake_systemctl()
        self._write_noop("chown")
        self._write_noop("chgrp")

        self.source_dir = self.tmp / "multinexus-src"
        self.source_dir.mkdir()
        (self.source_dir / "multinexus").mkdir()
        (self.source_dir / "scripts").mkdir()
        (self.source_dir / "config").mkdir()

        # Copy the real verifier module and helper into the fake source tree.
        repo_root = Path(__file__).parent.parent
        shutil.copy(
            repo_root / "multinexus" / "registry_authority.py",
            self.source_dir / "multinexus" / "registry_authority.py",
        )
        shutil.copy(
            repo_root / "scripts" / "agent_registry_deploy_verify.py",
            self.source_dir / "scripts" / "agent_registry_deploy_verify.py",
        )

        self.authority = self.source_dir / "config" / "agent-registry.toml"
        self.authority.write_text(
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

        # Runtime config used for local and remote parity.  Tests mutate this.
        self.runtime = self.source_dir / "agents.toml"
        self.runtime.write_text(
            textwrap.dedent("""\
            [[agents]]
            id = "mac-claude"
            display_name = "Mac Claude"
            discord_user_id = "1507329791982833775"
            adapter = "claude"
            token_env = "SECRET_TOKEN"

            [[external_agents]]
            id = "server-hermes"
            display_name = "Hermes"
            discord_user_id = "1505562531706568928"
            """),
            encoding="utf-8",
        )

        # Pre-create the remote agents.toml so the deploy heredoc `test -f` passes.
        self.remote_opt = self.fake_root / "opt" / "multinexus"
        self.remote_opt.mkdir(parents=True)
        (self.remote_opt / "agents.toml").write_text(self.runtime.read_text(), encoding="utf-8")

        # Fake coordinate venv wrapper that execs the current interpreter.
        coord_venv = self.fake_root / "opt" / "coordinate" / ".venv"
        coord_venv.mkdir(parents=True)
        (coord_venv / "bin").mkdir()
        python_wrapper = coord_venv / "bin" / "python"
        python_wrapper.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            f"fake_pkg = {str(self.tmp / 'fake-coordinate')!r}\n"
            "pp = os.environ.get('PYTHONPATH', '')\n"
            "os.environ['PYTHONPATH'] = fake_pkg + (os.pathsep + pp if pp else '')\n"
            "os.execv(sys.executable, [sys.executable] + sys.argv[1:])\n",
            encoding="utf-8",
        )
        _make_executable(python_wrapper)

        # Minimal fake coordinate package for the verify helper.
        fake_pkg = self.tmp / "fake-coordinate" / "coordinate"
        fake_pkg.mkdir(parents=True)
        (fake_pkg / "__init__.py").write_text("", encoding="utf-8")
        (fake_pkg / "db.py").write_text(_FAKE_COORDINATE_DB, encoding="utf-8")

        self.deploy_script = repo_root / "scripts" / "deploy-server.sh"
        self._env = {
            "PATH": f"{self.bin_dir}:{os.environ.get('PATH', '')}",
            "DEPLOY_HOST": "fake-host",
            "FAKE_SSH_LOG": str(self.ssh_log),
            "FAKE_SSH_ROOT": str(self.fake_root),
            "FAKE_COORD_LOCAL_BIN": str(self.bin_dir / "coord-local"),
            "FAKE_GIT_SHA": self.git_sha,
            "FAKE_GIT_BRANCH": self.git_branch,
            "FAKE_GIT_STATUS": "",
        }

    def _write_fake_git(self):
        script = self.bin_dir / "git"
        script.write_text(
            textwrap.dedent("""\
            #!/bin/sh
            case "$*" in
              *"rev-parse --is-inside-work-tree"*) exit 0 ;;
              *"status --short"*) echo "$FAKE_GIT_STATUS"; exit 0 ;;
              *"rev-parse HEAD"*) echo "$FAKE_GIT_SHA"; exit 0 ;;
              *"branch --show-current"*) echo "$FAKE_GIT_BRANCH"; exit 0 ;;
              *) echo "fake-git: unexpected args $*" >&2; exit 1 ;;
            esac
            """),
            encoding="utf-8",
        )
        _make_executable(script)

    def _write_fake_ssh(self):
        script = self.bin_dir / "ssh"
        script.write_text(
            textwrap.dedent(f"""\
            #!{sys.executable}
            import os, sys, subprocess, tempfile, textwrap

            log_path = os.environ["FAKE_SSH_LOG"]
            root = os.environ["FAKE_SSH_ROOT"]
            coord_local = os.environ.get("FAKE_COORD_LOCAL_BIN", "")

            host = sys.argv[1]
            cmd = sys.argv[2] if len(sys.argv) > 2 else ""

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{{host}}: {{cmd}}\\n")

            def rewrite(s):
                s = s.replace("/opt/multinexus", os.path.join(root, "opt/multinexus"))
                s = s.replace("/opt/coordinate", os.path.join(root, "opt/coordinate"))
                s = s.replace("/var/lib/coordinate", os.path.join(root, "var/lib/coordinate"))
                s = s.replace("/usr/local/bin/coord-local", coord_local)
                # Drop sudo wrappers; the test runner has local filesystem rights.
                s = s.replace("sudo -u coord env ", "env ")
                s = s.replace("sudo -u multinexus ", "")
                s = s.replace("sudo ", "")
                return s

            rewritten = rewrite(cmd)

            if cmd.startswith("sudo bash -s"):
                script_text = sys.stdin.read()
                rewritten_script = rewrite(script_text)
                with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tf:
                    tf.write(rewritten_script)
                    tf_path = tf.name
                try:
                    sys.exit(subprocess.run(["bash", tf_path], stdin=subprocess.DEVNULL).returncode)
                finally:
                    os.unlink(tf_path)

            if "tar -xzf - -C" in rewritten:
                sys.exit(subprocess.run(rewritten, shell=True, stdin=sys.stdin).returncode)

            sys.exit(subprocess.run(rewritten, shell=True, stdin=sys.stdin).returncode)
            """),
            encoding="utf-8",
        )
        _make_executable(script)

    def _write_fake_coord_local(self):
        script = self.bin_dir / "coord-local"
        script.write_text(
            _FAKE_COORD_LOCAL.replace("{sys_executable}", sys.executable),
            encoding="utf-8",
        )
        _make_executable(script)

    def _write_fake_systemctl(self):
        script = self.bin_dir / "systemctl"
        script.write_text(
            textwrap.dedent("""\
            #!/bin/sh
            echo "systemctl $*" >> "$FAKE_SSH_LOG"
            exit 0
            """),
            encoding="utf-8",
        )
        _make_executable(script)

    def _write_noop(self, name: str):
        script = self.bin_dir / name
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        _make_executable(script)

    def _run_deploy(self, *extra_args, dirty: bool = False) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.update(self._env)
        if dirty:
            env["FAKE_GIT_STATUS"] = " M agents.toml\n"
        cmd = [
            "bash",
            str(self.deploy_script),
            "multinexus",
            "--multinexus-src",
            str(self.source_dir),
            "--host",
            "fake-host",
            "--skip-install",
            "--no-smoke",
        ] + list(extra_args)
        return subprocess.run(cmd, capture_output=True, text=True, env=env)

    def _ssh_log(self) -> str:
        if not self.ssh_log.exists():
            return ""
        return self.ssh_log.read_text(encoding="utf-8")

    def test_local_mismatch_performs_no_remote_mutation(self):
        # Remove an entry from the local runtime config to break parity.
        self.runtime.write_text(
            textwrap.dedent("""\
            [[agents]]
            id = "mac-claude"
            display_name = "Mac Claude"
            discord_user_id = "1507329791982833775"
            """),
            encoding="utf-8",
        )
        result = self._run_deploy()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        log = self._ssh_log()
        self.assertNotIn("rsync", log)
        self.assertNotIn("coord-local", log)
        self.assertNotIn("systemctl", log)
        self.assertIn("local-parity", result.stderr)

    def test_remote_mismatch_performs_no_sync_or_restart(self):
        # Remote agents.toml is missing an entry; local matches authority.
        (self.remote_opt / "agents.toml").write_text(
            textwrap.dedent("""\
            [[agents]]
            id = "mac-claude"
            display_name = "Mac Claude"
            discord_user_id = "1507329791982833775"
            """),
            encoding="utf-8",
        )
        result = self._run_deploy()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        log = self._ssh_log()
        self.assertIn("registry_authority verify", log)  # remote parity attempted after copy
        self.assertNotIn("coord-local", log)
        self.assertNotIn("systemctl", log)
        self.assertIn("remote-parity", result.stderr)

    def test_success_orders_parity_sync_evidence_version_restart(self):
        result = self._run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self._ssh_log()
        # Order: remote parity -> sync -> committed verify -> version tee -> restart
        parity_pos = log.find("registry_authority verify")
        sync_pos = log.find("coord-local")
        verify_pos = log.find("agent_registry_deploy_verify.py")
        version_pos = log.find("VERSION_DEPLOYED")
        restart_pos = log.find("systemctl restart multinexus-discord-bridge")
        self.assertLess(parity_pos, sync_pos, log)
        self.assertLess(sync_pos, verify_pos, log)
        self.assertLess(verify_pos, version_pos, log)
        self.assertLess(version_pos, restart_pos, log)
        self.assertIn("agent_registry_deploy_verify.py", log)
        self.assertIn("--strict-effective", log)
        version_file = self.remote_opt / "VERSION_DEPLOYED"
        self.assertTrue(version_file.exists())

    def test_no_restart_still_syncs_and_verifies(self):
        result = self._run_deploy("--no-restart")
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self._ssh_log()
        self.assertIn("coord-local", log)
        self.assertIn("agent_registry_deploy_verify.py", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)

    def test_skip_install_does_not_skip_parity_or_sync(self):
        # --skip-install is already default in _run_deploy; this test documents it.
        result = self._run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self._ssh_log()
        self.assertIn("registry_authority verify", log)
        self.assertIn("coord-local", log)
        self.assertNotIn("pip install", log)

    def test_dirty_refusal(self):
        result = self._run_deploy(dirty=True)
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("refusing to deploy dirty", result.stderr)
        self.assertNotIn("coord-local", self._ssh_log())


if __name__ == "__main__":
    unittest.main()
