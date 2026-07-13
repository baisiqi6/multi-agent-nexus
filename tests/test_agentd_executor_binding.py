"""Tests for agentd worker integration of the executor binding validator."""
from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from multinexus.adapters.base import AdapterResult
from multinexus.agentd.worker import AgentdWorker
from multinexus.models import AgentConfig


def _config(**overrides):
    defaults = {
        "id": "mac-omp",
        "token": "fake-token",
        "adapter": "omp",
        "context_db_path": str(Path(tempfile.mkdtemp()) / "test.sqlite3"),
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)


def _make_binding(**overrides) -> dict[str, object]:
    fixture = json.loads(
        (Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "executor_binding_v1.json")
        .read_text(encoding="utf-8")
    )
    fixture.update(overrides)
    return fixture


def _make_context(job_id: str = "request:e1") -> dict[str, object]:
    import hashlib

    ctx = {
        "job_id": job_id,
        "workspace_id": "ws",
        "task_id": None,
        "assigned_agent": "mac-omp",
        "host_id": "host1",
        "workspace_path": "/host/ws",
        "worktree_path": "/host/ws",
        "harness_root": "/host/harness",
        "branch": None,
        "session_scope_id": "scope:1",
        "legacy_scope_ids": [],
        "log_handle": {"kind": "coordinate_job", "job_id": job_id, "logs_path": None},
        "contract_version": 1,
    }
    canonical = json.dumps(ctx, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ctx["context_id"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return ctx


def _claim_result(binding: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "claimed": True,
        "job": {
            "id": "request:e1",
            "workspace_id": "ws",
            "assigned_agent": "mac-omp",
            "attempt_count": 1,
            "payload_json": json.dumps(
                {"prompt": "hello", "executor_binding": binding},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
        "attempt_token": 1,
        "execution_context": _make_context(),
    }


class WorkerBindingIntegrationTests(unittest.TestCase):
    def _make_worker(self, config=None):
        worker = AgentdWorker(config or _config())
        worker.adapter = AsyncMock()
        worker.adapter.call = AsyncMock(return_value=AdapterResult(text="ok", session_id="s1"))
        return worker

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_typed_binding_matching_config_executes_adapter(self):
        worker = self._make_worker()
        reported = []

        async def mock_report(*, job_id, agent_id, status, result_json, attempt_token=None):
            reported.append({"status": status, "result_json": result_json})

        worker.coordinate.report_job = mock_report
        self._run(worker._process_job(_claim_result(_make_binding())))

        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0]["status"], "done")
        self.assertIn("executor_binding_id", reported[0]["result_json"])
        self.assertIn("executor_definition_id", reported[0]["result_json"])
        worker.adapter.call.assert_awaited_once()

    def test_legacy_null_binding_executes_adapter(self):
        worker = self._make_worker()
        reported = []

        async def mock_report(*, job_id, agent_id, status, result_json, attempt_token=None):
            reported.append({"status": status, "result_json": result_json})

        worker.coordinate.report_job = mock_report
        self._run(worker._process_job(_claim_result(None)))

        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0]["status"], "done")
        self.assertNotIn("executor_binding_id", reported[0]["result_json"])
        worker.adapter.call.assert_awaited_once()

    def test_adapter_mismatch_fails_closed_before_adapter(self):
        worker = self._make_worker(_config(adapter="claude"))
        reported = []

        async def mock_report(*, job_id, agent_id, status, result_json, attempt_token=None):
            reported.append({"status": status, "result_json": result_json, "attempt_token": attempt_token})

        worker.coordinate.report_job = mock_report
        self._run(worker._process_job(_claim_result(_make_binding())))

        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0]["status"], "failed")
        self.assertIn("executor_binding_mismatch", reported[0]["result_json"]["error"])
        self.assertEqual(reported[0]["attempt_token"], 1)
        worker.adapter.call.assert_not_awaited()

    def test_instance_id_mismatch_fails_closed_before_adapter(self):
        worker = self._make_worker()
        reported = []

        async def mock_report(*, job_id, agent_id, status, result_json, attempt_token=None):
            reported.append({"status": status, "result_json": result_json})

        worker.coordinate.report_job = mock_report
        binding = _make_binding()
        binding["executor_instance_id"] = "other"
        self._run(worker._process_job(_claim_result(binding)))

        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0]["status"], "failed")
        self.assertIn("executor_binding_mismatch", reported[0]["result_json"]["error"])
        worker.adapter.call.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
