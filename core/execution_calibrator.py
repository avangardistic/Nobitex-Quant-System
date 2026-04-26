"""Build calibrated execution profiles from observed order book snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Any

from core.client import NobitexClient
from core.execution_profile import ExecutionProfile


@dataclass
class OrderBookSnapshot:
    best_bid: float
    best_ask: float
    spread_bps: float
    visible_depth: float
    raw: dict[str, Any]


class ExecutionCalibrator:
    """Estimate symbol-specific spread and slippage assumptions from order books."""

    def __init__(self, client: NobitexClient) -> None:
        self.client = client

    @staticmethod
    def _parse_levels(payload: dict[str, Any], key: str) -> list[tuple[float, float]]:
        levels = payload.get(key) or payload.get(key.upper()) or []
        parsed: list[tuple[float, float]] = []
        for level in levels:
            if isinstance(level, dict):
                price = level.get("price") or level.get("p") or level.get("0")
                quantity = level.get("quantity") or level.get("q") or level.get("1")
            else:
                if len(level) < 2:
                    continue
                price, quantity = level[0], level[1]
            try:
                parsed.append((float(price), float(quantity)))
            except (TypeError, ValueError):
                continue
        return parsed

    def snapshot(self, symbol: str) -> OrderBookSnapshot:
        payload = self.client.get_orderbook(symbol)
        bids = self._parse_levels(payload, "bids")
        asks = self._parse_levels(payload, "asks")
        if not bids or not asks:
            raise ValueError(f"Order book for {symbol} did not contain usable bids/asks")
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid = max((best_bid + best_ask) / 2, 1e-12)
        spread_bps = ((best_ask - best_bid) / mid) * 10_000
        visible_depth = sum(quantity for _, quantity in bids[:5] + asks[:5])
        return OrderBookSnapshot(best_bid=best_bid, best_ask=best_ask, spread_bps=spread_bps, visible_depth=visible_depth, raw=payload)

    def calibrate(self, symbol: str, snapshots: int = 5) -> ExecutionProfile:
        observed = [self.snapshot(symbol) for _ in range(max(snapshots, 1))]
        spreads = [item.spread_bps for item in observed]
        depths = [item.visible_depth for item in observed]
        median_spread = float(median(spreads)) if spreads else 5.0
        median_depth = float(median(depths)) if depths else 0.0
        # Conservative slippage heuristic that scales with thinner visible depth.
        slippage_bps = max(3.0, min(25.0, median_spread * 0.75 + (10.0 if median_depth <= 0 else 1_000 / max(median_depth, 1.0))))
        profile = ExecutionProfile(
            symbol=symbol,
            mode="calibrated",
            spread_bps=median_spread,
            slippage_bps=slippage_bps,
            calibrated_at=datetime.now(timezone.utc).isoformat(),
            sample_count=len(observed),
            depth_levels=[{"visible_depth": median_depth}],
            metadata={"source": "orderbook", "note": "Spread/slippage estimated from top-of-book snapshots"},
        )
        return profile
