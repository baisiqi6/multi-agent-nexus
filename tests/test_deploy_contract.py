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
now = datetime.now(timezone.utc).isoformat()

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

    def _ssh_log(self) -> str:
        if not self.ssh_log.exists():
            return ""
        return self.ssh_log.read_text(encoding="utf-8")

    def _snapshot_full_db_state(self, db_path) -> dict:
        """Capture exact tuples of roster, executor, and capacity rows for exact restore verification."""
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            roster_rows = conn.execute(
                "SELECT workspace_id, agent_name, entry_kind, discord_user_id, display_name, agent_type "
                "FROM workspace_agent_registry_entries WHERE entry_kind = 'authoritative' ORDER BY agent_name"
            ).fetchall()
            def_rows = conn.execute(
                "SELECT id, source_id, provider, adapter, capabilities_json "
                "FROM executor_definitions ORDER BY id"
            ).fetchall()
            binding_rows = conn.execute(
                "SELECT agent_id, source_id, executor_definition_id, runner_profile_id, enabled "
                "FROM executor_instance_bindings ORDER BY agent_id"
            ).fetchall()
            cap_source_rows = conn.execute(
                "SELECT source_id, source_version, catalog_hash FROM executor_capacity_sources"
            ).fetchall()
            cap_policy_rows = conn.execute(
                "SELECT agent_id, source_id, source_version, catalog_hash, capacity_policy_id, max_concurrent_jobs "
                "FROM executor_capacity_policies ORDER BY agent_id"
            ).fetchall()
            return {
                "roster": [tuple(r) for r in roster_rows],
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

    def _seed_previous_capacity(self, db_path, remote_config) -> tuple:
        """Seed DB with canonical v1 capacity source + policy. Returns (catalog_hash, policy_id)."""
        import hashlib, json, sqlite3
        catalog_hash = hashlib.sha256(b"multinexus.discord.capacity:v1:mac-claude:1").hexdigest()
        policy_id = "sha256:" + hashlib.sha256(json.dumps({
            "agent_id": "mac-claude",
            "catalog_hash": catalog_hash,
            "contract_version": 1,
            "max_concurrent_jobs": 1,
            "source_id": "multinexus.discord.capacity",
            "source_version": 1,
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
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
              max_concurrent_jobs INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO executor_capacity_sources (source_id, source_version, catalog_hash, source_path, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("multinexus.discord.capacity", 1, catalog_hash, str(remote_config), "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO executor_capacity_policies (agent_id, source_id, source_version, catalog_hash, capacity_policy_id, max_concurrent_jobs, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("mac-claude", "multinexus.discord.capacity", 1, catalog_hash, policy_id, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.close()
        return catalog_hash, policy_id

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



    def test_capacity_sync_failure_no_version_restart_and_previous_restored(self):
        # Pre-create the remote config and DB with a v1 capacity projection so
        # the backup has something to restore to.
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        v1_authority = self.authority.read_text(encoding="utf-8")
        remote_config.write_text(v1_authority, encoding="utf-8")

        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _catalog_hash, _policy_id = self._seed_previous_capacity(db_path, remote_config)

        # Modify local authority to a v2 capacity projection.
        v2 = v1_authority.replace('version = 1', 'version = 2').replace('max_concurrent_jobs = 1', 'max_concurrent_jobs = 2')
        self.authority.write_text(v2, encoding="utf-8")

        # Inject capacity sync failure on the remote side.
        env = dict(self._env)
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

        # R3-3: exact tuple comparison for all three projections.
        state = self._snapshot_full_db_state(db_path)
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT source_version, max_concurrent_jobs FROM executor_capacity_policies WHERE agent_id = ?",
            ("mac-claude",),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["source_version"], 1)
        self.assertEqual(row["max_concurrent_jobs"], 1)
        conn.close()
        # Exact comparison of roster + executor after re-sync.
        self.assertEqual(
            sorted(state["roster"]),
            sorted([
                ("discord-nexus", "mac-claude", "authoritative", "1507329791982833775", "Mac Claude", "managed"),
                ("discord-nexus", "server-hermes", "authoritative", "1505562531706568928", "Hermes", "external"),
            ]),
        )
        self.assertEqual(
            sorted(state["definitions"]),
            [("claude-code", "multinexus.discord", "anthropic-claude", "claude", '["coding", "review"]')],
        )
        self.assertEqual(
            sorted(state["bindings"]),
            [("mac-claude", "multinexus.discord", "claude-code", "mac-claude", 1)],
        )
        # Authority bytes: backup must match restored remote config.
        backup_path = self.fake_root / "tmp" / "agent-registry.toml.capacity-backup"
        if backup_path.exists():
            self.assertEqual(
                backup_path.read_text(encoding="utf-8"),
                remote_config.read_text(encoding="utf-8"),
                "authority bytes must be exactly restored",
            )


    def test_capacity_policy_id_mismatch_restores_previous_and_no_version_restart(self):
        # Pre-create the remote config and DB with a v1 capacity projection so
        # the backup has something to restore to.
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        v1_authority = self.authority.read_text(encoding="utf-8")
        remote_config.write_text(v1_authority, encoding="utf-8")

        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _catalog_hash, _policy_id = self._seed_previous_capacity(db_path, remote_config)

        # Modify local authority to a v2 capacity projection.
        v2 = v1_authority.replace('version = 1', 'version = 2').replace('max_concurrent_jobs = 1', 'max_concurrent_jobs = 2')
        self.authority.write_text(v2, encoding="utf-8")

        # Inject a one-time capacity policy id tamper so the committed verifier fails.
        env = dict(self._env)
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

        # R3-3: exact tuple comparison for all three projections.
        state = self._snapshot_full_db_state(db_path)
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT source_version, max_concurrent_jobs FROM executor_capacity_policies WHERE agent_id = ?",
            ("mac-claude",),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["source_version"], 1)
        self.assertEqual(row["max_concurrent_jobs"], 1)
        conn.close()
        self.assertEqual(
            sorted(state["roster"]),
            sorted([
                ("discord-nexus", "mac-claude", "authoritative", "1507329791982833775", "Mac Claude", "managed"),
                ("discord-nexus", "server-hermes", "authoritative", "1505562531706568928", "Hermes", "external"),
            ]),
        )
        self.assertEqual(
            sorted(state["definitions"]),
            [("claude-code", "multinexus.discord", "anthropic-claude", "claude", '["coding", "review"]')],
        )
        self.assertEqual(
            sorted(state["bindings"]),
            [("mac-claude", "multinexus.discord", "claude-code", "mac-claude", 1)],
        )
        backup_path = self.fake_root / "tmp" / "agent-registry.toml.capacity-backup"
        if backup_path.exists():
            self.assertEqual(
                backup_path.read_text(encoding="utf-8"),
                remote_config.read_text(encoding="utf-8"),
                "authority bytes must be exactly restored",
            )


    def test_prior_absence_first_rollout_verifier_failure_restores_no_capacity(self):
        # First rollout: remote has an OLD authority without capacity roots and
        # no capacity projection in the DB. The new authority adds capacity.
        # If the committed verifier fails after capacity sync, the restore must
        # delete the newly created capacity projection (prior-absence restore).
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        old_authority = textwrap.dedent("""\
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
        remote_config.write_text(old_authority, encoding="utf-8")

        # No capacity projection pre-exists in the DB (prior absence).
        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        import sqlite3

        # Inject a one-time capacity policy id tamper so the committed verifier
        # fails after the new capacity sync succeeds.
        env = dict(self._env)
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

        # R3-3: capacity must be EXACTLY absent (prior absence), roster+executor restored.
        state = self._snapshot_full_db_state(db_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        source = conn.execute(
            "SELECT COUNT(*) AS n FROM executor_capacity_sources"
        ).fetchone()
        self.assertEqual(source["n"], 0, "capacity source must be exactly absent")
        policy = conn.execute(
            "SELECT COUNT(*) AS n FROM executor_capacity_policies"
        ).fetchone()
        self.assertEqual(policy["n"], 0, "capacity policies must be exactly absent")
        conn.close()
        self.assertEqual(
            sorted(state["roster"]),
            sorted([
                ("discord-nexus", "mac-claude", "authoritative", "1507329791982833775", "Mac Claude", "managed"),
                ("discord-nexus", "server-hermes", "authoritative", "1505562531706568928", "Hermes", "external"),
            ]),
        )
        self.assertEqual(
            sorted(state["definitions"]),
            [("claude-code", "multinexus.discord", "anthropic-claude", "claude", '["coding", "review"]')],
        )
        self.assertEqual(
            sorted(state["bindings"]),
            [("mac-claude", "multinexus.discord", "claude-code", "mac-claude", 1)],
        )


    def test_source_mutation_failure_restores_all_three_projections(self):
        # Source rsync fails after partially overwriting /opt/multinexus.
        # The deploy must restore old authority + roster + executor + capacity.
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        v1_authority = self.authority.read_text(encoding="utf-8")
        remote_config.write_text(v1_authority, encoding="utf-8")

        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._seed_previous_capacity(db_path, remote_config)

        v2 = v1_authority.replace('version = 1', 'version = 2').replace('max_concurrent_jobs = 1', 'max_concurrent_jobs = 2')
        self.authority.write_text(v2, encoding="utf-8")

        env = dict(self._env)
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

        # R3-3: exact comparison for all three projections.
        state = self._snapshot_full_db_state(db_path)
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT source_version, max_concurrent_jobs FROM executor_capacity_policies WHERE agent_id = ?",
            ("mac-claude",),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["source_version"], 1)
        self.assertEqual(row["max_concurrent_jobs"], 1)
        conn.close()
        self.assertEqual(
            sorted(state["roster"]),
            sorted([
                ("discord-nexus", "mac-claude", "authoritative", "1507329791982833775", "Mac Claude", "managed"),
                ("discord-nexus", "server-hermes", "authoritative", "1505562531706568928", "Hermes", "external"),
            ]),
        )
        self.assertEqual(
            sorted(state["definitions"]),
            [("claude-code", "multinexus.discord", "anthropic-claude", "claude", '["coding", "review"]')],
        )
        self.assertEqual(
            sorted(state["bindings"]),
            [("mac-claude", "multinexus.discord", "claude-code", "mac-claude", 1)],
        )
        backup_path = self.fake_root / "tmp" / "agent-registry.toml.capacity-backup"
        if backup_path.exists():
            self.assertEqual(
                backup_path.read_text(encoding="utf-8"),
                remote_config.read_text(encoding="utf-8"),
                "authority bytes must be exactly restored",
            )

    def test_restore_hard_failure_is_loud_nonzero_no_version_restart(self):
        # The committed verifier fails, and the capacity snapshot restore
        # itself fails. The deploy must exit nonzero with no version/restart/smoke
        # and must not claim state was restored.
        remote_config = self.remote_opt / "config" / "agent-registry.toml"
        remote_config.parent.mkdir(parents=True, exist_ok=True)
        v1_authority = self.authority.read_text(encoding="utf-8")
        remote_config.write_text(v1_authority, encoding="utf-8")

        db_path = self.fake_root / "var" / "lib" / "coordinate" / "coord.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._seed_previous_capacity(db_path, remote_config)

        v2 = v1_authority.replace('version = 1', 'version = 2').replace('max_concurrent_jobs = 1', 'max_concurrent_jobs = 2')
        self.authority.write_text(v2, encoding="utf-8")

        env = dict(self._env)
        env["FAKE_CAPACITY_VERIFY_FAILURE"] = "1"
        env["FAKE_RESTORE_FAILURE"] = "1"
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
        self.assertIn("restore-capacity-snapshot", result.stderr)
        log = self._ssh_log()
        self.assertNotIn("VERSION_DEPLOYED", log)
        self.assertNotIn("systemctl restart multinexus-discord-bridge", log)

        # R3-3: roster + executor ARE restored (re-synced before capacity restore step).
        # Capacity is NOT restored (restore failure is loud/nonzero).
        state = self._snapshot_full_db_state(db_path)
        self.assertEqual(
            sorted(state["roster"]),
            sorted([
                ("discord-nexus", "mac-claude", "authoritative", "1507329791982833775", "Mac Claude", "managed"),
                ("discord-nexus", "server-hermes", "authoritative", "1505562531706568928", "Hermes", "external"),
            ]),
        )
        self.assertEqual(
            sorted(state["definitions"]),
            [("claude-code", "multinexus.discord", "anthropic-claude", "claude", '["coding", "review"]')],
        )
        self.assertEqual(
            sorted(state["bindings"]),
            [("mac-claude", "multinexus.discord", "claude-code", "mac-claude", 1)],
        )


if __name__ == "__main__":
    unittest.main()
