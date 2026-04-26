"""Template users can copy into strategies/user/.

Limitations:
- Demonstrates the expected API but does not implement a profitable edge.
"""

import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class TemplateStrategy(BaseStrategy):
    name = "TemplateStrategy"

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        return {"close": data["close"]}

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        if len(context.history) < 2:
            return None
        timestamp = context.data.index[context.current_index]
        if context.history["close"].iloc[-1] > context.history["close"].iloc[-2]:
            return Signal(timestamp=timestamp, symbol=context.symbol, action="buy")
        return None
