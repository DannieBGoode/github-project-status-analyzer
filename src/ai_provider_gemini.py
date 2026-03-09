from ai_http import post_json_with_retries


def get_gemini_summary(api_key, model, prompt, timeout_seconds, max_retries):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = post_json_with_retries(
        url,
        headers=headers,
        json_body=payload,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    response.raise_for_status()
    result = response.json()
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            f"Gemini API returned unexpected response structure: {result}"
        ) from exc
