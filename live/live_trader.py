"""Live trading engine with risk checks and audit reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from analysis.reporter import write_json_report
from live.order_manager import TradingOrderManager
from live.risk_manager import TradingRiskManager
from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


@dataclass
class LiveTradingEngine:
    strategy: BaseStrategy
    symbol: str
    capital: float
    order_manager: TradingOrderManager
    risk_manager: TradingRiskManager
    report_dir: str | Path
    trade_log: list[dict[str, Any]] = field(default_factory=list)
    price_history: list[dict[str, float | str]] = field(default_factory=list)
    open_position: float = 0.0

    def __post_init__(self) -> None:
        self.report_dir = Path(self.report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.strategy.reset()

    def _history_frame(self) -> pd.DataFrame:
        if not self.price_history:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        frame = pd.DataFrame(self.price_history)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        return frame.set_index("timestamp")[["open", "high", "low", "close", "volume"]]

    def on_tick(self, timestamp: str, price: float, volume: float = 0.0) -> Signal | None:
        self.price_history.append({"timestamp": timestamp, "open": price, "high": price, "low": price, "close": price, "volume": volume})
        frame = self._history_frame()
        current_index = len(frame) - 1
        if current_index <= 0:
            return None
        signal = self.strategy.generate_signal(StrategyContext(symbol=self.symbol, data=frame, history=frame.iloc[:current_index], current_index=current_index))
        if signal is None:
            return None
        quantity = float(signal.metadata.get("quantity")) if signal.metadata and signal.metadata.get("quantity") else self.risk_manager.recommended_quantity(self.capital, price)
        if quantity <= 0:
            return signal
        allowed, reason = self.risk_manager.allow_order(self.symbol, quantity, price)
        if not allowed:
            self.trade_log.append({"timestamp": timestamp, "event": "blocked", "reason": reason, "signal": signal.action, "price": price})
            return signal
        if signal.action == "buy":
            order = self.order_manager.place(self.symbol, "buy", quantity, price=None, order_type="market")
            self.open_position += quantity
            self.risk_manager.record_fill(self.symbol, "buy", quantity)
        elif signal.action == "sell" and self.open_position > 0:
            order = self.order_manager.place(self.symbol, "sell", self.open_position, price=None, order_type="market")
            self.risk_manager.record_fill(self.symbol, "sell", self.open_position)
            self.open_position = 0.0
        else:
            return signal
        self.trade_log.append({"timestamp": timestamp, "signal": signal.action, "price": price, "quantity": quantity, "order_id": order.order_id, "response": order.response})
        return signal

    def emergency_stop(self) -> list[dict[str, Any]]:
        canceled: list[dict[str, Any]] = []
        for order in self.order_manager.open_orders():
            canceled.append(self.order_manager.cancel(order.order_id))
        return canceled

    def report(self, session_id: str, status: str = "stopped") -> Path:
        payload = {
            "session_id": session_id,
            "symbol": self.symbol,
            "status": status,
            "open_position": self.open_position,
            "trades": self.trade_log,
            "audit_log": self.order_manager.audit_log,
            "open_orders": [order.__dict__.copy() for order in self.order_manager.open_orders()],
        }
        return write_json_report(self.report_dir / f"{session_id}.json", payload)
