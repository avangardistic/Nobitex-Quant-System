"""Walk-forward split generation.

Limitations:
- Generates contiguous windows only.
"""

from __future__ import annotations

import pandas as pd


def rolling_windows(frame: pd.DataFrame, train_size: int, test_size: int) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    windows = []
    start = 0
    while start + train_size + test_size <= len(frame):
        train = frame.iloc[start : start + train_size]
        test = frame.iloc[start + train_size : start + train_size + test_size]
        windows.append((train, test))
        start += test_size
    return windows
