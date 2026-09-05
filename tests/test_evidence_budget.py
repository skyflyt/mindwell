"""Fictional passage-coverage fixtures; no answer-model accuracy claims."""
import unittest

from mindwell.engine import assemble_context


class EvidenceBudgetTests(unittest.TestCase):
    def selected(self, count=5):
        selected = []
        for index in range(count):
            path = f"wiki/projects/regional-observatory-{index}-maintenance-bulletin.md"
            heading = f"Regional observatory {index} maintenance bulletin ownership and delivery"
            prefix = f"Vault note: {path}. Title: {heading}. Section: {heading}."
            body = (f"The observatory {index} maintenance bulletin recipient is Morgan Example-{index}. "
                    "The delivery coordinator is a separate role and does not receive this bulletin.\n\n"
                    + "Unrelated history. " * 100)
            row = (path, heading, body, prefix, "project", "active", "2024-01-02", 5)
            selected.append((.05, f"chunk-{index}", row))
        return selected

    def test_all_five_recipient_facts_fit_standard_budget(self):
        selected = self.selected()
        context, manifest = assemble_context(
            selected, "Who is the observatory maintenance bulletin recipient?", 2500)
        self.assertLessEqual(len(context), 2500)
        self.assertEqual(5, len(manifest))
        for index in range(5):
            self.assertIn(f"Morgan Example-{index}", context)
        self.assertNotIn("Vault note:", context)
        self.assertEqual(selected[0][2][3], manifest[0]["prefix"])

    def test_historical_status_and_date_remain_in_answer_context(self):
        selected = self.selected(1)
        row = list(selected[0][2])
        row[5] = "historical"
        selected[0] = (.05, "chunk-0", tuple(row))
        context, manifest = assemble_context(selected, "Who receives the bulletin?", 700)
        self.assertIn("status=historical", context)
        self.assertIn("updated=2024-01-02", context)
        self.assertEqual("historical", manifest[0]["status"])

    def test_empty_selection(self):
        self.assertEqual(("", []), assemble_context([], "Any evidence?", 2500))
