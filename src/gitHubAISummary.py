import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.append(str(Path(__file__).resolve().parent.parent))
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


def github_graphql_request(query, variables):
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()

    if "errors" in body:
        raise ValueError(f"GitHub GraphQL error: {body['errors']}")

    return body


def parse_project_v2_url(project_url):
    """Parses org/user project V2 URLs and returns (scope, owner, project_number)."""
    parsed = urlparse(project_url)
    parts = [p for p in parsed.path.split("/") if p]

    # Supported formats:
    # - /orgs/<org>/projects/<number>
    # - /users/<username>/projects/<number>
    if len(parts) == 4 and parts[2] == "projects" and parts[3].isdigit():
        scope = parts[0]
        owner = parts[1]
        project_number = int(parts[3])

        if scope not in {"orgs", "users"}:
            raise ValueError(
                "Unsupported project URL scope. Use /orgs/<org>/projects/<n> "
                "or /users/<user>/projects/<n>."
            )

        return scope, owner, project_number

    raise ValueError(
        "PROJECT_URL format not recognized. Expected: "
        "https://github.com/orgs/<org>/projects/<n> or "
        "https://github.com/users/<user>/projects/<n>."
    )


def resolve_project_id_from_url(project_url):
    """Resolves a GitHub Project V2 URL into a GraphQL node ID."""
    scope, owner, project_number = parse_project_v2_url(project_url)

    if scope == "orgs":
        query = """
        query($owner: String!, $number: Int!) {
          organization(login: $owner) {
            projectV2(number: $number) {
              id
            }
          }
        }
        """
        body = github_graphql_request(
            query, {"owner": owner, "number": project_number}
        )
        project = body.get("data", {}).get("organization", {}).get("projectV2")
    else:
        query = """
        query($owner: String!, $number: Int!) {
          user(login: $owner) {
            projectV2(number: $number) {
              id
            }
          }
        }
        """
        body = github_graphql_request(
            query, {"owner": owner, "number": project_number}
        )
        project = body.get("data", {}).get("user", {}).get("projectV2")

    if not project or not project.get("id"):
        raise ValueError(
            "Could not resolve PROJECT_ID from PROJECT_URL. "
            "Check URL correctness and token permissions."
        )

    return project["id"]


def get_project_id():
    """Returns PROJECT_ID directly or resolves it from PROJECT_URL."""
    project_id = getattr(config, "PROJECT_ID", "").strip()
    if project_id:
        return project_id

    project_url = getattr(config, "PROJECT_URL", "").strip()
    if not project_url:
        raise ValueError("Set PROJECT_ID or PROJECT_URL in config.py.")

    resolved_id = resolve_project_id_from_url(project_url)
    print(f"[{datetime.now()}] Resolved PROJECT_ID from PROJECT_URL: {resolved_id}")
    return resolved_id


def fetch_github_project_data(project_id):
    """Fetches items and metadata from GitHub Project V2."""
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

    body = github_graphql_request(query, {"id": project_id})
    return body


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

    print(f"[{datetime.now()}] Resolving target project...")
    project_id = get_project_id()

    print(f"[{datetime.now()}] Fetching GitHub data...")
    raw_data = fetch_github_project_data(project_id)

    print(f"[{datetime.now()}] Generating AI summary with provider: {provider}...")
    summary = generate_summary(raw_data)

    # TODO: Write the summary into a Google Doc.
    # TODO: Send this to a Slack webhook.

    print("\n--- EXECUTIVE REPORT ---\n")
    print(summary)


if __name__ == "__main__":
    run_report()
