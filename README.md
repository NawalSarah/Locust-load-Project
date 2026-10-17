# Project 2 - Locust Load-Testing Suite

This project creates a small fake banking API, then uses Locust to simulate many people using it at the same time. It checks whether the API stays fast and responds correctly.

## What is this, in plain English?

Think of a supermarket: serving one customer is easy. What happens when 50 customers arrive and start asking for things? That is the idea behind load testing.

The fake banking API handles transactions, while a Locust script simulates many users and measures how quickly the API responds and how many requests fail.
At the end a **gate** decides pass or fail: if the 95th-percentile response time or the error rate is too high,
the run exits with an error, which would fail a CI pipeline.

Everything runs on your own computer; no internet needed.

## Run it
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_load_test.py
```
It takes about 45 seconds. At the end you will see lines starting with `[GATE]` and `PASSED`.
Open **`results/report.html`** for charts.

Other ways to run it:

| Command | What happens |
|---------|--------------|
| `python run_load_test.py --quick` | 10 users for 15 seconds (fast check) |
| `python run_load_test.py --break-it` | API is made 800 ms slower on purpose, so the gate **FAILS** (you will see `FAILED` and exit code 1) |
| `python run_load_test.py --ui` | Opens Locust's web page at http://localhost:8089 so you can start the test with buttons |

While it runs you can also open http://127.0.0.1:8001/docs to see the API's interactive documentation.

## How the pieces fit

```
app/main.py            the Transactions API (FastAPI) being tested
locustfile.py          the load test: user types, tasks, response checks, pass/fail gate
step_shape.py          the stepped load profile (5 -> 15 -> 30 -> 50 users)
run_load_test.py       starts the API, runs Locust, saves the report, stops the API
Dockerfile             packs everything into one container
.github/workflows/     GitHub Actions: runs the test on every push, fails the build if the gate fails
```

## Key ideas to understand

- **Virtual user** - one simulated person. `BrowsingUser` reads data; `PayingUser` creates payments.
- **Weights** - `weight = 7` vs `weight = 3` means 70% browsers / 30% payers. Inside a user, `@task(5)` vs `@task(1)`
  means "do this five times as often". Real traffic is uneven, so the test should be too.
- **`wait_time = between(0.5, 2)`** - "think time". Real users pause; without it you test something unrealistic.
- **Stepped load** - users go up in stages so you can see *at which step* response times start to degrade.
- **p95 (95th percentile)** - "95% of requests were faster than this". Better than the average, which hides slow outliers.
- **Error rate** - share of failed requests. A system that answers fast with errors is not healthy.
- **Response validation** - `catch_response=True` lets us mark a request failed if the status code or the body is wrong.
- **Negative test under load** - the "invalid payment" task expects HTTP 422 and counts that as a pass.
- **The gate** - at the bottom of `locustfile.py`. It sets `environment.process_exit_code = 1` when a limit is broken.
  CI systems fail a job when a command exits with a non-zero code.

Change the limits without editing code: `P95_MS=300 python run_load_test.py` (on Windows PowerShell: `$env:P95_MS=300; python run_load_test.py`).

## Try these changes yourself

1. Run `--break-it` and read the output. Which line tells you why it failed?
2. Edit `STAGES` in `step_shape.py` to peak at 100 users. Does the gate still pass?
3. Add a new task to `BrowsingUser`, for example calling `/health` more often, or a new endpoint in `app/main.py` plus a task for it.
4. Set `FAIL_RATE=0.2` as an environment variable when running: the **error-rate** part of the gate should fail.
   (Mac/Linux: `FAIL_RATE=0.2 python run_load_test.py --quick`)

## Docker and GitHub Actions (not run by the person who built this - try them once)
```bash
docker build -t locust-suite .
docker run --rm -v "$(pwd)/results:/app/results" locust-suite ; echo "exit code: $?"
```
For GitHub Actions: push this folder to its own repository. The **Actions** tab shows the run; download the **locust-report** artifact.

## Talking points
- "Two user types with weights 70/30, each with weighted tasks and think time."
- "I validate responses, not just timings, because a fast error is still a failure."
- "The pipeline gate checks p95 and error rate and fails the build with exit code 1 on a breach. I proved it by slowing the API on purpose."
