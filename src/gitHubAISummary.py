import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config


REPORT_PROMPT_TEMPLATE = """
Context: You are a CTO reporting agent.

Current Date: {current_date}
Lookback Window: Last {lookback_days} days (since {cutoff_date})
Project Name: {project_title}
Project URL: {project_url}

Task:
Write a concise executive report using ONLY the provided data.

Mandatory output rules:
- Use the exact Current Date above. Never output placeholders like [Current Date].
- Format output as Markdown headings:
  - Use `##` for major sections.
  - Use `###` for subsection breakdowns where helpful.
  - Do not use bold text as a substitute for headings.
- At the top of the report, include exactly these 3 bullet metrics in this order with their values between backlashes:
  - `- Total Items Fetched`
  - `- Items Updated in Lookback Window`
  - `- Comments Created in Lookback Window`
- Keep ONLY this section structure (as `##` headings):
  1. Key Achievements in the last {lookback_days} days
  2. Risks
  3. Issues and Blockers
- Do NOT include sections named `Utilization & Throughput` or `Data Scope Notes`.
- Apply these definitions strictly:
  - `Risks`: external or uncertain factors not directly controlled by the team that may cause future delay.
  - `Issues`: risks that have already materialized and are currently impacting delivery.
  - `Blockers`: concrete dependencies that block task completion (for example, waiting on another team/system/approval).
- In `Issues and Blockers` separate content with `### Issues` and `### Blockers`.
- If there are none, explicitly state:
  - `No risks.`
  - `No issues.`
  - `No blockers.`
- Whenever referencing an issue or pull request, use a Markdown hyperlink format like `[#1234](https://github.com/org/repo/issues/1234)` using URLs from the provided data.

Data Payload:
{raw_data}
"""


def parse_github_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def truncate_text(value, limit=600):
    if value is None:
        return ""
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def build_report_prompt(data):
    lookback_days = int(getattr(config, "LOOKBACK_DAYS", 14))
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=lookback_days)

    project = data.get("project", {})
    project_title = project.get("title") or "Unknown Project"
    project_url = project.get("url") or "Unknown URL"

    return REPORT_PROMPT_TEMPLATE.format(
        current_date=now_utc.strftime("%Y-%m-%d"),
        lookback_days=lookback_days,
        cutoff_date=cutoff.strftime("%Y-%m-%d"),
        project_title=project_title,
        project_url=project_url,
        raw_data=json.dumps(data),
    )


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
    configured_item_limit = int(getattr(config, "MAX_ITEMS", 100))
    item_limit = min(configured_item_limit, 100)
    if configured_item_limit > 100:
        print(
            f"[{datetime.now()}] MAX_ITEMS={configured_item_limit} exceeds GitHub "
            "GraphQL limit (100); using 100."
        )
    comment_limit = int(getattr(config, "MAX_COMMENTS_PER_ITEM", 20))

    query = """
    query($id: ID!, $itemLimit: Int!, $commentLimit: Int!) {
      node(id: $id) {
        ... on ProjectV2 {
          title
          url
          items(first: $itemLimit) {
            nodes {
              updatedAt
              content {
                ... on PullRequest {
                  number
                  title
                  body
                  state
                  url
                  createdAt
                  updatedAt
                  comments(last: $commentLimit) {
                    totalCount
                    nodes {
                      bodyText
                      createdAt
                      updatedAt
                      url
                      author {
                        login
                      }
                    }
                  }
                  reviews { totalCount }
                }
                ... on Issue {
                  number
                  title
                  body
                  state
                  url
                  createdAt
                  updatedAt
                  comments(last: $commentLimit) {
                    totalCount
                    nodes {
                      bodyText
                      createdAt
                      updatedAt
                      url
                      author {
                        login
                      }
                    }
                  }
                }
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

    return github_graphql_request(
        query,
        {"id": project_id, "itemLimit": item_limit, "commentLimit": comment_limit},
    )


def build_analysis_payload(raw_data):
    """Builds prompt payload with explicit query scope and time-window stats."""
    project = raw_data.get("data", {}).get("node", {}) or {}
    items = project.get("items", {}).get("nodes", []) or []

    lookback_days = int(getattr(config, "LOOKBACK_DAYS", 14))
    max_comments_per_item = int(getattr(config, "MAX_COMMENTS_PER_ITEM", 20))
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=lookback_days)

    recent_count = 0
    recent_comments_total = 0
    filtered_items = []
    for item in items:
        item_updated_at = parse_github_datetime(item.get("updatedAt"))
        content = item.get("content") or {}
        content_updated_at = parse_github_datetime(content.get("updatedAt"))

        is_recent = False
        if item_updated_at and item_updated_at >= cutoff:
            is_recent = True
        if content_updated_at and content_updated_at >= cutoff:
            is_recent = True

        if is_recent:
            recent_count += 1

        comments = content.get("comments", {}).get("nodes", []) or []
        recent_comments = []
        for comment in comments:
            created_at = parse_github_datetime(comment.get("createdAt"))
            if created_at and created_at >= cutoff:
                recent_comments.append(
                    {
                        "author": (comment.get("author") or {}).get("login"),
                        "createdAt": comment.get("createdAt"),
                        "updatedAt": comment.get("updatedAt"),
                        "url": comment.get("url"),
                        "bodyText": truncate_text(comment.get("bodyText")),
                    }
                )

        recent_comments_total += len(recent_comments)

        filtered_content = dict(content)
        filtered_content["recentComments"] = recent_comments
        filtered_content.pop("comments", None)
        filtered_items.append(
            {
                **item,
                "content": filtered_content,
            }
        )

    return {
        "project": {
            "title": project.get("title"),
            "url": project.get("url"),
        },
        "query_scope": {
            "description": "Fetched Project V2 items via GitHub GraphQL.",
            "item_limit": min(int(getattr(config, "MAX_ITEMS", 100)), 100),
            "comment_limit_per_item": max_comments_per_item,
            "lookback_days": lookback_days,
            "lookback_start_utc": cutoff.isoformat(),
            "queried_fields": [
                "project.title",
                "project.url",
                "project.items.nodes.updatedAt",
                "content for Issue/PullRequest: number, title, body, state, url, createdAt, updatedAt",
                "Issue comments.totalCount and comments(last: MAX_COMMENTS_PER_ITEM){bodyText, createdAt, updatedAt, url, author.login}",
                "PullRequest comments.totalCount and comments(last: MAX_COMMENTS_PER_ITEM){bodyText, createdAt, updatedAt, url, author.login}",
                "PullRequest reviews.totalCount",
                "project fieldValueByName('Status').name",
            ],
            "not_included": [
                "Issue/PR timeline events",
                "discussion thread text",
                "full review text",
            ],
        },
        "metrics": {
            "total_items_fetched": len(items),
            "items_updated_in_lookback_window": recent_count,
            "comments_created_in_lookback_window": recent_comments_total,
        },
        "items": filtered_items,
    }


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


def auto_link_issue_references(summary, data):
    """Auto-links #1234 references when a unique URL exists in payload items."""
    items = data.get("items", []) or []
    number_to_urls = {}
    for item in items:
        content = item.get("content") or {}
        number = content.get("number")
        url = content.get("url")
        if isinstance(number, int) and isinstance(url, str) and url:
            number_to_urls.setdefault(number, set()).add(url)

    unique_links = {n: next(iter(urls)) for n, urls in number_to_urls.items() if len(urls) == 1}
    if not unique_links:
        return summary

    # Avoid replacing if already linked: [#1234](...)
    pattern = re.compile(r"(?<!\[)#(\d+)\b")

    def replacer(match):
        number = int(match.group(1))
        url = unique_links.get(number)
        if not url:
            return match.group(0)
        return f"[#{number}]({url})"

    return pattern.sub(replacer, summary)


def normalize_subsection_headings(summary):
    """Converts bullet-style bold subsection labels into H3 headings."""
    normalized_lines = []
    pattern = re.compile(r"^\s*[*-]\s+\*\*(.+?)\*\*:\s*$")

    for line in summary.splitlines():
        match = pattern.match(line)
        if match:
            normalized_lines.append(f"### {match.group(1)}")
        else:
            normalized_lines.append(line)

    return "\n".join(normalized_lines)


def enforce_top_metrics_block(summary, data):
    """Ensures top metrics are present as bullet lines in a consistent format."""
    metrics = data.get("metrics", {}) or {}
    total_items = metrics.get("total_items_fetched", 0)
    updated_items = metrics.get("items_updated_in_lookback_window", 0)
    comments_count = metrics.get("comments_created_in_lookback_window", 0)

    cleaned_lines = []
    metric_pattern = re.compile(
        r"^\s*[*-]?\s*(\*\*)?\s*"
        r"(Total Items Fetched|Items Updated in Lookback Window|Comments Created in Lookback Window)"
        r"\s*:\s*.*$"
    )
    for line in summary.splitlines():
        if metric_pattern.match(line.strip()):
            continue
        cleaned_lines.append(line)

    metrics_block = [
        f"*   **Total Items Fetched:** {total_items}",
        f"*   **Items Updated in Lookback Window:** {updated_items}",
        f"*   **Comments Created in Lookback Window:** {comments_count}",
        "",
    ]

    return "\n".join(metrics_block + cleaned_lines).strip() + "\n"


def write_report(summary, provider, project):
    """Writes the generated report to a timestamped Markdown file."""
    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"report-{timestamp.strftime('%Y%m%d-%H%M%S')}.md"
    report_path = reports_dir / filename

    project_name = project.get("title") or "Unknown Project"
    project_url = project.get("url") or "Unknown URL"

    header = (
        "# Executive Report\n\n"
        f"- Generated: {timestamp.isoformat()}\n"
        f"- AI Provider: {provider}\n"
        f"- Project Name: {project_name}\n"
        f"- Project URL: {project_url}\n\n"
        "---\n\n"
    )
    report_path.write_text(header + summary + "\n", encoding="utf-8")
    return report_path


def run_report():
    provider = getattr(config, "AI_PROVIDER", "gemini").strip().lower()

    print(f"[{datetime.now()}] Resolving target project...")
    project_id = get_project_id()

    print(f"[{datetime.now()}] Fetching GitHub data...")
    raw_data = fetch_github_project_data(project_id)
    analysis_payload = build_analysis_payload(raw_data)

    print(f"[{datetime.now()}] Generating AI summary with provider: {provider}...")
    summary = generate_summary(analysis_payload)
    summary = auto_link_issue_references(summary, analysis_payload)
    summary = normalize_subsection_headings(summary)
    summary = enforce_top_metrics_block(summary, analysis_payload)

    report_path = write_report(summary, provider, analysis_payload.get("project", {}))
    print(f"[{datetime.now()}] Report saved to: {report_path}")

    # TODO: Write the summary into a Google Doc.
    # TODO: Send this to a Slack webhook.

    print("\n--- EXECUTIVE REPORT ---\n")
    print(summary)


if __name__ == "__main__":
    run_report()
