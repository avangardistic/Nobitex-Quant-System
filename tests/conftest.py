"""Shared pytest fixtures."""

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture()
def sample_frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=80, freq="h", tz="UTC")
    prices = pd.Series(range(100, 180), index=index, dtype=float)
    return pd.DataFrame(
        {"open": prices, "high": prices + 1, "low": prices - 1, "close": prices + 0.5, "volume": 1000.0},
        index=index,
    )


@pytest.fixture()
def csv_data_file(sample_frame: pd.DataFrame, tmp_path: Path) -> Path:
    path = tmp_path / "sample.csv"
    sample_frame.rename_axis("timestamp").to_csv(path)
    return path
