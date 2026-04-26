"""Paper trading engine using real or simulated price ticks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from analysis.reporter import write_json_report
from core.cost_engine import CostEngine
from live.risk_manager import TradingRiskManager
from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


@dataclass
class PaperPosition:
    symbol: str
    quantity: float
    entry_price: float
    entry_time: str


@dataclass
class PaperTradingEngine:
    strategy: BaseStrategy
    symbol: str
    capital: float
    cost_engine: CostEngine
    risk_manager: TradingRiskManager
    report_dir: str | Path
    trade_history: list[dict[str, Any]] = field(default_factory=list)
    cash: float = 0.0
    position: PaperPosition | None = None
    price_history: list[dict[str, float | str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cash = self.capital
        self.report_dir = Path(self.report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.strategy.reset()

    def _history_frame(self) -> pd.DataFrame:
        if not self.price_history:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        frame = pd.DataFrame(self.price_history)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        return frame.set_index("timestamp")[["open", "high", "low", "close", "volume"]]

    def _signal(self, frame: pd.DataFrame) -> Signal | None:
        current_index = len(frame) - 1
        if current_index <= 0:
            return None
        context = StrategyContext(symbol=self.symbol, data=frame, history=frame.iloc[:current_index], current_index=current_index)
        signal = self.strategy.generate_signal(context)
        if signal is not None and not isinstance(signal, Signal):
            raise TypeError("generate_signal must return Signal or None")
        return signal

    def _default_quantity(self, price: float) -> float:
        return self.risk_manager.recommended_quantity(self.cash, price)

    def _execute_buy(self, timestamp: str, price: float, quantity: float) -> None:
        fill = self.cost_engine.apply(price, quantity, "buy", avg_volume=1_000.0, volatility=0.0)
        total_cost = fill.effective_price * quantity + fill.commission
        if total_cost > self.cash:
            return
        self.cash -= total_cost
        self.position = PaperPosition(symbol=self.symbol, quantity=quantity, entry_price=fill.effective_price, entry_time=timestamp)
        self.risk_manager.record_fill(self.symbol, "buy", quantity)
        self.trade_history.append({
            "timestamp": timestamp,
            "symbol": self.symbol,
            "side": "buy",
            "quantity": quantity,
            "price": fill.effective_price,
            "commission": fill.commission,
            "spread_cost": fill.spread_cost,
            "slippage_cost": fill.slippage_cost,
            "mode": "paper",
        })

    def _execute_sell(self, timestamp: str, price: float, quantity: float) -> None:
        fill = self.cost_engine.apply(price, quantity, "sell", avg_volume=1_000.0, volatility=0.0)
        self.cash += fill.effective_price * quantity - fill.commission
        pnl = 0.0
        if self.position is not None:
            pnl = (fill.effective_price - self.position.entry_price) * quantity - fill.commission
            self.risk_manager.record_realized_pnl(pnl)
        self.risk_manager.record_fill(self.symbol, "sell", quantity)
        self.trade_history.append({
            "timestamp": timestamp,
            "symbol": self.symbol,
            "side": "sell",
            "quantity": quantity,
            "price": fill.effective_price,
            "commission": fill.commission,
            "spread_cost": fill.spread_cost,
            "slippage_cost": fill.slippage_cost,
            "pnl": pnl,
            "mode": "paper",
        })
        self.position = None

    def on_tick(self, timestamp: str, price: float, volume: float = 0.0) -> Signal | None:
        self.price_history.append({"timestamp": timestamp, "open": price, "high": price, "low": price, "close": price, "volume": volume})
        frame = self._history_frame()
        signal = self._signal(frame)
        if signal is None:
            return None
        quantity = float(signal.metadata.get("quantity")) if signal.metadata and signal.metadata.get("quantity") else self._default_quantity(price)
        if quantity <= 0:
            return signal
        allowed, _ = self.risk_manager.allow_order(self.symbol, quantity, price)
        if not allowed:
            return signal
        if signal.action == "buy" and self.position is None:
            self._execute_buy(timestamp, price, quantity)
        elif signal.action == "sell" and self.position is not None:
            self._execute_sell(timestamp, price, self.position.quantity)
        return signal

    def report(self, session_id: str, status: str = "stopped") -> Path:
        mark_price = self.price_history[-1]["close"] if self.price_history else 0.0
        equity = self.cash + ((self.position.quantity * mark_price) if self.position is not None else 0.0)
        payload = {
            "session_id": session_id,
            "symbol": self.symbol,
            "status": status,
            "cash": self.cash,
            "equity": equity,
            "open_position": None if self.position is None else self.position.__dict__.copy(),
            "trades": self.trade_history,
            "ticks_processed": len(self.price_history),
        }
        path = self.report_dir / f"{session_id}.json"
        write_json_report(path, payload)
        return path


@dataclass
class PaperTrader:
    cash: float
    positions: dict[str, float] = field(default_factory=dict)
    orders: list[dict] = field(default_factory=list)

    def execute(self, symbol: str, side: str, quantity: float, price: float) -> dict:
        order = {"symbol": symbol, "side": side, "quantity": quantity, "price": price}
        if side == "buy":
            self.cash -= quantity * price
            self.positions[symbol] = self.positions.get(symbol, 0.0) + quantity
        else:
            self.cash += quantity * price
            self.positions[symbol] = self.positions.get(symbol, 0.0) - quantity
        self.orders.append(order)
        return order
