import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from settings import Settings
from report_runner import run_report_pipeline


def _make_settings(**overrides):
    defaults = dict(
        github_token="ghp_token",
        project_id="",
        project_url="https://github.com/orgs/acme/projects/1",
        ai_provider="gemini",
        lookback_days=14,
        max_items=50,
        max_comments_per_item=10,
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


_RAW_DATA = {
    "data": {
        "node": {
            "title": "Acme Board",
            "url": "https://github.com/orgs/acme/projects/1",
            "items": {"nodes": []},
        }
    }
}

_PIPELINE_PATCHES = {
    "report_runner.get_project_id": MagicMock(return_value="PVT_abc123"),
    "report_runner.fetch_github_project_data": MagicMock(return_value=_RAW_DATA),
    "report_runner.generate_summary": MagicMock(return_value="## Summary\nAll good."),
}


class TestRunReportPipeline(unittest.TestCase):
    def _run(self, settings=None, **kwargs):
        """Helper: run the pipeline with all external calls mocked."""
        s = settings or _make_settings()
        with patch("report_runner.get_project_id", return_value="PVT_abc123"), \
             patch("report_runner.fetch_github_project_data", return_value=_RAW_DATA), \
             patch("report_runner.generate_summary", return_value="## Key Achievements\nAll good.\n## Risks\nNo risks.\n## Issues and Blockers\n### Issues\nNo issues.\n### Blockers\nNo blockers."):
            return run_report_pipeline(s, base_dir=Path("/tmp"), log=lambda *a, **k: None, save_report=False, **kwargs)

    def test_returns_expected_keys(self):
        result = self._run()
        for key in ("summary", "markdown", "report_path", "project", "metrics", "provider"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_report_path_is_none_when_save_false(self):
        result = self._run()
        self.assertIsNone(result["report_path"])

    def test_provider_in_result(self):
        result = self._run()
        self.assertEqual(result["provider"], "gemini")

    def test_openai_provider_selects_openai_model(self):
        s = _make_settings(ai_provider="openai")
        with patch("report_runner.get_project_id", return_value="PVT_abc123"), \
             patch("report_runner.fetch_github_project_data", return_value=_RAW_DATA), \
             patch("report_runner.generate_summary", return_value="## Key Achievements\nDone.\n## Risks\nNo risks.\n## Issues and Blockers\n### Issues\nNo issues.\n### Blockers\nNo blockers.") as mock_gen:
            result = run_report_pipeline(s, base_dir=Path("/tmp"), log=lambda *a, **k: None, save_report=False)
        # generate_summary called with openai provider
        self.assertEqual(mock_gen.call_args[0][0], "openai")
        self.assertEqual(result["provider"], "openai")

    def test_progress_callback_receives_steps(self):
        steps = []
        self._run(progress_callback=lambda evt: steps.append(evt))
        step_ids = [s["step_id"] for s in steps]
        self.assertIn("github_request", step_ids)
        self.assertIn("github_response", step_ids)
        self.assertIn("ai_send", step_ids)
        self.assertIn("ai_wait", step_ids)
        self.assertIn("markdown_build", step_ids)

    def test_progress_callback_steps_have_completed_status(self):
        steps = []
        self._run(progress_callback=lambda evt: steps.append(evt))
        completed = [s for s in steps if s["status"] == "completed"]
        self.assertTrue(len(completed) > 0, "Expected at least one completed step")

    def test_get_project_id_called_with_token_and_url(self):
        s = _make_settings()
        with patch("report_runner.get_project_id", return_value="PVT_abc123") as mock_pid, \
             patch("report_runner.fetch_github_project_data", return_value=_RAW_DATA), \
             patch("report_runner.generate_summary", return_value="## Key Achievements\nDone.\n## Risks\nNo risks.\n## Issues and Blockers\n### Issues\nNo issues.\n### Blockers\nNo blockers."):
            run_report_pipeline(s, base_dir=Path("/tmp"), log=lambda *a, **k: None, save_report=False)
        mock_pid.assert_called_once_with(s.github_token, s.project_id, s.project_url)

    def test_save_report_writes_file(self):
        s = _make_settings()
        mock_path = MagicMock()
        mock_path.__str__ = lambda self: "/tmp/reports/report.md"
        with patch("report_runner.get_project_id", return_value="PVT_abc123"), \
             patch("report_runner.fetch_github_project_data", return_value=_RAW_DATA), \
             patch("report_runner.generate_summary", return_value="## Key Achievements\nDone.\n## Risks\nNo risks.\n## Issues and Blockers\n### Issues\nNo issues.\n### Blockers\nNo blockers."), \
             patch("report_runner.write_report", return_value=mock_path) as mock_write:
            result = run_report_pipeline(s, base_dir=Path("/tmp"), log=lambda *a, **k: None, save_report=True)
        mock_write.assert_called_once()
        self.assertIsNotNone(result["report_path"])

    def test_pipeline_propagates_generate_summary_error(self):
        s = _make_settings()
        with patch("report_runner.get_project_id", return_value="PVT_abc123"), \
             patch("report_runner.fetch_github_project_data", return_value=_RAW_DATA), \
             patch("report_runner.generate_summary", side_effect=ValueError("API key invalid")):
            with self.assertRaises(ValueError) as ctx:
                run_report_pipeline(s, base_dir=Path("/tmp"), log=lambda *a, **k: None, save_report=False)
        self.assertIn("API key invalid", str(ctx.exception))

    def test_pipeline_propagates_github_fetch_error(self):
        s = _make_settings()
        with patch("report_runner.get_project_id", return_value="PVT_abc123"), \
             patch("report_runner.fetch_github_project_data", side_effect=RuntimeError("GitHub unreachable")):
            with self.assertRaises(RuntimeError) as ctx:
                run_report_pipeline(s, base_dir=Path("/tmp"), log=lambda *a, **k: None, save_report=False)
        self.assertIn("GitHub unreachable", str(ctx.exception))

    def test_markdown_contains_project_title(self):
        result = self._run()
        self.assertIn("Acme Board", result["markdown"])

    def test_project_info_in_result(self):
        result = self._run()
        self.assertEqual(result["project"].get("title"), "Acme Board")

    def test_no_progress_callback_does_not_raise(self):
        """Pipeline must work fine when progress_callback is None (default)."""
        s = _make_settings()
        with patch("report_runner.get_project_id", return_value="PVT_abc123"), \
             patch("report_runner.fetch_github_project_data", return_value=_RAW_DATA), \
             patch("report_runner.generate_summary", return_value="## Key Achievements\nDone.\n## Risks\nNo risks.\n## Issues and Blockers\n### Issues\nNo issues.\n### Blockers\nNo blockers."):
            result = run_report_pipeline(s, base_dir=Path("/tmp"), log=lambda *a, **k: None, save_report=False)
        self.assertIn("summary", result)


if __name__ == "__main__":
    unittest.main()
