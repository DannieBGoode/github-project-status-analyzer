from ai_provider_gemini import get_gemini_summary
from ai_provider_openai import get_openai_summary


def generate_summary(
    provider,
    prompt,
    gemini_api_key,
    gemini_model,
    openai_api_key,
    openai_model,
    timeout_seconds=120,
    max_retries=0,
):
    if provider == "gemini":
        return get_gemini_summary(
            gemini_api_key,
            gemini_model,
            prompt,
            timeout_seconds,
            max_retries,
        )
    if provider == "openai":
        return get_openai_summary(
            openai_api_key,
            openai_model,
            prompt,
            timeout_seconds,
            max_retries,
        )
    raise ValueError("AI_PROVIDER must be either 'gemini' or 'openai'.")
