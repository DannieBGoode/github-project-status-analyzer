from datetime import datetime
from pathlib import Path

from ai_clients import generate_summary
from github_project_data import fetch_github_project_data
from payload_builder import build_analysis_payload
from project_target import get_project_id
from prompt_template import build_report_prompt
from report_formatting import (
    auto_link_issue_references,
    enforce_top_metrics_block,
    normalize_subsection_headings,
)
from report_writer import build_markdown_document, write_report


def run_report_pipeline(
    settings, *, base_dir, log=print, save_report=True, progress_callback=None
):
    selected_model = (
        settings.openai_model
        if settings.ai_provider == "openai"
        else settings.gemini_model
    )

    def emit(step_id, status, message):
        if progress_callback:
            progress_callback(
                {"step_id": step_id, "status": status, "message": message}
            )

    log(f"[{datetime.now()}] Resolving target project...")
    emit(
        "github_request",
        "in_progress",
        (
            "Sending request to GitHub for "
            f"{settings.effective_max_items} items and "
            f"{settings.max_comments_per_item} comments per item "
            f"in the last {settings.lookback_days} days."
        ),
    )
    project_id = get_project_id(
        settings.github_token, settings.project_id, settings.project_url
    )
    if settings.project_url and not settings.project_id:
        log(f"[{datetime.now()}] Resolved PROJECT_ID from PROJECT_URL: {project_id}")

    if settings.max_items > 100:
        log(
            f"[{datetime.now()}] MAX_ITEMS={settings.max_items} exceeds GitHub "
            "GraphQL limit (100); using 100."
        )

    log(f"[{datetime.now()}] Fetching GitHub data...")
    emit("github_response", "in_progress", "Awaiting response from GitHub...")
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
    emit("github_request", "completed", "GitHub request completed.")
    metrics = analysis_payload.get("metrics", {})
    emit(
        "github_response",
        "completed",
        (
            "Received "
            f"{metrics.get('total_items_fetched', 0)} items and "
            f"{metrics.get('comments_created_in_lookback_window', 0)} "
            "comments in lookback window."
        ),
    )

    log(
        f"[{datetime.now()}] Generating AI summary with provider: "
        f"{settings.ai_provider}..."
    )
    emit(
        "ai_send",
        "in_progress",
        f"Sending items to {settings.ai_provider.capitalize()}...",
    )
    prompt = build_report_prompt(analysis_payload, settings.lookback_days)
    emit("ai_send", "completed", "Items sent successfully.")
    emit(
        "ai_wait",
        "in_progress",
        f"Waiting for {settings.ai_provider.capitalize()} response...",
    )
    summary = generate_summary(
        settings.ai_provider,
        prompt,
        settings.gemini_api_key,
        settings.gemini_model,
        settings.openai_api_key,
        settings.openai_model,
        settings.ai_timeout_seconds,
        settings.ai_max_retries,
    )
    emit("ai_wait", "completed", "AI response received.")
    emit("markdown_build", "in_progress", "Building markdown report...")
    summary = auto_link_issue_references(summary, analysis_payload)
    summary = normalize_subsection_headings(summary)
    summary = enforce_top_metrics_block(summary, analysis_payload)

    project = analysis_payload.get("project", {})
    markdown = build_markdown_document(
        summary,
        settings.ai_provider,
        selected_model,
        project,
        settings.report_timezone,
        settings.report_timezone_label,
    )
    emit("markdown_build", "completed", "Markdown report built.")

    report_path = None
    if save_report:
        report_path = write_report(
            summary,
            settings.ai_provider,
            selected_model,
            project,
            Path(base_dir),
            settings.report_timezone,
            settings.report_timezone_label,
        )
        log(f"[{datetime.now()}] Report saved to: {report_path}")

    return {
        "summary": summary,
        "markdown": markdown,
        "report_path": str(report_path) if report_path else None,
        "project": project,
        "metrics": analysis_payload.get("metrics", {}),
        "provider": settings.ai_provider,
    }
