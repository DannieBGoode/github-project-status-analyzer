import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from github_client import github_graphql_request


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    if status_code >= 400:
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} Error", response=mock
        )
    return mock


class TestGithubGraphqlRequest(unittest.TestCase):
    def _call(self, json_data=None, status_code=200, side_effect=None):
        if side_effect:
            with patch("github_client.requests.post", side_effect=side_effect):
                return github_graphql_request("ghp_token", "query { }", {})
        resp = _mock_response(json_data or {"data": {}}, status_code)
        with patch("github_client.requests.post", return_value=resp):
            return github_graphql_request("ghp_token", "query { }", {})

    def test_returns_body_on_success(self):
        body = self._call(json_data={"data": {"node": {"id": "PVT_abc"}}})
        self.assertEqual(body["data"]["node"]["id"], "PVT_abc")

    def test_authorization_header_uses_bearer_token(self):
        resp = _mock_response({"data": {}})
        with patch("github_client.requests.post", return_value=resp) as mock_post:
            github_graphql_request("ghp_mytoken", "query { }", {})
        _, kwargs = mock_post.call_args
        self.assertIn("Authorization", kwargs["headers"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer ghp_mytoken")

    def test_posts_to_github_graphql_endpoint(self):
        resp = _mock_response({"data": {}})
        with patch("github_client.requests.post", return_value=resp) as mock_post:
            github_graphql_request("token", "query { }", {})
        url = mock_post.call_args[0][0]
        self.assertEqual(url, "https://api.github.com/graphql")

    def test_sends_query_and_variables(self):
        resp = _mock_response({"data": {}})
        with patch("github_client.requests.post", return_value=resp) as mock_post:
            github_graphql_request("token", "query Q { }", {"id": "PVT_123"})
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["query"], "query Q { }")
        self.assertEqual(kwargs["json"]["variables"], {"id": "PVT_123"})

    def test_raises_on_http_error(self):
        resp = _mock_response({"message": "Bad credentials"}, status_code=401)
        with patch("github_client.requests.post", return_value=resp):
            with self.assertRaises(requests.exceptions.HTTPError):
                github_graphql_request("bad_token", "query { }", {})

    def test_raises_value_error_on_graphql_errors(self):
        body = {"errors": [{"message": "Field 'node' doesn't exist"}]}
        with self.assertRaises(ValueError) as ctx:
            self._call(json_data=body)
        self.assertIn("GitHub GraphQL error", str(ctx.exception))

    def test_graphql_error_message_included(self):
        body = {"errors": [{"message": "Could not resolve to a node"}]}
        with self.assertRaises(ValueError) as ctx:
            self._call(json_data=body)
        self.assertIn("Could not resolve to a node", str(ctx.exception))

    def test_network_timeout_propagates(self):
        with patch("github_client.requests.post",
                   side_effect=requests.exceptions.ReadTimeout):
            with self.assertRaises(requests.exceptions.ReadTimeout):
                github_graphql_request("token", "query { }", {})

    def test_connection_error_propagates(self):
        with patch("github_client.requests.post",
                   side_effect=requests.exceptions.ConnectionError("DNS failure")):
            with self.assertRaises(requests.exceptions.ConnectionError):
                github_graphql_request("token", "query { }", {})

    def test_raise_for_status_called(self):
        resp = _mock_response({"data": {}})
        with patch("github_client.requests.post", return_value=resp):
            github_graphql_request("token", "query { }", {})
        resp.raise_for_status.assert_called_once()

    def test_empty_data_body_returned_without_error(self):
        body = {"data": {"node": None}}
        result = self._call(json_data=body)
        self.assertIsNone(result["data"]["node"])


if __name__ == "__main__":
    unittest.main()
