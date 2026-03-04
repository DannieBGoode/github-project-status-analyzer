import sys
from pathlib import Path

from report_runner import run_report_pipeline
from settings import load_settings

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config


def run_report():
    settings = load_settings(config)
    base_dir = Path(__file__).resolve().parent.parent

    result = run_report_pipeline(
        settings,
        base_dir=base_dir,
        log=print,
        save_report=True,
    )

    print("\n--- EXECUTIVE REPORT ---\n")
    print(result["summary"])


if __name__ == "__main__":
    run_report()
