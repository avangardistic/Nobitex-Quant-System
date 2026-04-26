"""Reusable test fixture builders."""

import pandas as pd


def synthetic_ohlcv(length: int = 50) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=length, freq="h", tz="UTC")
    prices = pd.Series(range(100, 100 + length), index=index, dtype=float)
    return pd.DataFrame(
        {"open": prices, "high": prices + 1, "low": prices - 1, "close": prices + 0.5, "volume": 1000.0},
        index=index,
    )
