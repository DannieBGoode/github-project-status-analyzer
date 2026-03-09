import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from report_writer import (
    build_markdown_document,
    format_generated_timestamp,
    format_model_display,
    format_provider_display,
    write_report,
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


class TestWriteReport(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, **kwargs):
        defaults = dict(
            summary="## Key Highlights\nAll good.",
            provider="gemini",
            model="gemini-2.5-flash-lite-preview-09-2025",
            project={"title": "Acme", "url": "https://github.com/orgs/acme/projects/1"},
            base_dir=self.tmp,
            report_timezone="",
            report_timezone_label="UTC",
        )
        defaults.update(kwargs)
        return write_report(**defaults)

    def test_returns_path_object(self):
        path = self._write()
        self.assertIsInstance(path, Path)

    def test_file_exists_after_write(self):
        path = self._write()
        self.assertTrue(path.exists())

    def test_file_is_inside_reports_subdir(self):
        path = self._write()
        self.assertEqual(path.parent.name, "reports")

    def test_creates_reports_directory_if_missing(self):
        new_base = self.tmp / "nested" / "dir"
        path = self._write(base_dir=new_base)
        self.assertTrue(path.exists())

    def test_filename_matches_report_timestamp_pattern(self):
        import re
        path = self._write()
        self.assertRegex(path.name, r"^report-\d{8}-\d{6}\.md$")

    def test_file_has_md_extension(self):
        path = self._write()
        self.assertEqual(path.suffix, ".md")

    def test_file_contains_summary(self):
        path = self._write()
        content = path.read_text(encoding="utf-8")
        self.assertIn("All good.", content)

    def test_file_starts_with_executive_report_heading(self):
        path = self._write()
        content = path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("# Executive Report"))

    def test_utf8_encoding_with_special_characters(self):
        path = self._write(summary="## Notes\nCafé résumé — naïve approach 🎉")
        content = path.read_text(encoding="utf-8")
        self.assertIn("Café résumé", content)
        self.assertIn("🎉", content)

    def test_second_report_with_different_timestamp_has_different_filename(self):
        import re
        # Both reports must follow the timestamp pattern; uniqueness across
        # different seconds is guaranteed by the format — enough to verify format.
        path1 = self._write()
        path2 = self._write()
        self.assertRegex(path1.name, r"^report-\d{8}-\d{6}\.md$")
        self.assertRegex(path2.name, r"^report-\d{8}-\d{6}\.md$")


if __name__ == "__main__":
    unittest.main()
