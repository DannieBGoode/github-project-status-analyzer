import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ai_http import post_json_with_retries


def _make_session_mock(side_effects):
    """
    Build a mock for `requests.Session` used as a context manager.
    `side_effects` is passed to the `session.post` mock as `side_effect`.
    Returns (MockSession, mock_session_instance).
    """
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    if isinstance(side_effects, list):
        mock_session.post.side_effect = side_effects
    else:
        mock_session.post.side_effect = side_effects
    MockSession = MagicMock(return_value=mock_session)
    return MockSession, mock_session


class TestPostJsonWithRetries(unittest.TestCase):
    def test_returns_response_on_first_success(self):
        mock_response = MagicMock()
        MockSession, mock_session = _make_session_mock([mock_response])
        with patch("ai_http.requests.Session", MockSession), \
             patch("time.sleep") as mock_sleep:
            result = post_json_with_retries(
                "https://example.com/api",
                json_body={"key": "value"},
                headers={"Authorization": "Bearer token"},
                timeout_seconds=30,
                max_retries=0,
            )
        self.assertIs(result, mock_response)
        mock_session.post.assert_called_once()
        mock_sleep.assert_not_called()

    def test_raises_timeout_error_after_exhausting_retries(self):
        MockSession, _ = _make_session_mock(requests.exceptions.ReadTimeout)
        with patch("ai_http.requests.Session", MockSession), \
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
        MockSession, mock_session = _make_session_mock(side_effects)
        with patch("ai_http.requests.Session", MockSession), \
             patch("time.sleep") as mock_sleep:
            result = post_json_with_retries(
                "https://example.com/api",
                json_body={},
                max_retries=1,
            )
        self.assertIs(result, mock_response)
        self.assertEqual(mock_session.post.call_count, 2)
        mock_sleep.assert_called_once_with(1)  # 2^(1-1) = 1, capped at 4

    def test_sleep_uses_exponential_backoff(self):
        mock_response = MagicMock()
        side_effects = [
            requests.exceptions.ReadTimeout,
            requests.exceptions.ReadTimeout,
            mock_response,
        ]
        MockSession, _ = _make_session_mock(side_effects)
        with patch("ai_http.requests.Session", MockSession), \
             patch("time.sleep") as mock_sleep:
            post_json_with_retries("https://example.com/api", json_body={}, max_retries=2)
        # Backoff: attempt 1 -> sleep(1), attempt 2 -> sleep(2)
        self.assertEqual(mock_sleep.call_count, 2)
        self.assertEqual(mock_sleep.call_args_list[0], call(1))
        self.assertEqual(mock_sleep.call_args_list[1], call(2))

    def test_no_retries_raises_immediately_on_timeout(self):
        MockSession, _ = _make_session_mock(requests.exceptions.ReadTimeout)
        with patch("ai_http.requests.Session", MockSession), \
             patch("time.sleep") as mock_sleep:
            with self.assertRaises(TimeoutError):
                post_json_with_retries("https://example.com/api", json_body={}, max_retries=0)
        mock_sleep.assert_not_called()

    def test_session_used_as_context_manager(self):
        """Session must be used as a context manager so connections are released."""
        mock_response = MagicMock()
        MockSession, mock_session = _make_session_mock([mock_response])
        with patch("ai_http.requests.Session", MockSession), \
             patch("time.sleep"):
            post_json_with_retries("https://example.com/api", json_body={})
        mock_session.__enter__.assert_called_once()
        mock_session.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()
