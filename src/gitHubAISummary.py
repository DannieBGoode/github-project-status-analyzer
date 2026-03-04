import json
from datetime import datetime

import requests

import config


REPORT_PROMPT_TEMPLATE = """
Context: You are a CTO's reporting agent. You need to report on achievements, risks, issues at a high level.

Task: Review the following GitHub Project data and write a concise executive report.
Structure:
1. Key Achievements in the last 2 weeks.
2. Risks.
3. Issues and Blockers.
4. Utilization & Throughput (how efficiently we are delivering).

Raw Data: {raw_data}
"""


def build_report_prompt(data):
    return REPORT_PROMPT_TEMPLATE.format(raw_data=json.dumps(data))


def fetch_github_project_data():
    """Fetches items and metadata from GitHub Project V2."""
    url = "https://api.github.com/graphql"

    query = """
    query($id: ID!) {
      node(id: $id) {
        ... on ProjectV2 {
          items(first: 40) {
            nodes {
              content {
                ... on PullRequest { title body state }
                ... on Issue { title body state }
              }
              fieldValueByName(name: "Status") {
                ... on ProjectV2ItemFieldSingleSelectValue { name }
              }
            }
          }
        }
      }
    }
    """

    headers = {"Authorization": f"Bearer {config.GITHUB_TOKEN}"}
    variables = {"id": config.PROJECT_ID}

    response = requests.post(
        url,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_gemini_summary(prompt):
    """Generates an executive summary using Gemini."""
    model = getattr(config, "GEMINI_MODEL", "gemini-2.5-flash")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={config.GEMINI_API_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()

    # TODO: Validate model output format before returning.
    return result["candidates"][0]["content"]["parts"][0]["text"]


def get_openai_summary(prompt):
    """Generates an executive summary using OpenAI Chat Completions."""
    model = getattr(config, "OPENAI_MODEL", "gpt-4.1-mini")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
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

    # TODO: Validate model output format before returning.
    return result["choices"][0]["message"]["content"]


def generate_summary(data):
    provider = getattr(config, "AI_PROVIDER", "gemini").strip().lower()
    prompt = build_report_prompt(data)

    if provider == "gemini":
        return get_gemini_summary(prompt)
    if provider == "openai":
        return get_openai_summary(prompt)

    raise ValueError("AI_PROVIDER must be either 'gemini' or 'openai'.")


def run_report():
    provider = getattr(config, "AI_PROVIDER", "gemini").strip().lower()

    print(f"[{datetime.now()}] Fetching GitHub data...")
    raw_data = fetch_github_project_data()

    print(f"[{datetime.now()}] Generating AI summary with provider: {provider}...")
    summary = generate_summary(raw_data)

    # TODO: Write the summary into a Google Doc.
    # TODO: Send this to a Slack webhook.

    print("\n--- EXECUTIVE REPORT ---\n")
    print(summary)


if __name__ == "__main__":
    run_report()
