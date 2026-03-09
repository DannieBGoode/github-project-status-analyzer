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


class TestPayloadBuilderEdgeCases(unittest.TestCase):
    def _empty_raw(self):
        return {
            "data": {
                "node": {
                    "title": "Empty Project",
                    "url": "https://github.com/orgs/acme/projects/2",
                    "items": {"nodes": []},
                }
            }
        }

    def test_empty_project_zero_metrics(self):
        payload = build_analysis_payload(self._empty_raw(), 14, 100, 20)
        self.assertEqual(payload["metrics"]["total_items_fetched"], 0)
        self.assertEqual(payload["metrics"]["items_updated_in_lookback_window"], 0)
        self.assertEqual(payload["metrics"]["comments_created_in_lookback_window"], 0)
        self.assertEqual(payload["items"], [])

    def test_empty_project_preserves_title_and_url(self):
        payload = build_analysis_payload(self._empty_raw(), 14, 100, 20)
        self.assertEqual(payload["project"]["title"], "Empty Project")
        self.assertEqual(payload["project"]["url"], "https://github.com/orgs/acme/projects/2")

    def test_none_items_node_treated_as_empty(self):
        raw = {"data": {"node": {"title": "T", "url": "U", "items": {"nodes": None}}}}
        payload = build_analysis_payload(raw, 14, 100, 20)
        self.assertEqual(payload["metrics"]["total_items_fetched"], 0)

    def test_missing_data_key_returns_empty(self):
        payload = build_analysis_payload({}, 14, 100, 20)
        self.assertEqual(payload["metrics"]["total_items_fetched"], 0)
        self.assertIsNone(payload["project"]["title"])

    def test_malformed_item_timestamp_not_counted_as_recent(self):
        """Items with unparseable timestamps should not count as recent."""
        raw = {
            "data": {
                "node": {
                    "title": "T",
                    "url": "U",
                    "items": {
                        "nodes": [
                            {
                                "updatedAt": "not-a-date",
                                "content": {
                                    "updatedAt": "also-bad",
                                    "comments": {"nodes": []},
                                },
                            }
                        ]
                    },
                }
            }
        }
        payload = build_analysis_payload(raw, 14, 100, 20)
        self.assertEqual(payload["metrics"]["total_items_fetched"], 1)
        self.assertEqual(payload["metrics"]["items_updated_in_lookback_window"], 0)

    def test_comment_with_null_timestamp_excluded(self):
        now = datetime.now(timezone.utc)
        recent = now.isoformat().replace("+00:00", "Z")
        raw = {
            "data": {
                "node": {
                    "title": "T",
                    "url": "U",
                    "items": {
                        "nodes": [
                            {
                                "updatedAt": recent,
                                "content": {
                                    "updatedAt": recent,
                                    "comments": {
                                        "nodes": [
                                            {"createdAt": None, "bodyText": "null-date comment"},
                                            {"createdAt": recent, "bodyText": "valid comment"},
                                        ]
                                    },
                                },
                            }
                        ]
                    },
                }
            }
        }
        payload = build_analysis_payload(raw, 14, 100, 20)
        self.assertEqual(payload["metrics"]["comments_created_in_lookback_window"], 1)

    def test_truncate_text_at_boundary(self):
        # Exactly at limit — should NOT be truncated
        text = "a" * 600
        self.assertEqual(truncate_text(text, limit=600), text)
        # One over limit — should be truncated with ellipsis
        text_over = "a" * 601
        result = truncate_text(text_over, limit=600)
        self.assertTrue(result.endswith("..."))
        self.assertEqual(len(result), 603)  # 600 chars + "..."

    def test_parse_github_datetime_none_input(self):
        self.assertIsNone(parse_github_datetime(None))

    def test_parse_github_datetime_iso_with_offset(self):
        parsed = parse_github_datetime("2026-01-15T10:00:00+05:30")
        self.assertIsNotNone(parsed)

    def test_query_scope_fields_present(self):
        payload = build_analysis_payload(self._empty_raw(), 7, 50, 5)
        scope = payload["query_scope"]
        self.assertEqual(scope["lookback_days"], 7)
        self.assertEqual(scope["item_limit"], 50)
        self.assertEqual(scope["comment_limit_per_item"], 5)
        self.assertIn("lookback_start_utc", scope)


if __name__ == "__main__":
    unittest.main()
