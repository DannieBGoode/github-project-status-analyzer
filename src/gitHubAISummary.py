import sys
from pathlib import Path

from report_runner import run_report_pipeline
from settings import load_settings

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config


def run_report():
    try:
        settings = load_settings(config)
    except Exception as exc:
        print(f"Error loading configuration: {exc}", file=sys.stderr)
        return 1

    base_dir = Path(__file__).resolve().parent.parent

    try:
        result = run_report_pipeline(
            settings,
            base_dir=base_dir,
            log=print,
            save_report=True,
        )
    except Exception as exc:
        print(f"Error generating report: {exc}", file=sys.stderr)
        return 1

    print("\n--- EXECUTIVE REPORT ---\n")
    print(result["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(run_report())
