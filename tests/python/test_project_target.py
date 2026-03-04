import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from project_target import parse_project_v2_url


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


if __name__ == "__main__":
    unittest.main()
