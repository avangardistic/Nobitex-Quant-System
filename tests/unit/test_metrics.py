import pandas as pd

from backtest.metrics import summarize


def test_summarize_metrics():
    curve = pd.Series([100, 101, 105, 103], dtype=float)
    metrics = summarize(curve)
    assert "sharpe" in metrics
    assert metrics["max_drawdown"] >= 0
