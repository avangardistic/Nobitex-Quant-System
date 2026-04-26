import pytest

from config.settings import Settings
from core.client import NobitexClient, TokenBucket
from core.exceptions import RateLimitError


class DummyResponse:
    def __init__(self, payload, ok=True, status_code=200, text=""):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


class DummySession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers=None, params=None, json=None, timeout=None):
        self.calls.append((method, url, headers, params, json, timeout))
        return DummyResponse({"ok": True})


def test_token_bucket_raises_when_empty():
    bucket = TokenBucket(capacity=1, refill_window_seconds=1000)
    bucket.acquire()
    with pytest.raises(RateLimitError):
        bucket.acquire()


def test_client_requests_orderbook():
    session = DummySession()
    client = NobitexClient(Settings(api_token="token"), session=session)
    payload = client.get_orderbook("BTCIRT")
    assert payload == {"ok": True}
    assert session.calls[0][0] == "GET"
