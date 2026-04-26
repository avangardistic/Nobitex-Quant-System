"""Risk and position sizing helpers.

Limitations:
- Supports long-only position sizing by default and simple VaR estimation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class RiskDecision:
    quantity: float
    stop_price: float | None
    take_profit_price: float | None


class RiskManager:
    """Position sizing and risk controls."""

    def __init__(self, risk_per_trade: float = 0.01, max_positions: int = 1) -> None:
        self.risk_per_trade = risk_per_trade
        self.max_positions = max_positions

    def position_size(self, capital: float, entry_price: float, stop_price: float | None = None) -> float:
        if entry_price <= 0:
            raise ValueError("entry_price must be positive")
        if stop_price is None or stop_price <= 0 or stop_price >= entry_price:
            return capital * self.risk_per_trade / entry_price
        per_unit_risk = entry_price - stop_price
        return max(0.0, (capital * self.risk_per_trade) / per_unit_risk)

    def build_decision(self, capital: float, entry_price: float, stop_pct: float | None = None, take_profit_pct: float | None = None) -> RiskDecision:
        stop_price = entry_price * (1 - stop_pct) if stop_pct else None
        take_profit_price = entry_price * (1 + take_profit_pct) if take_profit_pct else None
        quantity = self.position_size(capital, entry_price, stop_price)
        return RiskDecision(quantity=quantity, stop_price=stop_price, take_profit_price=take_profit_price)

    @staticmethod
    def historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
        if returns.empty:
            return 0.0
        percentile = (1 - confidence) * 100
        return abs(float(np.percentile(returns.dropna(), percentile)))

    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> float:
        if equity_curve.empty:
            return 0.0
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max.replace(0, math.nan)
        return abs(float(drawdown.min()))
