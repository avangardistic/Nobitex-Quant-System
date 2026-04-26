"""Moving-average crossover reference strategy.

Limitations:
- Long-only and designed for bar-close signals executed on the next bar.
"""

import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.indicators import sma
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class MACrossoverStrategy(BaseStrategy):
    name = "MACrossoverStrategy"

    def __init__(self, fast: int = 5, slow: int = 20) -> None:
        self.fast = fast
        self.slow = slow

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        return {
            "fast": sma(data["close"], self.fast),
            "slow": sma(data["close"], self.slow),
        }

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        history = context.history
        if len(history) < self.slow + 1:
            return None
        indicators = self.calculate_indicators(history)
        fast = indicators["fast"].iloc[-1]
        slow = indicators["slow"].iloc[-1]
        prev_fast = indicators["fast"].iloc[-2]
        prev_slow = indicators["slow"].iloc[-2]
        timestamp = context.data.index[context.current_index]
        if pd.notna(prev_fast) and pd.notna(prev_slow) and prev_fast <= prev_slow and fast > slow:
            return Signal(timestamp=timestamp, symbol=context.symbol, action="buy")
        if pd.notna(prev_fast) and pd.notna(prev_slow) and prev_fast >= prev_slow and fast < slow:
            return Signal(timestamp=timestamp, symbol=context.symbol, action="sell")
        return None
