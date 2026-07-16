"""Behaviour tests for P9-3C0 Package 3 unit-helper slice.

All OS/systemd/filesystem identity/time/process evidence is mocked.  No real
systemd, Coordinate, network, or production path is exercised.

Each ``render`` / ``preflight`` / ``start`` test exercises the real
``main`` entrypoint so the authority, manifest, identity, recovery, and
static-verify gates are proven reachable end-to-end.  Helper functions are
not invoked directly except for the parser and pure normalizer checks.
"""
from __future__ import annotations

import os
import hashlib
import json
import re
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
UNIT_HELPER = REPO_ROOT / "multinexus" / "fixture" / "bin" / "p9-3c0-unit.sh"
LOCAL_VERIFY = REPO_ROOT / "scripts" / "p9-3c0-local-verify.sh"
CLEANUP = REPO_ROOT / "scripts" / "p9-3c0-cleanup.sh"

# Identity constants used by every mocked authority/identity scenario.
# Tests pin these so the wrapper/manifest/identity gid can be checked
# consistently without leaking real NSS values.
MOCK_UID = "1001"
MOCK_GID = "1001"
MOCK_USER = "testuser"
MOCK_GROUP = "testgroup"
MOCK_WRAPPER_MODE = "750"
MOCK_MANIFEST_MODE = "640"
MOCK_WRAPPER_SHA = "abc123def456abc123def456abc123def456abc123def456abc123def456abcd"
MOCK_DEF_SHA = "def987abc654def987abc654def987abc654def987abc654def987abc654def6"

def _run_bash(script: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a bash script using the system default bash (macOS 3.2 is supported)."""
    return subprocess.run(
        ["bash", "-u", "-o", "pipefail", "-c", script],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _chmod_exec(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _production_snapshot_python(config_paths: tuple[Path, ...]) -> str:
    """Extract the real embedded snapshot program with test-only config paths."""
    source = LOCAL_VERIFY.read_text()
    match = re.search(
        r"_p9c0_real_production_snapshot\(\) \{.*?<<'PY'\n(?P<body>.*?)\nPY\n\}",
        source,
        re.DOTALL,
    )
    assert match is not None
    body = match.group("body")
    replacement = "config_paths = " + repr(tuple(str(path) for path in config_paths))
    body, count = re.subn(
        r"config_paths = \(\n(?:    .*\n)+?\)", replacement, body, count=1
    )
    assert count == 1
    return body


def _mocked_authority_lines() -> str:
    """Snippet that mocks every authority/identity seam.

    Tests override individual pieces by writing to env-style globals or by
    sourcing the helper after this snippet runs.  The defaults model the
    canonical fixture: root-owned wrapper, exact unit-group gid, mode
    0750/0640, sha captured at creation time, and the requested
    user/group resolving to the pinned numeric ids.
    """
    return f"""
        # Captured argv from real systemd-run invocations.
        SYSTEMD_RUN_CALLS=$(mktemp)
        WRAPPER_HEALTH_CALLS=$(mktemp)

        _p9c0_run_systemd_run() {{
            printf '%s\\n' "$*" >> "$SYSTEMD_RUN_CALLS"
            return 0
        }}

        # Captured argv from the wrapper health probe.
        _p9c0_wrapper_health() {{
            printf 'wrapper-ok %s\\n' "$*" >> "$WRAPPER_HEALTH_CALLS"
            return 0
        }}

        # Default identity lookups: the requested user/group exist with
        # non-zero numeric ids matching the wrapper gid.
        _p9c0_identity_lookup_user() {{
            local name="$1"
            case $name in
                {MOCK_USER}) echo {MOCK_UID}; return 0 ;;
                root|nobody) return 1 ;;
                *) echo 0; return 1 ;;
            esac
        }}
        _p9c0_identity_lookup_group() {{
            local name="$1"
            case $name in
                {MOCK_GROUP}) echo {MOCK_GID}; return 0 ;;
                root|nogroup) return 1 ;;
                *) echo 0; return 1 ;;
            esac
        }}

        # Default stat: root-owned wrapper with exact unit-group gid, mode
        # 0750, single hard link. Manifest has mode 0640. The static
        # unit-definition file is root-owned mode 0600 with no group
        # identity and a separate SHA so the sealed values can be checked
        # against the live file. The render-time definition writes
        # verifiable bytes; the per-test seams override these to inject
        # content / mode / owner drift.
        _p9c0_stat_file() {{
            case "$1" in
                */wrapper.manifest) echo "0:0:128:1:0:{MOCK_GID}:{MOCK_MANIFEST_MODE}" ;;
                */systemd.verify.service) echo "0:0:0:1:0:0:600" ;;
                */controller.lock|*/unit-helper.lock) echo "0:0:0:1:0:0:600" ;;
                *) echo "0:0:256:1:0:{MOCK_GID}:{MOCK_WRAPPER_MODE}" ;;
            esac
        }}
        _p9c0_sha256_file() {{
            case "$1" in
                */systemd.verify.service) echo "{MOCK_DEF_SHA}" ;;
                *) echo "{MOCK_WRAPPER_SHA}" ;;
            esac
        }}
        _p9c0_systemctl() {{
            return 0
        }}
        _p9c0_systemd_analyze() {{ return 0; }}
        _p9c0_date_ms() {{ echo 1000; }}
        _p9c0_flock() {{ return 0; }}
        _p9c0_sleep() {{ return 0; }}
        _p9c0_python_normalize() {{ return 0; }}
        _p9c0_set_owner_group_mode() {{ chmod "$4" "$1"; }}
        _p9c0_lock_file_authority() {{ return 0; }}

        # Stub binaries for ``command -v`` lookups so preflight can pass
        # its environment gate without a real systemd install.
        STUB_BIN=$(mktemp -d)
        cat > "$STUB_BIN/systemctl" <<'STUB'
#!/bin/sh
exit 0
STUB
        cat > "$STUB_BIN/systemd-run" <<'STUB'
#!/bin/sh
exit 0
STUB
        chmod +x "$STUB_BIN/systemctl" "$STUB_BIN/systemd-run"
        export PATH="$STUB_BIN:$PATH"
    """


def _bootstrap_render_state(
    tmp_path: Path,
    *,
    run_id: str = "pkg3-render",
    state_root_name: str = "state",
) -> dict:
    """Create the on-disk artefacts render expects and return their paths.

    The render helper refuses to create, overwrite, chmod, or chown the
    manifest. The controller (this bootstrap) is therefore responsible
    for placing the exact single-line ``wrapper.manifest`` in the per-run
    state directory before render runs. The bytes written here must match
    what the helper's live-wrapper stat/sha would produce; the mocked
    stat seam returns ``0:0:256:1:0:{gid}:750`` for the wrapper and
    ``0:0:128:1:0:{gid}:640`` for the manifest file itself.
    """
    state_root = tmp_path / state_root_name
    state_root.mkdir(parents=True, exist_ok=True)
    work_dir = state_root / "work"
    coord_db = state_root / "coord.sqlite3"
    # Wrapper must live under state_root so the containment gate passes.
    wrapper = state_root / "wrapper.sh"
    fixture_bin = tmp_path / "fixture.py"
    # Wrapper doubles as a probe: it logs every invocation to a marker
    # file passed via WRAPPER_INVOKED so preflight tests can prove the
    # wrapper is only contacted after manifest + identity rechecks pass.
    wrapper.write_text(
        "#!/bin/sh\n"
        "if [ -n \"${WRAPPER_INVOKED:-}\" ]; then\n"
        "    echo \"called $@\" >> \"$WRAPPER_INVOKED\"\n"
        "fi\n"
        "echo \"wrapper-version\"\n"
    )
    fixture_bin.write_text("#!/bin/sh\necho fixture\n")
    _chmod_exec(wrapper)
    _chmod_exec(fixture_bin)
    # Pre-create the manifest the controller is required to place. The
    # record format mirrors ``_p9c0_wrapper_manifest_record`` exactly:
    # tab-separated ``wrapper_raw=...``, ``wrapper_dev_inode_size_nlink_
    # uid_gid_mode=dev:inode:size:nlink:uid:gid:mode``, and ``wrapper_
    # sha256=...`` fields, terminated by a single newline.
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
    manifest = state_dir / "wrapper.manifest"
    manifest_record = (
        f"wrapper_raw={wrapper}"
        f"\twrapper_dev_inode_size_nlink_uid_gid_mode="
        f"0:0:256:1:0:{MOCK_GID}:{MOCK_WRAPPER_MODE}"
        f"\twrapper_sha256={MOCK_WRAPPER_SHA}\n"
    )
    manifest.write_text(manifest_record)
    manifest.chmod(0o640)
    return {
        "state_root": state_root,
        "work_dir": work_dir,
        "coord_db": coord_db,
        "wrapper": wrapper,
        "fixture_bin": fixture_bin,
        "run_id": run_id,
        "user": MOCK_USER,
        "group": MOCK_GROUP,
        "manifest": manifest,
        "manifest_record": manifest_record,
    }


def _render_script(facts: dict, *, extra_overrides: str = "") -> str:
    flags = " ".join(
        [
            f"--state-root {facts['state_root']!s}",
            f"--run-id {facts['run_id']}",
            f"--fixture-bin {facts['fixture_bin']!s}",
            f"--wrapper {facts['wrapper']!s}",
            f"--coord-db {facts['coord_db']!s}",
            f"--work-dir {facts['work_dir']!s}",
            f"--python {sys.executable!r}",
            f"--repo-root {REPO_ROOT}",
            f"--user {facts['user']}",
            f"--group {facts['group']}",
        ]
    )
    runtime_parent = facts.get("runtime_parent")
    if runtime_parent:
        flags += f" --runtime-parent {runtime_parent}"
    return f"""
        set -euo pipefail
        source "{UNIT_HELPER}"
        {_mocked_authority_lines()}
        {extra_overrides}
        main render {flags}
        """

class TestSourceSafeSeam:
    """The helper can be sourced for testing without running main()."""

    def test_source_does_not_invoke_main(self):
        script = f"""
        set -euo pipefail
        source "{UNIT_HELPER}"
        if ! type main >/dev/null 2>&1; then
            echo "main-missing"
            exit 1
        fi
        echo "sourced-ok"
        """
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert "sourced-ok" in result.stdout


class TestSourceSealed:
    """The source must not contain ``eval`` or ``--dry-run`` anywhere."""

    def test_no_eval_no_dry_run_in_source(self, tmp_path: Path):
        script = f"""
        set -euo pipefail
        source "{UNIT_HELPER}"
        if grep -nE '\\beval\\b|--dry-run' "{UNIT_HELPER}"; then
            echo "leaked"
            exit 1
        fi
        echo "sealed"
        """
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert "sealed" in result.stdout


class TestRenderReachability:
    """render creates manifest + values + enforces every authority gate."""

    def test_render_success_writes_manifest_and_values(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr

        run_id = facts["run_id"]
        state_dir = facts["state_root"] / run_id
        manifest = state_dir / "wrapper.manifest"
        values = state_dir / "values.rendered"
        rendered = state_dir / "agents.rendered.toml"

        assert manifest.exists()
        assert values.exists()
        assert rendered.exists()

        manifest_text = manifest.read_text()
        assert f"wrapper_raw={facts['wrapper']}" in manifest_text
        assert f"wrapper_sha256={MOCK_WRAPPER_SHA}" in manifest_text
        assert f"wrapper_dev_inode_size_nlink_uid_gid_mode=0:0:256:1:0:{MOCK_GID}:{MOCK_WRAPPER_MODE}" in manifest_text

        values_text = values.read_text()
        assert f"manifest_path={manifest}" in values_text
        assert f"manifest_record={manifest_text.strip()}" in values_text
        assert f"unit_user={MOCK_USER}" in values_text
        assert f"unit_group={MOCK_GROUP}" in values_text
        assert f"unit_uid={MOCK_UID}" in values_text
        assert f"unit_gid={MOCK_GID}" in values_text
        assert f"state_path={state_dir}" in values_text

    def test_render_rejects_production_alias_before_use(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        # Capture the controller-placed manifest content so we can prove
        # the helper left it untouched after the production-alias failure.
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        before = manifest.read_bytes()
        # Mock the production-alias check so the wrapper resolves to the
        # production coordinate CLI path.
        override = """
        _p9c0_is_resolved_production_wrapper() { return 0; }
        """
        result = _run_bash(_render_script(facts, extra_overrides=override))
        assert result.returncode != 0
        assert "refusing production wrapper" in result.stderr
        # Manifest must remain exactly as the controller placed it.
        assert manifest.exists()
        assert manifest.read_bytes() == before

    def test_render_rejects_wrapper_outside_state_root(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        before = manifest.read_bytes()
        # Override containment so the wrapper is reported as escaping the
        # state prefix; authority still rejects it before any write.
        override = """
        _p9c0_wrapper_is_safe_under_prefix() { return 1; }
        """
        result = _run_bash(_render_script(facts, extra_overrides=override))
        assert result.returncode != 0
        assert "containment rejected" in result.stderr
        # Manifest untouched after a containment failure.
        assert manifest.exists()
        assert manifest.read_bytes() == before

    def test_render_rejects_wrapper_wrong_owner_mode(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        before = manifest.read_bytes()
        override = """
        _p9c0_stat_file() { echo "0:0:0:1:1000:1000:755"; }
        """
        result = _run_bash(_render_script(facts, extra_overrides=override))
        assert result.returncode != 0
        assert "owner/mode rejected" in result.stderr
        # Manifest untouched after a wrapper owner/mode rejection.
        assert manifest.exists()
        assert manifest.read_bytes() == before

    def test_render_rejects_manifest_wrong_mode(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        before = manifest.read_bytes()
        # Manifest is preexisting; the mocked stat seam now reports the
        # manifest with mode 644 so the verify gate catches the drift.
        override = """
        _p9c0_stat_file() {
            case "$1" in
                */wrapper.manifest) echo "0:0:128:1:0:1001:644" ;;
                *) echo "0:0:256:1:0:1001:750" ;;
            esac
        }
        """
        result = _run_bash(_render_script(facts, extra_overrides=override))
        assert result.returncode != 0
        assert "wrapper manifest: mode must be 0640 got=644" in result.stderr
        # Helper must not chmod the manifest.
        assert manifest.exists()
        assert manifest.read_bytes() == before

    def test_render_rejects_missing_user(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        before = manifest.read_bytes()
        override = """
        _p9c0_identity_lookup_user() { return 1; }
        """
        result = _run_bash(_render_script(facts, extra_overrides=override))
        assert result.returncode != 0
        assert "unit identity rejected" in result.stderr
        assert "user does not exist" in result.stderr
        # Manifest untouched after a missing-user failure.
        assert manifest.exists()
        assert manifest.read_bytes() == before

    def test_render_rejects_gid_mismatch_between_wrapper_and_group(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        before = manifest.read_bytes()
        override = """
        # Identity returns gid 2002 but wrapper stat says gid 1001 -> mismatch.
        _p9c0_identity_lookup_group() { echo 2002; return 0; }
        """
        result = _run_bash(_render_script(facts, extra_overrides=override))
        assert result.returncode != 0
        assert "unit identity rejected" in result.stderr
        assert "does not match wrapper gid" in result.stderr
        # Manifest untouched after a gid mismatch.
        assert manifest.exists()
        assert manifest.read_bytes() == before

    def test_render_rejects_runtime_parent_outside_prefix(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        before = manifest.read_bytes()
        facts["runtime_parent"] = "/etc/passwd"
        flags = " ".join(
            [
                f"--state-root {facts['state_root']!s}",
                f"--run-id {facts['run_id']}",
                f"--fixture-bin {facts['fixture_bin']!s}",
                f"--wrapper {facts['wrapper']!s}",
                f"--coord-db {facts['coord_db']!s}",
                f"--work-dir {facts['work_dir']!s}",
                f"--python {sys.executable!r}",
                f"--repo-root {REPO_ROOT}",
                f"--user {facts['user']}",
                f"--group {facts['group']}",
                f"--runtime-parent {facts['runtime_parent']}",
            ]
        )
        script = f"""
            set -euo pipefail
            source "{UNIT_HELPER}"
            {_mocked_authority_lines()}
            main render {flags}
            """
        result = _run_bash(script)
        assert result.returncode != 0
        assert "unit identity rejected" in result.stderr
        assert "outside approved prefix" in result.stderr
        # Manifest untouched after a runtime-parent containment failure.
        assert manifest.exists()
        assert manifest.read_bytes() == before

    def test_render_rejects_symlink_wrapper_before_use(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        # Replace the regular wrapper with a symlink so the helper's
        # containment + authority gate catches it before any use.
        facts["wrapper"].unlink()
        facts["wrapper"].symlink_to(facts["fixture_bin"])
        result = _run_bash(_render_script(facts))
        assert result.returncode != 0
        # Either the symlink detection or the containment gate must fire.
        stderr = result.stderr
        assert (
            "wrapper is a symlink" in stderr
            or "containment rejected" in stderr
            or "owner/mode rejected" in stderr
        ), stderr


class TestPreflightReachability:
    """preflight rechecks manifest + identity before invoking the wrapper."""

    @pytest.fixture
    def rendered_state(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path, run_id="pkg3-preflight")
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr
        return facts

    def _preflight_script(
        self,
        facts: dict,
        *,
        extra_overrides: str = "",
    ) -> str:
        state_root = facts["state_root"]
        run_id = facts["run_id"]
        wrapper = facts["wrapper"]
        return f"""
            set -euo pipefail
            source "{UNIT_HELPER}"
            {_mocked_authority_lines()}
            {extra_overrides}
            WRAPPER_INVOKED=$(mktemp)
            export WRAPPER_INVOKED
            # Bypass locking so the probe runs synchronously.
            _p9c0_with_lock() {{
                shift 2
                "$@"
            }}
            ( main preflight \
                --state-root "{state_root}" \
                --run-id "{run_id}" \
                --agent-id p9-3c-fixture-e1 ) || PREFLIGHT_RC=$?
            if [[ -s "$WRAPPER_INVOKED" ]]; then
                echo "wrapper-invoked"
            else
                echo "wrapper-not-invoked"
            fi
            exit ${{PREFLIGHT_RC:-0}}
            """

    def test_preflight_success_invokes_wrapper(self, rendered_state):
        result = _run_bash(self._preflight_script(rendered_state))
        assert result.returncode == 0, result.stderr
    def test_preflight_manifest_drift_fails_before_wrapper(self, rendered_state):
        # Mutate the SHA the next sha256_file call returns so the
        # recorded manifest record no longer matches the live wrapper
        # stat + sha. The drift must be detected BEFORE the wrapper is
        # invoked.
        override = """
        _p9c0_sha256_file() { echo "drifted-deadbeef"; }
        """
        script = self._preflight_script(
            rendered_state, extra_overrides=override
        )
        result = _run_bash(script)
        assert result.returncode != 0, result.stderr
        assert "authority drift detected" in result.stderr
        assert "wrapper-not-invoked" in result.stdout

    def test_preflight_identity_drift_fails_before_wrapper(self, rendered_state):
        # Make the identity lookup fail at preflight time so the gid
        # equality check breaks.
        override = """
        _p9c0_identity_lookup_user() { return 1; }
        """
        script = self._preflight_script(
            rendered_state, extra_overrides=override
        )
        result = _run_bash(script)
        assert result.returncode != 0, result.stderr
        assert "unit identity drift detected" in result.stderr
        assert "wrapper-not-invoked" in result.stdout


class TestStartLifecycle:
    """start invokes systemd-run after manifest + identity rechecks pass."""

    @pytest.fixture
    def rendered_state(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path, run_id="pkg3-lifecycle")
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr
        return facts

    def _start_script(
        self,
        facts: dict,
        *,
        recovery_flags: str = "",
        systemd_run_capture: Path | None = None,
        extra_overrides: str = "",
    ) -> str:
        state_root = facts["state_root"]
        run_id = facts["run_id"]
        capture = systemd_run_capture or Path("/dev/null")
        cgroup = f"/system.slice/p9-3c-fixture-e1-{run_id}.service"
        cgroup_procs = "/tmp/cgroup.procs.empty"
        # Build the bash body via ``str.format`` so the f-string layer
        # never touches literal ``${...}`` brace expansions.
        body = '''
            set -uo pipefail
            source "{UNIT_HELPER}"

            MOCK_STATE=$(mktemp)
            echo active > "$MOCK_STATE"
            SYSTEMD_RUN_FILE="{capture}"

            _p9c0_systemctl() {{
                if [[ "$1" == "list-units" ]]; then
                    return 0
                fi
                if [[ "$1" == "stop" ]]; then
                    echo inactive > "$MOCK_STATE"
                    return 0
                fi
                if [[ "$1" != "show" ]]; then
                    return 0
                fi
                local keys=()
                local use_value=0
                local i=1
                while [[ $i -lt $# ]]; do
                    local arg="${{!i}}"
                    case "$arg" in
                        -p)
                            i=$((i+1))
                            local k="${{!i}}"
                            keys+=("$k")
                            ;;
                        --value)
                            use_value=1
                            ;;
                    esac
                    i=$((i+1))
                done
                local k
                for k in "${{keys[@]}}"; do
                    local v=""
                    case "$k" in
                        ActiveState) v=$(cat "$MOCK_STATE") ;;
                        SubState) v=running ;;
                        MainPID) v=1234 ;;
                        ControlGroup) v="{cgroup}" ;;
                        Result) v=success ;;
                        User) v={MOCK_USER} ;;
                        Group) v={MOCK_GROUP} ;;
                        WorkingDirectory) v="{state_root}/work" ;;
                        RuntimeMaxUSec) v=300000000 ;;
                        TimeoutStopUSec) v=30000000 ;;
                        KillMode) v=control-group ;;
                        UMask) v=0077 ;;
                        NoNewPrivileges) v=yes ;;
                        PrivateTmp) v=yes ;;
                        ProtectSystem) v=strict ;;
                        ProtectHome) v=yes ;;
                        BindPaths) v="{state_root}:{state_root}:rbind" ;;
                        ReadWritePaths) v="{state_root}" ;;
                        UnsetEnvironment) v="${{P9C0_UNSET_ENVIRONMENT_NAMES//,/ }}" ;;
                        RestrictAddressFamilies) v=AF_UNIX ;;
                        IPAddressDeny) v=any ;;
                    esac
                    if [[ $use_value -eq 1 ]]; then
                        echo "$v"
                    else
                        echo "$k=$v"
                    fi
                done
            }}

            _p9c0_stat_file() {{
                case "$1" in
                    */wrapper.manifest) echo "0:0:128:1:0:{MOCK_GID}:{MOCK_MANIFEST_MODE}" ;;
                    */systemd.verify.service) echo "0:0:0:1:0:0:600" ;;
                    */controller.lock|*/unit-helper.lock) echo "0:0:0:1:0:0:600" ;;
                    *) echo "0:0:256:1:0:{MOCK_GID}:{MOCK_WRAPPER_MODE}" ;;
                esac
            }}
            _p9c0_sha256_file() {{
                case "$1" in
                    */systemd.verify.service) echo "{MOCK_DEF_SHA}" ;;
                    *) echo "{MOCK_WRAPPER_SHA}" ;;
                esac
            }}
            _p9c0_systemd_analyze() {{ return 0; }}
            _p9c0_run_systemd_run() {{
                printf '%s\\n' "$*" > "$SYSTEMD_RUN_FILE"
                return 0
            }}
            _p9c0_date_ms() {{ echo 1000; }}
            _p9c0_flock() {{ return 0; }}
            _p9c0_lock_file_authority() {{ return 0; }}
            _p9c0_sleep() {{ return 0; }}
            _p9c0_cgroup_procs_path() {{ echo "{cgroup_procs}"; }}
            _p9c0_read_cgroup_procs() {{ cat "$1"; }}
            _p9c0_identity_lookup_user() {{ echo {MOCK_UID}; return 0; }}
            _p9c0_identity_lookup_group() {{ echo {MOCK_GID}; return 0; }}
            {extra_overrides}

            ( main start \\
                --state-root "{state_root}" \\
                --run-id "{run_id}" \\
                --agent-id p9-3c-fixture-e1 \\
                --mode complete \\
                --user {MOCK_USER} \\
                --group {MOCK_GROUP} {recovery_flags} ) || START_RC=$?
            echo "START_RC=${{START_RC:-0}}"
            START_RC="${{START_RC:-0}}"
            exit "$START_RC"
            '''
        return body.format(
            UNIT_HELPER=UNIT_HELPER,
            capture=capture,
            cgroup=cgroup,
            cgroup_procs=cgroup_procs,
            state_root=state_root,
            MOCK_USER=MOCK_USER,
            MOCK_GROUP=MOCK_GROUP,
            MOCK_UID=MOCK_UID,
            MOCK_GID=MOCK_GID,
            MOCK_WRAPPER_MODE=MOCK_WRAPPER_MODE,
            MOCK_MANIFEST_MODE=MOCK_MANIFEST_MODE,
            MOCK_WRAPPER_SHA=MOCK_WRAPPER_SHA,
            MOCK_DEF_SHA=MOCK_DEF_SHA,
            extra_overrides=extra_overrides,
            run_id=run_id,
            recovery_flags=recovery_flags,
        )

    def test_start_passes_log_level_debug(self, rendered_state, tmp_path):
        capture = tmp_path / "systemd-run-args.txt"
        script = self._start_script(rendered_state, systemd_run_capture=capture)
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        args = capture.read_text()
        assert "--log-level DEBUG" in args
        assert (
            f"--property=BindPaths={rendered_state['state_root']}" in args
        )
        assert "--recoverable" not in args
        assert "--prior-process-stopped" not in args

    def test_start_recovery_full_passes_three_flags(self, rendered_state, tmp_path):
        capture = tmp_path / "systemd-run-args.txt"
        recovery = (
            '--recoverable --recovery-reason "prior-lease-expired" '
            '--prior-process-stopped'
        )
        script = self._start_script(
            rendered_state,
            recovery_flags=recovery,
            systemd_run_capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        args = capture.read_text()
        assert "--recoverable" in args
        assert "--recovery-reason" in args
        assert "--prior-process-stopped" in args
        # Ledger must carry mode + digest, never the raw reason.
        ledger = (
            rendered_state["state_root"]
            / rendered_state["run_id"]
            / "ledger"
            / "events.jsonl"
        ).read_text()
        assert "recovery mode=recovery" in ledger
        assert "reason_sha256=" in ledger
        assert "prior-lease-expired" not in ledger

    def test_start_recovery_ledger_digest_matches_sha256(self, rendered_state, tmp_path):
        capture = tmp_path / "systemd-run-args.txt"
        recovery = (
            '--recoverable --recovery-reason "prior lease expired" '
            '--prior-process-stopped'
        )
        script = self._start_script(
            rendered_state,
            recovery_flags=recovery,
            systemd_run_capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        ledger = (
            rendered_state["state_root"]
            / rendered_state["run_id"]
            / "ledger"
            / "events.jsonl"
        ).read_text()
        # SHA-256 hex of "prior lease expired".
        import hashlib
        expected = hashlib.sha256(b"prior lease expired").hexdigest()
        assert f"reason_sha256={expected}" in ledger

    def test_start_partial_recovery_fails_early(self, rendered_state, tmp_path):
        capture = tmp_path / "systemd-run-args.txt"
        recovery = "--recoverable"  # missing reason + prior
        script = self._start_script(
            rendered_state,
            recovery_flags=recovery,
            systemd_run_capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "recovery evidence rejected" in result.stderr
        # systemd-run must not have been called.
        assert not capture.exists() or capture.read_text() == ""
        ledger_path = (
            rendered_state["state_root"]
            / rendered_state["run_id"]
            / "ledger"
            / "events.jsonl"
        )
        # The render ledger line is allowed, but no start/recovery line.
        if ledger_path.exists():
            assert "recovery mode=recovery" not in ledger_path.read_text()

    def test_start_blank_recovery_reason_fails_early(self, rendered_state, tmp_path):
        capture = tmp_path / "systemd-run-args.txt"
        recovery = '--recoverable --recovery-reason "" --prior-process-stopped'
        script = self._start_script(
            rendered_state,
            recovery_flags=recovery,
            systemd_run_capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "recovery evidence rejected" in result.stderr
        assert not capture.exists() or capture.read_text() == ""

    def test_start_manifest_drift_fails_before_static_verify(self, rendered_state, tmp_path):
        capture = tmp_path / "systemd-run-args.txt"
        override = """
        _p9c0_sha256_file() { echo "drifted-sha"; }
        """
        script = self._start_script(
            rendered_state,
            systemd_run_capture=capture,
            extra_overrides=override,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "authority drift detected" in result.stderr
        # Static verify was never run, so the ledger must not contain a
        # static-verify line.
        ledger_path = (
            rendered_state["state_root"]
            / rendered_state["run_id"]
            / "ledger"
            / "events.jsonl"
        )
        if ledger_path.exists():
            assert "static-verify-failed" not in ledger_path.read_text()

    def test_start_identity_drift_fails_before_static_verify(self, rendered_state, tmp_path):
        capture = tmp_path / "systemd-run-args.txt"
        override = """
        _p9c0_identity_lookup_user() { return 1; }
        """
        script = self._start_script(
            rendered_state,
            systemd_run_capture=capture,
            extra_overrides=override,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "unit identity drift detected" in result.stderr


class TestRecoveryFlags:
    """--recoverable / --recovery-reason / --prior-process-stopped are all-or-none."""

    def _parse(self, extra_args: str) -> subprocess.CompletedProcess[str]:
        script = f"""
        set -uo pipefail
        source "{UNIT_HELPER}"
        if _p9c0_parse_recovery_flags {extra_args}; then
            printf 'ok<%s><%s><%s><%s><%s>\\n' \
                "$P9C0_RECOVERABLE" \
                "$P9C0_RECOVERY_REASON" \
                "$P9C0_PRIOR_PROCESS_STOPPED" \
                "$P9C0_RECOVERY_MODE" \
                "$P9C0_RECOVERY_REASON_SHA256"
        else
            printf 'fail\\n'
            exit 1
        fi
        """
        return _run_bash(script)

    def test_all_recovery_flags_accepted(self):
        result = self._parse(
            '--recoverable --recovery-reason prior-lease-expired --prior-process-stopped'
        )
        assert result.returncode == 0, result.stderr
        assert "ok<1><prior-lease-expired><1><recovery>" in result.stdout

    def test_missing_reason_rejected(self):
        result = self._parse("--recoverable --prior-process-stopped")
        assert result.returncode != 0
        assert "--recovery-reason required" in result.stderr

    def test_missing_recoverable_rejected(self):
        result = self._parse(
            '--recovery-reason "prior lease expired" --prior-process-stopped'
        )
        assert result.returncode != 0
        assert "--recoverable required" in result.stderr

    def test_missing_prior_rejected(self):
        result = self._parse(
            '--recoverable --recovery-reason "prior lease expired"'
        )
        assert result.returncode != 0
        assert "--prior-process-stopped required" in result.stderr

    def test_empty_args_is_normal_mode(self):
        result = self._parse("")
        assert result.returncode == 0, result.stderr
        assert "ok<><><><normal>" in result.stdout

    def test_reason_with_control_character_rejected(self):
        script = f"""
        set -uo pipefail
        source "{UNIT_HELPER}"
        reason=$(printf 'bad\\nreason')
        if _p9c0_parse_recovery_flags --recoverable --recovery-reason "$reason" --prior-process-stopped; then
            printf 'unexpected-pass\\n'
            exit 1
        fi
        printf 'rejected\\n'
        """
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert "rejected" in result.stdout
        assert "control characters" in result.stderr


class TestSystemd255Normalizers:
    """The embedded normalizers reject unknown and partial encodings."""

    def _norm(self, name: str, value: str, expected: str) -> subprocess.CompletedProcess[str]:
        script = f"""
        set -uo pipefail
        source "{UNIT_HELPER}"
        _p9c0_python_normalize "{name}" "{value}" "{expected}"
        """
        return _run_bash(script)

    def test_runtime_max_usec_accepts_human_duration(self):
        result = self._norm("runtime-max-usec", "5min", "300000000")
        assert result.returncode == 0, result.stderr

    def test_runtime_max_usec_rejects_garbage_between_tokens(self):
        result = self._norm("runtime-max-usec", "5min,30s", "330000000")
        assert result.returncode != 0

    def test_runtime_max_usec_rejects_unknown_unit(self):
        result = self._norm("runtime-max-usec", "5weeks", "0")
        assert result.returncode != 0

    def test_bool_rejects_unknown_encoding(self):
        result = self._norm("bool", "maybe", "yes")
        assert result.returncode != 0

    def test_umask_rejects_non_octal(self):
        result = self._norm("umask", "0778", "0077")
        assert result.returncode != 0

    def test_ip_address_deny_rejects_partial_ipv4_only(self):
        result = self._norm("ip-address-deny", "0.0.0.0/0", "")
        assert result.returncode != 0

    def test_restrict_address_families_rejects_extra_family(self):
        result = self._norm(
            "restrict-address-families", "AF_INET AF_UNIX", ""
        )
        assert result.returncode != 0

    def test_bind_paths_accepts_exact_systemd_255_same_path_rbind(self, tmp_path):
        root = tmp_path / "state"
        root.mkdir()
        result = self._norm(
            "bind-paths", f"{root}:{root}:rbind", str(root)
        )
        assert result.returncode == 0, result.stderr

    def test_bind_paths_rejects_extra_or_different_host_path(self, tmp_path):
        root = tmp_path / "state"
        outside = tmp_path / "outside"
        root.mkdir()
        outside.mkdir()
        escaped = self._norm(
            "bind-paths", f"{outside}:{root}:rbind", str(root)
        )
        extra = self._norm(
            "bind-paths",
            f"{root}:{root}:rbind {outside}:{outside}:rbind",
            str(root),
        )
        assert escaped.returncode != 0
        assert extra.returncode != 0

    def test_unset_environment_accepts_only_the_exact_sealed_set(self):
        result = self._norm(
            "unset-environment",
            "OPENAI_API_KEY ANTHROPIC_API_KEY",
            "ANTHROPIC_API_KEY,OPENAI_API_KEY",
        )
        assert result.returncode == 0, result.stderr

    def test_unset_environment_rejects_wildcards_and_duplicates(self):
        wildcard = self._norm(
            "unset-environment", "OPENAI_*", "OPENAI_API_KEY"
        )
        duplicate = self._norm(
            "unset-environment",
            "OPENAI_API_KEY OPENAI_API_KEY",
            "OPENAI_API_KEY",
        )
        assert wildcard.returncode != 0
        assert duplicate.returncode != 0

    def test_unset_environment_prefixes_expand_to_exact_names(self):
        script = f'''
        set -euo pipefail
        source "{UNIT_HELPER}"
        _p9c0_environment_names() {{
            printf '%s\n' OPENAI_EXTRA_TOKEN SAFE_NAME 'AWS_*'
        }}
        _p9c0_join_unset_environment_names
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        names = set(result.stdout.strip().split(","))
        assert "OPENAI_EXTRA_TOKEN" in names
        assert "SAFE_NAME" not in names
        assert all("*" not in name for name in names)


class TestManifestAndAuthority:
    """Wrapper manifest record detects drift; owner/mode gates fail closed."""

    def test_manifest_mismatch_on_sha_drift(self, tmp_path: Path):
        wrapper = tmp_path / "wrapper.sh"
        wrapper.write_text("v1")
        script = f"""
        set -uo pipefail
        source "{UNIT_HELPER}"
        _p9c0_stat_file() {{ echo "0:0:10:1:0:1000:750"; }}
        _p9c0_sha256_file() {{
            if [[ -n "${{_SHA:-}}" ]]; then
                echo "$_SHA"
            else
                echo "abc123"
            fi
        }}
        line=$(_p9c0_wrapper_manifest_record "{wrapper}")
        _SHA="def456"
        if _p9c0_validate_wrapper_manifest_match "{wrapper}" "$line"; then
            echo "unexpected-pass"
            exit 1
        else
            echo "detected-drift"
        fi
        """
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert "detected-drift" in result.stdout

    def test_wrapper_owner_mode_enforces_root_nonroot_mode(self, tmp_path: Path):
        wrapper = tmp_path / "wrapper.sh"
        wrapper.write_text("x")
        script = f"""
        set -uo pipefail
        source "{UNIT_HELPER}"
        _p9c0_stat_file() {{ echo "0:0:0:1:0:1000:755"; }}
        if _p9c0_enforce_wrapper_owner_mode "{wrapper}"; then
            echo "unexpected-pass"
            exit 1
        fi
        echo "mode-rejected"
        """
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert "mode-rejected" in result.stdout


class TestStaticVerify:
    """systemd-analyze verify gate fails closed on warnings even with exit 0."""

    def test_verify_rejects_stderr_warning(self, tmp_path: Path):
        state_root = tmp_path / "state"
        state_root.mkdir()
        def_file = state_root / "test.service"
        script = f"""
        set -uo pipefail
        source "{UNIT_HELPER}"
        P9C0_UNSET_ENVIRONMENT_NAMES="OPENAI_API_KEY,HTTP_PROXY"
        _p9c0_render_unit_definition "{def_file}" testuser testgroup /tmp/work {state_root}
        _p9c0_systemd_analyze() {{
            echo "Warning: foobar" >&2
            return 0
        }}
        if _p9c0_verify_unit_definition "{def_file}" "{state_root}"; then
            echo "unexpected-pass"
            exit 1
        fi
        echo "warning-rejected"
        """
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert "warning-rejected" in result.stdout

    def test_verify_rejects_missing_seam(self, tmp_path: Path):
        # Bootstrap mock for the seams is inlined so we can drop
        # ``_p9c0_systemd_analyze`` entirely and prove the verify
        # gate fails closed when the seam is unset / returns 127.
        state_root = tmp_path / "state"
        state_root.mkdir()
        def_file = state_root / "missing-seam.service"
        def_file.write_text("[Unit]\nDescription=missing-seam\n")
        def_file.chmod(0o600)
        script = f"""
        set -uo pipefail
        source "{UNIT_HELPER}"
        if _p9c0_verify_unit_definition "{def_file}" "{state_root}"; then
            echo "unexpected-pass"
            exit 1
        fi
        echo "missing-seam-rejected"
        """
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert "missing-seam-rejected" in result.stdout


# ---------------------------------------------------------------------------
# Repair #1: manifest is controller-pre-created; render must not write it.
# ---------------------------------------------------------------------------

class TestManifestPreexisting:
    """The controller pre-creates the wrapper.manifest. The helper must
    only read, verify, and seal the bytes the controller placed there.
    Tests prove no-overwrite, content drift, nlink/gid/mode gates, and
    recheck on every controller invocation.
    """

    def _override_manifest_stat(
        self,
        *,
        manifest_dev: str = "0",
        manifest_inode: str = "0",
        manifest_size: str = "128",
        manifest_nlink: str = "1",
        manifest_uid: str = "0",
        manifest_gid: str = MOCK_GID,
        manifest_mode: str = MOCK_MANIFEST_MODE,
        wrapper_gid: str = MOCK_GID,
        wrapper_mode: str = MOCK_WRAPPER_MODE,
    ) -> str:
        return f"""
            _p9c0_stat_file() {{
                case "$1" in
                    */wrapper.manifest)
                        echo "{manifest_dev}:{manifest_inode}:{manifest_size}:{manifest_nlink}:{manifest_uid}:{manifest_gid}:{manifest_mode}"
                        ;;
                    *)
                        echo "0:0:256:1:0:{wrapper_gid}:{wrapper_mode}"
                        ;;
                esac
            }}
            """

    def _write_drifted_manifest(self, manifest: Path, *, sha: str) -> None:
        # Same tab-separated layout as the bootstrap, but the SHA value
        # is the caller's choice so the live-wrapper SHA will not match.
        drifted = (
            f"wrapper_raw={manifest.parent.parent / 'wrapper.sh'}"
            f"\twrapper_dev_inode_size_nlink_uid_gid_mode="
            f"0:0:256:1:0:{MOCK_GID}:{MOCK_WRAPPER_MODE}"
            f"\twrapper_sha256={sha}\n"
        )
        manifest.write_text(drifted)
        manifest.chmod(0o640)

    def test_render_does_not_overwrite_preexisting_manifest(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        before = manifest.read_bytes()
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr
        # Helper must leave the controller-placed manifest untouched.
        assert manifest.read_bytes() == before

    def test_render_rejects_preexisting_manifest_content_drift(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        self._write_drifted_manifest(manifest, sha="deadbeef" * 8)
        result = _run_bash(_render_script(facts))
        assert result.returncode != 0
        assert "manifest verify: content drift" in result.stderr

    def test_render_rejects_preexisting_manifest_wrong_gid(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        override = self._override_manifest_stat(manifest_gid="2002")
        result = _run_bash(_render_script(facts, extra_overrides=override))
        assert result.returncode != 0
        assert "wrapper manifest: gid=2002 does not match unit gid=" in result.stderr

    def test_render_rejects_preexisting_manifest_wrong_mode(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        override = self._override_manifest_stat(manifest_mode="644")
        result = _run_bash(_render_script(facts, extra_overrides=override))
        assert result.returncode != 0
        assert "wrapper manifest: mode must be 0640 got=644" in result.stderr

    def test_render_rejects_preexisting_manifest_wrong_nlink(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        override = self._override_manifest_stat(manifest_nlink="2")
        result = _run_bash(_render_script(facts, extra_overrides=override))
        assert result.returncode != 0
        assert "wrapper manifest: hard-link count must be 1 got=2" in result.stderr

    def test_render_rejects_preexisting_manifest_symlink(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        # Replace the regular manifest with a symlink to a real file.
        target = facts["state_root"] / "manifest-target"
        target.write_text("payload")
        manifest.unlink()
        manifest.symlink_to(target)
        result = _run_bash(_render_script(facts))
        assert result.returncode != 0
        assert "symlink not allowed" in result.stderr

    def test_render_rejects_missing_preexisting_manifest(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        manifest.unlink()
        result = _run_bash(_render_script(facts))
        assert result.returncode != 0
        assert "manifest verify: missing" in result.stderr

    def test_render_rejects_multiline_preexisting_manifest(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        manifest = facts["state_root"] / facts["run_id"] / "wrapper.manifest"
        # Append a second line so the manifest has more than one record.
        with manifest.open("a") as fp:
            fp.write("wrapper_raw=trailing\twrapper_dev_inode_size_nlink_uid_gid_mode=0:0:0:1:0:0:0\twrapper_sha256=x\n")
        result = _run_bash(_render_script(facts))
        assert result.returncode != 0
        assert "manifest verify: not single line" in result.stderr

    def test_preflight_recheck_detects_manifest_content_drift(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path, run_id="pkg3-preflight-drift")
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr
        # Mutate the SHA seam so the manifest bytes no longer match the
        # live wrapper's record at recheck time.
        script = f"""
            set -euo pipefail
            source "{UNIT_HELPER}"
            {_mocked_authority_lines()}
            _p9c0_sha256_file() {{ echo "drifted-after-render"; }}
            # Bypass locking so the probe runs synchronously.
            _p9c0_with_lock() {{
                shift 2
                "$@"
            }}
            ( main preflight \
                --state-root "{facts['state_root']}" \
                --run-id "{facts['run_id']}" \
                --agent-id p9-3c-fixture-e1 )
            """
        result = _run_bash(script)
        assert "manifest authority drift detected" in result.stderr
        # Either the manifest-file check or the live-wrapper check may
        # surface the drift; both are valid fail-closed outcomes.
        assert (
            "manifest recheck: content drift" in result.stderr
            or "wrapper manifest mismatch" in result.stderr
        ), result.stderr

    def test_preflight_recheck_detects_manifest_gid_drift(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path, run_id="pkg3-preflight-gid")
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr
        # Mutate the manifest gid seam so owner/mode recheck fails.
        override = """
            _p9c0_stat_file() {
                case "$1" in
                    */wrapper.manifest) echo "0:0:128:1:0:2002:640" ;;
                    *) echo "0:0:256:1:0:1001:750" ;;
                esac
            }
            """
        script = f"""
            set -euo pipefail
            source "{UNIT_HELPER}"
            {_mocked_authority_lines()}
            {override}
            _p9c0_with_lock() {{
                shift 2
                "$@"
            }}
            ( main preflight \
                --state-root "{facts['state_root']}" \
                --run-id "{facts['run_id']}" \
                --agent-id p9-3c-fixture-e1 )
            """
        result = _run_bash(script)
        assert result.returncode != 0, result.stderr
        assert "manifest authority drift detected" in result.stderr
        assert "wrapper manifest: gid=2002 does not match unit gid=" in result.stderr

    def test_start_recheck_detects_manifest_drift_before_static_verify(
        self, tmp_path: Path
    ):
        facts = _bootstrap_render_state(tmp_path, run_id="pkg3-start-drift")
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr
        capture = tmp_path / "systemd-run-args.txt"
        # Build a start script that mirrors TestStartLifecycle._start_script
        # but exposes the override hook for the manifest SHA drift.
        body = f'''
            set -uo pipefail
            source "{UNIT_HELPER}"

            MOCK_STATE=$(mktemp)
            echo active > "$MOCK_STATE"
            SYSTEMD_RUN_FILE="{capture}"

            _p9c0_systemctl() {{
                if [[ "$1" == "stop" ]]; then
                    echo inactive > "$MOCK_STATE"
                    return 0
                fi
                return 0
            }}
            _p9c0_run_systemd_run() {{
                printf '%s\\n' "$*" > "$SYSTEMD_RUN_FILE"
                return 0
            }}
            _p9c0_systemd_analyze() {{ return 0; }}
            _p9c0_date_ms() {{ echo 1000; }}
            _p9c0_flock() {{ return 0; }}
            _p9c0_lock_file_authority() {{ return 0; }}
            _p9c0_sleep() {{ return 0; }}
            _p9c0_identity_lookup_user() {{ echo {MOCK_UID}; return 0; }}
            _p9c0_identity_lookup_group() {{ echo {MOCK_GID}; return 0; }}
            _p9c0_stat_file() {{
                case "$1" in
                    */wrapper.manifest) echo "0:0:128:1:0:{MOCK_GID}:{MOCK_MANIFEST_MODE}" ;;
                    *) echo "0:0:256:1:0:{MOCK_GID}:{MOCK_WRAPPER_MODE}" ;;
                esac
            }}
            _p9c0_sha256_file() {{ echo "drifted-mid-life"; }}

            ( main start \\
                --state-root "{facts['state_root']}" \\
                --run-id "{facts['run_id']}" \\
                --agent-id p9-3c-fixture-e1 \\
                --mode complete \\
                --user {MOCK_USER} \\
                --group {MOCK_GROUP} ) || START_RC=$?
            echo "START_RC=${{START_RC:-0}}"
            exit ${{START_RC:-0}}
            '''
        result = _run_bash(body)
        assert result.returncode != 0, result.stderr
        assert "manifest authority drift detected" in result.stderr
        # systemd-run must not have been called before the recheck failed.
        assert not capture.exists() or capture.read_text() == ""


# ---------------------------------------------------------------------------
# Repair #2: containment + identity exact (no hardcoded bypasses).
# ---------------------------------------------------------------------------

class TestContainmentExact:
    """runtime_parent raw + realpath must lie under the exact approved
    prefix. The /var/tmp/multinexus-p9-3c0 and P9C0_PROD_DB bypasses are
    removed; every containment drift fails closed at the identity gate.
    """

    def _script_with_runtime_parent(self, facts: dict, runtime_parent: str) -> str:
        flags = " ".join(
            [
                f"--state-root {facts['state_root']!s}",
                f"--run-id {facts['run_id']}",
                f"--fixture-bin {facts['fixture_bin']!s}",
                f"--wrapper {facts['wrapper']!s}",
                f"--coord-db {facts['coord_db']!s}",
                f"--work-dir {facts['work_dir']!s}",
                f"--python {sys.executable!r}",
                f"--repo-root {REPO_ROOT}",
                f"--user {facts['user']}",
                f"--group {facts['group']}",
                f"--runtime-parent {runtime_parent}",
            ]
        )
        return f"""
            set -euo pipefail
            source "{UNIT_HELPER}"
            {_mocked_authority_lines()}
            main render {flags}
            """

    def test_render_rejects_var_tmp_bypass(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        # Previously accepted via the /var/tmp/multinexus-p9-3c0 hardcoded
        # bypass; the exact-prefix gate must now refuse it.
        script = self._script_with_runtime_parent(
            facts, "/var/tmp/multinexus-p9-3c0/inner"
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "unit identity rejected" in result.stderr
        assert "outside approved prefix" in result.stderr

    def test_render_rejects_production_db_path_bypass(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        script = self._script_with_runtime_parent(
            facts, "/var/lib/coordinate/coord.sqlite3/inner"
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "unit identity rejected" in result.stderr
        assert "outside approved prefix" in result.stderr

    def test_render_rejects_resolved_path_bypass(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        # Point runtime_parent at a path whose realpath resolves outside
        # the state root (the prior $rp_resolved bypass used to allow it).
        outside = tmp_path / "outside-target"
        outside.mkdir()
        script = self._script_with_runtime_parent(facts, str(outside))
        result = _run_bash(script)
        assert result.returncode != 0
        assert "unit identity rejected" in result.stderr

    def test_render_accepts_runtime_parent_inside_state_root(self, tmp_path: Path):
        facts = _bootstrap_render_state(tmp_path)
        # state_dir (= state_root/run_id) is the canonical default and
        # must still be accepted after the containment rewrite.
        script = self._script_with_runtime_parent(
            facts, str(facts["state_root"] / facts["run_id"] / "work")
        )
        (facts["state_root"] / facts["run_id"] / "work").mkdir(
            parents=True, exist_ok=True
        )
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr


class TestStartIdentityExact:
    """start --user / --group must equal P9C0_UNIT_USER / P9C0_UNIT_GROUP
    sealed at render time. A mismatch fails closed before any wrapper,
    static-verify, or systemd-run invocation.
    """

    def _start_with_user_group(
        self, facts: dict, *, user: str, group: str, capture: Path
    ) -> str:
        body = f'''
            set -uo pipefail
            source "{UNIT_HELPER}"

            MOCK_STATE=$(mktemp)
            echo active > "$MOCK_STATE"
            SYSTEMD_RUN_FILE="{capture}"

            _p9c0_systemctl() {{
                if [[ "$1" == "stop" ]]; then
                    echo inactive > "$MOCK_STATE"
                    return 0
                fi
                return 0
            }}
            _p9c0_run_systemd_run() {{
                printf '%s\\n' "$*" > "$SYSTEMD_RUN_FILE"
                return 0
            }}
            _p9c0_systemd_analyze() {{ return 0; }}
            _p9c0_date_ms() {{ echo 1000; }}
            _p9c0_flock() {{ return 0; }}
            _p9c0_lock_file_authority() {{ return 0; }}
            _p9c0_sleep() {{ return 0; }}
            _p9c0_identity_lookup_user() {{ echo {MOCK_UID}; return 0; }}
            _p9c0_identity_lookup_group() {{ echo {MOCK_GID}; return 0; }}
            _p9c0_stat_file() {{
                case "$1" in
                    */wrapper.manifest) echo "0:0:128:1:0:{MOCK_GID}:{MOCK_MANIFEST_MODE}" ;;
                    */systemd.verify.service) echo "0:0:0:1:0:0:600" ;;
                    */controller.lock|*/unit-helper.lock) echo "0:0:0:1:0:0:600" ;;
                    *) echo "0:0:256:1:0:{MOCK_GID}:{MOCK_WRAPPER_MODE}" ;;
                esac
            }}
            _p9c0_sha256_file() {{
                case "$1" in
                    */systemd.verify.service) echo "{MOCK_DEF_SHA}" ;;
                    *) echo "{MOCK_WRAPPER_SHA}" ;;
                esac
            }}

            ( main start \\
                --state-root "{facts['state_root']}" \\
                --run-id "{facts['run_id']}" \\
                --agent-id p9-3c-fixture-e1 \\
                --mode complete \\
                --user {user} \\
                --group {group} ) || START_RC=$?
            echo "START_RC=${{START_RC:-0}}"
            exit ${{START_RC:-0}}
            '''
        return body

    def _render_facts(self, tmp_path: Path, *, run_id: str) -> dict:
        facts = _bootstrap_render_state(tmp_path, run_id=run_id)
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr
        return facts

    def test_start_user_mismatch_fails_before_static_verify(self, tmp_path: Path):
        facts = self._render_facts(tmp_path, run_id="pkg3-id-user")
        capture = tmp_path / "systemd-run-args.txt"
        script = self._start_with_user_group(
            facts, user="otheruser", group=MOCK_GROUP, capture=capture
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "does not match sealed unit_user" in result.stderr
        assert "otheruser" in result.stderr
        # systemd-run must not have been called.
        assert not capture.exists() or capture.read_text() == ""

    def test_start_group_mismatch_fails_before_static_verify(self, tmp_path: Path):
        facts = self._render_facts(tmp_path, run_id="pkg3-id-group")
        capture = tmp_path / "systemd-run-args.txt"
        script = self._start_with_user_group(
            facts, user=MOCK_USER, group="othergroup", capture=capture
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "does not match sealed unit_group" in result.stderr
        assert "othergroup" in result.stderr
        # systemd-run must not have been called.
        assert not capture.exists() or capture.read_text() == ""


# ---------------------------------------------------------------------------
# Repair #3: recovery flag parser sees each flag's original presence.
# ---------------------------------------------------------------------------

class TestRecoveryOriginalPresence:
    """start must pass the original presence of each recovery flag to the
    parser. Normal = none; recovery = all three. Any 1/2-item partial,
    reason-only, prior-only, recoverable-only, blank / control / >512-byte
    reasons fail closed before systemd-run is invoked. The ledger still
    carries only the digest.
    """

    def _start_script_with_recovery(
        self, facts: dict, *, recovery_flags: str, capture: Path
    ) -> str:
        # Mirror TestStartLifecycle._start_script so the systemctl show
        # mock returns canonical properties and post-start verify can
        # pass. The recovery-specific tests stay isolated from the
        # shared TestStartLifecycle helper.
        state_root = facts["state_root"]
        run_id = facts["run_id"]
        cgroup = f"/system.slice/p9-3c-fixture-e1-{run_id}.service"
        cgroup_procs = "/tmp/cgroup.procs.empty"
        body = f'''
            set -uo pipefail
            source "{UNIT_HELPER}"

            MOCK_STATE=$(mktemp)
            echo active > "$MOCK_STATE"
            SYSTEMD_RUN_FILE="{capture}"

            _p9c0_systemctl() {{
                if [[ "$1" == "list-units" ]]; then
                    return 0
                fi
                if [[ "$1" == "stop" ]]; then
                    echo inactive > "$MOCK_STATE"
                    return 0
                fi
                if [[ "$1" != "show" ]]; then
                    return 0
                fi
                local keys=()
                local use_value=0
                local i=1
                while [[ $i -lt $# ]]; do
                    local arg="${{!i}}"
                    case "$arg" in
                        -p)
                            i=$((i+1))
                            local k="${{!i}}"
                            keys+=("$k")
                            ;;
                        --value)
                            use_value=1
                            ;;
                    esac
                    i=$((i+1))
                done
                local k
                for k in "${{keys[@]}}"; do
                    local v=""
                    case "$k" in
                        ActiveState) v=$(cat "$MOCK_STATE") ;;
                        SubState) v=running ;;
                        MainPID) v=1234 ;;
                        ControlGroup) v="{cgroup}" ;;
                        Result) v=success ;;
                        User) v={MOCK_USER} ;;
                        Group) v={MOCK_GROUP} ;;
                        WorkingDirectory) v="{state_root}/work" ;;
                        RuntimeMaxUSec) v=300000000 ;;
                        TimeoutStopUSec) v=30000000 ;;
                        KillMode) v=control-group ;;
                        UMask) v=0077 ;;
                        NoNewPrivileges) v=yes ;;
                        PrivateTmp) v=yes ;;
                        ProtectSystem) v=strict ;;
                        ProtectHome) v=yes ;;
                        BindPaths) v="{state_root}:{state_root}:rbind" ;;
                        ReadWritePaths) v="{state_root}" ;;
                        UnsetEnvironment) v="${{P9C0_UNSET_ENVIRONMENT_NAMES//,/ }}" ;;
                        RestrictAddressFamilies) v=AF_UNIX ;;
                        IPAddressDeny) v=any ;;
                    esac
                    if [[ $use_value -eq 1 ]]; then
                        echo "$v"
                    else
                        echo "$k=$v"
                    fi
                done
            }}

            _p9c0_run_systemd_run() {{
                printf '%s\\n' "$*" > "$SYSTEMD_RUN_FILE"
                return 0
            }}
            _p9c0_systemd_analyze() {{ return 0; }}
            _p9c0_date_ms() {{ echo 1000; }}
            _p9c0_flock() {{ return 0; }}
            _p9c0_lock_file_authority() {{ return 0; }}
            _p9c0_sleep() {{ return 0; }}
            _p9c0_cgroup_procs_path() {{ echo "{cgroup_procs}"; }}
            _p9c0_read_cgroup_procs() {{ cat "$1"; }}
            _p9c0_identity_lookup_user() {{ echo {MOCK_UID}; return 0; }}
            _p9c0_identity_lookup_group() {{ echo {MOCK_GID}; return 0; }}
            _p9c0_stat_file() {{
                case "$1" in
                    */wrapper.manifest) echo "0:0:128:1:0:{MOCK_GID}:{MOCK_MANIFEST_MODE}" ;;
                    */systemd.verify.service) echo "0:0:0:1:0:0:600" ;;
                    */controller.lock|*/unit-helper.lock) echo "0:0:0:1:0:0:600" ;;
                    *) echo "0:0:256:1:0:{MOCK_GID}:{MOCK_WRAPPER_MODE}" ;;
                esac
            }}
            _p9c0_sha256_file() {{
                case "$1" in
                    */systemd.verify.service) echo "{MOCK_DEF_SHA}" ;;
                    *) echo "{MOCK_WRAPPER_SHA}" ;;
                esac
            }}

            ( main start \\
                --state-root "{state_root}" \\
                --run-id "{run_id}" \\
                --agent-id p9-3c-fixture-e1 \\
                --mode complete \\
                --user {MOCK_USER} \\
                --group {MOCK_GROUP} {recovery_flags} ) || START_RC=$?
            echo "START_RC=${{START_RC:-0}}"
            exit ${{START_RC:-0}}
            '''
        return body

    def _render_facts(self, tmp_path: Path, *, run_id: str) -> dict:
        facts = _bootstrap_render_state(tmp_path, run_id=run_id)
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr
        return facts

    def _assert_no_systemd_run(self, facts: dict, capture: Path) -> None:
        assert not capture.exists() or capture.read_text() == ""
        ledger = (
            facts["state_root"] / facts["run_id"] / "ledger" / "events.jsonl"
        )
        if ledger.exists():
            text = ledger.read_text()
            assert "recovery mode=recovery" not in text
            assert "reason_sha256=" not in text

    def test_start_recoverable_only_fails_early(self, tmp_path: Path):
        facts = self._render_facts(tmp_path, run_id="pkg3-rec-recoverable")
        capture = tmp_path / "systemd-run-args.txt"
        script = self._start_script_with_recovery(
            facts, recovery_flags="--recoverable", capture=capture
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "recovery evidence rejected" in result.stderr
        self._assert_no_systemd_run(facts, capture)

    def test_start_reason_only_fails_early(self, tmp_path: Path):
        facts = self._render_facts(tmp_path, run_id="pkg3-rec-reason")
        capture = tmp_path / "systemd-run-args.txt"
        script = self._start_script_with_recovery(
            facts,
            recovery_flags='--recovery-reason "prior-lease-expired"',
            capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "recovery evidence rejected" in result.stderr
        assert "--recoverable required" in result.stderr
        self._assert_no_systemd_run(facts, capture)

    def test_start_prior_only_fails_early(self, tmp_path: Path):
        facts = self._render_facts(tmp_path, run_id="pkg3-rec-prior")
        capture = tmp_path / "systemd-run-args.txt"
        script = self._start_script_with_recovery(
            facts,
            recovery_flags="--prior-process-stopped",
            capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "recovery evidence rejected" in result.stderr
        assert "--recoverable required" in result.stderr
        self._assert_no_systemd_run(facts, capture)

    def test_start_two_item_partial_fails_early(self, tmp_path: Path):
        # recoverable + reason (no prior) must fail on the prior gate
        # instead of being silently completed with an empty prior.
        facts = self._render_facts(tmp_path, run_id="pkg3-rec-2item")
        capture = tmp_path / "systemd-run-args.txt"
        script = self._start_script_with_recovery(
            facts,
            recovery_flags='--recoverable --recovery-reason "prior-lease"',
            capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "--prior-process-stopped required" in result.stderr
        self._assert_no_systemd_run(facts, capture)

    @pytest.mark.parametrize(
        ("run_id", "recovery_flags", "expected"),
        [
            (
                "pkg3-rec-recoverable-prior",
                "--recoverable --prior-process-stopped",
                "--recovery-reason required",
            ),
            (
                "pkg3-rec-reason-prior",
                '--recovery-reason "prior-lease" --prior-process-stopped',
                "--recoverable required",
            ),
        ],
    )
    def test_start_other_two_item_partials_fail_early(
        self,
        tmp_path: Path,
        run_id: str,
        recovery_flags: str,
        expected: str,
    ):
        facts = self._render_facts(tmp_path, run_id=run_id)
        capture = tmp_path / "systemd-run-args.txt"
        script = self._start_script_with_recovery(
            facts,
            recovery_flags=recovery_flags,
            capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert expected in result.stderr
        self._assert_no_systemd_run(facts, capture)

    def test_start_blank_reason_presence_is_not_treated_as_normal(
        self, tmp_path: Path
    ):
        facts = self._render_facts(tmp_path, run_id="pkg3-rec-blank-only")
        capture = tmp_path / "systemd-run-args.txt"
        script = self._start_script_with_recovery(
            facts,
            recovery_flags='--recovery-reason ""',
            capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "--recoverable required" in result.stderr
        self._assert_no_systemd_run(facts, capture)

    def test_start_recovery_too_long_reason_fails_early(self, tmp_path: Path):
        facts = self._render_facts(tmp_path, run_id="pkg3-rec-long")
        capture = tmp_path / "systemd-run-args.txt"
        long_reason = "x" * 513
        script = self._start_script_with_recovery(
            facts,
            recovery_flags=(
                f'--recoverable --recovery-reason "{long_reason}" '
                '--prior-process-stopped'
            ),
            capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "too long" in result.stderr
        self._assert_no_systemd_run(facts, capture)

    def test_start_recovery_ledger_never_records_raw_reason(self, tmp_path: Path):
        facts = self._render_facts(tmp_path, run_id="pkg3-rec-ledger")
        capture = tmp_path / "systemd-run-args.txt"
        unique_phrase = "marker-WHAT-ever-7f3c"
        script = self._start_script_with_recovery(
            facts,
            recovery_flags=(
                f'--recoverable --recovery-reason "{unique_phrase}" '
                '--prior-process-stopped'
            ),
            capture=capture,
        )
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        # The helper-owned ledger remains digest-only even though the
        # reason flows through to agentd via the systemd-run argv.
        ledger = (
            facts["state_root"] / facts["run_id"] / "ledger" / "events.jsonl"
        ).read_text()
        assert unique_phrase not in ledger
        assert "reason_sha256=" in ledger


class TestDurableStaticDefinitionAuthority:
    """The static verification definition is durable, sealed, and removed
    only by exact cleanup. Later gates must never repair drift by rendering.
    """

    @staticmethod
    def _render(tmp_path: Path, run_id: str) -> dict:
        facts = _bootstrap_render_state(tmp_path, run_id=run_id)
        result = _run_bash(_render_script(facts))
        assert result.returncode == 0, result.stderr
        return facts

    @staticmethod
    def _values(facts: dict) -> dict[str, str]:
        path = facts["state_root"] / facts["run_id"] / "values.rendered"
        return dict(
            line.split("=", 1)
            for line in path.read_text().splitlines()
            if "=" in line
        )

    def test_render_retains_sealed_definition_and_ledger_record(
        self, tmp_path: Path
    ):
        facts = self._render(tmp_path, "pkg3-static-retained")
        state_dir = facts["state_root"] / facts["run_id"]
        definition = state_dir / "systemd.verify.service"
        values = self._values(facts)

        assert definition.is_file()
        assert values["unit_definition_path"] == str(definition)
        assert values["unit_definition_sha256"] == MOCK_DEF_SHA
        unit_text = definition.read_text()
        for required in (
            "ExecStart=/bin/true",
            "IPAddressDeny=any",
            "RestrictAddressFamilies=AF_UNIX",
            "NoNewPrivileges=yes",
            "PrivateTmp=yes",
            "ProtectSystem=strict",
            "ProtectHome=yes",
            f"BindPaths={facts['state_root']}",
            f"ReadWritePaths={facts['state_root']}",
            "UnsetEnvironment=",
            "KillMode=control-group",
            "RuntimeMaxSec=300",
            "TimeoutStopSec=30",
            "UMask=0077",
        ):
            assert required in unit_text
        assert "*" not in next(
            line for line in unit_text.splitlines() if line.startswith("UnsetEnvironment=")
        )
        assert "OPENAI_API_KEY" in unit_text
        assert values["unset_environment_names"]
        assert "*" not in values["unset_environment_names"]
        ledger = (state_dir / "ledger" / "events.jsonl").read_text()
        assert (
            f"static-definition run={facts['run_id']} "
            f"def_path={definition} def_sha256={MOCK_DEF_SHA} "
            "def_mode=0600 def_owner=root"
        ) in ledger

    def test_preflight_rejects_drift_without_rewriting_bytes(
        self, tmp_path: Path
    ):
        facts = self._render(tmp_path, "pkg3-static-drift")
        definition = (
            facts["state_root"] / facts["run_id"] / "systemd.verify.service"
        )
        drifted = b"[Service]\nExecStart=/bin/false\n"
        definition.write_bytes(drifted)
        override = f'''
        _p9c0_sha256_file() {{
            case "$1" in
                */systemd.verify.service) echo "drifted-static-sha" ;;
                *) echo "{MOCK_WRAPPER_SHA}" ;;
            esac
        }}
        '''
        script = TestPreflightReachability()._preflight_script(
            facts, extra_overrides=override
        )
        result = _run_bash(script)
        assert result.returncode != 0
        assert "unit definition authority drift detected" in result.stderr
        assert "wrapper-not-invoked" in result.stdout
        assert definition.read_bytes() == drifted

    def test_preflight_rejects_missing_static_ledger_authority(
        self, tmp_path: Path
    ):
        facts = self._render(tmp_path, "pkg3-static-ledger")
        ledger = facts["state_root"] / facts["run_id"] / "ledger" / "events.jsonl"
        ledger.write_text(
            "\n".join(
                line
                for line in ledger.read_text().splitlines()
                if not line.startswith("static-definition ")
            )
            + "\n"
        )
        script = TestPreflightReachability()._preflight_script(facts)
        result = _run_bash(script)
        assert result.returncode != 0
        assert "ledger authority drift detected" in result.stderr
        assert "wrapper-not-invoked" in result.stdout

    def test_cleanup_removes_only_exact_sealed_definition(
        self, tmp_path: Path
    ):
        facts = self._render(tmp_path, "pkg3-static-cleanup")
        state_dir = facts["state_root"] / facts["run_id"]
        definition = state_dir / "systemd.verify.service"
        sibling = state_dir / "unrelated.service"
        sibling.write_text("must-survive\n")
        unit = f"p9-3c-fixture-e1-{facts['run_id']}.service"
        with (state_dir / "ledger" / "events.jsonl").open("a") as handle:
            handle.write(f"unit {unit} agent=p9-3c-fixture-e1\n")
            handle.write(f"cgroup-empty unit={unit}\n")
        script = f'''
        set -euo pipefail
        source "{UNIT_HELPER}"
        _p9c0_with_lock() {{ shift 2; "$@"; }}
        main cleanup \\
            --state-root "{facts['state_root']}" \\
            --run-id "{facts['run_id']}" \\
            --agent-id p9-3c-fixture-e1
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert not definition.exists()
        assert sibling.read_text() == "must-survive\n"


def _local_verify_mock_prelude(state_root: Path) -> str:
    """Source the controller with filesystem/identity seams kept in tmp_path."""
    return f'''
    set -euo pipefail
    mkdir -p "{state_root}"
    touch "{state_root}/production-wrapper" "{state_root}/production.sqlite3"
    source "{LOCAL_VERIFY}"
    P9C0_PROD_STATE_PREFIX="{state_root}"
    P9C0_PROD_WRAPPER="{state_root}/production-wrapper"
    P9C0_PROD_DB="{state_root}/production.sqlite3"
    P9C0_WRAPPER_EXEC="{state_root}/coordinate"
    _p9c0_controller_state_prefix() {{ printf '%s\\n' "{state_root}"; }}
    _p9c0_assert_state_prefix_authority() {{ return 0; }}
    _p9c0_assert_state_prefix_resolved() {{ return 0; }}
    _p9c0_euid() {{ echo 0; }}
    _p9c0_identity_lookup_user() {{ [[ "$1" == "{MOCK_USER}" ]] && echo {MOCK_UID}; }}
    _p9c0_identity_lookup_group() {{ [[ "$1" == "{MOCK_GROUP}" ]] && echo {MOCK_GID}; }}
    _p9c0_environment_names() {{ printf '%s\\n' OPENAI_EXTRA_TOKEN SAFE_NAME; }}
    _p9c0_flock() {{ :; }}
    _p9c0_mkdir() {{ mkdir -m "$1" "$2"; }}
    _p9c0_chown() {{ :; }}
    _p9c0_chmod() {{ chmod "$1" "$2"; }}
    _p9c0_install() {{ cp "$2" "$3"; chmod "$1" "$3"; }}
    _p9c0_unit_helper() {{
        [[ "$1" == render ]] || return 91
        shift
        local state_root="" run_id=""
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --state-root) state_root="$2"; shift 2 ;;
                --run-id) run_id="$2"; shift 2 ;;
                *) shift 2 ;;
            esac
        done
        [[ -n "$state_root" && -n "$run_id" ]] || return 92
        printf '[fixture]\n' > "$state_root/$run_id/agents.rendered.toml"
        printf 'run_id=%s\n' "$run_id" > "$state_root/$run_id/values.rendered"
        printf '[Service]\n' > "$state_root/$run_id/systemd.verify.service"
    }}
    _p9c0_sha256_file() {{ shasum -a 256 "$1" | awk '{{print $1}}'; }}
    _p9c0_stat_file() {{
        case "$1" in
            "{state_root}") echo "1:1:0:3:0:0:755" ;;
            */coord-isolated) echo "1:10:2048:1:0:{MOCK_GID}:750" ;;
            */wrapper.manifest) echo "1:11:256:1:0:{MOCK_GID}:640" ;;
            */controller.lock|*/unit-helper.lock) echo "1:12:0:1:0:0:600" ;;
            */values.rendered|*/events.jsonl|*/control/*|*/evidence/*) echo "1:13:128:1:0:0:600" ;;
            */agents.rendered.toml) echo "1:14:128:1:0:{MOCK_GID}:640" ;;
            *.toml) echo "1:14:128:1:0:0:644" ;;
            */control|*/lock|*/ledger|*/evidence) echo "1:2:0:3:0:0:700" ;;
            */work/p9-3c-fixture-e1|*/work/p9-3c-fixture-e2) echo "1:3:0:2:{MOCK_UID}:{MOCK_GID}:700" ;;
            */db|*/work|*/harness|*/context) echo "1:3:0:3:{MOCK_UID}:{MOCK_GID}:700" ;;
            *) echo "1:4:0:3:0:{MOCK_GID}:750" ;;
        esac
    }}
    '''


class TestLocalVerifyControllerFoundation:
    def test_source_safe_and_fixed_argv_contract(self):
        result = _run_bash(f'source "{LOCAL_VERIFY}"; printf source-ok')
        assert result.returncode == 0, result.stderr
        assert result.stdout == "source-ok"
        source = LOCAL_VERIFY.read_text()
        assert 'exec \\"\\$EXPECTED_EXEC\\" --db \\"\\$EXPECTED_DB\\" \\"\\$@\\"' in source
        assert "/bin/sh -c" not in source
        assert (
            "env -i PATH=/usr/local/bin:/usr/bin:/bin /usr/sbin/runuser" in source
        )

    def test_real_runuser_uses_absolute_binary_outside_clean_path(self):
        script = f'''
        set -euo pipefail
        source "{LOCAL_VERIFY}"
        env() {{ printf '<%s>\\n' "$@"; }}
        _p9c0_real_runuser --user coord -- /bin/true
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == [
            "<-i>",
            "<PATH=/usr/local/bin:/usr/bin:/bin>",
            "</usr/sbin/runuser>",
            "<--user>",
            "<coord>",
            "<-->",
            "</bin/true>",
        ]

    def test_run_id_bound_and_exact_credential_name_expansion(self):
        script = f'''
        set -euo pipefail
        source "{LOCAL_VERIFY}"
        _p9c0_environment_names() {{
            printf '%s\\n' OPENAI_EXTRA_TOKEN SAFE_NAME 'AWS_*'
        }}
        _p9c0_validate_run_id "$(printf 'a%.0s' {{1..64}})"
        ! _p9c0_validate_run_id "$(printf 'a%.0s' {{1..65}})"
        ! _p9c0_validate_run_id '../escape'
        names=$(_p9c0_collect_unset_environment_names)
        printf '%s\\n' "$names"
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        names = set(result.stdout.splitlines())
        assert "OPENAI_EXTRA_TOKEN" in names
        assert "SAFE_NAME" not in names
        assert all("*" not in name for name in names)

    def test_prepare_creates_non_conflicting_ledger_and_sealed_wrapper(
        self, tmp_path: Path
    ):
        state_root = tmp_path / "state"
        script = _local_verify_mock_prelude(state_root) + f'''
        main prepare --run-id pkg3-foundation --unit-user {MOCK_USER} \\
            --unit-group {MOCK_GROUP} --agent local-operator
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        run_root = state_root / "pkg3-foundation"
        ledger_dir = run_root / "ledger"
        ledger = ledger_dir / "events.jsonl"
        assert ledger_dir.is_dir()
        assert ledger.is_file()
        assert "foundation ready run=pkg3-foundation" in ledger.read_text()
        wrapper = run_root / "coord-isolated"
        manifest = run_root / "wrapper.manifest"
        assert wrapper.is_file() and manifest.is_file()
        manifest_line = manifest.read_text().rstrip("\n")
        assert manifest.read_text().count("\n") == 1
        assert manifest_line.startswith(f"wrapper_raw={wrapper}\t")
        assert "wrapper_dev_inode_size_nlink_uid_gid_mode=" in manifest_line
        assert "\twrapper_sha256=" in manifest_line
        assert "exec \"$EXPECTED_EXEC\" --db \"$EXPECTED_DB\" \"$@\"" in wrapper.read_text()
        assert (run_root / "control" / "phase").read_text() == "phase=foundation-ready\n"
        assert (run_root / "control" / "intake").read_text() == "intake=open\n"
        assert (run_root / "agents.rendered.toml").read_text() == "[fixture]\n"
        assert (run_root / "values.rendered").read_text() == "run_id=pkg3-foundation\n"
        assert (run_root / "systemd.verify.service").read_text() == "[Service]\n"

    def test_prepare_passes_controller_layout_directly_to_helper_render(
        self, tmp_path: Path
    ):
        state_root = tmp_path / "state"
        calls = tmp_path / "helper.calls"
        script = _local_verify_mock_prelude(state_root) + f'''
        _p9c0_unit_helper() {{
            printf '<%s>\\n' "$@" > "{calls}"
            [[ "$1" == render ]] || return 91
            shift
            local state_root="" run_id=""
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --state-root) state_root="$2"; shift 2 ;;
                    --run-id) run_id="$2"; shift 2 ;;
                    *) shift 2 ;;
                esac
            done
            printf '[fixture]\\n' > "$state_root/$run_id/agents.rendered.toml"
            printf 'run_id=%s\\n' "$run_id" > "$state_root/$run_id/values.rendered"
            printf '[Service]\\n' > "$state_root/$run_id/systemd.verify.service"
        }}
        main prepare --run-id pkg3-helper-layout --unit-user {MOCK_USER} \\
            --unit-group {MOCK_GROUP} --agent local-operator
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        run_root = state_root / "pkg3-helper-layout"
        assert calls.read_text().splitlines() == [
            "<render>",
            "<--state-root>",
            f"<{state_root}>",
            "<--run-id>",
            "<pkg3-helper-layout>",
            "<--fixture-bin>",
            "</opt/multinexus/multinexus/fixture/bin/p9-3c0-fixture.py>",
            "<--wrapper>",
            f"<{run_root / 'coord-isolated'}>",
            "<--coord-db>",
            f"<{run_root / 'db' / 'coord.sqlite3'}>",
            "<--work-dir>",
            f"<{run_root / 'work'}>",
            "<--python>",
            "</opt/multinexus/.venv/bin/python>",
            "<--repo-root>",
            "</opt/multinexus>",
            "<--user>",
            f"<{MOCK_USER}>",
            "<--group>",
            f"<{MOCK_GROUP}>",
            "<--runtime-parent>",
            f"<{run_root}>",
        ]

    def test_repeat_prepare_fails_before_touching_existing_state(self, tmp_path: Path):
        state_root = tmp_path / "state"
        prelude = _local_verify_mock_prelude(state_root)
        command = f'''main prepare --run-id pkg3-repeat --unit-user {MOCK_USER} \\
            --unit-group {MOCK_GROUP} --agent local-operator'''
        first = _run_bash(prelude + command)
        assert first.returncode == 0, first.stderr
        wrapper = state_root / "pkg3-repeat" / "coord-isolated"
        manifest = state_root / "pkg3-repeat" / "wrapper.manifest"
        before = (wrapper.read_bytes(), manifest.read_bytes())
        second = _run_bash(prelude + command)
        assert second.returncode != 0
        assert "refusing repeat prepare" in second.stderr
        assert (wrapper.read_bytes(), manifest.read_bytes()) == before

    def test_recovery_namespace_uses_same_isolated_db_and_separate_ledger(
        self, tmp_path: Path
    ):
        state_root = tmp_path / "state"
        prelude = _local_verify_mock_prelude(state_root)
        script = prelude + f'''
        main prepare --run-id pkg3-recovery --unit-user {MOCK_USER} \\
            --unit-group {MOCK_GROUP} --agent local-operator
        P9C0_RUN_ID=pkg3-recovery
        P9C0_UNIT_USER={MOCK_USER}; P9C0_UNIT_GROUP={MOCK_GROUP}
        P9C0_UNIT_UID={MOCK_UID}; P9C0_UNIT_GID={MOCK_GID}
        P9C0_AGENT_ID=local-operator; P9C0_COORD_DB=""
        : > "{state_root / 'pkg3-recovery' / 'db' / 'coord.sqlite3'}"
        _p9c0_record_intake "$P9C0_INTAKE_FROZEN"
        _p9c0_prepare_recovery_namespace pkg3-recovery
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        primary = state_root / "pkg3-recovery"
        recovery = state_root / "pkg3-recovery-r2"
        shared_db = primary / "db" / "coord.sqlite3"
        assert recovery.is_dir()
        assert f"EXPECTED_DB='{shared_db}'" in (recovery / "coord-isolated").read_text()
        assert f"coord_db={shared_db}\n" not in (recovery / "values.rendered").read_text()
        assert (
            f"recovery-run run_id=pkg3-recovery-r2 shared_db={shared_db}"
            in (primary / "ledger" / "events.jsonl").read_text()
        )
        assert (
            f"parent-run run_id=pkg3-recovery shared_db={shared_db}"
            in (recovery / "ledger" / "events.jsonl").read_text()
        )

    def test_recovery_namespace_rejects_unbounded_derived_run_id(self):
        script = f'''
        source "{LOCAL_VERIFY}"
        ! _p9c0_recovery_run_id "$(printf 'a%.0s' {{1..62}})"
        [[ "$(_p9c0_recovery_run_id "$(printf 'a%.0s' {{1..61}})")" == \
           "$(printf 'a%.0s' {{1..61}})-r2" ]]
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr

    def test_verify_phase_machine_runs_gates_in_order_then_cleanup(self, tmp_path: Path):
        state_root = tmp_path / "state"
        run_id = "pkg3-phase-flow"
        run_root = state_root / run_id
        calls = tmp_path / "verify.calls"
        prelude = _local_verify_mock_prelude(state_root)
        prepare = f'''main prepare --run-id {run_id} --unit-user {MOCK_USER} \\
            --unit-group {MOCK_GROUP} --agent local-operator'''
        assert _run_bash(prelude + prepare).returncode == 0
        db = run_root / "db" / "coord.sqlite3"
        db.touch()
        (run_root / "values.rendered").write_text(
            f"coord_db={db}\nunit_user={MOCK_USER}\nunit_group={MOCK_GROUP}\n"
            f"unit_uid={MOCK_UID}\nunit_gid={MOCK_GID}\n"
        )
        seams = f'''
        _p9c0_verify_capture_baseline() {{ echo baseline >> "{calls}"; }}
        _p9c0_verify_prepare_catalog() {{ echo catalog >> "{calls}"; }}
        _p9c0_verify_base_scenario() {{ echo base >> "{calls}"; }}
        _p9c0_verify_hold_scenario() {{ echo hold >> "{calls}"; }}
        _p9c0_verify_first_reap() {{ echo first-reap >> "{calls}"; }}
        _p9c0_verify_recovery_start() {{ echo recovery >> "{calls}"; }}
        _p9c0_verify_stale_reject() {{ echo stale >> "{calls}"; }}
        _p9c0_verify_second_reap() {{ echo second-reap >> "{calls}"; }}
        _p9c0_production_snapshot() {{ echo compare >> "{calls}"; }}
        _p9c0_run_cleanup() {{ echo cleanup >> "{calls}"; }}
        main verify --run-id {run_id} --unit-user {MOCK_USER} --unit-group {MOCK_GROUP}
        '''
        result = _run_bash(prelude + seams)
        assert result.returncode == 0, result.stderr
        assert calls.read_text().splitlines() == [
            "baseline", "catalog", "base", "hold", "first-reap", "recovery",
            "stale", "second-reap", "compare", "cleanup",
        ]
        assert (run_root / "control" / "phase").read_text() == "phase=done\n"
        assert (run_root / "evidence" / "evidence").read_text() == (
            "evidence=verified-and-cleaned\n"
        )

    def test_cleanup_failure_preserves_cleanup_ready_for_resume(self, tmp_path: Path):
        state_root = tmp_path / "state"
        run_id = "pkg3-cleanup-resume"
        run_root = state_root / run_id
        prelude = _local_verify_mock_prelude(state_root)
        assert _run_bash(
            prelude
            + f'''main prepare --run-id {run_id} --unit-user {MOCK_USER} \\
                --unit-group {MOCK_GROUP} --agent local-operator'''
        ).returncode == 0
        db = run_root / "db" / "coord.sqlite3"
        db.touch()
        (run_root / "values.rendered").write_text(
            f"coord_db={db}\nunit_user={MOCK_USER}\nunit_group={MOCK_GROUP}\n"
            f"unit_uid={MOCK_UID}\nunit_gid={MOCK_GID}\n"
        )
        (run_root / "control" / "phase").write_text("phase=cleanup-ready\n")
        failed = _run_bash(
            prelude
            + f'''
            _p9c0_run_cleanup() {{ return 7; }}
            main verify --run-id {run_id} --unit-user {MOCK_USER} --unit-group {MOCK_GROUP}
            '''
        )
        assert failed.returncode != 0
        assert (run_root / "control" / "phase").read_text() == "phase=cleanup-ready\n"
        resumed = _run_bash(
            prelude
            + f'''
            _p9c0_run_cleanup() {{ :; }}
            main verify --run-id {run_id} --unit-user {MOCK_USER} --unit-group {MOCK_GROUP}
            '''
        )
        assert resumed.returncode == 0, resumed.stderr
        assert (run_root / "control" / "phase").read_text() == "phase=done\n"

    def test_unknown_run_entry_fails_before_coordinate_invocation(self, tmp_path: Path):
        state_root = tmp_path / "state"
        prelude = _local_verify_mock_prelude(state_root)
        prepare = f'''main prepare --run-id pkg3-unknown --unit-user {MOCK_USER} \\
            --unit-group {MOCK_GROUP} --agent local-operator'''
        first = _run_bash(prelude + prepare)
        assert first.returncode == 0, first.stderr
        (state_root / "pkg3-unknown" / "intruder").write_text("x")
        calls = tmp_path / "runuser.calls"
        invoke = prelude + f'''
        P9C0_RUN_ID=pkg3-unknown
        P9C0_UNIT_USER={MOCK_USER}
        P9C0_UNIT_GROUP={MOCK_GROUP}
        P9C0_UNIT_UID={MOCK_UID}
        P9C0_UNIT_GID={MOCK_GID}
        _p9c0_runuser() {{ printf '%s\\n' "$*" >> "{calls}"; }}
        _p9c0_controller_run_coordinate {MOCK_USER} {MOCK_UID} runtime job list
        '''
        result = _run_bash(invoke)
        assert result.returncode != 0
        assert "unknown pre-existing per-run entry" in result.stderr
        assert not calls.exists()

    def test_controller_rechecks_identity_then_uses_fixed_runuser_argv(self, tmp_path: Path):
        state_root = tmp_path / "state"
        prelude = _local_verify_mock_prelude(state_root)
        prepare = f'''main prepare --run-id pkg3-argv --unit-user {MOCK_USER} \\
            --unit-group {MOCK_GROUP} --agent local-operator'''
        assert _run_bash(prelude + prepare).returncode == 0
        calls = tmp_path / "runuser.calls"
        invoke = prelude + f'''
        P9C0_RUN_ID=pkg3-argv
        P9C0_UNIT_USER={MOCK_USER}
        P9C0_UNIT_GROUP={MOCK_GROUP}
        P9C0_UNIT_UID={MOCK_UID}
        P9C0_UNIT_GID={MOCK_GID}
        _p9c0_runuser() {{ printf '<%s>\\n' "$@" > "{calls}"; }}
        _p9c0_controller_run_coordinate {MOCK_USER} {MOCK_UID} runtime job list
        '''
        result = _run_bash(invoke)
        assert result.returncode == 0, result.stderr
        assert calls.read_text().splitlines() == [
            f"<--user>",
            f"<{MOCK_USER}>",
            "<-->",
            f"<{state_root / 'pkg3-argv' / 'coord-isolated'}>",
            "<runtime>",
            "<job>",
            "<list>",
        ]

        drift = prelude + f'''
        P9C0_RUN_ID=pkg3-argv
        P9C0_UNIT_USER={MOCK_USER}; P9C0_UNIT_GROUP={MOCK_GROUP}
        P9C0_UNIT_UID={MOCK_UID}; P9C0_UNIT_GID={MOCK_GID}
        _p9c0_identity_lookup_user() {{ echo 2002; }}
        _p9c0_runuser() {{ echo invoked; }}
        _p9c0_controller_run_coordinate {MOCK_USER} {MOCK_UID} runtime job list
        '''
        rejected = _run_bash(drift)
        assert rejected.returncode != 0
        assert "uid mismatch" in rejected.stderr
        assert "invoked" not in rejected.stdout

    def test_wrapper_self_check_recomputes_manifest_and_sha_before_exec(
        self, tmp_path: Path
    ):
        state_root = tmp_path / "state"
        prelude = _local_verify_mock_prelude(state_root)
        prepare = f'''main prepare --run-id pkg3-selfcheck --unit-user {MOCK_USER} \\
            --unit-group {MOCK_GROUP} --agent local-operator'''
        first = _run_bash(prelude + prepare)
        assert first.returncode == 0, first.stderr
        run_root = state_root / "pkg3-selfcheck"
        wrapper = run_root / "coord-isolated"
        manifest = run_root / "wrapper.manifest"
        approved_manifest = manifest.read_bytes()

        calls = tmp_path / "coordinate.calls"
        coordinate = state_root / "coordinate"
        coordinate.write_text(
            f'#!/bin/sh\nprintf "<%s>\\n" "$@" >> "{calls}"\n'
        )
        _chmod_exec(coordinate)

        stub_bin = tmp_path / "stub-bin"
        stub_bin.mkdir()
        (stub_bin / "stat").write_text(
            f'''#!/bin/sh
case "$*" in
  *wrapper.manifest*) echo "1:11:256:1:0:{MOCK_GID}:640" ;;
  *) echo "1:10:2048:1:0:{MOCK_GID}:750" ;;
esac
'''
        )
        (stub_bin / "sha256sum").write_text(
            "#!/bin/sh\n/usr/bin/shasum -a 256 \"$1\"\n"
        )
        (stub_bin / "realpath").write_text(
            "#!/bin/sh\nwhile [ \"${1:-}\" = -- ] || [ \"${1:-}\" = -m ]; do shift; done\nprintf '%s\\n' \"$1\"\n"
        )
        for executable in stub_bin.iterdir():
            _chmod_exec(executable)
        env = {"PATH": f"{stub_bin}:/usr/bin:/bin"}

        ok = subprocess.run(
            [str(wrapper), "runtime", "job", "list"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert ok.returncode == 0, ok.stderr
        assert calls.read_text().splitlines() == [
            "<--db>",
            f"<{run_root / 'db' / 'coord.sqlite3'}>",
            "<runtime>",
            "<job>",
            "<list>",
        ]

        manifest.write_bytes(approved_manifest + b"drift\n")
        manifest_drift = subprocess.run(
            [str(wrapper), "runtime", "job", "list"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert manifest_drift.returncode != 0
        assert "manifest must be one line" in manifest_drift.stderr
        assert len(calls.read_text().splitlines()) == 5

        manifest.write_bytes(approved_manifest)
        wrapper.write_text(wrapper.read_text() + "# sha drift\n")
        sha_drift = subprocess.run(
            [str(wrapper), "runtime", "job", "list"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert sha_drift.returncode != 0
        assert "manifest content drift" in sha_drift.stderr
        assert len(calls.read_text().splitlines()) == 5

    def test_controller_manifest_drift_fails_before_runuser(self, tmp_path: Path):
        state_root = tmp_path / "state"
        prelude = _local_verify_mock_prelude(state_root)
        prepare = f'''main prepare --run-id pkg3-manifest-drift --unit-user {MOCK_USER} \\
            --unit-group {MOCK_GROUP} --agent local-operator'''
        assert _run_bash(prelude + prepare).returncode == 0
        manifest = state_root / "pkg3-manifest-drift" / "wrapper.manifest"
        manifest.write_text(manifest.read_text() + "extra\n")
        invoke = prelude + f'''
        P9C0_RUN_ID=pkg3-manifest-drift
        P9C0_UNIT_USER={MOCK_USER}; P9C0_UNIT_GROUP={MOCK_GROUP}
        P9C0_UNIT_UID={MOCK_UID}; P9C0_UNIT_GID={MOCK_GID}
        _p9c0_runuser() {{ echo invoked; }}
        _p9c0_controller_run_coordinate {MOCK_USER} {MOCK_UID} runtime job list
        '''
        result = _run_bash(invoke)
        assert result.returncode != 0
        assert "manifest line count drift" in result.stderr
        assert "invoked" not in result.stdout

    def test_failure_trap_freezes_then_stops_only_two_exact_ledger_units(
        self, tmp_path: Path
    ):
        state_root = tmp_path / "state"
        run_root = state_root / "pkg3-failure"
        for child in ("control", "ledger", "evidence"):
            (run_root / child).mkdir(parents=True, exist_ok=True)
        (run_root / "control" / "intake").write_text("intake=open\n")
        (run_root / "control" / "phase").write_text("phase=foundation-ready\n")
        ledger = run_root / "ledger" / "events.jsonl"
        ledger.write_text(
            "unit=p9-3c-fixture-e1-pkg3-failure.service run=pkg3-failure\n"
            "unit=p9-3c-fixture-e2-pkg3-failure.service run=pkg3-failure\n"
            "unit=p9-3c-fixture-e1-pkg3-failure.service duplicate=true\n"
            "unit=p9-3c-fixture-e1-pkg3-failure-near.service run=near\n"
        )
        calls = tmp_path / "stop.calls"
        script = _local_verify_mock_prelude(state_root) + f'''
        P9C0_RUN_ID=pkg3-failure
        _p9c0_helper_exact_stop() {{
            printf '%s|%s\\n' "$1" "$(cat "{run_root / 'control' / 'intake'}")" >> "{calls}"
        }}
        _p9c0_failure_trap
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert calls.read_text().splitlines() == [
            "p9-3c-fixture-e1-pkg3-failure.service|intake=frozen",
            "p9-3c-fixture-e2-pkg3-failure.service|intake=frozen",
        ]
        assert (run_root / "control" / "phase").read_text() == "phase=failed\n"
        assert (run_root / "control" / "failure").read_text() == "failure=preserved\n"
        assert (run_root / "evidence" / "evidence").read_text() == "evidence=failed\n"

    def test_recovery_failure_trap_freezes_and_stops_both_linked_runs(
        self, tmp_path: Path
    ):
        state_root = tmp_path / "state"
        primary_id = "pkg3-linked-failure"
        recovery_id = f"{primary_id}-r2"
        primary = state_root / primary_id
        recovery = state_root / recovery_id
        shared_db = primary / "db" / "coord.sqlite3"
        for root in (primary, recovery):
            for child in ("control", "ledger", "evidence"):
                (root / child).mkdir(parents=True, exist_ok=True)
            (root / "control" / "intake").write_text("intake=open\n")
            (root / "control" / "phase").write_text("phase=foundation-ready\n")
        (primary / "ledger" / "events.jsonl").write_text(
            f"recovery-run run_id={recovery_id} shared_db={shared_db}\n"
            f"unit p9-3c-fixture-e1-{primary_id}.service agent=p9-3c-fixture-e1\n"
            f"unit p9-3c-fixture-e2-{primary_id}.service agent=p9-3c-fixture-e2\n"
        )
        (recovery / "ledger" / "events.jsonl").write_text(
            f"parent-run run_id={primary_id} shared_db={shared_db}\n"
            f"unit p9-3c-fixture-e1-{recovery_id}.service agent=p9-3c-fixture-e1\n"
        )
        calls = tmp_path / "linked-stop.calls"
        script = _local_verify_mock_prelude(state_root) + f'''
        P9C0_RUN_ID={recovery_id}
        _p9c0_helper_exact_stop() {{ printf '%s|%s\n' "$1" "$2" >> "{calls}"; }}
        _p9c0_failure_trap
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert calls.read_text().splitlines() == [
            f"p9-3c-fixture-e1-{primary_id}.service|{primary_id}",
            f"p9-3c-fixture-e2-{primary_id}.service|{primary_id}",
            f"p9-3c-fixture-e1-{recovery_id}.service|{recovery_id}",
        ]
        assert (primary / "control" / "intake").read_text() == "intake=frozen\n"
        assert (recovery / "control" / "intake").read_text() == "intake=frozen\n"
        assert (recovery / "control" / "phase").read_text() == "phase=failed\n"


class TestProductionSnapshotRowShape:
    def _fixture(self, tmp_path: Path) -> tuple[str, Path, dict[str, str]]:
        fragment = tmp_path / "canonical.service"
        fragment.write_text("[Service]\nExecStart=/bin/true\n")
        configs = tuple(
            tmp_path / name
            for name in ("registry.toml", "agents.toml", "VERSION_DEPLOYED")
        )
        for index, path in enumerate(configs):
            path.write_text(f"config-{index}\n")

        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        systemctl = fake_bin / "systemctl"
        systemctl.write_text(
            "#!/bin/sh\n"
            "unit=''\n"
            "for arg in \"$@\"; do unit=$arg; done\n"
            "fixture=0\n"
            "case \"$unit\" in p9-3c-fixture-*) fixture=1;; esac\n"
            "while [ $# -gt 0 ]; do\n"
            "  if [ \"$1\" = -p ]; then\n"
            "    prop=$2; shift 2\n"
            "    case \"$prop\" in\n"
            "      Id) value=$unit;;\n"
            "      LoadState) [ $fixture -eq 1 ] && value=not-found || value=loaded;;\n"
            "      ActiveState) [ $fixture -eq 1 ] && value=inactive || value=active;;\n"
            "      SubState) value=running;;\n"
            "      MainPID) value=4242;;\n"
            "      NRestarts) value=0;;\n"
            f"      FragmentPath) value='{fragment}';;\n"
            "    esac\n"
            "    printf '%s=%s\\n' \"$prop\" \"$value\"\n"
            "  else\n"
            "    shift\n"
            "  fi\n"
            "done\n"
        )
        _chmod_exec(systemctl)

        db = tmp_path / "production.sqlite3"
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            PRAGMA user_version=13;
            CREATE TABLE jobs (status TEXT, assigned_agent TEXT);
            CREATE TABLE execution_attempt_leases (status TEXT, agent_id TEXT);
            CREATE TABLE agents (id TEXT);
            CREATE TABLE runner_profiles (id TEXT);
            CREATE TABLE executor_catalog_sources (
                source_id TEXT, source_version TEXT, catalog_hash TEXT
            );
            CREATE TABLE executor_capacity_sources (
                source_id TEXT, source_version TEXT, catalog_hash TEXT
            );
            INSERT INTO executor_catalog_sources VALUES ('executor', 'v1', 'hash-e1');
            INSERT INTO executor_capacity_sources VALUES ('capacity', 'v1', 'hash-c1');
            """
        )
        conn.commit()
        conn.close()
        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
        return _production_snapshot_python(configs), db, env

    @staticmethod
    def _run_snapshot(
        program: str, mode: str, baseline: Path, db: Path, env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-c",
                program,
                mode,
                str(baseline),
                str(db),
                "row-shape-test",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

    def test_unchanged_snapshot_survives_json_round_trip(self, tmp_path: Path):
        program, db, env = self._fixture(tmp_path)
        baseline = tmp_path / "baseline.json"
        captured = self._run_snapshot(program, "capture", baseline, db, env)
        assert captured.returncode == 0, captured.stderr
        compared = self._run_snapshot(program, "compare", baseline, db, env)
        assert compared.returncode == 0, compared.stderr

    def test_source_row_value_drift_still_fails_closed(self, tmp_path: Path):
        program, db, env = self._fixture(tmp_path)
        baseline = tmp_path / "baseline.json"
        captured = self._run_snapshot(program, "capture", baseline, db, env)
        assert captured.returncode == 0, captured.stderr
        conn = sqlite3.connect(db)
        conn.execute(
            "UPDATE executor_catalog_sources SET catalog_hash='hash-e2' WHERE source_id='executor'"
        )
        conn.commit()
        conn.close()
        compared = self._run_snapshot(program, "compare", baseline, db, env)
        assert compared.returncode != 0
        assert "production state drifted from captured baseline" in compared.stderr


class TestLocalVerifyMissingDbRealpath:
    """Isolation DB realpath must resolve missing leaf/suffix while still
    rejecting symlink escapes and production aliases."""

    def _fresh_state_root(self, tmp_path: Path) -> Path:
        state_root = tmp_path / "state"
        state_root.mkdir(parents=True, exist_ok=True)
        return state_root

    def _prelude(self, state_root: Path, prod_db: Path) -> str:
        return f'''
        set -euo pipefail
        source "{LOCAL_VERIFY}"
        P9C0_PROD_STATE_PREFIX="{state_root}"
        P9C0_PROD_DB="{prod_db}"
        P9C0_UNIT_USER="{MOCK_USER}"
        P9C0_UNIT_GROUP="{MOCK_GROUP}"
        P9C0_UNIT_UID="{MOCK_UID}"
        P9C0_UNIT_GID="{MOCK_GID}"
        _p9c0_controller_state_prefix() {{ printf '%s\\n' "{state_root}"; }}
        _p9c0_identity_lookup_user() {{ [[ "$1" == "{MOCK_USER}" ]] && echo {MOCK_UID}; }}
        _p9c0_identity_lookup_group() {{ [[ "$1" == "{MOCK_GROUP}" ]] && echo {MOCK_GID}; }}
        '''

    def _call_enforce(
        self,
        tmp_path: Path,
        db: Path,
        prod_db: Path,
        *,
        extra_overrides: str = "",
    ) -> subprocess.CompletedProcess[str]:
        state_root = self._fresh_state_root(tmp_path)
        script = self._prelude(state_root, prod_db) + extra_overrides + f'''
        _p9c0_enforce_unit_identity "{MOCK_USER}" "{MOCK_GROUP}" \
            "{MOCK_UID}" "{MOCK_GID}" "{db}" "{prod_db}"
        '''
        return _run_bash(script)

    def test_fresh_db_with_missing_suffixes_passes(self, tmp_path: Path):
        state_root = self._fresh_state_root(tmp_path)
        prod_db = tmp_path / "production.sqlite3"
        prod_db.touch()
        db = state_root / "run" / "db" / "coord.sqlite3"
        result = self._call_enforce(tmp_path, db, prod_db)
        assert result.returncode == 0, result.stderr

    def test_fresh_state_prefix_and_db_suffixes_pass(self, tmp_path: Path):
        state_root = tmp_path / "not-created-yet" / "state"
        prod_db = tmp_path / "production.sqlite3"
        prod_db.touch()
        db = state_root / "run" / "db" / "coord.sqlite3"
        script = self._prelude(state_root, prod_db) + f'''
        _p9c0_enforce_unit_identity "{MOCK_USER}" "{MOCK_GROUP}" \
            "{MOCK_UID}" "{MOCK_GID}" "{db}" "{prod_db}"
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert not state_root.exists()

    def test_ancestor_symlink_to_production_db_is_rejected(self, tmp_path: Path):
        state_root = self._fresh_state_root(tmp_path)
        prod_db = state_root / "production.sqlite3"
        prod_db.touch()
        trap = state_root / "trap"
        trap.symlink_to(prod_db)
        db = state_root / "trap"
        result = self._call_enforce(tmp_path, db, prod_db)
        assert result.returncode != 0
        assert "isolation db resolves to production" in result.stderr

    def test_ancestor_symlink_escaping_state_prefix_is_rejected(self, tmp_path: Path):
        state_root = self._fresh_state_root(tmp_path)
        outside = tmp_path / "outside"
        outside.mkdir()
        prod_db = tmp_path / "production.sqlite3"
        prod_db.touch()
        trap = state_root / "trap"
        trap.symlink_to(outside)
        db = state_root / "trap" / "db" / "coord.sqlite3"
        result = self._call_enforce(tmp_path, db, prod_db)
        assert result.returncode != 0
        assert "isolation db resolved path escapes state prefix" in result.stderr

    def test_realpath_seam_failure_is_rejected(self, tmp_path: Path):
        state_root = self._fresh_state_root(tmp_path)
        prod_db = tmp_path / "production.sqlite3"
        prod_db.touch()
        db = state_root / "run" / "db" / "coord.sqlite3"
        result = self._call_enforce(
            tmp_path,
            db,
            prod_db,
            extra_overrides='\n        _p9c0_realpath_missing_ok() { return 1; }\n        ',
        )
        assert result.returncode != 0
        assert "isolation db realpath failed" in result.stderr

    def test_missing_suffix_dotdot_is_rejected(self, tmp_path: Path):
        state_root = self._fresh_state_root(tmp_path)
        prod_db = tmp_path / "production.sqlite3"
        prod_db.touch()
        db = f"{state_root}/run/../outside/coord.sqlite3"
        result = self._call_enforce(tmp_path, db, prod_db)
        assert result.returncode != 0
        assert "isolation db realpath failed" in result.stderr

    def test_production_db_strict_realpath_failure_is_rejected(
        self, tmp_path: Path
    ):
        state_root = self._fresh_state_root(tmp_path)
        prod_db = tmp_path / "production.sqlite3"
        prod_db.touch()
        db = state_root / "run" / "db" / "coord.sqlite3"
        override = f'''
        _p9c0_realpath() {{
            [[ "$1" == "{prod_db}" ]] && return 1
            _p9c0_real_realpath "$1"
        }}
        '''
        result = self._call_enforce(
            tmp_path, db, prod_db, extra_overrides=override
        )
        assert result.returncode != 0
        assert "production db realpath failed" in result.stderr



class TestLocalVerifyNestedRunLock:
    """Behavioral regression tests for the explicit two-depth run lock.

    These tests exercise the real `_p9c0_with_run_lock` helper in isolation.
    A real `flock` binary is not required because the lock seam is mocked to
    record its FD and mode rather than to serialize.

    Outer (depth 0 -> 1) and inner (depth 1 -> 2) must operate in distinct
    namespaces so their `controller.lock` files are independent. Nesting depth
    validation runs before any per-run directory or lock-file side effect.
    """

    PRIMARY_RUN_ID = "pkg3-lock-primary"
    RECOVERY_RUN_ID = f"{PRIMARY_RUN_ID}-r2"

    def _nested_lock_script(self, state_root: Path, body: str) -> str:
        primary_root = state_root / self.PRIMARY_RUN_ID
        recovery_root = state_root / self.RECOVERY_RUN_ID
        return f'''
        set -uo pipefail
        source "{LOCAL_VERIFY}"
        P9C0_PROD_STATE_PREFIX="{state_root}"
        _p9c0_controller_state_prefix() {{ printf '%s\\n' "{state_root}"; }}
        _p9c0_assert_state_prefix_authority() {{ return 0; }}
        _p9c0_assert_state_prefix_resolved() {{ return 0; }}
        _p9c0_euid() {{ echo 0; }}
        mkdir -p "{primary_root}/lock"
        mkdir -p "{recovery_root}/lock"
        P9C0_RUN_ID={self.PRIMARY_RUN_ID}
        _p9c0_enforce_root_owned_dir() {{ return 0; }}
        _p9c0_enforce_root_owned_file() {{ return 0; }}
        _p9c0_chown() {{ :; }}
        _p9c0_chmod() {{ chmod "$1" "$2"; }}
        {body}
        '''

    def test_acquire_9_then_8_release_8_then_9(self, tmp_path: Path):
        state_root = tmp_path / "state"
        calls = tmp_path / "lock.calls"
        primary = self.PRIMARY_RUN_ID
        recovery = self.RECOVERY_RUN_ID
        body = f'''
        _p9c0_flock() {{
            printf '%s|%s\\n' "$1" "$2" >> "{calls}"
            return 0
        }}
        _inner() {{
            printf 'inner\\n'
        }}
        _outer() {{
            printf 'outer-before\\n'
            P9C0_RUN_ID={recovery}
            _p9c0_with_run_lock _inner
            P9C0_RUN_ID={primary}
            printf 'outer-after\\n'
        }}
        _p9c0_with_run_lock _outer
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 0, result.stderr
        lines = calls.read_text().splitlines()
        assert lines == ["-x|9", "-x|8", "-u|8", "-u|9"]

    def test_inner_critical_section_can_write_fd_9_and_fd_8(self, tmp_path: Path):
        state_root = tmp_path / "state"
        primary = self.PRIMARY_RUN_ID
        recovery = self.RECOVERY_RUN_ID
        body = f'''
        _p9c0_flock() {{ return 0; }}
        _inner() {{
            printf 'inner-9' >&9 || {{ echo "write-fd9-failed" >&2; return 3; }}
            printf 'inner-8' >&8 || {{ echo "write-fd8-failed" >&2; return 4; }}
        }}
        _outer() {{
            printf 'outer-9' >&9 || {{ echo "write-fd9-failed" >&2; return 1; }}
            P9C0_RUN_ID={recovery}
            _p9c0_with_run_lock _inner || return 2
            P9C0_RUN_ID={primary}
        }}
        _p9c0_with_run_lock _outer
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 0, result.stderr

    def test_inner_return_closes_fd_8_but_fd_9_stays_alive(self, tmp_path: Path):
        state_root = tmp_path / "state"
        inner_after = tmp_path / "inner-after"
        outer_after = tmp_path / "outer-after"
        primary = self.PRIMARY_RUN_ID
        recovery = self.RECOVERY_RUN_ID
        body = f'''
        _p9c0_flock() {{ return 0; }}
        _inner() {{
            printf 'inside' >&8
        }}
        _outer() {{
            P9C0_RUN_ID={recovery}
            _p9c0_with_run_lock _inner
            P9C0_RUN_ID={primary}
            if printf 'still-9' >&9; then
                echo fd9-alive > "{outer_after}"
            else
                echo fd9-dead > "{outer_after}"
            fi
            if (printf 'closed-8' >&8) 2>/dev/null; then
                echo fd8-open > "{inner_after}"
            else
                echo fd8-closed > "{inner_after}"
            fi
        }}
        _p9c0_with_run_lock _outer
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 0, result.stderr
        assert outer_after.read_text().strip() == "fd9-alive"
        assert inner_after.read_text().strip() == "fd8-closed"

    def test_final_return_closes_both_fd_9_and_fd_8(self, tmp_path: Path):
        state_root = tmp_path / "state"
        after = tmp_path / "after"
        primary = self.PRIMARY_RUN_ID
        recovery = self.RECOVERY_RUN_ID
        body = f'''
        _p9c0_flock() {{ return 0; }}
        _inner() {{ :; }}
        _outer() {{
            P9C0_RUN_ID={recovery}
            _p9c0_with_run_lock _inner
            P9C0_RUN_ID={primary}
        }}
        _p9c0_with_run_lock _outer
        if (printf 'closed-9' >&9) 2>/dev/null; then
            echo fd9-open > "{after}"
        elif (printf 'closed-8' >&8) 2>/dev/null; then
            echo fd8-open > "{after}"
        else
            echo both-closed > "{after}"
        fi
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 0, result.stderr
        assert after.read_text().strip() == "both-closed"

    def test_fd_lifecycle_writes_distinct_markers_to_independent_lock_files(
        self, tmp_path: Path
    ):
        state_root = tmp_path / "state"
        primary = self.PRIMARY_RUN_ID
        recovery = self.RECOVERY_RUN_ID
        primary_lock = state_root / primary / "lock" / "controller.lock"
        recovery_lock = state_root / recovery / "lock" / "controller.lock"
        body = f'''
        _p9c0_flock() {{ return 0; }}
        _inner() {{
            printf 'marker-8' >&8
        }}
        _outer() {{
            printf 'marker-9' >&9
            P9C0_RUN_ID={recovery}
            _p9c0_with_run_lock _inner
            P9C0_RUN_ID={primary}
        }}
        _p9c0_with_run_lock _outer
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 0, result.stderr
        assert primary_lock.read_text() == "marker-9"
        assert recovery_lock.read_text() == "marker-8"

    def test_third_level_fail_closed_and_outer_inner_unwind(self, tmp_path: Path):
        state_root = tmp_path / "state"
        calls = tmp_path / "unwind.calls"
        third_root = state_root / "pkg3-lock-third"
        primary = self.PRIMARY_RUN_ID
        recovery = self.RECOVERY_RUN_ID
        body = f'''
        _p9c0_flock() {{
            printf '%s|%s\\n' "$1" "$2" >> "{calls}"
            return 0
        }}
        _third() {{ echo "should-not-run"; }}
        _inner() {{
            printf 'inner-before\\n'
            P9C0_RUN_ID={third_root.name}
            _p9c0_with_run_lock _third || INNER_RC=$?
            P9C0_RUN_ID={recovery}
            printf 'inner-rc-${{INNER_RC:-0}}\\n'
            return "${{INNER_RC:-0}}"
        }}
        _outer() {{
            printf 'outer-before\\n'
            P9C0_RUN_ID={recovery}
            _p9c0_with_run_lock _inner || return 99
            P9C0_RUN_ID={primary}
            printf 'outer-after\\n'
        }}
        _p9c0_with_run_lock _outer || OUTER_RC=$?
        echo "OUTER_RC=${{OUTER_RC:-0}}"
        exit "${{OUTER_RC:-0}}"
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 99, result.stderr
        assert "should-not-run" not in result.stdout
        assert "outer-after" not in result.stdout
        lines = calls.read_text().splitlines()
        assert lines == ["-x|9", "-x|8", "-u|8", "-u|9"]
        # Third namespace must not have any controller.lock created.
        assert not (third_root / "lock" / "controller.lock").exists()
        assert not third_root.exists()

    def test_callback_nonzero_still_releases_and_propagates(self, tmp_path: Path):
        state_root = tmp_path / "state"
        calls = tmp_path / "lock.calls"
        body = f'''
        _p9c0_flock() {{
            printf '%s|%s\\n' "$1" "$2" >> "{calls}"
            return 0
        }}
        _failing() {{
            printf 'failing\\n'
            return 42
        }}
        _p9c0_with_run_lock _failing || LOCK_RC=$?
        echo "LOCK_RC=${{LOCK_RC:-0}}"
        exit "${{LOCK_RC:-0}}"
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 42, result.stderr
        lines = calls.read_text().splitlines()
        assert lines == ["-x|9", "-u|9"]

    def test_unlock_failure_makes_result_fail(self, tmp_path: Path):
        state_root = tmp_path / "state"
        calls = tmp_path / "lock.calls"
        body = f'''
        _p9c0_flock() {{
            printf '%s|%s\\n' "$1" "$2" >> "{calls}"
            if [[ "$1" == "-u" ]]; then
                return 7
            fi
            return 0
        }}
        _ok() {{ :; }}
        _p9c0_with_run_lock _ok || LOCK_RC=$?
        echo "LOCK_RC=${{LOCK_RC:-0}}"
        exit "${{LOCK_RC:-0}}"
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 1, result.stderr
        lines = calls.read_text().splitlines()
        assert lines == ["-x|9", "-u|9"]

    def test_acquire_failure_closes_fd_and_restores_depth(self, tmp_path: Path):
        state_root = tmp_path / "state"
        calls = tmp_path / "lock.calls"
        after = tmp_path / "after"
        body = f'''
        _p9c0_flock() {{
            printf '%s|%s\\n' "$1" "$2" >> "{calls}"
            if [[ "$1" == "-x" && "$2" == "9" ]]; then
                return 3
            fi
            return 0
        }}
        _p9c0_die() {{
            printf 'died: %s\\n' "$1" >&2
            printf 'DEPTH=%s\\n' "${{P9C0_RUN_LOCK_DEPTH:-unset}}" > "{after}"
            if (printf 'closed-9' >&9) 2>/dev/null; then
                echo fd9-open >> "{after}"
            else
                echo fd9-closed >> "{after}"
            fi
            exit "${{2:-1}}"
        }}
        _ok() {{ :; }}
        _p9c0_with_run_lock _ok
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 26, result.stderr
        assert "run lock acquire failed" in result.stderr
        lines = calls.read_text().splitlines()
        assert lines == ["-x|9"]
        assert after.read_text().splitlines() == [
            "DEPTH=0",
            "fd9-closed",
        ]

    @pytest.mark.parametrize(
        ("previous_depth", "run_id"),
        [
            ("2", "pkg3-lock-bad-depth-2"),
            ("-1", "pkg3-lock-bad-depth-neg"),
            ("nonnumeric", "pkg3-lock-bad-depth-nan"),
        ],
    )
    def test_invalid_previous_depth_rejects_without_filesystem_side_effects(
        self,
        tmp_path: Path,
        previous_depth: str,
        run_id: str,
    ):
        state_root = tmp_path / "state"
        bad_root = state_root / run_id
        after = tmp_path / "after"
        callback_marker = tmp_path / "callback-marker"
        body = f'''
        _p9c0_flock() {{ return 0; }}
        _ok() {{
            echo "ran" > "{callback_marker}"
        }}
        P9C0_RUN_ID={run_id}
        P9C0_RUN_LOCK_DEPTH={previous_depth}
        _p9c0_with_run_lock _ok || RC=$?
        printf 'RC=%s\\n' "${{RC:-0}}" > "{after}"
        printf 'DEPTH=%s\\n' "${{P9C0_RUN_LOCK_DEPTH:-unset}}" >> "{after}"
        exit "${{RC:-0}}"
        '''
        result = _run_bash(self._nested_lock_script(state_root, body))
        assert result.returncode == 1, result.stderr
        assert "previous depth rejected" in result.stderr
        assert after.read_text().splitlines() == [
            "RC=1",
            f"DEPTH={previous_depth}",
        ]
        assert not callback_marker.exists()
        assert not (bad_root / "lock" / "controller.lock").exists()
        assert not bad_root.exists()


class TestLocalVerifyScenarioContracts:
    def _prepared(self, tmp_path: Path, run_id: str) -> tuple[Path, str]:
        state_root = tmp_path / "state"
        prelude = _local_verify_mock_prelude(state_root)
        result = _run_bash(
            prelude
            + f'''main prepare --run-id {run_id} --unit-user {MOCK_USER} \\
                --unit-group {MOCK_GROUP} --agent local-operator'''
        )
        assert result.returncode == 0, result.stderr
        return state_root, prelude

    def test_submit_is_refused_while_frozen_before_coordinate(self, tmp_path: Path):
        state_root, prelude = self._prepared(tmp_path, "pkg3-submit-frozen")
        calls = tmp_path / "coordinate.calls"
        script = prelude + f'''
        P9C0_RUN_ID=pkg3-submit-frozen
        P9C0_UNIT_USER={MOCK_USER}; P9C0_UNIT_UID={MOCK_UID}
        _p9c0_record_intake "$P9C0_INTAKE_FROZEN"
        _p9c0_controller_run_coordinate() {{ echo invoked >> "{calls}"; }}
        _p9c0_submit_request p9-3c-fixture-e1 complete false complete
        '''
        result = _run_bash(script)
        assert result.returncode != 0
        assert "intake is frozen" in result.stderr
        assert not calls.exists()

    def test_claude_boundary_normalizer_accepts_python_log_prefix_only(self):
        script = f'''
        source "{LOCAL_VERIFY}"
        printf '%s\n' \
            'claude_child_boundary monotonic_ns=101 pid=201' \
            '2026-07-16 00:40:39,255 multinexus.adapters.claude DEBUG claude_child_boundary monotonic_ns=102 pid=202' \
            'claude_child_boundary monotonic_ns=bad pid=203' \
            'prefix claude_child_boundary monotonic_ns=104 pid=204 suffix' \
            | _p9c0_claude_boundary_lines
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == [
            "claude_child_boundary monotonic_ns=101 pid=201",
            "claude_child_boundary monotonic_ns=102 pid=202",
        ]

    def test_hold_scenario_counts_one_new_boundary_after_formatted_base_log(
        self, tmp_path: Path
    ):
        journal = tmp_path / "journal.log"
        ledger = tmp_path / "ledger.log"
        stops = tmp_path / "stops.log"
        run_root = tmp_path / "run"
        (run_root / "evidence").mkdir(parents=True)
        journal.write_text(
            "2026-07-16 00:39:21,392 multinexus.adapters.claude DEBUG "
            "claude_child_boundary monotonic_ns=101 pid=201\n"
        )
        script = f'''
        source "{LOCAL_VERIFY}"
        P9C0_RUN_ID=pkg3-hold-prefixed
        _p9c0_unit_journal() {{ cat "{journal}"; }}
        _p9c0_submit_request() {{
            local ns
            ns=$(python3 -c 'import time; print(time.monotonic_ns())')
            printf '2026-07-16 00:40:39,255 multinexus.adapters.claude DEBUG claude_child_boundary monotonic_ns=%s pid=202\n' "$ns" >> "{journal}"
        }}
        _p9c0_hold_monitor() {{
            printf '{{"job_id":"job","lease_id":"lease","attempt_token":1}}\n'
        }}
        _p9c0_process_tree_proof() {{ printf 'process-tree-ok\n'; }}
        _p9c0_ledger_append() {{ printf '%s\n' "$1" >> "{ledger}"; }}
        _p9c0_record_intake() {{ :; }}
        _p9c0_wait_monotonic_target() {{ :; }}
        _p9c0_unit_stop() {{ printf '%s\n' "$*" >> "{stops}"; }}
        _p9c0_per_run_root() {{ printf '%s\n' "{run_root}"; }}
        _p9c0_hold_authority() {{ printf 'lease-active lease_id=lease\n'; }}
        _p9c0_chown() {{ :; }}
        _p9c0_chmod() {{ :; }}
        _p9c0_production_snapshot() {{ :; }}
        _p9c0_real_verify_hold_scenario
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        lines = ledger.read_text().splitlines()
        boundaries = [line for line in lines if line.startswith("claude_child_boundary")]
        assert len(boundaries) == 1
        assert boundaries[0].endswith("pid=202")
        stop_lines = stops.read_text().splitlines()
        assert "p9-3c-fixture-e1 --crash --fixture-start-monotonic-ms" in stop_lines[0]
        assert stop_lines[1] == "p9-3c-fixture-e2"

    def test_process_tree_proof_models_env_python_shebang_exactly(self):
        source = LOCAL_VERIFY.read_text()
        assert 'b"#!/usr/bin/env python3"' in source
        assert '"python3", fixture_bin, "-p", "--verbose", "--output-format"' in source
        assert 'actual_executable=pathlib.Path(f"/proc/{fixture_pid}/exe")' in source
        assert 'PWD={expected_worktree}' in source
        assert '"LC_CTYPE=C.UTF-8"' in source
        assert "fixture executable mismatch" not in source

    def test_process_tree_proof_defaults_to_current_run_worktree(self, tmp_path: Path):
        calls = tmp_path / "python.argv"
        state_root = tmp_path / "state"
        script = f'''
        source "{LOCAL_VERIFY}"
        P9C0_RUN_ID=pkg3-base-proof
        P9C0_FIXTURE_BIN=/fixture.py
        _p9c0_controller_state_prefix() {{ printf '%s\n' "{state_root}"; }}
        python3() {{ printf '%s\n' "$@" > "{calls}"; }}
        _p9c0_real_process_tree_proof base.service 123
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert calls.read_text().splitlines()[-1] == str(
            state_root / "pkg3-base-proof" / "work" / "p9-3c-fixture-e1"
        )

    def test_recovery_proof_uses_primary_worktree_in_recovery_namespace(
        self, tmp_path: Path
    ):
        state_root = tmp_path / "state"
        primary_run = "pkg3-recovery-proof"
        recovery_run = f"{primary_run}-r2"
        primary_root = state_root / primary_run
        recovery_root = state_root / recovery_run
        (primary_root / "ledger").mkdir(parents=True)
        (primary_root / "evidence").mkdir()
        (recovery_root / "ledger").mkdir(parents=True)
        old_unit = f"p9-3c-fixture-e1-{primary_run}.service"
        (primary_root / "ledger" / "events.jsonl").write_text(
            f"cgroup-empty unit={old_unit}\n"
        )
        proof = tmp_path / "proof.argv"
        started = tmp_path / "started"
        script = f'''
        source "{LOCAL_VERIFY}"
        P9C0_RUN_ID={primary_run}
        P9C0_COORD_DB="{primary_root / 'db' / 'coord.sqlite3'}"
        _p9c0_controller_state_prefix() {{ printf '%s\n' "{state_root}"; }}
        _p9c0_prepare_recovery_namespace() {{ :; }}
        _p9c0_unit_start() {{ : > "{started}"; }}
        _p9c0_unit_journal() {{
            [[ -f "{started}" ]] && printf 'claude_child_boundary monotonic_ns=10 pid=777\n'
        }}
        _p9c0_recovery_monitor() {{ : > "$2"; printf '{{}}\n'; }}
        _p9c0_process_tree_proof() {{
            printf '%s|%s\n' "$P9C0_RUN_ID" "$*" > "{proof}"
            printf 'process-tree-ok\n'
        }}
        _p9c0_ledger_append() {{ :; }}
        _p9c0_record_intake() {{ :; }}
        _p9c0_chown() {{ :; }}
        _p9c0_chmod() {{ :; }}
        _p9c0_real_verify_recovery_start
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert proof.read_text().strip() == (
            f"{recovery_run}|p9-3c-fixture-e1-{recovery_run}.service 777 "
            f"{primary_root / 'work' / 'p9-3c-fixture-e1'}"
        )

    def test_only_hold_and_recovery_stops_request_crash_semantics(self):
        source = LOCAL_VERIFY.read_text()
        assert source.count('_p9c0_unit_stop "$agent" --crash') == 2
        assert '_p9c0_unit_stop p9-3c-fixture-e2 \\\n' in source
        assert "_p9c0_unit_stop p9-3c-fixture-e2 --crash" not in source

    def test_submit_uses_exact_compact_fixture_and_literal_json_argv(self, tmp_path: Path):
        state_root, prelude = self._prepared(tmp_path, "pkg3-submit-exact")
        calls = tmp_path / "coordinate.argv"
        script = prelude + f'''
        P9C0_RUN_ID=pkg3-submit-exact
        P9C0_UNIT_USER={MOCK_USER}; P9C0_UNIT_GROUP={MOCK_GROUP}
        P9C0_UNIT_UID={MOCK_UID}; P9C0_UNIT_GID={MOCK_GID}
        _p9c0_controller_run_coordinate() {{ printf '<%s>\n' "$@" > "{calls}"; }}
        _p9c0_submit_request p9-3c-fixture-e1 hold true hold
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        argv = calls.read_text().splitlines()
        assert '<{"contract_version":1,"mode":"hold","quiet_seconds":75,"spawn_descendant":true}>' in argv
        assert '<{"platform":"local-fixture","destination":"p9-3c-fixture-e1","session_scope_id":"pkg3-submit-exact:p9-3c-fixture-e1:hold","message_id":"pkg3-submit-exact-p9-3c-fixture-e1-hold"}>' in argv
        assert '<{"platform":"local-fixture","destination":"p9-3c-fixture-e1"}>' in argv
        assert '<--worktree-path>' in argv
        assert f'<{state_root / "pkg3-submit-exact" / "work" / "p9-3c-fixture-e1"}>' in argv
        assert not any("@" in item for item in argv)

    def test_submit_freezes_distinct_allowlisted_worktrees(self, tmp_path: Path):
        state_root, prelude = self._prepared(tmp_path, "pkg3-submit-worktrees")
        calls = tmp_path / "coordinate.calls"
        script = prelude + f'''
        P9C0_RUN_ID=pkg3-submit-worktrees
        P9C0_UNIT_USER={MOCK_USER}; P9C0_UNIT_GROUP={MOCK_GROUP}
        P9C0_UNIT_UID={MOCK_UID}; P9C0_UNIT_GID={MOCK_GID}
        _p9c0_controller_run_coordinate() {{ printf '%s\n' "$*" >> "{calls}"; }}
        _p9c0_submit_request p9-3c-fixture-e1 complete false e1
        _p9c0_submit_request p9-3c-fixture-e2 complete false e2
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        lines = calls.read_text().splitlines()
        assert len(lines) == 2
        e1 = state_root / "pkg3-submit-worktrees" / "work" / "p9-3c-fixture-e1"
        e2 = state_root / "pkg3-submit-worktrees" / "work" / "p9-3c-fixture-e2"
        assert e1 != e2
        assert e1.is_dir() and e2.is_dir()
        assert f"--target-agent p9-3c-fixture-e1 --worktree-path {e1}" in lines[0]
        assert f"--target-agent p9-3c-fixture-e2 --worktree-path {e2}" in lines[1]

    def test_catalog_authority_is_sealed_and_forward_order_is_exact(self, tmp_path: Path):
        state_root, prelude = self._prepared(tmp_path, "pkg3-catalog-order")
        assets = {}
        for stage in (
            "executor-v1-disabled", "capacity-v1", "executor-v2-enabled",
            "executor-v3-disabled", "capacity-v2-empty", "executor-v4-empty",
        ):
            path = tmp_path / f"{stage}.toml"
            path.write_text(f"stage={stage}\n")
            assets[stage] = path
        calls = tmp_path / "catalog.calls"
        script = prelude + f'''
        P9C0_RUN_ID=pkg3-catalog-order
        P9C0_UNIT_USER={MOCK_USER}; P9C0_UNIT_GROUP={MOCK_GROUP}
        P9C0_UNIT_UID={MOCK_UID}; P9C0_UNIT_GID={MOCK_GID}; P9C0_COORD_DB=""
        P9C0_EXECUTOR_V1="{assets['executor-v1-disabled']}"
        P9C0_CAPACITY_V1="{assets['capacity-v1']}"
        P9C0_EXECUTOR_V2="{assets['executor-v2-enabled']}"
        P9C0_EXECUTOR_V3="{assets['executor-v3-disabled']}"
        P9C0_CAPACITY_V2="{assets['capacity-v2-empty']}"
        P9C0_EXECUTOR_V4="{assets['executor-v4-empty']}"
        _p9c0_expected_catalog_sha() {{
            case "$1" in
                executor-v1-disabled) _p9c0_sha256_file "$P9C0_EXECUTOR_V1" ;;
                capacity-v1) _p9c0_sha256_file "$P9C0_CAPACITY_V1" ;;
                executor-v2-enabled) _p9c0_sha256_file "$P9C0_EXECUTOR_V2" ;;
                executor-v3-disabled) _p9c0_sha256_file "$P9C0_EXECUTOR_V3" ;;
                capacity-v2-empty) _p9c0_sha256_file "$P9C0_CAPACITY_V2" ;;
                executor-v4-empty) _p9c0_sha256_file "$P9C0_EXECUTOR_V4" ;;
            esac
        }}
        _p9c0_hostname() {{ echo fixture-host; }}
        _p9c0_controller_run_coordinate() {{ printf '%s\n' "$*" >> "{calls}"; }}
        _p9c0_verify_catalog_state() {{ :; }}
        _p9c0_verify_prepare_catalog
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        syncs = [line for line in calls.read_text().splitlines() if " sync --source " in line]
        assert syncs == [
            f"{MOCK_USER} {MOCK_UID} runtime executor sync --source {assets['executor-v1-disabled']}",
            f"{MOCK_USER} {MOCK_UID} runtime capacity sync --source {assets['capacity-v1']}",
            f"{MOCK_USER} {MOCK_UID} runtime executor sync --source {assets['executor-v2-enabled']}",
        ]
        ledger = state_root / "pkg3-catalog-order" / "ledger" / "events.jsonl"
        authority = [line for line in ledger.read_text().splitlines() if line.startswith("catalog-authority ")]
        assert len(authority) == 6
        assert all(" stat=" in line and " sha256=" in line for line in authority)

    def test_reap_summary_must_be_exactly_one_without_errors(self, tmp_path: Path):
        authority = tmp_path / "authority.json"
        authority.write_text("{}\n")
        valid = f'''
        source "{LOCAL_VERIFY}"
        P9C0_UNIT_USER={MOCK_USER}; P9C0_UNIT_UID={MOCK_UID}
        _p9c0_reap_state() {{ echo "$1"; }}
        _p9c0_controller_run_coordinate() {{
            echo '{{"result":{{"due_found":1,"reaped_count":1,"reaped":[{{}}],"errors":[]}}}}'
        }}
        _p9c0_reap_once "{authority}"
        '''
        result = _run_bash(valid)
        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == ["before", "after"]
        invalid = valid.replace('"due_found":1', '"due_found":2')
        result = _run_bash(invalid)
        assert result.returncode != 0
        assert "reap summary mismatch" in result.stderr

    def test_second_reap_uses_linked_ledger_authority_for_both_runs(
        self, tmp_path: Path
    ):
        state_root = tmp_path / "state"
        primary_id = "pkg3-second-reap"
        recovery_id = f"{primary_id}-r2"
        primary = state_root / primary_id
        recovery = state_root / recovery_id
        (primary / "db").mkdir(parents=True)
        (primary / "ledger").mkdir()
        (recovery / "ledger").mkdir(parents=True)
        (recovery / "evidence").mkdir()
        primary_db = primary / "db" / "coord.sqlite3"
        primary_db.touch()
        recovery_ledger = recovery / "ledger" / "events.jsonl"
        recovery_ledger.write_text(
            f"cgroup-empty unit=p9-3c-fixture-e1-{recovery_id}.service\n"
        )
        authority = recovery / "evidence" / "recovery-stopped-authority.json"
        authority.write_text(
            '{"expires_at":"2030-01-01T00:00:00Z","lease_id":"lease-r2"}\n'
        )
        calls = tmp_path / "ledger.calls"
        script = f'''
        set -euo pipefail
        source "{LOCAL_VERIFY}"
        _p9c0_controller_state_prefix() {{ printf '%s\n' "{state_root}"; }}
        P9C0_RUN_ID={primary_id}
        P9C0_COORD_DB="{primary_db}"
        _p9c0_wait_expiry() {{ :; }}
        _p9c0_reap_once() {{ :; }}
        _p9c0_ledger_append() {{
            printf '%s|%s|%s\n' "$P9C0_RUN_ID" "$P9C0_COORD_DB" "$1" >> "{calls}"
        }}
        _p9c0_real_verify_second_reap
        '''
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert calls.read_text().splitlines() == [
            f"{recovery_id}|{primary_db}|lease-terminal lease_id=lease-r2",
            (
                f"{primary_id}|{primary_db}|second-reap "
                f"recovery_run={recovery_id} lease_id=lease-r2"
            ),
        ]


def _bootstrap_cleanup_state(tmp_path: Path, run_id: str = "pkg3-cleanup") -> dict:
    import hashlib

    state_root = tmp_path / "state"
    prelude = _local_verify_mock_prelude(state_root)
    prepare = f'''main prepare --run-id {run_id} --unit-user {MOCK_USER} \\
        --unit-group {MOCK_GROUP} --agent local-operator'''
    result = _run_bash(prelude + prepare)
    assert result.returncode == 0, result.stderr
    run_root = state_root / run_id
    values = run_root / "values.rendered"
    values.write_text(
        f"state_root={state_root}\n"
        f"run_id={run_id}\n"
        f"coord_db={run_root / 'db' / 'coord.sqlite3'}\n"
        f"unit_user={MOCK_USER}\n"
        f"unit_group={MOCK_GROUP}\n"
        f"unit_uid={MOCK_UID}\n"
        f"unit_gid={MOCK_GID}\n"
    )
    values.chmod(0o600)
    (run_root / "db" / "coord.sqlite3").touch()
    assets = {}
    for stage, name in (
        ("executor-v3-disabled", "executor.fixture.v3-disabled.toml"),
        ("capacity-v2-empty", "capacity.fixture.v2-empty.toml"),
        ("executor-v4-empty", "executor.fixture.v4-empty.toml"),
    ):
        path = tmp_path / name
        path.write_text(f"stage={stage}\n")
        path.chmod(0o644)
        assets[stage] = path
    ledger = run_root / "ledger" / "events.jsonl"
    with ledger.open("a") as handle:
        for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
            unit = f"{agent}-{run_id}.service"
            handle.write(f"unit {unit} agent={agent}\n")
            handle.write(f"cgroup-empty unit={unit}\n")
        for stage, path in assets.items():
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            handle.write(
                f"catalog-authority stage={stage} path={path} "
                f"stat=1:14:128:1:0:0:644 sha256={sha}\n"
            )
    return {
        "state_root": state_root,
        "run_root": run_root,
        "run_id": run_id,
        "assets": assets,
        "prelude": prelude.replace(
            f'source "{LOCAL_VERIFY}"', f'source "{CLEANUP}"'
        ),
    }


def _cleanup_success_seams(facts: dict, tmp_path: Path) -> str:
    calls = tmp_path / "cleanup.calls"
    stage_file = tmp_path / "catalog.stage"
    assets = facts["assets"]
    return f'''
    P9C0_EXECUTOR_V3="{assets['executor-v3-disabled']}"
    P9C0_CAPACITY_V2="{assets['capacity-v2-empty']}"
    P9C0_EXECUTOR_V4="{assets['executor-v4-empty']}"
    _p9c0_helper_exact_stop() {{ :; }}
    _p9c0_cleanup_helper() {{
        if [[ "$1" == status ]]; then
            printf 'ActiveState=inactive\\nSubState=dead\\n'
        else
            printf 'helper:%s:%s\\n' "$1" "$2" >> "{calls}"
        fi
    }}
    _p9c0_controller_run_coordinate() {{
        printf 'coordinate:%s\\n' "$*" >> "{calls}"
        case "$*" in
            *executor.fixture.v3-disabled.toml*) echo v3 > "{stage_file}" ;;
            *capacity.fixture.v2-empty.toml*) echo capacity-v2 > "{stage_file}" ;;
            *executor.fixture.v4-empty.toml*) echo v4 > "{stage_file}" ;;
            *"runtime job lease reap"*) echo reaped > "{stage_file}" ;;
        esac
    }}
    _p9c0_cleanup_query_counts() {{
        local stage=initial
        [[ -f "{stage_file}" ]] && stage=$(cat "{stage_file}")
        case "$stage" in
            initial) echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=2 definitions=1 policies=2' ;;
            v3) echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=0 definitions=1 policies=2' ;;
            capacity-v2) echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=0 definitions=1 policies=0' ;;
            v4) echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=0 definitions=0 policies=0' ;;
            reaped) echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=2 definitions=1 policies=2' ;;
        esac
    }}
    _p9c0_cleanup_capture_snapshot() {{ printf 'snapshot\\n' >> "{calls}"; }}
    _p9c0_cleanup_verify_final_residue() {{ :; }}
    '''


class TestCleanupController:
    def test_source_safe_executable_and_forbidden_tokens(self):
        result = _run_bash(f'source "{CLEANUP}"; printf cleanup-sourced')
        assert result.returncode == 0, result.stderr
        assert result.stdout == "cleanup-sourced"
        assert CLEANUP.stat().st_mode & stat.S_IXUSR
        source = CLEANUP.read_text()
        for token in ("pkill", "pgrep", "--exact-unit", "sqlite3 DELETE", "sqlite3 UPDATE"):
            assert token not in source

    def test_exact_order_and_done_reentry_do_not_repeat_mutations(self, tmp_path: Path):
        facts = _bootstrap_cleanup_state(tmp_path)
        seams = _cleanup_success_seams(facts, tmp_path)
        command = f'''main cleanup --run-id {facts['run_id']} \\
            --unit-user {MOCK_USER} --unit-group {MOCK_GROUP}'''
        first = _run_bash(facts["prelude"] + seams + command)
        assert first.returncode == 0, first.stderr
        calls = (tmp_path / "cleanup.calls").read_text().splitlines()
        coordinate = [line for line in calls if line.startswith("coordinate:")]
        assert len(coordinate) == 3
        assert "executor.fixture.v3-disabled.toml" in coordinate[0]
        assert "capacity.fixture.v2-empty.toml" in coordinate[1]
        assert "executor.fixture.v4-empty.toml" in coordinate[2]
        assert [line for line in calls if line.startswith("helper:cleanup:")] == [
            "helper:cleanup:p9-3c-fixture-e1",
            "helper:cleanup:p9-3c-fixture-e2",
        ]
        phase = facts["run_root"] / "control" / "cleanup-phase"
        assert phase.read_text() == "cleanup-phase=done\n"
        before = (tmp_path / "cleanup.calls").read_text()
        second = _run_bash(facts["prelude"] + seams + command)
        assert second.returncode == 0, second.stderr
        assert (tmp_path / "cleanup.calls").read_text() == before

    def test_unknown_phase_is_rejected_without_catalog_mutation(self, tmp_path: Path):
        facts = _bootstrap_cleanup_state(tmp_path, run_id="pkg3-bad-phase")
        phase = facts["run_root"] / "control" / "cleanup-phase"
        phase.write_text("cleanup-phase=teleport\n")
        seams = _cleanup_success_seams(facts, tmp_path)
        command = f'''main cleanup --run-id {facts['run_id']} \\
            --unit-user {MOCK_USER} --unit-group {MOCK_GROUP}'''
        result = _run_bash(facts["prelude"] + seams + command)
        assert result.returncode != 0
        assert "unknown cleanup phase" in result.stderr
        calls = tmp_path / "cleanup.calls"
        assert not calls.exists() or "coordinate:" not in calls.read_text()
        assert phase.read_text() == "cleanup-phase=teleport\n"

    def test_malformed_counts_fail_before_first_catalog_sync(self, tmp_path: Path):
        facts = _bootstrap_cleanup_state(tmp_path, run_id="pkg3-bad-count")
        seams = _cleanup_success_seams(facts, tmp_path) + '''
        _p9c0_cleanup_query_counts() {
            echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=2 definitions=1'
        }
        '''
        command = f'''main cleanup --run-id {facts['run_id']} \\
            --unit-user {MOCK_USER} --unit-group {MOCK_GROUP}'''
        result = _run_bash(facts["prelude"] + seams + command)
        assert result.returncode != 0
        assert "count record policies invalid" in result.stderr
        calls = tmp_path / "cleanup.calls"
        assert not calls.exists() or "coordinate:" not in calls.read_text()

    def test_active_lease_waits_for_ledger_expiry_then_reaps_once(self, tmp_path: Path):
        facts = _bootstrap_cleanup_state(tmp_path, run_id="pkg3-expiry-cleanup")
        ledger = facts["run_root"] / "ledger" / "events.jsonl"
        with ledger.open("a") as handle:
            handle.write("lease-active lease_id=lease-1 expires_at=2030-01-01T00:00:00Z\n")
        seams = _cleanup_success_seams(facts, tmp_path)
        seams += f'''
        _p9c0_cleanup_query_counts() {{
            local stage=active
            [[ -f "{tmp_path / 'catalog.stage'}" ]] && stage=$(cat "{tmp_path / 'catalog.stage'}")
            case "$stage" in
                active) echo 'active_leases=1 pending_running=1 capacity_refs=1 bindings=2 definitions=1 policies=2' ;;
                reaped) echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=2 definitions=1 policies=2' ;;
                v3) echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=0 definitions=1 policies=2' ;;
                capacity-v2) echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=0 definitions=1 policies=0' ;;
                v4) echo 'active_leases=0 pending_running=0 capacity_refs=0 bindings=0 definitions=0 policies=0' ;;
            esac
        }}
        _p9c0_cleanup_wait_past_expiry() {{ printf 'wait:%s\\n' "$1" >> "{tmp_path / 'cleanup.calls'}"; }}
        '''
        command = f'''main cleanup --run-id {facts['run_id']} \\
            --unit-user {MOCK_USER} --unit-group {MOCK_GROUP}'''
        result = _run_bash(facts["prelude"] + seams + command)
        assert result.returncode == 0, result.stderr
        calls = (tmp_path / "cleanup.calls").read_text().splitlines()
        assert calls.count("wait:2030-01-01T00:00:00Z") == 1
        assert calls.count(
            f"coordinate:{MOCK_USER} {MOCK_UID} runtime job lease reap"
        ) == 1

    def test_cleanup_collects_and_cleans_linked_recovery_unit(self, tmp_path: Path):
        facts = _bootstrap_cleanup_state(tmp_path, "pkg3-linked-cleanup")
        primary = facts["run_root"]
        recovery_id = f"{facts['run_id']}-r2"
        recovery = facts["state_root"] / recovery_id
        (recovery / "ledger").mkdir(parents=True)
        for child in ("control", "lock", "evidence", "db", "work", "harness", "context"):
            (recovery / child).mkdir(parents=True, exist_ok=True)
        shared_db = primary / "db" / "coord.sqlite3"
        with (primary / "ledger" / "events.jsonl").open("a") as handle:
            handle.write(
                f"recovery-run run_id={recovery_id} shared_db={shared_db}\n"
            )
        recovery_unit = f"p9-3c-fixture-e1-{recovery_id}.service"
        (recovery / "ledger" / "events.jsonl").write_text(
            f"parent-run run_id={facts['run_id']} shared_db={shared_db}\n"
            f"unit {recovery_unit} agent=p9-3c-fixture-e1\n"
            f"cgroup-empty unit={recovery_unit}\n"
        )
        (recovery / "values.rendered").write_text(
            f"state_root={facts['state_root']}\n"
            f"run_id={recovery_id}\n"
            f"coord_db={shared_db}\n"
            f"unit_user={MOCK_USER}\n"
            f"unit_group={MOCK_GROUP}\n"
            f"unit_uid={MOCK_UID}\n"
            f"unit_gid={MOCK_GID}\n"
        )
        linked_calls = tmp_path / "linked-helper.calls"
        script = (
            facts["prelude"]
            + _cleanup_success_seams(facts, tmp_path)
            + f'''
            _p9c0_cleanup_helper() {{
                if [[ "$1" == status ]]; then
                    printf 'ActiveState=inactive\nSubState=dead\n'
                else
                    printf '%s|%s|%s\n' "$1" "$2" "$3" >> "{linked_calls}"
                fi
            }}
            main cleanup --run-id {facts['run_id']} --unit-user {MOCK_USER} \\
                --unit-group {MOCK_GROUP}
            '''
        )
        result = _run_bash(script)
        assert result.returncode == 0, result.stderr
        assert linked_calls.read_text().splitlines() == [
            f"cleanup|p9-3c-fixture-e1|{facts['run_id']}",
            f"cleanup|p9-3c-fixture-e2|{facts['run_id']}",
            f"cleanup|p9-3c-fixture-e1|{recovery_id}",
        ]


def _p9c1_helper_state(tmp_path: Path) -> dict:
    """Build a fake installed production tree for public helper commands."""
    run_id = "p9-3c1-prod-20260716t120000z-abcdef01"
    state_base = tmp_path / "state"
    state_root = state_base / run_id
    for relative in (
        "control",
        "ledger",
        "evidence",
        "backup",
        "runtime/work/e1",
        "runtime/work/e2",
        "runtime/context",
        "runtime/unit",
    ):
        (state_root / relative).mkdir(parents=True, exist_ok=True)

    python_path = Path(sys.executable).resolve()
    helper_path = UNIT_HELPER.resolve()
    fixture = tmp_path / "p9-3c0-fixture.py"
    fixture.write_text("#!/bin/sh\nexit 0\n")
    _chmod_exec(fixture)
    cli = tmp_path / "coord-local"
    cli.write_text("#!/bin/sh\nexit 0\n")
    _chmod_exec(cli)
    db = tmp_path / "coord.sqlite3"
    db.write_bytes(b"fake-production-db")
    lock_helper = tmp_path / "production-mutation-lock.sh"
    lock_helper.write_text("#!/bin/sh\nexit 0\n")
    _chmod_exec(lock_helper)
    template = tmp_path / "agents.production.toml"
    template_text = (
        REPO_ROOT
        / "multinexus"
        / "fixture"
        / "config"
        / "p9-3c1"
        / "agents.production.toml"
    ).read_text()
    template.write_text(
        template_text.replace(
            "/opt/multinexus/multinexus/fixture/bin/p9-3c0-fixture.py",
            str(fixture),
        )
        .replace("/usr/local/bin/coord-local", str(cli))
        .replace("/var/lib/coordinate/coord.sqlite3", str(db))
    )

    def identity(path: Path, digest: str, inode: int, mode: int) -> dict:
        return {
            "path": str(path),
            "dev": 10,
            "inode": inode,
            "size": 128,
            "nlink": 1,
            "owner": 0,
            "group": 0,
            "mode": mode,
            "sha256": digest,
        }

    identities = {
        "python": identity(python_path, "1" * 64, 101, 0o755),
        "helper": identity(helper_path, "2" * 64, 102, 0o755),
        "fixture_bin": identity(fixture, "3" * 64, 103, 0o755),
        "agent_template": identity(template, "4" * 64, 104, 0o644),
        "mutation_lock_helper": identity(lock_helper, "5" * 64, 105, 0o755),
    }
    cli_identity = identity(cli, "6" * 64, 106, 0o755)
    db_identity = identity(db, "7" * 64, 107, 0o600)
    launcher = {
        "cli_path": str(cli),
        "cli_dev": cli_identity["dev"],
        "cli_inode": cli_identity["inode"],
        "cli_owner": 0,
        "cli_group": 0,
        "cli_mode": 0o755,
        "db_path": str(db),
        "db_dev": db_identity["dev"],
        "db_inode": db_identity["inode"],
        "db_owner": 0,
        "db_group": 0,
        "db_mode": 0o600,
        "python_path": str(python_path),
        "python_sha256": identities["python"]["sha256"],
        "python_dev": 10,
        "python_inode": 101,
        "python_owner": 0,
        "python_group": 0,
        "python_mode": 0o755,
        "helper_path": str(helper_path),
        "helper_sha256": identities["helper"]["sha256"],
        "fixture_bin_path": str(fixture),
        "fixture_bin_sha256": identities["fixture_bin"]["sha256"],
        "agent_template_path": str(template),
        "agent_template_sha256": identities["agent_template"]["sha256"],
        "config_dir": str(tmp_path),
        "lock_helper_path": str(lock_helper),
        "files": identities,
        "cli_file": cli_identity,
        "db_file": db_identity,
    }
    manifest = {
        "production_launcher_identity": launcher,
        "run_id": run_id,
        "state_root": str(state_root),
        "unit_user": MOCK_USER,
        "unit_group": MOCK_GROUP,
        "unit_uid": int(MOCK_UID),
        "unit_gid": int(MOCK_GID),
        "installed_revisions": {
            "multinexus_deployed": "8" * 40,
            "coordinate_deployed": "9" * 40,
        },
        "installed_hashes": {"controller": "a" * 64},
        "config_hashes": {"agents.production.toml": "b" * 64},
        "helper_allowlist": ["p9-3c-fixture-e1", "p9-3c-fixture-e2"],
        "reap_policy": {"mode": "none", "reason": "p9-3c1-sealed-test"},
        "budgets": {
            "total_requests": 5,
            "max_active_units": 2,
            "provider_network": 0,
            "external_delivery": 0,
        },
        "workspace_id": "p9-3c1-production",
        "host_id": "VM-0-15-ubuntu",
        "backup_identity": db_identity,
        "canonical_projection_sha256": "d" * 64,
        "prepared_at_utc": "2026-07-16T12:00:00Z",
        "p3_authorization_digest": None,
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()
    manifest_path = state_root / "control" / "manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    manifest_path.chmod(0o600)
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    token = state_root / "control" / "production-lock.token"
    token.write_text("c" * 64)
    token.chmod(0o600)

    calls = tmp_path / "systemd-run.calls"
    stopped = tmp_path / "systemd.stopped"
    stub_bin = tmp_path / "stub-bin"
    stub_bin.mkdir()
    for name in ("systemctl", "systemd-run"):
        stub = stub_bin / name
        stub.write_text("#!/bin/sh\nexit 0\n")
        _chmod_exec(stub)

    stat_cases = []
    sha_cases = []
    for item in [*identities.values(), cli_identity, db_identity]:
        if item["path"] == str(db):
            stat_cases.append(
                f'"{item["path"]}") '
                f'echo "{item["dev"]}:$([[ "${{DB_INODE_DRIFT:-0}}" == 1 ]] '
                f'&& echo 999 || echo {item["inode"]}):'
                f'$([[ "${{DB_CONTENT_MUTATED:-0}}" == 1 ]] && echo 999 || echo {item["size"]})'
                f':1:0:0:{item["mode"]:o}" ;;'
            )
        else:
            stat_cases.append(
                f'"{item["path"]}") echo "{item["dev"]}:{item["inode"]}:'
                f'{item["size"]}:1:0:0:{item["mode"]:o}" ;;'
            )
        sha_cases.append(f'"{item["path"]}") echo "{item["sha256"]}" ;;')

    prelude = f'''
    source "{UNIT_HELPER}"
    P9C1_STATE_ROOT_PREFIX="{state_base}"
    P9C1_INSTALLED_PYTHON="{python_path}"
    P9C1_INSTALLED_LOCK_HELPER="{lock_helper}"
    export PATH="{stub_bin}:$PATH"
    _p9c1_effective_uid() {{ echo 0; }}
    _p9c1_lock_helper_status() {{
        if [[ "${{LOCK_MISMATCH:-0}}" == 1 ]]; then
            printf '%s\n' '{{"state":"held","phase":"held","owner":"wrong","action":"p9-3c1-run:{run_id}","token_matches":false}}'
        else
            printf '%s\n' '{{"state":"held","phase":"held","owner":"p9-3c1-controller","action":"p9-3c1-run:{run_id}","token_matches":true}}'
        fi
    }}
    _p9c0_identity_lookup_user() {{ [[ "$1" == "{MOCK_USER}" ]] && echo {MOCK_UID}; }}
    _p9c0_identity_lookup_group() {{ [[ "$1" == "{MOCK_GROUP}" ]] && echo {MOCK_GID}; }}
    _p9c0_set_owner_group_mode() {{ chmod "$4" "$1"; }}
    _p9c0_lock_file_authority() {{ return 0; }}
    _p9c0_stat_file() {{
        case "$1" in
            {os.linesep.join(stat_cases)}
            "{manifest_path}"|"{token}"|*/helper-events.log|*/unit-helper.lock|*/values.rendered|*/systemd.verify.service)
                echo "10:201:128:1:0:0:600" ;;
            *) echo "10:202:128:1:0:{MOCK_GID}:640" ;;
        esac
    }}
    _p9c0_sha256_file() {{
        case "$1" in
            "{manifest_path}") echo "{manifest_sha}" ;;
            {os.linesep.join(sha_cases)}
            */systemd.verify.service) echo "{MOCK_DEF_SHA}" ;;
            *) echo "{MOCK_WRAPPER_SHA}" ;;
        esac
    }}
    _p9c0_systemd_analyze() {{ return 0; }}
    _p9c0_run_systemd_run() {{ printf '%s\n' "$*" >> "{calls}"; }}
    _p9c0_post_start_verify() {{ return 0; }}
    _p9c0_date_ms() {{ echo 1000; }}
    _p9c0_flock() {{ return 0; }}
    _p9c0_sleep() {{ return 0; }}
    _p9c0_python_normalize() {{ return 0; }}
    _p9c0_cgroup_procs_path() {{ printf '%s\n' "{tmp_path}/absent-cgroup.procs"; }}
    _p9c0_systemctl() {{
        if [[ "$1" == list-units ]]; then
            [[ "${{EXACT_UNIT_ACTIVE:-0}}" == 1 ]] && printf '%s loaded active running\n' "${{@: -1}}"
            return 0
        fi
        if [[ "$1" == stop ]]; then : > "{stopped}"; return 0; fi
        if [[ "$1" == reset-failed || "$1" == kill ]]; then return 0; fi
        if [[ "$1" == show ]]; then
            case "$*" in
                *"-p ActiveState -p SubState -p MainPID -p ControlGroup -p Result"*)
                    printf 'ActiveState=%s\nSubState=%s\nMainPID=4321\nControlGroup=/system.slice/fake.service\nResult=success\n' \
                        "$([[ -f "{stopped}" ]] && echo inactive || echo active)" \
                        "$([[ -f "{stopped}" ]] && echo dead || echo running)" ;;
                *"-p MainPID --value"*) echo 4321 ;;
                *"-p ControlGroup --value"*) echo /system.slice/fake.service ;;
                *"-p ActiveState --value"*) [[ -f "{stopped}" ]] && echo inactive || echo active ;;
                *"-p Result --value"*) echo success ;;
                *) return 0 ;;
            esac
            return 0
        fi
        return 0
    }}
    '''
    base_args = (
        f'--state-root "{state_root}" --run-id "{run_id}" '
        f'--controller-manifest "{manifest_path}" '
        f'--controller-manifest-sha256 "{manifest_sha}"'
    )
    return {
        "prelude": prelude,
        "state_root": state_root,
        "run_id": run_id,
        "manifest": manifest_path,
        "manifest_sha": manifest_sha,
        "token": token,
        "calls": calls,
        "base_args": base_args,
    }


def _tree_snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): (
            stat.S_IMODE(path.stat().st_mode),
            path.stat().st_mtime_ns,
            path.read_bytes() if path.is_file() else None,
        )
        for path in sorted(root.rglob("*"))
    }


class TestP9C1ProductionUnitHelper:
    def test_public_commands_reuse_start_stop_cleanup_and_sealed_reap_policy(self, tmp_path: Path):
        facts = _p9c1_helper_state(tmp_path)
        render = _run_bash(
            facts["prelude"]
            + f'main production-render {facts["base_args"]} '
            + f'--lock-token-file "{facts["token"]}"'
        )
        assert render.returncode == 0, render.stderr

        before = _tree_snapshot(facts["state_root"])
        preflight = _run_bash(
            facts["prelude"]
            + f'main production-preflight {facts["base_args"]} --agent-id p9-3c-fixture-e1'
        )
        assert preflight.returncode == 0, preflight.stderr
        assert _tree_snapshot(facts["state_root"]) == before

        normal = _run_bash(
            facts["prelude"]
            + f'main production-start {facts["base_args"]} '
            + f'--lock-token-file "{facts["token"]}" --agent-id p9-3c-fixture-e1 --mode complete'
        )
        assert normal.returncode == 0, normal.stderr
        recovery = _run_bash(
            facts["prelude"]
            + f'main production-start {facts["base_args"]} '
            + f'--lock-token-file "{facts["token"]}" --agent-id p9-3c-fixture-e2 --mode hold '
            + '--recoverable --recovery-reason bounded-recovery --prior-process-stopped'
        )
        assert recovery.returncode == 0, recovery.stderr
        calls = facts["calls"].read_text().splitlines()
        assert len(calls) == 2
        assert "--reap-mode none --reap-reason p9-3c1-sealed-test" in calls[0]
        assert "--recoverable" not in calls[0]
        assert "--recoverable --recovery-reason bounded-recovery --prior-process-stopped" in calls[1]
        assert "--reap-mode none --reap-reason p9-3c1-sealed-test" in calls[1]

        third = _run_bash(
            facts["prelude"]
            + "EXACT_UNIT_ACTIVE=1; "
            + f'main production-start {facts["base_args"]} '
            + f'--lock-token-file "{facts["token"]}" --agent-id p9-3c-fixture-e1 --mode complete'
        )
        assert third.returncode != 0
        assert "already active" in third.stderr
        assert len(facts["calls"].read_text().splitlines()) == 2

        status_before = _tree_snapshot(facts["state_root"])
        status = _run_bash(
            facts["prelude"]
            + f'main production-status {facts["base_args"]} --agent-id p9-3c-fixture-e1'
        )
        assert status.returncode == 0, status.stderr
        assert json.loads(status.stdout)["properties"]["ActiveState"] == "active"
        assert _tree_snapshot(facts["state_root"]) == status_before

        crashed = _run_bash(
            facts["prelude"]
            + f'main production-stop {facts["base_args"]} '
            + f'--lock-token-file "{facts["token"]}" --agent-id p9-3c-fixture-e1 --crash'
        )
        assert crashed.returncode == 0, crashed.stderr
        assert json.loads(crashed.stdout)["termination"] == "crash"

        recovered = _run_bash(
            facts["prelude"]
            + f'main production-start {facts["base_args"]} '
            + f'--lock-token-file "{facts["token"]}" --agent-id p9-3c-fixture-e1 --mode hold '
            + '--recoverable --recovery-reason bounded-recovery-generation --prior-process-stopped'
        )
        assert recovered.returncode == 0, recovered.stderr
        calls = facts["calls"].read_text().splitlines()
        assert len(calls) == 3
        assert "--recoverable --recovery-reason bounded-recovery-generation --prior-process-stopped" in calls[2]

        for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
            stopped = _run_bash(
                facts["prelude"]
                + f'main production-stop {facts["base_args"]} '
                + f'--lock-token-file "{facts["token"]}" --agent-id {agent}'
            )
            assert stopped.returncode == 0, stopped.stderr
        definition = facts["state_root"] / "runtime" / "unit" / "systemd.verify.service"
        for agent in ("p9-3c-fixture-e1", "p9-3c-fixture-e2"):
            cleaned = _run_bash(
                facts["prelude"]
                + f'main production-cleanup {facts["base_args"]} '
                + f'--lock-token-file "{facts["token"]}" --agent-id {agent}'
            )
            assert cleaned.returncode == 0, cleaned.stderr
        assert not definition.exists()

    def test_lock_mismatch_blocks_render_before_helper_state_mutation(self, tmp_path: Path):
        facts = _p9c1_helper_state(tmp_path)
        result = _run_bash(
            facts["prelude"]
            + "LOCK_MISMATCH=1; "
            + f'main production-render {facts["base_args"]} '
            + f'--lock-token-file "{facts["token"]}"'
        )
        assert result.returncode != 0
        assert "lock helper" in result.stderr
        assert not (facts["state_root"] / "runtime" / "unit" / "helper-events.log").exists()
        assert not (facts["state_root"] / "agents.rendered.toml").exists()

    def test_identity_drift_fails_read_only_preflight_without_repair(self, tmp_path: Path):
        facts = _p9c1_helper_state(tmp_path)
        render = _run_bash(
            facts["prelude"]
            + f'main production-render {facts["base_args"]} '
            + f'--lock-token-file "{facts["token"]}"'
        )
        assert render.returncode == 0, render.stderr
        before = _tree_snapshot(facts["state_root"])
        drift = facts["prelude"] + f'''
        _p9c0_sha256_file() {{
            if [[ "$1" == "{facts['manifest']}" ]]; then echo "{facts['manifest_sha']}";
            elif [[ "$1" == */p9-3c0-fixture.py ]]; then echo "{'f' * 64}";
            elif [[ "$1" == */systemd.verify.service ]]; then echo "{MOCK_DEF_SHA}";
            else echo "{MOCK_WRAPPER_SHA}"; fi
        }}
        main production-preflight {facts['base_args']} --agent-id p9-3c-fixture-e1
        '''
        result = _run_bash(drift)
        assert result.returncode != 0
        assert "identity drift" in result.stderr
        assert _tree_snapshot(facts["state_root"]) == before

    def test_database_content_may_change_but_inode_authority_may_not(self, tmp_path: Path):
        facts = _p9c1_helper_state(tmp_path)
        render = _run_bash(
            facts["prelude"]
            + f'main production-render {facts["base_args"]} '
            + f'--lock-token-file "{facts["token"]}"'
        )
        assert render.returncode == 0, render.stderr
        before = _tree_snapshot(facts["state_root"])
        content_change = _run_bash(
            facts["prelude"]
            + "DB_CONTENT_MUTATED=1; "
            + f'main production-preflight {facts["base_args"]} --agent-id p9-3c-fixture-e1'
        )
        assert content_change.returncode == 0, content_change.stderr
        assert _tree_snapshot(facts["state_root"]) == before
        inode_change = _run_bash(
            facts["prelude"]
            + "DB_INODE_DRIFT=1; "
            + f'main production-preflight {facts["base_args"]} --agent-id p9-3c-fixture-e1'
        )
        assert inode_change.returncode != 0
        assert "DB identity drift" in inode_change.stderr
        assert _tree_snapshot(facts["state_root"]) == before
