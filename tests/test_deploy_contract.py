"""Contract tests for the registry-aware deploy-server.sh flow.

These tests execute the real deploy script with fake ssh/git/tar/chown binaries
and safe fixtures, verifying failure ordering and success sequencing without
any production access.
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
from pathlib import Path


# Reuse the same coordinate venv the worker tests run under.
COORDINATE_VENV = Path("/Users/yinxin/projects/coordinate/.venv")


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

        # Runtime config used for local and remote parity.  Tests mutate this.
        self.runtime = self.source_dir / "agents.toml"
        self.runtime.write_text(
            textwrap.dedent("""\
            [[agents]]
            id = "mac-claude"
            display_name = "Mac Claude"
discord_user_id = "1507329791982833775"
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

        # Fake coordinate venv used by the verify helper.
        coord_venv = self.fake_root / "opt" / "coordinate" / ".venv"
        coord_venv.mkdir(parents=True)
        (coord_venv / "bin").mkdir()
        python_wrapper = coord_venv / "bin" / "python"
        python_wrapper.write_text(
            f"#!/bin/sh\nexec {COORDINATE_VENV / 'bin' / 'python'} \"$@\"\n",
            encoding="utf-8",
        )
        _make_executable(python_wrapper)

        self.deploy_script = repo_root / "scripts" / "deploy-server.sh"
        self._env = {
            "PATH": f"{self.bin_dir}:{os.environ.get('PATH', '')}",
            "DEPLOY_HOST": "fake-host",
            "FAKE_SSH_LOG": str(self.ssh_log),
            "FAKE_SSH_ROOT": str(self.fake_root),
            "FAKE_COORDINATE_VENV": str(COORDINATE_VENV),
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
            coord_venv = os.environ.get("FAKE_COORDINATE_VENV", "")
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
            textwrap.dedent(f"""\
            #!{COORDINATE_VENV / "bin" / "python"}
            import os, sys, tomllib
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "multinexus"))
            from coordinate.agent_registry import parse_agents_toml
            from coordinate.db import connect, initialize, upsert_workspace, sync_workspace_agents
            from coordinate.schema import migrate

            root = os.environ.get("FAKE_SSH_ROOT", "")
            db_path = Path(root) / "var/lib/coordinate/coord.sqlite3" if root else Path("coord.sqlite3")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = connect(str(db_path))
            migrate(conn)

            # Parse args: workspace agent sync <ws> --source <path> --replace
            args = sys.argv[1:]
            if "sync" not in args:
                print("fake coord-local: only sync supported", file=sys.stderr)
                sys.exit(1)
            workspace_id = args[args.index("sync") + 1]
            source_path = Path(args[args.index("--source") + 1])

            parsed = parse_agents_toml(source_path)
            if parsed.errors:
                for e in parsed.errors:
                    print(e, file=sys.stderr)
                sys.exit(1)

            upsert_workspace(conn, workspace_id=workspace_id, name=workspace_id, path="/x", harness_root="docs")
            entries = [
                {{"id": a.id, "display_name": a.display_name,
                  "discord_user_id": a.discord_user_id, "agent_type": a.agent_type}}
                for a in parsed.agents
            ]
            sync_workspace_agents(
                conn,
                workspace_id=workspace_id,
                source_id=parsed.source.source_id,
                source_version=parsed.source.source_version,
                source_hash=parsed.source.source_hash,
                source_path=str(source_path),
                entries=entries,
                replace=True,
                synced_by="deploy",
            )
            conn.close()
            """),
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
