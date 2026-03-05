import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from report_writer import (
    build_markdown_document,
    format_generated_timestamp,
    format_model_display,
    format_provider_display,
)


class TestFormatProviderDisplay(unittest.TestCase):
    def test_gemini(self):
        self.assertEqual(format_provider_display("gemini"), "Gemini")

    def test_openai(self):
        self.assertEqual(format_provider_display("openai"), "OpenAI")

    def test_unknown_passthrough(self):
        self.assertEqual(format_provider_display("anthropic"), "anthropic")


class TestFormatModelDisplay(unittest.TestCase):
    def test_known_model_returns_display_name(self):
        self.assertEqual(
            format_model_display("gemini-2.5-flash-lite-preview-09-2025"),
            "Gemini 2.5 Flash-Lite Preview",
        )

    def test_unknown_model_returned_unchanged(self):
        self.assertEqual(format_model_display("my-custom-model"), "my-custom-model")

    def test_empty_string_returned_as_is(self):
        self.assertEqual(format_model_display(""), "")

    def test_none_returned_as_is(self):
        self.assertIsNone(format_model_display(None))


class TestBuildMarkdownDocument(unittest.TestCase):
    def _build(self, **kwargs):
        defaults = dict(
            summary="## Key Highlights\nAll good.",
            provider="gemini",
            model="gemini-2.5-flash-lite-preview-09-2025",
            project={"title": "Acme Project", "url": "https://github.com/orgs/acme/projects/1"},
            report_timezone="",
            report_timezone_label="UTC",
        )
        defaults.update(kwargs)
        return build_markdown_document(**defaults)

    def test_starts_with_executive_report_heading(self):
        doc = self._build()
        self.assertTrue(doc.startswith("# Executive Report"))

    def test_contains_project_name(self):
        doc = self._build()
        self.assertIn("Acme Project", doc)

    def test_contains_project_url(self):
        doc = self._build()
        self.assertIn("https://github.com/orgs/acme/projects/1", doc)

    def test_contains_provider_and_model(self):
        doc = self._build()
        self.assertIn("Gemini", doc)
        self.assertIn("Gemini 2.5 Flash-Lite Preview", doc)

    def test_contains_summary(self):
        doc = self._build()
        self.assertIn("## Key Highlights", doc)
        self.assertIn("All good.", doc)

    def test_uses_unknown_project_fallback(self):
        doc = self._build(project={})
        self.assertIn("Unknown Project", doc)
        self.assertIn("Unknown URL", doc)

    def test_model_omitted_when_empty(self):
        doc = self._build(model="")
        self.assertIn("Gemini", doc)
        self.assertNotIn("Gemini -", doc)


class TestFormatGeneratedTimestamp(unittest.TestCase):
    def test_returns_nonempty_string(self):
        result = format_generated_timestamp()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_uses_timezone_label(self):
        result = format_generated_timestamp(report_timezone_label="GMT+1")
        self.assertIn("GMT+1", result)

    def test_invalid_timezone_does_not_raise(self):
        result = format_generated_timestamp(report_timezone="Not/AReal_Zone")
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
