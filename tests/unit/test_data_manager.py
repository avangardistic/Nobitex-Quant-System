import pandas as pd
import pytest

from core.data_manager import DataManager


def test_normalize_history():
    payload = {"t": [1, 2], "o": [1, 2], "h": [2, 3], "l": [0, 1], "c": [1.5, 2.5], "v": [10, 20]}
    frame = DataManager.normalize_history(payload)
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
    assert len(frame) == 2


def test_resample(sample_frame):
    resampled = DataManager.resample(sample_frame, "4h")
    assert len(resampled) < len(sample_frame)


def test_validate_columns_raises():
    with pytest.raises(ValueError):
        DataManager.validate_columns(pd.DataFrame({"open": [1]}))
