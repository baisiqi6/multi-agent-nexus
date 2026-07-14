"""Contract tests for the registry-aware deploy-server.sh flow.

These tests execute the real deploy script with fake ssh/git/tar/chown binaries
and safe fixtures.  They are standalone: no Coordinate worktree path is
hardcoded.  The fake `coord-local` writes the v13 projection schema/rows the
read-after-write verifier inspects, and a tiny fake `coordinate.db` stub
satisfies the verify helper's single Coordinate import.
"""

import json
import os
import re
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

_FAKE_EXECUTOR_CAPACITY = '''\
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

EXPECTED_CAPACITY_SOURCE_ID = "multinexus.discord.capacity"
SNAPSHOT_CONTRACT_VERSION = 1


class CapacityError(ValueError):
    pass


def _cj(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def capture_capacity_snapshot(conn, target_source_id, output_path):
    source = None
    try:
        row = conn.execute(
            "SELECT * FROM executor_capacity_sources WHERE source_id = ?",
            (target_source_id,),
        ).fetchone()
        if row is not None:
            source = dict(row)
    except sqlite3.OperationalError:
        pass
    if source is None:
        captured_state = None
    else:
        policies = []
        try:
            for r in conn.execute(
                "SELECT * FROM executor_capacity_policies WHERE source_id = ? ORDER BY agent_id",
                (target_source_id,),
            ).fetchall():
                policies.append(dict(r))
        except sqlite3.OperationalError:
            pass
        captured_state = {"source": source, "policies": policies}
    inner = {
        "contract_version": SNAPSHOT_CONTRACT_VERSION,
        "target_source_id": target_source_id,
        "captured_state": captured_state,
    }
    digest = hashlib.sha256(_cj(inner).encode("utf-8")).hexdigest()
    envelope = {"snapshot": inner, "snapshot_sha256": digest}
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".cap-snap-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(_cj(envelope).encode("utf-8"))
        os.replace(tmp, str(p))
        os.chmod(str(p), 0o600)
        if os.environ.get("FAKE_SNAPSHOT_CAPTURE_FAILURE_AFTER_WRITE") == "1":
            raise RuntimeError("injected post-write snapshot capture failure")
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return envelope


def restore_capacity_snapshot(conn, target_source_id, snapshot_path):
    if os.environ.get("FAKE_RESTORE_FAILURE") == "1":
        raise RuntimeError("injected restore failure")
    raw = Path(snapshot_path).read_bytes()
    envelope = json.loads(raw.decode("utf-8"))
    inner = envelope["snapshot"]
    captured_state = inner["captured_state"]
    try:
        conn.execute("DELETE FROM executor_capacity_policies WHERE source_id = ?", (target_source_id,))
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("DELETE FROM executor_capacity_sources WHERE source_id = ?", (target_source_id,))
    except sqlite3.OperationalError:
        pass
    if captured_state is not None:
        s = captured_state["source"]
        conn.execute(
            "INSERT OR REPLACE INTO executor_capacity_sources (source_id, source_version, catalog_hash, source_path, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (s["source_id"], s["source_version"], s["catalog_hash"], s.get("source_path"), s["updated_at"]),
        )
        for p in captured_state.get("policies", []):
            conn.execute(
                "INSERT OR REPLACE INTO executor_capacity_policies (agent_id, source_id, source_version, catalog_hash, capacity_policy_id, max_concurrent_jobs, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (p["agent_id"], p["source_id"], p["source_version"], p["catalog_hash"], p["capacity_policy_id"], p["max_concurrent_jobs"], p["created_at"], p["updated_at"]),
            )
    conn.commit()
    return envelope
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
from multinexus.executor_capacity_authority import load_capacity_authority

db_path = Path(root) / "var/lib/coordinate/coord.sqlite3" if root else Path("coord.sqlite3")
db_path.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
now = os.environ.get("FAKE_COORD_NOW") or datetime.now(timezone.utc).isoformat()

conn.executescript("""
PRAGMA user_version = 13;

CREATE TABLE IF NOT EXISTS executor_capacity_sources (
  source_id TEXT PRIMARY KEY,
  source_version INTEGER NOT NULL,
  catalog_hash TEXT NOT NULL,
  source_path TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS executor_capacity_policies (
  agent_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  source_version INTEGER NOT NULL,
  catalog_hash TEXT NOT NULL,
  capacity_policy_id TEXT NOT NULL,
  max_concurrent_jobs INTEGER NOT NULL CHECK(max_concurrent_jobs BETWEEN 1 AND 32),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES executor_capacity_sources(source_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS execution_attempt_leases (
  lease_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  attempt_token INTEGER NOT NULL CHECK(attempt_token > 0),
  agent_id TEXT NOT NULL,
  runner_profile_id TEXT NOT NULL,
  host_id TEXT NOT NULL,
  resource_kind TEXT NOT NULL CHECK(resource_kind = 'worktree'),
  resource_key TEXT NOT NULL,
  normalized_path TEXT NOT NULL,
  capacity_policy_id TEXT,
  max_concurrent_jobs INTEGER NOT NULL CHECK(max_concurrent_jobs BETWEEN 1 AND 32),
  status TEXT NOT NULL CHECK(status IN ('active', 'released', 'expired')),
  acquired_at TEXT NOT NULL,
  renewed_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  released_at TEXT,
  release_reason TEXT,
  UNIQUE(job_id, attempt_token),
  FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE RESTRICT,
  FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  FOREIGN KEY(runner_profile_id) REFERENCES runner_profiles(id) ON DELETE RESTRICT
);

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
if "list" in args:
    print("capacity list OK")
    sys.exit(0)
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
elif args[0] == "runtime" and args[1] == "capacity":
    if "list" in args:
        print("capacity list OK")
        sys.exit(0)
    if os.environ.get("FAKE_CAPACITY_SYNC_FAILURE") == "1":
        print("fake coord-local: injected capacity sync failure", file=sys.stderr)
        sys.exit(1)
    capacity = load_capacity_authority(source_path)
    conn.execute(
        "INSERT OR REPLACE INTO executor_capacity_sources (source_id, source_version, catalog_hash, source_path, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (capacity.source_id, capacity.source_version, capacity.catalog_hash, str(source_path), now),
    )
    conn.execute(
        "DELETE FROM executor_capacity_policies WHERE source_id = ?",
        (capacity.source_id,),
    )
    for p in capacity.policies:
        policy_id = "sha256:" + __import__("hashlib").sha256(
            __import__("json").dumps({
                "agent_id": p.agent_id,
                "catalog_hash": capacity.catalog_hash,
                "contract_version": 1,
                "max_concurrent_jobs": p.max_concurrent_jobs,
                "source_id": capacity.source_id,
                "source_version": capacity.source_version,
            }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        conn.execute(
            "INSERT INTO executor_capacity_policies (agent_id, source_id, source_version, catalog_hash, capacity_policy_id, max_concurrent_jobs, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (p.agent_id, capacity.source_id, capacity.source_version, capacity.catalog_hash, policy_id, p.max_concurrent_jobs, now, now),
        )
    # Fault-injection: tamper a policy id once so the committed verifier fails on
    # the first attempt, then leave the marker so the restore attempt is clean.
    tamper_marker = Path(root) / ".capacity_verify_tamper_done"
    if os.environ.get("FAKE_CAPACITY_VERIFY_FAILURE") == "1" and not tamper_marker.exists():
        conn.execute(
            "UPDATE executor_capacity_policies SET capacity_policy_id = ? WHERE agent_id = ?",
            ("sha256:tampered", "mac-claude"),
        )
        tamper_marker.write_text("done", encoding="utf-8")
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
            repo_root / "multinexus" / "executor_capacity_authority.py",
            self.source_dir / "multinexus" / "executor_capacity_authority.py",
        )
        shutil.copy(
            repo_root / "scripts" / "agent_registry_deploy_verify.py",
            self.source_dir / "scripts" / "agent_registry_deploy_verify.py",
        )
        shutil.copy(
            repo_root / "scripts" / "capacity_snapshot_helper.py",
            self.source_dir / "scripts" / "capacity_snapshot_helper.py",
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

            [capacity_registry]
            id = "multinexus.discord.capacity"
            version = 1

            [[executor_capacities]]
            agent_id = "mac-claude"
            max_concurrent_jobs = 1
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
        (fake_pkg / "executor_capacity.py").write_text(_FAKE_EXECUTOR_CAPACITY, encoding="utf-8")

        # Pre-create the DB directory so the snapshot helper can connect even
        # before the first sync populates it (prior-absence capture path).
        (self.fake_root / "var" / "lib" / "coordinate").mkdir(parents=True, exist_ok=True)

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
            "FAKE_COORD_NOW": "2026-01-01T00:00:00Z",
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
                s = s.replace("/tmp/", os.path.join(root, "tmp/"))
                # Drop sudo wrappers; the test runner has local filesystem rights.
                s = s.replace("sudo -u coord env ", "env ")
                s = s.replace("sudo -u multinexus ", "")
                s = s.replace("sudo ", "")
                return s

            rewritten = rewrite(cmd)

            cleanup_marker = os.path.join(root, ".cleanup_failure_done")
            if (
                os.environ.get("FAKE_CLEANUP_FAILURE_ONCE") == "1"
                and "sudo rm -f '/tmp/capacity-snapshot-" in cmd
                and not os.path.exists(cleanup_marker)
            ):
                open(cleanup_marker, "w", encoding="utf-8").close()
                sys.exit(1)

            if cmd.startswith("sudo bash -s"):
                script_text = sys.stdin.read()
                rewritten_script = rewrite(script_text)
                if os.environ.get("FAKE_SOURCE_MUTATION_FAILURE") == "1":
                    # Inject failure after rsync+chown but before agents.toml test.
                    rewritten_script = rewritten_script.replace(
                        "test -f",
                        "false  # injected source mutation failure\\n#test -f",
                        1,
                    )
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

    def _run_deploy_with_env(self, **env_updates) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.update(self._env)
        env.update(env_updates)
        return subprocess.run(
            [
                "bash",
                str(self.deploy_script),
                "multinexus",
                "--multinexus-src",
                str(self.source_dir),
                "--host",
                "fake-host",
                "--skip-install",
                "--no-smoke",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

    def _ssh_log(self) -> str:
        if not self.ssh_log.exists():
            return ""
        return self.ssh_log.read_text(encoding="utf-8")

    def _snapshot_full_db_state(self, db_path) -> dict:
        """Capture exact tuples (all columns, stable ordering) of every
        rollback-affected projection so post-rollback comparison can verify
        byte-level fidelity to the captured accepted pre-state.
        """
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            workspace_rows = conn.execute(
                "SELECT * FROM workspaces WHERE id = 'discord-nexus' ORDER BY id"
            ).fetchall()
            roster_source_rows = conn.execute(
                "SELECT * FROM workspace_agent_registry_sources "
                "WHERE workspace_id = 'discord-nexus' ORDER BY workspace_id"
            ).fetchall()
            roster_rows = conn.execute(
                "SELECT * FROM workspace_agent_registry_entries "
                "WHERE entry_kind = 'authoritative' ORDER BY workspace_id, agent_name"
            ).fetchall()
            agent_rows = conn.execute(
                "SELECT * FROM agents WHERE id IN ('mac-claude', 'server-hermes') ORDER BY id"
            ).fetchall()
            runner_rows = conn.execute(
                "SELECT * FROM runner_profiles WHERE id IN ('mac-claude', 'server-hermes') ORDER BY id"
            ).fetchall()
            executor_source_rows = conn.execute(
                "SELECT * FROM executor_catalog_sources "
                "WHERE source_id = 'multinexus.discord' ORDER BY source_id"
            ).fetchall()
            def_rows = conn.execute(
                "SELECT * FROM executor_definitions ORDER BY source_id, id"
            ).fetchall()
            binding_rows = conn.execute(
                "SELECT * FROM executor_instance_bindings ORDER BY source_id, agent_id"
            ).fetchall()
            cap_source_rows = conn.execute(
                "SELECT * FROM executor_capacity_sources ORDER BY source_id"
            ).fetchall()
            cap_policy_rows = conn.execute(
                "SELECT * FROM executor_capacity_policies ORDER BY source_id, agent_id"
            ).fetchall()
            return {
                "workspaces": [tuple(r) for r in workspace_rows],
                "roster_sources": [tuple(r) for r in roster_source_rows],
                "roster": [tuple(r) for r in roster_rows],
                "agents": [tuple(r) for r in agent_rows],
                "runner_profiles": [tuple(r) for r in runner_rows],
                "executor_sources": [tuple(r) for r in executor_source_rows],
                "definitions": [tuple(r) for r in def_rows],
                "bindings": [tuple(r) for r in binding_rows],
                "cap_sources": [tuple(r) for r in cap_source_rows],
                "cap_policies": [tuple(r) for r in cap_policy_rows],
            }
        finally:
            conn.close()

    def _assert_db_state_matches(self, db_path, expected: dict) -> None:
        """Assert the current DB state exactly matches the expected snapshot tuples."""
        actual = self._snapshot_full_db_state(db_path)
        for key in expected:
            self.assertEqual(
                expected[key], actual[key],
                f"DB state mismatch for {key}: expected {expected[key]!r}, got {actual[key]!r}"
            )

    def _seed_previous_accepted_state(self, remote_config, *, include_capacity=True) -> None:
        """Materialize the full accepted roster/executor/capacity projection."""
        shutil.copytree(
            self.source_dir / "multinexus",
            self.remote_opt / "multinexus",
            dirs_exist_ok=True,
        )
        commands = [
            ["workspace", "agent", "sync", "discord-nexus", "--source", str(remote_config), "--replace"],
            ["runtime", "executor", "sync", "--source", str(remote_config)],
        ]
        if include_capacity:
            commands.append(["runtime", "capacity", "sync", "--source", str(remote_config)])
        env = dict(os.environ)
        env.update(self._env)
        for command in commands:
            result = subprocess.run(
                [str(self.bin_dir / "coord-local"), *command],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def _deploy_residue(self) -> list[str]:
        tmp_root = self.fake_root / "tmp"
        if not tmp_root.exists():
            return []
        prefixes = (
            "deploy-multinexus-",
            "capacity-snapshot-",
            "agent-registry.toml.capacity-backup-",
        )
        return sorted(
            str(path.relative_to(self.fake_root))
            for path in tmp_root.iterdir()
            if path.name.startswith(prefixes)
        )

    def _assert_no_deploy_residue(self) -> None:
        self.assertEqual(self._deploy_residue(), [])

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
        self._assert_no_deploy_residue()

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



    def test_capacity_sync_failure_no_version_restart_and_previous_restored(self):
        # Pre-create the remote config and DB with a v1 capacity projection so
        # the backup has something to restore to.
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        v1_authority_bytes = self.authority.read_text(encoding="utf-8")
        remote_config.write_text(v1_authority_bytes, encoding="utf-8")

        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._seed_previous_accepted_state(remote_config)

        # Capture the COMPLETE accepted pre-state (every column, every row)
        # before any mutation, so post-rollback comparison can prove exact
        # fidelity of the restore.
        pre_state = self._snapshot_full_db_state(db_path)

        # Modify local authority to a v2 capacity projection.
        v2_authority_bytes = v1_authority_bytes.replace(
            'version = 1', 'version = 2'
        ).replace('max_concurrent_jobs = 1', 'max_concurrent_jobs = 2')
        self.authority.write_text(v2_authority_bytes, encoding="utf-8")

        # Inject capacity sync failure on the remote side.
        env = dict(os.environ)
        env.update(self._env)
        env["FAKE_CAPACITY_SYNC_FAILURE"] = "1"
        result = subprocess.run(
            [
                "bash",
                str(self.deploy_script),
                "multinexus",
                "--multinexus-src",
                str(self.source_dir),
                "--host",
                "fake-host",
                "--skip-install",
                "--no-smoke",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("capacity-sync", result.stderr)
        log = self._ssh_log()
        self.assertNotIn("VERSION_DEPLOYED", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)

        # R3-6: post-rollback DB must be byte-identical to the captured pre-state.
        self._assert_db_state_matches(db_path, pre_state)

        # Authority bytes: restored remote config must be byte-identical to v1.
        self.assertEqual(
            remote_config.read_text(encoding="utf-8"),
            v1_authority_bytes,
            "remote authority must be byte-identical to v1 after rollback",
        )
        self._assert_no_deploy_residue()


    def test_capacity_policy_id_mismatch_restores_previous_and_no_version_restart(self):
        # Pre-create the remote config and DB with a v1 capacity projection so
        # the backup has something to restore to.
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        v1_authority_bytes = self.authority.read_text(encoding="utf-8")
        remote_config.write_text(v1_authority_bytes, encoding="utf-8")

        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._seed_previous_accepted_state(remote_config)

        # Capture the COMPLETE accepted pre-state before any mutation.
        pre_state = self._snapshot_full_db_state(db_path)

        # Modify local authority to a v2 capacity projection.
        v2_authority_bytes = v1_authority_bytes.replace(
            'version = 1', 'version = 2'
        ).replace('max_concurrent_jobs = 1', 'max_concurrent_jobs = 2')
        self.authority.write_text(v2_authority_bytes, encoding="utf-8")

        # Inject a one-time capacity policy id tamper so the committed verifier fails.
        env = dict(os.environ)
        env.update(self._env)
        env["FAKE_CAPACITY_VERIFY_FAILURE"] = "1"
        result = subprocess.run(
            [
                "bash",
                str(self.deploy_script),
                "multinexus",
                "--multinexus-src",
                str(self.source_dir),
                "--host",
                "fake-host",
                "--skip-install",
                "--no-smoke",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("committed-state", result.stderr)
        log = self._ssh_log()
        self.assertNotIn("VERSION_DEPLOYED", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)

        # R3-6: post-rollback DB must be byte-identical to the captured pre-state.
        self._assert_db_state_matches(db_path, pre_state)

        # Authority bytes: restored remote config must be byte-identical to v1.
        self.assertEqual(
            remote_config.read_text(encoding="utf-8"),
            v1_authority_bytes,
            "remote authority must be byte-identical to v1 after rollback",
        )
        self._assert_no_deploy_residue()

    def test_prior_absence_first_rollout_verifier_failure_restores_no_capacity(self):
        # First rollout: remote has an OLD authority without capacity roots and
        # no capacity projection in the DB. The new authority adds capacity.
        # If the committed verifier fails after capacity sync, the restore must
        # delete the newly created capacity projection (prior-absence restore).
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        old_authority_bytes = textwrap.dedent("""\
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
            """)
        remote_config.write_text(old_authority_bytes, encoding="utf-8")

        # Pre-create the agents.toml so the deploy heredoc `test -f` passes.
        # The deploy also writes the agents.toml into remote_opt before the
        # rsync runs (setUp), but the local parity check at the start of the
        # deploy validates the v1 authority against the same v1 runtime, so
        # we are good here.

        # No capacity projection pre-exists in the DB (prior absence).
        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._seed_previous_accepted_state(remote_config, include_capacity=False)

        # Capture the COMPLETE prior-absence pre-state. For prior absence the
        # capacity tables must be empty; roster/executor capture whatever
        # exists before the deploy runs.
        pre_state = self._snapshot_full_db_state(db_path)
        self.assertEqual(pre_state["cap_sources"], [],
                          "prior-absence pre-state must have no capacity sources")
        self.assertEqual(pre_state["cap_policies"], [],
                          "prior-absence pre-state must have no capacity policies")

        # Inject a one-time capacity policy id tamper so the committed verifier
        # fails after the new capacity sync succeeds.
        env = dict(os.environ)
        env.update(self._env)
        env["FAKE_CAPACITY_VERIFY_FAILURE"] = "1"
        result = subprocess.run(
            [
                "bash",
                str(self.deploy_script),
                "multinexus",
                "--multinexus-src",
                str(self.source_dir),
                "--host",
                "fake-host",
                "--skip-install",
                "--no-smoke",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("committed-state", result.stderr)
        log = self._ssh_log()
        self.assertNotIn("VERSION_DEPLOYED", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)

        # R3-6: post-rollback DB must be byte-identical to prior-absence pre-state.
        self._assert_db_state_matches(db_path, pre_state)

        # Authority bytes: restored remote config must be byte-identical to the old authority.
        self.assertEqual(
            remote_config.read_text(encoding="utf-8"),
            old_authority_bytes,
            "remote authority must be byte-identical to old authority after rollback",
        )
        self._assert_no_deploy_residue()


    def test_source_mutation_failure_restores_all_three_projections(self):
        # Source rsync fails after partially overwriting /opt/multinexus.
        # The deploy must restore old authority + roster + executor + capacity.
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        v1_authority_bytes = self.authority.read_text(encoding="utf-8")
        remote_config.write_text(v1_authority_bytes, encoding="utf-8")

        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._seed_previous_accepted_state(remote_config)

        # Capture the COMPLETE accepted pre-state before any mutation.
        pre_state = self._snapshot_full_db_state(db_path)

        v2_authority_bytes = v1_authority_bytes.replace(
            'version = 1', 'version = 2'
        ).replace('max_concurrent_jobs = 1', 'max_concurrent_jobs = 2')
        self.authority.write_text(v2_authority_bytes, encoding="utf-8")

        env = dict(os.environ)
        env.update(self._env)
        env["FAKE_SOURCE_MUTATION_FAILURE"] = "1"
        result = subprocess.run(
            [
                "bash",
                str(self.deploy_script),
                "multinexus",
                "--multinexus-src",
                str(self.source_dir),
                "--host",
                "fake-host",
                "--skip-install",
                "--no-smoke",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("source-mutation", result.stderr)
        log = self._ssh_log()
        self.assertNotIn("VERSION_DEPLOYED", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)

        # R3-6: post-rollback DB must be byte-identical to the captured pre-state.
        self._assert_db_state_matches(db_path, pre_state)

        # Authority bytes: restored remote config must be byte-identical to v1.
        self.assertEqual(
            remote_config.read_text(encoding="utf-8"),
            v1_authority_bytes,
            "remote authority must be byte-identical to v1 after rollback",
        )
        self._assert_no_deploy_residue()

    def test_restore_hard_failure_is_loud_nonzero_no_version_restart(self):
        # The committed verifier fails, and the capacity snapshot restore
        # itself fails. The deploy must exit nonzero with no version/restart/smoke
        # and must not claim state was restored.
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        v1_authority_bytes = self.authority.read_text(encoding="utf-8")
        remote_config.write_text(v1_authority_bytes, encoding="utf-8")

        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._seed_previous_accepted_state(remote_config)

        # Capture the COMPLETE accepted pre-state before any mutation.
        pre_state = self._snapshot_full_db_state(db_path)

        v2_authority_bytes = v1_authority_bytes.replace(
            'version = 1', 'version = 2'
        ).replace('max_concurrent_jobs = 1', 'max_concurrent_jobs = 2')
        self.authority.write_text(v2_authority_bytes, encoding="utf-8")

        result = self._run_deploy_with_env(
            FAKE_CAPACITY_VERIFY_FAILURE="1",
            FAKE_RESTORE_FAILURE="1",
        )

        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("restore-capacity-snapshot", result.stderr)
        log = self._ssh_log()
        self.assertNotIn("VERSION_DEPLOYED", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)

        # R3-6 partial: only the components actually restored (roster,
        # executor, authority) must match the pre-state. Capacity restore
        # hard-failed; assert that capacity is NOT the pre-state, proving we
        # did not falsely claim it was restored.
        actual_state = self._snapshot_full_db_state(db_path)
        restored_components = (
            "workspaces",
            "roster_sources",
            "roster",
            "agents",
            "runner_profiles",
            "executor_sources",
            "definitions",
            "bindings",
        )
        for component in restored_components:
            self.assertEqual(
                actual_state[component],
                pre_state[component],
                f"{component} must match pre-state after partial restore",
            )

        # Capacity must NOT match pre-state — restore hard-failed before
        # any DELETE, so the v2 capacity synced during the deploy remains.
        # Proving non-equality is enough to prove we did not falsely report
        # capacity restored.
        self.assertNotEqual(
            actual_state["cap_sources"], pre_state["cap_sources"],
            "capacity sources must NOT match pre-state (restore hard-failed)",
        )
        self.assertNotEqual(
            actual_state["cap_policies"], pre_state["cap_policies"],
            "capacity policies must NOT match pre-state (restore hard-failed)",
        )
        # Specifically the v2 max_concurrent_jobs (2) and source_version (2)
        # prove the synced v2 capacity is what remains.
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT source_version, max_concurrent_jobs FROM executor_capacity_policies "
            "WHERE agent_id = ?",
            ("mac-claude",),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["source_version"], 2)
        self.assertEqual(row["max_concurrent_jobs"], 2)
        conn.close()

        # Authority bytes: the source was restored (cp backup → v1) before
        # the capacity restore failed.
        self.assertEqual(
            remote_config.read_text(encoding="utf-8"),
            v1_authority_bytes,
            "remote authority must be byte-identical to v1 after partial restore",
        )
        self._assert_no_deploy_residue()

    def test_snapshot_capture_failure_after_write_cleans_all_residue(self):
        result = self._run_deploy_with_env(
            FAKE_SNAPSHOT_CAPTURE_FAILURE_AFTER_WRITE="1"
        )

        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("snapshot-capture", result.stderr)
        log = self._ssh_log()
        self.assertNotIn("VERSION_DEPLOYED", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)
        self._assert_no_deploy_residue()

    def test_source_mutation_restore_double_failure_is_loud_and_cleans_residue(self):
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        remote_config.write_bytes(self.authority.read_bytes())
        self._seed_previous_accepted_state(remote_config)

        result = self._run_deploy_with_env(
            FAKE_SOURCE_MUTATION_FAILURE="1",
            FAKE_RESTORE_FAILURE="1",
        )

        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("source-mutation", result.stderr)
        self.assertIn("recovery-failure", result.stderr)
        log = self._ssh_log()
        self.assertNotIn("VERSION_DEPLOYED", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)
        self._assert_no_deploy_residue()

    def test_checked_success_cleanup_failure_blocks_acceptance_and_trap_retries(self):
        result = self._run_deploy_with_env(FAKE_CLEANUP_FAILURE_ONCE="1")

        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("cleanup-artifacts", result.stderr)
        log = self._ssh_log()
        self.assertNotIn("VERSION_DEPLOYED", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)
        self._assert_no_deploy_residue()

    def test_same_sha_invocations_use_isolated_artifact_paths(self):
        first = self._run_deploy()
        second = self._run_deploy()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)

        log = self._ssh_log()
        run_ids = set(
            re.findall(r"/tmp/capacity-snapshot-([^' ]+)\.json", log)
        )
        self.assertEqual(len(run_ids), 2, log)
        for run_id in run_ids:
            self.assertIn(f"/tmp/deploy-multinexus-{run_id}", log)
            self.assertIn(
                f"/tmp/agent-registry.toml.capacity-backup-{run_id}",
                log,
            )
        self._assert_no_deploy_residue()


if __name__ == "__main__":
    unittest.main()
