from core.backtest_engine import BacktestConfig, BacktestEngine
from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy
from strategies.builtin.ma_crossover import MACrossoverStrategy
from strategies.builtin.rsi_strategy import RSIStrategy


def test_end_to_end_backtest_is_deterministic(sample_frame):
    config = BacktestConfig(initial_capital=10000, random_seed=42)
    engine = BacktestEngine(config)
    first = engine.run(sample_frame, MACrossoverStrategy(), "BTCIRT")
    second = BacktestEngine(config).run(sample_frame, MACrossoverStrategy(), "BTCIRT")
    assert first.trust["reproducibility_hash"] == second.trust["reproducibility_hash"]
    assert first.metrics == second.metrics


def test_multiple_scenarios(sample_frame):
    trend = BacktestEngine(BacktestConfig(initial_capital=10000)).run(sample_frame, MACrossoverStrategy(), "BTCIRT")
    mean_reversion = BacktestEngine(BacktestConfig(initial_capital=10000)).run(sample_frame.iloc[::-1].copy(), RSIStrategy(), "BTCIRT")
    random_like = BacktestEngine(BacktestConfig(initial_capital=10000)).run(sample_frame.sample(frac=1, random_state=42).sort_index(), MACrossoverStrategy(), "BTCIRT")
    assert trend.equity_curve.iloc[-1] > 0
    assert mean_reversion.equity_curve.iloc[-1] > 0
    assert random_like.equity_curve.iloc[-1] > 0


class QuantitySignalStrategy(BaseStrategy):
    def calculate_indicators(self, data):
        return {"close": data["close"]}

    def generate_signal(self, context: StrategyContext):
        timestamp = context.data.index[context.current_index]
        if context.current_index == 1:
            return Signal(
                timestamp=timestamp,
                symbol=context.symbol,
                action="buy",
                metadata={"quantity": 10, "execution_price": float(context.data.iloc[context.current_index]["open"])},
            )
        if context.current_index == len(context.data) - 1:
            return Signal(
                timestamp=timestamp,
                symbol=context.symbol,
                action="sell",
                metadata={"execution_price": float(context.data.iloc[context.current_index]["close"]), "exit_reason": "test_exit"},
            )
        return None


class ResettableSingleShotStrategy(BaseStrategy):
    def __init__(self):
        self.reset()

    def reset(self):
        self.fired = False

    def calculate_indicators(self, data):
        return {"close": data["close"]}

    def generate_signal(self, context: StrategyContext):
        if self.fired:
            return None
        if context.current_index == 1:
            self.fired = True
            return Signal(timestamp=context.data.index[context.current_index], symbol=context.symbol, action="buy")
        return None


def test_backtest_uses_signal_quantity_and_explicit_execution_price(sample_frame):
    result = BacktestEngine(
        BacktestConfig(initial_capital=10_000, execution_model="next_open", commission_rate=0.0, spread_bps=0.0, slippage_bps=0.0)
    ).run(
        sample_frame.iloc[:6],
        QuantitySignalStrategy(),
        "BTCIRT",
    )
    assert result.trades
    assert result.trades[0]["quantity"] == 10
    assert result.trades[0]["entry_price"] == float(sample_frame.iloc[1]["open"])
    assert result.trades[0]["exit_price"] == float(sample_frame.iloc[5]["close"])
    assert result.trades[0]["exit_reason"] == "test_exit"


def test_backtest_resets_strategy_state_between_runs(sample_frame):
    strategy = ResettableSingleShotStrategy()
    config = BacktestConfig(initial_capital=10_000, random_seed=42)
    first = BacktestEngine(config).run(sample_frame, strategy, "BTCIRT")
    second = BacktestEngine(config).run(sample_frame, strategy, "BTCIRT")
    assert len(first.trades) == len(second.trades)
    assert first.trust["reproducibility_hash"] == second.trust["reproducibility_hash"]
