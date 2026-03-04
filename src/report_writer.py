from datetime import datetime
from pathlib import Path


def write_report(summary, provider, project, base_dir):
    reports_dir = base_dir / "reports"
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
