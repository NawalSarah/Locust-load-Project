"""One-command runner:  python run_load_test.py

What it does:
  1. Starts the Transactions API (uvicorn) on port 8001
  2. Runs Locust headless (no web UI) with the stepped load profile
  3. Writes results/report.html and results/stats_*.csv
  4. Stops the API and exits with 0 (gate passed) or 1 (gate failed)

Options:
  --break-it   start the API with a deliberate 800 ms slowdown, so you can watch the gate FAIL
  --quick      constant 10 users for 15 seconds instead of the 40-second stepped profile
  --ui         open Locust's web page (http://localhost:8089) instead of running headless
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
API_PORT = 8001


def wait_for_api(timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/health", timeout=1)
            return
        except Exception:
            time.sleep(0.3)
    raise SystemExit("API did not start in time")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--break-it", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--ui", action="store_true")
    args = parser.parse_args()

    api_env = dict(os.environ, SLOW_MS="800" if args.break_it else os.getenv("SLOW_MS", "0"))
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(API_PORT), "--log-level", "warning"],
        cwd=ROOT, env=api_env,
    )
    try:
        wait_for_api()
        print(f"API is up on http://127.0.0.1:{API_PORT}  (docs: /docs)")

        files = "locustfile.py" if (args.quick or args.ui) else "locustfile.py,step_shape.py"
        cmd = [sys.executable, "-m", "locust", "-f", files, "--host", f"http://127.0.0.1:{API_PORT}"]
        if not args.ui:
            (ROOT / "results").mkdir(exist_ok=True)
            cmd += ["--headless", "--html", "results/report.html", "--csv", "results/stats"]
            if args.quick:
                cmd += ["-u", "10", "-r", "5", "-t", "15s"]
        code = subprocess.call(cmd, cwd=ROOT)
    finally:
        api.terminate()
        api.wait()
    if not args.ui:
        print("\nReport: results/report.html")
    sys.exit(code)


if __name__ == "__main__":
    main()
