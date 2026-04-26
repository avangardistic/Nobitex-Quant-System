import pandas as pd

from core.backtest_engine import BacktestConfig, BacktestEngine
from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class ShortFirstStrategy(BaseStrategy):
    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        return {"close": data["close"]}

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        ts = context.data.index[context.current_index]
        if context.current_index == 1:
            return Signal(timestamp=ts, symbol=context.symbol, action="sell")
        if context.current_index == len(context.data) - 1:
            return Signal(timestamp=ts, symbol=context.symbol, action="buy")
        return None


def test_backtest_engine_opens_and_closes_short_positions():
    index = pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC")
    prices = pd.Series([100, 99, 95, 93, 92, 90], index=index, dtype=float)
    frame = pd.DataFrame(
        {"open": prices, "high": prices + 1, "low": prices - 1, "close": prices, "volume": 1_000_000.0},
        index=index,
    )
    result = BacktestEngine(
        BacktestConfig(initial_capital=10_000, execution_model="same_close", commission_rate=0.0, spread_bps=0.0, slippage_bps=0.0)
    ).run(frame, ShortFirstStrategy(), "BTCUSDT")
    assert result.trades
    assert result.trades[0]["side"] == "short"
    assert result.trades[0]["pnl"] > 0
    assert result.equity_curve.iloc[-1] > 10_000
