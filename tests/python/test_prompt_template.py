import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from prompt_template import build_report_prompt


_SAMPLE_DATA = {
    "project": {
        "title": "Mithril Network",
        "url": "https://github.com/orgs/acme/projects/1",
    },
    "metrics": {
        "total_items_fetched": 42,
        "items_updated_in_lookback_window": 10,
        "comments_created_in_lookback_window": 5,
    },
    "items": [],
}


class TestBuildReportPrompt(unittest.TestCase):
    def test_contains_project_title(self):
        prompt = build_report_prompt(_SAMPLE_DATA, 7)
        self.assertIn("Mithril Network", prompt)

    def test_contains_project_url(self):
        prompt = build_report_prompt(_SAMPLE_DATA, 7)
        self.assertIn("https://github.com/orgs/acme/projects/1", prompt)

    def test_contains_lookback_days(self):
        prompt = build_report_prompt(_SAMPLE_DATA, 14)
        self.assertIn("14", prompt)

    def test_contains_metrics_values(self):
        prompt = build_report_prompt(_SAMPLE_DATA, 7)
        self.assertIn("42", prompt)
        self.assertIn("10", prompt)
        self.assertIn("5", prompt)

    def test_fallback_project_title_when_missing(self):
        data = {"project": {}, "metrics": {}, "items": []}
        prompt = build_report_prompt(data, 7)
        self.assertIn("Unknown Project", prompt)

    def test_fallback_project_url_when_missing(self):
        data = {"project": {}, "metrics": {}, "items": []}
        prompt = build_report_prompt(data, 7)
        self.assertIn("Unknown URL", prompt)

    def test_fallback_metrics_to_zero_when_missing(self):
        data = {"project": {"title": "X", "url": "Y"}, "items": []}
        prompt = build_report_prompt(data, 7)
        # All three metric placeholders should be filled with 0
        self.assertIn("0", prompt)

    def test_raw_data_serialized_as_json(self):
        prompt = build_report_prompt(_SAMPLE_DATA, 7)
        # The JSON-serialized payload must appear in the prompt
        self.assertIn(json.dumps(_SAMPLE_DATA), prompt)


if __name__ == "__main__":
    unittest.main()
