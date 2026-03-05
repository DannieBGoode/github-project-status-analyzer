import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Stub `config` before web_ui is imported so the module-level `import config` succeeds.
if "config" not in sys.modules:
    sys.modules["config"] = types.ModuleType("config")

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import web_ui  # noqa: E402

from settings import Settings  # noqa: E402


def _make_settings(**overrides):
    defaults = dict(
        github_token="ghp_real",
        project_id="",
        project_url="https://github.com/orgs/acme/projects/1",
        ai_provider="gemini",
        lookback_days=14,
        max_items=100,
        max_comments_per_item=20,
        gemini_api_key="g_key",
        gemini_model="gemini-2.5-flash-lite-preview-09-2025",
        openai_api_key="o_key",
        openai_model="gpt-5-nano",
        ai_timeout_seconds=120,
        ai_max_retries=1,
        report_timezone="",
        report_timezone_label="",
    )
    defaults.update(overrides)
    return Settings(**defaults)


class TestGetConfig(unittest.TestCase):
    def setUp(self):
        self.client = web_ui.app.test_client()
        self.settings = _make_settings()

    def test_returns_200_with_expected_keys(self):
        with patch("web_ui.load_settings", return_value=self.settings):
            resp = self.client.get("/api/config")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for key in (
            "ai_provider",
            "project_url",
            "lookback_days",
            "max_items",
            "max_comments_per_item",
            "model_options",
            "github_token",
            "gemini_api_key",
            "openai_api_key",
            "has_github_token",
            "has_gemini_api_key",
            "has_openai_api_key",
        ):
            self.assertIn(key, data, f"missing key: {key}")

    def test_github_token_is_masked(self):
        with patch("web_ui.load_settings", return_value=self.settings):
            resp = self.client.get("/api/config")
        data = resp.get_json()
        self.assertIn("*", data["github_token"])
        self.assertNotIn("ghp_real", data["github_token"])

    def test_has_github_token_true_when_set(self):
        with patch("web_ui.load_settings", return_value=self.settings):
            resp = self.client.get("/api/config")
        self.assertTrue(resp.get_json()["has_github_token"])

    def test_has_github_token_false_when_empty(self):
        empty_settings = _make_settings(github_token="")
        with patch("web_ui.load_settings", return_value=empty_settings):
            resp = self.client.get("/api/config")
        self.assertFalse(resp.get_json()["has_github_token"])


class TestPostRun(unittest.TestCase):
    def setUp(self):
        self.client = web_ui.app.test_client()
        self.settings = _make_settings()

    def _post(self, payload=None):
        return self.client.post(
            "/api/run",
            json=payload or {},
            content_type="application/json",
        )

    def test_returns_ok_true_on_success(self):
        pipeline_result = {
            "summary": "Summary text",
            "markdown": "# Report\n\nSummary text\n",
            "report_path": None,
            "project": {"title": "Acme", "url": "https://github.com/orgs/acme/projects/1"},
            "metrics": {},
            "provider": "gemini",
        }
        with patch("web_ui.load_settings", return_value=self.settings), \
             patch("web_ui.run_report_pipeline", return_value=pipeline_result):
            resp = self._post()

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("filename", data)
        self.assertIn("markdown", data)
        self.assertIn("summary", data)

    def test_returns_400_and_ok_false_on_pipeline_error(self):
        with patch("web_ui.load_settings", return_value=self.settings), \
             patch("web_ui.run_report_pipeline", side_effect=RuntimeError("GitHub fetch failed")):
            resp = self._post()

        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("GitHub fetch failed", data["error"])

    def test_filename_has_md_extension(self):
        pipeline_result = {
            "summary": "s",
            "markdown": "m",
            "report_path": None,
            "project": {},
            "metrics": {},
            "provider": "gemini",
        }
        with patch("web_ui.load_settings", return_value=self.settings), \
             patch("web_ui.run_report_pipeline", return_value=pipeline_result):
            resp = self._post()

        self.assertTrue(resp.get_json()["filename"].endswith(".md"))


if __name__ == "__main__":
    unittest.main()
