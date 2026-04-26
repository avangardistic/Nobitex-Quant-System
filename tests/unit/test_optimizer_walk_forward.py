import pandas as pd

from backtest.optimizer import grid_search, random_search
from backtest.walk_forward import rolling_windows


def test_grid_and_random_search():
    assert len(grid_search({"a": [1, 2], "b": [3]})) == 2
    assert random_search({"a": [1], "b": [2]}, 3, seed=1)[0] == {"a": 1, "b": 2}


def test_rolling_windows(sample_frame):
    windows = rolling_windows(sample_frame, 20, 10)
    assert windows
    assert len(windows[0][0]) == 20
