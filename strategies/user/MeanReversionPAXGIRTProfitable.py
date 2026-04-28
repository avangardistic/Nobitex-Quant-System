from __future__ import annotations

import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.indicators import atr
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class MeanReversionPAXGIRTEnhanced(BaseStrategy):
    """Trend-filtered mean-reversion strategy for PAXGIRT."""

    name = "MeanReversionPAXGIRTEnhanced"

    def __init__(self) -> None:
        self.warmup_bars = 50
        self.lookback = 20
        self.ema_period = 50
        self.atr_period = 14
        self.entry_z = 2.0
        self.volume_ratio_floor = 0.5
        self.cooldown_bars = 5
        self._last_signal_index = -10_000

    def reset(self) -> None:
        self._last_signal_index = -10_000

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)
        mean = close.rolling(self.lookback, min_periods=self.lookback).mean()
        std = close.rolling(self.lookback, min_periods=self.lookback).std()
        zscore = (close - mean) / std.replace(0, pd.NA)
        average_volume = volume.rolling(self.lookback, min_periods=self.lookback).mean()
        vol_ratio = volume / average_volume.replace(0, pd.NA)
        ema200 = close.ewm(span=self.ema_period, adjust=False, min_periods=self.ema_period).mean()
        return {
            "zscore": zscore,
            "atr": atr(data, self.atr_period),
            "vol_ratio": vol_ratio,
            "ema200": ema200,
        }

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        history = context.history
        if len(history) < self.warmup_bars:
            return None
        if context.current_index - self._last_signal_index < self.cooldown_bars:
            return None

        indicators = self.calculate_indicators(history)
        zscore = indicators["zscore"].iloc[-1]
        atr_value = indicators["atr"].iloc[-1]
        vol_ratio = indicators["vol_ratio"].iloc[-1]
        ema200 = indicators["ema200"].iloc[-1]
        current_price = float(history["close"].iloc[-1])

        values = [zscore, atr_value, vol_ratio, ema200]
        if any(pd.isna(value) for value in values):
            return None
        if float(zscore) > -self.entry_z:
            return None
        if current_price <= float(ema200):
            return None
        if float(vol_ratio) < self.volume_ratio_floor:
            return None

        self._last_signal_index = context.current_index
        return Signal(
            timestamp=context.data.index[context.current_index],
            symbol=context.symbol,
            action="buy",
            stop_loss=current_price - 2.0 * float(atr_value),
            take_profit=current_price + 3.0 * float(atr_value),
        )
