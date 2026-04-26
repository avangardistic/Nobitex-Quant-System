# فایل: strategies/user/SimpleBuyAndHold.py
import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class SimpleBuyAndHold(BaseStrategy):
    """Simple buy and hold - buys at bar 10 and holds forever."""
    
    name = "SimpleBuyAndHold"

    def __init__(self) -> None:
        self.entry_bar = 10
        self._bought = False
        self.reset()

    def reset(self) -> None:
        self._bought = False

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        return {}

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        if self._bought:
            return None
            
        if len(context.history) < self.entry_bar:
            return None

        current_price = float(context.history["close"].iloc[-1])
        timestamp = context.data.index[context.current_index]
        
        self._bought = True
        
        print(f"\n🔵 BUY & HOLD at bar {context.current_index}")
        print(f"   Price: {current_price:.2f}")
        
        return Signal(
            timestamp=timestamp,
            symbol=context.symbol,
            action="buy",
        )