"""Locust load test for the Transactions API.

Key ideas (each one is something you can explain in an interview):

1. WEIGHTED USER SCENARIOS - real traffic is not uniform. Most visitors read data
   (BrowsingUser, weight 7), fewer create payments (PayingUser, weight 3).
   Inside each user, @task(N) sets how often a step runs relative to the others.

2. VALIDATION - we do not just measure speed; each response is also checked
   (right status code, expected fields). A fast wrong answer is still a failure.

3. PASS/FAIL GATE - when the test ends, we compare the 95th percentile (p95) response
   time and the error rate with limits. If a limit is broken the process exits with
   code 1, which makes a CI pipeline fail. Limits can be changed via environment variables:
       P95_MS=500      error if 95% of requests are not faster than 500 ms
       ERROR_RATE=0.01 error if more than 1% of requests fail
"""
import os
import random

from locust import HttpUser, between, events, task

P95_LIMIT_MS = float(os.getenv("P95_MS", "500"))
ERROR_RATE_LIMIT = float(os.getenv("ERROR_RATE", "0.01"))

ACCOUNTS = [f"ACC-{n:04d}" for n in range(1, 21)]   # ACC-0001 ... ACC-0020
CURRENCIES = ["PLN", "EUR", "USD"]


class BrowsingUser(HttpUser):
    """Reads data. The most common type of visitor."""

    weight = 7
    wait_time = between(0.5, 2)   # "think time" between actions, like a real person

    @task(5)
    def check_balance(self):
        account = random.choice(ACCOUNTS)
        # name= groups all balance calls into one row in the report
        self.client.get(f"/accounts/{account}/balance", name="/accounts/[id]/balance")

    @task(3)
    def list_transactions(self):
        with self.client.get(
            "/transactions",
            params={"account_id": random.choice(ACCOUNTS)},
            name="/transactions?account_id=[id]",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Expected 200, got {response.status_code}")
            elif "items" not in response.json():
                response.failure("Response has no 'items' field")

    @task(1)
    def health_check(self):
        self.client.get("/health")


class PayingUser(HttpUser):
    """Creates a payment and then looks it up. Less common, but heavier (it writes data)."""

    weight = 3
    wait_time = between(1, 3)

    @task
    def create_then_read_transaction(self):
        payload = {
            "account_id": random.choice(ACCOUNTS),
            "amount": round(random.uniform(1, 500), 2),
            "currency": random.choice(CURRENCIES),
        }
        with self.client.post(
            "/transactions", json=payload, name="/transactions", catch_response=True
        ) as response:
            if response.status_code != 201:
                response.failure(f"Expected 201, got {response.status_code}")
                return
            transaction_id = response.json().get("id")
            if not transaction_id:
                response.failure("No 'id' in response")
                return

        self.client.get(f"/transactions/{transaction_id}", name="/transactions/[id]")

    @task(1)
    def send_invalid_payment(self):
        """Negative test: the API must reject bad input with 422 (and that is a PASS here)."""
        bad_payload = {"account_id": "WRONG", "amount": -5, "currency": "XXX"}
        with self.client.post(
            "/transactions", json=bad_payload, name="/transactions (invalid input)",
            catch_response=True,
        ) as response:
            if response.status_code == 422:
                response.success()
            else:
                response.failure(f"Expected 422, got {response.status_code}")


@events.quitting.add_listener
def enforce_thresholds(environment, **kwargs):
    """Runs once when the test finishes. Sets a non-zero exit code if limits are broken."""
    total = environment.stats.total
    if total.num_requests == 0:
        print("\n[GATE] FAILED - no requests were made")
        environment.process_exit_code = 1
        return

    p95 = total.get_response_time_percentile(0.95)
    error_rate = total.fail_ratio

    print("\n" + "=" * 60)
    print(f"[GATE] requests: {total.num_requests}   failures: {total.num_failures}")
    print(f"[GATE] p95 response time: {p95:.0f} ms   (limit {P95_LIMIT_MS:.0f} ms)")
    print(f"[GATE] error rate: {error_rate:.2%}   (limit {ERROR_RATE_LIMIT:.2%})")

    problems = []
    if p95 > P95_LIMIT_MS:
        problems.append(f"p95 {p95:.0f} ms is above {P95_LIMIT_MS:.0f} ms")
    if error_rate > ERROR_RATE_LIMIT:
        problems.append(f"error rate {error_rate:.2%} is above {ERROR_RATE_LIMIT:.2%}")

    if problems:
        print("[GATE] FAILED - " + "; ".join(problems))
        environment.process_exit_code = 1
    else:
        print("[GATE] PASSED")
    print("=" * 60)
