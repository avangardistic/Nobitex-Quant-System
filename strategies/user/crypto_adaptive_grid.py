from __future__ import annotations

import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class CryptoAdaptiveGridStrategy(BaseStrategy):
    """Deterministic adaptive grid-style strategy for crypto regression tests."""

    name = "CryptoAdaptiveGridStrategy"

    def __init__(self) -> None:
        self.warmup_bars = 60
        self.grid_window = 30
        self.base_quantity = 0.1
        self._entered = False

    def reset(self) -> None:
        self._entered = False

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        close = data["close"].astype(float)
        rolling_mean = close.rolling(self.grid_window, min_periods=self.grid_window).mean()
        rolling_std = close.rolling(self.grid_window, min_periods=self.grid_window).std()
        lower_grid = rolling_mean - rolling_std
        upper_grid = rolling_mean + rolling_std
        return {
            "rolling_mean": rolling_mean,
            "rolling_std": rolling_std,
            "lower_grid": lower_grid,
            "upper_grid": upper_grid,
        }

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        history = context.history
        if self._entered or len(history) < self.warmup_bars:
            return None

        indicators = self.calculate_indicators(history)
        lower_grid = indicators["lower_grid"].iloc[-1]
        current_close = float(history["close"].iloc[-1])

        if pd.isna(lower_grid) or current_close > float(lower_grid):
            return None

        self._entered = True
        return Signal(
            timestamp=context.data.index[context.current_index],
            symbol=context.symbol,
            action="buy",
            metadata={"quantity": self.base_quantity},
        )
