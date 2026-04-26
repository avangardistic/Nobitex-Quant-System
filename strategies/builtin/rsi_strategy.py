"""RSI mean-reversion reference strategy.

Limitations:
- Long-only and does not pyramid positions.
"""

import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.indicators import rsi
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class RSIStrategy(BaseStrategy):
    name = "RSIStrategy"

    def __init__(self, oversold: float = 30, overbought: float = 70) -> None:
        self.oversold = oversold
        self.overbought = overbought

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        return {"rsi": rsi(data["close"], 14)}

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        history = context.history
        if len(history) < 20:
            return None
        value = self.calculate_indicators(history)["rsi"].iloc[-1]
        timestamp = context.data.index[context.current_index]
        if pd.isna(value):
            return None
        if value < self.oversold:
            return Signal(timestamp=timestamp, symbol=context.symbol, action="buy")
        if value > self.overbought:
            return Signal(timestamp=timestamp, symbol=context.symbol, action="sell")
        return None
