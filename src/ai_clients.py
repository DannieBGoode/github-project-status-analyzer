import requests


def get_gemini_summary(api_key, model, prompt):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    return result["candidates"][0]["content"]["parts"][0]["text"]


def get_openai_summary(api_key, model, prompt):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]


def generate_summary(provider, prompt, gemini_api_key, gemini_model, openai_api_key, openai_model):
    if provider == "gemini":
        return get_gemini_summary(gemini_api_key, gemini_model, prompt)
    if provider == "openai":
        return get_openai_summary(openai_api_key, openai_model, prompt)
    raise ValueError("AI_PROVIDER must be either 'gemini' or 'openai'.")
