from ai_http import post_json_with_retries


def get_gemini_summary(api_key, model, prompt, timeout_seconds, max_retries):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = post_json_with_retries(
        url,
        json_body=payload,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    response.raise_for_status()
    result = response.json()
    return result["candidates"][0]["content"]["parts"][0]["text"]
