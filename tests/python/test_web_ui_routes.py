import json
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


class TestGetIndex(unittest.TestCase):
    def setUp(self):
        self.client = web_ui.app.test_client()

    def test_returns_200(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_returns_html_content_type(self):
        resp = self.client.get("/")
        self.assertIn("text/html", resp.content_type)

    def test_response_has_security_headers(self):
        resp = self.client.get("/")
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("X-XSS-Protection", resp.headers)


class TestPostRunStream(unittest.TestCase):
    def setUp(self):
        self.client = web_ui.app.test_client()
        self.settings = _make_settings()
        self.pipeline_result = {
            "summary": "Summary text",
            "markdown": "# Report\n\nSummary text\n",
            "report_path": None,
            "project": {"title": "Acme", "url": "https://github.com/orgs/acme/projects/1"},
            "metrics": {"total_items_fetched": 5},
            "provider": "gemini",
        }

    def _make_pipeline_side_effect(self, result=None, error=None):
        """Return a side_effect that optionally fires progress_callback before returning."""
        base_result = result or self.pipeline_result

        def _pipeline(settings, *, base_dir, log, save_report, progress_callback=None):
            if progress_callback:
                progress_callback({"step_id": "github_request", "status": "completed", "message": "Done"})
            if error:
                raise error
            return base_result

        return _pipeline

    def _stream_events(self, pipeline_result=None, pipeline_error=None):
        """POST to /api/run-stream and parse all NDJSON events."""
        side_effect = self._make_pipeline_side_effect(
            result=pipeline_result, error=pipeline_error
        )
        with patch("web_ui.load_settings", return_value=self.settings), \
             patch("web_ui.run_report_pipeline", side_effect=side_effect):
            resp = self.client.post(
                "/api/run-stream",
                json={},
                content_type="application/json",
            )
            raw = resp.data.decode("utf-8")

        lines = [l for l in raw.strip().split("\n") if l.strip()]
        return resp, [json.loads(l) for l in lines]

    def test_returns_200(self):
        resp, _ = self._stream_events()
        self.assertEqual(resp.status_code, 200)

    def test_content_type_is_ndjson(self):
        resp, _ = self._stream_events()
        self.assertIn("ndjson", resp.content_type)

    def test_emits_result_event_on_success(self):
        _, events = self._stream_events()
        types = [e["type"] for e in events]
        self.assertIn("result", types)

    def test_emits_done_event(self):
        _, events = self._stream_events()
        types = [e["type"] for e in events]
        self.assertIn("done", types)

    def test_done_event_is_last(self):
        _, events = self._stream_events()
        self.assertEqual(events[-1]["type"], "done")

    def test_result_event_contains_markdown(self):
        _, events = self._stream_events()
        result_events = [e for e in events if e["type"] == "result"]
        self.assertEqual(len(result_events), 1)
        self.assertIn("markdown", result_events[0]["data"])

    def test_result_event_ok_is_true(self):
        _, events = self._stream_events()
        result_event = next(e for e in events if e["type"] == "result")
        self.assertTrue(result_event["data"]["ok"])

    def test_emits_step_events(self):
        _, events = self._stream_events()
        step_events = [e for e in events if e["type"] == "step"]
        self.assertTrue(len(step_events) > 0)

    def test_emits_error_event_on_pipeline_failure(self):
        _, events = self._stream_events(pipeline_error=RuntimeError("GitHub down"))
        types = [e["type"] for e in events]
        self.assertIn("error", types)

    def test_error_event_contains_message(self):
        _, events = self._stream_events(pipeline_error=RuntimeError("GitHub down"))
        error_events = [e for e in events if e["type"] == "error"]
        self.assertEqual(len(error_events), 1)
        self.assertIn("GitHub down", error_events[0]["error"])

    def test_done_event_emitted_even_on_error(self):
        _, events = self._stream_events(pipeline_error=RuntimeError("fail"))
        self.assertEqual(events[-1]["type"], "done")

    def test_error_is_redacted_in_stream(self):
        """Secrets in exception messages must be stripped before streaming."""
        exc = RuntimeError("Failed: ?key=AIzaSyRealKey")
        _, events = self._stream_events(pipeline_error=exc)
        error_events = [e for e in events if e["type"] == "error"]
        self.assertNotIn("AIzaSyRealKey", error_events[0]["error"])


if __name__ == "__main__":
    unittest.main()
