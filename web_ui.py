import sys
import json
import queue
import threading
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    request,
    send_from_directory,
    stream_with_context,
)

sys.path.append(str(Path(__file__).resolve().parent / "src"))
import config
from model_options import MODEL_OPTIONS
from report_runner import run_report_pipeline
from settings import load_settings


BASE_DIR = Path(__file__).resolve().parent
WEBUI_DIR = BASE_DIR / "webui"

app = Flask(__name__, static_folder=str(WEBUI_DIR), static_url_path="")

def mask_secret(value):
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def parse_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def model_ids(provider):
    return [entry["id"] for entry in MODEL_OPTIONS.get(provider, [])]


def cheapest_model(provider):
    ids = model_ids(provider)
    return ids[0] if ids else ""


def normalize_model(provider, configured_model):
    ids = model_ids(provider)
    if configured_model in ids:
        return configured_model
    return cheapest_model(provider)


def build_runtime_settings(payload, base_settings):
    github_token = payload.get("github_token", "").strip()
    gemini_api_key = payload.get("gemini_api_key", "").strip()
    openai_api_key = payload.get("openai_api_key", "").strip()

    if "*" in github_token:
        github_token = base_settings.github_token
    if "*" in gemini_api_key:
        gemini_api_key = base_settings.gemini_api_key
    if "*" in openai_api_key:
        openai_api_key = base_settings.openai_api_key

    ai_provider = payload.get("ai_provider", base_settings.ai_provider).strip().lower()
    selected_model = payload.get("model", "").strip()

    gemini_model = cheapest_model("gemini")
    openai_model = cheapest_model("openai")
    if selected_model:
        if ai_provider == "gemini":
            gemini_model = normalize_model("gemini", selected_model)
        elif ai_provider == "openai":
            openai_model = normalize_model("openai", selected_model)

    return replace(
        base_settings,
        ai_provider=ai_provider,
        project_url=payload.get("project_url", base_settings.project_url).strip(),
        # UI intentionally uses URL targeting only.
        project_id="",
        lookback_days=parse_int(payload.get("lookback_days"), base_settings.lookback_days),
        max_items=min(100, parse_int(payload.get("max_items"), base_settings.max_items)),
        max_comments_per_item=parse_int(
            payload.get("max_comments_per_item"), base_settings.max_comments_per_item
        ),
        gemini_model=gemini_model,
        openai_model=openai_model,
        report_timezone=payload.get(
            "report_timezone", base_settings.report_timezone
        ).strip(),
        report_timezone_label=payload.get(
            "report_timezone_label", base_settings.report_timezone_label
        ).strip(),
        github_token=github_token or base_settings.github_token,
        gemini_api_key=gemini_api_key or base_settings.gemini_api_key,
        openai_api_key=openai_api_key or base_settings.openai_api_key,
    )


@app.get("/")
def index():
    return send_from_directory(WEBUI_DIR, "index.html")


@app.get("/api/config")
def get_config():
    settings = load_settings(config)
    gemini_model = cheapest_model("gemini")
    openai_model = cheapest_model("openai")
    return jsonify(
        {
            "ai_provider": settings.ai_provider,
            "project_url": settings.project_url,
            "lookback_days": settings.lookback_days,
            "max_items": settings.max_items,
            "max_comments_per_item": settings.max_comments_per_item,
            "gemini_model": gemini_model,
            "openai_model": openai_model,
            "model_options": MODEL_OPTIONS,
            "github_token": mask_secret(settings.github_token),
            "gemini_api_key": mask_secret(settings.gemini_api_key),
            "openai_api_key": mask_secret(settings.openai_api_key),
            "has_github_token": bool(settings.github_token),
            "has_gemini_api_key": bool(settings.gemini_api_key),
            "has_openai_api_key": bool(settings.openai_api_key),
        }
    )


@app.post("/api/run")
def run_report():
    payload = request.get_json(silent=True) or {}
    base_settings = load_settings(config)
    runtime_settings = build_runtime_settings(payload, base_settings)

    try:
        result = run_report_pipeline(
            runtime_settings,
            base_dir=BASE_DIR,
            log=lambda *_args, **_kwargs: None,
            save_report=False,
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    filename = f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    return jsonify(
        {
            "ok": True,
            "filename": filename,
            "markdown": result["markdown"],
            "summary": result["summary"],
        }
    )


@app.post("/api/run-stream")
def run_report_stream():
    payload = request.get_json(silent=True) or {}
    base_settings = load_settings(config)
    runtime_settings = build_runtime_settings(payload, base_settings)

    event_queue = queue.Queue()

    def push_event(event_type, **data):
        event_queue.put({"type": event_type, **data})

    def worker():
        try:
            result = run_report_pipeline(
                runtime_settings,
                base_dir=BASE_DIR,
                log=lambda *_args, **_kwargs: None,
                save_report=False,
                progress_callback=lambda evt: push_event("step", step=evt),
            )
            filename = f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
            push_event(
                "result",
                data={
                    "ok": True,
                    "filename": filename,
                    "markdown": result["markdown"],
                    "summary": result["summary"],
                },
            )
        except Exception as exc:
            push_event("error", error=str(exc))
        finally:
            push_event("done")

    threading.Thread(target=worker, daemon=True).start()

    @stream_with_context
    def stream():
        while True:
            message = event_queue.get()
            yield json.dumps(message) + "\n"
            if message.get("type") == "done":
                break

    return Response(stream(), mimetype="application/x-ndjson")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
