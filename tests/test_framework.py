import json
import tempfile
import unittest
import tomllib
from pathlib import Path

from mindwell.config import DEFAULT_CONFIG
from mindwell.coordinator import CoordinationError, Coordinator
from mindwell.engine import (assemble_context, build, chunks_for, compact_evidence,
                             frontmatter, intent, retrieve, rrf)
from mindwell.scaffold import init_vault
from mindwell.uncertainty import scan
from mindwell.advisor import recommend
from mindwell import __version__


class FrameworkTests(unittest.TestCase):
    def test_runtime_and_package_versions_match(self):
        project = Path(__file__).parents[1]
        package_version = tomllib.loads((project / "pyproject.toml").read_text())["project"]["version"]
        self.assertEqual(package_version, __version__)

    def test_scaffold_contains_contract_and_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, agent_name="Nova")
            self.assertTrue((vault / "AGENTS.md").exists())
            self.assertIn("# Nova", (vault / "AGENT.md").read_text())
            self.assertEqual("qwen3-embedding:0.6b",
                             json.loads((vault / "config/mindwell.json").read_text())["embedding_model"])
            self.assertEqual("lexical",
                             json.loads((vault / "config/mindwell.json").read_text())["retrieval_provider"])
            installation = json.loads((vault / "config/installation.json").read_text())
            self.assertEqual(__version__, installation["mindwell_version"])

    def test_lexical_setup_indexes_and_retrieves_without_embedding(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp); init_vault(vault)
            project = vault / "wiki" / "projects" / "atlas.md"
            project.parent.mkdir(parents=True, exist_ok=True)
            project.write_text("# Atlas migration\n\nMorgan Reed owns the Atlas migration.")
            stats = build(vault, rebuild=True)
            result = retrieve(vault, "Who owns the Atlas migration?")
            self.assertGreater(stats["chunks"], 0)
            self.assertEqual("lexical", result["provider"])
            self.assertIn("wiki/projects/atlas.md", [item["path"] for item in result["results"]])

    def test_retrieve_refreshes_changed_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp); init_vault(vault)
            build(vault, rebuild=True)
            note = vault / "projects" / "new-work.md"
            note.write_text("# Cedar\n\nAvery owns the Cedar forecast.")
            result = retrieve(vault, "Who owns the Cedar forecast?")
            self.assertEqual(1, result["index_refresh"]["changed_files"])
            self.assertIn("projects/new-work.md", [item["path"] for item in result["results"]])

    def test_personal_ops_profile_has_habits_recipes_and_automation_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops", automations="core",
                       timezone="America/Los_Angeles")
            self.assertIn("folder-capable", (vault / "START-HERE.md").read_text())
            self.assertTrue((vault / "recipes/batch-excel-analysis.md").exists())
            plan = json.loads((vault / "automations/plan.json").read_text())
            self.assertEqual("America/Los_Angeles", plan["timezone"])
            self.assertEqual(4, len(plan["tasks"]))
            self.assertEqual("never_without_confirmation",
                             plan["safety"]["external_sends"])
            plan_path = vault / "automations/plan.json"
            plan_path.write_text('{"customized": true}\n')
            init_vault(vault, profile="personal-ops", automations="core")
            self.assertEqual({"customized": True}, json.loads(plan_path.read_text()))

    def test_advisor_chooses_personal_ops_for_new_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "SecondBrain"
            advice = recommend(destination)
            self.assertEqual("personal-ops", advice["recommendation"]["track"])
            self.assertEqual("lexical", advice["recommendation"]["provider"])
            self.assertFalse(advice["recommendation"]["requires_admin"])
            self.assertIn("--profile personal-ops", advice["commands"][0])

    def test_advisor_detects_existing_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "existing.md").write_text("# Existing")
            advice = recommend(vault)
            self.assertEqual("existing-vault", advice["recommendation"]["track"])
            self.assertTrue(advice["checks"]["destination"]["has_markdown"])
            self.assertTrue(advice["warnings"])

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

    def test_compaction_prefers_query_bearing_evidence(self):
        text = (("Routine background with no useful owner detail. " * 20) +
                "\n\nMorgan Reed owns the Atlas migration and approves cutover.\n\n" +
                ("More unrelated historical background. " * 20))
        compacted = compact_evidence(text, "Who owns the Atlas migration?", 300)
        self.assertIn("Morgan Reed owns the Atlas migration", compacted)
        self.assertLessEqual(len(compacted), 300)

    def test_context_keeps_five_sources_inside_standard_budget(self):
        selected = []
        for index in range(5):
            row = (f"wiki/source-{index}.md", "Current", "relevant fact " * 100,
                   f"Vault note: wiki/source-{index}.md.", "synthesis", "active",
                   "2026-07-12", 4)
            selected.append((.02 - index / 1000, f"chunk-{index}", row))
        context, manifest = assemble_context(selected, "relevant fact", 2500)
        self.assertEqual(5, len(manifest))
        self.assertLessEqual(len(context), 2500)
        self.assertTrue(all(item["path"] in context for item in manifest))

    def test_optimized_context_mode_defaults(self):
        self.assertEqual(2500, DEFAULT_CONFIG["context_modes"]["standard"]["budget_chars"])
        self.assertEqual(5, DEFAULT_CONFIG["context_modes"]["standard"]["chunks"])

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
