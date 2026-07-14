"""Tests for MultiNexus strict consumption of Coordinate v1 ExecutionLease."""
from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from multinexus.adapters.base import AdapterResult
from multinexus.agentd.coordinate_client import (
    CoordinateRuntimeClient,
    CoordinateRuntimeError,
)
from multinexus.agentd.execution_lease import (
    ExecutionLeaseError,
    ExecutionLeaseV1,
    compute_lease_envelope_sha256,
    fixture_sha256,
    load_fixture,
    parse_execution_lease,
    validate_execution_lease,
)
from multinexus.agentd.worker import AgentdWorker
from multinexus.models import AgentConfig


def _config(**overrides):
    defaults = {
        "id": "test-agent",
        "token": "fake-token",
        "adapter": "claude",
        "context_db_path": str(Path(tempfile.mkdtemp()) / "test.sqlite3"),
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)


def _make_lease(
    *,
    job_id: str = "request:e1",
    agent_id: str = "test-agent",
    runner_profile_id: str = "test-agent",
    host_id: str = "host1",
    worktree_path: str = "/host/ws",
    attempt_token: int = 1,
) -> dict[str, object]:
    return {
        "contract_version": 1,
        "lease_id": "039bdcda-de94-4bbd-9f26-13f39b2d33bf",
        "job_id": job_id,
        "attempt_token": attempt_token,
        "agent_id": agent_id,
        "runner_profile_id": runner_profile_id,
        "host_id": host_id,
        "resource_kind": "worktree",
        "resource_key": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "normalized_path": worktree_path,
        "capacity_policy_id": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "max_concurrent_jobs": 1,
        "acquired_at": "2026-07-14T12:00:00Z",
        "expires_at": "2026-07-14T12:02:00Z",
        "server_now": "2026-07-14T12:00:00Z",
        "ttl_seconds": 120,
        "renew_interval_seconds": 30,
    }


def _make_context(
    *,
    job_id: str = "request:e1",
    worktree_path: str = "/host/ws",
    session_scope_id: str = "scope:1",
    host_id: str = "host1",
    assigned_agent: str = "test-agent",
) -> dict[str, object]:
    ctx = {
        "job_id": job_id,
        "workspace_id": "ws",
        "task_id": None,
        "assigned_agent": assigned_agent,
        "host_id": host_id,
        "workspace_path": worktree_path,
        "worktree_path": worktree_path,
        "harness_root": "/host/harness",
        "branch": None,
        "session_scope_id": session_scope_id,
        "legacy_scope_ids": [],
        "log_handle": {"kind": "coordinate_job", "job_id": job_id, "logs_path": None},
        "contract_version": 1,
    }
    canonical_json = json.dumps(ctx, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ctx["context_id"] = "sha256:" + hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return ctx


def _claim_result(
    *,
    job_id: str = "request:e1",
    worktree_path: str = "/host/ws",
    session_scope_id: str = "scope:1",
    host_id: str = "host1",
    assigned_agent: str = "test-agent",
    include_lease: bool = True,
    lease_overrides: dict | None = None,
) -> dict[str, object]:
    lease = _make_lease(
        job_id=job_id,
        agent_id=assigned_agent,
        worktree_path=worktree_path,
    )
    if lease_overrides:
        lease.update(lease_overrides)
    result: dict[str, object] = {
        "claimed": True,
        "job": {
            "id": job_id,
            "workspace_id": "ws",
            "assigned_agent": assigned_agent,
            "attempt_count": 1,
            "payload_json": json.dumps({"prompt": "hello"}),
        },
        "attempt_token": 1,
        "execution_context": _make_context(
            job_id=job_id,
            worktree_path=worktree_path,
            session_scope_id=session_scope_id,
            host_id=host_id,
            assigned_agent=assigned_agent,
        ),
    }
    if include_lease:
        result["execution_lease"] = lease
    return result


class ParseExecutionLeaseTests(unittest.TestCase):
    def test_parse_valid_lease(self) -> None:
        lease = parse_execution_lease(_make_lease())
        self.assertIsInstance(lease, ExecutionLeaseV1)
        self.assertEqual(lease.job_id, "request:e1")
        self.assertEqual(lease.agent_id, "test-agent")
        self.assertEqual(lease.ttl_seconds, 120)

    def test_parse_rejects_non_dict(self) -> None:
        with self.assertRaisesRegex(ExecutionLeaseError, "must be an object"):
            parse_execution_lease("lease")

    def test_parse_rejects_missing_keys(self) -> None:
        data = _make_lease()
        del data["lease_id"]
        with self.assertRaisesRegex(ExecutionLeaseError, "incorrect keys"):
            parse_execution_lease(data)

    def test_parse_rejects_extra_keys(self) -> None:
        data = _make_lease()
        data["extra"] = "surprise"
        with self.assertRaisesRegex(ExecutionLeaseError, "incorrect keys"):
            parse_execution_lease(data)

    def test_parse_rejects_wrong_version(self) -> None:
        data = _make_lease()
        data["contract_version"] = 2
        with self.assertRaisesRegex(ExecutionLeaseError, "contract_version 2"):
            parse_execution_lease(data)

    def test_parse_rejects_bad_lease_id(self) -> None:
        data = _make_lease()
        data["lease_id"] = "not-a-uuid"
        with self.assertRaisesRegex(ExecutionLeaseError, "lease_id must be a lowercase UUID"):
            parse_execution_lease(data)

    def test_parse_rejects_bad_resource_key(self) -> None:
        data = _make_lease()
        data["resource_key"] = "md5:abc"
        with self.assertRaisesRegex(ExecutionLeaseError, "sha256:<64-hex>"):
            parse_execution_lease(data)

    def test_parse_rejects_relative_path(self) -> None:
        data = _make_lease()
        data["normalized_path"] = "relative/path"
        with self.assertRaisesRegex(ExecutionLeaseError, "must be absolute"):
            parse_execution_lease(data)

    def test_parse_rejects_traversal(self) -> None:
        data = _make_lease()
        data["normalized_path"] = "/host/../other"
        with self.assertRaisesRegex(ExecutionLeaseError, "traversal"):
            parse_execution_lease(data)

    def test_parse_rejects_negative_ttl(self) -> None:
        data = _make_lease()
        data["ttl_seconds"] = -10
        with self.assertRaisesRegex(ExecutionLeaseError, "ttl_seconds"):
            parse_execution_lease(data)

    def test_parse_rejects_ttl_too_long(self) -> None:
        data = _make_lease()
        data["ttl_seconds"] = 601
        with self.assertRaisesRegex(ExecutionLeaseError, "ttl_seconds"):
            parse_execution_lease(data)

    def test_parse_rejects_renew_interval_gte_ttl(self) -> None:
        data = _make_lease()
        data["renew_interval_seconds"] = 120
        with self.assertRaisesRegex(ExecutionLeaseError, "renew_interval_seconds"):
            parse_execution_lease(data)

    def test_parse_rejects_expires_not_after_acquired(self) -> None:
        data = _make_lease()
        data["expires_at"] = data["acquired_at"]
        with self.assertRaisesRegex(ExecutionLeaseError, "expires_at must be after acquired_at"):
            parse_execution_lease(data)

    def test_parse_rejects_ttl_mismatch(self) -> None:
        data = _make_lease()
        data["ttl_seconds"] = 90
        with self.assertRaisesRegex(ExecutionLeaseError, "ttl_seconds .* does not match"):
            parse_execution_lease(data)

    def test_parse_rejects_server_now_before_acquired(self) -> None:
        data = _make_lease()
        data["server_now"] = "2026-07-14T11:59:59Z"
        with self.assertRaisesRegex(ExecutionLeaseError, "server_now must not be before"):
            parse_execution_lease(data)


class ValidateExecutionLeaseIdentityTests(unittest.TestCase):
    def test_accepts_matching_identity(self) -> None:
        lease = validate_execution_lease(
            _make_lease(),
            expected_agent_id="test-agent",
            expected_job_id="request:e1",
            expected_attempt_token=1,
        )
        self.assertEqual(lease.agent_id, "test-agent")

    def test_rejects_agent_id_mismatch(self) -> None:
        with self.assertRaisesRegex(ExecutionLeaseError, "agent_id mismatch"):
            validate_execution_lease(
                _make_lease(),
                expected_agent_id="other-agent",
            )

    def test_rejects_job_id_mismatch(self) -> None:
        with self.assertRaisesRegex(ExecutionLeaseError, "job_id mismatch"):
            validate_execution_lease(
                _make_lease(),
                expected_agent_id="test-agent",
                expected_job_id="request:e2",
            )

    def test_rejects_attempt_token_mismatch(self) -> None:
        with self.assertRaisesRegex(ExecutionLeaseError, "attempt_token mismatch"):
            validate_execution_lease(
                _make_lease(),
                expected_agent_id="test-agent",
                expected_attempt_token=2,
            )

    def test_context_cross_check_passes(self) -> None:
        lease = validate_execution_lease(
            _make_lease(),
            expected_agent_id="test-agent",
            execution_context=_make_context(),
        )
        self.assertEqual(lease.normalized_path, "/host/ws")

    def test_context_cross_check_rejects_worktree_mismatch(self) -> None:
        ctx = _make_context()
        ctx["worktree_path"] = "/host/other"
        with self.assertRaisesRegex(ExecutionLeaseError, "normalized_path does not match"):
            validate_execution_lease(
                _make_lease(),
                expected_agent_id="test-agent",
                execution_context=ctx,
            )

    def test_binding_cross_check_passes(self) -> None:
        binding = {
            "executor_instance_id": "test-agent",
            "runner_profile_id": "test-agent",
        }
        lease = validate_execution_lease(
            _make_lease(),
            expected_agent_id="test-agent",
            executor_binding=binding,
        )
        self.assertEqual(lease.runner_profile_id, "test-agent")

    def test_binding_cross_check_rejects_runner_mismatch(self) -> None:
        binding = {
            "executor_instance_id": "test-agent",
            "runner_profile_id": "other-profile",
        }
        with self.assertRaisesRegex(ExecutionLeaseError, "runner_profile_id does not match"):
            validate_execution_lease(
                _make_lease(),
                expected_agent_id="test-agent",
                executor_binding=binding,
            )


class FixtureTests(unittest.TestCase):
    def test_positive_fixture_loads_and_validates(self) -> None:
        data = load_fixture("execution_lease_v1_positive.json")
        lease = parse_execution_lease(data)
        self.assertEqual(lease.lease_id, "039bdcda-de94-4bbd-9f26-13f39b2d33bf")

    def test_positive_fixture_sha_is_pinned(self) -> None:
        actual = fixture_sha256("execution_lease_v1_positive.json")
        self.assertEqual(
            actual,
            "92a3ea27b61abe79482f574c7e5802c3e2b090f548f23fa86bc54fed65bde98e",
        )

    def test_missing_keys_fixture_rejected(self) -> None:
        data = load_fixture("execution_lease_v1_missing_keys.json")
        with self.assertRaisesRegex(ExecutionLeaseError, "incorrect keys"):
            parse_execution_lease(data)

    def test_bad_identity_fixture_rejected(self) -> None:
        data = load_fixture("execution_lease_v1_bad_identity.json")
        with self.assertRaisesRegex(ExecutionLeaseError, "agent_id mismatch"):
            validate_execution_lease(
                data,
                expected_agent_id="test-agent",
            )

    def test_context_mismatch_fixture_rejected(self) -> None:
        data = load_fixture("execution_lease_v1_context_mismatch.json")
        ctx = _make_context(
            assigned_agent="mac-omp",
            host_id="mac",
            worktree_path="/Users/yinxin/projects/multinexus",
        )
        with self.assertRaisesRegex(ExecutionLeaseError, "normalized_path does not match"):
            validate_execution_lease(
                data,
                expected_agent_id="mac-omp",
                execution_context=ctx,
            )

    def test_canonical_envelope_sha_matches_file_digest(self) -> None:
        data = load_fixture("execution_lease_v1_positive.json")
        envelope_sha = compute_lease_envelope_sha256(data)
        file_sha = fixture_sha256("execution_lease_v1_positive.json")
        self.assertEqual(envelope_sha, file_sha)


class CoordinateClientLeaseTests(unittest.TestCase):
    def _client(self):
        return CoordinateRuntimeClient(cli_path="/bin/true", db_path="/tmp/test.db")

    @patch("multinexus.agentd.coordinate_client.subprocess.run")
    def test_report_job_passes_lease_id(self, mock_run):
        import subprocess
        mock_run.return_value = subprocess.CompletedProcess(
            "cmd", 0, stdout='{"ok": true}', stderr=""
        )
        client = self._client()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                client.report_job(
                    job_id="j1",
                    agent_id="a1",
                    status="done",
                    result_json={},
                    attempt_token=1,
                    lease_id="lease-1",
                )
            )
        finally:
            loop.close()
        cmd = mock_run.call_args[0][0]
        self.assertIn("--lease-id", cmd)
        self.assertIn("lease-1", cmd)
        self.assertIn("--attempt-token", cmd)
        self.assertIn("1", cmd)

    @patch("multinexus.agentd.coordinate_client.subprocess.run")
    def test_record_progress_passes_lease_id(self, mock_run):
        import subprocess
        mock_run.return_value = subprocess.CompletedProcess(
            "cmd", 0, stdout='{"ok": true}', stderr=""
        )
        client = self._client()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                client.record_progress(
                    job_id="j1",
                    agent_id="a1",
                    stage="stream",
                    attempt_token=1,
                    lease_id="lease-1",
                )
            )
        finally:
            loop.close()
        cmd = mock_run.call_args[0][0]
        self.assertIn("--lease-id", cmd)
        self.assertIn("lease-1", cmd)

    @patch("multinexus.agentd.coordinate_client.subprocess.run")
    def test_renew_lease_command(self, mock_run):
        import subprocess
        mock_run.return_value = subprocess.CompletedProcess(
            "cmd", 0, stdout='{"result": {"expires_at": "2026-07-14T12:04:00Z", "server_now": "2026-07-14T12:00:00Z"}}', stderr=""
        )
        client = self._client()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                client.renew_lease(
                    job_id="j1",
                    agent_id="a1",
                    attempt_token=1,
                    lease_id="lease-1",
                )
            )
        finally:
            loop.close()
        cmd = mock_run.call_args[0][0]
        self.assertIn("runtime", cmd)
        self.assertIn("job", cmd)
        self.assertIn("lease", cmd)
        self.assertIn("renew", cmd)
        self.assertIn("--lease-id", cmd)
        self.assertIn("lease-1", cmd)
        self.assertEqual(result["result"]["expires_at"], "2026-07-14T12:04:00Z")

    @patch("multinexus.agentd.coordinate_client.subprocess.run")
    def test_reap_leases_command(self, mock_run):
        import subprocess
        mock_run.return_value = subprocess.CompletedProcess(
            "cmd", 0, stdout='{"reaped": 3}', stderr=""
        )
        client = self._client()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(client.reap_leases(actor="agentd", batch_size=50))
        finally:
            loop.close()
        cmd = mock_run.call_args[0][0]
        self.assertIn("runtime", cmd)
        self.assertIn("job", cmd)
        self.assertIn("lease", cmd)
        self.assertIn("reap", cmd)
        self.assertIn("--actor", cmd)
        self.assertIn("agentd", cmd)
        self.assertIn("--batch-size", cmd)
        self.assertIn("50", cmd)
        self.assertEqual(result["reaped"], 3)


class WorkerLeaseValidationTests(unittest.TestCase):
    """P9-3B: worker must validate execution_lease before invoking provider."""

    def _make_worker(self):
        worker = AgentdWorker(_config())
        calls = []

        class FakeAdapter:
            async def call(self, prompt, *, work_dir=None, on_progress=None, **kw):
                calls.append(("call", prompt, work_dir))
                return AdapterResult(text=f"reply: {prompt}", session_id="s1")

        worker.adapter = FakeAdapter()
        return worker, calls

    def test_adapter_not_called_when_lease_identity_bad(self):
        worker, calls = self._make_worker()
        reported = []

        async def mock_report(**kw):
            reported.append(kw)

        worker.coordinate.report_job = mock_report

        result = _claim_result(include_lease=True, lease_overrides={"agent_id": "other-agent"})
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(result))
        finally:
            loop.close()

        self.assertEqual(len(calls), 0)
        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0]["status"], "failed")
        self.assertEqual(reported[0]["attempt_token"], 1)
        self.assertIsNone(reported[0].get("lease_id"))

    def test_adapter_called_and_reports_lease_id_when_lease_valid(self):
        worker, calls = self._make_worker()
        reported = []

        async def mock_report(**kw):
            reported.append(kw)

        worker.coordinate.report_job = mock_report

        result = _claim_result(include_lease=True)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(result))
        finally:
            loop.close()

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0]["status"], "done")
        self.assertEqual(reported[0]["lease_id"], "039bdcda-de94-4bbd-9f26-13f39b2d33bf")

    def test_legacy_untyped_job_runs_without_lease(self):
        worker, calls = self._make_worker()
        reported = []

        async def mock_report(**kw):
            reported.append(kw)

        worker.coordinate.report_job = mock_report

        result = _claim_result(include_lease=False)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(result))
        finally:
            loop.close()

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0]["status"], "done")
        self.assertIsNone(reported[0].get("lease_id"))


class WorkerRenewalSupervisorTests(unittest.TestCase):
    """P9-3B: dedicated renewal supervisor cancels provider on lease loss."""

    def _make_worker(self):
        worker = AgentdWorker(_config())
        calls = []

        class FakeAdapter:
            async def call(self, prompt, *, work_dir=None, on_progress=None, **kw):
                calls.append(("call", prompt, work_dir))
                await asyncio.sleep(10)
                return AdapterResult(text="slow reply", session_id="s1")

        worker.adapter = FakeAdapter()
        return worker, calls

    def test_renewal_failure_cancels_provider_and_does_not_report_done(self):
        worker, calls = self._make_worker()
        reported = []

        async def mock_report(**kw):
            reported.append(kw)

        async def failing_renew(**kw):
            raise CoordinateRuntimeError("lease rejected")

        worker.coordinate.report_job = mock_report
        worker.coordinate.renew_lease = failing_renew

        result = _claim_result(
            include_lease=True,
            lease_overrides={
                "server_now": "2026-07-14T12:00:00Z",
                "expires_at": "2026-07-14T12:00:30Z",
                "ttl_seconds": 30,
                "renew_interval_seconds": 1,
            },
        )

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(asyncio.wait_for(worker._process_job(result), timeout=5))
        except asyncio.TimeoutError:
            pass
        finally:
            loop.close()

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(reported), 0)

    def test_provider_completes_before_deadline(self):
        worker, calls = self._make_worker()
        reported = []

        async def mock_report(**kw):
            reported.append(kw)

        renew_count = 0

        async def successful_renew(**kw):
            nonlocal renew_count
            renew_count += 1
            return {
                "result": {
                    "expires_at": "2026-07-14T12:05:00Z",
                    "server_now": "2026-07-14T12:00:00Z",
                }
            }

        worker.coordinate.report_job = mock_report
        worker.coordinate.renew_lease = successful_renew

        class FastAdapter:
            async def call(self, prompt, *, work_dir=None, on_progress=None, **kw):
                calls.append(("call", prompt, work_dir))
                return AdapterResult(text="fast reply", session_id="s1")

        worker.adapter = FastAdapter()

        result = _claim_result(
            include_lease=True,
            lease_overrides={
                "server_now": "2026-07-14T12:00:00Z",
                "expires_at": "2026-07-14T12:00:30Z",
                "ttl_seconds": 30,
                "renew_interval_seconds": 10,
            },
        )

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker._process_job(result))
        finally:
            loop.close()

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0]["status"], "done")
        self.assertEqual(reported[0]["lease_id"], "039bdcda-de94-4bbd-9f26-13f39b2d33bf")


if __name__ == "__main__":
    unittest.main()
