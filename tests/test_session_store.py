import os
import tempfile
import unittest

from discord_nexus.sessions.store import SessionStore


class TestSessionStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(self.tmpdir, "test_sessions.sqlite3")
        self.store = SessionStore(db_path)

    def test_get_returns_none_when_empty(self):
        result = self.store.get(scope_id="ch1", agent_id="claude")
        self.assertIsNone(result)

    def test_upsert_and_get(self):
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-abc",
            work_dir="/tmp/project",
        )
        result = self.store.get(scope_id="ch1", agent_id="claude")
        self.assertIsNotNone(result)
        self.assertEqual(result["session_id"], "sess-abc")
        self.assertEqual(result["adapter"], "claude")
        self.assertEqual(result["work_dir"], "/tmp/project")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["turn_count"], 1)

    def test_upsert_increments_turn_count_for_same_session(self):
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-1",
        )
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-1",
        )
        result = self.store.get(scope_id="ch1", agent_id="claude")
        self.assertEqual(result["session_id"], "sess-1")
        self.assertEqual(result["turn_count"], 2)

    def test_upsert_resets_turn_count_for_new_session(self):
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-1",
        )
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-2",
        )
        result = self.store.get(scope_id="ch1", agent_id="claude")
        self.assertEqual(result["session_id"], "sess-2")
        self.assertEqual(result["turn_count"], 1)

    def test_scope_isolation(self):
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-ch1",
        )
        self.store.upsert(
            scope_id="ch2", agent_id="claude",
            adapter="claude", session_id="sess-ch2",
        )
        r1 = self.store.get(scope_id="ch1", agent_id="claude")
        r2 = self.store.get(scope_id="ch2", agent_id="claude")
        self.assertEqual(r1["session_id"], "sess-ch1")
        self.assertEqual(r2["session_id"], "sess-ch2")

    def test_agent_isolation(self):
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-claude",
        )
        self.store.upsert(
            scope_id="ch1", agent_id="codex",
            adapter="codex", session_id="sess-codex",
        )
        r1 = self.store.get(scope_id="ch1", agent_id="claude")
        r2 = self.store.get(scope_id="ch1", agent_id="codex")
        self.assertEqual(r1["session_id"], "sess-claude")
        self.assertEqual(r2["session_id"], "sess-codex")

    def test_mark_stale_then_get_returns_none(self):
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-old",
        )
        self.store.mark_stale(scope_id="ch1", agent_id="claude")
        result = self.store.get(scope_id="ch1", agent_id="claude")
        self.assertIsNone(result)

    def test_upsert_reactivates_stale(self):
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-1",
        )
        self.store.mark_stale(scope_id="ch1", agent_id="claude")
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-2",
        )
        result = self.store.get(scope_id="ch1", agent_id="claude")
        self.assertIsNotNone(result)
        self.assertEqual(result["session_id"], "sess-2")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["turn_count"], 1)

    def test_upsert_same_session_after_stale_resets_turn_count(self):
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-1",
        )
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-1",
        )
        self.store.mark_stale(scope_id="ch1", agent_id="claude")
        self.store.upsert(
            scope_id="ch1", agent_id="claude",
            adapter="claude", session_id="sess-1",
        )
        result = self.store.get(scope_id="ch1", agent_id="claude")
        self.assertEqual(result["session_id"], "sess-1")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["turn_count"], 1)


if __name__ == "__main__":
    unittest.main()
