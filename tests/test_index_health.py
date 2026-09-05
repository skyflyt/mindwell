import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from mindwell.config import index_path
from mindwell.doctor import inspect, inspect_index
from mindwell.engine import build
from mindwell.scaffold import init_vault


class IndexHealthTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        env = patch.dict("os.environ", {"MINDWELL_INDEX": str(self.root / "cache.db"),
                                        "MINDWELL_CACHE": str(self.root / "cache")})
        env.start()
        self.addCleanup(env.stop)
        self.vault = self.root / "vault"
        init_vault(self.vault)
        self.db = index_path(self.vault)

    def test_missing_is_reported_without_creating_database(self):
        result = inspect(self.vault)
        self.assertTrue(result["ready"])  # Runtime can build the missing cache.
        self.assertIn("index", result["warnings"])
        self.assertEqual("missing", result["checks"]["index"]["state"])
        self.assertFalse(self.db.exists())

    def test_zero_byte_and_corrupt_files_are_not_healthy(self):
        for content in (b"", b"not a SQLite database"):
            with self.subTest(content=content):
                self.db.write_bytes(content)
                result = inspect_index(self.db)
                self.assertFalse(result["ok"])
                self.assertEqual("unreadable", result["state"])
                self.assertEqual(content, self.db.read_bytes())

    def test_readable_cache_reports_counts_without_claiming_freshness(self):
        stats = build(self.vault)
        original = self.db.read_bytes()
        result = inspect_index(self.db)
        self.assertTrue(result["ok"])
        self.assertEqual(stats["chunks"], result["chunks"])
        self.assertEqual(stats["files"], result["files"])
        self.assertEqual("not assessed", result["freshness"])
        self.assertEqual(original, self.db.read_bytes())

    def test_empty_schema_is_not_searchable(self):
        build(self.vault)
        with closing(sqlite3.connect(self.db)) as con, con:
            for table in ("chunks", "fts", "meta"):
                con.execute("DELETE FROM " + table)
        self.assertEqual("empty", inspect_index(self.db)["state"])

    def test_missing_fts_entry_warns(self):
        build(self.vault)
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("DELETE FROM fts WHERE rowid=(SELECT min(rowid) FROM fts)")
        result = inspect(self.vault)
        self.assertIn("index", result["warnings"])
        self.assertEqual("inconsistent", result["checks"]["index"]["state"])

    def test_equal_counts_with_wrong_ids_are_not_healthy(self):
        build(self.vault)
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE fts SET id='unrelated' WHERE rowid=(SELECT min(rowid) FROM fts)")
        self.assertEqual("inconsistent", inspect_index(self.db)["state"])


if __name__ == "__main__":
    unittest.main()
