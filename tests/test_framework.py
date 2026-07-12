import json
import tempfile
import unittest
from pathlib import Path

from loby.config import DEFAULT_CONFIG
from loby.coordinator import CoordinationError, Coordinator
from loby.engine import chunks_for, frontmatter, intent, rrf
from loby.scaffold import init_vault
from loby.uncertainty import scan


class FrameworkTests(unittest.TestCase):
    def test_scaffold_contains_contract_and_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault)
            self.assertTrue((vault / "AGENTS.md").exists())
            self.assertEqual("qwen3-embedding:0.6b",
                             json.loads((vault / "config/loby.json").read_text())["embedding_model"])

    def test_chunking_preserves_source_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp); path = vault / "wiki/a.md"; path.parent.mkdir()
            text = "# A\n\n" + "useful paragraph\n\n" * 200
            result = chunks_for(vault, path, text, DEFAULT_CONFIG)
            self.assertGreater(len(result), 1)
            self.assertTrue(all(chunk.path == "wiki/a.md" for chunk in result))

    def test_rrf_rewards_cross_signal_match(self):
        scores = rrf([["shared", "a"], ["shared", "b"]])
        self.assertGreater(scores["shared"], scores["a"])

    def test_intent_distinguishes_history(self):
        self.assertIn("historical", intent("Which completed project did this?"))

    def test_uncertainty_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp); wiki = vault / "wiki"; wiki.mkdir()
            (wiki / "x.md").write_text(
                "> [!gap] Missing owner\n> claim: Owner is unknown.\n> sources: [[source/a]]\n> status: open\n")
            self.assertEqual("Missing owner", scan(vault)[0]["title"])

    def test_stale_replica_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); shared = root / "shared"
            a, b = root / "a", root / "b"
            for vault in (a, b):
                vault.mkdir(); (vault / "state.md").write_text("v1")
            ca = Coordinator(a, root / "local-a", shared, "A")
            cb = Coordinator(b, root / "local-b", shared, "B")
            lease = ca.begin("state.md"); ca.verify(lease)
            (a / "state.md").write_text("v2"); ca.commit(lease)
            with self.assertRaises(CoordinationError): cb.begin("state.md")


if __name__ == "__main__": unittest.main()
