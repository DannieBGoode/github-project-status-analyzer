"""Tests for ai_provider_gemini and ai_provider_openai — including edge cases."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ai_provider_gemini import get_gemini_summary
from ai_provider_openai import get_openai_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    mock.text = str(json_data)
    return mock


# ---------------------------------------------------------------------------
# Gemini provider tests
# ---------------------------------------------------------------------------

class TestGetGeminiSummary(unittest.TestCase):
    def _call(self, json_data, status_code=200):
        mock_resp = _mock_response(json_data, status_code)
        with patch("ai_provider_gemini.post_json_with_retries", return_value=mock_resp):
            return get_gemini_summary("api_key", "gemini-2.5-flash", "prompt", 60, 0)

    def test_returns_text_on_valid_response(self):
        data = {"candidates": [{"content": {"parts": [{"text": "Summary here"}]}}]}
        result = self._call(data)
        self.assertEqual(result, "Summary here")

    def test_api_key_passed_as_header_not_url(self):
        """API key must go in x-goog-api-key header, NOT in the URL."""
        data = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        mock_resp = _mock_response(data)
        with patch("ai_provider_gemini.post_json_with_retries", return_value=mock_resp) as mock_post:
            get_gemini_summary("secret_key", "gemini-2.5-flash", "prompt", 60, 0)
        call_kwargs = mock_post.call_args
        url = call_kwargs[0][0]
        self.assertNotIn("secret_key", url, "API key must not appear in the URL")
        headers = call_kwargs[1].get("headers") or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        # headers may be a kwarg
        if call_kwargs[1].get("headers"):
            headers = call_kwargs[1]["headers"]
        self.assertEqual(headers.get("x-goog-api-key"), "secret_key")

    def test_raises_value_error_on_empty_candidates(self):
        data = {"candidates": []}
        with self.assertRaises(ValueError) as ctx:
            self._call(data)
        self.assertIn("unexpected response structure", str(ctx.exception))

    def test_raises_value_error_on_missing_candidates_key(self):
        data = {}
        with self.assertRaises(ValueError) as ctx:
            self._call(data)
        self.assertIn("unexpected response structure", str(ctx.exception))

    def test_raises_value_error_on_missing_content(self):
        data = {"candidates": [{"finishReason": "SAFETY"}]}
        with self.assertRaises(ValueError) as ctx:
            self._call(data)
        self.assertIn("unexpected response structure", str(ctx.exception))

    def test_raises_value_error_on_empty_parts(self):
        data = {"candidates": [{"content": {"parts": []}}]}
        with self.assertRaises(ValueError) as ctx:
            self._call(data)
        self.assertIn("unexpected response structure", str(ctx.exception))

    def test_raises_value_error_on_none_candidates(self):
        data = {"candidates": None}
        with self.assertRaises(ValueError) as ctx:
            self._call(data)
        self.assertIn("unexpected response structure", str(ctx.exception))

    def test_raise_for_status_called(self):
        data = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        mock_resp = _mock_response(data)
        with patch("ai_provider_gemini.post_json_with_retries", return_value=mock_resp):
            get_gemini_summary("key", "model", "prompt", 60, 0)
        mock_resp.raise_for_status.assert_called_once()

    def test_passes_max_retries_to_http(self):
        data = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        mock_resp = _mock_response(data)
        with patch("ai_provider_gemini.post_json_with_retries", return_value=mock_resp) as mock_post:
            get_gemini_summary("key", "model", "prompt", 30, 3)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["max_retries"], 3)
        self.assertEqual(kwargs["timeout_seconds"], 30)


# ---------------------------------------------------------------------------
# OpenAI provider tests
# ---------------------------------------------------------------------------

class TestGetOpenAISummary(unittest.TestCase):
    def _call(self, json_data, status_code=200):
        mock_resp = _mock_response(json_data, status_code)
        with patch("ai_provider_openai.post_json_with_retries", return_value=mock_resp):
            return get_openai_summary("api_key", "gpt-5-nano", "prompt", 60, 0)

    def test_returns_text_from_output_text_field(self):
        data = {"output_text": "Summary from output_text"}
        result = self._call(data)
        self.assertEqual(result, "Summary from output_text")

    def test_returns_text_from_output_array(self):
        data = {
            "output": [
                {"content": [{"type": "output_text", "text": "Summary from output array"}]}
            ]
        }
        result = self._call(data)
        self.assertEqual(result, "Summary from output array")

    def test_returns_text_type_from_output_array(self):
        data = {
            "output": [
                {"content": [{"type": "text", "text": "Summary from text type"}]}
            ]
        }
        result = self._call(data)
        self.assertEqual(result, "Summary from text type")

    def test_backward_compat_choices_format(self):
        data = {
            "choices": [{"message": {"content": "Legacy chat response"}}]
        }
        result = self._call(data)
        self.assertEqual(result, "Legacy chat response")

    def test_raises_value_error_on_empty_response(self):
        data = {}
        with self.assertRaises(ValueError) as ctx:
            self._call(data)
        self.assertIn("no text content", str(ctx.exception))

    def test_raises_value_error_on_400_status(self):
        mock_resp = _mock_response({"error": "invalid key"}, status_code=401)
        with patch("ai_provider_openai.post_json_with_retries", return_value=mock_resp):
            with self.assertRaises(ValueError) as ctx:
                get_openai_summary("bad_key", "gpt-5-nano", "prompt", 60, 0)
        self.assertIn("401", str(ctx.exception))

    def test_bearer_token_in_header(self):
        data = {"output_text": "ok"}
        mock_resp = _mock_response(data)
        with patch("ai_provider_openai.post_json_with_retries", return_value=mock_resp) as mock_post:
            get_openai_summary("sk-test-key", "gpt-5-nano", "prompt", 60, 0)
        _, kwargs = mock_post.call_args
        headers = kwargs["headers"]
        self.assertIn("Authorization", headers)
        self.assertIn("sk-test-key", headers["Authorization"])

    def test_raises_on_empty_choices(self):
        data = {"choices": []}
        with self.assertRaises(ValueError):
            self._call(data)

    def test_raises_on_output_array_with_no_matching_type(self):
        data = {
            "output": [
                {"content": [{"type": "image", "text": "not text"}]}
            ]
        }
        with self.assertRaises(ValueError):
            self._call(data)


if __name__ == "__main__":
    unittest.main()
