import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from project_target import parse_project_v2_url, resolve_project_id_from_url, get_project_id


class TestProjectTarget(unittest.TestCase):
    def test_parse_project_v2_url_org(self):
        scope, owner, number = parse_project_v2_url("https://github.com/orgs/acme/projects/26")
        self.assertEqual((scope, owner, number), ("orgs", "acme", 26))

    def test_parse_project_v2_url_user(self):
        scope, owner, number = parse_project_v2_url("https://github.com/users/octocat/projects/3")
        self.assertEqual((scope, owner, number), ("users", "octocat", 3))

    def test_parse_project_v2_url_rejects_unknown_shape(self):
        with self.assertRaises(ValueError):
            parse_project_v2_url("https://github.com/acme/repo/issues/1")


class TestParseProjectV2UrlEdgeCases(unittest.TestCase):
    def test_rejects_repos_scope(self):
        with self.assertRaises(ValueError) as ctx:
            parse_project_v2_url("https://github.com/repos/acme/projects/1")
        self.assertIn("Unsupported project URL scope", str(ctx.exception))

    def test_rejects_teams_scope(self):
        with self.assertRaises(ValueError) as ctx:
            parse_project_v2_url("https://github.com/teams/acme/projects/1")
        self.assertIn("Unsupported project URL scope", str(ctx.exception))

    def test_rejects_missing_project_number(self):
        with self.assertRaises(ValueError):
            parse_project_v2_url("https://github.com/orgs/acme/projects/")

    def test_rejects_non_numeric_project_number(self):
        with self.assertRaises(ValueError):
            parse_project_v2_url("https://github.com/orgs/acme/projects/beta")

    def test_rejects_too_short_path(self):
        with self.assertRaises(ValueError):
            parse_project_v2_url("https://github.com/orgs/projects/1")


class TestResolveProjectIdFromUrl(unittest.TestCase):
    def _mock_graphql(self, return_value):
        return patch("project_target.github_graphql_request", return_value=return_value)

    def test_resolves_org_project_id(self):
        body = {"data": {"organization": {"projectV2": {"id": "PVT_org123"}}}}
        with self._mock_graphql(body):
            result = resolve_project_id_from_url(
                "ghp_token", "https://github.com/orgs/acme/projects/1"
            )
        self.assertEqual(result, "PVT_org123")

    def test_resolves_user_project_id(self):
        body = {"data": {"user": {"projectV2": {"id": "PVT_user456"}}}}
        with self._mock_graphql(body):
            result = resolve_project_id_from_url(
                "ghp_token", "https://github.com/users/octocat/projects/3"
            )
        self.assertEqual(result, "PVT_user456")

    def test_raises_when_project_not_found(self):
        body = {"data": {"organization": {"projectV2": None}}}
        with self._mock_graphql(body):
            with self.assertRaises(ValueError) as ctx:
                resolve_project_id_from_url(
                    "ghp_token", "https://github.com/orgs/acme/projects/999"
                )
        self.assertIn("Could not resolve PROJECT_ID", str(ctx.exception))

    def test_raises_when_project_has_no_id(self):
        body = {"data": {"organization": {"projectV2": {"id": ""}}}}
        with self._mock_graphql(body):
            with self.assertRaises(ValueError):
                resolve_project_id_from_url(
                    "ghp_token", "https://github.com/orgs/acme/projects/1"
                )

    def test_raises_when_org_key_missing(self):
        body = {"data": {}}
        with self._mock_graphql(body):
            with self.assertRaises(ValueError):
                resolve_project_id_from_url(
                    "ghp_token", "https://github.com/orgs/acme/projects/1"
                )

    def test_uses_org_query_for_orgs_scope(self):
        from github_queries import PROJECT_ID_BY_ORG_QUERY, PROJECT_ID_BY_USER_QUERY
        body = {"data": {"organization": {"projectV2": {"id": "PVT_x"}}}}
        with patch("project_target.github_graphql_request", return_value=body) as mock_gql:
            resolve_project_id_from_url(
                "ghp_token", "https://github.com/orgs/acme/projects/5"
            )
        actual_query = mock_gql.call_args[0][1]
        self.assertEqual(actual_query, PROJECT_ID_BY_ORG_QUERY)

    def test_uses_user_query_for_users_scope(self):
        from github_queries import PROJECT_ID_BY_USER_QUERY
        body = {"data": {"user": {"projectV2": {"id": "PVT_y"}}}}
        with patch("project_target.github_graphql_request", return_value=body) as mock_gql:
            resolve_project_id_from_url(
                "ghp_token", "https://github.com/users/octocat/projects/2"
            )
        actual_query = mock_gql.call_args[0][1]
        self.assertEqual(actual_query, PROJECT_ID_BY_USER_QUERY)


class TestGetProjectId(unittest.TestCase):
    def test_returns_explicit_project_id_without_api_call(self):
        with patch("project_target.resolve_project_id_from_url") as mock_resolve:
            result = get_project_id("token", "PVT_explicit", "")
        self.assertEqual(result, "PVT_explicit")
        mock_resolve.assert_not_called()

    def test_explicit_id_takes_precedence_over_url(self):
        with patch("project_target.resolve_project_id_from_url") as mock_resolve:
            result = get_project_id(
                "token", "PVT_explicit", "https://github.com/orgs/acme/projects/1"
            )
        self.assertEqual(result, "PVT_explicit")
        mock_resolve.assert_not_called()

    def test_resolves_from_url_when_no_id(self):
        with patch(
            "project_target.resolve_project_id_from_url", return_value="PVT_from_url"
        ) as mock_resolve:
            result = get_project_id(
                "token", "", "https://github.com/orgs/acme/projects/1"
            )
        self.assertEqual(result, "PVT_from_url")
        mock_resolve.assert_called_once()

    def test_raises_when_both_missing(self):
        with self.assertRaises(ValueError) as ctx:
            get_project_id("token", "", "")
        self.assertIn("PROJECT_ID", str(ctx.exception))
        self.assertIn("PROJECT_URL", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
