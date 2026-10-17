"""Stepped load profile: raise the number of users in steps to see where the system starts to struggle.

Locust picks this up automatically when you add it to the command line:
    locust -f locustfile.py,step_shape.py ...

Edit STAGES to change the profile. Each stage = (run until this many seconds, users, users added per second).
"""
from locust import LoadTestShape

STAGES = [
    (10, 5, 5),     # first 10 s : 5 users   (warm-up)
    (20, 15, 5),    # 10-20 s    : 15 users
    (30, 30, 10),   # 20-30 s    : 30 users
    (40, 50, 10),   # 30-40 s    : 50 users  (peak)
]


class StepLoadShape(LoadTestShape):
    def tick(self):
        run_time = self.get_run_time()
        for end_time, users, spawn_rate in STAGES:
            if run_time < end_time:
                return users, spawn_rate
        return None   # None = stop the test
