"""Live engine orchestration.

Limitations:
- Runs strategies synchronously on provided bars and does not open sockets itself.
"""

from __future__ import annotations

from pathlib import Path

from core.order_manager import OrderManager, OrderRequest
from strategies.base.context import StrategyContext
from strategies.base.strategy_interface import BaseStrategy


class LiveEngine:
    """Execute strategies against live-like bars."""

    def __init__(self, order_manager: OrderManager, confirm_required: bool = True, stop_file: str | Path = "STOP_TRADING") -> None:
        self.order_manager = order_manager
        self.confirm_required = confirm_required
        self.stop_file = Path(stop_file)

    def on_bar(self, strategy: BaseStrategy, symbol: str, frame, current_index: int, confirm: bool = False):
        if self.stop_file.exists():
            return None
        if self.confirm_required and not confirm:
            return None
        context = StrategyContext(symbol=symbol, data=frame, history=frame.iloc[:current_index], current_index=current_index)
        signal = strategy.generate_signal(context)
        if signal is None:
            return None
        price = float(frame.iloc[current_index]["close"])
        if signal.action in {"buy", "sell"}:
            return self.order_manager.place(OrderRequest(symbol=symbol, side=signal.action, quantity=1.0, price=price))
        return None
