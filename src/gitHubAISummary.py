import sys
from datetime import datetime
from pathlib import Path

from ai_clients import generate_summary
from github_api import fetch_github_project_data, get_project_id
from payload_builder import build_analysis_payload
from prompt_template import build_report_prompt
from report_formatting import (
    auto_link_issue_references,
    enforce_top_metrics_block,
    normalize_subsection_headings,
)
from report_writer import write_report
from settings import load_settings

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config


def run_report():
    settings = load_settings(config)
    base_dir = Path(__file__).resolve().parent.parent

    print(f"[{datetime.now()}] Resolving target project...")
    project_id = get_project_id(
        settings.github_token, settings.project_id, settings.project_url
    )
    if settings.project_url and not settings.project_id:
        print(f"[{datetime.now()}] Resolved PROJECT_ID from PROJECT_URL: {project_id}")

    if settings.max_items > 100:
        print(
            f"[{datetime.now()}] MAX_ITEMS={settings.max_items} exceeds GitHub "
            "GraphQL limit (100); using 100."
        )

    print(f"[{datetime.now()}] Fetching GitHub data...")
    raw_data = fetch_github_project_data(
        settings.github_token,
        project_id,
        settings.effective_max_items,
        settings.max_comments_per_item,
    )
    analysis_payload = build_analysis_payload(
        raw_data,
        settings.lookback_days,
        settings.effective_max_items,
        settings.max_comments_per_item,
    )

    print(
        f"[{datetime.now()}] Generating AI summary with provider: "
        f"{settings.ai_provider}..."
    )
    prompt = build_report_prompt(analysis_payload, settings.lookback_days)
    summary = generate_summary(
        settings.ai_provider,
        prompt,
        settings.gemini_api_key,
        settings.gemini_model,
        settings.openai_api_key,
        settings.openai_model,
    )
    summary = auto_link_issue_references(summary, analysis_payload)
    summary = normalize_subsection_headings(summary)
    summary = enforce_top_metrics_block(summary, analysis_payload)

    report_path = write_report(
        summary,
        settings.ai_provider,
        analysis_payload.get("project", {}),
        base_dir,
    )
    print(f"[{datetime.now()}] Report saved to: {report_path}")

    print("\n--- EXECUTIVE REPORT ---\n")
    print(summary)


if __name__ == "__main__":
    run_report()
