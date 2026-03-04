from ai_http import post_json_with_retries


def _extract_text_from_responses_api(result):
    output_text = result.get("output_text")
    if output_text:
        return output_text

    for item in result.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return content["text"]

    return None


def get_openai_summary(api_key, model, prompt, timeout_seconds, max_retries):
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": prompt,
    }

    response = post_json_with_retries(
        url,
        headers=headers,
        json_body=payload,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    if response.status_code >= 400:
        raise ValueError(
            f"OpenAI API error ({response.status_code}): {response.text}"
        )
    result = response.json()
    text = _extract_text_from_responses_api(result)
    if text:
        return text

    # Backward compatibility if API returns chat-like payload.
    choices = result.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        if message.get("content"):
            return message["content"]

    raise ValueError("OpenAI API returned no text content.")
