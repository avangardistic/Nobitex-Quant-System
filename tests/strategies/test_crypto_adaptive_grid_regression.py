import pandas as pd

from core.backtest_engine import BacktestConfig, BacktestEngine
from strategies.user.crypto_adaptive_grid import CryptoAdaptiveGridStrategy


def _sample_minute_frame() -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=360, freq="min", tz="UTC")
    base = pd.Series(
        [50000 + ((i % 30) - 15) * 6 + i * 0.25 for i in range(len(index))],
        index=index,
        dtype=float,
    )
    return pd.DataFrame(
        {
            "open": base,
            "high": base + 18,
            "low": base - 18,
            "close": base + 3,
            "volume": 1200.0,
        },
        index=index,
    )


def test_crypto_adaptive_grid_regression_is_deterministic():
    frame = _sample_minute_frame()
    config = BacktestConfig(initial_capital=10_000, random_seed=42)

    first = BacktestEngine(config).run(frame, CryptoAdaptiveGridStrategy(), "BTCUSDT")
    second = BacktestEngine(config).run(frame, CryptoAdaptiveGridStrategy(), "BTCUSDT")

    assert first.trades
    assert first.trust["lookahead_verification_passed"] is True
    assert first.trust["reproducibility_hash"] == second.trust["reproducibility_hash"]
    assert first.metrics == second.metrics


def test_crypto_adaptive_grid_reuses_strategy_instance_safely():
    frame = _sample_minute_frame()
    strategy = CryptoAdaptiveGridStrategy()
    config = BacktestConfig(initial_capital=10_000, random_seed=42)

    first = BacktestEngine(config).run(frame, strategy, "BTCUSDT")
    second = BacktestEngine(config).run(frame, strategy, "BTCUSDT")

    assert first.trust["reproducibility_hash"] == second.trust["reproducibility_hash"]
    assert first.metrics == second.metrics


def test_crypto_adaptive_grid_trades_use_strategy_quantity_metadata():
    frame = _sample_minute_frame()
    result = BacktestEngine(BacktestConfig(initial_capital=10_000, random_seed=42)).run(frame, CryptoAdaptiveGridStrategy(), "BTCUSDT")

    assert result.trades
    assert result.trades[0]["quantity"] < 1
