"""Correctness checks for the backtest engine.

Limitations:
- Uses deterministic synthetic data and simple strategies, not exchange tick replay.
"""

from __future__ import annotations

import pandas as pd

from core.backtest_engine import BacktestConfig, BacktestEngine
from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):
    name = "BuyAndHoldStrategy"

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        return {"close": data["close"]}

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        if context.current_index == 1:
            return Signal(timestamp=context.data.index[context.current_index], symbol=context.symbol, action="buy")
        if context.current_index == len(context.data) - 1:
            return Signal(timestamp=context.data.index[context.current_index], symbol=context.symbol, action="sell")
        return None


class EveryBarStrategy(BaseStrategy):
    name = "EveryBarStrategy"

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        return {"close": data["close"]}

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        action = "buy" if context.current_index % 2 else "sell"
        return Signal(timestamp=context.data.index[context.current_index], symbol=context.symbol, action=action)


class CorrectnessChecker:
    """Known-result verification suite."""

    @staticmethod
    def synthetic_frame(length: int = 20, trend: bool = True) -> pd.DataFrame:
        index = pd.date_range("2024-01-01", periods=length, freq="D", tz="UTC")
        if trend:
            prices = pd.Series(range(100, 100 + length), index=index, dtype=float)
        else:
            prices = pd.Series([100.0] * length, index=index, dtype=float)
        return pd.DataFrame(
            {"open": prices, "high": prices + 1, "low": prices - 1, "close": prices, "volume": 1_000_000_000.0},
            index=index,
        )

    def run(self) -> dict[str, object]:
        frame = self.synthetic_frame()
        zero_cost_config = BacktestConfig(
            initial_capital=10_000,
            execution_model="same_close",
            commission_rate=0.0,
            spread_bps=0.0,
            slippage_bps=0.0,
        )
        result = BacktestEngine(zero_cost_config).run(frame, BuyAndHoldStrategy(), "BTCIRT")
        entry_price = float(frame["close"].iloc[1])
        final_price = float(frame["close"].iloc[-1])
        theoretical_final = zero_cost_config.initial_capital * (final_price / entry_price)
        cost_config = BacktestConfig(
            initial_capital=10_000,
            execution_model="same_close",
            commission_rate=0.001,
            spread_bps=0.0,
            slippage_bps=0.0,
        )
        cost_result = BacktestEngine(cost_config).run(frame, BuyAndHoldStrategy(), "BTCIRT")
        flat_frame = self.synthetic_frame(trend=False)
        churn_result = BacktestEngine(cost_config).run(flat_frame, EveryBarStrategy(), "BTCIRT")
        return {
            "buy_hold_trade_count": len(result.trades),
            "zero_cost_final_equity": float(result.equity_curve.iloc[-1]),
            "theoretical_final_equity": theoretical_final,
            "buy_hold_matches_theory": round(float(result.equity_curve.iloc[-1]), 6) == round(theoretical_final, 6),
            "commission_reduces_equity": float(cost_result.equity_curve.iloc[-1]) < float(result.equity_curve.iloc[-1]),
            "every_bar_loses_to_costs": float(churn_result.equity_curve.iloc[-1]) < cost_config.initial_capital,
            "lookahead_passed": result.trust["lookahead_verification_passed"],
        }
