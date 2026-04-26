"""Nobitex REST client with throttling and exponential backoff.

Limitations:
- WebSocket streaming is not implemented in this client module.
- Ed25519 request signing is not implemented; simple token auth is used.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import requests

from config.settings import Settings
from core.exceptions import APIRequestError, RateLimitError
from core.logger import get_logger

LOGGER = get_logger(__name__)


@dataclass
class TokenBucket:
    """Token bucket rate limiter."""

    capacity: int
    refill_window_seconds: int

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity)
        self.updated_at = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, cost: float = 1.0) -> None:
        with self._lock:
            now = time.monotonic()
            refill_rate = self.capacity / self.refill_window_seconds
            self.tokens = min(self.capacity, self.tokens + (now - self.updated_at) * refill_rate)
            self.updated_at = now
            if self.tokens < cost:
                raise RateLimitError("Rate limit exceeded")
            self.tokens -= cost


class NobitexClient:
    """HTTP client for Nobitex."""

    def __init__(self, settings: Settings | None = None, session: requests.Session | None = None) -> None:
        self.settings = settings or Settings()
        self.session = session or requests.Session()
        self.bucket = TokenBucket(
            capacity=self.settings.rate_limit_capacity,
            refill_window_seconds=self.settings.rate_limit_window_seconds,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.settings.api_token:
            headers["Authorization"] = f"Token {self.settings.api_token}"
        return headers

    def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None) -> Any:
        for attempt in range(4):
            self.bucket.acquire()
            response = self.session.request(
                method,
                f"{self.settings.base_rest_url}{path}",
                headers=self._headers(),
                params=params,
                json=json_body,
                timeout=15,
            )
            if response.ok:
                return response.json()
            if response.status_code not in {429, 500, 502, 503, 504}:
                raise APIRequestError(f"HTTP {response.status_code}: {response.text}")
            time.sleep(0.25 * (2 ** attempt))
        raise APIRequestError(f"Request failed after retries for {path}")

    def get_orderbook(self, symbol: str) -> Any:
        return self._request("GET", f"/v3/orderbook/{symbol}")

    def get_ohlcv(self, symbol: str, resolution: str, start: int, end: int) -> Any:
        return self._request(
            "GET",
            "/market/udf/history",
            params={"symbol": symbol, "resolution": resolution, "from": start, "to": end},
        )

    def place_order(self, payload: dict[str, Any]) -> Any:
        LOGGER.info("Placing order for %s", payload.get("symbol", "unknown"))
        return self._request("POST", "/market/orders/add", json_body=payload)

    def cancel_order(self, payload: dict[str, Any]) -> Any:
        return self._request("POST", "/market/orders/update-status", json_body=payload)

    def get_wallets(self) -> Any:
        return self._request("GET", "/users/wallets/list")
