import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from payload_builder import build_analysis_payload, parse_github_datetime, truncate_text


class TestPayloadBuilder(unittest.TestCase):
    def test_parse_github_datetime_handles_invalid(self):
        self.assertIsNone(parse_github_datetime(""))
        self.assertIsNone(parse_github_datetime("not-a-date"))

    def test_parse_github_datetime_parses_zulu(self):
        parsed = parse_github_datetime("2026-03-01T12:34:56Z")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_truncate_text(self):
        self.assertEqual(truncate_text(None), "")
        self.assertEqual(truncate_text("abc", limit=5), "abc")
        self.assertEqual(truncate_text("abcdef", limit=3), "abc...")

    def test_build_analysis_payload_filters_recent_comments_and_counts(self):
        now = datetime.now(timezone.utc)
        recent = now.isoformat().replace("+00:00", "Z")
        old = (now - timedelta(days=30)).isoformat().replace("+00:00", "Z")

        raw = {
            "data": {
                "node": {
                    "title": "Demo project",
                    "url": "https://github.com/orgs/acme/projects/1",
                    "items": {
                        "nodes": [
                            {
                                "updatedAt": recent,
                                "content": {
                                    "number": 1,
                                    "url": "https://github.com/acme/repo/issues/1",
                                    "updatedAt": old,
                                    "comments": {
                                        "nodes": [
                                            {"createdAt": recent, "bodyText": "recent comment"},
                                            {"createdAt": old, "bodyText": "old comment"},
                                        ]
                                    },
                                },
                            },
                            {
                                "updatedAt": old,
                                "content": {
                                    "number": 2,
                                    "url": "https://github.com/acme/repo/issues/2",
                                    "updatedAt": old,
                                    "comments": {"nodes": []},
                                },
                            },
                        ]
                    },
                }
            }
        }

        payload = build_analysis_payload(raw, 7, 100, 20)
        self.assertEqual(payload["project"]["title"], "Demo project")
        self.assertEqual(payload["metrics"]["total_items_fetched"], 2)
        self.assertEqual(payload["metrics"]["items_updated_in_lookback_window"], 1)
        self.assertEqual(payload["metrics"]["comments_created_in_lookback_window"], 1)
        self.assertIn("recentComments", payload["items"][0]["content"])
        self.assertEqual(len(payload["items"][0]["content"]["recentComments"]), 1)


if __name__ == "__main__":
    unittest.main()
