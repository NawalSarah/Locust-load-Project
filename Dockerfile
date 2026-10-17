# Runs the API and the load test together inside one container.
#   docker build -t locust-suite .
#   docker run --rm -v "$PWD/results:/app/results" locust-suite
# The container exit code is 0 when the p95/error-rate gate passes and 1 when it fails.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "run_load_test.py"]
