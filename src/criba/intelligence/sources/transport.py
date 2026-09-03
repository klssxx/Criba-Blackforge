"""IIE HTTP transport (P03): retries, timeouts, rate-limit responses, budget.

No adapter imports httpx directly; everything goes through Transport so tests
inject a fake sender (§101 no-network CI). Real sender is lazy-imported.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Response:
    status: int
    text: str
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        import json
        return json.loads(self.text)


@dataclass
class TransportBudget:
    """Blueprint §35: per-run request accounting."""
    max_requests: int = 20
    max_runtime_s: float = 120.0
    requests_made: int = 0
    started_at: float = field(default_factory=time.monotonic)

    def spend(self) -> bool:
        """True if a request may proceed; False if budget exhausted."""
        if self.requests_made >= self.max_requests:
            return False
        if time.monotonic() - self.started_at > self.max_runtime_s:
            return False
        self.requests_made += 1
        return True

    @property
    def exhausted(self) -> bool:
        return (self.requests_made >= self.max_requests
                or time.monotonic() - self.started_at > self.max_runtime_s)


class BudgetExceeded(Exception):
    pass


class Transport:
    """GET sender with retry/backoff/429 handling. sender is injectable."""

    RETRY_STATUSES = {429, 500, 502, 503, 504}

    def __init__(self, sender: Callable[..., Response] | None = None,
                 budget: TransportBudget | None = None,
                 max_retries: int = 2, timeout_s: float = 20.0,
                 user_agent: str = "criba-iie/0.1 (+research)"):
        self._sender = sender
        self.budget = budget or TransportBudget()
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self.user_agent = user_agent

    def _real_sender(self, url: str, params: dict | None, timeout: float,
                     headers: dict | None) -> Response:
        import httpx  # lazy: only hit when actually going online
        h = {"User-Agent": self.user_agent}
        if headers:
            h.update(headers)
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url, params=params, headers=h)
            return Response(status=r.status_code, text=r.text,
                            headers=dict(r.headers))

    def get(self, url: str, params: dict | None = None,
            headers: dict | None = None) -> Response:
        """Single GET honoring budget + retries. Raises BudgetExceeded."""
        last: Response | None = None
        for attempt in range(self.max_retries + 1):
            if not self.budget.spend():
                raise BudgetExceeded(
                    f"budget exhausted ({self.budget.requests_made}/"
                    f"{self.budget.max_requests} requests)")
            sender = self._sender or self._real_sender
            try:
                resp = sender(url, params=params, timeout=self.timeout_s,
                              headers=headers)
            except Exception as exc:  # network error -> retryable
                last = Response(status=0, text=f"network error: {exc}")
                resp = last
            if resp.status == 200:
                return resp
            if resp.status in self.RETRY_STATUSES and attempt < self.max_retries:
                time.sleep(min(2 ** attempt, 4))
                continue
            return resp
        return last or Response(status=0, text="unreachable")
