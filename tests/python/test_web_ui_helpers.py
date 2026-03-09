import sys
import types
import unittest
from pathlib import Path

# web_ui.py lives at the repo root; add it to the path.
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# web_ui.py appends src/ itself on import, but pre-seed it so sub-imports work.
_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# Stub out `config` before web_ui is imported so the module-level `import config` succeeds.
if "config" not in sys.modules:
    sys.modules["config"] = types.ModuleType("config")

import web_ui  # noqa: E402  (intentional late import after path/module setup)

from settings import load_settings  # noqa: E402


def _make_base_settings(**overrides):
    """Build a minimal Settings object via load_settings with a stub config."""
    cfg = types.ModuleType("cfg")
    cfg.GITHUB_TOKEN = "ghp_base"
    cfg.PROJECT_URL = "https://github.com/orgs/acme/projects/1"
    cfg.PROJECT_ID = ""
    cfg.AI_PROVIDER = "gemini"
    cfg.GEMINI_API_KEY = "g_base"
    cfg.OPENAI_API_KEY = "o_base"
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return load_settings(cfg)


class TestMaskSecret(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(web_ui.mask_secret(""), "")

    def test_short_value_all_stars(self):
        result = web_ui.mask_secret("abc")
        self.assertEqual(result, "***")
        self.assertEqual(len(result), 3)

    def test_exactly_8_chars_all_stars(self):
        result = web_ui.mask_secret("12345678")
        self.assertTrue(all(c == "*" for c in result))

    def test_long_value_masked_in_middle(self):
        result = web_ui.mask_secret("abcdefghij")  # 10 chars
        self.assertTrue(result.startswith("abcd"))
        self.assertTrue(result.endswith("ghij"))
        self.assertIn("*", result)


class TestParseInt(unittest.TestCase):
    def test_valid_string(self):
        self.assertEqual(web_ui.parse_int("5", 0), 5)

    def test_none_returns_fallback(self):
        self.assertEqual(web_ui.parse_int(None, 3), 3)

    def test_non_numeric_returns_fallback(self):
        self.assertEqual(web_ui.parse_int("bad", 7), 7)

    def test_integer_input(self):
        self.assertEqual(web_ui.parse_int(42, 0), 42)


class TestNormalizeModel(unittest.TestCase):
    def test_known_model_returned_unchanged(self):
        result = web_ui.normalize_model("gemini", "gemini-2.5-flash")
        self.assertEqual(result, "gemini-2.5-flash")

    def test_unknown_model_falls_back_to_cheapest(self):
        result = web_ui.normalize_model("gemini", "nonexistent-model")
        cheapest = web_ui.cheapest_model("gemini")
        self.assertEqual(result, cheapest)

    def test_unknown_provider_returns_empty(self):
        result = web_ui.normalize_model("unknown_provider", "some-model")
        self.assertEqual(result, "")


class TestBuildRuntimeSettings(unittest.TestCase):
    def test_masked_github_token_uses_base(self):
        base = _make_base_settings()
        payload = {"github_token": "ghp_****abcd"}
        result = web_ui.build_runtime_settings(payload, base)
        self.assertEqual(result.github_token, base.github_token)

    def test_new_github_token_from_payload(self):
        base = _make_base_settings()
        payload = {"github_token": "ghp_newtoken"}
        result = web_ui.build_runtime_settings(payload, base)
        self.assertEqual(result.github_token, "ghp_newtoken")

    def test_ai_provider_from_payload(self):
        base = _make_base_settings()
        payload = {"ai_provider": "openai"}
        result = web_ui.build_runtime_settings(payload, base)
        self.assertEqual(result.ai_provider, "openai")

    def test_max_items_clamped_to_100(self):
        base = _make_base_settings()
        payload = {"max_items": 200}
        result = web_ui.build_runtime_settings(payload, base)
        self.assertLessEqual(result.max_items, 100)

    def test_project_id_always_cleared(self):
        base = _make_base_settings()
        result = web_ui.build_runtime_settings({}, base)
        self.assertEqual(result.project_id, "")


class TestRedactError(unittest.TestCase):
    def test_redacts_gemini_query_param(self):
        exc = Exception("https://example.com?key=AIzaSyABCDEF1234")
        result = web_ui.redact_error(exc)
        self.assertNotIn("AIzaSyABCDEF1234", result)
        self.assertIn("key=***", result)

    def test_redacts_bearer_token(self):
        exc = Exception("Authorization: Bearer sk-proj-abcdef1234567890")
        result = web_ui.redact_error(exc)
        self.assertNotIn("abcdef1234567890", result)

    def test_redacts_github_ghp_token(self):
        exc = Exception("token ghp_realtoken123456")
        result = web_ui.redact_error(exc)
        self.assertNotIn("realtoken123456", result)
        self.assertIn("ghp_***", result)

    def test_redacts_github_ghu_token(self):
        exc = Exception("auth ghu_sometoken999")
        result = web_ui.redact_error(exc)
        self.assertNotIn("sometoken999", result)

    def test_redacts_openai_sk_token(self):
        exc = Exception("key=sk-proj-abcd1234xyz")
        result = web_ui.redact_error(exc)
        self.assertNotIn("1234xyz", result)

    def test_redacts_x_goog_api_key_header(self):
        exc = Exception('headers: {"x-goog-api-key": "AIzaSySecret"}')
        result = web_ui.redact_error(exc)
        self.assertNotIn("AIzaSySecret", result)

    def test_preserves_non_secret_text(self):
        exc = Exception("Network connection refused")
        result = web_ui.redact_error(exc)
        self.assertEqual(result, "Network connection refused")


class TestBuildRuntimeSettingsMasking(unittest.TestCase):
    def setUp(self):
        self.base = _make_base_settings()

    def test_masked_gemini_api_key_uses_base(self):
        payload = {"gemini_api_key": "AIza****abcd"}
        result = web_ui.build_runtime_settings(payload, self.base)
        self.assertEqual(result.gemini_api_key, self.base.gemini_api_key)

    def test_new_gemini_api_key_from_payload(self):
        payload = {"gemini_api_key": "AIzaSyNewKey"}
        result = web_ui.build_runtime_settings(payload, self.base)
        self.assertEqual(result.gemini_api_key, "AIzaSyNewKey")

    def test_masked_openai_api_key_uses_base(self):
        payload = {"openai_api_key": "sk-****abcd"}
        result = web_ui.build_runtime_settings(payload, self.base)
        self.assertEqual(result.openai_api_key, self.base.openai_api_key)

    def test_new_openai_api_key_from_payload(self):
        payload = {"openai_api_key": "sk-proj-newkey"}
        result = web_ui.build_runtime_settings(payload, self.base)
        self.assertEqual(result.openai_api_key, "sk-proj-newkey")


class TestBuildRuntimeSettingsModelSelection(unittest.TestCase):
    def setUp(self):
        self.base = _make_base_settings()

    def test_valid_gemini_model_applied(self):
        cheapest = web_ui.cheapest_model("gemini")
        all_ids = web_ui.model_ids("gemini")
        # pick a known model that exists
        model = all_ids[0] if all_ids else cheapest
        payload = {"ai_provider": "gemini", "model": model}
        result = web_ui.build_runtime_settings(payload, self.base)
        self.assertEqual(result.gemini_model, model)

    def test_invalid_gemini_model_falls_back_to_cheapest(self):
        payload = {"ai_provider": "gemini", "model": "nonexistent-model-xyz"}
        result = web_ui.build_runtime_settings(payload, self.base)
        self.assertEqual(result.gemini_model, web_ui.cheapest_model("gemini"))

    def test_valid_openai_model_applied(self):
        all_ids = web_ui.model_ids("openai")
        model = all_ids[0] if all_ids else web_ui.cheapest_model("openai")
        payload = {"ai_provider": "openai", "model": model}
        result = web_ui.build_runtime_settings(payload, self.base)
        self.assertEqual(result.openai_model, model)

    def test_no_model_in_payload_uses_cheapest(self):
        payload = {"ai_provider": "gemini"}
        result = web_ui.build_runtime_settings(payload, self.base)
        self.assertEqual(result.gemini_model, web_ui.cheapest_model("gemini"))


if __name__ == "__main__":
    unittest.main()
