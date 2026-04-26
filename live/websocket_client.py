"""Market data feed handler with Nobitex polling and deterministic simulation fallback."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pandas as pd

from core.client import NobitexClient


@dataclass
class PriceTick:
    timestamp: str
    symbol: str
    price: float
    bid: float | None = None
    ask: float | None = None
    volume: float = 0.0
    source: str = "simulated"


class WebSocketPriceFeed:
    """Yield price ticks from Nobitex order books or deterministic simulated data."""

    def __init__(self, client: NobitexClient | None = None, seed: int = 42) -> None:
        self.client = client
        self.random = random.Random(seed)

    @staticmethod
    def _extract_best(payload: dict, key: str) -> tuple[float, float] | None:
        levels = payload.get(key) or payload.get(key.upper()) or []
        if not levels:
            return None
        level = levels[0]
        if isinstance(level, dict):
            price = level.get("price") or level.get("p")
            quantity = level.get("quantity") or level.get("q") or 0.0
        else:
            if len(level) < 2:
                return None
            price, quantity = level[0], level[1]
        return float(price), float(quantity)

    def live_tick(self, symbol: str) -> PriceTick:
        if self.client is None:
            raise RuntimeError("live_tick requires a NobitexClient")
        payload = self.client.get_orderbook(symbol)
        bid = self._extract_best(payload, "bids")
        ask = self._extract_best(payload, "asks")
        if bid is None or ask is None:
            raise ValueError(f"No usable order book levels for {symbol}")
        price = (bid[0] + ask[0]) / 2
        return PriceTick(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            price=price,
            bid=bid[0],
            ask=ask[0],
            volume=bid[1] + ask[1],
            source="orderbook",
        )

    def simulated_tick(self, symbol: str, previous_price: float | None = None) -> PriceTick:
        anchor = previous_price if previous_price is not None else 100.0 + self.random.random() * 10
        delta = self.random.uniform(-0.003, 0.003) * anchor
        price = max(anchor + delta, 1e-6)
        spread = price * 0.0005
        return PriceTick(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            price=price,
            bid=price - spread / 2,
            ask=price + spread / 2,
            volume=1_000.0,
            source="simulated",
        )

    def iter_ticks(
        self,
        symbol: str,
        *,
        stop_path: Path,
        interval_seconds: float,
        max_ticks: int | None = None,
        simulated: bool = False,
        data_file: str | None = None,
    ) -> Iterator[PriceTick]:
        previous_price: float | None = None
        if data_file:
            frame = pd.read_csv(data_file, parse_dates=["timestamp"])
            for _, row in frame.iterrows():
                if stop_path.exists():
                    break
                price = float(row["close"])
                yield PriceTick(
                    timestamp=pd.Timestamp(row["timestamp"]).tz_localize("UTC") if pd.Timestamp(row["timestamp"]).tzinfo is None else pd.Timestamp(row["timestamp"]).tz_convert("UTC"),
                    symbol=symbol,
                    price=price,
                    bid=price,
                    ask=price,
                    volume=float(row.get("volume", 0.0) or 0.0),
                    source="csv",
                )
            return
        count = 0
        while not stop_path.exists():
            tick = self.simulated_tick(symbol, previous_price) if simulated or self.client is None else self.live_tick(symbol)
            previous_price = tick.price
            yield tick
            count += 1
            if max_ticks is not None and count >= max_ticks:
                break
            if interval_seconds > 0:
                time.sleep(interval_seconds)
