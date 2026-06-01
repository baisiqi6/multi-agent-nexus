import unittest

from discord_nexus.sessions.scope import (
    channel_scope,
    describe_scope,
    legacy_scope_for_channel_id,
    scope_for_channel_id,
    task_scope,
    thread_scope,
)


class TestSessionScopeHelpers(unittest.TestCase):
    def test_channel_scope_key(self):
        self.assertEqual(channel_scope(123), "channel:123")
        self.assertEqual(scope_for_channel_id(123), "channel:123")

    def test_thread_scope_key(self):
        self.assertEqual(thread_scope(456), "thread:456")
        self.assertEqual(scope_for_channel_id(456, is_thread=True), "thread:456")

    def test_task_scope_key(self):
        self.assertEqual(
            task_scope("discord-nexus", "phase-5.2"),
            "task:discord-nexus:phase-5.2",
        )

    def test_legacy_scope_key(self):
        self.assertEqual(legacy_scope_for_channel_id(123), "123")

    def test_describes_scope_type(self):
        self.assertEqual(describe_scope("channel:123").label, "channel scope")
        self.assertEqual(describe_scope("thread:456").label, "thread scope")
        self.assertEqual(
            describe_scope("task:discord-nexus:phase-5.2").label,
            "task scope",
        )
        self.assertEqual(describe_scope("123").label, "legacy channel scope")


if __name__ == "__main__":
    unittest.main()
