import json
from datetime import datetime, timedelta, timezone


REPORT_PROMPT_TEMPLATE = """
Context: You are a CTO reporting agent.

Current Date: {current_date}
Lookback Window: Last {lookback_days} days (since {cutoff_date})
Project Name: {project_title}
Project URL: {project_url}
- Total Items Fetched: `{values_total_items_fetched}`
- Items Updated in Lookback Window: `{values_items_updated_in_lookback_window}`
- Comments Created in Lookback Window: `{values_comments_created_in_lookback_window}`

Task:
Write a concise executive report using ONLY the provided data.

Mandatory output rules:
- Use the exact Current Date above. Never output placeholders like [Current Date].
- Format output as Markdown headings:
  - Use `##` for major sections.
  - Use `###` for subsection breakdowns where helpful.
  - Do not use bold text as a substitute for headings.
- Use this highlevel section structure with `##` headings:
  1. Key Achievements in the last {lookback_days} days
  2. Risks
  3. Issues and Blockers
- Anything inside the h2 sections that requires a structure should follow the h3, h4, h5 headings structure or use bullet points for lists.
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
- Whenever referencing an issue or pull request, use hyperlink format like [#1234](https://github.com/org/repo/issues/1234) using URLs from the provided data so that the hyperlink is displayed as a clickable link in markdown format. Do not escape the markdown syntax.

Data Payload:
{raw_data}
"""


def build_report_prompt(data, lookback_days):
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=lookback_days)

    project = data.get("project", {})
    project_title = project.get("title") or "Unknown Project"
    project_url = project.get("url") or "Unknown URL"
    metrics = data.get("metrics", {}) or {}

    return REPORT_PROMPT_TEMPLATE.format(
        current_date=now_utc.strftime("%Y-%m-%d"),
        lookback_days=lookback_days,
        cutoff_date=cutoff.strftime("%Y-%m-%d"),
        project_title=project_title,
        project_url=project_url,
        values_total_items_fetched=metrics.get("total_items_fetched", 0),
        values_items_updated_in_lookback_window=metrics.get(
            "items_updated_in_lookback_window", 0
        ),
        values_comments_created_in_lookback_window=metrics.get(
            "comments_created_in_lookback_window", 0
        ),
        raw_data=json.dumps(data),
    )
