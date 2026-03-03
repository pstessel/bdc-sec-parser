from __future__ import annotations
import time
import requests

BASE = "https://data.sec.gov/submissions"


class SecClient:
    def __init__(self, user_agent: str, requests_per_sec: float = 5.0):
        self.user_agent = user_agent
        self.min_interval = 1.0 / max(requests_per_sec, 0.2)
        self._last = 0.0

    def _throttle(self):
        now = time.time()
        wait = self.min_interval - (now - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def get_submissions(self, cik: str) -> dict:
        self._throttle()
        cik10 = str(cik).zfill(10)
        url = f"{BASE}/CIK{cik10}.json"
        r = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=30)
        r.raise_for_status()
        return r.json()
