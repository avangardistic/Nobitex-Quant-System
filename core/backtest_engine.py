"""Event-driven backtest engine with deterministic, no-lookahead execution.

Limitations:
- Supports a single symbol and full fills.
- Protective logic for trailing stop and risk-free uses optional signal metadata.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass

import pandas as pd

from backtest.metrics import summarize
from core.cost_engine import CostEngine
from core.risk_manager import RiskManager
from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


@dataclass
class BacktestConfig:
    initial_capital: float = 10_000_000
    execution_model: str = "next_open"
    random_seed: int = 42
    execution_mode: str = "static"
    execution_profile_path: str | None = None
    execution_profile_hash: str | None = None
    commission_rate: float = 0.0015
    spread_bps: float = 5.0
    slippage_bps: float = 5.0
    max_positions: int = 1
    allow_shorting: bool = True


@dataclass
class Trade:
    entry_time: object
    exit_time: object | None
    side: str
    quantity: float
    entry_price: float
    exit_price: float | None
    stop_loss: float | None = None
    take_profit: float | None = None
    pnl: float = 0.0
    commission: float = 0.0
    spread_cost: float = 0.0
    slippage_cost: float = 0.0
    exit_reason: str | None = None


@dataclass
class Position:
    entry_time: object
    side: str
    quantity: float
    entry_price: float
    stop_loss: float | None
    take_profit: float | None
    commission: float
    spread_cost: float
    slippage_cost: float
    point_value: float = 1.0
    trailing_start: float | None = None
    trailing_step: float | None = None
    risk_free_activation: float | None = None
    risk_free_offset: float | None = None
    engine_managed_exits: bool = True


@dataclass
class BacktestResult:
    trades: list[dict]
    equity_curve: pd.Series
    metrics: dict[str, float]
    trust: dict[str, object]


class BacktestEngine:
    """Deterministic bar-by-bar backtester with long and short support."""

    def __init__(self, config: BacktestConfig | None = None, risk_manager: RiskManager | None = None) -> None:
        self.config = config or BacktestConfig()
        self.risk_manager = risk_manager or RiskManager(max_positions=self.config.max_positions)
        self.cost_engine = CostEngine(
            commission_rate=self.config.commission_rate,
            spread_bps=self.config.spread_bps,
            slippage_bps=self.config.slippage_bps,
            seed=self.config.random_seed,
        )

    def _execution_price(self, frame: pd.DataFrame, signal_index: int) -> tuple[object, float]:
        if self.config.execution_model == "same_close":
            timestamp = frame.index[signal_index]
            return timestamp, float(frame.iloc[signal_index]["close"])
        execution_index = min(signal_index + 1, len(frame) - 1)
        timestamp = frame.index[execution_index]
        return timestamp, float(frame.iloc[execution_index]["open"])

    @staticmethod
    def _signal_execution_price(signal: Signal) -> float | None:
        if not signal.metadata:
            return None
        value = signal.metadata.get("execution_price")
        if value is None:
            return None
        price = float(value)
        if not math.isfinite(price) or price <= 0:
            return None
        return price

    @staticmethod
    def _signal_quantity(signal: Signal, fallback_quantity: float) -> float:
        if not signal.metadata or signal.metadata.get("quantity") is None:
            return fallback_quantity
        quantity = float(signal.metadata["quantity"])
        if not math.isfinite(quantity) or quantity <= 0:
            return fallback_quantity
        return quantity

    @staticmethod
    def _signal_manages_exits(signal: Signal) -> bool:
        if not signal.metadata:
            return True
        return bool(signal.metadata.get("engine_managed_exits", True))

    @staticmethod
    def _metadata_value(signal: Signal, key: str) -> float | None:
        if not signal.metadata:
            return None
        value = signal.metadata.get(key)
        return None if value is None else float(value)

    @staticmethod
    def _position_sign(position: Position) -> float:
        return 1.0 if position.side == "long" else -1.0

    def _mark_to_market_equity(self, cash: float, position: Position | None, mark_price: float) -> float:
        if position is None:
            return cash
        if position.side == "long":
            return cash + position.quantity * mark_price
        return cash - position.quantity * mark_price

    def _open_position(
        self,
        cash: float,
        signal: Signal,
        execution_time: object,
        raw_price: float,
        avg_volume: float,
        volatility: float,
    ) -> tuple[float, Position | None]:
        default_quantity = cash / raw_price if raw_price > 0 else 0.0
        quantity = self._signal_quantity(signal, default_quantity)
        if quantity <= 0:
            return cash, None

        if signal.action == "buy":
            fill = self.cost_engine.apply(raw_price, quantity, "buy", avg_volume, volatility)
            trade_value = fill.effective_price * quantity + fill.commission
            if trade_value > cash:
                max_affordable = max(quantity, 0.0)
                min_affordable = 0.0
                for _ in range(24):
                    candidate = (max_affordable + min_affordable) / 2
                    candidate_fill = self.cost_engine.apply(raw_price, candidate, "buy", avg_volume, volatility)
                    candidate_value = candidate_fill.effective_price * candidate + candidate_fill.commission
                    if candidate_value <= cash:
                        min_affordable = candidate
                        fill = candidate_fill
                        trade_value = candidate_value
                    else:
                        max_affordable = candidate
                quantity = min_affordable
            if quantity <= 0:
                return cash, None
            cash -= trade_value
            side = "long"
        else:
            fill = self.cost_engine.apply(raw_price, quantity, "sell", avg_volume, volatility)
            proceeds = fill.effective_price * quantity - fill.commission
            cash += proceeds
            side = "short"

        position = Position(
            entry_time=execution_time,
            side=side,
            quantity=quantity,
            entry_price=fill.effective_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            commission=fill.commission,
            spread_cost=fill.spread_cost,
            slippage_cost=fill.slippage_cost,
            point_value=self._metadata_value(signal, "point_value") or 1.0,
            trailing_start=self._metadata_value(signal, "trailing_start"),
            trailing_step=self._metadata_value(signal, "trailing_step"),
            risk_free_activation=self._metadata_value(signal, "risk_free_activation"),
            risk_free_offset=self._metadata_value(signal, "risk_free_offset"),
            engine_managed_exits=self._signal_manages_exits(signal),
        )
        return cash, position

    def _close_position(
        self,
        cash: float,
        position: Position,
        exit_time: object,
        raw_price: float,
        avg_volume: float,
        volatility: float,
        reason: str,
    ) -> tuple[float, dict]:
        close_side = "sell" if position.side == "long" else "buy"
        fill = self.cost_engine.apply(raw_price, position.quantity, close_side, avg_volume, volatility)

        if position.side == "long":
            cash += fill.effective_price * position.quantity - fill.commission
            pnl = (fill.effective_price - position.entry_price) * position.quantity - position.commission - fill.commission
        else:
            cash -= fill.effective_price * position.quantity + fill.commission
            pnl = (position.entry_price - fill.effective_price) * position.quantity - position.commission - fill.commission

        trade = Trade(
            entry_time=position.entry_time,
            exit_time=exit_time,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=fill.effective_price,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            pnl=pnl,
            commission=position.commission + fill.commission,
            spread_cost=position.spread_cost + fill.spread_cost,
            slippage_cost=position.slippage_cost + fill.slippage_cost,
            exit_reason=reason,
        )
        return cash, trade.__dict__.copy()

    def _apply_protective_adjustments(self, position: Position, close_price: float) -> None:
        point = max(position.point_value, 1e-12)
        if position.side == "long":
            profit_points = (close_price - position.entry_price) / point
            if position.risk_free_activation is not None and position.risk_free_offset is not None and profit_points >= position.risk_free_activation:
                new_stop = position.entry_price + position.risk_free_offset * point
                if position.stop_loss is None or new_stop > position.stop_loss:
                    position.stop_loss = new_stop
            if position.trailing_start is not None and position.trailing_step is not None and profit_points >= position.trailing_start:
                new_stop = close_price - position.trailing_step * point
                if position.stop_loss is None or new_stop > position.stop_loss:
                    position.stop_loss = new_stop
        else:
            profit_points = (position.entry_price - close_price) / point
            if position.risk_free_activation is not None and position.risk_free_offset is not None and profit_points >= position.risk_free_activation:
                new_stop = position.entry_price - position.risk_free_offset * point
                if position.stop_loss is None or new_stop < position.stop_loss:
                    position.stop_loss = new_stop
            if position.trailing_start is not None and position.trailing_step is not None and profit_points >= position.trailing_start:
                new_stop = close_price + position.trailing_step * point
                if position.stop_loss is None or new_stop < position.stop_loss:
                    position.stop_loss = new_stop

    def _protective_exit_price(self, position: Position, current_bar: pd.Series) -> tuple[float, str] | None:
        high = float(current_bar["high"])
        low = float(current_bar["low"])
        if position.side == "long":
            if position.stop_loss is not None and low <= position.stop_loss:
                return float(position.stop_loss), "stop_loss"
            if position.take_profit is not None and high >= position.take_profit:
                return float(position.take_profit), "take_profit"
            return None
        if position.stop_loss is not None and high >= position.stop_loss:
            return float(position.stop_loss), "stop_loss"
        if position.take_profit is not None and low <= position.take_profit:
            return float(position.take_profit), "take_profit"
        return None

    def run(self, frame: pd.DataFrame, strategy: BaseStrategy, symbol: str) -> BacktestResult:
        strategy.reset()
        cash = self.config.initial_capital
        position: Position | None = None
        trades: list[dict] = []
        equity_points: list[tuple[object, float]] = []
        lookahead_ok = True

        for i in range(len(frame)):
            history = frame.iloc[:i]
            current_bar = frame.iloc[i]
            mark_price = float(current_bar["close"])
            marked_equity = self._mark_to_market_equity(cash, position, mark_price)
            equity_points.append((frame.index[i], marked_equity))
            if i == 0:
                continue

            avg_volume = float(history["volume"].tail(20).mean()) if not history.empty else float(current_bar["volume"])
            volatility = float(history["close"].pct_change().tail(20).std() or 0.0)

            if position is not None and position.side == "short" and marked_equity <= 0:
                cash, trade = self._close_position(cash, position, frame.index[i], mark_price, avg_volume, volatility, "margin_call")
                cash = max(cash, 0.0)
                trades.append(trade)
                position = None
                equity_points[-1] = (frame.index[i], cash)
                continue

            if position is not None and position.engine_managed_exits:
                self._apply_protective_adjustments(position, mark_price)
                protective_exit = self._protective_exit_price(position, current_bar)
                if protective_exit is not None:
                    exit_price, reason = protective_exit
                    cash, trade = self._close_position(cash, position, frame.index[i], exit_price, avg_volume, volatility, reason)
                    trades.append(trade)
                    position = None
                    equity_points[-1] = (frame.index[i], cash)
                    continue

            context = StrategyContext(symbol=symbol, data=frame, history=history, current_index=i)
            pre_signal_state = copy.deepcopy(getattr(strategy, "__dict__", {}))
            signal = strategy.generate_signal(context)
            post_signal_state = copy.deepcopy(getattr(strategy, "__dict__", {}))
            shifted_frame = frame.copy()
            shifted_frame.iloc[i:, shifted_frame.columns.get_loc("close")] += 777
            shifted_context = StrategyContext(symbol=symbol, data=shifted_frame, history=shifted_frame.iloc[:i], current_index=i)
            strategy.__dict__.clear()
            strategy.__dict__.update(copy.deepcopy(pre_signal_state))
            shifted_signal = strategy.generate_signal(shifted_context)
            strategy.__dict__.clear()
            strategy.__dict__.update(post_signal_state)
            lookahead_ok = lookahead_ok and repr(signal) == repr(shifted_signal)

            if signal is None:
                continue

            explicit_price = self._signal_execution_price(signal)
            if explicit_price is None:
                execution_time, raw_price = self._execution_price(frame, i)
            else:
                execution_time, raw_price = frame.index[i], explicit_price

            if position is None:
                if signal.action == "buy":
                    cash, position = self._open_position(cash, signal, execution_time, raw_price, avg_volume, volatility)
                elif signal.action == "sell" and self.config.allow_shorting:
                    cash, position = self._open_position(cash, signal, execution_time, raw_price, avg_volume, volatility)
            else:
                should_close = (position.side == "long" and signal.action == "sell") or (position.side == "short" and signal.action == "buy")
                if should_close:
                    exit_reason = "signal_exit"
                    if signal.metadata and signal.metadata.get("exit_reason"):
                        exit_reason = str(signal.metadata["exit_reason"])
                    cash, trade = self._close_position(cash, position, execution_time, raw_price, avg_volume, volatility, exit_reason)
                    trades.append(trade)
                    position = None

            equity_points[-1] = (frame.index[i], self._mark_to_market_equity(cash, position, mark_price))

        if position is not None:
            final_price = float(frame.iloc[-1]["close"])
            avg_volume = float(frame["volume"].tail(20).mean())
            cash, trade = self._close_position(cash, position, frame.index[-1], final_price, avg_volume, 0.0, "forced_exit")
            trades.append(trade)

        equity_curve = pd.Series({timestamp: value for timestamp, value in equity_points}, dtype=float)
        if not equity_curve.empty:
            equity_curve.iloc[-1] = cash
        trust = {
            "seed": self.config.random_seed,
            "execution_model": self.config.execution_model,
            "execution_mode": self.config.execution_mode,
            "execution_profile_path": self.config.execution_profile_path,
            "execution_profile_hash": self.config.execution_profile_hash,
            "lookahead_verification_passed": lookahead_ok,
            "cost_breakdown": {
                "commission": float(sum(trade["commission"] for trade in trades)),
                "spread": float(sum(trade["spread_cost"] for trade in trades)),
                "slippage": float(sum(trade["slippage_cost"] for trade in trades)),
            },
            "reproducibility_hash": self.cost_engine.reproducibility_hash(trades),
        }
        return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=summarize(equity_curve), trust=trust)
