import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ai_http import post_json_with_retries


class TestPostJsonWithRetries(unittest.TestCase):
    def test_returns_response_on_first_success(self):
        mock_response = MagicMock()
        with patch("requests.post", return_value=mock_response) as mock_post, \
             patch("time.sleep") as mock_sleep:
            result = post_json_with_retries(
                "https://example.com/api",
                json_body={"key": "value"},
                headers={"Authorization": "Bearer token"},
                timeout_seconds=30,
                max_retries=0,
            )
        self.assertIs(result, mock_response)
        mock_post.assert_called_once()
        mock_sleep.assert_not_called()

    def test_raises_timeout_error_after_exhausting_retries(self):
        with patch("requests.post", side_effect=requests.exceptions.ReadTimeout), \
             patch("time.sleep"):
            with self.assertRaises(TimeoutError) as ctx:
                post_json_with_retries(
                    "https://example.com/api",
                    json_body={},
                    max_retries=1,
                )
        self.assertIn("2 attempt(s)", str(ctx.exception))

    def test_succeeds_on_second_attempt_after_timeout(self):
        mock_response = MagicMock()
        side_effects = [requests.exceptions.ReadTimeout, mock_response]
        with patch("requests.post", side_effect=side_effects) as mock_post, \
             patch("time.sleep") as mock_sleep:
            result = post_json_with_retries(
                "https://example.com/api",
                json_body={},
                max_retries=1,
            )
        self.assertIs(result, mock_response)
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(1)  # 2^(1-1) = 1, capped at 4

    def test_sleep_uses_exponential_backoff(self):
        mock_response = MagicMock()
        # Fail twice, succeed on third attempt
        side_effects = [
            requests.exceptions.ReadTimeout,
            requests.exceptions.ReadTimeout,
            mock_response,
        ]
        with patch("requests.post", side_effect=side_effects), \
             patch("time.sleep") as mock_sleep:
            post_json_with_retries("https://example.com/api", json_body={}, max_retries=2)
        # Backoff: attempt 1 -> sleep(1), attempt 2 -> sleep(2)
        self.assertEqual(mock_sleep.call_count, 2)
        self.assertEqual(mock_sleep.call_args_list[0], call(1))
        self.assertEqual(mock_sleep.call_args_list[1], call(2))

    def test_no_retries_raises_immediately_on_timeout(self):
        with patch("requests.post", side_effect=requests.exceptions.ReadTimeout), \
             patch("time.sleep") as mock_sleep:
            with self.assertRaises(TimeoutError):
                post_json_with_retries("https://example.com/api", json_body={}, max_retries=0)
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
