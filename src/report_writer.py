from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def format_provider_display(provider):
    if provider == "openai":
        return "OpenAI"
    if provider == "gemini":
        return "Gemini"
    return provider


MODEL_DISPLAY_NAMES = {
    "gpt-5.2": "GPT-5.2",
    "gpt-5-mini": "GPT-5 mini",
    "gpt-5-nano": "GPT-5 nano",
    "gpt-4.1": "GPT-4.1",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-flash-preview-09-2025": "Gemini 2.5 Flash Preview",
    "gemini-2.5-flash-lite-preview-09-2025": "Gemini 2.5 Flash-Lite Preview",
}


def format_model_display(model):
    if not model:
        return model
    return MODEL_DISPLAY_NAMES.get(model, model)


def format_generated_timestamp(report_timezone="", report_timezone_label=""):
    now_local = datetime.now().astimezone()
    if report_timezone:
        try:
            now_local = now_local.astimezone(ZoneInfo(report_timezone))
        except Exception:
            pass
    timezone_label = report_timezone_label.strip() or now_local.strftime("%Z")
    return f"{now_local.strftime('%Y-%b-%d %H:%M')} {timezone_label}"


def build_markdown_document(
    summary, provider, model, project, report_timezone="", report_timezone_label=""
):
    generated_label = format_generated_timestamp(
        report_timezone, report_timezone_label
    )
    project_name = project.get("title") or "Unknown Project"
    project_url = project.get("url") or "Unknown URL"
    provider_label = format_provider_display(provider)
    model_label = format_model_display(model)
    provider_with_model = (
        f"{provider_label} - {model_label}" if model_label else provider_label
    )

    header = (
        "# Executive Report\n\n"
        f"- Generated: {generated_label}\n"
        f"- AI Provider: {provider_with_model}\n"
        f"- Project Name: {project_name}\n"
        f"- Project URL: {project_url}\n\n"
        "---\n\n"
    )
    return header + summary + "\n"


def write_report(
    summary,
    provider,
    model,
    project,
    base_dir,
    report_timezone="",
    report_timezone_label="",
):
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"report-{timestamp.strftime('%Y%m%d-%H%M%S')}.md"
    report_path = reports_dir / filename

    report_path.write_text(
        build_markdown_document(
            summary,
            provider,
            model,
            project,
            report_timezone,
            report_timezone_label,
        ),
        encoding="utf-8",
    )
    return report_path
