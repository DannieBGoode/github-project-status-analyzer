import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from report_formatting import (
    auto_link_issue_references,
    enforce_top_metrics_block,
    normalize_subsection_headings,
)


class TestReportFormatting(unittest.TestCase):
    def test_auto_link_issue_references_only_links_unique_numbers(self):
        summary = "Worked on #1 and #2. Existing [#3](https://x/y/3) link remains."
        data = {
            "items": [
                {"content": {"number": 1, "url": "https://github.com/acme/repo/issues/1"}},
                {"content": {"number": 2, "url": "https://github.com/acme/repo/issues/2"}},
                {"content": {"number": 2, "url": "https://github.com/other/repo/issues/2"}},
            ]
        }
        output = auto_link_issue_references(summary, data)
        self.assertIn("[#1](https://github.com/acme/repo/issues/1)", output)
        self.assertIn(" #2", output)  # unchanged because ambiguous
        self.assertIn("[#3](https://x/y/3)", output)  # unchanged existing link

    def test_normalize_subsection_headings(self):
        summary = "- **Risks**:\nText\n- **Blockers**:\nMore"
        output = normalize_subsection_headings(summary)
        self.assertIn("### Risks", output)
        self.assertIn("### Blockers", output)

    def test_enforce_top_metrics_block(self):
        summary = "- Total Items Fetched: 999\nExisting body line."
        data = {
            "metrics": {
                "total_items_fetched": 10,
                "items_updated_in_lookback_window": 3,
                "comments_created_in_lookback_window": 5,
            }
        }
        output = enforce_top_metrics_block(summary, data)
        self.assertTrue(output.startswith("- Total Items Fetched: `10`"))
        self.assertIn("Existing body line.", output)
        self.assertNotIn("999", output)


if __name__ == "__main__":
    unittest.main()
