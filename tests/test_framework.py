import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from mindwell.config import DEFAULT_CONFIG, load_config
from mindwell.coordinator import CoordinationError, Coordinator
from mindwell.doctor import inspect as doctor_inspect
from mindwell.engine import (assemble_context, build, chunks_for, compact_evidence,
                             frontmatter, intent, retrieve, rrf)
from mindwell import scaffold
from mindwell.scaffold import init_vault, upgrade_vault
from mindwell.uncertainty import scan
from mindwell.advisor import recommend
from mindwell import __version__


class FrameworkTests(unittest.TestCase):
    def setUp(self):
        # Keep every index/backup write inside the test's own tempdir. Without
        # this, each tempdir-vault build() left an orphaned per-vault .db (and
        # upgrade tests a -backups dir) in the REAL user cache
        # (%LOCALAPPDATA%\mindwell / ~/.cache/mindwell) - observed in the field
        # as ~110 abandoned databases on a dev machine.
        self._cache_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        env = patch.dict("os.environ", {"MINDWELL_CACHE": self._cache_dir.name})
        env.start()
        self.addCleanup(self._cache_dir.cleanup)
        self.addCleanup(env.stop)

    def test_runtime_and_package_versions_match(self):
        project = Path(__file__).parents[1]
        text = (project / "pyproject.toml").read_text()
        package_version = re.search(r'^version = "([^"]+)"', text, re.M).group(1)
        self.assertEqual(package_version, __version__)

    def test_python_floor_is_310(self):
        project = Path(__file__).parents[1]
        text = (project / "pyproject.toml").read_text()
        requires = re.search(r'^requires-python = "([^"]+)"', text, re.M).group(1)
        self.assertEqual(">=3.10", requires)
        # sys.version_info is a tuple subclass, so this is the same comparison
        # doctor.py and advisor.py make against the floor.
        self.assertTrue((3, 10) <= sys.version_info)

    def test_ollama_url_env_override_wins_over_vault_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault)
            with patch.dict("os.environ", {"MINDWELL_OLLAMA_URL": "http://example.test:9999"}):
                config = load_config(vault)
            self.assertEqual("http://example.test:9999", config["ollama_url"])

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

    def test_retrieve_degrades_to_lexical_when_ollama_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp); init_vault(vault)
            note = vault / "wiki" / "projects" / "atlas.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text("# Atlas migration\n\nMorgan Reed owns the Atlas migration.")
            build(vault, rebuild=True)  # lexical index already populated

            config_path = vault / "config" / "mindwell.json"
            config = json.loads(config_path.read_text())
            config["retrieval_provider"] = "ollama"
            config["ollama_url"] = "http://127.0.0.1:1"  # refused immediately
            config_path.write_text(json.dumps(config))

            result = retrieve(vault, "Who owns the Atlas migration?")  # must not raise

            self.assertEqual("lexical (ollama unreachable, degraded)", result["provider"])
            self.assertTrue(result["warnings"])
            self.assertTrue(result["guidance"])
            self.assertIn("wiki/projects/atlas.md", [item["path"] for item in result["results"]])

    def test_index_reports_clean_error_when_ollama_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp); init_vault(vault)
            (vault / "note.md").write_text("# Note\n\nSome content.")
            config_path = vault / "config" / "mindwell.json"
            config = json.loads(config_path.read_text())
            config["retrieval_provider"] = "ollama"
            config["ollama_url"] = "http://127.0.0.1:1"
            config_path.write_text(json.dumps(config))

            from mindwell.engine import OllamaUnavailable
            with self.assertRaises(OllamaUnavailable) as ctx:
                build(vault, rebuild=True)
            self.assertIn("http://127.0.0.1:1", str(ctx.exception))

    def test_doctor_skips_ollama_probe_and_is_consistent_for_lexical(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops")
            result = doctor_inspect(vault)
            self.assertTrue(result["checks"]["ollama"]["ok"])
            self.assertTrue(result["checks"]["ollama"].get("skipped"))
            self.assertEqual("lexical", result["mode"])
            self.assertTrue(result["ready"])
            self.assertEqual("ready for zero-dependency lexical retrieval",
                             result["recommendation"])

    def test_doctor_gives_guidance_when_ollama_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops")
            config_path = vault / "config" / "mindwell.json"
            config = json.loads(config_path.read_text())
            config["retrieval_provider"] = "ollama"
            config["ollama_url"] = "http://127.0.0.1:1"
            config_path.write_text(json.dumps(config))

            result = doctor_inspect(vault)
            self.assertEqual("semantic-unreachable", result["mode"])
            self.assertFalse(result["ready"])
            self.assertFalse(result["checks"]["ollama"]["ok"])
            self.assertIn("guidance", result)
            self.assertTrue(any("native" in line.lower() for line in result["guidance"]))

    def test_doctor_warns_on_non_local_ollama_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops")
            config_path = vault / "config" / "mindwell.json"
            config = json.loads(config_path.read_text())
            config["retrieval_provider"] = "ollama"
            # RFC 5737 documentation address: non-localhost (so the security
            # notice fires) without tripping privacy_scan's private-ip pattern.
            config["ollama_url"] = "http://192.0.2.50:11434"
            config_path.write_text(json.dumps(config))

            fake_response = MagicMock()
            fake_response.read.return_value = b'{"models": []}'
            fake_response.__enter__.return_value = fake_response
            fake_response.__exit__.return_value = False

            with patch("mindwell.doctor.urllib.request.urlopen", return_value=fake_response):
                result = doctor_inspect(vault)
            self.assertEqual("semantic", result["mode"])
            self.assertIn("192.0.2.50", result.get("security_notice", ""))

    def test_scaffold_records_environment_and_runner_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, environment="sandbox")
            installation = json.loads((vault / "config/installation.json").read_text())
            self.assertEqual("sandbox", installation["environment"])
            self.assertIn("mindwell.cli", installation["runner_hint"])

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

    def test_private_workspaces_are_optional_and_never_persist_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops", private_workspaces=True)
            registry = json.loads(
                (vault / "config/private-workspaces.json").read_text())
            self.assertFalse(registry["policy"]["persist_locations"])
            self.assertTrue(registry["policy"]["require_location_each_task"])
            self.assertEqual([], registry["workspaces"])
            self.assertTrue(
                (vault / "recipes/private-external-workspaces.md").exists())
            self.assertIn("Never store, infer, search for, derive, or reuse",
                          (vault / "AGENTS.md").read_text())
            installation = json.loads(
                (vault / "config/installation.json").read_text())
            self.assertEqual(["private-workspaces"],
                             installation["optional_features"])

        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops")
            self.assertFalse((vault / "config/private-workspaces.json").exists())

    def test_advisor_chooses_personal_ops_for_new_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "SecondBrain"
            advice = recommend(destination)
            self.assertEqual("personal-ops", advice["recommendation"]["track"])
            self.assertEqual("lexical", advice["recommendation"]["provider"])
            self.assertFalse(advice["recommendation"]["requires_admin"])
            self.assertIn("--profile personal-ops", advice["commands"][0])
            self.assertNotIn("--private-workspaces", " ".join(advice["commands"]))

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

    def test_upgrade_preserves_customized_agents_md_and_reconciles_version(self):
        # Reproduces the reported data-loss scenario: a customized AGENTS.md,
        # an older recorded version, and existing user notes must all survive
        # `mindwell upgrade` byte-identical while the version reconciles.
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            init_vault(vault, profile="personal-ops", automations="core")

            agents_path = vault / "AGENTS.md"
            agents_path.write_text("Always call me Captain. Never touch crm/.\n",
                                   encoding="utf-8")
            notes_path = vault / "daily" / "2026-07-10.md"
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            notes_path.write_text("# Notes\n\nCaptain's log.\n", encoding="utf-8")

            install_path = vault / "config" / "installation.json"
            installation = json.loads(install_path.read_text())
            installation["mindwell_version"] = "0.1.0"
            install_path.write_text(json.dumps(installation))

            before_agents = agents_path.read_bytes()
            before_notes = notes_path.read_bytes()

            result = upgrade_vault(vault)

            self.assertTrue(result["ok"])
            self.assertEqual(before_agents, agents_path.read_bytes())
            self.assertEqual(before_notes, notes_path.read_bytes())
            self.assertEqual("0.1.0", result["from_version"])
            self.assertEqual(__version__, result["to_version"])
            self.assertIn("AGENTS.md", result["files"]["preserved_canonical"])
            self.assertTrue(result["doctor"]["ready"])
            self.assertTrue(result["doctor"]["checks"]["version_match"]["ok"])
            self.assertEqual(__version__,
                             json.loads(install_path.read_text())["mindwell_version"])

    def test_upgrade_is_idempotent_on_an_already_current_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            init_vault(vault, profile="personal-ops", automations="core")
            for _ in range(2):
                result = upgrade_vault(vault)
                self.assertFalse(result["changed"])
                self.assertEqual([], result["files"]["created"])
                self.assertEqual([], result["files"]["updated"])
                self.assertEqual([], result["files"]["preserved_customized"])
                self.assertTrue(result["doctor"]["ready"])

    def test_upgrade_adds_a_missing_managed_scaffold_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            init_vault(vault, profile="personal-ops")
            recipe_path = vault / "recipes" / "weekly-report.md"
            recipe_path.unlink()
            result = upgrade_vault(vault)
            self.assertTrue(recipe_path.exists())
            self.assertIn("recipes/weekly-report.md", result["files"]["created"])

    def test_upgrade_updates_an_untouched_file_matching_the_prior_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            init_vault(vault)
            install_path = vault / "config" / "installation.json"
            installation = json.loads(install_path.read_text())

            memory_path = vault / "MEMORY.md"
            old_template_text = "# Durable memory (old wording)\n"
            memory_path.write_text(old_template_text, encoding="utf-8")
            old_hash = hashlib.sha256(old_template_text.encode("utf-8")).hexdigest()
            installation.setdefault("scaffold_hashes", {})["MEMORY.md"] = old_hash
            install_path.write_text(json.dumps(installation))

            result = upgrade_vault(vault)
            self.assertIn("MEMORY.md", result["files"]["updated"])
            self.assertEqual(scaffold.FILES["MEMORY.md"], memory_path.read_text())

    def test_upgrade_preserves_a_user_modified_non_canonical_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            init_vault(vault)
            memory_path = vault / "MEMORY.md"
            memory_path.write_text("# My own memory format\n", encoding="utf-8")
            result = upgrade_vault(vault)
            self.assertIn("MEMORY.md", result["files"]["preserved_customized"])
            self.assertEqual("# My own memory format\n", memory_path.read_text())

    def test_upgrade_without_prior_init_reports_error_and_suggests_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            (vault / "note.md").write_text("hi", encoding="utf-8")
            result = upgrade_vault(vault)
            self.assertFalse(result["ok"])
            self.assertEqual("no_installation_record", result["error"])
            self.assertIn("mindwell init", result["message"])

    def test_upgrade_dry_run_makes_no_filesystem_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            init_vault(vault)
            memory_path = vault / "MEMORY.md"
            memory_path.write_text("# Custom\n", encoding="utf-8")
            install_path = vault / "config" / "installation.json"
            installation = json.loads(install_path.read_text())
            installation["mindwell_version"] = "0.1.0"
            install_path.write_text(json.dumps(installation))
            before_install = install_path.read_text()

            result = upgrade_vault(vault, dry_run=True)

            self.assertTrue(result["dry_run"])
            self.assertEqual(before_install, install_path.read_text())
            self.assertIsNone(result["backup"])
            self.assertIsNone(result["doctor"])
            self.assertIn("MEMORY.md", result["files"]["preserved_customized"])

    def test_init_force_never_overwrites_customized_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops")
            agents_path = vault / "AGENTS.md"
            agents_path.write_text("Always call me Captain. Never touch crm/.\n",
                                   encoding="utf-8")
            before = agents_path.read_bytes()
            result = init_vault(vault, force=True, profile="personal-ops")
            self.assertEqual(before, agents_path.read_bytes())
            self.assertIn(agents_path, result["preserved_canonical"])

    def test_init_force_preserves_a_user_modified_scaffold_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault)
            memory_path = vault / "MEMORY.md"
            memory_path.write_text("# My own memory\n", encoding="utf-8")
            result = init_vault(vault, force=True)
            self.assertEqual("# My own memory\n", memory_path.read_text())
            self.assertIn(memory_path, result["preserved_customized"])

    def test_init_force_still_repairs_an_untouched_stale_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault)
            memory_path = vault / "MEMORY.md"
            install_path = vault / "config" / "installation.json"
            installation = json.loads(install_path.read_text())
            old_text = "# stale wording\n"
            memory_path.write_text(old_text, encoding="utf-8")
            installation.setdefault("scaffold_hashes", {})["MEMORY.md"] = hashlib.sha256(
                old_text.encode("utf-8")).hexdigest()
            install_path.write_text(json.dumps(installation))
            result = init_vault(vault, force=True)
            self.assertEqual(scaffold.FILES["MEMORY.md"], memory_path.read_text())
            self.assertIn(memory_path, result["updated"])

    def test_recommend_suggests_upgrade_for_a_stale_mindwell_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops")
            install_path = vault / "config" / "installation.json"
            installation = json.loads(install_path.read_text())
            installation["mindwell_version"] = "0.0.1"
            install_path.write_text(json.dumps(installation))

            advice = recommend(vault)
            self.assertTrue(advice["checks"]["installation"]["needs_upgrade"])
            self.assertTrue(any(cmd.startswith("mindwell upgrade") for cmd in advice["commands"]))
            self.assertFalse(any(cmd.startswith("mindwell init") for cmd in advice["commands"]))

    def test_recommend_reports_a_current_mindwell_vault_as_a_safe_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops")
            advice = recommend(vault)
            self.assertFalse(advice["checks"]["installation"]["needs_upgrade"])
            self.assertTrue(any(cmd.startswith("mindwell upgrade") for cmd in advice["commands"]))

    def test_cache_root_honors_mindwell_cache_override(self):
        from mindwell.config import backup_root, index_path
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "relocated-cache"
            with patch.dict("os.environ", {"MINDWELL_CACHE": str(cache)}):
                vault = Path(tmp) / "vault"
                self.assertEqual(cache, index_path(vault).parent)
                self.assertEqual(cache, backup_root(vault).parent)

    def test_automation_prompts_use_done_marker_stamp_guard(self):
        from mindwell.automations import CORE_TASKS, PROMPTS
        for task in CORE_TASKS:
            prompt = PROMPTS[task["id"]]
            self.assertIn(f'automations/runs/{task["id"]}-YYYY-MM-DD.md', prompt)
            self.assertIn("done:", prompt)
            # The stamp-then-die takeover rule - a dead stamp must not block.
            self.assertIn("died mid-work", prompt)
        health = PROMPTS["weekly-health-check"]
        self.assertIn("started and never finished", health)
        self.assertIn("corroborate", health)

    def test_weekly_review_prompts_for_unwritten_decisions(self):
        from mindwell.automations import PROMPTS
        self.assertIn("wiki/decisions.md", PROMPTS["weekly-review"])
        self.assertIn("capture gaps", PROMPTS["weekday-startup"])

    def test_init_records_automation_template_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            init_vault(vault, profile="personal-ops", automations="core")
            installation = json.loads(
                (vault / "config/installation.json").read_text())
            hashes = installation["scaffold_hashes"]
            self.assertIn("automations/prompts/weekday-startup.md", hashes)
            self.assertIn("automations/REGISTER-WITH-YOUR-AGENT.md", hashes)
            self.assertNotIn("automations/plan.json", hashes)

    def test_upgrade_refreshes_an_unmodified_automation_prompt(self):
        from mindwell import automations
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            init_vault(vault, profile="personal-ops", automations="core")
            prompt_rel = "automations/prompts/weekday-startup.md"
            prompt_path = vault / prompt_rel

            # Simulate a vault whose prompt is an older release's template:
            # unknown to scaffold_hashes but present in the legacy-hash table.
            old_template = "# Weekday second-brain startup (older release)\n"
            prompt_path.write_text(old_template, encoding="utf-8")
            install_path = vault / "config" / "installation.json"
            installation = json.loads(install_path.read_text())
            installation["scaffold_hashes"].pop(prompt_rel, None)
            install_path.write_text(json.dumps(installation))

            legacy = {prompt_rel: {hashlib.sha256(
                old_template.encode("utf-8")).hexdigest()}}
            with patch.dict(automations.LEGACY_TEMPLATE_HASHES, legacy):
                result = upgrade_vault(vault)

            self.assertIn(prompt_rel, result["files"]["updated"])
            self.assertEqual(automations.PROMPTS["weekday-startup"],
                             prompt_path.read_text(encoding="utf-8"))

    def test_legacy_hash_table_pins_the_shipped_release_templates(self):
        # These digests are what v0.3.0-v0.4.1 actually wrote (rendered from
        # each tag's automations.py). If they drift, upgrade silently stops
        # recognizing real vaults in the field as unmodified.
        from mindwell.automations import LEGACY_TEMPLATE_HASHES
        self.assertIn(
            "e3e5653e250a0e206d2e9b7143cb021dc34b968e2d13a801cd0258dbe60b9ddf",
            LEGACY_TEMPLATE_HASHES["automations/prompts/weekday-startup.md"])
        self.assertIn(
            "5ce8bccba0943e8623c0bf391c9d52373d359fa8ddc5ab679a143d729ff0ac41",
            LEGACY_TEMPLATE_HASHES["automations/prompts/weekly-health-check.md"])

    def test_upgrade_preserves_a_customized_automation_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            init_vault(vault, profile="personal-ops", automations="core")
            prompt_rel = "automations/prompts/weekly-review.md"
            prompt_path = vault / prompt_rel
            custom = "# My review ritual\n\nOnly review what I tag #review.\n"
            prompt_path.write_text(custom, encoding="utf-8")
            result = upgrade_vault(vault)
            self.assertIn(prompt_rel, result["files"]["preserved_customized"])
            self.assertEqual(custom, prompt_path.read_text(encoding="utf-8"))

    def test_upgrade_heals_a_missing_automation_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            init_vault(vault, profile="personal-ops", automations="core")
            plan_path = vault / "automations" / "plan.json"
            plan_path.unlink()
            result = upgrade_vault(vault)
            self.assertTrue(plan_path.exists())
            self.assertIn("automations/plan.json", result["files"]["created"])
            self.assertEqual("not_registered",
                             json.loads(plan_path.read_text())["registration_status"])

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
