import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from settings import load_settings, Settings


def _make_config(**kwargs):
    mod = types.ModuleType("config")
    for k, v in kwargs.items():
        setattr(mod, k, v)
    return mod


class TestLoadSettings(unittest.TestCase):
    def test_defaults_applied_when_no_attrs(self):
        cfg = _make_config()
        s = load_settings(cfg)
        self.assertEqual(s.github_token, "")
        self.assertEqual(s.ai_provider, "gemini")
        self.assertEqual(s.lookback_days, 14)
        self.assertEqual(s.max_items, 100)
        self.assertEqual(s.max_comments_per_item, 20)
        self.assertEqual(s.ai_timeout_seconds, 120)
        self.assertEqual(s.ai_max_retries, 1)

    def test_explicit_values_used(self):
        cfg = _make_config(
            GITHUB_TOKEN="ghp_abc",
            PROJECT_URL="https://github.com/orgs/acme/projects/1",
            AI_PROVIDER="openai",
            LOOKBACK_DAYS=7,
            MAX_ITEMS=50,
        )
        s = load_settings(cfg)
        self.assertEqual(s.github_token, "ghp_abc")
        self.assertEqual(s.project_url, "https://github.com/orgs/acme/projects/1")
        self.assertEqual(s.ai_provider, "openai")
        self.assertEqual(s.lookback_days, 7)
        self.assertEqual(s.max_items, 50)

    def test_ai_provider_lowercased_and_stripped(self):
        cfg = _make_config(AI_PROVIDER="  Gemini  ")
        s = load_settings(cfg)
        self.assertEqual(s.ai_provider, "gemini")

    def test_github_token_stripped(self):
        cfg = _make_config(GITHUB_TOKEN="  ghp_token  ")
        s = load_settings(cfg)
        self.assertEqual(s.github_token, "ghp_token")


class TestEffectiveMaxItems(unittest.TestCase):
    def test_caps_at_100_when_over(self):
        cfg = _make_config(MAX_ITEMS=200)
        s = load_settings(cfg)
        self.assertEqual(s.effective_max_items, 100)

    def test_returns_value_unchanged_when_under_100(self):
        cfg = _make_config(MAX_ITEMS=60)
        s = load_settings(cfg)
        self.assertEqual(s.effective_max_items, 60)

    def test_returns_100_exactly_at_limit(self):
        cfg = _make_config(MAX_ITEMS=100)
        s = load_settings(cfg)
        self.assertEqual(s.effective_max_items, 100)


if __name__ == "__main__":
    unittest.main()
