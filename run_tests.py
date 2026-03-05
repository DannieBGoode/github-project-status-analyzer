import subprocess
import sys


def run_step(name, command):
    print(f"\n==> {name}")
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        print(f"{name} failed with exit code {completed.returncode}")
    return completed.returncode


def main():
    py_code = run_step(
        "Python tests",
        [sys.executable, "-m", "coverage", "run", "--rcfile=.coveragerc",
         "-m", "unittest", "discover", "-s", "tests/python", "-p", "test_*.py"],
    )
    run_step("Coverage report", [sys.executable, "-m", "coverage", "report"])
    js_code = run_step("JavaScript tests", ["node", "--test", "tests/js/*.test.js"])

    if py_code == 0 and js_code == 0:
        print("\nAll tests passed.")
        return 0

    return py_code or js_code


if __name__ == "__main__":
    raise SystemExit(main())
