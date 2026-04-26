"""Historical data download, caching, and resampling utilities.

Limitations:
- Uses CSV fallback when parquet support is unavailable in the runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from config.settings import Settings
from core.client import NobitexClient


class DataManager:
    """Manage OHLCV market data."""

    def __init__(self, client: NobitexClient | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.client = client or NobitexClient(self.settings)
        self.settings.data_dir.mkdir(exist_ok=True)

    @staticmethod
    def normalize_history(payload: dict) -> pd.DataFrame:
        frame = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(payload["t"], unit="s", utc=True),
                "open": payload["o"],
                "high": payload["h"],
                "low": payload["l"],
                "close": payload["c"],
                "volume": payload.get("v", [0] * len(payload["t"])),
            }
        )
        frame = frame.sort_values("timestamp").set_index("timestamp")
        return frame.astype(float)

    def cache_path(self, symbol: str, timeframe: str) -> Path:
        stem = f"{symbol}_{timeframe}".lower()
        return self.settings.data_dir / f"{stem}.csv"

    @staticmethod
    def timeframe_label(timeframe: str) -> str:
        normalized = timeframe.strip()
        if normalized.isdigit():
            return f"{normalized}m"
        return normalized.lower()

    def ranged_cache_path(self, symbol: str, timeframe: str, start, end) -> Path:
        start_date = pd.Timestamp(start).strftime("%Y-%m-%d")
        end_date = pd.Timestamp(end).strftime("%Y-%m-%d")
        stem = f"{symbol}_{self.timeframe_label(timeframe)}_{start_date}_{end_date}".lower()
        return self.settings.data_dir / f"{stem}.csv"

    def save(self, frame: pd.DataFrame, symbol: str, timeframe: str) -> Path:
        path = self.cache_path(symbol, timeframe)
        frame.to_csv(path)
        return path

    @staticmethod
    def save_to_path(frame: pd.DataFrame, path: Path) -> Path:
        path.parent.mkdir(exist_ok=True)
        frame.to_csv(path)
        return path

    def load(self, symbol: str, timeframe: str) -> pd.DataFrame:
        path = self.cache_path(symbol, timeframe)
        return pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")

    def fetch_history(self, symbol: str, timeframe: str, start: int, end: int, use_cache: bool = True) -> pd.DataFrame:
        path = self.cache_path(symbol, timeframe)
        if use_cache and path.exists():
            return self.load(symbol, timeframe)
        payload = self.client.get_ohlcv(symbol, timeframe, start, end)
        frame = self.normalize_history(payload)
        self.save(frame, symbol, timeframe)
        return frame

    @staticmethod
    def resample(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
        return frame.resample(rule).agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()

    @staticmethod
    def validate_columns(frame: pd.DataFrame, required: Iterable[str] = ("open", "high", "low", "close", "volume")) -> None:
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
