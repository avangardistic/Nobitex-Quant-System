"""Commission, spread, and slippage calculations.

Limitations:
- Partial fills are not modeled; costs are applied to full fills only.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass


@dataclass
class FillResult:
    effective_price: float
    commission: float
    spread_cost: float
    slippage_cost: float


class CostEngine:
    """Deterministic cost model."""

    def __init__(self, commission_rate: float, spread_bps: float, slippage_bps: float, seed: int = 42) -> None:
        self.commission_rate = commission_rate
        self.spread_bps = spread_bps
        self.slippage_bps = slippage_bps
        self.random = random.Random(seed)
        self.seed = seed

    def compute_slippage_bps(self, order_size: float, avg_volume: float, volatility: float = 0.0) -> float:
        base = self.slippage_bps
        if base <= 0:
            return 0.0
        if avg_volume <= 0:
            return base
        extra = min(20.0, (order_size / avg_volume) * 10.0 + volatility * 100.0)
        return base + extra

    def apply(self, price: float, quantity: float, side: str, avg_volume: float, volatility: float = 0.0) -> FillResult:
        direction = 1 if side.lower() == "buy" else -1
        slippage_bps = self.compute_slippage_bps(quantity, avg_volume, volatility)
        spread_cost = price * (self.spread_bps / 10_000) / 2
        slippage_cost = price * (slippage_bps / 10_000)
        effective_price = price * (1 + direction * ((self.spread_bps / 10_000) / 2 + (slippage_bps / 10_000)))
        commission = effective_price * quantity * self.commission_rate
        return FillResult(effective_price, commission, spread_cost * quantity, slippage_cost * quantity)

    @staticmethod
    def reproducibility_hash(trades: list[dict]) -> str:
        material = repr(trades).encode("utf-8")
        return hashlib.sha256(material).hexdigest()
