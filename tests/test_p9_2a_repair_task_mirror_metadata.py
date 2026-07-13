from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "docs/project-harness/tasks/p9-2a-executor-identity-registry"
    / "repair_task_mirror_metadata.py"
)
SPEC = importlib.util.spec_from_file_location("p9_2a_mirror_repair", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RepairTaskMirrorMetadataTests(unittest.TestCase):
    workspace_id = "discord-nexus"
    task_id = "p9-2a-executor-identity-registry"
    operation_id = "62175918-ce07-4da5-8bf4-03b9784fb64e"
    record_event_id = "a73556cf-5960-4542-b1c8-73bc771ed109"

    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE events (
              id TEXT PRIMARY KEY, workspace_id TEXT, event_type TEXT NOT NULL,
              actor TEXT NOT NULL, target TEXT, task_id TEXT, causation_id TEXT,
              idempotency_key TEXT NOT NULL UNIQUE, payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE tasks (
              workspace_id TEXT NOT NULL, task_id TEXT NOT NULL, phase TEXT,
              owner TEXT, branch TEXT, pr TEXT, last_event_id TEXT,
              payload_json TEXT NOT NULL, updated_at TEXT NOT NULL,
              PRIMARY KEY (workspace_id, task_id)
            );
            CREATE TABLE split_operations (
              operation_id TEXT PRIMARY KEY, contract_version INTEGER NOT NULL,
              operation_kind TEXT NOT NULL, workspace_id TEXT NOT NULL,
              target_kind TEXT NOT NULL, target_id TEXT NOT NULL,
              source_kind TEXT, source_id TEXT, input_fingerprint TEXT NOT NULL,
              before_fingerprint TEXT NOT NULL, after_fingerprint TEXT NOT NULL,
              status TEXT NOT NULL, record_event_id TEXT, created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        self.meta = {
            "contract_version": 1,
            "operation_id": self.operation_id,
            "operation_kind": "task.create",
            "input_fingerprint": "1" * 64,
            "before_fingerprint": "2" * 64,
            "after_fingerprint": "3" * 64,
        }
        self.conn.execute(
            """INSERT INTO split_operations VALUES
               (?, 1, 'task.create', ?, 'checklist_task', ?, NULL, NULL,
                ?, ?, ?, 'record_applied', ?, '2026-07-13T00:00:00Z',
                '2026-07-13T00:00:00Z')""",
            (
                self.operation_id,
                self.workspace_id,
                self.task_id,
                self.meta["input_fingerprint"],
                self.meta["before_fingerprint"],
                self.meta["after_fingerprint"],
                self.record_event_id,
            ),
        )
        self.conn.execute(
            """INSERT INTO events VALUES
               (?, ?, 'plan.ready', 'worker', ?, ?, NULL, ?, ?,
                '2026-07-13T00:00:00Z')""",
            (
                self.record_event_id,
                self.workspace_id,
                self.task_id,
                self.task_id,
                "record-event-key",
                self._json({"phase": "ready", "split_operation": self.meta}),
            ),
        )
        self.original_payload = {
            "id": self.task_id,
            "title": "P9-2A",
            "unrelated": {"keep": True},
        }
        self.original_columns = (
            "ready",
            "operator",
            "agents/mac-omp/p9-2a",
            "https://example.invalid/pr/1",
            "last-event",
            "2026-07-13T01:02:03Z",
        )
        self._insert_task(self.original_payload)
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    def _insert_task(self, payload: object) -> None:
        self.conn.execute(
            """INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                self.workspace_id,
                self.task_id,
                *self.original_columns[:5],
                self._json(payload),
                self.original_columns[5],
            ),
        )

    def _replace_payload(self, payload: object) -> None:
        self.conn.execute(
            "UPDATE tasks SET payload_json = ? WHERE workspace_id = ? AND task_id = ?",
            (self._json(payload), self.workspace_id, self.task_id),
        )
        self.conn.commit()

    def _run(self) -> dict[str, object]:
        return MODULE.repair_task_mirror_metadata(
            self.conn,
            workspace_id=self.workspace_id,
            task_id=self.task_id,
            operation_id=self.operation_id,
        )

    def _task(self) -> sqlite3.Row:
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE workspace_id = ? AND task_id = ?",
            (self.workspace_id, self.task_id),
        ).fetchone()
        assert row is not None
        return row

    def test_repairs_atomically_and_preserves_every_other_task_column(self) -> None:
        before = self._task()
        result = self._run()
        after = self._task()

        self.assertEqual(result["status"], "repaired")
        self.assertIsNotNone(result["repair_event_id"])
        for column in (
            "phase", "owner", "branch", "pr", "last_event_id", "updated_at"
        ):
            self.assertEqual(after[column], before[column])
        payload = json.loads(after["payload_json"])
        self.assertEqual(payload["phase"], "ready")
        self.assertEqual(payload["split_operation"], self.meta)
        self.assertEqual(payload["unrelated"], {"keep": True})
        event = self.conn.execute(
            "SELECT * FROM events WHERE id = ?", (result["repair_event_id"],)
        ).fetchone()
        self.assertEqual(event["event_type"], "projection.repaired")
        self.assertEqual(event["actor"], "codex-operator")
        self.assertEqual(event["causation_id"], self.record_event_id)
        audit = json.loads(event["payload_json"])
        self.assertEqual(audit["repaired_fields"], ["phase", "split_operation"])
        self.assertEqual(audit["restored_phase"], "ready")
        self.assertNotIn("plan_doc", audit)

    def test_exact_retry_is_zero_write_and_returns_original_before_hash(self) -> None:
        first = self._run()
        task_after_first = dict(self._task())
        event_after_first = dict(
            self.conn.execute(
                "SELECT * FROM events WHERE id = ?", (first["repair_event_id"],)
            ).fetchone()
        )
        second = self._run()

        self.assertEqual(second["status"], "already_repaired")
        self.assertEqual(second["repair_event_id"], first["repair_event_id"])
        self.assertEqual(
            second["before_payload_sha256"], first["before_payload_sha256"]
        )
        self.assertEqual(dict(self._task()), task_after_first)
        self.assertEqual(
            dict(
                self.conn.execute(
                    "SELECT * FROM events WHERE id = ?",
                    (first["repair_event_id"],),
                ).fetchone()
            ),
            event_after_first,
        )

    def test_preexisting_exact_metadata_without_repair_event_is_zero_write(self) -> None:
        payload = dict(self.original_payload)
        payload["phase"] = "ready"
        payload["split_operation"] = self.meta
        self._replace_payload(payload)
        before = dict(self._task())

        result = self._run()

        self.assertEqual(result["status"], "already_repaired")
        self.assertIsNone(result["repair_event_id"])
        self.assertEqual(dict(self._task()), before)
        self.assertEqual(
            self.conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'projection.repaired'"
            ).fetchone()[0],
            0,
        )

    def test_null_or_conflicting_mirror_metadata_fails_closed(self) -> None:
        for value in (None, {**self.meta, "after_fingerprint": "4" * 64}):
            with self.subTest(value=value):
                payload = dict(self.original_payload)
                payload["split_operation"] = value
                self._replace_payload(payload)
                before = dict(self._task())
                with self.assertRaises(MODULE.RepairError):
                    self._run()
                self.assertEqual(dict(self._task()), before)
                self.assertEqual(
                    self.conn.execute(
                        "SELECT COUNT(*) FROM events WHERE event_type = 'projection.repaired'"
                    ).fetchone()[0],
                    0,
                )

    def test_record_event_split_metadata_requires_exact_six_keys(self) -> None:
        forged = {**self.meta, "extra": "not-allowed"}
        self.conn.execute(
            "UPDATE events SET payload_json = ? WHERE id = ?",
            (
                self._json({"phase": "ready", "split_operation": forged}),
                self.record_event_id,
            ),
        )
        self.conn.commit()

        with self.assertRaisesRegex(
            MODULE.RepairError, "keys do not match the v1 contract"
        ):
            self._run()
        self.assertNotIn("split_operation", json.loads(self._task()["payload_json"]))

    def test_missing_mirror_with_preexisting_repair_event_fails_closed(self) -> None:
        key = MODULE._build_idempotency_key(
            self.workspace_id, self.task_id, self.operation_id
        )
        self.conn.execute(
            """INSERT INTO events VALUES
               (?, ?, 'projection.repaired', 'codex-operator', ?, ?, ?, ?, '{}',
                '2026-07-13T00:00:00Z')""",
            (
                MODULE._build_repair_event_id(key),
                self.workspace_id,
                f"task:{self.task_id}",
                self.task_id,
                self.record_event_id,
                key,
            ),
        )
        self.conn.commit()

        with self.assertRaisesRegex(
            MODULE.RepairError, "exists while mirror metadata is missing"
        ):
            self._run()
        self.assertNotIn("split_operation", json.loads(self._task()["payload_json"]))

    def test_exact_mirror_with_conflicting_repair_event_fails_closed(self) -> None:
        first = self._run()
        self.conn.execute(
            "UPDATE events SET actor = 'forged' WHERE id = ?",
            (first["repair_event_id"],),
        )
        self.conn.commit()
        before = dict(self._task())

        with self.assertRaisesRegex(MODULE.RepairError, "differs in actor"):
            self._run()
        self.assertEqual(dict(self._task()), before)

    def test_repairs_only_split_operation_when_phase_is_exact(self) -> None:
        payload = dict(self.original_payload)
        payload["phase"] = "ready"
        self._replace_payload(payload)

        result = self._run()
        repaired = json.loads(self._task()["payload_json"])
        event = self.conn.execute(
            "SELECT payload_json FROM events WHERE id = ?",
            (result["repair_event_id"],),
        ).fetchone()

        self.assertEqual(repaired["phase"], "ready")
        self.assertEqual(repaired["split_operation"], self.meta)
        self.assertEqual(
            json.loads(event["payload_json"])["repaired_fields"],
            ["split_operation"],
        )

    def test_repairs_only_phase_when_split_operation_is_exact(self) -> None:
        payload = dict(self.original_payload)
        payload["split_operation"] = self.meta
        self._replace_payload(payload)

        result = self._run()
        repaired = json.loads(self._task()["payload_json"])
        event = self.conn.execute(
            "SELECT payload_json FROM events WHERE id = ?",
            (result["repair_event_id"],),
        ).fetchone()

        self.assertEqual(repaired["phase"], "ready")
        self.assertEqual(repaired["split_operation"], self.meta)
        self.assertEqual(
            json.loads(event["payload_json"])["repaired_fields"], ["phase"]
        )

    def test_record_event_and_task_column_phase_must_agree(self) -> None:
        self.conn.execute(
            "UPDATE tasks SET phase = 'accepted' WHERE workspace_id = ? AND task_id = ?",
            (self.workspace_id, self.task_id),
        )
        self.conn.commit()
        before = dict(self._task())

        with self.assertRaisesRegex(
            MODULE.RepairError, "column does not match"
        ):
            self._run()
        self.assertEqual(dict(self._task()), before)
        self.assertEqual(
            self.conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'projection.repaired'"
            ).fetchone()[0],
            0,
        )

    def test_payload_phase_null_wrong_type_or_conflict_fails_closed(self) -> None:
        for value in (None, 7, "accepted"):
            with self.subTest(value=value):
                payload = dict(self.original_payload)
                payload["phase"] = value
                self._replace_payload(payload)
                before = dict(self._task())
                with self.assertRaisesRegex(MODULE.RepairError, "phase conflicts"):
                    self._run()
                self.assertEqual(dict(self._task()), before)
                self.assertEqual(
                    self.conn.execute(
                        "SELECT COUNT(*) FROM events WHERE event_type = 'projection.repaired'"
                    ).fetchone()[0],
                    0,
                )


if __name__ == "__main__":
    unittest.main()
