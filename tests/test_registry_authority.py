"""Tests for the registry authority projection/parity verifier."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from coordinate.agent_registry import parse_agents_toml
from multinexus.registry_authority import (
    AuthorityError,
    canonical_hash,
    load_authority,
    project_runtime_roster,
    verify_parity,
)


class WriteFileMixin:
    def _write(self, content: str, suffix: str = ".toml") -> Path:
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, mode="w", delete=False)
        tmp.write(content)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return Path(tmp.name)


class CanonicalHashTests(unittest.TestCase, WriteFileMixin):
    def test_matches_coordinate_v10_contract(self):
        """MultiNexus canonical SHA-256 must equal Coordinate's canonical hash."""
        authority = """
[registry]
id = "multinexus.discord"
version = 1

[[agents]]
id = "mac-claude"
display_name = "Mac Claude"
discord_user_id = "1507329791982833775"

[[external_agents]]
id = "mac-openclaw"
display_name = "小龙虾"
discord_user_id = "1503023508836450477"
"""
        path = self._write(authority)
        mn_entries = load_authority(path).entries
        mn_hash = canonical_hash(mn_entries)
        coord_result = parse_agents_toml(path)
        self.assertEqual(mn_hash, coord_result.source.source_hash)
        self.assertTrue(mn_hash)

    def test_hash_excludes_source_and_secrets(self):
        base = """
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
"""
        path1 = self._write(base)
        path2 = self._write(base.replace('id = "x"', 'id = "y"'))
        self.assertEqual(
            canonical_hash(load_authority(path1).entries),
            canonical_hash(load_authority(path2).entries),
        )


class AuthoritySchemaTests(unittest.TestCase, WriteFileMixin):
    def test_valid_authority_loads(self):
        path = self._write("""
[registry]
id = "multinexus.discord"
version = 1

[[agents]]
id = "a"
display_name = "A"
discord_user_id = "100000000000000001"

[[external_agents]]
id = "b"
discord_user_id = "100000000000000002"
""")
        auth = load_authority(path)
        self.assertEqual(auth.source_id, "multinexus.discord")
        self.assertEqual(auth.source_version, 1)
        self.assertEqual(len(auth.entries), 2)

    def test_missing_registry_rejected(self):
        path = self._write("""
[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        with self.assertRaisesRegex(AuthorityError, "missing \\[registry\\]"):
            load_authority(path)

    def test_unknown_root_key_rejected(self):
        path = self._write("""
[registry]
id = "x"
version = 1

[token]
value = "secret"

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        with self.assertRaisesRegex(AuthorityError, "unknown root keys"):
            load_authority(path)

    def test_unknown_registry_key_rejected(self):
        path = self._write("""
[registry]
id = "x"
version = 1
hash = "abc"

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        with self.assertRaisesRegex(AuthorityError, "unknown \\[registry\\] keys"):
            load_authority(path)

    def test_unknown_entry_key_rejected(self):
        for field, value in (
            ("token", '"secret"'),
            ("token_env", '"X"'),
            ("system_prompt", '"hi"'),
            ("work_dir", '"/x"'),
            ("channels", "[1]"),
            ("webhook", '"http://x"'),
            ("executable", '"x"'),
        ):
            path = self._write(f"""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
{field} = {value}
""")
            with self.subTest(field=field):
                with self.assertRaisesRegex(AuthorityError, "unknown keys in agents entry"):
                    load_authority(path)

    def test_authority_discord_id_must_be_quoted_string(self):
        path = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = 100000000000000001
""")
        with self.assertRaisesRegex(AuthorityError, "must be a quoted string"):
            load_authority(path)

    def test_invalid_discord_user_id_values(self):
        values = [
            '""',
            '"0"',
            '"-1"',
            '"12a"',
            '"１２"',
            '"12 34"',
            "12.5",
        ]
        for value in values:
            path = self._write(f"""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = {value}
""")
            with self.subTest(value=value):
                with self.assertRaisesRegex(AuthorityError, "invalid discord_user_id"):
                    load_authority(path)

    def test_version_must_be_non_negative_integer(self):
        for version in ("true", "1.5", '"1"', -1):
            path = self._write(f"""
[registry]
id = "x"
version = {version}

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
            with self.subTest(version=version):
                with self.assertRaisesRegex(AuthorityError, "version must be a non-negative integer"):
                    load_authority(path)

    def test_duplicate_id_rejected(self):
        path = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"

[[external_agents]]
id = "a"
discord_user_id = "100000000000000002"
""")
        with self.assertRaisesRegex(AuthorityError, "duplicate agent id 'a'"):
            load_authority(path)

    def test_duplicate_discord_id_rejected(self):
        path = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"

[[agents]]
id = "b"
discord_user_id = "100000000000000001"
""")
        with self.assertRaisesRegex(AuthorityError, "duplicate discord_user_id"):
            load_authority(path)

    def test_missing_id_rejected(self):
        path = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
discord_user_id = "100000000000000001"
""")
        with self.assertRaisesRegex(AuthorityError, "missing 'id'"):
            load_authority(path)

    def test_missing_discord_user_id_rejected(self):
        path = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
display_name = "A"
""")
        with self.assertRaisesRegex(AuthorityError, "missing discord_user_id"):
            load_authority(path)

    def test_display_name_defaults_to_id(self):
        path = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        entry = load_authority(path).entries[0]
        self.assertEqual(entry.display_name, "a")


class RuntimeProjectionTests(unittest.TestCase, WriteFileMixin):
    def test_runtime_integer_id_equivalent_to_string(self):
        path = self._write("""
[[agents]]
id = "a"
display_name = "A"
discord_user_id = 100000000000000001

[[external_agents]]
id = "b"
discord_user_id = "100000000000000002"
""")
        entries, errors = project_runtime_roster(path)
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].discord_user_id, "100000000000000001")

    def test_runtime_extra_fields_ignored(self):
        path = self._write("""
[defaults]
token_env = "SECRET_ENV"
system_prompt = "hi"

[[agents]]
id = "a"
display_name = "A"
discord_user_id = "100000000000000001"
token_env = "OTHER_SECRET"
work_dir = "/secret/path"
channels = [1, 2]
""")
        entries, errors = project_runtime_roster(path)
        self.assertEqual(errors, [])
        self.assertEqual(entries[0].id, "a")

    def test_runtime_missing_id_reported(self):
        path = self._write("""
[[agents]]
discord_user_id = "100000000000000001"
""")
        entries, errors = project_runtime_roster(path)
        self.assertEqual(entries, [])
        self.assertTrue(any("missing 'id'" in e for e in errors))

    def test_runtime_missing_discord_id_reported(self):
        path = self._write("""
[[agents]]
id = "a"
display_name = "A"
""")
        entries, errors = project_runtime_roster(path)
        self.assertEqual(entries, [])
        self.assertTrue(any("missing discord_user_id" in e for e in errors))

    def test_runtime_duplicate_id_reported(self):
        path = self._write("""
[[agents]]
id = "a"
discord_user_id = "100000000000000001"

[[agents]]
id = "a"
discord_user_id = "100000000000000002"
""")
        entries, errors = project_runtime_roster(path)
        self.assertTrue(any("duplicate agent id" in e for e in errors))


class ParityTests(unittest.TestCase, WriteFileMixin):
    def test_exact_parity_ok(self):
        authority = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
display_name = "A"
discord_user_id = "100000000000000001"
""")
        runtime = self._write("""
[[agents]]
id = "a"
display_name = "A"
discord_user_id = "100000000000000001"
token_env = "SECRET"
""")
        result = verify_parity(authority, runtime)
        self.assertTrue(result.ok)
        self.assertEqual(result.authority_count, 1)
        self.assertEqual(result.runtime_count, 1)

    def test_added_identity_reported(self):
        authority = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"

[[agents]]
id = "b"
discord_user_id = "100000000000000002"
""")
        runtime = self._write("""
[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        result = verify_parity(authority, runtime)
        self.assertFalse(result.ok)
        self.assertTrue(any(d["id"] == "b" and d["status"] == "added" for d in result.diff))

    def test_removed_identity_reported(self):
        authority = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        runtime = self._write("""
[[agents]]
id = "a"
discord_user_id = "100000000000000001"

[[agents]]
id = "b"
discord_user_id = "100000000000000002"
""")
        result = verify_parity(authority, runtime)
        self.assertFalse(result.ok)
        self.assertTrue(any(d["id"] == "b" and d["status"] == "removed" for d in result.diff))

    def test_changed_identity_reported(self):
        authority = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
display_name = "A"
discord_user_id = "100000000000000001"
""")
        runtime = self._write("""
[[agents]]
id = "a"
display_name = "B"
discord_user_id = "100000000000000001"
""")
        result = verify_parity(authority, runtime)
        self.assertFalse(result.ok)
        self.assertTrue(
            any(d["id"] == "a" and d["status"] == "changed" and "display_name" in d["fields"]
                for d in result.diff)
        )

    def test_kind_change_reported(self):
        authority = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        runtime = self._write("""
[[external_agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        result = verify_parity(authority, runtime)
        self.assertFalse(result.ok)
        self.assertTrue(
            any(d["id"] == "a" and d["status"] == "changed" and "agent_type" in d["fields"]
                for d in result.diff)
        )

    def test_authority_error_redacts_secret_value(self):
        authority = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
token_env = "SUPER_SECRET_TOKEN"
""")
        runtime = self._write("""
[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        result = verify_parity(authority, runtime)
        self.assertFalse(result.ok)
        output = json.dumps(result.to_dict())
        self.assertNotIn("SUPER_SECRET_TOKEN", output)

    def test_runtime_secret_not_in_output(self):
        authority = self._write("""
[registry]
id = "x"
version = 1

[[agents]]
id = "a"
discord_user_id = "100000000000000001"
""")
        runtime = self._write("""
[[agents]]
id = "a"
discord_user_id = "100000000000000001"
token_env = "RUNTIME_SECRET"
""")
        result = verify_parity(authority, runtime)
        self.assertTrue(result.ok)
        output = json.dumps(result.to_dict())
        self.assertNotIn("RUNTIME_SECRET", output)
        self.assertNotIn("token_env", output)


if __name__ == "__main__":
    unittest.main()
