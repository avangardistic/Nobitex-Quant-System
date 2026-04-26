import pandas as pd

from strategies.base.context import StrategyContext
from strategies.user.MeanReversionPAXGIRTProfitable import MeanReversionPAXGIRTEnhanced


def _history_frame(length: int = 80) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=length, freq="h", tz="UTC")
    close = pd.Series([100.0 + i for i in range(length)], index=index, dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": 1000.0,
        },
        index=index,
    )


def test_mean_reversion_buy_signal_requires_uptrend_pullback():
    strategy = MeanReversionPAXGIRTEnhanced()
    strategy.warmup_bars = 20
    strategy.cooldown_bars = 2
    strategy.entry_z = 1.5

    history = _history_frame(30)
    current_price = float(history["close"].iloc[-1])

    strategy.calculate_indicators = lambda data: {
        "zscore": pd.Series([-2.0] * len(data), index=data.index, dtype=float),
        "atr": pd.Series([2.0] * len(data), index=data.index, dtype=float),
        "vol_ratio": pd.Series([1.0] * len(data), index=data.index, dtype=float),
        "ema200": pd.Series([current_price - 5.0] * len(data), index=data.index, dtype=float),
    }

    context = StrategyContext(symbol="PAXGIRT", data=history, history=history, current_index=len(history) - 1)
    signal = strategy.generate_signal(context)

    assert signal is not None
    assert signal.action == "buy"


def test_mean_reversion_reset_clears_cooldown_state():
    strategy = MeanReversionPAXGIRTEnhanced()
    strategy.warmup_bars = 20
    strategy.cooldown_bars = 100
    strategy.entry_z = 1.5

    history = _history_frame(30)
    current_price = float(history["close"].iloc[-1])

    strategy.calculate_indicators = lambda data: {
        "zscore": pd.Series([-2.0] * len(data), index=data.index, dtype=float),
        "atr": pd.Series([2.0] * len(data), index=data.index, dtype=float),
        "vol_ratio": pd.Series([1.0] * len(data), index=data.index, dtype=float),
        "ema200": pd.Series([current_price - 5.0] * len(data), index=data.index, dtype=float),
    }

    context = StrategyContext(symbol="PAXGIRT", data=history, history=history, current_index=len(history) - 1)
    first = strategy.generate_signal(context)
    second = strategy.generate_signal(context)
    strategy.reset()
    third = strategy.generate_signal(context)

    assert first is not None
    assert second is None
    assert third is not None
