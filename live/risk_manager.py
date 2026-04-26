"""Risk controls shared by paper and live trading sessions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskState:
    starting_capital: float
    max_position_size: float
    max_daily_loss: float
    risk_per_trade: float
    realized_pnl: float = 0.0
    positions: dict[str, float] = field(default_factory=dict)

    def equity(self, prices: dict[str, float], cash: float) -> float:
        total = cash
        for symbol, quantity in self.positions.items():
            total += quantity * prices.get(symbol, 0.0)
        return total


class TradingRiskManager:
    """Position-size and account-level guards for trading sessions."""

    def __init__(self, starting_capital: float, max_position_size: float, max_daily_loss: float, risk_per_trade: float) -> None:
        self.state = RiskState(
            starting_capital=starting_capital,
            max_position_size=max_position_size,
            max_daily_loss=max_daily_loss,
            risk_per_trade=risk_per_trade,
        )

    def max_notional(self) -> float:
        return self.state.starting_capital * self.state.max_position_size

    def allow_order(self, symbol: str, quantity: float, price: float) -> tuple[bool, str | None]:
        notional = abs(quantity * price)
        if notional > self.max_notional():
            return False, "max_position_size"
        if -self.state.realized_pnl >= self.state.starting_capital * self.state.max_daily_loss:
            return False, "max_daily_loss"
        return True, None

    def recommended_quantity(self, cash: float, price: float) -> float:
        target_notional = min(cash * self.state.risk_per_trade, self.max_notional())
        if price <= 0:
            return 0.0
        return max(target_notional / price, 0.0)

    def record_fill(self, symbol: str, side: str, quantity: float) -> None:
        signed = quantity if side == "buy" else -quantity
        self.state.positions[symbol] = self.state.positions.get(symbol, 0.0) + signed

    def record_realized_pnl(self, pnl: float) -> None:
        self.state.realized_pnl += pnl
