from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    github_token: str
    project_id: str
    project_url: str
    ai_provider: str
    lookback_days: int
    max_items: int
    max_comments_per_item: int
    gemini_api_key: str
    gemini_model: str
    openai_api_key: str
    openai_model: str
    ai_timeout_seconds: int
    ai_max_retries: int
    report_timezone: str
    report_timezone_label: str

    @property
    def effective_max_items(self):
        return min(self.max_items, 100)


def load_settings(config_module):
    return Settings(
        github_token=getattr(config_module, "GITHUB_TOKEN", "").strip(),
        project_id=getattr(config_module, "PROJECT_ID", "").strip(),
        project_url=getattr(config_module, "PROJECT_URL", "").strip(),
        ai_provider=getattr(config_module, "AI_PROVIDER", "gemini").strip().lower(),
        lookback_days=int(getattr(config_module, "LOOKBACK_DAYS", 14)),
        max_items=int(getattr(config_module, "MAX_ITEMS", 100)),
        max_comments_per_item=int(
            getattr(config_module, "MAX_COMMENTS_PER_ITEM", 20)
        ),
        gemini_api_key=getattr(config_module, "GEMINI_API_KEY", "").strip(),
        gemini_model=getattr(
            config_module, "GEMINI_MODEL", "gemini-2.5-flash-lite-preview-09-2025"
        ).strip(),
        openai_api_key=getattr(config_module, "OPENAI_API_KEY", "").strip(),
        openai_model=getattr(config_module, "OPENAI_MODEL", "gpt-5-nano").strip(),
        ai_timeout_seconds=int(getattr(config_module, "AI_TIMEOUT_SECONDS", 120)),
        ai_max_retries=int(getattr(config_module, "AI_MAX_RETRIES", 1)),
        report_timezone=getattr(config_module, "REPORT_TIMEZONE", "").strip(),
        report_timezone_label=getattr(
            config_module, "REPORT_TIMEZONE_LABEL", ""
        ).strip(),
    )
