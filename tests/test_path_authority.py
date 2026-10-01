import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from mindwell.config import DEFAULT_CONFIG
from mindwell.engine import build, classify, retrieve


class PathAuthorityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.vault = self.root / "vault"
        self.vault.mkdir()
        self.db = self.root / "index.db"
        env = patch.dict("os.environ", {"MINDWELL_INDEX": str(self.db),
                                        "MINDWELL_CACHE": str(self.root / "cache")})
        env.start()
        self.addCleanup(env.stop)

    def write_note(self, path, text):
        note = self.vault / path
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(text, encoding="utf-8")

    def configure(self, **settings):
        path = self.vault / "config" / "mindwell.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings), encoding="utf-8")

    def classes(self):
        with closing(sqlite3.connect(self.db)) as con:
            return dict((path, (kind, authority)) for path, kind, authority in
                        con.execute("SELECT DISTINCT path,source_class,authority FROM chunks"))

    def test_default_and_legacy_paths(self):
        for path in DEFAULT_CONFIG["core_paths"]:
            self.assertEqual(("core", 5), classify(path, {}))
        for path in DEFAULT_CONFIG["current_paths"]:
            self.assertEqual(("current", 5), classify(path, {}))
        self.assertEqual(("core", 5), classify("AGENTS.md", {}))
        self.assertEqual(("core", 5), classify("LOBY.md", {}))

    def test_custom_paths_reach_index(self):
        self.configure(core_paths=["AGENTS.md", "core/profile.md", "memory/long-term.md"],
                       current_paths=["status/live.md"])
        for path in ("AGENTS.md", "core/profile.md", "memory/long-term.md", "status/live.md"):
            self.write_note(path, "# Profile\n\nMorgan prefers brief updates.")
        build(self.vault)
        self.assertEqual({"AGENTS.md": ("core", 5), "core/profile.md": ("core", 5),
                          "memory/long-term.md": ("core", 5), "status/live.md": ("current", 5)},
                         self.classes())

    def test_lists_replace_defaults_and_empty_lists_disable_tiers(self):
        self.assertEqual(("source", 2), classify("MEMORY.md", {}, {"core_paths": []}))
        self.assertEqual(("synthesis", 4), classify("wiki/now.md", {}, {"current_paths": []}))
        self.assertEqual(("source", 2), classify("AGENT.md", {}, {"core_paths": ["profile.md"]}))

    def test_exact_paths_normalize_separators_without_matching_siblings(self):
        config = {"core_paths": ["./core\\profile.md"], "current_paths": []}
        self.assertEqual(("core", 5), classify("core/profile.md", {}, config))
        self.assertEqual(("source", 2), classify("other/core/profile.md", {}, config))
        self.assertEqual(("source", 2), classify("core/profile.md.extra.md", {}, config))

    def test_core_wins_overlap(self):
        config = {"core_paths": ["profile.md"], "current_paths": ["profile.md"]}
        self.assertEqual(("core", 5), classify("profile.md", {}, config))

    def test_other_source_classes_stay_unchanged(self):
        for path, expected in {"projects/active/atlas.md": ("project", 5),
                               "wiki/projects/atlas.md": ("project", 5),
                               "people/morgan.md": ("people", 4),
                               "wiki/rules.md": ("synthesis", 4),
                               "daily/today.md": ("operating", 3),
                               "meetings/brief.md": ("operating", 3),
                               "archive/old.md": ("historical", 1),
                               "notes/raw.md": ("source", 2)}.items():
            with self.subTest(path=path):
                self.assertEqual(expected, classify(path, {}))

    def test_config_changes_refresh_unchanged_notes_without_embedding(self):
        self.write_note("core/profile.md", "# Profile\n\nMorgan prefers brief updates.")
        build(self.vault)
        self.assertEqual(("source", 2), self.classes()["core/profile.md"])
        with closing(sqlite3.connect(self.db)) as con, con:
            # Simulate an existing semantic cache; the policy refresh must retain it.
            con.execute("UPDATE meta SET model='ollama:fixture'")
            con.execute("UPDATE chunks SET dim=1,vec=?", (b"fixture-vector",))
            before = con.execute("SELECT id,body,prefix,dim,vec FROM chunks").fetchall()
        self.configure(core_paths=["core/profile.md"], retrieval_provider="ollama",
                       embedding_model="fixture")
        with patch("mindwell.engine.embed", side_effect=AssertionError("must reuse embeddings")):
            self.assertEqual(0, build(self.vault)["changed_files"])
        self.assertEqual(("core", 5), self.classes()["core/profile.md"])
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(before, con.execute("SELECT id,body,prefix,dim,vec FROM chunks").fetchall())
        self.configure(core_paths=[], current_paths=["core/profile.md"],
                       retrieval_provider="ollama", embedding_model="fixture")
        build(self.vault)
        self.assertEqual(("current", 5), self.classes()["core/profile.md"])
        self.configure(core_paths=[], current_paths=[], retrieval_provider="ollama",
                       embedding_model="fixture")
        build(self.vault)
        self.assertEqual(("source", 2), self.classes()["core/profile.md"])

    def test_existing_default_cache_is_reclassified_on_refresh(self):
        self.write_note("AGENTS.md", "# Agent rules\n\nPreserve source notes.")
        build(self.vault)
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE chunks SET source_class='source',authority=2")
        build(self.vault)
        self.assertEqual(("core", 5), self.classes()["AGENTS.md"])

    def test_custom_authority_changes_ranking_for_matching_evidence(self):
        text = "# Profile\n\nMorgan timezone communication style: UTC, brief updates."
        self.write_note("core/profile.md", text)
        self.write_note("logs/monthly.md", text)
        build(self.vault)
        self.configure(core_paths=["core/profile.md"])
        result = retrieve(self.vault, "Morgan timezone communication style")
        self.assertEqual("core/profile.md", result["results"][0]["path"])
        self.assertEqual(("core", 5), self.classes()["core/profile.md"])


if __name__ == "__main__":
    unittest.main()
