import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ai_clients import generate_summary


class TestGenerateSummary(unittest.TestCase):
    def test_dispatches_to_gemini(self):
        with patch("ai_clients.get_gemini_summary", return_value="gemini output") as mock_gemini, \
             patch("ai_clients.get_openai_summary") as mock_openai:
            result = generate_summary(
                provider="gemini",
                prompt="Summarise this",
                gemini_api_key="g_key",
                gemini_model="gemini-2.5-flash",
                openai_api_key="o_key",
                openai_model="gpt-5-nano",
                timeout_seconds=60,
                max_retries=1,
            )
        self.assertEqual(result, "gemini output")
        mock_gemini.assert_called_once_with("g_key", "gemini-2.5-flash", "Summarise this", 60, 1)
        mock_openai.assert_not_called()

    def test_dispatches_to_openai(self):
        with patch("ai_clients.get_openai_summary", return_value="openai output") as mock_openai, \
             patch("ai_clients.get_gemini_summary") as mock_gemini:
            result = generate_summary(
                provider="openai",
                prompt="Summarise this",
                gemini_api_key="g_key",
                gemini_model="gemini-2.5-flash",
                openai_api_key="o_key",
                openai_model="gpt-5-nano",
                timeout_seconds=30,
                max_retries=0,
            )
        self.assertEqual(result, "openai output")
        mock_openai.assert_called_once_with("o_key", "gpt-5-nano", "Summarise this", 30, 0)
        mock_gemini.assert_not_called()

    def test_raises_value_error_for_unknown_provider(self):
        with self.assertRaises(ValueError) as ctx:
            generate_summary(
                provider="anthropic",
                prompt="Summarise this",
                gemini_api_key="",
                gemini_model="",
                openai_api_key="",
                openai_model="",
            )
        self.assertIn("AI_PROVIDER", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
