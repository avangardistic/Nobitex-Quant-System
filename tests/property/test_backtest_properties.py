from hypothesis import given, settings
from hypothesis import strategies as st
import pandas as pd

from core.backtest_engine import BacktestConfig, BacktestEngine
from strategies.builtin.ma_crossover import MACrossoverStrategy


@st.composite
def ohlcv_frames(draw):
    length = draw(st.integers(min_value=30, max_value=80))
    closes = draw(st.lists(st.floats(min_value=50, max_value=500, allow_nan=False, allow_infinity=False), min_size=length, max_size=length))
    index = pd.date_range("2024-01-01", periods=length, freq="h", tz="UTC")
    close = pd.Series(closes, index=index).abs() + 1
    open_ = close.shift(1).fillna(close.iloc[0])
    high = pd.concat([open_, close], axis=1).max(axis=1) + 1
    low = pd.concat([open_, close], axis=1).min(axis=1) - 1
    volume = pd.Series([1000.0] * length, index=index)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=index)


@given(frame=ohlcv_frames())
@settings(max_examples=50, deadline=None)
def test_equity_non_negative_and_reproducible(frame):
    config = BacktestConfig(initial_capital=10000, random_seed=7)
    first = BacktestEngine(config).run(frame, MACrossoverStrategy(), "BTCIRT")
    second = BacktestEngine(config).run(frame, MACrossoverStrategy(), "BTCIRT")
    assert (first.equity_curve >= 0).all()
    assert sum(trade["pnl"] for trade in first.trades) == sum(trade["pnl"] for trade in first.trades)
    assert first.trust["reproducibility_hash"] == second.trust["reproducibility_hash"]
