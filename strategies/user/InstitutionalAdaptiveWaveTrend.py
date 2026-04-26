import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class InstitutionalAdaptiveWaveTrend(BaseStrategy):
    """
    Institutional-grade adaptive trend breakout strategy.
    Trades strong directional expansions with volatility regime filter.
    """

    name = "InstitutionalAdaptiveWaveTrend"

    def __init__(self) -> None:
        # Trend parameters
        self.ema_fast_length = 20
        self.ema_slow_length = 50

        # Volatility parameters
        self.volatility_window = 20
        self.volatility_median_window = 20

        # Momentum parameters
        self.momentum_period = 10

        # Breakout parameters
        self.breakout_period = 30

        # Warmup
        self.warmup_bars = 60

        # State tracking
        self._last_signal_index = -100

    def reset(self) -> None:
        """Reset internal state for deterministic replay."""
        self._last_signal_index = -100

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all required indicators aligned with input data."""
        close = data["close"].astype(float)

        # EMAs for trend direction
        ema_fast = close.ewm(span=self.ema_fast_length, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow_length, adjust=False).mean()

        # Returns and volatility
        returns = close.pct_change()
        volatility = returns.rolling(window=self.volatility_window).std()
        volatility_median = volatility.rolling(window=self.volatility_median_window).median()

        # Momentum (Rate of Change)
        momentum = close / close.shift(self.momentum_period) - 1

        # Breakout levels (shifted to prevent lookahead)
        rolling_high = close.rolling(window=self.breakout_period).max().shift(1)
        rolling_low = close.rolling(window=self.breakout_period).min().shift(1)

        return {
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "volatility": volatility,
            "volatility_median": volatility_median,
            "momentum": momentum,
            "rolling_high": rolling_high,
            "rolling_low": rolling_low,
        }

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        """Generate buy/sell signals based on trend breakout with volatility filter."""
        history = context.history

        # Warm-up protection
        if len(history) < self.warmup_bars:
            return None

        # Cooldown to reduce overtrading
        current_idx = context.current_index
        if current_idx - self._last_signal_index < 3:
            return None

        # Calculate indicators on historical data only
        indicators = self.calculate_indicators(history)

        # Get latest values
        ema_fast = indicators["ema_fast"].iloc[-1]
        ema_slow = indicators["ema_slow"].iloc[-1]
        volatility = indicators["volatility"].iloc[-1]
        volatility_median = indicators["volatility_median"].iloc[-1]
        momentum = indicators["momentum"].iloc[-1]
        rolling_high = indicators["rolling_high"].iloc[-1]
        rolling_low = indicators["rolling_low"].iloc[-1]

        # Ensure all indicators are valid
        if any(pd.isna(x) for x in [ema_fast, ema_slow, volatility, volatility_median, momentum, rolling_high, rolling_low]):
            return None

        current_close = float(history["close"].iloc[-1])
        timestamp = context.data.index[current_idx]

        # BUY CONDITIONS:
        # 1. Uptrend: Fast EMA above Slow EMA
        # 2. Breakout: Price above previous period high
        # 3. Positive momentum
        # 4. Volatility expansion regime
        if (ema_fast > ema_slow and
            current_close > rolling_high and
            momentum > 0 and
            volatility > volatility_median):

            self._last_signal_index = current_idx
            return Signal(
                timestamp=timestamp,
                symbol=context.symbol,
                action="buy",
            )

        # SELL CONDITIONS:
        # 1. Downtrend: Fast EMA below Slow EMA
        # 2. Breakdown: Price below previous period low
        # 3. Negative momentum
        # 4. Volatility expansion regime
        if (ema_fast < ema_slow and
            current_close < rolling_low and
            momentum < 0 and
            volatility > volatility_median):

            self._last_signal_index = current_idx
            return Signal(
                timestamp=timestamp,
                symbol=context.symbol,
                action="sell",
            )

        return None